from __future__ import annotations

from collections.abc import Sequence

from app.services.algorithm.taxonomy import UnknownRestaurantCategoryError
from fastapi import BackgroundTasks

from app.config.http_errors import AppError, NotFoundError
from app.config.lifespan import Context, InternalContext
from app.models.restaurant import RestaurantModel
from app.repositories.bookmark import BookmarkRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.restaurant import (
    PersonalizationInfo,
    RestaurantDetailInfo,
    RestaurantSummaryInfo,
    SearchResultInfo,
)
from app.services.algorithm.restaurants import profile_restaurants
from app.services.kakao.client import KakaoService
from app.utils.geo import haversine_m

# Refresh from Kakao when the cached set is thinner than what the caller asked for
# (cold/sparse cache). Once enough rows are cached, serve from DB (stale-while-revalidate).
_REFRESH_BELOW = 10


class RestaurantService:
    def __init__(
        self,
        ctx: Context,
        background_tasks: BackgroundTasks | None = None,
        internal: InternalContext | None = None,
    ):
        self.repo = RestaurantRepository(ctx.db_session)
        self.bookmarks = BookmarkRepository(ctx.db_session)
        self.kakao = KakaoService(ctx.http_client)
        self.background_tasks = background_tasks
        self.internal = internal

    async def nearby(
        self,
        lat: float,
        lng: float,
        radius_m: int,
        sort: str,
        category: str | None,
        min_rating: float | None,
        limit: int,
        user_id: str | None,
    ) -> list[RestaurantSummaryInfo]:
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise AppError(400, "invalid_coordinates", "Invalid lat/lng.")

        rows = list(await self.repo.list_active(category, min_rating, limit=200))
        # Cold/sparse cache → pull from Kakao, upsert, re-read (stale-while-revalidate).
        if len(rows) < max(_REFRESH_BELOW, limit):
            rows = await self._refresh_from_kakao(lat, lng, radius_m, category, min_rating)

        self._schedule_profile_refresh(rows)
        bookmarked = await self._bookmarked(user_id)
        items = [self._summary(r, lat, lng, bookmarked) for r in rows]
        # The cache (list_active) is not geo-bounded, so drop anything outside the
        # requested radius before sorting/slicing — otherwise /nearby can return
        # places well outside radius_m (REQ-4.2-007).
        items = [i for i in items if i.distance_m <= radius_m]
        items = self._sort(items, sort)
        return items[:limit]

    async def search(
        self,
        q: str,
        lat: float | None,
        lng: float | None,
        category: str | None,
        min_rating: float | None,
        limit: int,
        user_id: str | None,
    ) -> list[SearchResultInfo]:
        rows = await self.repo.search_text(q, category, min_rating, limit)
        bookmarked = await self._bookmarked(user_id)
        ql = q.lower()
        out: list[SearchResultInfo] = []
        for r in rows:
            base = self._summary(r, lat, lng, bookmarked).model_dump()
            out.append(SearchResultInfo(**base, match_score=self._match_score(r, ql)))
        out.sort(key=lambda i: -i.match_score)
        return out

    async def get_detail(
        self, restaurant_id: str, lat: float | None, lng: float | None, user_id: str | None
    ) -> RestaurantDetailInfo:
        r = await self.repo.find(restaurant_id)
        if r is None or r.deleted_at is not None:
            raise NotFoundError("Restaurant not found.")
        bookmarked = await self._bookmarked(user_id)
        dist = self._distance(r, lat, lng)
        return RestaurantDetailInfo.from_detail(
            r,
            distance_m=dist,
            is_bookmarked=r.id in bookmarked,
            personalization=PersonalizationInfo(),
        )

    # ── helpers ───────────────────────────────────────────────────────────────
    async def _refresh_from_kakao(
        self, lat: float, lng: float, radius_m: int, category: str | None, min_rating: float | None
    ) -> list[RestaurantModel]:
        try:
            kakao_rows = await self.kakao.category_search(lat, lng, radius_m)
        except UnknownRestaurantCategoryError:
            raise
        except Exception:
            # Kakao down + empty cache → nothing to serve.
            return []
        if not kakao_rows:
            return []
        # neighborhood for the area (one call, applied to all)
        neighborhood = await self.kakao.neighborhood_for(lat, lng)
        for k in kakao_rows:
            k.neighborhood = neighborhood
        await self.repo.upsert_many(kakao_rows)
        return list(await self.repo.list_active(category, min_rating, limit=200))

    def _schedule_profile_refresh(self, rows: Sequence[RestaurantModel]) -> None:
        if self.background_tasks is None or self.internal is None:
            return
        self.background_tasks.add_task(
            profile_restaurants,
            self.internal,
            [restaurant.id for restaurant in rows],
        )

    async def _bookmarked(self, user_id: str | None) -> set[str]:
        if not user_id:
            return set()
        return await self.bookmarks.bookmarked_restaurant_ids(user_id)

    def _summary(
        self, r: RestaurantModel, lat: float | None, lng: float | None, bookmarked: set[str]
    ) -> RestaurantSummaryInfo:
        return RestaurantSummaryInfo.from_model(
            r, distance_m=self._distance(r, lat, lng), is_bookmarked=r.id in bookmarked
        )

    @staticmethod
    def _distance(r: RestaurantModel, lat: float | None, lng: float | None) -> int:
        if lat is None or lng is None:
            return 0
        return haversine_m(lat, lng, r.lat, r.lng)

    @staticmethod
    def _sort(items: list[RestaurantSummaryInfo], sort: str) -> list[RestaurantSummaryInfo]:
        if sort == "rating":
            return sorted(items, key=lambda i: -i.rating)
        # 'distance' (default) and 'recommended' (no rec ranking here) → distance
        return sorted(items, key=lambda i: i.distance_m)

    @staticmethod
    def _match_score(r: RestaurantModel, ql: str) -> float:
        hay = f"{r.name} {r.signature_dish or ''} {r.category} {r.neighborhood}".lower()
        if not ql:
            return 0.5
        if ql in hay:
            return round(min(1.0, len(ql) / max(len(hay), 1) + 0.5), 2)
        q_chars = set(ql)
        overlap = sum(1 for c in q_chars if c in hay)
        return round(overlap / max(len(q_chars), 1) * 0.3, 2)
