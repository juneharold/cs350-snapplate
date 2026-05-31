from __future__ import annotations

from datetime import datetime

from app.dto.base import BaseRequest, BaseResponse, BaseResponseCore
from app.schemas.entry import EntryDetailInfo, EntrySummaryInfo


# ── Request DTOs ──────────────────────────────────────────────────────────────
class UpdateEntryRequest(BaseRequest):
    rating: float | None = None
    note: str | None = None


# ── Repo data schemas ─────────────────────────────────────────────────────────
class CreateEntryData(BaseRequest):
    user_id: str
    draft_id: str | None = None
    restaurant_id: str
    cover_media_id: str
    captured_at: datetime
    meal_period: str | None = None
    rating: float | None = None
    note: str
    ai_tags: list[str] = []


class UpdateEntryData(BaseRequest):
    rating: float | None = None
    note: str | None = None
    deleted_at: datetime | None = None


# ── Response Cores + aliases ──────────────────────────────────────────────────
class EntryListStats(BaseResponseCore):
    entries_total: int
    places_total: int
    this_month: int
    avg_rating: float


class EntryListResponseCore(BaseResponseCore):
    items: list[EntrySummaryInfo]
    next_cursor: str | None = None
    has_more: bool = False
    total: int
    stats: EntryListStats


EntryListResponse = BaseResponse[EntryListResponseCore]
EntryDetailResponse = BaseResponse[EntryDetailInfo]
