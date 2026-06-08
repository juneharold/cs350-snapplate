from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image
from scripts import seed_demo_data

from app.config.algorithm import MIN_ENTRIES_FOR_PERSONALIZATION
from app.models.restaurant import RestaurantModel
from app.services.algorithm import generate_recommendations


class _ExistingRestaurantDb:
    def __init__(
        self,
        seed_restaurant: RestaurantModel | None,
        kakao_restaurant: RestaurantModel | None = None,
    ) -> None:
        self.seed_restaurant = seed_restaurant
        self.kakao_restaurant = kakao_restaurant
        self.added: list[RestaurantModel] = []
        self.executed = False
        self.flushed = False

    async def get(self, model: type[RestaurantModel], restaurant_id: str) -> RestaurantModel | None:
        assert model is RestaurantModel
        if self.seed_restaurant is not None and restaurant_id == self.seed_restaurant.id:
            return self.seed_restaurant
        return None

    async def execute(self, stmt: object) -> _ScalarResult:
        self.executed = True
        return _ScalarResult(self.kakao_restaurant)

    def add(self, restaurant: RestaurantModel) -> None:
        self.added.append(restaurant)

    async def flush(self) -> None:
        self.flushed = True


class _ScalarResult:
    def __init__(self, restaurant: RestaurantModel | None) -> None:
        self.restaurant = restaurant

    def scalar_one_or_none(self) -> RestaurantModel | None:
        return self.restaurant


def test_demo_seed_data_is_algorithm_demo_ready() -> None:
    data = seed_demo_data.demo_seed_data()

    assert data.demo_email == "demo@snapplate.app"
    assert len(data.demo_entries) >= MIN_ENTRIES_FOR_PERSONALIZATION
    assert len(data.candidate_restaurants) >= 10

    visited = {entry.restaurant.id for entry in data.demo_diary_inputs()}
    candidates = {restaurant.id for restaurant in data.candidate_restaurant_inputs()}
    assert visited.isdisjoint(candidates)

    peer_entries_by_user = {}
    for entry in data.peer_diary_inputs():
        peer_entries_by_user.setdefault(entry.user_id, []).append(entry)
    assert len(peer_entries_by_user) >= 3
    assert all(
        len(entries) >= MIN_ENTRIES_FOR_PERSONALIZATION for entries in peer_entries_by_user.values()
    )


def test_demo_seed_restaurants_reference_real_kakao_places() -> None:
    data = seed_demo_data.demo_seed_data()

    assert all(restaurant.kakao_id.isdecimal() for restaurant in data.restaurants)
    assert all(restaurant.image_query for restaurant in data.restaurants)


def test_image_variants_are_resized_from_source_photo() -> None:
    source = BytesIO()
    Image.new("RGB", (1200, 900), (180, 80, 40)).save(source, format="JPEG")

    variants = seed_demo_data.image_variants_from_bytes(source.getvalue())

    assert set(variants) == {"original", "medium", "thumb"}
    assert len(variants["original"]) > len(variants["medium"]) > len(variants["thumb"])
    for key, expected_size in {
        "original": (960, 720),
        "medium": (640, 480),
        "thumb": (320, 240),
    }.items():
        assert variants[key].startswith(b"\xff\xd8")
        image = Image.open(BytesIO(variants[key]))
        assert image.size == expected_size
        assert image.format == "JPEG"


async def test_seed_restaurants_update_existing_seed_id_when_kakao_id_changed() -> None:
    source = BytesIO()
    Image.new("RGB", (1200, 900), (180, 80, 40)).save(source, format="JPEG")
    seed = seed_demo_data.demo_seed_data().visited_restaurants[0]
    existing = RestaurantModel(
        id=seed.id,
        kakao_id="old-fake-kakao-id",
        name="Old fake name",
        category="Noodles",
        signature_dish=None,
        rating=0.0,
        rating_count=0,
        lat=seed.lat,
        lng=seed.lng,
        neighborhood=seed.neighborhood,
        address=seed.address,
    )
    db = _ExistingRestaurantDb(existing)

    result = await seed_demo_data._seed_restaurants(
        db,
        [seed],
        {
            seed.id: seed_demo_data.RestaurantImage(
                source_url="https://example.com/source.jpg",
                variants=seed_demo_data.image_variants_from_bytes(source.getvalue()),
            )
        },
    )

    assert db.executed is True
    assert db.flushed is True
    assert result[seed.id] is existing
    assert existing.kakao_id == seed.kakao_id
    assert existing.name == seed.name


async def test_seed_restaurants_prefer_existing_kakao_row_over_stale_seed_id() -> None:
    source = BytesIO()
    Image.new("RGB", (1200, 900), (180, 80, 40)).save(source, format="JPEG")
    seed = seed_demo_data.demo_seed_data().visited_restaurants[0]
    stale = RestaurantModel(
        id=seed.id,
        kakao_id="old-fake-kakao-id",
        name="Old fake name",
        category="Noodles",
        signature_dish=None,
        rating=0.0,
        rating_count=0,
        lat=seed.lat,
        lng=seed.lng,
        neighborhood=seed.neighborhood,
        address=seed.address,
    )
    canonical = RestaurantModel(
        id="existing-real-kakao-row",
        kakao_id=seed.kakao_id,
        name="Existing Kakao name",
        category="Noodles",
        signature_dish=None,
        rating=0.0,
        rating_count=0,
        lat=seed.lat,
        lng=seed.lng,
        neighborhood=seed.neighborhood,
        address=seed.address,
    )
    db = _ExistingRestaurantDb(stale, canonical)

    result = await seed_demo_data._seed_restaurants(
        db,
        [seed],
        {
            seed.id: seed_demo_data.RestaurantImage(
                source_url="https://example.com/source.jpg",
                variants=seed_demo_data.image_variants_from_bytes(source.getvalue()),
            )
        },
    )

    assert result[seed.id] is canonical
    assert canonical.id == "existing-real-kakao-row"
    assert canonical.name == seed.name
    assert stale.deleted_at is not None
    assert stale in db.added


def test_demo_seed_data_drives_collaborative_recommendations() -> None:
    data = seed_demo_data.demo_seed_data()
    context = data.recommendation_context()

    response = generate_recommendations(data.demo_user_id, context, limit=5)

    assert response.has_enough_data is True
    assert response.based_on_entries >= MIN_ENTRIES_FOR_PERSONALIZATION
    assert len(response.items) >= 5
    assert any("Similar users" in item.reason for item in response.items)


def test_seed_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        seed_demo_data.require_openai_api_key()


def test_seed_requires_kakao_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="KAKAO_REST_API_KEY"):
        seed_demo_data.require_kakao_api_key()
