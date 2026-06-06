from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import UTC, datetime

from PIL import Image, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS


@dataclass
class ProcessedImage:
    original: bytes
    thumbnail: bytes
    medium: bytes
    width: int
    height: int
    exif_captured_at: datetime | None = None
    exif_lat: float | None = None
    exif_lng: float | None = None
    variant_dims: dict = field(default_factory=dict)


class ImageService:
    THUMB = (320, 320)
    MEDIUM = (1080, 1080)

    def process(self, data: bytes) -> ProcessedImage:
        img = Image.open(io.BytesIO(data))
        exif = self._exif_dict(img)
        captured_at = self._parse_captured_at(exif)
        lat, lng = self._parse_gps(img)

        # Apply orientation, then strip EXIF by re-encoding (saved bytes carry none).
        oriented = ImageOps.exif_transpose(img)
        width, height = oriented.size

        thumb_img = ImageOps.contain(oriented.copy(), self.THUMB)
        medium_img = ImageOps.contain(oriented.copy(), self.MEDIUM)

        return ProcessedImage(
            original=self._encode(oriented),
            thumbnail=self._encode(thumb_img),
            medium=self._encode(medium_img),
            width=width,
            height=height,
            exif_captured_at=captured_at,
            exif_lat=lat,
            exif_lng=lng,
            variant_dims={"thumb": thumb_img.size, "medium": medium_img.size},
        )

    @staticmethod
    def _exif_dict(img: Image.Image) -> dict:
        raw = img.getexif()
        return {TAGS.get(k, k): v for k, v in raw.items()} if raw else {}

    @staticmethod
    def _parse_captured_at(exif: dict) -> datetime | None:
        val = exif.get("DateTimeOriginal") or exif.get("DateTime")
        if not val:
            return None
        try:
            # EXIF format: "YYYY:MM:DD HH:MM:SS"
            dt = datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S")
            return dt.replace(tzinfo=UTC)
        except ValueError:
            return None

    @staticmethod
    def _parse_gps(img: Image.Image) -> tuple[float | None, float | None]:
        raw = img.getexif()
        gps_ifd = raw.get_ifd(0x8825) if raw else None
        if not gps_ifd:
            return None, None
        gps = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}

        def _to_deg(value, ref) -> float | None:
            try:
                d, m, s = value
                deg = float(d) + float(m) / 60 + float(s) / 3600
                return -deg if ref in ("S", "W") else deg
            except Exception:
                return None

        lat = _to_deg(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
        lng = _to_deg(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
        return lat, lng

    @staticmethod
    def _encode(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        return buf.getvalue()
