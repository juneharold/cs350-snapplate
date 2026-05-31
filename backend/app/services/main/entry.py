from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, asc, desc, func, or_, select

from app.config.http_errors import AppError, NotFoundError, OwnershipError
from app.config.lifespan import Context
from app.dto.entry import EntryListStats, UpdateEntryData
from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.repositories.entry import EntryMediaRepository, EntryRepository
from app.repositories.media import MediaRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.entry import (
    EntryDetailInfo,
    EntryMediaItem,
    EntryRestaurantBrief,
    EntrySummaryInfo,
    EntryVisitHistoryItem,
)
from app.schemas.restaurant import RestaurantSummaryInfo
from app.services.s3.storage import StorageService
from app.utils.time import as_utc, day_label, meal_period, utcnow

_EXCERPT = 100
_NOTE_MAX = 500


class EntryService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.repo = EntryRepository(self.db)
        self.entry_media = EntryMediaRepository(self.db)
        self.media = MediaRepository(self.db)
        self.restaurants = RestaurantRepository(self.db)
        self.storage = StorageService(ctx.s3)

    async def list(
        self,
        user_id: str,
        sort: str,
        q: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
    ) -> tuple[list[EntrySummaryInfo], EntryListStats]:
        conds = [EntryModel.user_id == user_id, EntryModel.deleted_at.is_(None)]  # type: ignore[union-attr]
        if date_from:
            conds.append(EntryModel.captured_at >= as_utc(date_from))
        if date_to:
            conds.append(EntryModel.captured_at <= as_utc(date_to))

        stmt = (
            select(EntryModel, RestaurantModel)
            .join(RestaurantModel, EntryModel.restaurant_id == RestaurantModel.id)
            .where(and_(*conds))
        )
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(EntryModel.note.ilike(like), RestaurantModel.name.ilike(like))  # type: ignore[attr-defined]
            )
        stmt = stmt.order_by(*self._order(sort)).limit(limit)

        rows = (await self.db.execute(stmt)).all()
        items = [await self._summary(e, r) for e, r in rows]
        stats = await self._stats(user_id)
        return items, stats

    async def get(self, user_id: str, entry_id: str) -> EntryDetailInfo:
        entry = await self._owned(user_id, entry_id)
        restaurant = await self.restaurants.find(entry.restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurant not found.")

        media_items: list[EntryMediaItem] = []
        for link in await self.entry_media.for_entry(entry.id):
            m = await self.media.find(link.media_id)
            if m:
                url, _ = await self.storage.signed_urls_for(m.storage_key, m.variant_keys)
                media_items.append(
                    EntryMediaItem(
                        id=m.id, url=url, is_cover=link.is_cover, tone=m.tone, label=m.label
                    )
                )

        history = await self._visit_history(user_id, entry.restaurant_id, exclude=entry.id)
        return EntryDetailInfo(
            id=entry.id,
            captured_at=as_utc(entry.captured_at).isoformat(),
            meal_period=entry.meal_period or meal_period(as_utc(entry.captured_at)),
            media=media_items,
            rating=entry.rating,
            note=entry.note,
            ai_tags=list(entry.ai_tags or []),
            restaurant=RestaurantSummaryInfo.from_model(restaurant),
            user_visit_history=history,
            created_at=as_utc(entry.created_at).isoformat(),
        )

    async def update(
        self, user_id: str, entry_id: str, rating: float | None, note: str | None
    ) -> EntryDetailInfo:
        entry = await self._owned(user_id, entry_id)
        changes = UpdateEntryData()
        if rating is not None:
            if not (0.5 <= rating <= 5.0):
                raise AppError(400, "invalid_rating", "Rating must be 0.5–5.0.", "rating")
            changes.rating = rating
        if note is not None:
            note = note.strip()
            if not note:
                raise AppError(400, "note_required", "Note can't be empty.", "note")
            if len(note) > _NOTE_MAX:
                raise AppError(400, "note_too_long", "Note is too long.", "note")
            changes.note = note
        await self.repo.update(entry, changes)
        return await self.get(user_id, entry_id)

    async def delete(self, user_id: str, entry_id: str) -> None:
        entry = await self._owned(user_id, entry_id)
        await self.repo.update(entry, UpdateEntryData(deleted_at=utcnow()))

    # ── helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _order(sort: str):
        if sort == "rating_desc":
            return [desc(EntryModel.rating), desc(EntryModel.captured_at)]
        # 'distance' has no stored coord on entries → fall back to recency
        return [desc(EntryModel.captured_at), desc(EntryModel.id)]

    async def _owned(self, user_id: str, entry_id: str) -> EntryModel:
        entry = await self.repo.find(entry_id)
        if entry is None or entry.deleted_at is not None:
            raise NotFoundError("Entry not found.")
        if entry.user_id != user_id:
            raise OwnershipError("Entry not found.")
        return entry

    async def _summary(self, entry: EntryModel, restaurant: RestaurantModel) -> EntrySummaryInfo:
        cover = await self.media.find(entry.cover_media_id)
        media_count = len(list(await self.entry_media.for_entry(entry.id)))
        excerpt = entry.note[:_EXCERPT] + ("…" if len(entry.note) > _EXCERPT else "")
        cover_thumb_url = None
        if cover:
            _, cover_thumb_url = await self.storage.signed_urls_for(
                cover.storage_key, cover.variant_keys
            )
        return EntrySummaryInfo(
            id=entry.id,
            captured_at=as_utc(entry.captured_at).isoformat(),
            day_label=day_label(entry.captured_at),
            cover_media_url=cover_thumb_url,
            cover_media_tone=cover.tone if cover else "bone",  # type: ignore[arg-type]
            cover_media_label=cover.label if cover else "",
            media_count=media_count,
            restaurant=EntryRestaurantBrief(
                id=restaurant.id,
                name=restaurant.name,
                signature_dish=restaurant.signature_dish,
                neighborhood=restaurant.neighborhood,
            ),
            rating=entry.rating,
            note_excerpt=excerpt,
        )

    async def _visit_history(
        self, user_id: str, restaurant_id: str, exclude: str
    ) -> list[EntryVisitHistoryItem]:
        stmt = (
            select(EntryModel)
            .where(
                EntryModel.user_id == user_id,
                EntryModel.restaurant_id == restaurant_id,
                EntryModel.id != exclude,
                EntryModel.deleted_at.is_(None),  # type: ignore[union-attr]
            )
            .order_by(desc(EntryModel.captured_at))
            .limit(10)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            EntryVisitHistoryItem(
                entry_id=e.id, captured_at=as_utc(e.captured_at).isoformat(), rating=e.rating
            )
            for e in rows
        ]

    async def _stats(self, user_id: str) -> EntryListStats:
        active = and_(EntryModel.user_id == user_id, EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]
        entries_total = (await self.db.execute(select(func.count()).select_from(EntryModel).where(active))).scalar() or 0
        places_total = (await self.db.execute(select(func.count(func.distinct(EntryModel.restaurant_id))).where(active))).scalar() or 0
        avg = (await self.db.execute(select(func.avg(EntryModel.rating)).where(and_(active, EntryModel.rating.is_not(None))))).scalar()  # type: ignore[union-attr]
        now = utcnow()
        this_month = (
            await self.db.execute(
                select(func.count()).select_from(EntryModel).where(
                    and_(
                        active,
                        func.extract("year", EntryModel.captured_at) == now.year,
                        func.extract("month", EntryModel.captured_at) == now.month,
                    )
                )
            )
        ).scalar() or 0
        return EntryListStats(
            entries_total=int(entries_total),
            places_total=int(places_total),
            this_month=int(this_month),
            avg_rating=round(float(avg), 1) if avg is not None else 0.0,
        )
