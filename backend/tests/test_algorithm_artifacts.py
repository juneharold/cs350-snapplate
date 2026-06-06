from datetime import UTC, datetime


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
        algorithm_version="alg-test",
        generated_at=generated_at,
    )
    restaurant = RestaurantProfileArtifactModel(
        restaurant_id="r_1",
        payload_json={"restaurant_id": "r_1", "embedding": [0.1]},
        algorithm_version="alg-test",
        generated_at=generated_at,
    )

    assert entry.payload_json["entry_id"] == "e_1"
    assert user.source_entry_count == 10
    assert restaurant.algorithm_version == "alg-test"
