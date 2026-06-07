from __future__ import annotations

from app.models.media import MediaModel
from app.schemas.base import BaseSchema
from app.types.restaurant import FoodTone
from app.utils.time import as_utc


class ExifInfo(BaseSchema):
    captured_at: str | None = None
    lat: float | None = None
    lng: float | None = None
    has_location: bool = False
    has_timestamp: bool = False


class MediaInfo(BaseSchema):
    id: str
    url: str | None = None
    thumbnail_url: str | None = None
    width: int
    height: int
    bytes: int
    tone: FoodTone
    label: str
    exif: ExifInfo

    @classmethod
    def from_model(
        cls, m: MediaModel, url: str | None = None, thumbnail_url: str | None = None
    ) -> MediaInfo:
        """url/thumbnail_url are freshly-signed URLs minted at serialize time.

        We no longer read m.url/m.thumbnail_url (those frozen columns are unused).
        """
        has_loc = m.exif_lat is not None and m.exif_lng is not None
        captured_at = m.exif_captured_at
        return cls(
            id=m.id,
            url=url,
            thumbnail_url=thumbnail_url,
            width=m.width,
            height=m.height,
            bytes=m.bytes,
            tone=m.tone,
            label=m.label,
            exif=ExifInfo(
                captured_at=as_utc(captured_at).isoformat() if captured_at is not None else None,
                lat=m.exif_lat,
                lng=m.exif_lng,
                has_location=has_loc,
                has_timestamp=captured_at is not None,
            ),
        )
