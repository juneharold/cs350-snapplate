from __future__ import annotations

from datetime import datetime, timezone

from algorithm import profile_kakao_restaurant
from algorithm.config import EMBEDDING_DIMENSIONS
from algorithm.providers import DeterministicProvider
from algorithm.schemas import KakaoRestaurantMetadata, RestaurantProfileArtifact


NOW = datetime(2026, 5, 24, 12, 43, tzinfo=timezone.utc)


def test_profile_kakao_restaurant_normalizes_supported_metadata() -> None:
    restaurant = KakaoRestaurantMetadata(
        id="26338954",
        place_name="Bonga BBQ",
        category_name="Food > Korean BBQ",
        road_address_name="Eoeun-dong 99",
        x="127.361",
        y="36.371",
        place_url="https://place.map.kakao.com/26338954",
        signature_dish="Marinated short rib",
        tags=["reserve ahead", "smoky grill"],
        rating=4.7,
        rating_count=312,
    )

    profile = profile_kakao_restaurant(
        restaurant,
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
    )
    repeat = profile_kakao_restaurant(
        restaurant,
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
    )

    assert isinstance(profile, RestaurantProfileArtifact)
    assert profile.restaurant_id == "26338954"
    assert profile.generated_at == NOW
    assert profile.profile["cuisine"]["korean"] == 0.85
    assert profile.profile["food_type"]["bbq"] == 0.8
    assert profile.profile["venue"]["bbq_place"] == 0.8
    assert "context" not in profile.profile
    assert profile.profile["taste"]["smoky"] == 0.62
    assert profile.profile["location_feature"]["near_campus"] == 0.55
    assert profile.confidence["taste"] == 0.62
    assert "category_name: Food > Korean BBQ" in profile.evidence["cuisine"]
    assert "tag: smoky grill" in profile.evidence["taste"]
    assert "korean" in profile.profile_text
    assert len(profile.embedding) == EMBEDDING_DIMENSIONS
    assert profile.embedding == repeat.embedding


def test_profile_kakao_restaurant_keeps_sparse_metadata_low_confidence() -> None:
    restaurant = KakaoRestaurantMetadata(
        id="sparse",
        place_name="Sparse Place",
        category_name="Restaurant",
        address_name="Daejeon",
    )

    profile = profile_kakao_restaurant(
        restaurant,
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
    )

    assert profile.profile.get("taste", {}) == {}
    assert profile.profile.get("food_type", {}) == {}
    assert profile.profile.get("cuisine", {}) == {}
    assert profile.profile == {}
    assert profile.confidence == {}
    assert "taste" not in profile.evidence
    assert len(profile.embedding) == EMBEDDING_DIMENSIONS
