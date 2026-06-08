from __future__ import annotations

from typing import Final

PUBLIC_RESTAURANT_CATEGORIES: Final[tuple[str, ...]] = (
    "Korean",
    "Korean BBQ",
    "Noodles",
    "Diner / Set meal",
    "Comfort Korean",
    "Cafe",
    "Bakery",
    "Snacks",
    "Chinese",
    "Japanese",
    "Western",
    "Bar",
    "Dessert",
)

_PUBLIC_RESTAURANT_CATEGORY_BY_KEY: Final[dict[str, str]] = {
    category.casefold(): category for category in PUBLIC_RESTAURANT_CATEGORIES
}

_KAKAO_CATEGORY_ALIASES: Final[dict[str, str]] = {
    "한식": "Korean",
    "백반": "Diner / Set meal",
    "정식": "Diner / Set meal",
    "구내식당": "Diner / Set meal",
    "찌개": "Comfort Korean",
    "국밥": "Comfort Korean",
    "육류,고기": "Korean BBQ",
    "고기": "Korean BBQ",
    "구이": "Korean BBQ",
    "국수": "Noodles",
    "냉면": "Noodles",
    "면": "Noodles",
    "분식": "Snacks",
    "김밥": "Snacks",
    "떡볶이": "Snacks",
    "카페": "Cafe",
    "커피전문점": "Cafe",
    "제과,베이커리": "Bakery",
    "베이커리": "Bakery",
    "빵집": "Bakery",
    "중식": "Chinese",
    "중국요리": "Chinese",
    "일식": "Japanese",
    "일본식": "Japanese",
    "초밥": "Japanese",
    "양식": "Western",
    "이탈리안": "Western",
    "패밀리레스토랑": "Western",
    "술집": "Bar",
    "호프,요리주점": "Bar",
    "호프": "Bar",
    "요리주점": "Bar",
    "디저트카페": "Dessert",
    "디저트": "Dessert",
    # Expanded from a wider Kakao FD6 category harvest (~90 distinct paths) so
    # more real restaurants classify at the algorithm boundary instead of being
    # skipped as unsupported. Keyed on Kakao's depth-1 cuisine level and the
    # common leaf labels legacy rows store.
    "해물,생선": "Korean",
    "두부전문점": "Korean",
    "순대": "Korean",
    "닭요리": "Korean",
    "회": "Korean",
    "게,대게": "Korean",
    "퓨전한식": "Korean",
    "갈비": "Korean BBQ",
    "삼겹살": "Korean BBQ",
    "곱창,막창,양": "Korean BBQ",
    "곰탕": "Comfort Korean",
    "설렁탕": "Comfort Korean",
    "찌개,전골": "Comfort Korean",
    "해장국": "Comfort Korean",
    "삼계탕": "Comfort Korean",
    "샤브샤브": "Comfort Korean",
    "칼국수": "Noodles",
    "뷔페": "Diner / Set meal",
    "한식뷔페": "Diner / Set meal",
    "고기뷔페": "Diner / Set meal",
    "푸드코트": "Diner / Set meal",
    "도시락": "Diner / Set meal",
    "토스트": "Snacks",
    "간식": "Snacks",
    "도넛": "Dessert",
    "아이스크림": "Dessert",
    "아이스크림판매": "Dessert",
    "초콜릿": "Dessert",
    "떡,한과": "Dessert",
    "초밥,롤": "Japanese",
    "돈까스,우동": "Japanese",
    "일본식라면": "Japanese",
    "퓨전일식": "Japanese",
    "퓨전중식": "Chinese",
    "피자": "Western",
    "햄버거": "Western",
    "스테이크,립": "Western",
    "패스트푸드": "Western",
    "샌드위치": "Western",
    "치킨": "Western",
    "샐러드": "Western",
    "칵테일바": "Bar",
    "일본식주점": "Bar",
    "와인바": "Bar",
    "실내포장마차": "Bar",
}

FLAVOR_LEAN_FIELDS: Final[tuple[str, ...]] = (
    "umami",
    "sweet",
    "salty",
    "sour",
    "spicy",
    "bitter",
)

INTERNAL_PROFILE_TAXONOMY: Final[dict[str, tuple[str, ...]]] = {
    "cuisine": (
        "korean",
        "japanese",
        "chinese",
        "western",
        "italian",
        "asian_fusion",
        "cafe_bakery",
    ),
    "food_type": (
        "noodle",
        "rice_bowl",
        "soup",
        "stew",
        "bbq",
        "fried",
        "set_meal",
        "bread",
        "pastry",
        "coffee",
        "dessert",
        "snack",
        "drink",
    ),
    "taste": (
        "savory",
        "umami",
        "spicy",
        "sweet",
        "salty",
        "sour",
        "bitter",
        "smoky",
        "buttery",
        "crisp",
        "rich",
        "light",
        "fresh",
        "creamy",
        "chewy",
    ),
    "context": (
        "quick_meal",
        "solo_meal",
        "group_meal",
        "casual",
        "date",
        "study_work",
        "takeout",
        "late_night",
        "comfort_meal",
        "special_occasion",
    ),
    "venue": (
        "casual",
        "cafe",
        "bakery",
        "bar",
        "diner",
        "bbq_place",
        "dessert_shop",
        "fast_casual",
        "sit_down",
    ),
    "emotion": (
        "satisfied",
        "delighted",
        "neutral",
        "disappointed",
        "reliable",
        "craving",
    ),
    "location_feature": (
        "nearby",
        "near_campus",
        "neighborhood_repeat",
        "destination",
        "commute_area",
    ),
    "temporal_feature": (
        "breakfast",
        "lunch",
        "afternoon",
        "dinner",
        "late_night",
        "weekday",
        "weekend",
    ),
}

PROFILE_FIELD_NAMES: Final[tuple[str, ...]] = tuple(INTERNAL_PROFILE_TAXONOMY)


class UnknownRestaurantCategoryError(ValueError):
    pass


def normalize_public_restaurant_category(
    raw_category: str | None,
    raw_path: str | None = None,
) -> str:
    values = [value.strip() for value in (raw_category, raw_path) if value and value.strip()]
    path_parts = [part.strip() for value in values for part in value.split(">") if part.strip()]

    for candidate in [*values, *reversed(path_parts)]:
        normalized = _normalize_category_candidate(candidate)
        if normalized is not None:
            return normalized

    searchable = " > ".join(values)
    for alias, category in _KAKAO_CATEGORY_ALIASES.items():
        if alias in searchable:
            return category

    raise UnknownRestaurantCategoryError(
        f"unsupported restaurant category: {raw_category or raw_path or ''}"
    )


def _normalize_category_candidate(candidate: str) -> str | None:
    public = _PUBLIC_RESTAURANT_CATEGORY_BY_KEY.get(candidate.casefold())
    if public is not None:
        return public
    return _KAKAO_CATEGORY_ALIASES.get(candidate)
