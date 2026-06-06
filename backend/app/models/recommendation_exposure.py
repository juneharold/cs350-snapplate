from __future__ import annotations

from datetime import datetime

from sqlmodel import BigInteger, Column, Field

from app.models.base import ForeignKeyField, OptionalTimestampField, SQLModelBase, TimestampField


class RecommendationExposureModel(SQLModelBase, table=True):
    __tablename__ = "recommendation_exposure"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    restaurant_id: str = ForeignKeyField("restaurants.id", ondelete="CASCADE")
    shown_at: datetime = TimestampField()
    reason: str | None = Field(default=None)
