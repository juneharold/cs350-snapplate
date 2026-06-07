# pyright: reportArgumentType=false
from __future__ import annotations

from sqlalchemy import func, select

from app.config.http_errors import AppError
from app.config.lifespan import Context
from app.dto.auth import UpdateUserData
from app.models.bookmark import BookmarkModel
from app.models.entry import EntryModel
from app.repositories.user import UserRepository
from app.schemas.user import MeInfo, UserStatsInfo
from app.services.s3.storage import StorageService

_NICKNAME_MAX = 30


class UserService:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.users = UserRepository(ctx.db_session)
        self.storage = StorageService(ctx.s3)

    async def get_me(self, user_id: str) -> MeInfo:
        user = await self.users.find(user_id)
        if user is None:
            raise AppError(404, "not_found", "User not found.")
        stats = await self._stats(user_id)
        profile_image_url = await self._profile_image_url(user.profile_image_url)
        return MeInfo.from_model(user, stats, profile_image_url=profile_image_url)

    async def update_me(self, user_id: str, nickname: str | None) -> MeInfo:
        user = await self.users.find(user_id)
        if user is None:
            raise AppError(404, "not_found", "User not found.")
        changes = UpdateUserData()
        if nickname is not None:
            nickname = nickname.strip()
            if not nickname:
                raise AppError(400, "nickname_empty", "Nickname can't be empty.", "nickname")
            if len(nickname) > _NICKNAME_MAX:
                raise AppError(400, "nickname_too_long", "Nickname is too long.", "nickname")
            changes.nickname = nickname
        # First profile edit marks onboarding complete.
        changes.is_onboarded = True
        user = await self.users.update(user, changes)
        profile_image_url = await self._profile_image_url(user.profile_image_url)
        return MeInfo.from_model(
            user,
            await self._stats(user_id),
            profile_image_url=profile_image_url,
        )

    async def _profile_image_url(self, key: str | None) -> str | None:
        return await self.storage.signed_url(key) if key else None

    async def _stats(self, user_id: str) -> UserStatsInfo:
        db = self.ctx.db_session
        active = (EntryModel.user_id == user_id) & (EntryModel.deleted_at.is_(None))  # type: ignore[union-attr]

        entries_count = (
            await db.execute(select(func.count()).select_from(EntryModel).where(active))
        ).scalar() or 0
        places_count = (
            await db.execute(
                select(func.count(func.distinct(EntryModel.restaurant_id))).where(active)
            )
        ).scalar() or 0
        avg_rating = (
            await db.execute(
                select(func.avg(EntryModel.rating)).where(
                    active & (EntryModel.rating.is_not(None))  # type: ignore[union-attr]
                )
            )
        ).scalar()
        bookmarks_count = (
            await db.execute(
                select(func.count())
                .select_from(BookmarkModel)
                .where(BookmarkModel.user_id == user_id)
            )
        ).scalar() or 0

        return UserStatsInfo(
            entries_count=int(entries_count),
            places_count=int(places_count),
            bookmarks_count=int(bookmarks_count),
            avg_rating=round(float(avg_rating), 1) if avg_rating is not None else 0.0,
        )
