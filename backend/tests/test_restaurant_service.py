from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.config.algorithm import EMBEDDING_DIMENSIONS
from app.models.algorithm_artifact import RestaurantProfileArtifactModel
from app.models.restaurant import RestaurantModel
from app.services.main import restaurant as restaurant_module
from app.services.main.restaurant import RestaurantService
from app.types.restaurant import FoodTone

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)


async def test_schedule_profile_refresh_skips_when_all_restaurant_profiles_are_fresh(
    monkeypatch,
) -> None:
    artifacts = _FakeArtifactRepository(
        {
            "r_fresh": _profile("r_fresh", generated_at=NOW - timedelta(minutes=10)),
        }
    )
    background_tasks = _RecordingBackgroundTasks()
    service = _service(monkeypatch, artifacts, background_tasks)

    await service._schedule_profile_refresh([_restaurant("r_fresh")])

    assert artifacts.requested_ids == ["r_fresh"]
    assert background_tasks.calls == []


async def test_schedule_profile_refresh_schedules_only_missing_or_stale_profiles(
    monkeypatch,
) -> None:
    artifacts = _FakeArtifactRepository(
        {
            "r_fresh": _profile("r_fresh", generated_at=NOW - timedelta(minutes=10)),
            "r_stale": _profile("r_stale", generated_at=NOW - timedelta(hours=2)),
        }
    )
    background_tasks = _RecordingBackgroundTasks()
    service = _service(monkeypatch, artifacts, background_tasks)

    await service._schedule_profile_refresh(
        [_restaurant("r_fresh"), _restaurant("r_stale"), _restaurant("r_missing")]
    )

    assert artifacts.requested_ids == ["r_fresh", "r_stale", "r_missing"]
    assert background_tasks.calls == [
        (
            service.internal.algorithm_service.profile_restaurants,
            service.internal,
            ["r_stale", "r_missing"],
        )
    ]


def _service(monkeypatch, artifacts, background_tasks) -> RestaurantService:
    monkeypatch.setattr(restaurant_module, "utcnow", lambda: NOW)
    monkeypatch.setattr(
        restaurant_module,
        "AlgorithmArtifactRepository",
        lambda db_session: artifacts,  # noqa: ARG005
    )
    return RestaurantService(
        SimpleNamespace(db_session=object(), http_client=object()),
        background_tasks=background_tasks,
        internal=SimpleNamespace(algorithm_service=_FakeAlgorithmService()),
    )


def _restaurant(restaurant_id: str) -> RestaurantModel:
    return RestaurantModel(
        id=restaurant_id,
        kakao_id=f"k_{restaurant_id}",
        name=f"Restaurant {restaurant_id}",
        category="Noodles",
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
        raw_payload={"category_name": "음식점 > 한식 > 국수"},
    )


def _profile(restaurant_id: str, *, generated_at: datetime) -> RestaurantProfileArtifactModel:
    return RestaurantProfileArtifactModel(
        restaurant_id=restaurant_id,
        payload_json={"restaurant_id": restaurant_id, "embedding": [0.1] * EMBEDDING_DIMENSIONS},
        embedding=[0.1] * EMBEDDING_DIMENSIONS,
        algorithm_version="alg-v1",
        generated_at=generated_at,
    )


class _FakeArtifactRepository:
    def __init__(self, existing: dict[str, RestaurantProfileArtifactModel]):
        self.existing = existing
        self.requested_ids = []

    async def latest_restaurant_profiles(
        self, restaurant_ids: list[str]
    ) -> dict[str, RestaurantProfileArtifactModel]:
        self.requested_ids = restaurant_ids
        return self.existing


class _RecordingBackgroundTasks:
    def __init__(self):
        self.calls = []

    def add_task(self, fn, *args):
        self.calls.append((fn, *args))


class _FakeAlgorithmService:
    async def profile_restaurants(self, *args, **kwargs):  # noqa: ARG002
        raise AssertionError("background task should only be recorded")
