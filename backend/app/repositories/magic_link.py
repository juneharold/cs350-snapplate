from __future__ import annotations

from app.dto.auth import CreateMagicLinkData, UpdateMagicLinkData
from app.models.magic_link import MagicLinkModel
from app.repositories.base import BaseRepository


class MagicLinkRepository(
    BaseRepository[MagicLinkModel, CreateMagicLinkData, UpdateMagicLinkData]
):
    model = MagicLinkModel

    async def find_by_token(self, token_hash: str) -> MagicLinkModel | None:
        return await self.find_by(token=token_hash)
