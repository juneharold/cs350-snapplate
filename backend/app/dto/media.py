from __future__ import annotations

from datetime import datetime

from app.dto.base import BaseResponse, BaseResponseCore, BaseRequest
from app.schemas.media import MediaInfo
from app.types.restaurant import FoodTone


class CreateMediaData(BaseRequest):
    user_id: str
    storage_key: str
    url: str | None = None
    thumbnail_url: str | None = None
    width: int
    height: int
    bytes: int
    tone: FoodTone
    label: str
    variant_keys: dict | None = None
    exif_captured_at: datetime | None = None
    exif_lat: float | None = None
    exif_lng: float | None = None


class UpdateMediaData(BaseRequest):
    url: str | None = None
    thumbnail_url: str | None = None


class MediaUploadResponseCore(BaseResponseCore):
    uploads: list[MediaInfo]


MediaUploadResponse = BaseResponse[MediaUploadResponseCore]
