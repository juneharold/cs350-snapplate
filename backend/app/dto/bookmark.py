from __future__ import annotations

from app.dto.base import BaseRequest, BaseResponse, BaseResponseCore
from app.schemas.bookmark import BookmarkInfo


class CreateBookmarkRequest(BaseRequest):
    restaurant_id: str


class CreateBookmarkData(BaseRequest):
    user_id: str
    restaurant_id: str


class UpdateBookmarkData(BaseRequest):
    pass


class CreateBookmarkResponseCore(BaseResponseCore):
    id: str
    restaurant_id: str
    bookmarked_at: str


class BookmarkListResponseCore(BaseResponseCore):
    items: list[BookmarkInfo]
    next_cursor: str | None = None
    total: int


CreateBookmarkResponse = BaseResponse[CreateBookmarkResponseCore]
BookmarkListResponse = BaseResponse[BookmarkListResponseCore]
