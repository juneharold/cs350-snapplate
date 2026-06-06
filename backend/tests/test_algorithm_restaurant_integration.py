from datetime import UTC, datetime, timedelta

from algorithm.config import EMBEDDING_DIMENSIONS
from algorithm.providers import DeterministicProvider

from app.models.algorithm_artifact import RestaurantProfileArtifactModel
from app.models.restaurant import RestaurantModel
from app.types.restaurant import FoodTone

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)


def _restaurant() -> RestaurantModel:
    return RestaurantModel(
        id="r_profile",
        kakao_id="k_profile",
        name="Noodle House",
        category="Noodles",
        signature_dish="Clam noodle soup",
        rating=4.6,
        rating_count=120,
        thumbnail_url="https://place.map.kakao.com/k_profile",
        thumbnail_tone=FoodTone.BONE,
        thumbnail_label="Noodle House",
        tags=["quick lunch"],
        lat=36.3504,
        lng=127.3845,
        neighborhood="Eoeun-dong",
        address="Eoeun-dong",
        phone="042-000-0000",
        raw_payload={"category_name": "음식점 > 한식 > 국수"},
    )


def test_metadata_from_restaurant_model_uses_public_category() -> None:
    from app.services.algorithm.restaurants import metadata_from_restaurant_model

    metadata = metadata_from_restaurant_model(_restaurant())

    assert metadata.id == "r_profile"
    assert metadata.category_name == "Noodles"
    assert metadata.address_name == "Eoeun-dong"


def test_build_restaurant_profile_artifact() -> None:
    from app.services.algorithm.restaurants import build_restaurant_profile_artifact

    profile = build_restaurant_profile_artifact(
        _restaurant(),
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
    )

    assert profile.restaurant_id == "r_profile"
    assert profile.profile["food_type"]["noodle"] > 0
    assert profile.embedding


async def test_profile_restaurants_skips_fresh_existing_profiles(monkeypatch) -> None:
    from app.services.algorithm import restaurants as restaurant_module

    fresh = _restaurant()
    fresh.id = "r_fresh"
    stale = _restaurant()
    stale.id = "r_stale"
    provider = _CountingProvider()
    restaurant_repo = _FakeRestaurantRepository({"r_fresh": fresh, "r_stale": stale})
    artifact_repo = _FakeArtifactRepository(
        {
            "r_fresh": RestaurantProfileArtifactModel(
                restaurant_id="r_fresh",
                payload_json={"restaurant_id": "r_fresh", "embedding": [0.1]},
                embedding=[0.1] * EMBEDDING_DIMENSIONS,
                algorithm_version="alg-old",
                generated_at=NOW - timedelta(minutes=10),
            ),
            "r_stale": RestaurantProfileArtifactModel(
                restaurant_id="r_stale",
                payload_json={"restaurant_id": "r_stale", "embedding": [0.1]},
                embedding=[0.1] * EMBEDDING_DIMENSIONS,
                algorithm_version="alg-old",
                generated_at=NOW - timedelta(hours=2),
            ),
        }
    )
    db = _CommitOnlyDb()
    internal = _FakeInternal(db, provider)

    monkeypatch.setattr(restaurant_module, "utcnow", lambda: NOW)
    monkeypatch.setattr(
        restaurant_module,
        "RestaurantRepository",
        lambda db_session: restaurant_repo,  # noqa: ARG005
    )
    monkeypatch.setattr(
        restaurant_module,
        "AlgorithmArtifactRepository",
        lambda db_session: artifact_repo,  # noqa: ARG005
        raising=False,
    )

    await restaurant_module.profile_restaurants(internal, ["r_fresh", "r_stale", "r_fresh"])

    assert artifact_repo.requested_ids == ["r_fresh", "r_stale"]
    assert len(provider.embedded_texts) == 1
    assert artifact_repo.added_restaurant_ids == ["r_stale"]
    assert db.commits == 1


class _CountingProvider:
    def __init__(self):
        self.embedded_texts = []

    def embed_text(self, text: str) -> list[float]:
        self.embedded_texts.append(text)
        return [0.1] * EMBEDDING_DIMENSIONS


class _FakeRestaurantRepository:
    def __init__(self, rows: dict[str, RestaurantModel]):
        self.rows = rows

    async def find(self, restaurant_id: str) -> RestaurantModel | None:
        return self.rows.get(restaurant_id)


class _FakeArtifactRepository:
    def __init__(self, existing: dict[str, RestaurantProfileArtifactModel]):
        self.existing = existing
        self.requested_ids = []
        self.added_restaurant_ids = []

    async def latest_restaurant_profiles(
        self, restaurant_ids: list[str]
    ) -> dict[str, RestaurantProfileArtifactModel]:
        self.requested_ids = restaurant_ids
        return self.existing

    async def add_restaurant_profile(self, **kwargs):
        self.added_restaurant_ids.append(kwargs["restaurant_id"])


class _CommitOnlyDb:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class _FakeSessionContext:
    def __init__(self, db: _CommitOnlyDb):
        self.db = db

    async def __aenter__(self) -> _CommitOnlyDb:
        return self.db

    async def __aexit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        return None


class _FakeSessionmaker:
    def __init__(self, db: _CommitOnlyDb):
        self.db = db

    def __call__(self) -> _FakeSessionContext:
        return _FakeSessionContext(self.db)


class _FakeInternal:
    def __init__(self, db: _CommitOnlyDb, profile_provider: _CountingProvider):
        self.db_sessionmaker = _FakeSessionmaker(db)
        self.profile_provider = profile_provider
