from __future__ import annotations

from sqlalchemy import select

from app.config.lifespan import Context
from app.config.logger import create_logger
from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.schemas.algorithm import DiaryEntryInput
from app.utils.restaurant_taxonomy import UnknownRestaurantCategoryError

logger = create_logger(__name__)


class DiaryInputService:
    def __init__(self, ctx: Context):
        self.db = ctx.db_session
        self.algorithm = ctx.algorithm_service

    async def for_user(self, user_id: str) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)  # type: ignore[reportArgumentType]
            .where(EntryModel.user_id == user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
        )
        rows = (await self.db.execute(stmt)).all()
        return self._inputs_from_rows(rows)

    async def for_peers(self, user_id: str, limit: int = 500) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)  # type: ignore[reportArgumentType]
            .where(EntryModel.user_id != user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
            .order_by(EntryModel.captured_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return self._inputs_from_rows(rows)

    def _inputs_from_rows(self, rows) -> list[DiaryEntryInput]:
        inputs = []
        for entry, restaurant in rows:
            try:
                inputs.append(self.algorithm.diary_entry_input_from_models(entry, restaurant))
            except UnknownRestaurantCategoryError as exc:
                logger.warning(
                    f"skipping diary entry {entry.id} with unsupported restaurant category "
                    f"on restaurant {restaurant.id}: {exc}"
                )
        return inputs
