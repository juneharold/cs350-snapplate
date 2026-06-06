from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.config.auth import UserContext, get_optional_user_context
from app.config.lifespan import Context, get_context
from app.dto.restaurant import (
    NearbyResponse,
    NearbyResponseCore,
    RecommendedResponse,
    RestaurantDetailResponse,
    SearchResponse,
    SearchResponseCore,
)
from app.services.main.recommendation import RecommendationService
from app.services.main.restaurant import RestaurantService

api = APIRouter()


def _uid(user: UserContext | None) -> str | None:
    return user.user_id if user else None


@api.get("/restaurants/nearby", response_model=NearbyResponse)
async def nearby(
    background_tasks: BackgroundTasks,
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: int = Query(default=1500, ge=200, le=10000),
    sort: str = Query(default="distance"),
    category: str | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    limit: int = Query(default=20, le=50),
    ctx: Context = Depends(get_context),
    user: UserContext | None = Depends(get_optional_user_context),
) -> NearbyResponse:
    items = await RestaurantService(
        ctx,
        background_tasks,
        request.state.context,
    ).nearby(lat, lng, radius_m, sort, category, min_rating, limit, _uid(user))
    return NearbyResponse(
        response=NearbyResponseCore(items=items, next_cursor=None, has_more=False)
    )


@api.get("/restaurants/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    category: str | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    limit: int = Query(default=20, le=50),
    ctx: Context = Depends(get_context),
    user: UserContext | None = Depends(get_optional_user_context),
) -> SearchResponse:
    items = await RestaurantService(ctx).search(
        q, lat, lng, category, min_rating, limit, _uid(user)
    )
    return SearchResponse(
        response=SearchResponseCore(items=items, next_cursor=None, has_more=False)
    )


@api.get("/restaurants/recommended", response_model=RecommendedResponse)
async def recommended(
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    limit: int = Query(default=10, le=50),
    ctx: Context = Depends(get_context),
    user: UserContext | None = Depends(get_optional_user_context),
) -> RecommendedResponse:
    result = await RecommendationService(ctx).recommend(_uid(user), lat, lng, limit)
    return RecommendedResponse(response=result)


# NOTE: this dynamic route is registered LAST so /nearby, /search, /recommended
# (static paths) are matched before the {restaurant_id} catch-all.
@api.get("/restaurants/{restaurant_id}", response_model=RestaurantDetailResponse)
async def detail(
    restaurant_id: str,
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    ctx: Context = Depends(get_context),
    user: UserContext | None = Depends(get_optional_user_context),
) -> RestaurantDetailResponse:
    r = await RestaurantService(ctx).get_detail(restaurant_id, lat, lng, _uid(user))
    return RestaurantDetailResponse(response=r)
