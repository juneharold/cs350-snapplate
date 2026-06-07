# pyright: reportAssignmentType=false
from __future__ import annotations

from datetime import datetime

from sqlmodel import JSON as SAJSON
from sqlmodel import Column, Field

from app.models.base import ForeignKeyField, OptionalTimestampField, SQLModelBase
from app.types.restaurant import FoodTone
from app.utils.ids import media_id


class MediaModel(SQLModelBase, table=True):
    __tablename__ = "media"

    id: str = Field(default_factory=media_id, primary_key=True)
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    storage_key: str = Field(nullable=False)
    url: str | None = Field(default=None)
    thumbnail_url: str | None = Field(default=None)
    width: int = Field(nullable=False)
    height: int = Field(nullable=False)
    bytes: int = Field(nullable=False)
    tone: FoodTone = FoodTone.db_field(default=FoodTone.BONE)
    label: str = Field(default="", max_length=24, nullable=False)
    # {thumb: key, medium: key} — variant object keys (vs a child table; only 2 sizes)
    variant_keys: dict | None = Field(default=None, sa_column=Column(SAJSON))
    exif_captured_at: datetime | None = OptionalTimestampField()
    exif_lat: float | None = Field(default=None)
    exif_lng: float | None = Field(default=None)
    deleted_at: datetime | None = OptionalTimestampField()
