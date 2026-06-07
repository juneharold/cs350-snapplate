from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.services.algorithm.providers import DeterministicProvider
from app.services.algorithm.service import AlgorithmService
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
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, stmt):  # noqa: ARG002
        return _FakeResult(self.rows)


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows
