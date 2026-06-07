from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import insert
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
        commit: bool = True,
    ) -> EntryProfileArtifactModel:
        stmt = (
            insert(EntryProfileArtifactModel)
            .values(
                entry_id=entry_id,
                user_id=user_id,
                payload_json=payload_json,
                algorithm_version=algorithm_version,
                generated_at=generated_at,
            )
            .on_conflict_do_update(
                index_elements=["entry_id"],
                set_={
                    "user_id": user_id,
                    "payload_json": payload_json,
                    "algorithm_version": algorithm_version,
                    "generated_at": generated_at,
                },
            )
            .returning(EntryProfileArtifactModel)
        )
        result = await self.db.execute(stmt)
        artifact = result.scalar_one()
        if commit:
            await self.db.commit()
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
        long_term_embedding: Sequence[float],
        short_term_embedding: Sequence[float],
        algorithm_version: str,
        generated_at: datetime,
        commit: bool = True,
    ) -> UserProfileArtifactModel:
        stmt = (
            insert(UserProfileArtifactModel)
            .values(
                user_id=user_id,
                source_entry_count=source_entry_count,
                payload_json=payload_json,
                long_term_embedding=list(long_term_embedding),
                short_term_embedding=list(short_term_embedding),
                algorithm_version=algorithm_version,
                generated_at=generated_at,
            )
            .on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "source_entry_count": source_entry_count,
                    "payload_json": payload_json,
                    "long_term_embedding": list(long_term_embedding),
                    "short_term_embedding": list(short_term_embedding),
                    "algorithm_version": algorithm_version,
                    "generated_at": generated_at,
                },
            )
            .returning(UserProfileArtifactModel)
        )
        result = await self.db.execute(stmt)
        artifact = result.scalar_one()
        if commit:
            await self.db.commit()
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
        embedding: Sequence[float],
        algorithm_version: str,
        generated_at: datetime,
        commit: bool = True,
    ) -> RestaurantProfileArtifactModel:
        stmt = (
            insert(RestaurantProfileArtifactModel)
            .values(
                restaurant_id=restaurant_id,
                payload_json=payload_json,
                embedding=list(embedding),
                algorithm_version=algorithm_version,
                generated_at=generated_at,
            )
            .on_conflict_do_update(
                index_elements=["restaurant_id"],
                set_={
                    "payload_json": payload_json,
                    "embedding": list(embedding),
                    "algorithm_version": algorithm_version,
                    "generated_at": generated_at,
                },
            )
            .returning(RestaurantProfileArtifactModel)
        )
        result = await self.db.execute(stmt)
        artifact = result.scalar_one()
        if commit:
            await self.db.commit()
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

    async def nearest_restaurant_profiles(
        self,
        query_embedding: Sequence[float],
        *,
        candidate_restaurant_ids: Sequence[str] | None = None,
        limit: int,
    ) -> list[tuple[RestaurantProfileArtifactModel, float]]:
        # Upserts plus the restaurant_id UNIQUE constraint keep one profile row per restaurant.
        distance = RestaurantProfileArtifactModel.embedding.cosine_distance(
            list(query_embedding)
        ).label("distance")
        stmt = select(RestaurantProfileArtifactModel, distance)
        if candidate_restaurant_ids is not None:
            stmt = stmt.where(
                RestaurantProfileArtifactModel.restaurant_id.in_(  # type: ignore[attr-defined]
                    list(candidate_restaurant_ids)
                )
            )
        stmt = stmt.order_by(distance.asc()).limit(limit)
        result = await self.db.execute(stmt)
        return [(artifact, float(distance)) for artifact, distance in result.all()]
