from __future__ import annotations

from app.dto.base import BaseRequest, BaseResponse, BaseResponseCore
from app.schemas.restaurant import (
    RecommendedRestaurantInfo,
    RestaurantDetailInfo,
    RestaurantSummaryInfo,
    SearchResultInfo,
)
from app.types.restaurant import FoodTone


# ── Repo / Kakao data schema (maps 1:1 to RestaurantModel columns) ────────────
class KakaoRestaurantData(BaseRequest):
    kakao_id: str
    name: str
    category: str
    signature_dish: str | None = None
    rating: float = 0.0
    rating_count: int = 0
    thumbnail_url: str | None = None
    thumbnail_tone: FoodTone = FoodTone.BONE
    thumbnail_label: str = ""
    tags: list[str] = []
    lat: float = 0.0
    lng: float = 0.0
    neighborhood: str = ""
    address: str | None = None
    price_range: str | None = None
    hours: str | None = None
    phone: str | None = None
    raw_payload: dict | None = None


class UpdateRestaurantData(BaseRequest):
    rating: float | None = None
    rating_count: int | None = None
    neighborhood: str | None = None
    raw_payload: dict | None = None


# ── Response Cores + aliases ──────────────────────────────────────────────────
class NearbyResponseCore(BaseResponseCore):
    items: list[RestaurantSummaryInfo]
    next_cursor: str | None = None
    has_more: bool = False


class SearchResponseCore(BaseResponseCore):
    items: list[SearchResultInfo]
    next_cursor: str | None = None
    has_more: bool = False


class RecommendedResponseCore(BaseResponseCore):
    items: list[RecommendedRestaurantInfo]
    based_on_entries: int
    has_enough_data: bool


NearbyResponse = BaseResponse[NearbyResponseCore]
SearchResponse = BaseResponse[SearchResponseCore]
RecommendedResponse = BaseResponse[RecommendedResponseCore]
RestaurantDetailResponse = BaseResponse[RestaurantDetailInfo]
