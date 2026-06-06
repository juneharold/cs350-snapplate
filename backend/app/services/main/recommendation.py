from __future__ import annotations

from collections.abc import Sequence

from algorithm import generate_recommendations
from algorithm.config import RECOMMENDATION_COOLDOWN_REQUESTS
from algorithm.schemas import DiaryEntryInput, RestaurantInput

from app.config.http_errors import AppError
from app.config.lifespan import Context
from app.dto.restaurant import RecommendedResponseCore
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.repositories.bookmark import BookmarkRepository
from app.repositories.recommendation_exposure import RecommendationExposureRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.restaurant import RecommendedRestaurantInfo
from app.services.algorithm.inputs import restaurant_input_from_model
from app.services.algorithm.recommendations import recommendation_context_from_artifacts
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

    async def recommend(
        self, user_id: str | None, lat: float | None, lng: float | None, limit: int
    ) -> RecommendedResponseCore:
        if not user_id:
            return RecommendedResponseCore(items=[], based_on_entries=0, has_enough_data=False)

        entries = await DiaryInputService(self.ctx).for_user(user_id)
        if len(entries) < _MIN_ENTRIES:
            return RecommendedResponseCore(
                items=[], based_on_entries=len(entries), has_enough_data=False
            )

        user_profile = await self.artifacts.latest_user_profile(user_id)
        if user_profile is None:
            raise AppError(
                503,
                "recommendations_unavailable",
                "Recommendations are not ready. Refresh taste analysis first.",
            )

        candidates = await self._candidates(entries, user_id, lat, lng)
        restaurant_artifacts = await self.artifacts.latest_restaurant_profiles(
            [candidate.id for candidate in candidates]
        )
        profiled_candidates = [
            candidate for candidate in candidates if candidate.id in restaurant_artifacts
        ]
        if not profiled_candidates:
            raise AppError(
                503,
                "recommendations_unavailable",
                "Restaurant profiles are not ready yet.",
            )

        requested_at = utcnow()
        context = recommendation_context_from_artifacts(
            diary_entries=entries,
            peer_diary_entries=await DiaryInputService(self.ctx).for_peers(user_id),
            candidate_restaurants=profiled_candidates,
            user_profile_payload=user_profile.payload_json,
            restaurant_profile_payloads=[
                restaurant_artifacts[candidate.id].payload_json for candidate in profiled_candidates
            ],
            exposure_history=await self.exposures.latest_restaurant_ids(
                user_id,
                RECOMMENDATION_COOLDOWN_REQUESTS,
            ),
            lat=lat,
            lng=lng,
            requested_at=requested_at,
        )
        result = generate_recommendations(
            user_id,
            context,
            limit=limit,
            min_entries_required=_MIN_ENTRIES,
        )

        items = [RecommendedRestaurantInfo(**r.model_dump()) for r in result.items]
        await self.exposures.add_many(
            user_id=user_id,
            restaurant_reasons={item.id: item.reason for item in items},
            shown_at=requested_at,
        )
        return RecommendedResponseCore(
            items=items,
            based_on_entries=result.based_on_entries,
            has_enough_data=result.has_enough_data,
        )

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
            restaurant_input_from_model(
                row,
                lat=lat,
                lng=lng,
                is_bookmarked=row.id in bookmarked,
            )
            for row in rows
            if row.id not in visited
        ]
