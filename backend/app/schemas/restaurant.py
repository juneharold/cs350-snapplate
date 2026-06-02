from __future__ import annotations

from app.models.restaurant import RestaurantModel
from app.schemas.base import BaseSchema
from app.types.restaurant import FoodTone


class RestaurantSummaryInfo(BaseSchema):
    id: str
    name: str
    category: str
    signature_dish: str | None = None
    rating: float
    rating_count: int
    distance_m: int
    thumbnail_url: str | None = None
    thumbnail_tone: FoodTone
    thumbnail_label: str
    tags: list[str]
    lat: float
    lng: float
    kakao_id: str
    neighborhood: str
    is_bookmarked: bool = False

    @classmethod
    def from_model(
        cls, m: RestaurantModel, *, distance_m: int = 0, is_bookmarked: bool = False
    ) -> "RestaurantSummaryInfo":
        return cls(
            id=m.id,
            name=m.name,
            category=m.category,
            signature_dish=m.signature_dish,
            rating=m.rating,
            rating_count=m.rating_count,
            distance_m=distance_m,
            thumbnail_url=m.thumbnail_url,
            thumbnail_tone=m.thumbnail_tone,
            thumbnail_label=m.thumbnail_label,
            tags=list(m.tags or []),
            lat=m.lat,
            lng=m.lng,
            kakao_id=m.kakao_id,
            neighborhood=m.neighborhood,
            is_bookmarked=is_bookmarked,
        )


class PopularDishInfo(BaseSchema):
    name: str
    price: str
    photo_url: str | None = None
    tone: FoodTone


class PersonalizationInfo(BaseSchema):
    reason: str | None = None
    user_visited_count: int = 0
    user_first_visit: str | None = None
    user_last_visit: str | None = None


class RestaurantDetailInfo(RestaurantSummaryInfo):
    address: str | None = None
    price_range: str | None = None
    hours: str | None = None
    phone: str | None = None
    kakao_place_url: str
    popular_dishes: list[PopularDishInfo] = []
    personalization: PersonalizationInfo

    @classmethod
    def from_detail(
        cls,
        m: RestaurantModel,
        *,
        distance_m: int = 0,
        is_bookmarked: bool = False,
        personalization: PersonalizationInfo | None = None,
    ) -> "RestaurantDetailInfo":
        base = RestaurantSummaryInfo.from_model(
            m, distance_m=distance_m, is_bookmarked=is_bookmarked
        ).model_dump()
        popular = (
            [PopularDishInfo(name=m.signature_dish, price="", tone=m.thumbnail_tone)]
            if m.signature_dish
            else []
        )
        return cls(
            **base,
            address=m.address,
            price_range=m.price_range,
            hours=m.hours,
            phone=m.phone,
            kakao_place_url=f"https://place.map.kakao.com/{m.kakao_id}",
            popular_dishes=popular,
            personalization=personalization or PersonalizationInfo(),
        )


class SearchResultInfo(RestaurantSummaryInfo):
    match_score: float


class RecommendedRestaurantInfo(RestaurantSummaryInfo):
    reason: str
