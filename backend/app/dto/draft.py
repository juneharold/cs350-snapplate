from __future__ import annotations

from datetime import datetime

from app.dto.base import BaseRequest, BaseResponse, BaseResponseCore
from app.schemas.draft import DraftDetailInfo, DraftSummaryInfo
from app.types.draft import DraftStatus


# ── Request DTOs ──────────────────────────────────────────────────────────────
class CreateDraftRequest(BaseRequest):
    media_ids: list[str]
    cover_media_id: str | None = None
    captured_at: datetime | None = None
    lat: float | None = None
    lng: float | None = None
    restaurant_id: str | None = None
    restaurant_suggested: bool | None = None


class UpdateDraftRequest(BaseRequest):
    restaurant_id: str | None = None
    captured_at: datetime | None = None
    cover_media_id: str | None = None


class FinalizeDraftRequest(BaseRequest):
    note: str
    rating: float | None = None
    restaurant_id: str | None = None


# ── Repo data schemas ─────────────────────────────────────────────────────────
class CreateDraftData(BaseRequest):
    user_id: str
    status: DraftStatus
    cover_media_id: str
    captured_at: datetime
    lat: float | None = None
    lng: float | None = None
    restaurant_id: str | None = None
    restaurant_suggested: bool = False
    remind_at: datetime | None = None


class UpdateDraftData(BaseRequest):
    status: DraftStatus | None = None
    cover_media_id: str | None = None
    captured_at: datetime | None = None
    restaurant_id: str | None = None
    restaurant_suggested: bool | None = None


# ── Response Cores + aliases ──────────────────────────────────────────────────
class DraftListResponseCore(BaseResponseCore):
    items: list[DraftSummaryInfo]
    next_cursor: str | None = None
    total: int


class FinalizeDraftResponseCore(BaseResponseCore):
    entry_id: str
    draft_id: str


DraftDetailResponse = BaseResponse[DraftDetailInfo]
DraftListResponse = BaseResponse[DraftListResponseCore]
FinalizeDraftResponse = BaseResponse[FinalizeDraftResponseCore]
