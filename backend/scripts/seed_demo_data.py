from __future__ import annotations

import asyncio
import base64
import contextlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Protocol, cast

import aioboto3
import httpx
from openai import OpenAI
from PIL import Image, ImageOps
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.algorithm import MIN_ENTRIES_FOR_PERSONALIZATION
from app.config.env import Env, db_dsn
from app.models.algorithm_artifact import RestaurantProfileArtifactModel
from app.models.bookmark import BookmarkModel
from app.models.entry import EntryMediaModel, EntryModel
from app.models.media import MediaModel
from app.models.restaurant import RestaurantModel
from app.models.taste_report import TasteReportModel
from app.models.user import UserModel
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.schemas.algorithm import (
    DiaryEntryInput,
    ProfileExtractionResult,
    ProfileSummaryResult,
    RecommendationContext,
    RestaurantInput,
)
from app.services.algorithm.providers import OpenAIProvider
from app.services.algorithm.service import AlgorithmService
from app.services.s3.storage import StorageService
from app.types.restaurant import FoodTone
from app.utils.time import utcnow

DEMO_USER_ID = "u_demo_seed"
DEMO_EMAIL = "demo@snapplate.app"
DEMO_NICKNAME = "SnapPlate Demo"

_KAKAO_IMAGE_SEARCH_URL = "https://dapi.kakao.com/v2/search/image"
_IMAGE_SIZES = {
    "original": (960, 720),
    "medium": (640, 480),
    "thumb": (320, 240),
}
_ALGORITHM_IMAGE_RESTAURANT_LIMIT = 6
_SEED_OPENAI_TIMEOUT_SECONDS = 90.0


@dataclass(frozen=True)
class RestaurantSeed:
    id: str
    kakao_id: str
    name: str
    category: str
    signature_dish: str
    rating: float
    rating_count: int
    distance_m: int
    thumbnail_tone: FoodTone
    thumbnail_label: str
    tags: tuple[str, ...]
    lat: float
    lng: float
    neighborhood: str
    address: str
    image_query: str
    thumbnail_url: str | None = None


@dataclass(frozen=True)
class EntrySeed:
    id: str
    user_id: str
    restaurant_id: str
    captured_at: datetime
    meal_period: str
    rating: float
    note: str
    ai_tags: tuple[str, ...]

    @property
    def media_id(self) -> str:
        return self.id.replace("e_", "m_", 1)


@dataclass(frozen=True)
class FetchedImage:
    source_url: str
    data: bytes


@dataclass(frozen=True)
class RestaurantImage:
    source_url: str
    variants: dict[str, bytes]


@dataclass(frozen=True)
class RestaurantImages:
    thumbnail: RestaurantImage
    entries: dict[str, RestaurantImage]


class SeedImageClient(Protocol):
    async def fetch_images(self, queries: Sequence[str], count: int) -> list[FetchedImage]:
        ...


@dataclass(frozen=True)
class DemoSeedData:
    demo_user_id: str
    demo_email: str
    demo_nickname: str
    peer_users: dict[str, str]
    visited_restaurants: tuple[RestaurantSeed, ...]
    candidate_restaurants: tuple[RestaurantSeed, ...]
    demo_entries: tuple[EntrySeed, ...]
    peer_entries: tuple[EntrySeed, ...]
    bookmarked_restaurant_ids: tuple[str, ...]

    @property
    def restaurants(self) -> tuple[RestaurantSeed, ...]:
        return self.visited_restaurants + self.candidate_restaurants

    def restaurant_by_id(self) -> dict[str, RestaurantSeed]:
        return {restaurant.id: restaurant for restaurant in self.restaurants}

    def demo_diary_inputs(self) -> list[DiaryEntryInput]:
        return self._diary_inputs(self.demo_entries)

    def peer_diary_inputs(self) -> list[DiaryEntryInput]:
        return self._diary_inputs(self.peer_entries)

    def candidate_restaurant_inputs(self) -> list[RestaurantInput]:
        return [_restaurant_input(restaurant) for restaurant in self.candidate_restaurants]

    def recommendation_context(self) -> RecommendationContext:
        return RecommendationContext(
            diary_entries=self.demo_diary_inputs(),
            peer_diary_entries=self.peer_diary_inputs(),
            candidate_restaurants=self.candidate_restaurant_inputs(),
            lat=36.371,
            lng=127.361,
            requested_at=_dt("2026-05-30T12:30:00Z"),
        )

    def _diary_inputs(self, entries: Sequence[EntrySeed]) -> list[DiaryEntryInput]:
        restaurants = self.restaurant_by_id()
        return [
            DiaryEntryInput(
                id=entry.id,
                user_id=entry.user_id,
                captured_at=entry.captured_at,
                restaurant=_restaurant_input(restaurants[entry.restaurant_id]),
                rating=entry.rating,
                note=entry.note,
                image_labels=list(entry.ai_tags),
            )
            for entry in entries
        ]


def require_openai_api_key() -> str:
    api_key = (Env.raw_get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for make db-seed.")
    return api_key


def require_kakao_api_key() -> str:
    api_key = (Env.raw_get("KAKAO_REST_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("KAKAO_REST_API_KEY is required for make db-seed images.")
    return api_key


def build_openai_algorithm_service(api_key: str) -> AlgorithmService:
    embeddings = OpenAIProvider(
        client=OpenAI(api_key=api_key, timeout=_SEED_OPENAI_TIMEOUT_SECONDS, max_retries=0),
        timeout_seconds=_SEED_OPENAI_TIMEOUT_SECONDS,
        fallback_to_deterministic_embedding=False,
    )
    return AlgorithmService(SeedArtifactProvider(embeddings))


class SeedArtifactProvider:
    def __init__(self, embeddings: OpenAIProvider) -> None:
        self.embeddings = embeddings

    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        return ProfileExtractionResult()

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        return ProfileExtractionResult()

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        return ProfileSummaryResult(
            label="The Campus Comfort Regular",
            blurb="Your demo profile is built from repeated campus meals, noodles, bakeries, and comfort dinners.",
            insights=[
                "Noodle and bakery visits are strong repeat signals.",
                "Peer overlap is seeded for collaborative recommendations.",
            ],
        )

    def embed_text(self, text: str) -> list[float]:
        return self.embeddings.embed_text(text)


def demo_seed_data() -> DemoSeedData:
    return DemoSeedData(
        demo_user_id=DEMO_USER_ID,
        demo_email=DEMO_EMAIL,
        demo_nickname=DEMO_NICKNAME,
        peer_users={
            "u_demo_peer_01": "peer-1@snapplate.app",
            "u_demo_peer_02": "peer-2@snapplate.app",
            "u_demo_peer_03": "peer-3@snapplate.app",
        },
        visited_restaurants=_VISITED_RESTAURANTS,
        candidate_restaurants=_CANDIDATE_RESTAURANTS,
        demo_entries=_DEMO_ENTRIES,
        peer_entries=_PEER_ENTRIES,
        bookmarked_restaurant_ids=("r_seed_candidate_bakery", "r_seed_candidate_bbq"),
    )


async def seed_demo_database(
    db: AsyncSession,
    s3: aioboto3.Session,
    algorithm: AlgorithmService,
    data: DemoSeedData | None = None,
) -> dict[str, int | str]:
    seed = data or demo_seed_data()
    storage = StorageService(s3)
    all_entries = [*seed.demo_entries, *seed.peer_entries]
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http_client:
        image_client = KakaoImageClient(http_client, require_kakao_api_key())
        restaurant_images = await _restaurant_images(image_client, seed.restaurants, all_entries)

    users = await _seed_users(db, seed)
    restaurants = await _seed_restaurants(db, seed.restaurants, restaurant_images)
    await _seed_media_objects(storage, all_entries, restaurant_images)
    media = await _seed_media(db, all_entries, users, restaurant_images)
    entries = await _seed_entries(db, all_entries, users, restaurants, media)
    await _seed_entry_media(db, entries, media)
    await _seed_bookmarks(db, users[seed.demo_user_id], restaurants, seed.bookmarked_restaurant_ids)
    await db.commit()

    await _seed_algorithm_artifacts(
        db,
        algorithm,
        seed,
        users[seed.demo_user_id],
        entries,
        restaurants,
        restaurant_images,
    )

    return {
        "demo_email": seed.demo_email,
        "demo_entries": len(seed.demo_entries),
        "peer_entries": len(seed.peer_entries),
        "restaurants": len(seed.restaurants),
        "candidate_restaurants": len(seed.candidate_restaurants),
    }


async def main() -> None:
    Env.load_defaults()
    try:
        api_key = require_openai_api_key()
        require_kakao_api_key()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    engine = create_async_engine(db_dsn(), echo=False, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    s3 = aioboto3.Session()
    await _ensure_bucket(s3)
    algorithm = build_openai_algorithm_service(api_key)
    try:
        async with sessionmaker() as db:
            summary = await seed_demo_database(db, s3, algorithm)
    finally:
        await engine.dispose()

    print(
        "Seeded SnapPlate demo data: "
        f"{summary['demo_entries']} demo entries, "
        f"{summary['peer_entries']} peer entries, "
        f"{summary['restaurants']} restaurants. "
        f"Sign in as {summary['demo_email']}."
    )


def _restaurant_input(restaurant: RestaurantSeed) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant.id,
        name=restaurant.name,
        category=restaurant.category,
        signature_dish=restaurant.signature_dish,
        rating=restaurant.rating,
        rating_count=restaurant.rating_count,
        distance_m=restaurant.distance_m,
        thumbnail_url=restaurant.thumbnail_url,
        thumbnail_tone=restaurant.thumbnail_tone,
        thumbnail_label=restaurant.thumbnail_label,
        tags=list(restaurant.tags),
        lat=restaurant.lat,
        lng=restaurant.lng,
        kakao_id=restaurant.kakao_id,
        neighborhood=restaurant.neighborhood,
    )


async def _seed_users(db: AsyncSession, seed: DemoSeedData) -> dict[str, UserModel]:
    users = {
        seed.demo_user_id: (seed.demo_email, seed.demo_nickname),
        **{
            user_id: (email, f"Demo Peer {index}")
            for index, (user_id, email) in enumerate(seed.peer_users.items(), 1)
        },
    }
    out = {}
    for user_id, (email, nickname) in users.items():
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = UserModel(
                id=user_id,
                email=email,
                nickname=nickname,
                is_onboarded=True,
                deleted_at=None,
            )
        else:
            user.nickname = nickname
            user.is_onboarded = True
            user.deleted_at = None
        db.add(user)
        await db.flush()
        out[user_id] = user
    return out


async def _seed_restaurants(
    db: AsyncSession,
    restaurant_seeds: Sequence[RestaurantSeed],
    restaurant_images: dict[str, RestaurantImages],
) -> dict[str, RestaurantModel]:
    out = {}
    for seed in restaurant_seeds:
        result = await db.execute(
            select(RestaurantModel).where(RestaurantModel.kakao_id == seed.kakao_id)
        )
        restaurant = result.scalar_one_or_none()
        old_seed_restaurant = await db.get(RestaurantModel, seed.id)
        if restaurant is None:
            restaurant = old_seed_restaurant
        elif old_seed_restaurant is not None and old_seed_restaurant.id != restaurant.id:
            old_seed_restaurant.deleted_at = utcnow()
            db.add(old_seed_restaurant)
        values = _restaurant_values(seed, restaurant_images[seed.id].thumbnail)
        if restaurant is None:
            restaurant = RestaurantModel(**values)
        else:
            for key, value in values.items():
                if key != "id":
                    setattr(restaurant, key, value)
            restaurant.deleted_at = None
        db.add(restaurant)
        await db.flush()
        out[seed.id] = restaurant
    return out


async def _seed_media_objects(
    storage: StorageService,
    entries: Sequence[EntrySeed],
    restaurant_images: dict[str, RestaurantImages],
) -> None:
    for entry in entries:
        variants = restaurant_images[entry.restaurant_id].entries[entry.id].variants
        for variant, key in _media_keys(entry.media_id).items():
            await storage.put(key, variants[variant], content_type="image/jpeg")


async def _seed_media(
    db: AsyncSession,
    entries: Sequence[EntrySeed],
    users: dict[str, UserModel],
    restaurant_images: dict[str, RestaurantImages],
) -> dict[str, MediaModel]:
    out = {}
    for entry in entries:
        media_id = entry.media_id
        media = await db.get(MediaModel, media_id)
        keys = _media_keys(media_id)
        variants = restaurant_images[entry.restaurant_id].entries[entry.id].variants
        values = {
            "id": media_id,
            "user_id": users[entry.user_id].id,
            "storage_key": keys["original"],
            "url": None,
            "thumbnail_url": None,
            "width": _IMAGE_SIZES["original"][0],
            "height": _IMAGE_SIZES["original"][1],
            "bytes": len(variants["original"]),
            "tone": _restaurant_tone_for_entry(entry),
            "label": entry.ai_tags[0][:24] if entry.ai_tags else "demo meal",
            "variant_keys": {"thumb": keys["thumb"], "medium": keys["medium"]},
            "exif_captured_at": entry.captured_at,
            "exif_lat": None,
            "exif_lng": None,
            "deleted_at": None,
        }
        if media is None:
            media = MediaModel(**values)
        else:
            for key, value in values.items():
                setattr(media, key, value)
        db.add(media)
        await db.flush()
        out[entry.id] = media
    return out


async def _seed_entries(
    db: AsyncSession,
    entry_seeds: Sequence[EntrySeed],
    users: dict[str, UserModel],
    restaurants: dict[str, RestaurantModel],
    media: dict[str, MediaModel],
) -> dict[str, EntryModel]:
    out = {}
    for seed in entry_seeds:
        entry = await db.get(EntryModel, seed.id)
        values = {
            "id": seed.id,
            "user_id": users[seed.user_id].id,
            "draft_id": None,
            "restaurant_id": restaurants[seed.restaurant_id].id,
            "cover_media_id": media[seed.id].id,
            "captured_at": seed.captured_at,
            "meal_period": seed.meal_period,
            "rating": seed.rating,
            "note": seed.note,
            "ai_tags": list(seed.ai_tags),
            "deleted_at": None,
        }
        if entry is None:
            entry = EntryModel(**values)
        else:
            for key, value in values.items():
                setattr(entry, key, value)
        db.add(entry)
        await db.flush()
        out[seed.id] = entry
    return out


async def _seed_entry_media(
    db: AsyncSession,
    entries: dict[str, EntryModel],
    media: dict[str, MediaModel],
) -> None:
    for entry_id, entry in entries.items():
        await db.execute(delete(EntryMediaModel).where(EntryMediaModel.entry_id == entry.id))
        db.add(
            EntryMediaModel(
                entry_id=entry.id,
                media_id=media[entry_id].id,
                position=0,
                is_cover=True,
            )
        )


async def _seed_bookmarks(
    db: AsyncSession,
    user: UserModel,
    restaurants: dict[str, RestaurantModel],
    restaurant_seed_ids: Sequence[str],
) -> None:
    for seed_id in restaurant_seed_ids:
        restaurant = restaurants[seed_id]
        result = await db.execute(
            select(BookmarkModel).where(
                BookmarkModel.user_id == user.id,
                BookmarkModel.restaurant_id == restaurant.id,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(BookmarkModel(user_id=user.id, restaurant_id=restaurant.id))


async def _seed_algorithm_artifacts(
    db: AsyncSession,
    algorithm: AlgorithmService,
    seed: DemoSeedData,
    demo_user: UserModel,
    entries: dict[str, EntryModel],
    restaurants: dict[str, RestaurantModel],
    restaurant_images: dict[str, RestaurantImages],
) -> None:
    generated_at = utcnow()
    demo_inputs = []
    image_profiled_restaurant_ids: set[str] = set()
    for entry in seed.demo_entries:
        image_references = []
        if (
            entry.restaurant_id not in image_profiled_restaurant_ids
            and len(image_profiled_restaurant_ids) < _ALGORITHM_IMAGE_RESTAURANT_LIMIT
        ):
            image_profiled_restaurant_ids.add(entry.restaurant_id)
            image_references = [
                restaurant_images[entry.restaurant_id].entries[entry.id].source_url
            ]
        demo_inputs.append(
            algorithm.diary_entry_input_from_models(
                entries[entry.id],
                restaurants[entry.restaurant_id],
                image_references=image_references,
            )
        )
    artifacts = algorithm.build_taste_refresh_artifacts(
        demo_user.id,
        demo_inputs,
        generated_at=generated_at,
        min_entries_required=MIN_ENTRIES_FOR_PERSONALIZATION,
    )
    artifact_repo = AlgorithmArtifactRepository(db)
    for profile in artifacts.entry_profiles:
        payload = profile.model_dump(mode="json")
        await artifact_repo.add_entry_profile(
            entry_id=profile.entry_id,
            user_id=profile.user_id,
            payload_json=payload,
            algorithm_version=payload["algorithm_version"],
            generated_at=generated_at,
            commit=False,
        )
    if artifacts.user_profile is None:
        raise RuntimeError("demo seed did not create a user profile artifact")
    user_profile_payload = artifacts.user_profile.model_dump(mode="json")
    await artifact_repo.add_user_profile(
        user_id=demo_user.id,
        source_entry_count=artifacts.user_profile.source_entry_count,
        payload_json=user_profile_payload,
        long_term_embedding=user_profile_payload["long_term_embedding"],
        short_term_embedding=user_profile_payload["short_term_embedding"],
        algorithm_version=user_profile_payload["algorithm_version"],
        generated_at=generated_at,
        commit=False,
    )
    await db.execute(delete(TasteReportModel).where(TasteReportModel.user_id == demo_user.id))
    report_payload = artifacts.report.model_dump(mode="json")
    db.add(
        TasteReportModel(
            user_id=demo_user.id,
            payload_json=report_payload,
            has_enough_data=bool(artifacts.report.has_enough_data),
            source_entry_count=len(demo_inputs),
            algorithm_version=artifacts.report.algorithm_version,
            generated_at=generated_at,
        )
    )
    if artifacts.report.has_enough_data:
        label = report_payload.get("type", {}).get("label")
        if label:
            demo_user.taste_type = label
            db.add(demo_user)

    for restaurant_seed in seed.candidate_restaurants:
        restaurant = restaurants[restaurant_seed.id]
        await db.execute(
            delete(RestaurantProfileArtifactModel).where(
                RestaurantProfileArtifactModel.restaurant_id == restaurant.id
            )
        )
        profile = algorithm.build_restaurant_profile_artifact(restaurant, generated_at=generated_at)
        payload = profile.model_dump(mode="json")
        await artifact_repo.add_restaurant_profile(
            restaurant_id=restaurant.id,
            payload_json=payload,
            embedding=payload["embedding"],
            algorithm_version=payload["algorithm_version"],
            generated_at=generated_at,
            commit=False,
        )
    await db.commit()


async def _ensure_bucket(s3: aioboto3.Session) -> None:
    client = cast(Any, s3.client)(
        "s3",
        endpoint_url=Env.get(Env.S3_ENDPOINT),
        aws_access_key_id=Env.get(Env.S3_ACCESS_KEY),
        aws_secret_access_key=Env.get(Env.S3_SECRET_KEY),
        region_name=Env.get(Env.S3_REGION),
    )
    async with client as c:
        with contextlib.suppress(Exception):
            await c.create_bucket(Bucket=Env.get(Env.S3_BUCKET))


async def _restaurant_images(
    image_client: SeedImageClient,
    restaurants: Sequence[RestaurantSeed],
    entries: Sequence[EntrySeed],
) -> dict[str, RestaurantImages]:
    entries_by_restaurant_id = {restaurant.id: [] for restaurant in restaurants}
    for entry in entries:
        if entry.restaurant_id in entries_by_restaurant_id:
            entries_by_restaurant_id[entry.restaurant_id].append(entry)

    images = {}
    for restaurant in restaurants:
        restaurant_entries = entries_by_restaurant_id[restaurant.id]
        sources = await image_client.fetch_images(
            _restaurant_image_queries(restaurant),
            max(1, len(restaurant_entries)),
        )
        restaurant_images = [
            RestaurantImage(
                source_url=source.source_url,
                variants=image_variants_from_bytes(source.data),
            )
            for source in sources
        ]
        images[restaurant.id] = RestaurantImages(
            thumbnail=restaurant_images[0],
            entries={
                entry.id: restaurant_images[index]
                for index, entry in enumerate(restaurant_entries)
            },
        )
    return images


class KakaoImageClient:
    def __init__(self, http_client: httpx.AsyncClient, api_key: str) -> None:
        self.http = http_client
        self.api_key = api_key

    async def fetch_image(self, query: str) -> FetchedImage:
        return (await self.fetch_images([query], 1))[0]

    async def fetch_images(self, queries: Sequence[str], count: int) -> list[FetchedImage]:
        seen_urls = set()
        images = []
        for query in queries:
            response = await self.http.get(
                _KAKAO_IMAGE_SEARCH_URL,
                headers={"Authorization": f"KakaoAK {self.api_key}"},
                params={"query": query, "sort": "accuracy", "size": 50},
            )
            response.raise_for_status()
            for doc in response.json().get("documents", []):
                for url in (doc.get("image_url"), doc.get("thumbnail_url")):
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        try:
                            image_response = await self.http.get(url)
                            image_response.raise_for_status()
                            image_variants_from_bytes(image_response.content)
                            images.append(
                                FetchedImage(source_url=url, data=image_response.content)
                            )
                            if len(images) == count:
                                return images
                        except Exception:
                            continue
        raise RuntimeError(
            f"Kakao image search found only {len(images)} usable images "
            f"for {queries[0]!r}; need {count}."
        )


def _restaurant_image_queries(restaurant: RestaurantSeed) -> list[str]:
    return [
        f"{restaurant.image_query} {restaurant.signature_dish}",
        f"{restaurant.image_query} 음식",
        f"{restaurant.image_query} 메뉴",
        f"{restaurant.image_query} 후기",
        restaurant.image_query,
    ]


def image_variants_from_bytes(data: bytes) -> dict[str, bytes]:
    image = Image.open(BytesIO(data))
    image = _rgb_image(ImageOps.exif_transpose(image))
    variants = {}
    for name, size in _IMAGE_SIZES.items():
        output = BytesIO()
        ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).save(
            output,
            format="JPEG",
            quality=88,
            optimize=True,
        )
        variants[name] = output.getvalue()
    return variants


def _rgb_image(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def _image_data_url(data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _restaurant_values(seed: RestaurantSeed, image: RestaurantImage) -> dict[str, object]:
    return {
        "id": seed.id,
        "kakao_id": seed.kakao_id,
        "name": seed.name,
        "category": seed.category,
        "signature_dish": seed.signature_dish,
        "rating": seed.rating,
        "rating_count": seed.rating_count,
        "thumbnail_url": _image_data_url(image.variants["thumb"]),
        "thumbnail_tone": seed.thumbnail_tone,
        "thumbnail_label": seed.thumbnail_label,
        "tags": list(seed.tags),
        "lat": seed.lat,
        "lng": seed.lng,
        "neighborhood": seed.neighborhood,
        "address": seed.address,
        "price_range": None,
        "hours": None,
        "phone": None,
        "raw_payload": {
            "id": seed.kakao_id,
            "place_name": seed.name,
            "category_name": seed.category,
            "address_name": seed.address,
            "place_url": f"http://place.map.kakao.com/{seed.kakao_id}",
            "image_source_url": image.source_url,
        },
        "fetched_at": utcnow(),
        "deleted_at": None,
    }


def _media_keys(media_id: str) -> dict[str, str]:
    base = f"media/demo-seed/{media_id}"
    return {
        "original": f"{base}.jpg",
        "thumb": f"{base}-thumb.jpg",
        "medium": f"{base}-medium.jpg",
    }


def _restaurant_tone_for_entry(entry: EntrySeed) -> FoodTone:
    restaurant = demo_seed_data().restaurant_by_id()[entry.restaurant_id]
    return restaurant.thumbnail_tone


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _r(
    id: str,
    name: str,
    category: str,
    signature_dish: str,
    rating: float,
    rating_count: int,
    distance_m: int,
    tone: FoodTone,
    label: str,
    tags: tuple[str, ...],
    lat: float,
    lng: float,
    neighborhood: str,
    address: str,
    image_query: str,
    kakao_id: str,
) -> RestaurantSeed:
    return RestaurantSeed(
        id=id,
        kakao_id=kakao_id,
        name=name,
        category=category,
        signature_dish=signature_dish,
        rating=rating,
        rating_count=rating_count,
        distance_m=distance_m,
        thumbnail_tone=tone,
        thumbnail_label=label,
        tags=tags,
        lat=lat,
        lng=lng,
        neighborhood=neighborhood,
        address=address,
        image_query=image_query,
    )


def _e(
    id: str,
    user_id: str,
    restaurant_id: str,
    captured_at: str,
    meal_period: str,
    rating: float,
    note: str,
    ai_tags: tuple[str, ...],
) -> EntrySeed:
    return EntrySeed(
        id=id,
        user_id=user_id,
        restaurant_id=restaurant_id,
        captured_at=_dt(captured_at),
        meal_period=meal_period,
        rating=rating,
        note=note,
        ai_tags=ai_tags,
    )


# fmt: off
_VISITED_RESTAURANTS = tuple(_r(*row) for row in (
    ("r_seed_noodle_broth", "봉평옹심이메밀칼국수 유성구청점", "Noodles", "메밀칼국수", 4.6, 182, 950, FoodTone.BONE, "메밀칼국수", ("warm broth", "chewy noodles"), 36.3624833242943, 127.357479669607, "어은동", "대전 유성구 어은동 115-1", "봉평옹심이메밀칼국수 유성구청점", "23486703"),
    ("r_seed_soba", "궁손칼국수", "Noodles", "손칼국수", 4.4, 97, 880, FoodTone.BONE, "손칼국수", ("quick lunch", "light"), 36.36342931715781, 127.35695696927411, "어은동", "대전 유성구 어은동 110-1", "궁손칼국수", "25851699"),
    ("r_seed_bakery", "베이커리해끝", "Bakery", "소금빵", 4.8, 891, 1500, FoodTone.CREAM, "소금빵", ("buttery", "local favorite"), 36.3625553946621, 127.35141201218, "궁동", "대전 유성구 궁동 407-3", "베이커리해끝", "13406208"),
    ("r_seed_cafe", "은샘치아바타카페", "Cafe", "치아바타", 4.3, 210, 2500, FoodTone.CHAR, "치아바타", ("quiet", "study work"), 36.38859052983648, 127.34824112834363, "신성동", "대전 유성구 신성동 209-4", "은샘치아바타카페", "582446282"),
    ("r_seed_setmeal", "카이스트 본원 학생식당", "Diner / Set meal", "백반", 4.2, 144, 300, FoodTone.RUST, "학생식당", ("quick lunch", "comfort"), 36.3738863201192, 127.359430726946, "구성동", "대전 유성구 구성동 23", "카이스트 본원 학생식당", "996644954"),
    ("r_seed_bbq", "화통", "Korean BBQ", "삼겹살", 4.7, 312, 900, FoodTone.PAPRIKA, "삼겹살", ("smoky", "group dinner"), 36.3633350603017, 127.357135928354, "어은동", "대전 유성구 어은동 110-2", "화통 어은동", "23826739"),
    ("r_seed_comfort_stew", "사계절두부사랑 죽동본점", "Comfort Korean", "순두부", 4.5, 188, 2700, FoodTone.RUST, "순두부", ("savory", "comfort"), 36.370681282629, 127.337978580256, "죽동", "대전 유성구 죽동 716-3", "사계절두부사랑 죽동본점", "1166267459"),
    ("r_seed_dumpling", "더큰식탁 카이스트점", "Snacks", "분식", 4.3, 88, 250, FoodTone.OCHRE, "분식", ("snack", "spicy"), 36.373654839412985, 127.35939065912356, "구성동", "대전 유성구 구성동 23", "더큰식탁 카이스트점", "732207276"),
))

_CANDIDATE_RESTAURANTS = tuple(_r(*row) for row in (
    ("r_seed_candidate_noodle", "소담칼국수쭈꾸미 어은점", "Noodles", "칼국수", 4.9, 228, 820, FoodTone.BONE, "칼국수", ("warm broth", "chewy noodles"), 36.3631355489631, 127.357855915778, "어은동", "대전 유성구 어은동 113-15", "소담칼국수쭈꾸미 어은점", "992007017"),
    ("r_seed_candidate_udon", "안골칼국수", "Noodles", "칼국수", 4.7, 144, 850, FoodTone.BONE, "칼국수", ("handmade noodles", "savory"), 36.36364061556, 127.357418109348, "어은동", "대전 유성구 어은동 111-2", "안골칼국수", "21336920"),
    ("r_seed_candidate_bakery", "오픈오븐", "Bakery", "베이커리", 4.8, 431, 2600, FoodTone.CREAM, "베이커리", ("buttery", "breakfast"), 36.352707886663, 127.373807330348, "갈마동", "대전 서구 갈마동 844", "오픈오븐 대전", "877961063"),
    ("r_seed_candidate_cafe", "루키식탁 & 루키카페", "Cafe", "브런치", 4.5, 198, 2300, FoodTone.CHAR, "브런치", ("quiet", "study work"), 36.3722199863032, 127.340060152592, "죽동", "대전 유성구 죽동 720-8", "루키식탁 루키카페", "125505352"),
    ("r_seed_candidate_setmeal", "별리달리 카이스트", "Diner / Set meal", "한식", 4.4, 155, 280, FoodTone.RUST, "한식", ("quick lunch", "comfort"), 36.37365129529478, 127.35907081922086, "구성동", "대전 유성구 구성동 23", "별리달리 카이스트", "1286820465"),
    ("r_seed_candidate_bbq", "본전고깃골", "Korean BBQ", "삼겹살", 4.6, 289, 900, FoodTone.PAPRIKA, "삼겹살", ("smoky", "group dinner"), 36.3632088044466, 127.357166549572, "어은동", "대전 유성구 어은동 110-3", "본전고깃골 어은동", "14751473"),
    ("r_seed_candidate_japanese", "역전우동0410 대전카이스트점", "Japanese", "우동", 4.2, 174, 350, FoodTone.BUTTER, "우동", ("rice bowl", "quick"), 36.37307346452151, 127.36002874163714, "구성동", "대전 유성구 구성동 23", "역전우동0410 대전카이스트점", "616563112"),
    ("r_seed_candidate_chinese", "웰차이", "Chinese", "짜장면", 4.4, 260, 300, FoodTone.RUST, "짜장면", ("spicy", "rich"), 36.3738882018781, 127.359703756574, "구성동", "대전 유성구 구성동 23", "웰차이 카이스트", "625543528"),
    ("r_seed_candidate_dessert", "성심당오븐스토리", "Dessert", "케이크", 4.6, 122, 4300, FoodTone.BERRY, "케이크", ("sweet", "date"), 36.34083988478328, 127.38973617836369, "괴정동", "대전 서구 괴정동 423-1", "성심당오븐스토리 롯데백화점 대전점", "1361222593"),
    ("r_seed_candidate_western", "롤링파스타 대전카이스트점", "Western", "파스타", 4.1, 98, 300, FoodTone.TERRA, "파스타", ("casual", "fresh"), 36.3738767115569, 127.359629040803, "구성동", "대전 유성구 구성동 23", "롤링파스타 대전카이스트점", "313823832"),
    ("r_seed_candidate_korean", "왕비성", "Korean", "짬뽕", 4.3, 202, 850, FoodTone.MOSS, "짬뽕", ("savory", "set meal"), 36.3633031146449, 127.358174235824, "어은동", "대전 유성구 어은동 113-12", "왕비성 어은동", "10618024"),
    ("r_seed_candidate_snack", "뿅떡 신성점", "Snacks", "떡볶이", 4.2, 156, 2500, FoodTone.OCHRE, "떡볶이", ("spicy", "snack"), 36.38759610966981, 127.35023734184107, "신성동", "대전 유성구 신성동 210-19", "뿅떡 신성점", "592375127"),
    ("r_seed_candidate_bar", "더랜치펍", "Bar", "펍 메뉴", 4.2, 135, 1500, FoodTone.CHAR, "펍 메뉴", ("late night", "group"), 36.3626827538857, 127.352230416261, "궁동", "대전 유성구 궁동 404-5", "더랜치펍 궁동", "26561770"),
    ("r_seed_candidate_comfort", "형제돌구이", "Comfort Korean", "김치찌개", 4.5, 190, 850, FoodTone.RUST, "김치찌개", ("comfort", "spicy"), 36.3632227698246, 127.358521504036, "어은동", "대전 유성구 어은동 114-7", "형제돌구이", "10107854"),
))

_DEMO_ENTRIES = tuple(_e(*row) for row in (
    ("e_seed_demo_01", DEMO_USER_ID, "r_seed_noodle_broth", "2026-05-24T12:43:00Z", "lunch", 4.5, "Clear savory broth, chewy noodles, and a light seafood finish.", ("noodle", "soup")),
    ("e_seed_demo_02", DEMO_USER_ID, "r_seed_noodle_broth", "2026-05-22T12:10:00Z", "lunch", 5.0, "Best when the broth is hot, simple, and satisfying.", ("noodle", "broth")),
    ("e_seed_demo_03", DEMO_USER_ID, "r_seed_noodle_broth", "2026-05-20T18:45:00Z", "dinner", 4.0, "Still satisfying for dinner after lab, especially the chewy noodles.", ("noodle",)),
    ("e_seed_demo_04", DEMO_USER_ID, "r_seed_soba", "2026-05-18T12:20:00Z", "lunch", 4.5, "Clean dipping sauce, springy noodles, and a light lunch pace.", ("soba", "noodle")),
    ("e_seed_demo_05", DEMO_USER_ID, "r_seed_bakery", "2026-05-15T09:20:00Z", "breakfast", 5.0, "Crisp outside, soft inside, buttery but not too sweet.", ("bread", "pastry")),
    ("e_seed_demo_06", DEMO_USER_ID, "r_seed_bakery", "2026-05-12T09:10:00Z", "breakfast", 4.5, "Good breakfast when I want something buttery and reliable.", ("bread",)),
    ("e_seed_demo_07", DEMO_USER_ID, "r_seed_cafe", "2026-05-10T15:30:00Z", "afternoon", 4.0, "Quiet enough to study and the latte is steady.", ("latte", "coffee")),
    ("e_seed_demo_08", DEMO_USER_ID, "r_seed_cafe", "2026-05-08T16:00:00Z", "afternoon", 4.0, "Reliable afternoon work stop with a creamy latte.", ("coffee",)),
    ("e_seed_demo_09", DEMO_USER_ID, "r_seed_setmeal", "2026-05-06T12:35:00Z", "lunch", 4.0, "Fast comfort lunch with savory stew and enough side dishes.", ("stew",)),
    ("e_seed_demo_10", DEMO_USER_ID, "r_seed_bbq", "2026-05-05T19:10:00Z", "dinner", 4.5, "Tender smoky meat, balanced sauce, and a good group dinner.", ("bbq", "grilled meat")),
    ("e_seed_demo_11", DEMO_USER_ID, "r_seed_comfort_stew", "2026-05-03T18:40:00Z", "dinner", 4.5, "Savory comfort stew when I am craving something warm.", ("stew", "korean")),
    ("e_seed_demo_12", DEMO_USER_ID, "r_seed_dumpling", "2026-05-01T20:30:00Z", "dinner", 4.0, "Spicy dumplings made a quick casual snack dinner.", ("dumpling", "snack")),
))

_PEER_ENTRIES = tuple(_e(*row) for row in (
    ("e_seed_peer_01_01", "u_demo_peer_01", "r_seed_candidate_noodle", "2026-05-24T12:00:00Z", "lunch", 5.0, "Savory broth and chewy noodles were excellent.", ("noodle",)),
    ("e_seed_peer_01_02", "u_demo_peer_01", "r_seed_noodle_broth", "2026-05-22T12:00:00Z", "lunch", 4.5, "Reliable noodle lunch.", ("noodle",)),
    ("e_seed_peer_01_03", "u_demo_peer_01", "r_seed_candidate_bakery", "2026-05-20T09:00:00Z", "breakfast", 4.5, "Buttery roll and quick breakfast.", ("bread",)),
    ("e_seed_peer_01_04", "u_demo_peer_01", "r_seed_bakery", "2026-05-18T09:00:00Z", "breakfast", 4.5, "Crisp pastry.", ("pastry",)),
    ("e_seed_peer_01_05", "u_demo_peer_01", "r_seed_candidate_cafe", "2026-05-16T15:00:00Z", "afternoon", 4.0, "Quiet study cafe.", ("coffee",)),
    ("e_seed_peer_01_06", "u_demo_peer_01", "r_seed_cafe", "2026-05-14T15:00:00Z", "afternoon", 4.0, "Reliable latte.", ("latte",)),
    ("e_seed_peer_01_07", "u_demo_peer_01", "r_seed_candidate_bbq", "2026-05-12T19:00:00Z", "dinner", 4.5, "Smoky group dinner.", ("bbq",)),
    ("e_seed_peer_01_08", "u_demo_peer_01", "r_seed_setmeal", "2026-05-10T12:00:00Z", "lunch", 4.0, "Quick set meal.", ("stew",)),
    ("e_seed_peer_01_09", "u_demo_peer_01", "r_seed_candidate_setmeal", "2026-05-08T12:00:00Z", "lunch", 4.0, "Comfort stew set.", ("stew",)),
    ("e_seed_peer_01_10", "u_demo_peer_01", "r_seed_dumpling", "2026-05-06T20:00:00Z", "dinner", 4.0, "Spicy snack.", ("snack",)),
    ("e_seed_peer_02_01", "u_demo_peer_02", "r_seed_candidate_udon", "2026-05-24T12:30:00Z", "lunch", 4.5, "Savory handmade noodles.", ("noodle",)),
    ("e_seed_peer_02_02", "u_demo_peer_02", "r_seed_candidate_noodle", "2026-05-22T12:30:00Z", "lunch", 5.0, "Warm broth and chewy noodles.", ("noodle",)),
    ("e_seed_peer_02_03", "u_demo_peer_02", "r_seed_noodle_broth", "2026-05-20T18:30:00Z", "dinner", 4.5, "Simple satisfying noodles.", ("noodle",)),
    ("e_seed_peer_02_04", "u_demo_peer_02", "r_seed_bakery", "2026-05-18T09:30:00Z", "breakfast", 4.5, "Buttery local bread.", ("bread",)),
    ("e_seed_peer_02_05", "u_demo_peer_02", "r_seed_candidate_bakery", "2026-05-16T09:30:00Z", "breakfast", 4.5, "Crisp butter roll.", ("bread",)),
    ("e_seed_peer_02_06", "u_demo_peer_02", "r_seed_cafe", "2026-05-14T16:00:00Z", "afternoon", 4.0, "Quiet work table.", ("coffee",)),
    ("e_seed_peer_02_07", "u_demo_peer_02", "r_seed_candidate_cafe", "2026-05-12T16:00:00Z", "afternoon", 4.0, "Steady latte.", ("latte",)),
    ("e_seed_peer_02_08", "u_demo_peer_02", "r_seed_bbq", "2026-05-10T19:00:00Z", "dinner", 4.5, "Smoky meat.", ("bbq",)),
    ("e_seed_peer_02_09", "u_demo_peer_02", "r_seed_candidate_comfort", "2026-05-08T18:30:00Z", "dinner", 4.5, "Warm comfort stew.", ("stew",)),
    ("e_seed_peer_02_10", "u_demo_peer_02", "r_seed_setmeal", "2026-05-06T12:15:00Z", "lunch", 4.0, "Quick lunch set.", ("stew",)),
    ("e_seed_peer_03_01", "u_demo_peer_03", "r_seed_candidate_noodle", "2026-05-23T12:15:00Z", "lunch", 4.5, "Clean savory noodle soup.", ("noodle",)),
    ("e_seed_peer_03_02", "u_demo_peer_03", "r_seed_soba", "2026-05-21T12:15:00Z", "lunch", 4.5, "Light soba lunch.", ("soba",)),
    ("e_seed_peer_03_03", "u_demo_peer_03", "r_seed_noodle_broth", "2026-05-19T18:15:00Z", "dinner", 4.5, "Warm noodle dinner.", ("noodle",)),
    ("e_seed_peer_03_04", "u_demo_peer_03", "r_seed_candidate_bakery", "2026-05-17T09:15:00Z", "breakfast", 4.5, "Buttery breakfast bread.", ("bread",)),
    ("e_seed_peer_03_05", "u_demo_peer_03", "r_seed_bakery", "2026-05-15T09:15:00Z", "breakfast", 5.0, "Excellent streusel bun.", ("bread",)),
    ("e_seed_peer_03_06", "u_demo_peer_03", "r_seed_candidate_cafe", "2026-05-13T15:15:00Z", "afternoon", 4.0, "Quiet cafe for work.", ("coffee",)),
    ("e_seed_peer_03_07", "u_demo_peer_03", "r_seed_cafe", "2026-05-11T15:15:00Z", "afternoon", 4.0, "Reliable latte.", ("latte",)),
    ("e_seed_peer_03_08", "u_demo_peer_03", "r_seed_candidate_bbq", "2026-05-09T19:15:00Z", "dinner", 4.5, "Good smoky BBQ.", ("bbq",)),
    ("e_seed_peer_03_09", "u_demo_peer_03", "r_seed_comfort_stew", "2026-05-07T18:15:00Z", "dinner", 4.5, "Savory comfort stew.", ("stew",)),
    ("e_seed_peer_03_10", "u_demo_peer_03", "r_seed_candidate_setmeal", "2026-05-05T12:15:00Z", "lunch", 4.0, "Fast stew set.", ("stew",)),
))
# fmt: on

if __name__ == "__main__":
    asyncio.run(main())
