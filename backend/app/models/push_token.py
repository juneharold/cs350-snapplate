from __future__ import annotations

from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import ForeignKeyField, SQLModelBase, TimestampField
from app.types.media import PushPlatform
from app.utils.ids import push_token_id


class PushTokenModel(SQLModelBase, table=True):
    __tablename__ = "push_tokens"
    __table_args__ = (UniqueConstraint("user_id", "expo_token", name="uq_push_user_token"),)

    id: str = Field(default_factory=push_token_id, primary_key=True)
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    expo_token: str = Field(nullable=False)
    platform: PushPlatform = PushPlatform.db_field()
    last_seen_at: datetime = TimestampField()
