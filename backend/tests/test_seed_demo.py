from __future__ import annotations

from collections import Counter

from scripts.seed_demo import demo_fallback_restaurants

from app.utils.restaurant_taxonomy import normalize_public_restaurant_category


def test_demo_fallback_restaurants_are_normalizable_and_unique() -> None:
    items = demo_fallback_restaurants({"Korean BBQ": 2, "Cafe": 1})

    assert len(items) == 3
    assert len({item.kakao_id for item in items}) == 3
    assert Counter(item.category for item in items) == {"Korean BBQ": 2, "Cafe": 1}
    assert all(item.kakao_id.startswith("demo-") for item in items)
    assert all(item.rating >= 4.0 for item in items)
    assert all(item.rating_count > 0 for item in items)

    for item in items:
        assert (
            normalize_public_restaurant_category(
                item.category,
                (item.raw_payload or {}).get("category_name"),
            )
            == item.category
        )
