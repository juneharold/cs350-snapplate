from collections import Counter

from algorithm import generate_recommendations, generate_taste_report
from algorithm.fixtures import (
    load_synthetic_fixture_set,
    synthetic_recommendation_context_for_user,
)
from algorithm.schemas import RecommendationContext, SyntheticFixtureSet, TasteProfileReady


def test_synthetic_fixture_set_is_deterministic_and_complete() -> None:
    first = load_synthetic_fixture_set()
    second = load_synthetic_fixture_set()

    assert isinstance(first, SyntheticFixtureSet)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.is_synthetic is True
    assert first.generated_at.tzinfo is not None

    user_ids = {user.id for user in first.users}
    restaurant_ids = {restaurant.id for restaurant in first.restaurants}
    entry_counts = Counter(entry.user_id for entry in first.diary_entries)

    assert len(user_ids) == len(first.users)
    assert len(user_ids) >= 4
    assert len(first.restaurants) >= 8
    assert len(first.diary_entries) >= 24
    assert all(count >= 5 for count in entry_counts.values())
    assert set(entry_counts) == user_ids
    assert all(entry.rating is not None for entry in first.diary_entries)
    assert all(entry.captured_at.tzinfo is not None for entry in first.diary_entries)
    assert all(entry.restaurant.id in restaurant_ids for entry in first.diary_entries)
    assert any(entry.image_labels for entry in first.diary_entries)
    assert set(first.exposure_history) == user_ids
    assert all(first.exposure_history[user_id] for user_id in user_ids)
    assert all(
        restaurant_id in restaurant_ids
        for exposure in first.exposure_history.values()
        for restaurant_id in exposure
    )

    categories_by_user = {
        user.id: {
            entry.restaurant.category
            for entry in first.diary_entries
            if entry.user_id == user.id
        }
        for user in first.users
    }
    assert all(len(categories) >= 2 for categories in categories_by_user.values())
    assert any(
        left_categories & right_categories
        for left_user, left_categories in categories_by_user.items()
        for right_user, right_categories in categories_by_user.items()
        if left_user < right_user
    )


def test_synthetic_contexts_drive_outputs_and_novelty_checks() -> None:
    fixtures = load_synthetic_fixture_set()
    user_id = fixtures.users[0].id
    context = synthetic_recommendation_context_for_user(user_id)

    assert isinstance(context, RecommendationContext)
    assert context.exposure_history == fixtures.exposure_history[user_id]
    assert {entry.user_id for entry in context.diary_entries} == {user_id}
    assert len(context.candidate_restaurants) >= 4

    report = generate_taste_report(
        user_id,
        context.diary_entries,
        min_entries_required=len(context.diary_entries),
        generated_at=fixtures.generated_at,
    )
    recommendations = generate_recommendations(
        user_id,
        context,
        limit=3,
        min_entries_required=len(context.diary_entries),
    )

    assert isinstance(report, TasteProfileReady)
    assert report.current_entries == len(context.diary_entries)
    assert recommendations.has_enough_data is True
    assert recommendations.based_on_entries == len(context.diary_entries)
    assert len(recommendations.items) == 3
    assert all(
        item.id not in {entry.restaurant.id for entry in context.diary_entries}
        for item in recommendations.items
    )
    assert all("score" not in item.model_dump() for item in recommendations.items)
