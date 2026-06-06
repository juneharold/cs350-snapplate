from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.algorithm_artifact import (
    EntryProfileArtifactModel,
    RestaurantProfileArtifactModel,
    UserProfileArtifactModel,
)


class AlgorithmArtifactRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_entry_profile(
        self,
        *,
        entry_id: str,
        user_id: str,
        payload_json: dict,
        algorithm_version: str,
        generated_at: datetime,
    ) -> EntryProfileArtifactModel:
        artifact = EntryProfileArtifactModel(
            entry_id=entry_id,
            user_id=user_id,
            payload_json=payload_json,
            algorithm_version=algorithm_version,
            generated_at=generated_at,
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def latest_entry_profile(self, entry_id: str) -> EntryProfileArtifactModel | None:
        stmt = (
            select(EntryProfileArtifactModel)
            .where(EntryProfileArtifactModel.entry_id == entry_id)
            .order_by(desc(EntryProfileArtifactModel.generated_at))  # type: ignore[reportArgumentType]
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def latest_entry_profiles(
        self, entry_ids: list[str]
    ) -> dict[str, EntryProfileArtifactModel]:
        if not entry_ids:
            return {}
        stmt = (
            select(EntryProfileArtifactModel)
            .where(EntryProfileArtifactModel.entry_id.in_(entry_ids))  # type: ignore[attr-defined]
            .order_by(desc(EntryProfileArtifactModel.generated_at))  # type: ignore[reportArgumentType]
        )
        result = await self.db.execute(stmt)
        latest: dict[str, EntryProfileArtifactModel] = {}
        for artifact in result.scalars().all():
            latest.setdefault(artifact.entry_id, artifact)
        return latest

    async def add_user_profile(
        self,
        *,
        user_id: str,
        source_entry_count: int,
        payload_json: dict,
        algorithm_version: str,
        generated_at: datetime,
    ) -> UserProfileArtifactModel:
        artifact = UserProfileArtifactModel(
            user_id=user_id,
            source_entry_count=source_entry_count,
            payload_json=payload_json,
            algorithm_version=algorithm_version,
            generated_at=generated_at,
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def latest_user_profile(self, user_id: str) -> UserProfileArtifactModel | None:
        stmt = (
            select(UserProfileArtifactModel)
            .where(UserProfileArtifactModel.user_id == user_id)
            .order_by(desc(UserProfileArtifactModel.generated_at))  # type: ignore[reportArgumentType]
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_restaurant_profile(
        self,
        *,
        restaurant_id: str,
        payload_json: dict,
        algorithm_version: str,
        generated_at: datetime,
    ) -> RestaurantProfileArtifactModel:
        artifact = RestaurantProfileArtifactModel(
            restaurant_id=restaurant_id,
            payload_json=payload_json,
            algorithm_version=algorithm_version,
            generated_at=generated_at,
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def latest_restaurant_profile(
        self, restaurant_id: str
    ) -> RestaurantProfileArtifactModel | None:
        stmt = (
            select(RestaurantProfileArtifactModel)
            .where(RestaurantProfileArtifactModel.restaurant_id == restaurant_id)
            .order_by(desc(RestaurantProfileArtifactModel.generated_at))  # type: ignore[reportArgumentType]
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def latest_restaurant_profiles(
        self, restaurant_ids: list[str]
    ) -> dict[str, RestaurantProfileArtifactModel]:
        if not restaurant_ids:
            return {}
        stmt = (
            select(RestaurantProfileArtifactModel)
            .where(RestaurantProfileArtifactModel.restaurant_id.in_(restaurant_ids))  # type: ignore[attr-defined]
            .order_by(desc(RestaurantProfileArtifactModel.generated_at))  # type: ignore[reportArgumentType]
        )
        result = await self.db.execute(stmt)
        latest: dict[str, RestaurantProfileArtifactModel] = {}
        for artifact in result.scalars().all():
            latest.setdefault(artifact.restaurant_id, artifact)
        return latest
