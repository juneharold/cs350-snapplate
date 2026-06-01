from __future__ import annotations

from app.models.user import UserModel
from app.schemas.base import BaseSchema


class AuthUserInfo(BaseSchema):
    """The compact user shape returned by /auth/verify (types.ts AuthUser)."""

    id: str
    email: str
    nickname: str | None = None
    profile_image_url: str | None = None
    is_new: bool = False

    @classmethod
    def from_model(cls, m: UserModel, *, is_new: bool = False) -> "AuthUserInfo":
        return cls(
            id=m.id,
            email=m.email,
            nickname=m.nickname,
            profile_image_url=m.profile_image_url,
            is_new=is_new,
        )
