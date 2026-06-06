from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import asc, desc, select

from app.dto.draft import CreateDraftData, UpdateDraftData
from app.models.draft import DraftMediaModel, DraftModel
from app.repositories.base import BaseRepository


class DraftRepository(BaseRepository[DraftModel, CreateDraftData, UpdateDraftData]):
    model = DraftModel

    async def list_for_user(
        self, user_id: str, status: str | None, limit: int
    ) -> Sequence[DraftModel]:
        conds = [DraftModel.user_id == user_id]
        if status:
            conds.append(DraftModel.status == status)
        stmt = select(DraftModel).where(*conds).order_by(desc(DraftModel.created_at)).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()


class DraftMediaRepository:
    """Link table — no generic CRUD typevars needed; thin direct ops."""

    def __init__(self, db):
        self.db = db

    async def add(self, draft_id: str, media_id: str, position: int, is_cover: bool) -> None:
        self.db.add(
            DraftMediaModel(
                draft_id=draft_id, media_id=media_id, position=position, is_cover=is_cover
            )
        )
        await self.db.commit()

    async def for_draft(self, draft_id: str) -> Sequence[DraftMediaModel]:
        stmt = (
            select(DraftMediaModel)
            .where(DraftMediaModel.draft_id == draft_id)
            .order_by(asc(DraftMediaModel.position))
        )
        return (await self.db.execute(stmt)).scalars().all()
