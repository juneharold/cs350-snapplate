from datetime import datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from algorithm import generate_recommendations, generate_taste_report
from algorithm.schemas import (
    DiaryEntryInput,
    EntryProfileArtifact,
    RecommendationContext,
    RecommendedResponse,
    RestaurantInput,
    TasteProfileInsufficient,
    TasteProfileReady,
    TasteProfileResponse,
)


NOW = datetime(2026, 5, 24, 12, 43, tzinfo=timezone.utc)
USER_ID = "u_contract"


def restaurant(
    restaurant_id: str,
    category: str,
    *,
    name: str | None = None,
    signature_dish: str | None = None,
    rating: float = 4.5,
    distance_m: int = 400,
) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant_id,
        name=name or f"{category} Place {restaurant_id}",
        category=category,
        signature_dish=signature_dish,
        rating=rating,
        rating_count=120,
        distance_m=distance_m,
        thumbnail_url=None,
        thumbnail_tone="bone",
        thumbnail_label=signature_dish or category.lower(),
        tags=[],
        lat=36.371,
        lng=127.361,
        kakao_id=f"kakao_{restaurant_id}",
        neighborhood="Eoeun-dong",
        is_bookmarked=False,
    )


def entry(
    index: int,
    restaurant_input: RestaurantInput,
    *,
    rating: float = 4.0,
) -> DiaryEntryInput:
    return DiaryEntryInput(
        id=f"e_{index}",
        user_id=USER_ID,
        captured_at=NOW - timedelta(days=index),
        restaurant=restaurant_input,
        rating=rating,
        note=f"Entry {index} at {restaurant_input.name}",
    )


def enough_entries() -> list[DiaryEntryInput]:
    noodles = restaurant("noodles", "Noodles", signature_dish="Clam noodle soup", rating=4.6)
    cafe = restaurant("cafe", "Cafe", signature_dish="Acorn latte", rating=4.3)
    bakery = restaurant("bakery", "Bakery", signature_dish="Fried streusel bun", rating=4.8)
    restaurants = [noodles, noodles, noodles, noodles, cafe, cafe, cafe, bakery, bakery, bakery]
    ratings = [4.5, 4.0, 5.0, 4.5, 3.5, 4.0, 4.0, 5.0, 4.5, 4.5]
    return [entry(i, r, rating=ratings[i]) for i, r in enumerate(restaurants)]


def test_taste_report_matches_frontend_profile_payload() -> None:
    report = generate_taste_report(USER_ID, enough_entries(), generated_at=NOW)

    assert isinstance(report, TasteProfileReady)
    payload = report.model_dump(mode="json")
    TypeAdapter(TasteProfileResponse).validate_python(payload)

    assert set(payload) == {
        "has_enough_data",
        "min_entries_required",
        "current_entries",
        "computed_at",
        "type",
        "summary",
        "categories",
        "time_heatmap",
        "flavor_lean",
        "top_dishes",
        "insights",
    }
    assert payload["has_enough_data"] is True
    assert payload["min_entries_required"] == 10
    assert payload["current_entries"] == 10
    assert payload["computed_at"] == "2026-05-24T12:43:00Z"
    assert set(payload["summary"]) == {
        "avg_rating",
        "avg_rating_delta_month",
        "places_count",
        "new_places_month",
        "top_day_of_week",
    }
    assert payload["summary"]["avg_rating"] == 4.4
    assert payload["categories"][0] == {
        "name": "Noodles",
        "weight": 1.0,
        "visits": 4,
        "tone": "bone",
    }
    assert payload["time_heatmap"]["rows"] == ["8 AM", "12 PM", "3 PM", "7 PM", "10 PM"]
    assert payload["time_heatmap"]["cols"] == ["M", "T", "W", "T", "F", "S", "S"]
    assert len(payload["time_heatmap"]["data"]) == 5
    assert all(len(row) == 7 for row in payload["time_heatmap"]["data"])
    assert set(payload["flavor_lean"]) == {"umami", "sweet", "salty", "sour", "spicy", "bitter"}
    assert payload["top_dishes"][0]["name"] == "Clam noodle soup"
    assert payload["insights"]


def test_taste_report_insufficient_data_shape_is_minimal() -> None:
    report = generate_taste_report(USER_ID, enough_entries()[:3], generated_at=NOW)

    assert isinstance(report, TasteProfileInsufficient)
    assert report.model_dump(mode="json") == {
        "has_enough_data": False,
        "min_entries_required": 10,
        "current_entries": 3,
    }


def test_recommendations_match_frontend_payload_and_hide_internal_scores() -> None:
    history = enough_entries()
    candidates = [
        restaurant("new_noodles", "Noodles", name="New Noodle Bar", rating=4.9, distance_m=300),
        restaurant("new_bakery", "Bakery", name="New Bakery", rating=4.8, distance_m=500),
        restaurant("new_chinese", "Chinese", name="New Chinese House", rating=4.6, distance_m=250),
    ]
    context = RecommendationContext(
        diary_entries=history,
        candidate_restaurants=candidates,
        lat=36.371,
        lng=127.361,
        exposure_history=["new_bakery"],
    )

    response = generate_recommendations(USER_ID, context, limit=2)
    payload = response.model_dump(mode="json")

    assert isinstance(response, RecommendedResponse)
    assert payload["has_enough_data"] is True
    assert payload["based_on_entries"] == 10
    assert len(payload["items"]) == 2
    assert payload["items"][0]["id"] == "new_noodles"
    assert "reason" in payload["items"][0]
    assert "score" not in payload["items"][0]
    assert "scores" not in payload["items"][0]
    assert set(payload["items"][0]) == {
        "id",
        "name",
        "category",
        "signature_dish",
        "rating",
        "rating_count",
        "distance_m",
        "thumbnail_url",
        "thumbnail_tone",
        "thumbnail_label",
        "tags",
        "lat",
        "lng",
        "kakao_id",
        "neighborhood",
        "is_bookmarked",
        "reason",
    }


def test_internal_entry_profile_artifact_requires_confidence_and_evidence() -> None:
    artifact = EntryProfileArtifact(
        entry_id="e_1",
        user_id=USER_ID,
        captured_at=NOW,
        rating=4.5,
        taste={"spicy": 0.7},
        confidence={"taste": 0.8},
        evidence={"taste": ["note: spicy but balanced"]},
    )

    assert artifact.taste == {"spicy": 0.7}
    assert artifact.confidence["taste"] == 0.8
    assert artifact.evidence["taste"] == ["note: spicy but balanced"]

    with pytest.raises(ValidationError):
        EntryProfileArtifact(
            entry_id="e_bad",
            user_id=USER_ID,
            captured_at=NOW,
            rating=4.0,
            taste={"savory": 0.6},
            confidence={"taste": 0.7},
            evidence={},
        )
