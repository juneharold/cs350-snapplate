from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.recommendation_exposure import RecommendationExposureModel


class RecommendationExposureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def latest_restaurant_ids(self, user_id: str, limit: int) -> list[str]:
        stmt = (
            select(RecommendationExposureModel.restaurant_id)
            .where(RecommendationExposureModel.user_id == user_id)
            .order_by(desc(RecommendationExposureModel.shown_at))  # type: ignore[reportArgumentType]
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_many(
        self,
        *,
        user_id: str,
        restaurant_reasons: dict[str, str],
        shown_at: datetime,
    ) -> None:
        for restaurant_id, reason in restaurant_reasons.items():
            self.db.add(
                RecommendationExposureModel(
                    user_id=user_id,
                    restaurant_id=restaurant_id,
                    shown_at=shown_at,
                    reason=reason,
                )
            )
        await self.db.commit()
