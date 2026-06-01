from __future__ import annotations

from app.dto.media import CreateMediaData, UpdateMediaData
from app.models.media import MediaModel
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[MediaModel, CreateMediaData, UpdateMediaData]):
    model = MediaModel
