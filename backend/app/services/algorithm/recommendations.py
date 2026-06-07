from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.schemas.algorithm import (
    DiaryEntryInput,
    RecommendationContext,
    RestaurantInput,
    RestaurantProfileArtifact,
    UserProfileArtifact,
)


def recommendation_context_from_artifacts(
    *,
    diary_entries: Sequence[DiaryEntryInput],
    peer_diary_entries: Sequence[DiaryEntryInput],
    candidate_restaurants: Sequence[RestaurantInput],
    user_profile_payload: dict,
    restaurant_profile_payloads: Sequence[dict],
    exposure_history: Sequence[str],
    lat: float | None,
    lng: float | None,
    requested_at: datetime,
) -> RecommendationContext:
    return RecommendationContext(
        diary_entries=list(diary_entries),
        peer_diary_entries=list(peer_diary_entries),
        candidate_restaurants=list(candidate_restaurants),
        user_profile=UserProfileArtifact.model_validate(user_profile_payload),
        restaurant_profiles=[
            RestaurantProfileArtifact.model_validate(payload)
            for payload in restaurant_profile_payloads
        ],
        lat=lat,
        lng=lng,
        exposure_history=list(exposure_history),
        requested_at=requested_at,
    )
