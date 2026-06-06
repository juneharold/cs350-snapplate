# pyright: reportArgumentType=false
from __future__ import annotations

from sqlalchemy import desc, select

from app.config.http_errors import AppError, NotFoundError
from app.config.lifespan import Context
from app.dto.bookmark import CreateBookmarkData
from app.models.bookmark import BookmarkModel
from app.repositories.bookmark import BookmarkRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.bookmark import BookmarkInfo
from app.schemas.restaurant import RestaurantSummaryInfo
from app.utils.time import as_utc


class BookmarkService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.repo = BookmarkRepository(ctx.db_session)
        self.restaurants = RestaurantRepository(ctx.db_session)

    async def add(self, user_id: str, restaurant_id: str) -> BookmarkModel:
        restaurant = await self.restaurants.find(restaurant_id)
        if restaurant is None or restaurant.deleted_at is not None:
            raise AppError(404, "restaurant_not_found", "Restaurant not found.")
        existing = await self.repo.find_one(user_id, restaurant_id)
        if existing is not None:
            raise AppError(409, "already_bookmarked", "Already bookmarked.")
        return await self.repo.create(
            CreateBookmarkData(user_id=user_id, restaurant_id=restaurant_id)
        )

    async def remove(self, user_id: str, restaurant_id: str) -> None:
        existing = await self.repo.find_one(user_id, restaurant_id)
        if existing is None:
            raise NotFoundError("Bookmark not found.")
        await self.repo.delete(existing.id)

    async def list(self, user_id: str, q: str | None, limit: int) -> tuple[list[BookmarkInfo], int]:
        db = self.ctx.db_session
        stmt = (
            select(BookmarkModel)
            .where(BookmarkModel.user_id == user_id)
            .order_by(desc(BookmarkModel.bookmarked_at))
        )
        rows = list((await db.execute(stmt)).scalars().all())
        total = len(rows)

        items: list[BookmarkInfo] = []
        for bm in rows:
            r = await self.restaurants.find(bm.restaurant_id)
            if r is None:
                continue
            if q and q.lower() not in r.name.lower():
                continue
            items.append(
                BookmarkInfo(
                    id=bm.id,
                    restaurant_id=bm.restaurant_id,
                    restaurant=RestaurantSummaryInfo.from_model(r, is_bookmarked=True),
                    bookmarked_at=as_utc(bm.bookmarked_at).isoformat(),
                )
            )
        return items[:limit], total
