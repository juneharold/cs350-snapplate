from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from app.config.auth import UserContext, get_user_context
from app.config.lifespan import Context, get_context
from app.dto.bookmark import (
    BookmarkListResponse,
    BookmarkListResponseCore,
    CreateBookmarkRequest,
    CreateBookmarkResponse,
    CreateBookmarkResponseCore,
)
from app.services.main.bookmark import BookmarkService
from app.utils.time import as_utc

api = APIRouter()


@api.get("/bookmarks", response_model=BookmarkListResponse)
async def list_bookmarks(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, le=50),
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> BookmarkListResponse:
    items, total = await BookmarkService(ctx).list(user.user_id, q, limit)
    return BookmarkListResponse(
        response=BookmarkListResponseCore(items=items, next_cursor=None, total=total)
    )


@api.post("/bookmarks", response_model=CreateBookmarkResponse, status_code=201)
async def add_bookmark(
    body: CreateBookmarkRequest,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> CreateBookmarkResponse:
    bm = await BookmarkService(ctx).add(user.user_id, body.restaurant_id)
    return CreateBookmarkResponse(
        response=CreateBookmarkResponseCore(
            id=bm.id,
            restaurant_id=bm.restaurant_id,
            bookmarked_at=as_utc(bm.bookmarked_at).isoformat(),
        )
    )


@api.delete("/bookmarks/{restaurant_id}")
async def remove_bookmark(
    restaurant_id: str,
    ctx: Context = Depends(get_context),
    user: UserContext = Depends(get_user_context),
) -> Response:
    await BookmarkService(ctx).remove(user.user_id, restaurant_id)
    return Response(status_code=204)
