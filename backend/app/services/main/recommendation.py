from __future__ import annotations

from algorithm import generate_recommendations
from algorithm.schemas import DiaryEntryInput, RecommendationContext, RestaurantInput

from app.config.lifespan import Context
from app.dto.restaurant import RecommendedResponseCore
from app.repositories.restaurant import RestaurantRepository
from app.schemas.restaurant import RecommendedRestaurantInfo
from app.services.main.diary_inputs import DiaryInputService

_MIN_ENTRIES = 3


class RecommendationService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.restaurants = RestaurantRepository(ctx.db_session)

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

        candidates = await self._candidates(entries)
        context = RecommendationContext(
            diary_entries=entries,
            candidate_restaurants=candidates,
            lat=lat,
            lng=lng,
            exposure_history=[],
        )
        try:
            result = generate_recommendations(user_id, context, limit=limit, min_entries_required=_MIN_ENTRIES)
        except Exception:
            return RecommendedResponseCore(
                items=[], based_on_entries=len(entries), has_enough_data=False
            )

        items = [
            RecommendedRestaurantInfo(**r.model_dump())
            for r in result.items
        ]
        return RecommendedResponseCore(
            items=items,
            based_on_entries=result.based_on_entries,
            has_enough_data=result.has_enough_data,
        )

    async def _candidates(self, entries: list[DiaryEntryInput]) -> list[RestaurantInput]:
        """Candidate pool = all active restaurants not yet visited, as RestaurantInput."""
        visited = {e.restaurant.id for e in entries}
        rows = await self.restaurants.list_active(None, None, limit=200)
        out: list[RestaurantInput] = []
        for r in rows:
            if r.id in visited:
                continue
            out.append(
                RestaurantInput(
                    id=r.id,
                    name=r.name,
                    category=r.category,
                    signature_dish=r.signature_dish,
                    rating=r.rating,
                    rating_count=r.rating_count,
                    distance_m=0,
                    thumbnail_url=r.thumbnail_url,
                    thumbnail_tone=r.thumbnail_tone,
                    thumbnail_label=r.thumbnail_label,
                    tags=list(r.tags or []),
                    lat=r.lat,
                    lng=r.lng,
                    kakao_id=r.kakao_id,
                    neighborhood=r.neighborhood,
                    is_bookmarked=False,
                )
            )
        return out
