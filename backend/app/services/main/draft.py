from __future__ import annotations

from datetime import timedelta

from app.config.http_errors import AppError, NotFoundError, OwnershipError
from app.config.lifespan import Context
from app.dto.draft import CreateDraftData, UpdateDraftData
from app.models.draft import DraftModel
from app.models.entry import EntryMediaModel, EntryModel
from app.repositories.draft import DraftMediaRepository, DraftRepository
from app.repositories.media import MediaRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.draft import (
    DraftDetailInfo,
    DraftMediaItem,
    DraftRestaurantBrief,
    DraftSummaryInfo,
)
from app.schemas.restaurant import RestaurantSummaryInfo
from app.services.kakao.client import KakaoService
from app.services.main.taste import TasteService
from app.services.s3.storage import StorageService
from app.types.draft import DraftStatus
from app.utils.ids import entry_id
from app.utils.time import as_utc, captured_relative, meal_period, utcnow

_REMIND_AFTER = timedelta(hours=1)
_NOTE_MAX = 500


class DraftService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.db = ctx.db_session
        self.repo = DraftRepository(self.db)
        self.draft_media = DraftMediaRepository(self.db)
        self.media = MediaRepository(self.db)
        self.restaurants = RestaurantRepository(self.db)
        self.kakao = KakaoService(ctx.http_client)
        self.storage = StorageService(ctx.s3)

    # ── create ─────────────────────────────────────────────────────────────────
    async def create(
        self,
        user_id: str,
        media_ids: list[str],
        cover_media_id: str | None,
        captured_at,
        lat: float | None,
        lng: float | None,
        restaurant_id: str | None,
        restaurant_suggested: bool | None,
    ) -> DraftDetailInfo:
        captured = as_utc(captured_at) if captured_at else utcnow()
        if captured > utcnow():
            raise AppError(400, "invalid_captured_at", "Capture time can't be in the future.")

        if not media_ids:
            raise AppError(400, "media_required", "At least one photo is required.", "media_ids")
        # Every linked media must belong to the caller. Otherwise a guessed id
        # lets someone attach another user's photo and read its signed URL via
        # _detail (REQ-SEC-004 / REQ-SEC-009).
        owned = await self.media.owned_ids(media_ids, user_id)
        missing = [mid for mid in media_ids if mid not in owned]
        if missing:
            raise AppError(404, "media_not_found", "Media not found.", "media_ids")
        if cover_media_id is not None and cover_media_id not in owned:
            raise AppError(404, "media_not_found", "Media not found.", "cover_media_id")
        cover = cover_media_id or media_ids[0]

        suggested = bool(restaurant_suggested)
        # GPS → restaurant suggestion when none provided.
        if restaurant_id is None and lat is not None and lng is not None:
            restaurant_id, suggested = await self._suggest_restaurant(lat, lng)

        status = DraftStatus.NEEDS_PLACE if restaurant_id is None else DraftStatus.WAITING

        draft = await self.repo.create(
            CreateDraftData(
                user_id=user_id,
                status=status,
                cover_media_id=cover,
                captured_at=captured,
                lat=lat,
                lng=lng,
                restaurant_id=restaurant_id,
                restaurant_suggested=suggested,
                remind_at=captured + _REMIND_AFTER,
            )
        )
        for i, mid in enumerate(media_ids):
            await self.draft_media.add(draft.id, mid, position=i, is_cover=(mid == cover))

        return await self._detail(draft)

    async def _suggest_restaurant(self, lat: float, lng: float) -> tuple[str | None, bool]:
        """Find the nearest restaurant via Kakao, upsert it, return its internal id."""
        try:
            candidates = await self.kakao.category_search(lat, lng, radius_m=500)
        except Exception:
            return None, False
        if not candidates:
            return None, False
        nearest = candidates[0]
        nearest.neighborhood = await self.kakao.neighborhood_for(lat, lng)
        rows = await self.restaurants.upsert_many([nearest])
        return (rows[0].id, True) if rows else (None, False)

    # ── read ───────────────────────────────────────────────────────────────────
    async def get(self, user_id: str, draft_id: str) -> DraftDetailInfo:
        draft = await self._owned(user_id, draft_id)
        return await self._detail(draft)

    async def list(
        self, user_id: str, status: str | None, limit: int
    ) -> tuple[list[DraftSummaryInfo], int]:
        rows = list(await self.repo.list_for_user(user_id, status, limit))
        items = [await self._summary(d) for d in rows]
        return items, len(items)

    # ── update ─────────────────────────────────────────────────────────────────
    async def update(
        self, user_id: str, draft_id: str, restaurant_id, captured_at, cover_media_id
    ) -> DraftDetailInfo:
        draft = await self._owned(user_id, draft_id)
        changes = UpdateDraftData()
        if restaurant_id is not None:
            changes.restaurant_id = restaurant_id
            changes.restaurant_suggested = False
            if draft.status == DraftStatus.NEEDS_PLACE:
                changes.status = DraftStatus.WAITING
        if captured_at is not None:
            changes.captured_at = as_utc(captured_at)
        if cover_media_id is not None:
            # The new cover must be the caller's own media (REQ-SEC-004).
            if not await self.media.owned_ids([cover_media_id], user_id):
                raise AppError(404, "media_not_found", "Media not found.", "cover_media_id")
            changes.cover_media_id = cover_media_id
        draft = await self.repo.update(draft, changes)
        return await self._detail(draft)

    # ── delete ─────────────────────────────────────────────────────────────────
    async def delete(self, user_id: str, draft_id: str) -> None:
        draft = await self._owned(user_id, draft_id)
        await self.repo.delete(draft.id)  # draft_media cascades

    # ── finalize (THE transaction) ─────────────────────────────────────────────
    async def finalize(
        self,
        user_id: str,
        draft_id: str,
        note: str,
        rating: float | None,
        restaurant_id: str | None,
    ) -> str:
        draft = await self._owned(user_id, draft_id)

        note = (note or "").strip()
        if not note:
            raise AppError(400, "note_required", "A note is required.", "note")
        if len(note) > _NOTE_MAX:
            raise AppError(400, "note_too_long", "Note is too long (max 500).", "note")
        if rating is not None and not (0.5 <= rating <= 5.0):
            raise AppError(400, "invalid_rating", "Rating must be 0.5–5.0.", "rating")

        resolved_restaurant = restaurant_id or draft.restaurant_id
        if resolved_restaurant is None:
            raise AppError(400, "restaurant_required", "Pick a restaurant first.", "restaurant_id")
        if as_utc(draft.captured_at) > utcnow():
            raise AppError(400, "invalid_captured_at", "Capture time can't be in the future.")

        links = list(await self.draft_media.for_draft(draft.id))
        new_entry_id = entry_id()

        # ── single transaction: build entry + copy media + delete draft ──
        entry = EntryModel(
            id=new_entry_id,
            user_id=user_id,
            draft_id=draft.id,
            restaurant_id=resolved_restaurant,
            cover_media_id=draft.cover_media_id,
            captured_at=as_utc(draft.captured_at),
            meal_period=meal_period(as_utc(draft.captured_at)),
            rating=rating,
            note=note,
            ai_tags=[],
        )
        self.db.add(entry)
        # Flush so the entry row exists before entry_media FKs reference it
        # (still one transaction — flush emits the INSERT without committing).
        await self.db.flush()
        for link in links:
            self.db.add(
                EntryMediaModel(
                    entry_id=new_entry_id,
                    media_id=link.media_id,
                    position=link.position,
                    is_cover=link.is_cover,
                )
            )
        # Delete the draft (draft_media cascades on the same commit).
        draft_obj = await self.db.get(DraftModel, draft.id)
        if draft_obj is not None:
            await self.db.delete(draft_obj)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        # ── post-commit: recompute taste inline (separate concern, own txn) ──
        await TasteService(self.ctx).recompute_and_store(user_id)
        return new_entry_id

    # ── helpers ────────────────────────────────────────────────────────────────
    async def _owned(self, user_id: str, draft_id: str) -> DraftModel:
        draft = await self.repo.find(draft_id)
        if draft is None:
            raise NotFoundError("Draft not found.")
        if draft.user_id != user_id:
            raise OwnershipError("Draft not found.")
        return draft

    async def _summary(self, draft: DraftModel) -> DraftSummaryInfo:
        links = list(await self.draft_media.for_draft(draft.id))
        cover = await self.media.find(draft.cover_media_id)
        cover_thumb_url = None
        if cover:
            _, cover_thumb_url = await self.storage.signed_urls_for(
                cover.storage_key, cover.variant_keys
            )
        restaurant = None
        if draft.restaurant_id:
            r = await self.restaurants.find(draft.restaurant_id)
            if r:
                restaurant = DraftRestaurantBrief(id=r.id, name=r.name, neighborhood=r.neighborhood)
        return DraftSummaryInfo(
            id=draft.id,
            status=draft.status,
            captured_at=as_utc(draft.captured_at).isoformat(),
            captured_relative=captured_relative(draft.captured_at),
            cover_media_url=cover_thumb_url,
            cover_media_tone=cover.tone if cover else "bone",  # type: ignore[arg-type]
            cover_media_label=cover.label if cover else "",
            media_count=len(links),
            restaurant=restaurant,
            restaurant_suggested=draft.restaurant_suggested,
            remind_at=as_utc(draft.remind_at).isoformat() if draft.remind_at else None,
        )

    async def _detail(self, draft: DraftModel) -> DraftDetailInfo:
        links = list(await self.draft_media.for_draft(draft.id))
        media_items: list[DraftMediaItem] = []
        for link in links:
            m = await self.media.find(link.media_id)
            if m is None:
                continue
            url, thumb_url = await self.storage.signed_urls_for(m.storage_key, m.variant_keys)
            media_items.append(
                DraftMediaItem(
                    id=m.id,
                    url=url,
                    thumbnail_url=thumb_url,
                    is_cover=link.is_cover,
                    tone=m.tone,
                    label=m.label,
                )
            )
        restaurant = None
        if draft.restaurant_id:
            r = await self.restaurants.find(draft.restaurant_id)
            if r:
                restaurant = RestaurantSummaryInfo.from_model(r)
        return DraftDetailInfo(
            id=draft.id,
            status=draft.status,
            media=media_items,
            captured_at=as_utc(draft.captured_at).isoformat(),
            lat=draft.lat,
            lng=draft.lng,
            restaurant=restaurant,
            restaurant_suggested=draft.restaurant_suggested,
            created_at=as_utc(draft.created_at).isoformat(),
            remind_at=as_utc(draft.remind_at).isoformat() if draft.remind_at else None,
        )
