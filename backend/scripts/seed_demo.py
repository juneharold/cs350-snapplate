"""Seed two contrasting, data-rich demo users (B & C) for the demo video.

Creates curated diary histories so the live taste pipeline produces visibly
different flavor radars, top categories, time heatmaps, persona labels, and
recommendation feeds — the money shot for demo flows 6 (Taste) and 7 (Recommends).

  - User B "Junho Kang"  → carnivore: Korean BBQ / Comfort Korean / Korean,
    rich-smoky-savory notes, evening + weekend meals.
  - User C "Seoyeon Lim" → light/healthy: Noodles / Japanese / Cafe,
    light-fresh-sour notes, weekday lunches.

The seed is ADDITIVE (reuses real Kakao restaurants, never deletes existing data)
and idempotent (re-uses B/C by email; only tops up entries when short).

Run:   cd backend && uv run python -m scripts.seed_demo
Flags: --skip-taste     create users/entries but don't run the taste pipeline
       --taste-only     skip seeding, just (re)run the taste pipeline for B & C
       --force-entries  add a fresh batch of entries even if the user already has some
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import aioboto3
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.env import Env, db_dsn
from app.config.jwt import issue_token
from app.config.lifespan import Context, _build_profile_provider
from app.dto.restaurant import KakaoRestaurantData
from app.models.entry import EntryMediaModel, EntryModel
from app.models.media import MediaModel
from app.models.restaurant import RestaurantModel
from app.models.user import UserModel
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.repositories.restaurant import RestaurantRepository
from app.services.algorithm.service import AlgorithmService
from app.services.kakao.client import KakaoService
from app.services.main.taste import TasteService
from app.services.s3.storage import StorageService
from app.types.restaurant import FoodTone
from app.utils.restaurant_taxonomy import (
    UnknownRestaurantCategoryError,
    normalize_public_restaurant_category,
)
from app.utils.time import meal_period as derive_meal_period
from app.utils.time import utcnow

# KAIST / Daejeon area — matches FALLBACK_LOCATION the frontend uses.
ANCHOR_LAT = 36.371
ANCHOR_LNG = 127.361

ASSET_DIR = Path(__file__).resolve().parent / "demo_assets"


# ───────────────────────────────────────────────────────────────────────────
# Entry spec: one diary entry to create for a persona.
#   category   — MUST be a public taxonomy category (drives top-categories chart)
#   note       — natural language carrying flavor/context keywords
#   rating     — 0.5..5.0
#   utc_hour   — captured_at hour IN UTC; binning (_hour_bucket / meal_period) is
#                UTC-based, so this directly controls the heatmap row + meal period
#   weekday    — 0=Mon .. 6=Sun (heatmap column)
#   week_ago   — how many weeks back (spreads history over ~6 weeks)
#   photo_kw   — LoremFlickr keyword(s) for a dish-matched cover photo
#   tone       — FoodTone for the placeholder/label accent
# ───────────────────────────────────────────────────────────────────────────
@dataclass
class EntrySpec:
    dish: str
    category: str
    note: str
    rating: float
    utc_hour: int
    weekday: int
    week_ago: int
    photo_kw: str
    tone: FoodTone


@dataclass
class Persona:
    email: str
    nickname: str
    entries: list[EntrySpec]


# Evenings (utc_hour 18-21 → "dinner" + "7 PM"/"10 PM" rows), weekends skew.
USER_B = Persona(
    email="junho.kang.kr@gmail.com",
    nickname="Junho Kang",
    entries=[
        EntrySpec("Thick-cut samgyeopsal", "Korean BBQ",
                  "Thick-cut samgyeopsal grilled at the table — super smoky and rich, "
                  "fat crisping up perfect. Best shared with the whole group.",
                  5.0, 19, 5, 1, "korean,barbecue,pork,grill", FoodTone.CHAR),
        EntrySpec("Wood-fire galbi", "Korean BBQ",
                  "Marinated galbi over charcoal, deeply savory and a little sweet. "
                  "Hearty group dinner, everyone went back for seconds.",
                  4.5, 20, 6, 1, "galbi,korean,beef,bbq", FoodTone.RUST),
        EntrySpec("Pork gukbap", "Comfort Korean",
                  "Hearty dwaeji-gukbap, deep savory umami broth — hit the spot on a cold night.",
                  4.5, 18, 2, 2, "korean,soup,pork,broth", FoodTone.HAY),
        EntrySpec("Kimchi jjigae", "Comfort Korean",
                  "Bubbling kimchi jjigae, rich and a bit spicy, loaded with pork belly. "
                  "Proper comfort food.",
                  4.0, 19, 3, 2, "kimchi,stew,korean,spicy", FoodTone.PAPRIKA),
        EntrySpec("Spicy dakgalbi", "Korean BBQ",
                  "Sizzling dakgalbi, smoky and spicy, cheese pull at the end. Loud, fun group meal.",
                  4.5, 20, 5, 3, "dakgalbi,chicken,korean,spicy", FoodTone.PAPRIKA),
        EntrySpec("Beef bulgogi set", "Korean",
                  "Bulgogi, savory-sweet and tender, piled over rice. Filling and satisfying.",
                  4.0, 18, 1, 3, "bulgogi,korean,beef,rice", FoodTone.OCHRE),
        EntrySpec("Grilled hanwoo", "Korean BBQ",
                  "Splurged on hanwoo — buttery, rich marbling, melts on the grill. "
                  "Special occasion dinner with friends.",
                  5.0, 21, 6, 4, "wagyu,beef,grill,bbq", FoodTone.RUST),
        EntrySpec("Sundae gukbap", "Comfort Korean",
                  "Sundae-gukbap, hearty and warming, deep meaty broth. Solid late dinner.",
                  4.0, 20, 4, 4, "korean,soup,broth,meat", FoodTone.HAY),
        EntrySpec("Jokbal platter", "Korean",
                  "Jokbal — sticky, savory, rich braised pork. Big platter for the table.",
                  4.5, 19, 5, 5, "jokbal,pork,korean,braised", FoodTone.TERRA),
        EntrySpec("Budae jjigae", "Comfort Korean",
                  "Army stew, salty and rich and spicy, everything thrown in. Group favorite.",
                  4.0, 18, 6, 5, "budae,stew,korean,spicy", FoodTone.PAPRIKA),
        EntrySpec("Yangnyeom + fried chicken", "Korean",
                  "Half-half fried chicken, crispy and smoky-sweet. Beers with the crew.",
                  4.5, 21, 4, 6, "korean,fried,chicken,crispy", FoodTone.OCHRE),
        EntrySpec("Galmegisal BBQ", "Korean BBQ",
                  "Skirt-meat galmegisal, smoky char and super savory. Another great grill night.",
                  5.0, 20, 5, 6, "pork,grill,bbq,smoky", FoodTone.CHAR),
        EntrySpec("Gamjatang", "Comfort Korean",
                  "Gamjatang, rich pork-bone broth, hearty and spicy. Warming weekend dinner.",
                  4.5, 19, 6, 2, "gamjatang,korean,soup,spicy", FoodTone.HAY),
    ],
)

# Weekday lunches (utc_hour 11-13 → "lunch" + "12 PM" row), solo skew.
USER_C = Persona(
    email="seoyeon.lim.eats@gmail.com",
    nickname="Seoyeon Lim",
    entries=[
        EntrySpec("Mul-naengmyeon", "Noodles",
                  "Cold mul-naengmyeon, light and tangy, so refreshing. Quiet solo lunch.",
                  4.5, 12, 0, 1, "naengmyeon,noodles,cold,korean", FoodTone.BONE),
        EntrySpec("Salmon sushi set", "Japanese",
                  "Salmon sushi set, clean and delicate, fresh fish. Calm weekday lunch alone.",
                  4.0, 12, 1, 1, "sushi,salmon,japanese,fresh", FoodTone.CREAM),
        EntrySpec("Cold soba", "Japanese",
                  "Chilled zaru soba, light and nutty with a crisp dipping sauce. Refreshing.",
                  4.0, 13, 2, 2, "soba,noodles,japanese,cold", FoodTone.MOSS),
        EntrySpec("Makguksu", "Noodles",
                  "Buckwheat makguksu, tangy and fresh, bright and sour. Light solo meal.",
                  4.5, 11, 3, 2, "noodles,buckwheat,korean,fresh", FoodTone.MOSS),
        EntrySpec("Matcha latte + scone", "Cafe",
                  "Matcha latte and a plain scone, light and a little sweet. Cozy study cafe.",
                  4.0, 13, 4, 3, "matcha,latte,cafe,coffee", FoodTone.FOREST),
        EntrySpec("Kalguksu", "Noodles",
                  "Clean anchovy-broth kalguksu, light and comforting. Easy weekday lunch.",
                  3.5, 12, 0, 3, "kalguksu,noodles,soup,korean", FoodTone.BONE),
        EntrySpec("Sashimi don", "Japanese",
                  "Sashimi rice bowl, fresh and clean, delicate slices over vinegared rice.",
                  4.5, 12, 1, 4, "sashimi,don,japanese,fresh", FoodTone.CREAM),
        EntrySpec("Iced americano + salad", "Cafe",
                  "Iced americano and a light citrus salad — crisp, fresh, a little sour. Solo break.",
                  3.8, 13, 2, 4, "americano,coffee,cafe,salad", FoodTone.HAY),
        EntrySpec("Udon", "Japanese",
                  "Kake udon, light dashi broth, soft and soothing. Gentle midday meal.",
                  4.0, 11, 3, 5, "udon,noodles,japanese,broth", FoodTone.BUTTER),
        EntrySpec("Bibim-guksu", "Noodles",
                  "Bibim-guksu, tangy and bright and a touch sweet-sour. Refreshing solo lunch.",
                  4.0, 12, 4, 5, "noodles,korean,spicy,fresh", FoodTone.PAPRIKA),
        EntrySpec("Fruit tart + tea", "Cafe",
                  "Fresh fruit tart and herbal tea, light and sweet. Slow afternoon cafe stop.",
                  4.5, 13, 0, 6, "fruit,tart,cafe,dessert", FoodTone.BERRY),
        EntrySpec("Chirashi bowl", "Japanese",
                  "Chirashi, clean and fresh, assorted sashimi over rice. Bright, delicate flavors.",
                  4.5, 12, 1, 6, "chirashi,sushi,japanese,fresh", FoodTone.CREAM),
        EntrySpec("Cold kongguksu", "Noodles",
                  "Kongguksu, chilled soybean broth, light and nutty and mild. Summery solo lunch.",
                  4.0, 11, 2, 2, "noodles,soybean,korean,cold", FoodTone.BONE),
    ],
)

# Korean keywords to top up restaurants per needed public category, near KAIST.
CATEGORY_SEARCH_KEYWORDS = {
    "Korean BBQ": ["삼겹살", "갈비", "고기집"],
    "Comfort Korean": ["국밥", "찌개", "감자탕"],
    "Korean": ["한식", "백반"],
    "Noodles": ["국수", "냉면", "칼국수"],
    "Japanese": ["초밥", "일식", "돈카츠"],
    "Cafe": ["카페", "커피"],
}

DEMO_RESTAURANT_NAMES = {
    "Korean BBQ": ["Demo Charcoal Table", "Demo Galbi House", "Demo Samgyeopsal Lab"],
    "Comfort Korean": ["Demo Gukbap Kitchen", "Demo Stew House", "Demo Soup Table"],
    "Korean": ["Demo Hansik Table", "Demo Campus Baekban", "Demo Home Meal"],
    "Noodles": ["Demo Noodle Bar", "Demo Kalguksu Room", "Demo Cold Noodle House"],
    "Japanese": ["Demo Sushi Counter", "Demo Donkatsu Table", "Demo Udon Bar"],
    "Cafe": ["Demo Slow Cafe", "Demo Cream Coffee", "Demo Study Cafe"],
}


def demo_fallback_restaurants(needed: dict[str, int]) -> list[KakaoRestaurantData]:
    items: list[KakaoRestaurantData] = []
    for category, count in needed.items():
        names = DEMO_RESTAURANT_NAMES.get(category, [f"Demo {category} Table"])
        for index in range(count):
            name = names[index % len(names)]
            suffix = f"{category.lower().replace(' ', '-').replace('/', '')}-{index + 1}"
            items.append(
                KakaoRestaurantData(
                    kakao_id=f"demo-{suffix}",
                    name=name if index < len(names) else f"{name} {index + 1}",
                    category=category,
                    signature_dish=category,
                    rating=round(4.1 + (index % 5) * 0.1, 1),
                    rating_count=80 + index * 17,
                    thumbnail_tone=FoodTone.BONE,
                    thumbnail_label=category,
                    tags=[category],
                    lat=ANCHOR_LAT + index * 0.001,
                    lng=ANCHOR_LNG + index * 0.001,
                    neighborhood="Eoeun-dong",
                    address="Demo data near KAIST",
                    raw_payload={"category_name": f"음식점 > Demo > {category}"},
                )
            )
    return items


# ───────────────────────────────────────────────────────────────────────────
# Photo sourcing — LoremFlickr (keyword, no API key) → Foodish → gray placeholder.
# Cached on disk so re-runs don't re-fetch and image choices stay stable.
# ───────────────────────────────────────────────────────────────────────────
def _gray_placeholder() -> bytes:
    # Minimal valid 1x1 grayscale JPEG (enough to satisfy the vision call + storage).
    return bytes.fromhex(
        "ffd8ffdb0043000302020302020303030304030304050805050404050a070706080c0a0c0c0b0a"
        "0b0b0d0e12100d0e110e0b0b1016101113141515150c0f17181614180d141514ffc9000b080001"
        "00010101011100ffcc000600101005ffda0008010100003f00d2cf20ffd9"
    )


async def fetch_photo(
    client: httpx.AsyncClient, dish_key: str, keyword: str
) -> tuple[bytes, str, bool]:
    """Return (jpeg_bytes, source, is_real). Caches to demo_assets/."""
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    cached = ASSET_DIR / f"{dish_key}.jpg"
    if cached.exists() and cached.stat().st_size > 1024:
        return cached.read_bytes(), "cache", True

    lock = abs(hash(dish_key)) % 9999
    candidates = [
        f"https://loremflickr.com/640/480/{keyword}?lock={lock}",
        "https://foodish-api.com/api/",  # returns JSON {"image": url}
    ]
    for url in candidates:
        try:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            if "foodish" in url:
                img_url = resp.json().get("image")
                if not img_url:
                    continue
                resp = await client.get(img_url, timeout=30)
                resp.raise_for_status()
            data = resp.content
            if len(data) > 1024 and data[:2] == b"\xff\xd8":
                cached.write_bytes(data)
                return data, url.split("?")[0], True
        except Exception as exc:  # noqa: BLE001
            print(f"    photo source failed ({url.split('?')[0]}): {exc}")
    return _gray_placeholder(), "placeholder", False


# ───────────────────────────────────────────────────────────────────────────
# Context wiring (mirrors app/config/lifespan.py) for a standalone script run.
# ───────────────────────────────────────────────────────────────────────────
async def _ensure_bucket(s3: aioboto3.Session) -> None:
    client = cast(Any, s3.client)(
        "s3",
        endpoint_url=Env.get(Env.S3_ENDPOINT),
        aws_access_key_id=Env.get(Env.S3_ACCESS_KEY),
        aws_secret_access_key=Env.get(Env.S3_SECRET_KEY),
        region_name=Env.get(Env.S3_REGION),
    )
    async with client as c:
        try:
            await c.create_bucket(Bucket=Env.get(Env.S3_BUCKET))
        except Exception:  # noqa: BLE001
            pass  # already exists


async def get_or_create_user(db: AsyncSession, persona: Persona) -> UserModel:
    existing = (
        await db.execute(select(UserModel).where(UserModel.email == persona.email))
    ).scalars().first()
    if existing is not None:
        if not existing.is_onboarded or existing.nickname != persona.nickname:
            existing.nickname = persona.nickname
            existing.is_onboarded = True
            db.add(existing)
            await db.commit()
        return existing
    user = UserModel(email=persona.email, nickname=persona.nickname, is_onboarded=True)
    db.add(user)
    await db.commit()
    return user


async def restaurants_by_category(
    db: AsyncSession, kakao: KakaoService, needed: dict[str, int]
) -> dict[str, list[RestaurantModel]]:
    """Return >= N usable (normalizable) restaurants per public category, fetching
    from Kakao to top up where the local cache is short. Additive upsert."""
    repo = RestaurantRepository(db)

    def public_cat(r: RestaurantModel) -> str | None:
        try:
            return normalize_public_restaurant_category(
                r.category, (r.raw_payload or {}).get("category_name")
            )
        except UnknownRestaurantCategoryError:
            return None

    def bucket(rows: list[RestaurantModel]) -> dict[str, list[RestaurantModel]]:
        out: dict[str, list[RestaurantModel]] = {c: [] for c in needed}
        for r in rows:
            pc = public_cat(r)
            if pc in out:
                out[pc].append(r)
        return out

    rows = list(await repo.list_active(category=None, min_rating=None, limit=500))
    buckets = bucket(rows)

    for category, count in needed.items():
        if len(buckets[category]) >= count:
            continue
        for keyword in CATEGORY_SEARCH_KEYWORDS.get(category, []):
            if len(buckets[category]) >= count:
                break
            try:
                found = await kakao.keyword_search(keyword, ANCHOR_LAT, ANCHOR_LNG, radius_m=8000)
            except Exception as exc:  # noqa: BLE001
                print(f"  kakao keyword_search '{keyword}' failed: {exc}")
                continue
            usable: list[KakaoRestaurantData] = []
            for k in found:
                try:
                    normalize_public_restaurant_category(
                        k.category, (k.raw_payload or {}).get("category_name")
                    )
                except UnknownRestaurantCategoryError:
                    continue
                usable.append(k)
            if usable:
                await repo.upsert_many(usable)
        rows = list(await repo.list_active(category=None, min_rating=None, limit=500))
        buckets = bucket(rows)
        if len(buckets[category]) < count:
            remaining = count - len(buckets[category])
            print(f"  using {remaining} demo fallback restaurant(s) for {category}")
            await repo.upsert_many(demo_fallback_restaurants({category: remaining}))
            rows = list(await repo.list_active(category=None, min_rating=None, limit=500))
            buckets = bucket(rows)

    return buckets


def _enrich_restaurant(r: RestaurantModel, category: str) -> None:
    """Give seeded-target restaurants a believable rating for the quality score
    and a signature dish, without touching unrelated rows."""
    if not r.rating:
        r.rating = round(4.0 + (abs(hash(r.id)) % 9) / 10.0, 1)  # 4.0..4.8
    if not r.rating_count:
        r.rating_count = 40 + abs(hash(r.id)) % 260


async def seed_entries_for(
    ctx: Context,
    http: httpx.AsyncClient,
    user: UserModel,
    persona: Persona,
    cat_pool: dict[str, list[RestaurantModel]],
    *,
    force: bool,
) -> int:
    db = ctx.db_session
    storage = StorageService(ctx.s3)

    existing = (
        await db.execute(
            select(func.count())
            .select_from(EntryModel)
            .where(EntryModel.user_id == user.id, EntryModel.deleted_at.is_(None))
        )
    ).scalar_one()
    if existing >= len(persona.entries) and not force:
        print(f"  {persona.nickname}: {existing} entries already present — skipping (use --force-entries).")
        return 0

    now = datetime.now(timezone.utc)
    cursor = {c: 0 for c in cat_pool}
    created = 0
    missing_photos: list[str] = []

    for spec in persona.entries:
        pool = cat_pool.get(spec.category) or []
        if not pool:
            print(f"  ! no restaurant for category '{spec.category}', skipping '{spec.dish}'")
            continue
        restaurant = pool[cursor[spec.category] % len(pool)]
        cursor[spec.category] += 1
        _enrich_restaurant(restaurant, spec.category)
        if not restaurant.signature_dish:
            restaurant.signature_dish = spec.dish
        db.add(restaurant)

        # captured_at: chosen weekday/hour, N weeks back; clamp to <= now.
        base = now - timedelta(weeks=spec.week_ago)
        delta_days = (spec.weekday - base.weekday()) % 7
        captured = (base + timedelta(days=delta_days)).replace(
            hour=spec.utc_hour, minute=abs(hash(spec.dish)) % 60, second=0, microsecond=0
        )
        if captured > now:
            captured -= timedelta(days=7)

        dish_key = f"{persona.nickname.split()[0].lower()}-{spec.dish.lower().replace(' ', '-').replace('+', 'and')}"
        photo, source, is_real = await fetch_photo(http, dish_key, spec.photo_kw)
        if not is_real:
            missing_photos.append(f"- {persona.nickname}: {spec.dish} (keyword: {spec.photo_kw})")

        media = MediaModel(
            user_id=user.id,
            storage_key=f"media/{user.id}/{spec.dish.lower().replace(' ', '_')}.jpg",
            width=640,
            height=480,
            bytes=len(photo),
            tone=spec.tone,
            label=spec.dish[:24],
            exif_captured_at=captured,
            exif_lat=restaurant.lat,
            exif_lng=restaurant.lng,
        )
        media.variant_keys = {"thumb": media.storage_key, "medium": media.storage_key}
        await storage.put(media.storage_key, photo)
        db.add(media)
        await db.flush()  # assign media.id

        entry = EntryModel(
            user_id=user.id,
            restaurant_id=restaurant.id,
            cover_media_id=media.id,
            captured_at=captured,
            meal_period=derive_meal_period(captured),
            rating=spec.rating,
            note=spec.note,
        )
        db.add(entry)
        await db.flush()  # assign entry.id
        db.add(EntryMediaModel(entry_id=entry.id, media_id=media.id, position=0, is_cover=True))
        created += 1
        print(f"    + {persona.nickname}: {spec.dish}  [{spec.category}]  ({source})")

    await db.commit()

    if missing_photos:
        shot = ASSET_DIR.parent / "shot_list.md"
        shot.write_text(
            "# Photos still needed (auto-download failed)\n\n"
            "Drop matching JPEGs into backend/scripts/demo_assets/ named "
            "`<first-name>-<dish>.jpg` and re-run with --force-entries.\n\n"
            + "\n".join(missing_photos)
            + "\n",
            encoding="utf-8",
        )
        print(f"  ⚠ {len(missing_photos)} photos used placeholders — see {shot}")
    return created


async def profile_seed_restaurants(
    ctx: Context,
    cat_pool: dict[str, list[RestaurantModel]],
) -> int:
    artifact_repo = AlgorithmArtifactRepository(ctx.db_session)
    generated_at = utcnow()
    restaurants = {restaurant.id: restaurant for rows in cat_pool.values() for restaurant in rows}
    created = 0
    for restaurant in restaurants.values():
        try:
            profile = ctx.algorithm_service.build_restaurant_profile_artifact(
                restaurant,
                generated_at=generated_at,
            )
        except UnknownRestaurantCategoryError as exc:
            print(f"  ! skipped restaurant profile for {restaurant.name}: {exc}")
            continue
        await artifact_repo.add_restaurant_profile(
            restaurant_id=restaurant.id,
            payload_json=profile.model_dump(mode="json"),
            embedding=profile.embedding,
            algorithm_version=profile.algorithm_version,
            generated_at=generated_at,
            commit=False,
        )
        created += 1
    await ctx.db_session.commit()
    return created


async def run_taste(ctx: Context, user: UserModel, persona: Persona) -> str | None:
    payload = await TasteService(ctx).recompute_and_store(user.id)
    label = (payload.get("type") or {}).get("label")
    has_enough = payload.get("has_enough_data")
    print(f"  {persona.nickname}: has_enough_data={has_enough}  type={label!r}")
    return label


async def smoke_test_profile_provider(algorithm: AlgorithmService) -> None:
    provider = algorithm.profile_provider
    print("Smoke-testing the configured profile provider …")
    try:
        provider.extract_text_profile("Grilled pork belly, smoky and rich.")
        provider.generate_profile_summary("cuisine: korean; taste: savory, smoky")
    except Exception as exc:  # noqa: BLE001
        print(
            "\n✗ Provider smoke test FAILED. Likely an invalid model id in "
            "app/config/algorithm.py or an API/key issue.\n"
            f"  error: {exc}\n"
            "  Fallbacks: set valid *_MODEL ids, or run the app with "
            "ALGORITHM_PROVIDER=deterministic (radar/categories/heatmap still differ; "
            "only the persona label becomes generic).\n"
        )
        raise
    provider.embed_text("savory smoky korean bbq")
    print("  ✓ provider OK\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo users B & C")
    parser.add_argument("--skip-taste", action="store_true")
    parser.add_argument("--taste-only", action="store_true")
    parser.add_argument("--force-entries", action="store_true")
    args = parser.parse_args()

    Env.load_defaults()
    algorithm_service = AlgorithmService(_build_profile_provider())
    engine = create_async_engine(db_dsn(), echo=False, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    s3 = aioboto3.Session()
    await _ensure_bucket(s3)

    personas = [USER_B, USER_C]

    async with httpx.AsyncClient(follow_redirects=True) as kakao_http, httpx.AsyncClient(
        follow_redirects=True
    ) as photo_http:
        kakao = KakaoService(kakao_http)

        if not args.skip_taste:
            await smoke_test_profile_provider(algorithm_service)

        async with sessionmaker() as session:
            ctx = Context(
                db_session=session,
                http_client=kakao_http,
                s3=s3,
                algorithm_service=algorithm_service,
            )

            users: dict[str, UserModel] = {}
            for persona in personas:
                users[persona.email] = await get_or_create_user(session, persona)

            if not args.taste_only:
                needed = {
                    "Korean BBQ": 4, "Comfort Korean": 3, "Korean": 3,
                    "Noodles": 4, "Japanese": 4, "Cafe": 3,
                }
                print("Resolving restaurants by category (Kakao top-up as needed) …")
                cat_pool = await restaurants_by_category(session, kakao, needed)
                for c, rows in cat_pool.items():
                    print(f"  {c}: {len(rows)} available")
                profiled_count = await profile_seed_restaurants(ctx, cat_pool)
                print(f"  restaurant profiles: {profiled_count}")

                for persona in personas:
                    print(f"\nSeeding entries for {persona.nickname} <{persona.email}> …")
                    await seed_entries_for(
                        ctx, photo_http, users[persona.email], persona, cat_pool,
                        force=args.force_entries,
                    )

            if not args.skip_taste:
                print("\nRunning taste pipeline with the configured provider …")
                for persona in personas:
                    await run_taste(ctx, users[persona.email], persona)

            print("\n── Demo login handles ──────────────────────────────")
            for persona in personas:
                user = users[persona.email]
                token, expires_in = issue_token(user.id)
                print(f"\n{persona.nickname} <{persona.email}>")
                print(f"  user_id: {user.id}")
                print(f"  taste_type: {user.taste_type!r}")
                print(f"  JWT (expires in {expires_in // 3600}h):\n  {token}")

    await engine.dispose()
    print(
        "\nFast demo login: in the running web app, open DevTools console and run:\n"
        "  const k='snapplate.auth'; const s=JSON.parse(localStorage.getItem(k)||'{\"state\":{},\"version\":0}');\n"
        "  s.state.accessToken='<JWT above>'; localStorage.setItem(k, JSON.stringify(s)); location.reload();\n"
        "  (set s.state.user too if route gates need it; or just use the magic-link flow.)\n"
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
