from __future__ import annotations

from app.dto.auth import CreateUserData, UpdateUserData
from app.models.user import UserModel
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel, CreateUserData, UpdateUserData]):
    model = UserModel

    async def find_by_email(self, email: str) -> UserModel | None:
        return await self.find_by(email=email)
