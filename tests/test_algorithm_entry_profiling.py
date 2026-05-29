from datetime import datetime, timezone

from algorithm import profile_diary_entry
from algorithm.schemas import DiaryEntryInput, EntryProfileArtifact, RestaurantInput


CAPTURED_AT = datetime(2026, 5, 24, 12, 43, tzinfo=timezone.utc)
USER_ID = "u_profile"


def restaurant(
    *,
    category: str,
    signature_dish: str | None,
    distance_m: int = 320,
    neighborhood: str = "Eoeun-dong",
) -> RestaurantInput:
    return RestaurantInput(
        id="r_profile",
        name="Profile Test Place",
        category=category,
        signature_dish=signature_dish,
        rating=4.5,
        rating_count=100,
        distance_m=distance_m,
        thumbnail_url=None,
        thumbnail_tone="bone",
        thumbnail_label=signature_dish or category.lower(),
        tags=[],
        lat=36.371,
        lng=127.361,
        kakao_id="kakao_profile",
        neighborhood=neighborhood,
        is_bookmarked=False,
    )


def entry(
    restaurant_input: RestaurantInput,
    *,
    rating: float | None = 4.5,
    note: str = "",
    image_labels: list[str] | None = None,
) -> DiaryEntryInput:
    return DiaryEntryInput(
        id="e_profile",
        user_id=USER_ID,
        captured_at=CAPTURED_AT,
        restaurant=restaurant_input,
        rating=rating,
        note=note,
        image_labels=image_labels or [],
    )


def test_profile_diary_entry_extracts_metadata_time_location_and_rating() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Korean BBQ",
                signature_dish="Marinated short rib",
            )
        )
    )

    assert isinstance(profile, EntryProfileArtifact)
    assert profile.entry_id == "e_profile"
    assert profile.user_id == USER_ID
    assert profile.captured_at == CAPTURED_AT
    assert profile.rating == 4.5
    assert "korean" in profile.cuisine
    assert "bbq" in profile.food_type
    assert profile.temporal_feature.keys() == {"lunch", "weekend"}
    assert profile.location_feature.keys() == {"eoeun_dong", "nearby"}
    assert "korean_bbq" in profile.venue
    assert "satisfied" in profile.emotion
    assert profile.taste == {}
    assert profile.context == {}
    assert_all_profile_fields_have_confidence_and_evidence(profile)
    assert profile.confidence["temporal_feature"] == 1.0
    assert profile.evidence["temporal_feature"] == [
        "captured_at: 2026-05-24T12:43:00+00:00"
    ]
    assert "restaurant.category: Korean BBQ" in profile.evidence["cuisine"]
    assert "restaurant.distance_m: 320" in profile.evidence["location_feature"]
    assert "rating: 4.5" in profile.evidence["emotion"]


def test_profile_diary_entry_leaves_unknown_optional_fields_empty() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Restaurant",
                signature_dish=None,
                distance_m=5000,
                neighborhood="",
            ),
            rating=None,
        )
    )

    assert profile.cuisine == {}
    assert profile.food_type == {}
    assert profile.taste == {}
    assert profile.context == {}
    assert profile.venue == {}
    assert profile.emotion == {}
    assert profile.location_feature == {}
    assert profile.temporal_feature == {"lunch": 1.0, "weekend": 1.0}
    assert set(profile.confidence) == {"temporal_feature"}
    assert set(profile.evidence) == {"temporal_feature"}


def test_profile_diary_entry_extracts_supported_text_signals() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Diner / Set meal",
                signature_dish="Kimchi stew set",
            ),
            rating=4.0,
            note="The kimchi stew was spicy, savory, and satisfying. Quick lunch after lab.",
        )
    )

    assert {"spicy", "savory"} <= set(profile.taste)
    assert "quick_meal" in profile.context
    assert {"positive", "satisfied"} <= set(profile.emotion)
    assert_all_profile_fields_have_confidence_and_evidence(profile)
    assert "note: spicy" in profile.evidence["taste"]
    assert "note: savory" in profile.evidence["taste"]
    assert "note: quick" in profile.evidence["context"]
    assert "note: satisfying" in profile.evidence["emotion"]


def test_profile_diary_entry_extracts_supported_image_labels() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(category="Restaurant", signature_dish=None),
            rating=None,
            image_labels=["korean stew", "rice bowl"],
        )
    )

    assert "korean" in profile.cuisine
    assert {"stew", "rice_bowl"} <= set(profile.food_type)
    assert_all_profile_fields_have_confidence_and_evidence(profile)
    assert "image_label: korean stew" in profile.evidence["cuisine"]
    assert "image_label: korean stew" in profile.evidence["food_type"]
    assert "image_label: rice bowl" in profile.evidence["food_type"]


def assert_all_profile_fields_have_confidence_and_evidence(
    profile: EntryProfileArtifact,
) -> None:
    profiled_fields = (
        "cuisine",
        "food_type",
        "taste",
        "context",
        "venue",
        "emotion",
        "location_feature",
        "temporal_feature",
    )
    for field_name in profiled_fields:
        values = getattr(profile, field_name)
        if not values:
            continue
        assert all(0 <= value <= 1 for value in values.values())
        assert 0 <= profile.confidence[field_name] <= 1
        assert profile.evidence[field_name]
