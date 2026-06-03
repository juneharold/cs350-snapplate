from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

import pytest

from algorithm import (
    aggregate_user_profile,
    generate_recommendation_artifact,
    generate_recommendations,
    generate_taste_report,
    profile_diary_entry,
    profile_kakao_restaurant,
)
from algorithm.config import EMBEDDING_DIMENSIONS, MIN_SIMILAR_USERS
from algorithm.providers import DeterministicMLProvider
from algorithm.schemas import (
    DiaryEntryInput,
    KakaoRestaurantMetadata,
    RecommendationContext,
    RestaurantProfileArtifact,
    RestaurantInput,
    UserProfileArtifact,
)


NOW = datetime(2026, 5, 24, 12, 43, tzinfo=timezone.utc)
USER_ID = "u_eval"


def test_evaluation_threshold_gates_taste_and_recommendations() -> None:
    entries = [
        entry(index, USER_ID, restaurant(f"r_history_{index}", "Noodles"))
        for index in range(3)
    ]
    context = RecommendationContext(
        diary_entries=entries,
        candidate_restaurants=[restaurant("r_candidate", "Noodles")],
    )

    report = generate_taste_report(
        USER_ID,
        entries,
        min_entries_required=len(entries) + 1,
        generated_at=NOW,
        ml_provider=DeterministicMLProvider(),
    )
    recommendations = generate_recommendations(
        USER_ID,
        context,
        min_entries_required=len(entries) + 1,
    )

    assert report.has_enough_data is False
    assert report.current_entries == len(entries)
    assert recommendations.has_enough_data is False
    assert recommendations.based_on_entries == len(entries)
    assert recommendations.items == []


def test_evaluation_profiles_keep_evidence_for_observed_signals() -> None:
    profiled_entry = entry(
        1,
        USER_ID,
        restaurant(
            "r_profiled",
            "Korean BBQ",
            signature_dish="Marinated short rib",
        ),
        note="Spicy, savory, smoky, and satisfying.",
        image_labels=["korean grilled meat"],
    )
    entry_profile = profile_diary_entry(
        profiled_entry,
        ml_provider=DeterministicMLProvider(),
    )
    user_profile = aggregate_user_profile(
        USER_ID,
        [profiled_entry],
        generated_at=NOW,
        ml_provider=DeterministicMLProvider(),
    )
    restaurant_profile = profile_kakao_restaurant(
        KakaoRestaurantMetadata(
            id="kakao_profiled",
            place_name="Bonga BBQ",
            category_name="Food > Korean BBQ",
            road_address_name="Eoeun-dong 99",
            signature_dish="Marinated short rib",
            tags=["smoky grill", "reserve ahead"],
        ),
        generated_at=NOW,
        ml_provider=DeterministicMLProvider(),
    )

    assert_profile_fields_have_evidence(entry_profile.model_dump(), field_names=ENTRY_FIELDS)
    assert_profile_fields_have_evidence(
        {
            "profile": user_profile.long_term_profile,
            "confidence": user_profile.confidence,
            "evidence": user_profile.evidence,
        },
        field_names=user_profile.long_term_profile,
    )
    assert_profile_fields_have_evidence(
        {
            "profile": restaurant_profile.profile,
            "confidence": restaurant_profile.confidence,
            "evidence": restaurant_profile.evidence,
        },
        field_names=restaurant_profile.profile,
    )


def test_evaluation_client_recommendations_do_not_leak_scores() -> None:
    entries = history_entries(USER_ID, "Noodles", count=10)
    context = RecommendationContext(
        diary_entries=entries,
        candidate_restaurants=[
            restaurant("r_noodles", "Noodles"),
            restaurant("r_bakery", "Bakery"),
        ],
    )

    response = generate_recommendations(USER_ID, context, limit=2)
    payload = response.model_dump(mode="json")

    assert response.has_enough_data is True
    assert response.items
    assert_no_score_keys(payload)


def test_evaluation_recommendation_artifact_keeps_internal_score_breakdown() -> None:
    entries = history_entries(USER_ID, "Noodles", count=10)
    candidate = restaurant("r_noodles", "Noodles")
    context = RecommendationContext(
        diary_entries=entries,
        candidate_restaurants=[candidate],
    )

    artifact = generate_recommendation_artifact(USER_ID, context, limit=1, generated_at=NOW)
    response = generate_recommendations(USER_ID, context, limit=1)

    assert artifact.has_enough_data is True
    assert artifact.generated_at == NOW
    assert artifact.ranked_items[0].restaurant_id == response.items[0].id
    assert artifact.ranked_items[0].reason == response.items[0].reason
    assert artifact.ranked_items[0].reason_category == "content"
    assert artifact.ranked_items[0].scores.content_score > 0
    assert artifact.ranked_items[0].scores.final_score > 0
    assert_no_score_keys(response.model_dump(mode="json"))


def test_evaluation_recommendation_artifact_uses_minimal_insufficient_data_shape() -> None:
    entries = history_entries(USER_ID, "Noodles", count=3)
    context = RecommendationContext(
        diary_entries=entries,
        candidate_restaurants=[restaurant("r_noodles", "Noodles")],
    )

    artifact = generate_recommendation_artifact(
        USER_ID,
        context,
        min_entries_required=len(entries) + 1,
        generated_at=NOW,
    )

    assert artifact.has_enough_data is False
    assert artifact.based_on_entries == len(entries)
    assert artifact.ranked_items == []


def test_evaluation_similar_users_boost_restaurants_the_peer_group_likes() -> None:
    peer_pick = restaurant("r_peer_pick", "Noodles", name="Z Similar Pick")
    plain_pick = restaurant("r_plain_pick", "Noodles", name="A Plain Pick")
    active_entries = history_entries(USER_ID, "Noodles", count=10)
    peer_entries = similar_peer_entries(peer_pick)
    context = RecommendationContext(
        diary_entries=active_entries,
        peer_diary_entries=peer_entries,
        candidate_restaurants=[plain_pick, peer_pick],
    )

    response = generate_recommendations(USER_ID, context, limit=2)
    artifact = generate_recommendation_artifact(USER_ID, context, limit=2, generated_at=NOW)

    assert response.items[0].id == peer_pick.id
    assert "similar" in response.items[0].reason.lower()
    assert artifact.ranked_items[0].reason_category == "collaborative"


def test_evaluation_repeated_exposure_penalty_prioritizes_fresh_equivalent_items() -> None:
    seen = restaurant("r_seen", "Noodles", name="A Seen Noodle")
    fresh = restaurant("r_fresh", "Noodles", name="Z Fresh Noodle")
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[seen, fresh],
        exposure_history=[seen.id],
    )

    response = generate_recommendations(USER_ID, context, limit=2)
    ranked_ids = [item.id for item in response.items]

    assert ranked_ids.index(fresh.id) < ranked_ids.index(seen.id)


def test_evaluation_exposure_cooldown_uses_only_recent_history_window() -> None:
    seen_recently = restaurant("r_recent", "Noodles", name="A Recent Noodle")
    seen_outside_window = restaurant("r_old", "Noodles", name="Z Old Noodle")
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[seen_recently, seen_outside_window],
        exposure_history=[
            seen_recently.id,
            *[f"r_padding_{index}" for index in range(20)],
            seen_outside_window.id,
        ],
    )

    artifact = generate_recommendation_artifact(USER_ID, context, limit=2, generated_at=NOW)
    scores = {item.restaurant_id: item.scores.novelty_score for item in artifact.ranked_items}

    assert scores[seen_recently.id] < scores[seen_outside_window.id]


def test_evaluation_category_diversity_keeps_one_category_from_crowding_out_feed() -> None:
    noodle_candidates = [
        restaurant(f"r_noodle_{index}", "Noodles", rating=4.9, distance_m=250 + index)
        for index in range(4)
    ]
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[
            *noodle_candidates,
            restaurant("r_bakery", "Bakery", rating=4.2, distance_m=1200),
        ],
    )

    response = generate_recommendations(USER_ID, context, limit=4)
    categories = [item.category for item in response.items]

    assert len(response.items) == 4
    assert len(set(categories)) > 1
    assert Counter(categories).most_common(1)[0][1] < len(categories)


def test_evaluation_diversity_reranking_penalizes_neighborhood_crowding() -> None:
    nearby_same_area = [
        restaurant(
            f"r_same_area_{index}",
            "Noodles",
            rating=4.9,
            distance_m=250 + index,
            neighborhood="Eoeun-dong",
        )
        for index in range(3)
    ]
    different_area = restaurant(
        "r_other_area",
        "Noodles",
        rating=4.5,
        distance_m=700,
        neighborhood="Gung-dong",
    )
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[*nearby_same_area, different_area],
    )

    response = generate_recommendations(USER_ID, context, limit=3)
    neighborhoods = [item.neighborhood for item in response.items]

    assert "Gung-dong" in neighborhoods


def test_evaluation_explanations_are_grounded_in_visible_signals() -> None:
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[
            restaurant("r_noodle", "Noodles", rating=4.8),
            restaurant("r_chinese", "Chinese", rating=4.7),
        ],
    )

    response = generate_recommendations(USER_ID, context, limit=2)
    reasons_by_category = {item.category: item.reason.lower() for item in response.items}

    assert "noodle" in reasons_by_category["Noodles"]
    assert any(
        signal in reasons_by_category["Chinese"]
        for signal in ("rated", "variety", "chinese")
    )
    assert all(reason.strip() for reason in reasons_by_category.values())


def test_evaluation_quality_signal_uses_metadata_beyond_rating() -> None:
    rich = restaurant(
        "r_rich",
        "Japanese",
        name="Metadata Rich",
        rating=4.5,
        rating_count=300,
        signature_dish="Tonkotsu ramen",
        thumbnail_url="https://img.example/ramen.jpg",
        tags=["menu", "popular"],
    )
    sparse = restaurant(
        "r_sparse",
        "Japanese",
        name="Metadata Sparse",
        rating=4.5,
        rating_count=3,
        signature_dish=None,
        thumbnail_url=None,
        tags=[],
    )
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[sparse, rich],
    )

    artifact = generate_recommendation_artifact(USER_ID, context, limit=2, generated_at=NOW)
    scores = {item.restaurant_id: item.scores.quality_score for item in artifact.ranked_items}

    assert response_ids(artifact) == [rich.id, sparse.id]
    assert scores[rich.id] > scores[sparse.id]
    assert artifact.ranked_items[0].reason_category == "quality"


def test_evaluation_low_signal_fresh_pick_gets_novelty_reason_category() -> None:
    fresh = restaurant(
        "r_fresh_variety",
        "Japanese",
        rating=3.0,
        rating_count=0,
        signature_dish=None,
        distance_m=5000,
    )
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[fresh],
    )

    artifact = generate_recommendation_artifact(USER_ID, context, limit=1, generated_at=NOW)

    assert artifact.ranked_items[0].reason_category == "novelty"
    assert "variety" in artifact.ranked_items[0].reason.lower()


def test_evaluation_context_signal_uses_time_and_filters() -> None:
    entries = [
        entry(
            index,
            USER_ID,
            restaurant(f"r_lunch_{index}", "Noodles"),
            days_ago=index,
        )
        for index in range(10)
    ]
    matching = restaurant(
        "r_matching",
        "Noodles",
        neighborhood="Eoeun-dong",
        distance_m=400,
    )
    filtered_out = restaurant(
        "r_filtered_out",
        "Bakery",
        neighborhood="Gung-dong",
        distance_m=2400,
    )
    context = RecommendationContext(
        diary_entries=entries,
        candidate_restaurants=[filtered_out, matching],
        requested_at=NOW.replace(hour=12),
        category_filters=["Noodles"],
        neighborhood_filters=["Eoeun-dong"],
        max_distance_m=1000,
    )

    artifact = generate_recommendation_artifact(USER_ID, context, limit=2, generated_at=NOW)
    scores = {item.restaurant_id: item.scores.context_score for item in artifact.ranked_items}

    assert response_ids(artifact)[0] == matching.id
    assert scores[matching.id] > scores[filtered_out.id]


def test_evaluation_embedding_content_score_beats_category_frequency_when_artifacts_exist() -> None:
    category_match = restaurant(
        "r_category_match",
        "Noodles",
        name="Category Match Noodles",
        rating=4.6,
        distance_m=400,
    )
    embedding_match = restaurant(
        "r_embedding_match",
        "Japanese",
        name="Embedding Match Ramen",
        rating=4.6,
        distance_m=400,
    )
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[category_match, embedding_match],
        user_profile=user_profile_artifact(
            long_term_embedding=embedding_axis(1.0),
            short_term_embedding=embedding_axis(1.0),
        ),
        restaurant_profiles=[
            restaurant_profile_artifact(category_match, embedding=embedding_axis(-1.0)),
            restaurant_profile_artifact(embedding_match, embedding=embedding_axis(1.0)),
        ],
    )

    response = generate_recommendations(USER_ID, context, limit=2)
    payload = response.model_dump(mode="json")

    assert response.items[0].id == embedding_match.id
    assert "taste profile" in response.items[0].reason.lower()
    assert_no_score_keys(payload)


def test_evaluation_non_artifact_recommendations_keep_category_content_score() -> None:
    category_match = restaurant(
        "r_category_match",
        "Noodles",
        name="Category Match Noodles",
        rating=4.6,
        distance_m=400,
    )
    variety_pick = restaurant(
        "r_variety_pick",
        "Japanese",
        name="Variety Ramen",
        rating=4.6,
        distance_m=400,
    )
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[variety_pick, category_match],
    )

    response = generate_recommendations(USER_ID, context, limit=2)

    assert response.items[0].id == category_match.id


def test_evaluation_artifact_mode_requires_user_profile() -> None:
    candidate = restaurant("r_candidate", "Noodles")
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[candidate],
        restaurant_profiles=[restaurant_profile_artifact(candidate, embedding=embedding_axis(1.0))],
    )

    with pytest.raises(ValueError, match="user_profile"):
        generate_recommendations(USER_ID, context, limit=1)


def test_evaluation_artifact_mode_requires_candidate_restaurant_profile() -> None:
    candidate = restaurant("r_candidate", "Noodles")
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[candidate],
        user_profile=user_profile_artifact(
            long_term_embedding=embedding_axis(1.0),
            short_term_embedding=embedding_axis(1.0),
        ),
        restaurant_profiles=[],
    )

    with pytest.raises(ValueError, match="restaurant profile"):
        generate_recommendations(USER_ID, context, limit=1)


def test_evaluation_artifact_mode_rejects_invalid_embedding_dimensions() -> None:
    candidate = restaurant("r_candidate", "Noodles")
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=[candidate],
        user_profile=user_profile_artifact(
            long_term_embedding=[1.0],
            short_term_embedding=embedding_axis(1.0),
        ),
        restaurant_profiles=[restaurant_profile_artifact(candidate, embedding=embedding_axis(1.0))],
    )

    with pytest.raises(ValueError, match="embedding"):
        generate_recommendations(USER_ID, context, limit=1)


def test_evaluation_recommendation_generation_stays_under_srs_latency_target() -> None:
    candidates = [
        restaurant(
            f"r_candidate_{index}",
            "Noodles" if index % 2 == 0 else "Bakery",
            rating=4.0 + (index % 10) / 10,
            distance_m=100 + index,
            neighborhood="Eoeun-dong" if index % 3 else "Gung-dong",
        )
        for index in range(500)
    ]
    context = RecommendationContext(
        diary_entries=history_entries(USER_ID, "Noodles", count=10),
        candidate_restaurants=candidates,
    )

    started_at = perf_counter()
    response = generate_recommendations(USER_ID, context, limit=10)
    elapsed = perf_counter() - started_at

    assert len(response.items) == 10
    assert elapsed < 3.0


ENTRY_FIELDS = (
    "cuisine",
    "food_type",
    "taste",
    "context",
    "venue",
    "emotion",
    "location_feature",
    "temporal_feature",
)


def restaurant(
    restaurant_id: str,
    category: str,
    *,
    name: str | None = None,
    signature_dish: str | None = "Signature dish",
    rating: float = 4.6,
    rating_count: int = 120,
    distance_m: int = 400,
    thumbnail_url: str | None = None,
    tags: list[str] | None = None,
    neighborhood: str = "Eoeun-dong",
) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant_id,
        name=name or f"{category} Place {restaurant_id}",
        category=category,
        signature_dish=signature_dish,
        rating=rating,
        rating_count=rating_count,
        distance_m=distance_m,
        thumbnail_url=thumbnail_url,
        thumbnail_tone="bone",
        thumbnail_label=signature_dish or category.lower(),
        tags=tags or [],
        lat=36.371,
        lng=127.361,
        kakao_id=f"kakao_{restaurant_id}",
        neighborhood=neighborhood,
        is_bookmarked=False,
    )


def entry(
    index: int,
    user_id: str,
    restaurant_input: RestaurantInput,
    *,
    rating: float = 4.5,
    note: str = "Reliable meal.",
    image_labels: list[str] | None = None,
    days_ago: int | None = None,
) -> DiaryEntryInput:
    return DiaryEntryInput(
        id=f"e_{user_id}_{index}",
        user_id=user_id,
        captured_at=NOW - timedelta(days=index if days_ago is None else days_ago),
        restaurant=restaurant_input,
        rating=rating,
        note=note,
        image_labels=image_labels or [],
    )


def history_entries(user_id: str, category: str, *, count: int) -> list[DiaryEntryInput]:
    return [
        entry(
            index,
            user_id,
            restaurant(f"r_{user_id}_{category}_{index}", category),
            rating=4.6,
            note=f"Reliable {category.lower()} meal.",
        )
        for index in range(count)
    ]


def similar_peer_entries(peer_pick: RestaurantInput) -> list[DiaryEntryInput]:
    rows: list[DiaryEntryInput] = []
    for peer_index in range(MIN_SIMILAR_USERS):
        user_id = f"u_peer_{peer_index}"
        rows.extend(history_entries(user_id, "Noodles", count=9))
        rows.append(
            entry(
                100 + peer_index,
                user_id,
                peer_pick,
                rating=5.0,
                note="Would recommend this noodle place.",
            )
        )
    return rows


def embedding_axis(value: float) -> list[float]:
    return [value, *([0.0] * (EMBEDDING_DIMENSIONS - 1))]


def user_profile_artifact(
    *,
    long_term_embedding: list[float],
    short_term_embedding: list[float],
) -> UserProfileArtifact:
    return UserProfileArtifact(
        user_id=USER_ID,
        generated_at=NOW,
        source_entry_count=10,
        long_term_profile={"taste": {"umami": 0.9}},
        short_term_profile={"taste": {"umami": 0.9}},
        confidence={"taste": 0.9},
        evidence={"taste": ["test: semantic taste profile"]},
        profile_text="User favors umami ramen-like meals.",
        long_term_embedding=long_term_embedding,
        short_term_embedding=short_term_embedding,
        category_rating_vector={"Noodles": 4.6},
    )


def restaurant_profile_artifact(
    restaurant_input: RestaurantInput,
    *,
    embedding: list[float],
) -> RestaurantProfileArtifact:
    return RestaurantProfileArtifact(
        restaurant_id=restaurant_input.id,
        generated_at=NOW,
        profile={"taste": {"umami": 0.9}},
        confidence={"taste": 0.9},
        evidence={"taste": ["test: candidate taste profile"]},
        profile_text=f"{restaurant_input.name} semantic profile.",
        embedding=embedding,
    )


def assert_profile_fields_have_evidence(
    payload: dict[str, Any],
    *,
    field_names: Any,
) -> None:
    values_by_field = payload.get("profile", payload)
    for field_name in field_names:
        if not values_by_field.get(field_name):
            continue
        assert payload["confidence"].get(field_name, 0) > 0
        assert payload["evidence"].get(field_name)


def assert_no_score_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in {"score", "scores"}
            assert not key.endswith("_score")
            assert_no_score_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_score_keys(child)


def response_ids(artifact: Any) -> list[str]:
    return [item.restaurant_id for item in artifact.ranked_items]
