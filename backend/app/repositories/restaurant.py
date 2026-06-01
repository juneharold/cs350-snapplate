from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select

from app.dto.restaurant import KakaoRestaurantData, UpdateRestaurantData
from app.models.restaurant import RestaurantModel
from app.repositories.base import BaseRepository


class RestaurantRepository(
    BaseRepository[RestaurantModel, KakaoRestaurantData, UpdateRestaurantData]
):
    model = RestaurantModel

    async def find_by_kakao_id(self, kakao_id: str) -> RestaurantModel | None:
        return await self.find_by(kakao_id=kakao_id)

    async def upsert_many(self, items: list[KakaoRestaurantData]) -> list[RestaurantModel]:
        """Upsert restaurants dedupe-on-kakao_id. We don't use the generic
        batch_upsert here because rows carry a generated text PK; instead we
        upsert one-by-one (find-or-create), which is fine at v1 volumes."""
        out: list[RestaurantModel] = []
        for item in items:
            existing = await self.find_by_kakao_id(item.kakao_id)
            if existing is None:
                out.append(await self.create(item))
            else:
                out.append(
                    await self.update(
                        existing,
                        UpdateRestaurantData(
                            rating=item.rating,
                            rating_count=item.rating_count,
                            neighborhood=item.neighborhood or existing.neighborhood,
                            raw_payload=item.raw_payload,
                        ),
                    )
                )
        return out

    async def search_text(
        self, q: str, category: str | None, min_rating: float | None, limit: int
    ) -> Sequence[RestaurantModel]:
        """Substring search across name/dish/category/neighborhood. (Postgres FTS/GIN
        is the production path; ILIKE is correct + adequate at v1 row counts and
        works for Korean text without a tsvector config.)"""
        like = f"%{q}%"
        conds = [
            RestaurantModel.deleted_at.is_(None),  # type: ignore[union-attr]
            or_(
                RestaurantModel.name.ilike(like),  # type: ignore[attr-defined]
                RestaurantModel.signature_dish.ilike(like),  # type: ignore[attr-defined]
                RestaurantModel.category.ilike(like),  # type: ignore[attr-defined]
                RestaurantModel.neighborhood.ilike(like),  # type: ignore[attr-defined]
            ),
        ]
        if category:
            conds.append(RestaurantModel.category == category)
        if min_rating is not None:
            conds.append(RestaurantModel.rating >= min_rating)
        stmt = select(RestaurantModel).where(*conds).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_active(
        self, category: str | None, min_rating: float | None, limit: int = 200
    ) -> Sequence[RestaurantModel]:
        conds = [RestaurantModel.deleted_at.is_(None)]  # type: ignore[union-attr]
        if category:
            conds.append(RestaurantModel.category == category)
        if min_rating is not None:
            conds.append(RestaurantModel.rating >= min_rating)
        stmt = select(RestaurantModel).where(*conds).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
