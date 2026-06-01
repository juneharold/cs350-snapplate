from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import asc, select

from app.dto.entry import CreateEntryData, UpdateEntryData
from app.models.entry import EntryMediaModel, EntryModel
from app.repositories.base import BaseRepository


class EntryRepository(BaseRepository[EntryModel, CreateEntryData, UpdateEntryData]):
    model = EntryModel


class EntryMediaRepository:
    def __init__(self, db):
        self.db = db

    async def add(self, entry_id: str, media_id: str, position: int, is_cover: bool) -> None:
        self.db.add(
            EntryMediaModel(
                entry_id=entry_id, media_id=media_id, position=position, is_cover=is_cover
            )
        )

    async def for_entry(self, entry_id: str) -> Sequence[EntryMediaModel]:
        stmt = (
            select(EntryMediaModel)
            .where(EntryMediaModel.entry_id == entry_id)
            .order_by(asc(EntryMediaModel.position))
        )
        return (await self.db.execute(stmt)).scalars().all()
