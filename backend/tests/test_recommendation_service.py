from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config.http_errors import AppError
from app.dto.restaurant import RecommendedResponseCore
from app.models.recommendation_exposure import RecommendationExposureModel
from app.models.restaurant import RestaurantModel
from app.services.algorithm.providers import DeterministicProvider
from app.services.algorithm.service import AlgorithmService
from app.services.main import recommendation as recommendation_module
from app.services.main.recommendation import RecommendationService
from app.types.restaurant import FoodTone


async def test_recommend_returns_plain_data_for_unauthenticated_user() -> None:
    service = RecommendationService(
        SimpleNamespace(db_session=object(), algorithm_service=_FakeAlgorithmService())
    )

    result = await service.recommend(None, None, None, 10)

    assert result == {"items": [], "based_on_entries": 0, "has_enough_data": False}
    assert not isinstance(result, RecommendedResponseCore)


async def test_recommend_returns_plain_data_for_insufficient_entries(monkeypatch) -> None:
    artifacts = _FakeArtifactRepository(user_profile=None)
    algorithm = _install_service_fakes(
        monkeypatch,
        artifacts=artifacts,
        exposures=_FakeExposureRepository(),
        entries=[object() for _ in range(3)],
        candidates=[],
    )

    result = await RecommendationService(
        SimpleNamespace(db_session=object(), algorithm_service=algorithm)
    ).recommend("u_short_history", None, None, 10)

    assert result == {"items": [], "based_on_entries": 3, "has_enough_data": False}
    assert artifacts.nearest_calls == []


async def test_recommend_uses_nearest_restaurant_profiles(monkeypatch) -> None:
    user_profile = SimpleNamespace(
        payload_json={"user_id": "u_ready"},
        long_term_embedding=[0.1, 0.2, 0.3],
    )
    restaurant_profile = SimpleNamespace(
        restaurant_id="r_nearest",
        payload_json={"restaurant_id": "r_nearest"},
    )
    artifacts = _FakeArtifactRepository(
        user_profile=user_profile,
        nearest_rows=[(restaurant_profile, 0.1)],
        fail_latest=True,
    )
    exposures = _FakeExposureRepository()
    captured_context: dict[str, object] = {}

    algorithm = _install_service_fakes(
        monkeypatch,
        artifacts=artifacts,
        exposures=exposures,
        entries=[object() for _ in range(10)],
        candidates=[SimpleNamespace(id="r_far"), SimpleNamespace(id="r_nearest")],
        captured_context=captured_context,
    )

    result = await RecommendationService(
        SimpleNamespace(db_session=object(), algorithm_service=algorithm)
    ).recommend("u_ready", 36.3504, 127.3845, 3)

    assert result["items"][0]["id"] == "r_nearest"
    assert artifacts.nearest_calls == [
        {
            "query_embedding": [0.1, 0.2, 0.3],
            "candidate_restaurant_ids": ["r_far", "r_nearest"],
            "limit": 15,
        }
    ]
    assert artifacts.latest_calls == []
    assert captured_context["candidate_restaurants"] == [SimpleNamespace(id="r_nearest")]
    assert captured_context["restaurant_profile_payloads"] == [{"restaurant_id": "r_nearest"}]
    assert exposures.added == [{"r_nearest": "Taste match"}]


async def test_recommend_missing_user_profile_has_distinct_error(monkeypatch) -> None:
    artifacts = _FakeArtifactRepository(user_profile=None)
    algorithm = _install_service_fakes(
        monkeypatch,
        artifacts=artifacts,
        exposures=_FakeExposureRepository(),
        entries=[object() for _ in range(10)],
        candidates=[],
    )

    with pytest.raises(AppError) as exc_info:
        await RecommendationService(
            SimpleNamespace(db_session=object(), algorithm_service=algorithm)
        ).recommend("u_missing_profile", None, None, 10)

    assert exc_info.value.status == 412
    assert exc_info.value.code == "user_profile_not_ready"


async def test_recommend_missing_restaurant_profiles_has_distinct_error(monkeypatch) -> None:
    user_profile = SimpleNamespace(
        payload_json={"user_id": "u_ready"},
        long_term_embedding=[0.1, 0.2, 0.3],
    )
    artifacts = _FakeArtifactRepository(user_profile=user_profile, nearest_rows=[])
    algorithm = _install_service_fakes(
        monkeypatch,
        artifacts=artifacts,
        exposures=_FakeExposureRepository(),
        entries=[object() for _ in range(10)],
        candidates=[SimpleNamespace(id="r_without_profile")],
    )

    with pytest.raises(AppError) as exc_info:
        await RecommendationService(
            SimpleNamespace(db_session=object(), algorithm_service=algorithm)
        ).recommend("u_ready", None, None, 10)

    assert exc_info.value.status == 503
    assert exc_info.value.code == "restaurant_profiles_not_ready"


async def test_candidates_skip_unmappable_restaurant_categories(monkeypatch) -> None:
    restaurants = _FakeCandidateRestaurantRepository(
        [
            _restaurant_model("r_unknown", "퓨전음식", "음식점 > 퓨전음식"),
            _restaurant_model("r_valid", "국수", "음식점 > 한식 > 국수"),
        ]
    )
    bookmarks = _FakeCandidateBookmarkRepository({"r_valid"})
    monkeypatch.setattr(
        recommendation_module,
        "RestaurantRepository",
        lambda db_session: restaurants,  # noqa: ARG005
    )
    monkeypatch.setattr(
        recommendation_module,
        "BookmarkRepository",
        lambda db_session: bookmarks,  # noqa: ARG005
    )
    service = RecommendationService(
        SimpleNamespace(
            db_session=object(),
            algorithm_service=AlgorithmService(DeterministicProvider()),
        )
    )

    result = await service._candidates([], "u_1", None, None)

    assert [candidate.id for candidate in result] == ["r_valid"]
    assert result[0].category == "Noodles"
    assert result[0].is_bookmarked is True


def test_recommendation_exposure_declares_shown_at_index() -> None:
    indexed_columns = {
        tuple(index.columns.keys()) for index in RecommendationExposureModel.__table__.indexes
    }

    assert ("shown_at",) in indexed_columns


def _install_service_fakes(
    monkeypatch,
    *,
    artifacts,
    exposures,
    entries,
    candidates,
    captured_context: dict[str, object] | None = None,
) -> _FakeAlgorithmService:
    diary_service = _FakeDiaryInputService(entries)
    algorithm = _FakeAlgorithmService(captured_context=captured_context)

    async def fake_candidates(self, entries, user_id, lat, lng):  # noqa: ARG001
        return candidates

    monkeypatch.setattr(
        recommendation_module,
        "DiaryInputService",
        lambda ctx: diary_service,  # noqa: ARG005
    )
    monkeypatch.setattr(
        recommendation_module,
        "AlgorithmArtifactRepository",
        lambda db_session: artifacts,  # noqa: ARG005
    )
    monkeypatch.setattr(
        recommendation_module,
        "BookmarkRepository",
        lambda db_session: object(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        recommendation_module,
        "RestaurantRepository",
        lambda db_session: object(),  # noqa: ARG005
    )
    monkeypatch.setattr(
        recommendation_module,
        "RecommendationExposureRepository",
        lambda db_session: exposures,  # noqa: ARG005
    )
    monkeypatch.setattr(RecommendationService, "_candidates", fake_candidates)
    return algorithm


class _FakeDiaryInputService:
    def __init__(self, entries):
        self.entries = entries

    async def for_user(self, user_id):  # noqa: ARG002
        return self.entries

    async def for_peers(self, user_id):  # noqa: ARG002
        return []


class _FakeArtifactRepository:
    def __init__(
        self,
        *,
        user_profile,
        nearest_rows=None,
        latest_profiles=None,
        fail_latest=False,
    ):
        self.user_profile = user_profile
        self.nearest_rows = nearest_rows or []
        self.latest_profiles = latest_profiles or {}
        self.fail_latest = fail_latest
        self.nearest_calls = []
        self.latest_calls = []

    async def latest_user_profile(self, user_id):  # noqa: ARG002
        return self.user_profile

    async def nearest_restaurant_profiles(
        self,
        query_embedding,
        *,
        candidate_restaurant_ids,
        limit,
    ):
        self.nearest_calls.append(
            {
                "query_embedding": query_embedding,
                "candidate_restaurant_ids": list(candidate_restaurant_ids),
                "limit": limit,
            }
        )
        return self.nearest_rows

    async def latest_restaurant_profiles(self, restaurant_ids):
        if self.fail_latest:
            raise AssertionError("latest_restaurant_profiles should not be used")
        self.latest_calls.append(list(restaurant_ids))
        return self.latest_profiles


class _FakeExposureRepository:
    def __init__(self):
        self.added = []

    async def latest_restaurant_ids(self, user_id, limit):  # noqa: ARG002
        return []

    async def add_many(self, *, user_id, restaurant_reasons, shown_at):  # noqa: ARG002
        self.added.append(restaurant_reasons)


class _FakeRecommendationResult:
    items = [SimpleNamespace(id="r_nearest", reason="Taste match")]
    based_on_entries = 10
    has_enough_data = True

    def model_dump(self, *, mode):  # noqa: ARG002
        return {
            "items": [
                {
                    "id": "r_nearest",
                    "name": "Nearest",
                    "category": "Korean",
                    "signature_dish": None,
                    "rating": 4.5,
                    "rating_count": 12,
                    "distance_m": 120,
                    "thumbnail_url": None,
                    "thumbnail_tone": "bone",
                    "thumbnail_label": "Nearest",
                    "tags": [],
                    "lat": 36.3504,
                    "lng": 127.3845,
                    "kakao_id": "k_nearest",
                    "neighborhood": "Eoeun-dong",
                    "is_bookmarked": False,
                    "reason": "Taste match",
                }
            ],
            "based_on_entries": self.based_on_entries,
            "has_enough_data": self.has_enough_data,
        }


class _FakeAlgorithmService:
    def __init__(self, *, captured_context: dict[str, object] | None = None):
        self.captured_context = captured_context

    def build_recommendation_context(self, **kwargs):
        if self.captured_context is not None:
            self.captured_context.update(kwargs)
        return SimpleNamespace()

    def generate_recommendations(self, *args, **kwargs):  # noqa: ARG002
        return _FakeRecommendationResult()


def _restaurant_model(restaurant_id: str, category: str, raw_path: str) -> RestaurantModel:
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


class _FakeCandidateRestaurantRepository:
    def __init__(self, rows):
        self.rows = rows

    async def list_active(self, category, min_rating, limit):  # noqa: ARG002
        return self.rows


class _FakeCandidateBookmarkRepository:
    def __init__(self, restaurant_ids: set[str]):
        self.restaurant_ids = restaurant_ids

    async def bookmarked_restaurant_ids(self, user_id):  # noqa: ARG002
        return self.restaurant_ids
