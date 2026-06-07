from datetime import UTC, datetime

import pytest

from app.schemas.algorithm import (
    DiaryEntryInput,
    EntryProfileArtifact,
    ProfileExtractionResult,
    ProfileSummaryResult,
    RestaurantInput,
)
from app.services.algorithm import profile_diary_entry
from app.services.algorithm.providers import DeterministicProvider

CAPTURED_AT = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)
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
    image_references: list[str] | None = None,
) -> DiaryEntryInput:
    return DiaryEntryInput(
        id="e_profile",
        user_id=USER_ID,
        captured_at=CAPTURED_AT,
        restaurant=restaurant_input,
        rating=rating,
        note=note,
        image_labels=image_labels or [],
        image_references=image_references or [],
    )


class FakeExtractionProvider:
    def __init__(self) -> None:
        self.text_inputs: list[str] = []
        self.image_references: list[str] = []

    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        self.text_inputs.append(text)
        return ProfileExtractionResult(
            profile={"taste": {"spicy": 0.93}, "context": {"solo_meal": 0.72}},
            confidence={"taste": 0.91, "context": 0.74},
            evidence={"taste": ["model: spicy broth"], "context": ["model: solo wording"]},
        )

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        self.image_references.append(image_reference)
        return ProfileExtractionResult(
            profile={"cuisine": {"japanese": 0.84}, "food_type": {"noodle": 0.82}},
            confidence={"cuisine": 0.86, "food_type": 0.83},
            evidence={"cuisine": ["image: Japanese bowl"], "food_type": ["image: noodles"]},
        )

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        raise AssertionError("entry profiling should not request profile summaries")

    def embed_text(self, text: str) -> list[float]:
        raise AssertionError("entry profiling should not request embeddings")


def test_profile_diary_entry_extracts_metadata_time_location_and_rating() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Korean BBQ",
                signature_dish="Marinated short rib",
            )
        ),
        profile_provider=DeterministicProvider(),
    )

    assert isinstance(profile, EntryProfileArtifact)
    assert profile.entry_id == "e_profile"
    assert profile.user_id == USER_ID
    assert profile.captured_at == CAPTURED_AT
    assert profile.rating == 4.5
    assert "korean" in profile.cuisine
    assert "bbq" in profile.food_type
    assert profile.temporal_feature.keys() == {"lunch", "weekend"}
    assert profile.location_feature.keys() == {"near_campus", "nearby"}
    assert "bbq_place" in profile.venue
    assert "delighted" in profile.emotion
    assert profile.taste == {}
    assert profile.context == {}
    assert_all_profile_fields_have_confidence_and_evidence(profile)
    assert profile.confidence["temporal_feature"] == 1.0
    assert profile.evidence["temporal_feature"] == ["captured_at: 2026-05-24T12:43:00+00:00"]
    assert "restaurant.category: Korean BBQ" in profile.evidence["cuisine"]
    assert "restaurant.distance_m: 320" in profile.evidence["location_feature"]
    assert "rating: 4.5" in profile.evidence["emotion"]


def test_profile_diary_entry_leaves_unknown_optional_fields_empty() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Western",
                signature_dish=None,
                distance_m=5000,
                neighborhood="",
            ),
            rating=None,
        ),
        profile_provider=DeterministicProvider(),
    )

    assert profile.cuisine == {"western": 0.85}
    assert profile.food_type == {}
    assert profile.taste == {}
    assert profile.context == {}
    assert profile.venue == {"sit_down": 0.8}
    assert profile.emotion == {}
    assert profile.location_feature == {}
    assert profile.temporal_feature == {"lunch": 1.0, "weekend": 1.0}
    assert set(profile.confidence) == {"cuisine", "venue", "temporal_feature"}
    assert set(profile.evidence) == {"cuisine", "venue", "temporal_feature"}


def test_profile_diary_entry_extracts_supported_text_signals() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Diner / Set meal",
                signature_dish="Kimchi stew set",
            ),
            rating=4.0,
            note="The kimchi stew was spicy, savory, and satisfying. Quick lunch after lab.",
        ),
        profile_provider=DeterministicProvider(),
    )

    assert {"spicy", "savory"} <= set(profile.taste)
    assert "quick_meal" in profile.context
    assert "satisfied" in profile.emotion
    assert_all_profile_fields_have_confidence_and_evidence(profile)
    assert "note: spicy" in profile.evidence["taste"]
    assert "note: savory" in profile.evidence["taste"]
    assert "note: quick" in profile.evidence["context"]
    assert "note: satisfying" in profile.evidence["emotion"]


def test_profile_diary_entry_extracts_supported_image_labels() -> None:
    profile = profile_diary_entry(
        entry(
            restaurant(category="Snacks", signature_dish=None),
            rating=None,
            image_labels=["korean stew", "rice bowl"],
        ),
        profile_provider=DeterministicProvider(),
    )

    assert "korean" in profile.cuisine
    assert {"stew", "rice_bowl"} <= set(profile.food_type)
    assert_all_profile_fields_have_confidence_and_evidence(profile)
    assert "image_label: korean stew" in profile.evidence["cuisine"]
    assert "image_label: korean stew" in profile.evidence["food_type"]
    assert "image_label: rice bowl" in profile.evidence["food_type"]


def test_profile_diary_entry_merges_ml_text_and_image_signals() -> None:
    provider = FakeExtractionProvider()

    profile = profile_diary_entry(
        entry(
            restaurant(
                category="Japanese",
                signature_dish="Shoyu ramen",
            ),
            rating=4.5,
            note="Spicy broth during a solo dinner.",
            image_references=["file-entry-image-1"],
        ),
        profile_provider=provider,
    )

    assert len(provider.text_inputs) == 1
    assert "Spicy broth during a solo dinner." in provider.text_inputs[0]
    assert "restaurant.category: Japanese" in provider.text_inputs[0]
    assert provider.image_references == ["file-entry-image-1"]
    assert profile.taste["spicy"] == 0.93
    assert profile.context["solo_meal"] == 0.72
    assert profile.cuisine["japanese"] == 0.85
    assert profile.food_type["noodle"] == 0.82
    assert "model: spicy broth" in profile.evidence["taste"]
    assert "image: noodles" in profile.evidence["food_type"]
    assert_all_profile_fields_have_confidence_and_evidence(profile)


def test_profile_diary_entry_requires_provider_argument() -> None:
    with pytest.raises(TypeError, match="profile_provider"):
        profile_diary_entry(
            entry(
                restaurant(
                    category="Japanese",
                    signature_dish="Shoyu ramen",
                ),
                note="Spicy broth.",
            )
        )


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
