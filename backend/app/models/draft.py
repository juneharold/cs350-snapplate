# pyright: reportArgumentType=false, reportAssignmentType=false
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field

from app.models.base import ForeignKeyField, OptionalTimestampField, SQLModelBase
from app.types.draft import DraftStatus
from app.utils.ids import draft_id


class DraftModel(SQLModelBase, table=True):
    __tablename__ = "drafts"
    __table_args__ = (
        CheckConstraint(
            "captured_at <= now() + interval '60 seconds'",
            name="ck_draft_captured_at_not_future",
        ),
    )

    id: str = Field(default_factory=draft_id, primary_key=True)
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    status: DraftStatus = DraftStatus.db_field(default=DraftStatus.WAITING)
    cover_media_id: str = ForeignKeyField("media.id", ondelete="RESTRICT")
    captured_at: datetime = Field(sa_type=DateTime(timezone=True), nullable=False)
    lat: float | None = Field(default=None)
    lng: float | None = Field(default=None)
    restaurant_id: str | None = ForeignKeyField(
        "restaurants.id", ondelete="SET NULL", nullable=True, default=None
    )
    restaurant_suggested: bool = Field(default=False, nullable=False)
    remind_at: datetime | None = OptionalTimestampField()


class DraftMediaModel(SQLModelBase, table=True):
    __tablename__ = "draft_media"

    draft_id: str = ForeignKeyField("drafts.id", ondelete="CASCADE", primary_key=True)
    media_id: str = ForeignKeyField("media.id", ondelete="CASCADE", primary_key=True)
    position: int = Field(default=0, nullable=False)
    is_cover: bool = Field(default=False, nullable=False)
