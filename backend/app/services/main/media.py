from __future__ import annotations

import hashlib

from app.config.http_errors import AppError
from app.config.lifespan import Context
from app.dto.media import CreateMediaData
from app.repositories.media import MediaRepository
from app.schemas.media import MediaInfo
from app.services.document.image import ImageService
from app.services.s3.storage import StorageService
from app.types.restaurant import FoodTone
from app.utils.ids import make_id


class MediaService:
    MAX_FILES = 10
    MAX_PER_FILE = 10 * 1024 * 1024
    MAX_TOTAL = 50 * 1024 * 1024
    ALLOWED = {"image/jpeg", "image/png", "image/jpg"}

    def __init__(self, ctx: Context):
        self.repo = MediaRepository(ctx.db_session)
        self.storage = StorageService(ctx.s3)
        self.images = ImageService()

    async def upload(
        self, user_id: str, files: list[tuple[str, str, bytes]], extract_exif: bool
    ) -> list[MediaInfo]:
        """files = list of (filename, content_type, data)."""
        if not files:
            raise AppError(400, "too_many_files", "No files provided.")
        if len(files) > self.MAX_FILES:
            raise AppError(400, "too_many_files", "Up to 10 files per upload.")
        total = sum(len(d) for _, _, d in files)
        if total > self.MAX_TOTAL:
            raise AppError(400, "file_too_large", "Total upload exceeds 50MB.")

        out: list[MediaInfo] = []
        for filename, content_type, data in files:
            if content_type not in self.ALLOWED:
                raise AppError(400, "unsupported_format", f"{content_type} not supported.")
            if len(data) > self.MAX_PER_FILE:
                raise AppError(400, "file_too_large", f"{filename} exceeds 10MB.")

            processed = self.images.process(data)
            mid = make_id("m")
            base_key = f"media/{user_id}/{mid}"
            keys = {
                "original": f"{base_key}.jpg",
                "thumb": f"{base_key}-thumb.jpg",
                "medium": f"{base_key}-medium.jpg",
            }
            await self.storage.put(keys["original"], processed.original)
            await self.storage.put(keys["thumb"], processed.thumbnail)
            await self.storage.put(keys["medium"], processed.medium)

            variant_keys = {"thumb": keys["thumb"], "medium": keys["medium"]}
            media = await self.repo.create(
                CreateMediaData(
                    user_id=user_id,
                    storage_key=keys["original"],
                    # url/thumbnail_url columns stay null — URLs are signed fresh at read time.
                    url=None,
                    thumbnail_url=None,
                    width=processed.width,
                    height=processed.height,
                    bytes=len(processed.original),
                    tone=self._tone_for(mid),
                    label=filename.rsplit(".", 1)[0][:24],
                    variant_keys=variant_keys,
                    exif_captured_at=processed.exif_captured_at if extract_exif else None,
                    exif_lat=processed.exif_lat if extract_exif else None,
                    exif_lng=processed.exif_lng if extract_exif else None,
                )
            )
            url, thumb_url = await self.storage.signed_urls_for(
                media.storage_key, media.variant_keys
            )
            out.append(MediaInfo.from_model(media, url=url, thumbnail_url=thumb_url))
        return out

    @staticmethod
    def _tone_for(seed: str) -> FoodTone:
        tones = list(FoodTone)
        return tones[int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(tones)]
