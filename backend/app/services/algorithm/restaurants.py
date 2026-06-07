from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from app.config.logger import create_logger
from app.models.restaurant import RestaurantModel
from app.repositories.algorithm_artifact import AlgorithmArtifactRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.algorithm import KakaoRestaurantMetadata, RestaurantProfileArtifact
from app.services.algorithm.providers import ProfileProvider
from app.services.algorithm.restaurant_profiling import profile_kakao_restaurant
from app.utils.restaurant_taxonomy import (
    UnknownRestaurantCategoryError,
    normalize_public_restaurant_category,
)
from app.utils.time import as_utc, utcnow

logger = create_logger(__name__)

_RESTAURANT_PROFILE_FRESHNESS_WINDOW = timedelta(hours=1)


def metadata_from_restaurant_model(restaurant: RestaurantModel) -> KakaoRestaurantMetadata:
    raw_payload = restaurant.raw_payload or {}
    category = normalize_public_restaurant_category(
        restaurant.category,
        raw_payload.get("category_name"),
    )
    return KakaoRestaurantMetadata(
        id=restaurant.id,
        place_name=restaurant.name,
        name=restaurant.name,
        category_name=category,
        category=category,
        category_group_name=raw_payload.get("category_group_name"),
        address_name=restaurant.address or raw_payload.get("address_name"),
        road_address_name=raw_payload.get("road_address_name") or restaurant.address,
        x=restaurant.lng,
        y=restaurant.lat,
        place_url=restaurant.thumbnail_url,
        phone=restaurant.phone,
        distance=raw_payload.get("distance"),
        signature_dish=restaurant.signature_dish,
        popular_dishes=[],
        tags=list(restaurant.tags or []),
        rating=restaurant.rating,
        rating_count=restaurant.rating_count,
    )


def build_restaurant_profile_artifact(
    restaurant: RestaurantModel,
    *,
    generated_at: datetime,
    profile_provider: ProfileProvider,
) -> RestaurantProfileArtifact:
    return profile_kakao_restaurant(
        metadata_from_restaurant_model(restaurant),
        generated_at=generated_at,
        profile_provider=profile_provider,
    )


async def profile_restaurants(
    internal: Any,
    restaurant_ids: Sequence[str],
    *,
    profile_provider: ProfileProvider,
) -> None:
    if not restaurant_ids:
        return
    async with internal.db_sessionmaker() as db:
        repo = RestaurantRepository(db)
        artifact_repo = AlgorithmArtifactRepository(db)
        generated_at = utcnow()
        unique_restaurant_ids = list(dict.fromkeys(restaurant_ids))
        fresh_after = generated_at - _RESTAURANT_PROFILE_FRESHNESS_WINDOW
        existing_profiles = await artifact_repo.latest_restaurant_profiles(unique_restaurant_ids)
        for restaurant_id in unique_restaurant_ids:
            existing = existing_profiles.get(restaurant_id)
            if existing is not None and as_utc(existing.generated_at) >= fresh_after:
                continue
            restaurant = await repo.find(restaurant_id)
            if restaurant is None or restaurant.deleted_at is not None:
                continue
            try:
                profile = build_restaurant_profile_artifact(
                    restaurant,
                    generated_at=generated_at,
                    profile_provider=profile_provider,
                )
            except UnknownRestaurantCategoryError as exc:
                logger.warning(
                    f"skipping restaurant profile {restaurant.id} with unsupported category: {exc}"
                )
                continue
            await artifact_repo.add_restaurant_profile(
                restaurant_id=restaurant.id,
                payload_json=profile.model_dump(mode="json"),
                embedding=profile.embedding,
                algorithm_version=profile.algorithm_version,
                generated_at=generated_at,
                commit=False,
            )
        try:
            await db.commit()
        except Exception as exc:
            logger.error(f"restaurant profiling failed: {exc}", exc_info=exc)
            raise
