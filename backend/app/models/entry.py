from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Column, Field
from sqlmodel import JSON as SAJSON

from app.models.base import ForeignKeyField, OptionalTimestampField, SQLModelBase, TimestampField
from app.utils.ids import entry_id


class EntryModel(SQLModelBase, table=True):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("captured_at <= now()", name="ck_entry_captured_at_not_future"),
    )

    id: str = Field(default_factory=entry_id, primary_key=True)
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    # source draft — plain audit text, NOT a live FK (the draft is deleted at finalize)
    draft_id: str | None = Field(default=None)
    restaurant_id: str = ForeignKeyField("restaurants.id", ondelete="RESTRICT")
    cover_media_id: str = ForeignKeyField("media.id", ondelete="RESTRICT")
    captured_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    meal_period: str | None = Field(default=None)
    rating: float | None = Field(default=None)
    note: str = Field(max_length=500, nullable=False)
    ai_tags: list[str] = Field(default_factory=list, sa_column=Column(SAJSON))
    deleted_at: datetime | None = OptionalTimestampField()


class EntryMediaModel(SQLModelBase, table=True):
    __tablename__ = "entry_media"

    entry_id: str = ForeignKeyField("entries.id", ondelete="CASCADE", primary_key=True)
    media_id: str = ForeignKeyField("media.id", ondelete="CASCADE", primary_key=True)
    position: int = Field(default=0, nullable=False)
    is_cover: bool = Field(default=False, nullable=False)
