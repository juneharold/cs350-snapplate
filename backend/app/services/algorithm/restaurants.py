from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from algorithm.providers import MLProvider
from algorithm.restaurant_profiling import profile_kakao_restaurant
from algorithm.schemas import KakaoRestaurantMetadata, RestaurantProfileArtifact
from algorithm.taxonomy import normalize_public_restaurant_category

from app.config.lifespan import InternalContext
from app.config.logger import create_logger
from app.models.algorithm_artifact import RestaurantProfileArtifactModel
from app.models.restaurant import RestaurantModel
from app.repositories.restaurant import RestaurantRepository
from app.utils.time import utcnow

logger = create_logger(__name__)


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
    ml_provider: MLProvider,
) -> RestaurantProfileArtifact:
    return profile_kakao_restaurant(
        metadata_from_restaurant_model(restaurant),
        generated_at=generated_at,
        ml_provider=ml_provider,
    )


async def profile_restaurants(
    internal: InternalContext,
    restaurant_ids: Sequence[str],
) -> None:
    if not restaurant_ids:
        return
    async with internal.db_sessionmaker() as db:
        repo = RestaurantRepository(db)
        generated_at = utcnow()
        for restaurant_id in dict.fromkeys(restaurant_ids):
            restaurant = await repo.find(restaurant_id)
            if restaurant is None or restaurant.deleted_at is not None:
                continue
            profile = build_restaurant_profile_artifact(
                restaurant,
                generated_at=generated_at,
                ml_provider=internal.profile_provider,
            )
            db.add(
                RestaurantProfileArtifactModel(
                    restaurant_id=restaurant.id,
                    payload_json=profile.model_dump(mode="json"),
                    algorithm_version=profile.algorithm_version,
                    generated_at=generated_at,
                )
            )
        try:
            await db.commit()
        except Exception as exc:
            logger.error(f"restaurant profiling failed: {exc}", exc_info=exc)
            raise
