from __future__ import annotations

from datetime import datetime, timedelta, timezone

from algorithm.schemas import (
    DiaryEntryInput,
    RecommendationContext,
    RestaurantInput,
    SyntheticFixtureSet,
    SyntheticUser,
)


GENERATED_AT = datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc)
BASE_LAT = 36.371
BASE_LNG = 127.361


def load_synthetic_fixture_set() -> SyntheticFixtureSet:
    restaurants = _restaurants()
    return SyntheticFixtureSet(
        generated_at=GENERATED_AT,
        users=[
            SyntheticUser(
                id="u_synth_broth",
                label="Broth regular",
                primary_categories=["Noodles", "Diner / Set meal"],
            ),
            SyntheticUser(
                id="u_synth_bakery",
                label="Bakery hunter",
                primary_categories=["Bakery", "Cafe"],
            ),
            SyntheticUser(
                id="u_synth_spicy",
                label="Spicy Korean regular",
                primary_categories=["Korean BBQ", "Noodles"],
            ),
            SyntheticUser(
                id="u_synth_cafe",
                label="Cafe worker",
                primary_categories=["Cafe", "Bakery"],
            ),
        ],
        restaurants=list(restaurants.values()),
        diary_entries=_diary_entries(restaurants),
        exposure_history={
            "u_synth_broth": ["r_synth_seen_noodles", "r_synth_new_bakery"],
            "u_synth_bakery": ["r_synth_seen_bakery", "r_synth_new_cafe"],
            "u_synth_spicy": ["r_synth_new_bbq", "r_synth_seen_noodles"],
            "u_synth_cafe": ["r_synth_new_cafe", "r_synth_seen_bakery"],
        },
    )


def synthetic_recommendation_context_for_user(user_id: str) -> RecommendationContext:
    fixtures = load_synthetic_fixture_set()
    user_ids = {user.id for user in fixtures.users}
    if user_id not in user_ids:
        raise ValueError(f"unknown synthetic user_id: {user_id}")

    return RecommendationContext(
        diary_entries=[entry for entry in fixtures.diary_entries if entry.user_id == user_id],
        candidate_restaurants=fixtures.restaurants,
        lat=BASE_LAT,
        lng=BASE_LNG,
        exposure_history=fixtures.exposure_history[user_id],
    )


def _restaurants() -> dict[str, RestaurantInput]:
    return {
        "r_synth_noodles_1": _restaurant(
            "r_synth_noodles_1",
            "Eoeun Kalguksu",
            "Noodles",
            "Clam noodle soup",
            4.7,
            260,
            "bone",
            "clam noodle soup",
            ["warm broth"],
        ),
        "r_synth_noodles_2": _restaurant(
            "r_synth_noodles_2",
            "Campus Soba",
            "Noodles",
            "Cold soba",
            4.4,
            610,
            "bone",
            "cold soba",
            ["quick lunch"],
        ),
        "r_synth_bakery_1": _restaurant(
            "r_synth_bakery_1",
            "Daejeon Oven",
            "Bakery",
            "Fried streusel bun",
            4.8,
            1180,
            "cream",
            "streusel bun",
            ["local favorite"],
        ),
        "r_synth_cafe_1": _restaurant(
            "r_synth_cafe_1",
            "Acorn Cafe",
            "Cafe",
            "Acorn latte",
            4.3,
            250,
            "char",
            "latte",
            ["quiet"],
        ),
        "r_synth_korean_1": _restaurant(
            "r_synth_korean_1",
            "Campus Baekban",
            "Diner / Set meal",
            "Kimchi stew set",
            4.2,
            520,
            "rust",
            "kimchi stew",
            ["quick lunch"],
        ),
        "r_synth_bbq_1": _restaurant(
            "r_synth_bbq_1",
            "Bonga BBQ",
            "Korean BBQ",
            "Marinated short rib",
            4.7,
            840,
            "paprika",
            "short rib",
            ["reserve ahead"],
        ),
        "r_synth_new_noodles": _restaurant(
            "r_synth_new_noodles",
            "New Noodle Bar",
            "Noodles",
            "Chicken noodle soup",
            4.8,
            300,
            "bone",
            "chicken noodle soup",
            ["warm broth"],
        ),
        "r_synth_seen_noodles": _restaurant(
            "r_synth_seen_noodles",
            "Seen Soba House",
            "Noodles",
            "Tempura soba",
            4.9,
            180,
            "bone",
            "tempura soba",
            ["quick lunch"],
        ),
        "r_synth_new_bakery": _restaurant(
            "r_synth_new_bakery",
            "Butter Lab",
            "Bakery",
            "Salt butter roll",
            4.6,
            450,
            "butter",
            "butter roll",
            ["fresh bread"],
        ),
        "r_synth_seen_bakery": _restaurant(
            "r_synth_seen_bakery",
            "Seen Croissant",
            "Bakery",
            "Almond croissant",
            4.9,
            210,
            "cream",
            "croissant",
            ["popular"],
        ),
        "r_synth_new_cafe": _restaurant(
            "r_synth_new_cafe",
            "Quiet Cup",
            "Cafe",
            "Flat white",
            4.5,
            220,
            "char",
            "flat white",
            ["quiet"],
        ),
        "r_synth_new_bbq": _restaurant(
            "r_synth_new_bbq",
            "Charcoal Table",
            "Korean BBQ",
            "Pork belly",
            4.6,
            560,
            "paprika",
            "pork belly",
            ["grill"],
        ),
        "r_synth_new_chinese": _restaurant(
            "r_synth_new_chinese",
            "Campus Wok",
            "Chinese",
            "Mapo tofu",
            4.4,
            390,
            "rust",
            "mapo tofu",
            ["spicy"],
        ),
    }


def _diary_entries(restaurants: dict[str, RestaurantInput]) -> list[DiaryEntryInput]:
    rows = [
        (
            "u_synth_broth",
            "r_synth_noodles_1",
            0,
            4.5,
            "Clear broth and chewy noodles.",
            ["noodle soup"],
        ),
        (
            "u_synth_broth",
            "r_synth_noodles_1",
            2,
            5.0,
            "Hot simple broth after lab.",
            ["noodle soup"],
        ),
        (
            "u_synth_broth",
            "r_synth_noodles_2",
            5,
            4.5,
            "Clean dipping sauce and springy noodles.",
            ["cold noodles"],
        ),
        (
            "u_synth_broth",
            "r_synth_korean_1",
            8,
            4.0,
            "Fast lunch with kimchi stew.",
            ["korean stew"],
        ),
        (
            "u_synth_broth",
            "r_synth_bbq_1",
            12,
            4.0,
            "Tender short rib with balanced sauce.",
            ["grilled meat"],
        ),
        (
            "u_synth_broth",
            "r_synth_noodles_2",
            16,
            4.5,
            "Reliable lunch noodles.",
            ["soba noodles"],
        ),
        (
            "u_synth_bakery",
            "r_synth_bakery_1",
            1,
            5.0,
            "Crisp outside, soft inside, not too sweet.",
            ["pastry"],
        ),
        (
            "u_synth_bakery",
            "r_synth_bakery_1",
            3,
            4.5,
            "Buttery breakfast bun.",
            ["bread"],
        ),
        (
            "u_synth_bakery",
            "r_synth_cafe_1",
            6,
            4.0,
            "Quiet cafe and steady latte.",
            ["coffee"],
        ),
        (
            "u_synth_bakery",
            "r_synth_seen_bakery",
            10,
            4.5,
            "Almond croissant was flaky.",
            ["croissant"],
        ),
        (
            "u_synth_bakery",
            "r_synth_new_bakery",
            14,
            4.0,
            "Good butter roll near campus.",
            ["bread roll"],
        ),
        (
            "u_synth_bakery",
            "r_synth_cafe_1",
            18,
            4.0,
            "Afternoon coffee stop.",
            ["latte"],
        ),
        (
            "u_synth_spicy",
            "r_synth_bbq_1",
            0,
            4.5,
            "Smoky grill and spicy side dishes.",
            ["grilled meat"],
        ),
        (
            "u_synth_spicy",
            "r_synth_korean_1",
            4,
            4.0,
            "Kimchi stew was spicy and savory.",
            ["korean stew"],
        ),
        (
            "u_synth_spicy",
            "r_synth_noodles_1",
            7,
            4.0,
            "Broth was warm after class.",
            ["noodle soup"],
        ),
        (
            "u_synth_spicy",
            "r_synth_new_chinese",
            9,
            4.5,
            "Mapo tofu had a strong spicy kick.",
            ["mapo tofu"],
        ),
        (
            "u_synth_spicy",
            "r_synth_new_bbq",
            13,
            4.5,
            "Pork belly with smoky char.",
            ["grilled meat"],
        ),
        (
            "u_synth_spicy",
            "r_synth_noodles_2",
            17,
            3.5,
            "Cold soba was fine but mild.",
            ["cold noodles"],
        ),
        (
            "u_synth_cafe",
            "r_synth_cafe_1",
            1,
            4.5,
            "Quiet enough to work with a latte.",
            ["latte"],
        ),
        (
            "u_synth_cafe",
            "r_synth_cafe_1",
            3,
            4.0,
            "Reliable afternoon stop.",
            ["coffee"],
        ),
        (
            "u_synth_cafe",
            "r_synth_new_cafe",
            6,
            4.5,
            "Flat white was smooth.",
            ["flat white"],
        ),
        (
            "u_synth_cafe",
            "r_synth_bakery_1",
            9,
            4.0,
            "Pastry paired well with coffee.",
            ["pastry"],
        ),
        (
            "u_synth_cafe",
            "r_synth_seen_bakery",
            11,
            4.0,
            "Croissant for a quick breakfast.",
            ["croissant"],
        ),
        (
            "u_synth_cafe",
            "r_synth_new_bakery",
            15,
            3.5,
            "Butter roll was okay.",
            ["bread roll"],
        ),
    ]
    return [
        DiaryEntryInput(
            id=f"e_synth_{index:02d}",
            user_id=user_id,
            captured_at=GENERATED_AT - timedelta(days=days_ago),
            restaurant=restaurants[restaurant_id],
            rating=rating,
            note=note,
            image_labels=image_labels,
        )
        for index, (user_id, restaurant_id, days_ago, rating, note, image_labels) in enumerate(
            rows,
            start=1,
        )
    ]


def _restaurant(
    restaurant_id: str,
    name: str,
    category: str,
    signature_dish: str,
    rating: float,
    distance_m: int,
    thumbnail_tone: str,
    thumbnail_label: str,
    tags: list[str],
) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant_id,
        name=name,
        category=category,
        signature_dish=signature_dish,
        rating=rating,
        rating_count=120,
        distance_m=distance_m,
        thumbnail_url=None,
        thumbnail_tone=thumbnail_tone,
        thumbnail_label=thumbnail_label,
        tags=tags,
        lat=BASE_LAT,
        lng=BASE_LNG,
        kakao_id=f"kakao_{restaurant_id}",
        neighborhood="Eoeun-dong",
        is_bookmarked=False,
    )
