from __future__ import annotations

import base64

from sqlalchemy import select

from app.config.lifespan import Context
from app.config.logger import create_logger
from app.models.entry import EntryModel
from app.models.media import MediaModel
from app.models.restaurant import RestaurantModel
from app.schemas.algorithm import DiaryEntryInput
from app.services.s3.storage import StorageService
from app.utils.restaurant_taxonomy import UnknownRestaurantCategoryError

logger = create_logger(__name__)


class DiaryInputService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.algorithm = ctx.algorithm_service

    async def for_user(
        self, user_id: str, *, include_image_references: bool = False
    ) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)  # type: ignore[reportArgumentType]
            .where(EntryModel.user_id == user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
        )
        rows = (await self.db.execute(stmt)).all()
        return await self._inputs_from_rows(
            rows,
            include_image_references=include_image_references,
        )

    async def for_peers(self, user_id: str, limit: int = 500) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)  # type: ignore[reportArgumentType]
            .where(EntryModel.user_id != user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
            .order_by(EntryModel.captured_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return await self._inputs_from_rows(rows, include_image_references=False)

    async def _inputs_from_rows(
        self, rows, *, include_image_references: bool
    ) -> list[DiaryEntryInput]:
        image_references = {}
        if include_image_references:
            entries = [entry for entry, _restaurant in rows]
            image_references = await self._image_references_by_entry(entries)

        inputs = []
        for entry, restaurant in rows:
            try:
                inputs.append(
                    self.algorithm.diary_entry_input_from_models(
                        entry,
                        restaurant,
                        image_references=image_references.get(entry.id, []),
                    )
                )
            except UnknownRestaurantCategoryError as exc:
                logger.warning(
                    f"skipping diary entry {entry.id} with unsupported restaurant category "
                    f"on restaurant {restaurant.id}: {exc}"
                )
        return inputs

    async def _image_references_by_entry(self, entries: list[EntryModel]) -> dict[str, list[str]]:
        media_ids = list({entry.cover_media_id for entry in entries})
        if not media_ids:
            return {}

        stmt = select(MediaModel).where(MediaModel.id.in_(media_ids))  # type: ignore[attr-defined]
        media_rows = (await self.db.execute(stmt)).scalars().all()
        media_by_id = {media.id: media for media in media_rows}
        references = {}
        storage = StorageService(self.ctx.s3)
        for entry in entries:
            media = media_by_id.get(entry.cover_media_id)
            if media is None:
                continue
            key = (media.variant_keys or {}).get("medium") or media.storage_key
            references[entry.id] = [_jpeg_data_url(await storage.get(key))]
        return references


def _jpeg_data_url(data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
