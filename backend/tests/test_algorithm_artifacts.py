from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.config.algorithm import EMBEDDING_DIMENSIONS


def test_algorithm_artifact_models_store_payload_and_version() -> None:
    from app.models.algorithm_artifact import (
        EntryProfileArtifactModel,
        RestaurantProfileArtifactModel,
        UserProfileArtifactModel,
    )

    generated_at = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)
    entry = EntryProfileArtifactModel(
        entry_id="e_1",
        user_id="u_1",
        payload_json={"entry_id": "e_1", "taste": {"spicy": 0.8}},
        algorithm_version="alg-test",
        generated_at=generated_at,
    )
    user = UserProfileArtifactModel(
        user_id="u_1",
        source_entry_count=10,
        payload_json={"user_id": "u_1", "long_term_embedding": [0.1]},
        long_term_embedding=[0.1] * EMBEDDING_DIMENSIONS,
        short_term_embedding=[0.2] * EMBEDDING_DIMENSIONS,
        algorithm_version="alg-test",
        generated_at=generated_at,
    )
    restaurant = RestaurantProfileArtifactModel(
        restaurant_id="r_1",
        payload_json={"restaurant_id": "r_1", "embedding": [0.1]},
        embedding=[0.1] * EMBEDDING_DIMENSIONS,
        algorithm_version="alg-test",
        generated_at=generated_at,
    )

    assert entry.payload_json["entry_id"] == "e_1"
    assert user.source_entry_count == 10
    assert restaurant.algorithm_version == "alg-test"


def test_algorithm_artifact_models_declare_vector_columns_and_unique_constraints() -> None:
    from app.models.algorithm_artifact import (
        EntryProfileArtifactModel,
        RestaurantProfileArtifactModel,
        UserProfileArtifactModel,
    )

    assert UserProfileArtifactModel.__table__.c.long_term_embedding.type.dim == EMBEDDING_DIMENSIONS
    assert (
        UserProfileArtifactModel.__table__.c.short_term_embedding.type.dim == EMBEDDING_DIMENSIONS
    )
    assert RestaurantProfileArtifactModel.__table__.c.embedding.type.dim == EMBEDDING_DIMENSIONS

    assert _unique_columns(EntryProfileArtifactModel) == {("entry_id",)}
    assert _unique_columns(UserProfileArtifactModel) == {("user_id",)}
    assert _unique_columns(RestaurantProfileArtifactModel) == {("restaurant_id",)}


async def test_nearest_restaurant_profiles_orders_by_cosine_distance() -> None:
    from app.repositories.algorithm_artifact import AlgorithmArtifactRepository

    db = _CapturingDb(rows=[("artifact", 0.125)])
    repo = AlgorithmArtifactRepository(db)

    rows = await repo.nearest_restaurant_profiles(
        [0.1] * EMBEDDING_DIMENSIONS,
        candidate_restaurant_ids=["r_1", "r_2"],
        limit=5,
    )

    assert rows == [("artifact", 0.125)]
    sql = str(db.statements[0].compile(dialect=postgresql.dialect()))
    assert "restaurant_profile_artifacts.embedding <=>" in sql
    assert "restaurant_profile_artifacts.restaurant_id IN" in sql
    assert "ORDER BY distance ASC" in sql
    assert "LIMIT" in sql


def _unique_columns(model) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.columns.keys())
        for constraint in model.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }


class _CapturingDb:
    def __init__(self, *, rows):
        self.rows = rows
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _RowsResult(self.rows)


class _RowsResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows
