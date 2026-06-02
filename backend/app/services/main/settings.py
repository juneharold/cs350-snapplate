from __future__ import annotations

from app.config.lifespan import Context
from app.dto.settings import UpdateSettingsData
from app.repositories.settings import SettingsRepository
from app.schemas.settings import SettingsInfo


class SettingsService:
    def __init__(self, ctx: Context):
        self.repo = SettingsRepository(ctx.db_session)

    async def get_settings(self, user_id: str) -> SettingsInfo:
        settings = await self.repo.get_or_create(user_id)
        return SettingsInfo.from_model(settings)

    async def update_settings(
        self, user_id: str, data: UpdateSettingsData
    ) -> SettingsInfo:
        settings = await self.repo.get_or_create(user_id)
        if data.model_dump(exclude_unset=True):
            settings = await self.repo.update(settings, data)
        return SettingsInfo.from_model(settings)
