from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.algorithm import EntryProfileArtifact, RestaurantInput, RestaurantProfileArtifact
from app.utils.restaurant_taxonomy import (
    FLAVOR_LEAN_FIELDS,
    INTERNAL_PROFILE_TAXONOMY,
    PUBLIC_RESTAURANT_CATEGORIES,
    UnknownRestaurantCategoryError,
    normalize_public_restaurant_category,
)

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)


def test_public_restaurant_categories_are_frozen_for_frontend_contract() -> None:
    assert PUBLIC_RESTAURANT_CATEGORIES == (
        "Korean",
        "Korean BBQ",
        "Noodles",
        "Diner / Set meal",
        "Comfort Korean",
        "Cafe",
        "Bakery",
        "Snacks",
        "Chinese",
        "Japanese",
        "Western",
        "Bar",
        "Dessert",
    )


def test_flavor_lean_fields_are_frozen_for_taste_radar() -> None:
    assert FLAVOR_LEAN_FIELDS == (
        "umami",
        "sweet",
        "salty",
        "sour",
        "spicy",
        "bitter",
    )


def test_internal_profile_taxonomy_is_frozen() -> None:
    assert INTERNAL_PROFILE_TAXONOMY == {
        "cuisine": (
            "korean",
            "japanese",
            "chinese",
            "western",
            "italian",
            "asian_fusion",
            "cafe_bakery",
        ),
        "food_type": (
            "noodle",
            "rice_bowl",
            "soup",
            "stew",
            "bbq",
            "fried",
            "set_meal",
            "bread",
            "pastry",
            "coffee",
            "dessert",
            "snack",
            "drink",
        ),
        "taste": (
            "savory",
            "umami",
            "spicy",
            "sweet",
            "salty",
            "sour",
            "bitter",
            "smoky",
            "buttery",
            "crisp",
            "rich",
            "light",
            "fresh",
            "creamy",
            "chewy",
        ),
        "context": (
            "quick_meal",
            "solo_meal",
            "group_meal",
            "casual",
            "date",
            "study_work",
            "takeout",
            "late_night",
            "comfort_meal",
            "special_occasion",
        ),
        "venue": (
            "casual",
            "cafe",
            "bakery",
            "bar",
            "diner",
            "bbq_place",
            "dessert_shop",
            "fast_casual",
            "sit_down",
        ),
        "emotion": (
            "satisfied",
            "delighted",
            "neutral",
            "disappointed",
            "reliable",
            "craving",
        ),
        "location_feature": (
            "nearby",
            "near_campus",
            "neighborhood_repeat",
            "destination",
            "commute_area",
        ),
        "temporal_feature": (
            "breakfast",
            "lunch",
            "afternoon",
            "dinner",
            "late_night",
            "weekday",
            "weekend",
        ),
    }


def test_restaurant_input_rejects_unknown_public_category() -> None:
    with pytest.raises(ValidationError, match="unsupported public restaurant category"):
        RestaurantInput(
            id="r_unknown",
            name="Unknown Place",
            category="Fusion",
            signature_dish=None,
            rating=4.5,
            rating_count=10,
            distance_m=400,
            thumbnail_url=None,
            thumbnail_tone="bone",
            thumbnail_label="fusion",
            tags=[],
            lat=36.371,
            lng=127.361,
            kakao_id="kakao_unknown",
            neighborhood="Eoeun-dong",
            is_bookmarked=False,
        )


@pytest.mark.parametrize(
    ("raw_category", "raw_path", "expected"),
    [
        ("한식", "음식점 > 한식", "Korean"),
        ("육류,고기", "음식점 > 한식 > 육류,고기", "Korean BBQ"),
        ("국수", "음식점 > 한식 > 국수", "Noodles"),
        ("분식", "음식점 > 분식", "Snacks"),
        ("커피전문점", "음식점 > 카페 > 커피전문점", "Cafe"),
        ("제과,베이커리", "음식점 > 카페 > 제과,베이커리", "Bakery"),
        ("중식", "음식점 > 중식", "Chinese"),
        ("일식", "음식점 > 일식", "Japanese"),
        ("양식", "음식점 > 양식", "Western"),
        ("호프,요리주점", "음식점 > 술집 > 호프,요리주점", "Bar"),
        ("Noodles", None, "Noodles"),
    ],
)
def test_normalize_public_restaurant_category_maps_kakao_labels(
    raw_category: str,
    raw_path: str | None,
    expected: str,
) -> None:
    assert normalize_public_restaurant_category(raw_category, raw_path) == expected


def test_normalize_public_restaurant_category_fails_loud_for_unknown_label() -> None:
    with pytest.raises(UnknownRestaurantCategoryError, match="unsupported restaurant category"):
        normalize_public_restaurant_category("퓨전음식", "음식점 > 퓨전음식")


def test_entry_profile_rejects_unknown_taxonomy_term() -> None:
    with pytest.raises(ValidationError, match="taste contains unsupported terms"):
        EntryProfileArtifact(
            entry_id="e_bad",
            user_id="u_bad",
            captured_at=NOW,
            taste={"crispy-ish": 0.7},
            confidence={"taste": 0.8},
            evidence={"taste": ["note: crispy-ish"]},
        )


def test_restaurant_profile_rejects_unknown_taxonomy_term() -> None:
    with pytest.raises(ValidationError, match="profile.context contains unsupported terms"):
        RestaurantProfileArtifact(
            restaurant_id="r_bad",
            generated_at=NOW,
            profile={"context": {"reserve_ahead": 0.7}},
            confidence={"context": 0.7},
            evidence={"context": ["tag: reserve ahead"]},
            profile_text="Restaurant bad profile.",
        )
