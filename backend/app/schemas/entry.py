from __future__ import annotations

from app.schemas.base import BaseSchema
from app.schemas.restaurant import RestaurantSummaryInfo
from app.types.restaurant import FoodTone


class EntryRestaurantBrief(BaseSchema):
    id: str
    name: str
    signature_dish: str | None = None
    neighborhood: str


class EntryMediaItem(BaseSchema):
    id: str
    url: str | None = None
    is_cover: bool
    tone: FoodTone
    label: str


class EntryVisitHistoryItem(BaseSchema):
    entry_id: str
    captured_at: str
    rating: float | None = None


class EntrySummaryInfo(BaseSchema):
    id: str
    captured_at: str
    day_label: str
    cover_media_url: str | None = None
    cover_media_tone: FoodTone
    cover_media_label: str
    media_count: int
    restaurant: EntryRestaurantBrief
    rating: float | None = None
    note_excerpt: str


class EntryDetailInfo(BaseSchema):
    id: str
    captured_at: str
    meal_period: str | None = None
    media: list[EntryMediaItem]
    rating: float | None = None
    note: str
    ai_tags: list[str]
    restaurant: RestaurantSummaryInfo
    user_visit_history: list[EntryVisitHistoryItem]
    created_at: str
