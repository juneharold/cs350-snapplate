from __future__ import annotations

from collections.abc import Sequence

from app.config.algorithm import RECOMMENDATION_COOLDOWN_REQUESTS
from app.config.http_errors import AppError
from app.config.lifespan import Context
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.repositories.bookmark import BookmarkRepository
from app.repositories.recommendation_exposure import RecommendationExposureRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.algorithm import DiaryEntryInput, RestaurantInput
from app.services.main.diary_inputs import DiaryInputService
from app.utils.time import utcnow

_MIN_ENTRIES = 10


class RecommendationService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.restaurants = RestaurantRepository(self.db)
        self.bookmarks = BookmarkRepository(self.db)
        self.artifacts = AlgorithmArtifactRepository(self.db)
        self.exposures = RecommendationExposureRepository(self.db)
        self.algorithm = ctx.algorithm_service

    async def recommend(
        self, user_id: str | None, lat: float | None, lng: float | None, limit: int
    ) -> dict:
        if not user_id:
            return {"items": [], "based_on_entries": 0, "has_enough_data": False}

        entries = await DiaryInputService(self.ctx).for_user(user_id)
        if len(entries) < _MIN_ENTRIES:
            return {"items": [], "based_on_entries": len(entries), "has_enough_data": False}

        user_profile = await self.artifacts.latest_user_profile(user_id)
        if user_profile is None:
            # Recommendations intentionally require a refreshed user profile artifact.
            raise AppError(
                412,
                "user_profile_not_ready",
                "Recommendations are not ready. Refresh taste analysis first.",
            )

        candidates = await self._candidates(entries, user_id, lat, lng)
        candidate_by_id = {candidate.id: candidate for candidate in candidates}
        nearest_restaurant_profiles = await self.artifacts.nearest_restaurant_profiles(
            user_profile.long_term_embedding,
            candidate_restaurant_ids=list(candidate_by_id),
            limit=max(limit * 5, limit),
        )
        restaurant_artifacts = [artifact for artifact, _distance in nearest_restaurant_profiles]
        profiled_candidates = [
            candidate_by_id[artifact.restaurant_id] for artifact in restaurant_artifacts
        ]
        if not profiled_candidates:
            raise AppError(
                503,
                "restaurant_profiles_not_ready",
                "Restaurant profiles are not ready yet.",
            )

        requested_at = utcnow()
        context = self.algorithm.build_recommendation_context(
            diary_entries=entries,
            peer_diary_entries=await DiaryInputService(self.ctx).for_peers(user_id),
            candidate_restaurants=profiled_candidates,
            user_profile_payload=user_profile.payload_json,
            restaurant_profile_payloads=[
                artifact.payload_json for artifact in restaurant_artifacts
            ],
            exposure_history=await self.exposures.latest_restaurant_ids(
                user_id,
                RECOMMENDATION_COOLDOWN_REQUESTS,
            ),
            lat=lat,
            lng=lng,
            requested_at=requested_at,
        )
        result = self.algorithm.generate_recommendations(
            user_id,
            context,
            limit=limit,
            min_entries_required=_MIN_ENTRIES,
        )

        await self.exposures.add_many(
            user_id=user_id,
            restaurant_reasons={item.id: item.reason for item in result.items},
            shown_at=requested_at,
        )
        return result.model_dump(mode="json")

    async def _candidates(
        self,
        entries: Sequence[DiaryEntryInput],
        user_id: str,
        lat: float | None,
        lng: float | None,
    ) -> list[RestaurantInput]:
        visited = {e.restaurant.id for e in entries}
        bookmarked = await self.bookmarks.bookmarked_restaurant_ids(user_id)
        rows = await self.restaurants.list_active(None, None, limit=200)
        return [
            self.algorithm.restaurant_input_from_model(
                row,
                lat=lat,
                lng=lng,
                is_bookmarked=row.id in bookmarked,
            )
            for row in rows
            if row.id not in visited
        ]
