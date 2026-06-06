from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import select

from app.dto.media import CreateMediaData, UpdateMediaData
from app.models.media import MediaModel
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[MediaModel, CreateMediaData, UpdateMediaData]):
    model = MediaModel

    async def owned_ids(self, media_ids: Sequence[str], user_id: str) -> set[str]:
        """Return the subset of media_ids that belong to user_id.

        Used to gate draft linking so a caller can't attach (and later get a
        signed URL for) another user's media (REQ-SEC-004 / REQ-SEC-009).
        """
        if not media_ids:
            return set()
        stmt = select(MediaModel.id).where(
            MediaModel.id.in_(list(media_ids)),  # type: ignore[attr-defined]
            MediaModel.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return set(result.scalars().all())
