from __future__ import annotations

from app.schemas.algorithm import DiaryEntryInput
from sqlalchemy import select

from app.config.lifespan import Context
from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.services.algorithm.inputs import diary_entry_input_from_models


class DiaryInputService:
    def __init__(self, ctx: Context):
        self.db = ctx.db_session

    async def for_user(self, user_id: str) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)  # type: ignore[reportArgumentType]
            .where(EntryModel.user_id == user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
        )
        rows = (await self.db.execute(stmt)).all()
        return [diary_entry_input_from_models(entry, r) for entry, r in rows]

    async def for_peers(self, user_id: str, limit: int = 500) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)  # type: ignore[reportArgumentType]
            .where(EntryModel.user_id != user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
            .order_by(EntryModel.captured_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [diary_entry_input_from_models(entry, r) for entry, r in rows]
