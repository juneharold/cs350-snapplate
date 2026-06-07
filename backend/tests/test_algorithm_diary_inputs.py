from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.entry import EntryModel
from app.models.media import MediaModel
from app.models.restaurant import RestaurantModel
from app.services.algorithm.providers import DeterministicProvider
from app.services.algorithm.service import AlgorithmService
from app.services.main import diary_inputs as diary_inputs_module
from app.services.main.diary_inputs import DiaryInputService
from app.types.restaurant import FoodTone

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)


async def test_diary_inputs_skip_entries_with_unmappable_restaurant_category() -> None:
    valid = _entry("e_valid", "r_valid"), _restaurant(
        "r_valid",
        "국수",
        "음식점 > 한식 > 국수",
    )
    unknown = _entry("e_unknown", "r_unknown"), _restaurant(
        "r_unknown",
        "퓨전음식",
        "음식점 > 퓨전음식",
    )
    service = DiaryInputService(
        SimpleNamespace(
            db_session=_FakeDb([unknown, valid]),
            algorithm_service=AlgorithmService(DeterministicProvider()),
        )
    )

    result = await service.for_user("u_1")

    assert [entry.id for entry in result] == ["e_valid"]
    assert result[0].restaurant.category == "Noodles"


async def test_diary_inputs_include_cover_image_reference_when_requested(monkeypatch) -> None:
    media = MediaModel(
        id="m_1",
        user_id="u_1",
        storage_key="media/u_1/m_1.jpg",
        width=1080,
        height=720,
        bytes=12,
        variant_keys={"medium": "media/u_1/m_1-medium.jpg"},
    )
    storage = _FakeStorage()
    monkeypatch.setattr(
        diary_inputs_module,
        "StorageService",
        lambda s3: storage,  # noqa: ARG005
    )
    service = DiaryInputService(
        SimpleNamespace(
            db_session=_FakeDb(
                [(_entry("e_1", "r_1"), _restaurant("r_1", "국수", "음식점 > 한식 > 국수"))],
                media_rows=[media],
            ),
            s3=object(),
            algorithm_service=AlgorithmService(DeterministicProvider()),
        )
    )

    result = await service.for_user("u_1", include_image_references=True)

    assert result[0].image_references == ["data:image/jpeg;base64,YmluYXJ5LWpwZWc="]
    assert storage.keys == ["media/u_1/m_1-medium.jpg"]


def _entry(entry_id: str, restaurant_id: str) -> EntryModel:
    return EntryModel(
        id=entry_id,
        user_id="u_1",
        restaurant_id=restaurant_id,
        cover_media_id="m_1",
        captured_at=NOW,
        rating=4.5,
        note="good noodles",
        ai_tags=[],
    )


def _restaurant(restaurant_id: str, category: str, raw_path: str) -> RestaurantModel:
    return RestaurantModel(
        id=restaurant_id,
        kakao_id=f"k_{restaurant_id}",
        name=f"Restaurant {restaurant_id}",
        category=category,
        signature_dish="Signature",
        rating=4.2,
        rating_count=12,
        thumbnail_url=None,
        thumbnail_tone=FoodTone.BONE,
        thumbnail_label=restaurant_id,
        tags=[],
        lat=36.3504,
        lng=127.3845,
        neighborhood="Eoeun-dong",
        raw_payload={"category_name": raw_path},
    )


class _FakeDb:
    def __init__(self, rows, media_rows=None):
        self.rows = rows
        self.media_rows = media_rows or []
        self.calls = 0

    async def execute(self, stmt):  # noqa: ARG002
        self.calls += 1
        if self.calls == 1:
            return _FakeResult(self.rows)
        return _FakeScalarResult(self.media_rows)


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _FakeStorage:
    def __init__(self):
        self.keys = []

    async def get(self, key: str) -> bytes:
        self.keys.append(key)
        return b"binary-jpeg"
