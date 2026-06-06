from datetime import UTC, datetime

from app.models.entry import EntryModel
from app.models.restaurant import RestaurantModel
from app.types.restaurant import FoodTone


def _restaurant(category: str = "음식점 > 카페 > 커피전문점") -> RestaurantModel:
    return RestaurantModel(
        id="r_1",
        kakao_id="k_1",
        name="Cafe One",
        category=category,
        signature_dish="Latte",
        rating=4.2,
        rating_count=12,
        thumbnail_url=None,
        thumbnail_tone=FoodTone.BONE,
        thumbnail_label="Cafe One",
        tags=["quiet"],
        lat=36.3504,
        lng=127.3845,
        neighborhood="Eoeun-dong",
    )


def test_restaurant_input_from_model_normalizes_category_and_distance() -> None:
    from app.services.algorithm.inputs import restaurant_input_from_model

    restaurant = _restaurant()

    result = restaurant_input_from_model(
        restaurant,
        lat=36.3510,
        lng=127.3850,
        is_bookmarked=True,
    )

    assert result.category == "Cafe"
    assert result.distance_m > 0
    assert result.is_bookmarked is True


def test_diary_entry_input_from_models_uses_restaurant_adapter() -> None:
    from app.services.algorithm.inputs import diary_entry_input_from_models

    entry = EntryModel(
        id="e_1",
        user_id="u_1",
        restaurant_id="r_1",
        cover_media_id="m_1",
        captured_at=datetime(2026, 5, 24, 12, 30, tzinfo=UTC),
        rating=4.5,
        note="quiet latte",
        ai_tags=["coffee"],
    )

    result = diary_entry_input_from_models(entry, _restaurant())

    assert result.restaurant.category == "Cafe"
    assert result.image_labels == ["coffee"]
