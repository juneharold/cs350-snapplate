def _doc(category_name: str) -> dict:
    return {
        "id": "123",
        "place_name": "Cafe One",
        "category_name": category_name,
        "y": "36.3504",
        "x": "127.3845",
        "place_url": "https://place.map.kakao.com/123",
    }


def test_kakao_restaurant_data_preserves_leaf_category_for_display() -> None:
    from app.services.kakao.client import KakaoService

    result = KakaoService._to_data(_doc("음식점 > 카페 > 커피전문점"))

    assert result.category == "커피전문점"


def test_kakao_cafeteria_category_preserves_leaf_category_for_display() -> None:
    from app.services.kakao.client import KakaoService

    result = KakaoService._to_data(_doc("음식점 > 구내식당"))

    assert result.category == "구내식당"


def test_kakao_restaurant_data_preserves_unknown_leaf_category_for_display() -> None:
    from app.services.kakao.client import KakaoService

    result = KakaoService._to_data(_doc("음식점 > 퓨전음식"))

    assert result.category == "퓨전음식"
