from __future__ import annotations

from datetime import datetime

from sqlmodel import Field

from app.models.base import OptionalTimestampField, SQLModelBase
from app.utils.ids import user_id


class UserModel(SQLModelBase, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=user_id, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    nickname: str | None = Field(default=None, max_length=30)
    profile_image_url: str | None = Field(default=None)
    taste_type: str | None = Field(default=None)
    is_onboarded: bool = Field(default=False, nullable=False)
    deleted_at: datetime | None = OptionalTimestampField()
