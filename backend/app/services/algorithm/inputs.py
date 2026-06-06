from __future__ import annotations

from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.schemas.algorithm import DiaryEntryInput, RestaurantInput
from app.services.algorithm.taxonomy import normalize_public_restaurant_category
from app.utils.geo import haversine_m
from app.utils.time import as_utc


def restaurant_input_from_model(
    restaurant: RestaurantModel,
    *,
    lat: float | None = None,
    lng: float | None = None,
    is_bookmarked: bool = False,
) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant.id,
        name=restaurant.name,
        category=normalize_public_restaurant_category(restaurant.category),
        signature_dish=restaurant.signature_dish,
        rating=restaurant.rating,
        rating_count=restaurant.rating_count,
        distance_m=_distance_m(restaurant, lat, lng),
        thumbnail_url=restaurant.thumbnail_url,
        thumbnail_tone=restaurant.thumbnail_tone,
        thumbnail_label=restaurant.thumbnail_label,
        tags=list(restaurant.tags or []),
        lat=restaurant.lat,
        lng=restaurant.lng,
        kakao_id=restaurant.kakao_id,
        neighborhood=restaurant.neighborhood,
        is_bookmarked=is_bookmarked,
    )


def diary_entry_input_from_models(
    entry: EntryModel,
    restaurant: RestaurantModel,
    *,
    lat: float | None = None,
    lng: float | None = None,
    is_bookmarked: bool = False,
) -> DiaryEntryInput:
    return DiaryEntryInput(
        id=entry.id,
        user_id=entry.user_id,
        captured_at=as_utc(entry.captured_at),
        restaurant=restaurant_input_from_model(
            restaurant,
            lat=lat,
            lng=lng,
            is_bookmarked=is_bookmarked,
        ),
        rating=entry.rating,
        note=entry.note,
        image_labels=list(entry.ai_tags or []),
    )


def _distance_m(restaurant: RestaurantModel, lat: float | None, lng: float | None) -> int:
    if lat is None or lng is None:
        return 0
    return haversine_m(lat, lng, restaurant.lat, restaurant.lng)
