# pyright: reportAssignmentType=false
from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import Index, desc
from sqlmodel import BigInteger, Column, Field

from app.models.base import ForeignKeyField, SQLModelBase, TimestampField


class RecommendationExposureModel(SQLModelBase, table=True):
    __tablename__ = "recommendation_exposure"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: str = ForeignKeyField("users.id", ondelete="CASCADE")
    restaurant_id: str = ForeignKeyField("restaurants.id", ondelete="CASCADE")
    shown_at: datetime = TimestampField(index=True)
    reason: str | None = Field(default=None)


Index(
    "ix_recommendation_exposure_user_shown_at",
    RecommendationExposureModel.user_id,
    desc(cast(Any, RecommendationExposureModel.shown_at)),
)
