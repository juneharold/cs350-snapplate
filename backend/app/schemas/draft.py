from __future__ import annotations

from app.schemas.base import BaseSchema
from app.schemas.restaurant import RestaurantSummaryInfo
from app.types.draft import DraftStatus
from app.types.restaurant import FoodTone


class DraftRestaurantBrief(BaseSchema):
    id: str
    name: str
    neighborhood: str


class DraftMediaItem(BaseSchema):
    id: str
    url: str | None = None
    thumbnail_url: str | None = None
    is_cover: bool
    tone: FoodTone
    label: str


class DraftSummaryInfo(BaseSchema):
    id: str
    status: DraftStatus
    captured_at: str
    captured_relative: str
    cover_media_url: str | None = None
    cover_media_tone: FoodTone
    cover_media_label: str
    media_count: int
    restaurant: DraftRestaurantBrief | None = None
    restaurant_suggested: bool
    remind_at: str | None = None


class DraftDetailInfo(BaseSchema):
    id: str
    status: DraftStatus
    media: list[DraftMediaItem]
    captured_at: str
    lat: float | None = None
    lng: float | None = None
    restaurant: RestaurantSummaryInfo | None = None
    restaurant_suggested: bool
    created_at: str
    remind_at: str | None = None
