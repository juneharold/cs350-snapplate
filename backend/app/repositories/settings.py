from __future__ import annotations

from app.dto.settings import CreateSettingsData, UpdateSettingsData
from app.models.settings import SettingsModel
from app.repositories.base import BaseRepository


class SettingsRepository(
    BaseRepository[SettingsModel, CreateSettingsData, UpdateSettingsData]
):
    model = SettingsModel

    async def get_or_create(self, user_id: str) -> SettingsModel:
        """Settings rows are created lazily with defaults on first read.

        Settings is keyed by user_id (1:1), not a generic `id`, so use find_by.
        """
        existing = await self.find_by(user_id=user_id)
        if existing is not None:
            return existing
        return await self.create(CreateSettingsData(user_id=user_id))
