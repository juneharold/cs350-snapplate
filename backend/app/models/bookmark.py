from __future__ import annotations

from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import ForeignKeyField, SQLModelBase, TimestampField
from app.utils.ids import bookmark_id


class BookmarkModel(SQLModelBase, table=True):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id", name="uq_bookmark_user_restaurant"),
    )

    id: str = Field(default_factory=bookmark_id, primary_key=True)
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    restaurant_id: str = ForeignKeyField("restaurants.id", ondelete="CASCADE")
    bookmarked_at: datetime = TimestampField()
