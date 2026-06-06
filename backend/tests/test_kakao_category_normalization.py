import pytest

from app.config.algorithm_taxonomy import UnknownRestaurantCategoryError


def _doc(category_name: str) -> dict:
    return {
        "id": "123",
        "place_name": "Cafe One",
        "category_name": category_name,
        "y": "36.3504",
        "x": "127.3845",
        "place_url": "https://place.map.kakao.com/123",
    }


def test_kakao_restaurant_data_uses_public_category() -> None:
    from app.services.kakao.client import KakaoService

    result = KakaoService._to_data(_doc("음식점 > 카페 > 커피전문점"))

    assert result.category == "Cafe"


def test_kakao_cafeteria_category_maps_to_set_meal() -> None:
    from app.services.kakao.client import KakaoService

    result = KakaoService._to_data(_doc("음식점 > 구내식당"))

    assert result.category == "Diner / Set meal"


def test_kakao_restaurant_data_rejects_unknown_category() -> None:
    from app.services.kakao.client import KakaoService

    with pytest.raises(UnknownRestaurantCategoryError):
        KakaoService._to_data(_doc("음식점 > 퓨전음식"))
