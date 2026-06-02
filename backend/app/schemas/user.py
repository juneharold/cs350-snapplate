from __future__ import annotations

from app.models.user import UserModel
from app.schemas.base import BaseSchema
from app.utils.time import as_utc


class UserStatsInfo(BaseSchema):
    entries_count: int
    places_count: int
    bookmarks_count: int
    avg_rating: float


class MeInfo(BaseSchema):
    id: str
    email: str
    nickname: str | None = None
    profile_image_url: str | None = None
    taste_type: str | None = None
    stats: UserStatsInfo
    created_at: str

    @classmethod
    def from_model(cls, m: UserModel, stats: UserStatsInfo) -> "MeInfo":
        return cls(
            id=m.id,
            email=m.email,
            nickname=m.nickname,
            profile_image_url=m.profile_image_url,
            taste_type=m.taste_type,
            stats=stats,
            created_at=as_utc(m.created_at).isoformat(),
        )
