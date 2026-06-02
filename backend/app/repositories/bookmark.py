from __future__ import annotations

from sqlalchemy import select

from app.dto.bookmark import CreateBookmarkData, UpdateBookmarkData
from app.models.bookmark import BookmarkModel
from app.repositories.base import BaseRepository


class BookmarkRepository(
    BaseRepository[BookmarkModel, CreateBookmarkData, UpdateBookmarkData]
):
    model = BookmarkModel

    async def bookmarked_restaurant_ids(self, user_id: str) -> set[str]:
        stmt = select(BookmarkModel.restaurant_id).where(BookmarkModel.user_id == user_id)
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def find_one(self, user_id: str, restaurant_id: str) -> BookmarkModel | None:
        return await self.find_by(user_id=user_id, restaurant_id=restaurant_id)
