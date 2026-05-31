from __future__ import annotations

from app.schemas.base import BaseSchema
from app.schemas.restaurant import RestaurantSummaryInfo


class BookmarkInfo(BaseSchema):
    id: str
    restaurant_id: str
    restaurant: RestaurantSummaryInfo
    bookmarked_at: str
