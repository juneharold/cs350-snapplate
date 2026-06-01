from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Column, Field
from sqlmodel import JSON as SAJSON

from app.models.base import OptionalTimestampField, SQLModelBase, TimestampField
from app.types.restaurant import FoodTone
from app.utils.ids import restaurant_id


class RestaurantModel(SQLModelBase, table=True):
    __tablename__ = "restaurants"
    __table_args__ = (
        CheckConstraint("lat >= -90 AND lat <= 90", name="ck_restaurant_lat"),
        CheckConstraint("lng >= -180 AND lng <= 180", name="ck_restaurant_lng"),
    )

    id: str = Field(default_factory=restaurant_id, primary_key=True)
    kakao_id: str = Field(unique=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    category: str = Field(nullable=False, index=True)
    signature_dish: str | None = Field(default=None)
    rating: float = Field(default=0.0, nullable=False)
    rating_count: int = Field(default=0, nullable=False)
    thumbnail_url: str | None = Field(default=None)
    thumbnail_tone: FoodTone = FoodTone.db_field(default=FoodTone.BONE)
    thumbnail_label: str = Field(default="", nullable=False)
    tags: list[str] = Field(default_factory=list, sa_column=Column(SAJSON))
    lat: float = Field(nullable=False)
    lng: float = Field(nullable=False)
    neighborhood: str = Field(default="", nullable=False)
    address: str | None = Field(default=None)
    price_range: str | None = Field(default=None)
    hours: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    raw_payload: dict | None = Field(default=None, sa_column=Column(SAJSON))
    fetched_at: datetime = TimestampField()
    deleted_at: datetime | None = OptionalTimestampField()
