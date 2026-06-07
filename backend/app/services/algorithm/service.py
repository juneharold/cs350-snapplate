from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.schemas.algorithm import (
    DiaryEntryInput,
    RecommendationContext,
    RecommendedResponse,
    RestaurantInput,
    RestaurantProfileArtifact,
    TasteProfileResponse,
)
from app.services.algorithm.inputs import (
    diary_entry_input_from_models,
    restaurant_input_from_model,
)
from app.services.algorithm.providers import ProfileProvider
from app.services.algorithm.recommendation_engine import generate_recommendations
from app.services.algorithm.recommendations import recommendation_context_from_artifacts
from app.services.algorithm.restaurants import (
    build_restaurant_profile_artifact,
    profile_restaurants,
)
from app.services.algorithm.taste import TasteRefreshArtifacts, build_taste_refresh_artifacts
from app.services.algorithm.taste_report import generate_taste_report


class AlgorithmService:
    def __init__(self, profile_provider: ProfileProvider):
        self.profile_provider = profile_provider

    def restaurant_input_from_model(
        self,
        restaurant: RestaurantModel,
        *,
        lat: float | None = None,
        lng: float | None = None,
        is_bookmarked: bool = False,
    ) -> RestaurantInput:
        return restaurant_input_from_model(
            restaurant,
            lat=lat,
            lng=lng,
            is_bookmarked=is_bookmarked,
        )

    def diary_entry_input_from_models(
        self,
        entry: EntryModel,
        restaurant: RestaurantModel,
        *,
        lat: float | None = None,
        lng: float | None = None,
        is_bookmarked: bool = False,
        image_references: list[str] | None = None,
    ) -> DiaryEntryInput:
        return diary_entry_input_from_models(
            entry,
            restaurant,
            lat=lat,
            lng=lng,
            is_bookmarked=is_bookmarked,
            image_references=image_references,
        )

    def build_recommendation_context(
        self,
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
        return recommendation_context_from_artifacts(
            diary_entries=diary_entries,
            peer_diary_entries=peer_diary_entries,
            candidate_restaurants=candidate_restaurants,
            user_profile_payload=user_profile_payload,
            restaurant_profile_payloads=restaurant_profile_payloads,
            exposure_history=exposure_history,
            lat=lat,
            lng=lng,
            requested_at=requested_at,
        )

    def generate_recommendations(
        self,
        user_id: str,
        context: RecommendationContext,
        *,
        limit: int,
        min_entries_required: int,
    ) -> RecommendedResponse:
        return generate_recommendations(
            user_id,
            context,
            limit=limit,
            min_entries_required=min_entries_required,
        )

    def build_taste_refresh_artifacts(
        self,
        user_id: str,
        diary_entries: Sequence[DiaryEntryInput],
        *,
        generated_at: datetime,
        min_entries_required: int,
    ) -> TasteRefreshArtifacts:
        return build_taste_refresh_artifacts(
            user_id,
            diary_entries,
            generated_at=generated_at,
            profile_provider=self.profile_provider,
            min_entries_required=min_entries_required,
        )

    def generate_taste_report(
        self,
        user_id: str,
        diary_entries: Sequence[DiaryEntryInput],
        *,
        min_entries_required: int,
    ) -> TasteProfileResponse:
        return generate_taste_report(
            user_id,
            diary_entries,
            profile_provider=self.profile_provider,
            min_entries_required=min_entries_required,
        )

    def build_restaurant_profile_artifact(
        self,
        restaurant: RestaurantModel,
        *,
        generated_at: datetime,
    ) -> RestaurantProfileArtifact:
        return build_restaurant_profile_artifact(
            restaurant,
            generated_at=generated_at,
            profile_provider=self.profile_provider,
        )

    async def profile_restaurants(
        self,
        internal: Any,
        restaurant_ids: Sequence[str],
    ) -> None:
        await profile_restaurants(
            internal,
            restaurant_ids,
            profile_provider=self.profile_provider,
        )
