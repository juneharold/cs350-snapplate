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
