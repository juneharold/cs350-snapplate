from __future__ import annotations

import aioboto3

from app.config.env import Env

_SIGNED_TTL_SEC = 15 * 60


class StorageService:
    def __init__(self, s3: aioboto3.Session):
        self.s3 = s3
        self.bucket = Env.get(Env.S3_BUCKET)
        self._endpoint = Env.get(Env.S3_ENDPOINT)
        self._access = Env.get(Env.S3_ACCESS_KEY)
        self._secret = Env.get(Env.S3_SECRET_KEY)
        self._region = Env.get(Env.S3_REGION)

    def _client(self):
        return self.s3.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access,
            aws_secret_access_key=self._secret,
            region_name=self._region,
        )

    async def put(self, key: str, data: bytes, content_type: str = "image/jpeg") -> None:
        async with self._client() as c:
            await c.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    async def signed_url(self, key: str, ttl: int = _SIGNED_TTL_SEC) -> str:
        async with self._client() as c:
            return await c.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl,
            )

    async def signed_urls_for(
        self, storage_key: str | None, variant_keys: dict | None
    ) -> tuple[str | None, str | None]:
        """Freshly sign (original, thumbnail) from stored keys.

        original ← storage_key; thumbnail ← variant_keys["thumb"] when present,
        else falls back to storage_key. Missing/None keys yield None.
        """
        original = await self.signed_url(storage_key) if storage_key else None
        thumb_key = (variant_keys or {}).get("thumb") or storage_key
        thumbnail = await self.signed_url(thumb_key) if thumb_key else None
        return original, thumbnail
