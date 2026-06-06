from __future__ import annotations

from algorithm.schemas import DiaryEntryInput, RestaurantInput
from sqlalchemy import select

from app.config.lifespan import Context
from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.utils.time import as_utc


class DiaryInputService:
    def __init__(self, ctx: Context):
        self.db = ctx.db_session

    async def for_user(self, user_id: str) -> list[DiaryEntryInput]:
        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)
            .where(EntryModel.user_id == user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
        )
        rows = (await self.db.execute(stmt)).all()
        return [self._to_input(entry, r) for entry, r in rows]

    @staticmethod
    def _to_input(entry: EntryModel, r: RestaurantModel) -> DiaryEntryInput:
        return DiaryEntryInput(
            id=entry.id,
            user_id=entry.user_id,
            captured_at=as_utc(entry.captured_at),
            restaurant=RestaurantInput(
                id=r.id,
                name=r.name,
                category=r.category,
                signature_dish=r.signature_dish,
                rating=r.rating,
                rating_count=r.rating_count,
                distance_m=0,
                thumbnail_url=r.thumbnail_url,
                thumbnail_tone=r.thumbnail_tone,
                thumbnail_label=r.thumbnail_label,
                tags=list(r.tags or []),
                lat=r.lat,
                lng=r.lng,
                kakao_id=r.kakao_id,
                neighborhood=r.neighborhood,
                is_bookmarked=False,
            ),
            rating=entry.rating,
            note=entry.note,
            image_labels=list(entry.ai_tags or []),
        )
