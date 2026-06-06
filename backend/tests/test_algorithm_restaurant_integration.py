from datetime import UTC, datetime

from algorithm.providers import DeterministicProvider

from app.models.restaurant import RestaurantModel
from app.types.restaurant import FoodTone

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)


def _restaurant() -> RestaurantModel:
    return RestaurantModel(
        id="r_profile",
        kakao_id="k_profile",
        name="Noodle House",
        category="Noodles",
        signature_dish="Clam noodle soup",
        rating=4.6,
        rating_count=120,
        thumbnail_url="https://place.map.kakao.com/k_profile",
        thumbnail_tone=FoodTone.BONE,
        thumbnail_label="Noodle House",
        tags=["quick lunch"],
        lat=36.3504,
        lng=127.3845,
        neighborhood="Eoeun-dong",
        address="Eoeun-dong",
        phone="042-000-0000",
        raw_payload={"category_name": "음식점 > 한식 > 국수"},
    )


def test_metadata_from_restaurant_model_uses_public_category() -> None:
    from app.services.algorithm.restaurants import metadata_from_restaurant_model

    metadata = metadata_from_restaurant_model(_restaurant())

    assert metadata.id == "r_profile"
    assert metadata.category_name == "Noodles"
    assert metadata.address_name == "Eoeun-dong"


def test_build_restaurant_profile_artifact() -> None:
    from app.services.algorithm.restaurants import build_restaurant_profile_artifact

    profile = build_restaurant_profile_artifact(
        _restaurant(),
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
    )

    assert profile.restaurant_id == "r_profile"
    assert profile.profile["food_type"]["noodle"] > 0
    assert profile.embedding
