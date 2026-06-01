from __future__ import annotations

from datetime import datetime, timedelta, timezone

from algorithm import aggregate_user_profile, generate_taste_report
from algorithm.schemas import DiaryEntryInput, RestaurantInput, TasteProfileReady


NOW = datetime(2026, 5, 24, 12, 43, tzinfo=timezone.utc)
USER_ID = "u_user_profile"


def restaurant(
    restaurant_id: str,
    category: str,
    *,
    signature_dish: str | None,
    rating: float,
) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant_id,
        name=f"{category} Place {restaurant_id}",
        category=category,
        signature_dish=signature_dish,
        rating=rating,
        rating_count=120,
        distance_m=400,
        thumbnail_url=None,
        thumbnail_tone="bone",
        thumbnail_label=signature_dish or category.lower(),
        tags=[],
        lat=36.371,
        lng=127.361,
        kakao_id=f"kakao_{restaurant_id}",
        neighborhood="Eoeun-dong",
        is_bookmarked=False,
    )


def entry(
    index: int,
    *,
    category: str,
    signature_dish: str | None,
    rating: float,
    note: str,
    image_labels: list[str] | None = None,
    days_ago: int,
) -> DiaryEntryInput:
    return DiaryEntryInput(
        id=f"e_profile_{index}",
        user_id=USER_ID,
        captured_at=NOW - timedelta(days=days_ago),
        restaurant=restaurant(
            f"r_profile_{index}",
            category,
            signature_dish=signature_dish,
            rating=rating,
        ),
        rating=rating,
        note=note,
        image_labels=image_labels or [],
    )


def test_aggregate_user_profile_weights_recency_richness_and_confidence() -> None:
    old_sparse_sweet = entry(
        1,
        category="Bakery",
        signature_dish="Honey roll",
        rating=5.0,
        note="Sweet.",
        days_ago=120,
    )
    recent_rich_spicy = entry(
        2,
        category="Korean BBQ",
        signature_dish="Marinated short rib",
        rating=4.5,
        note="Spicy, savory, smoky, and satisfying.",
        image_labels=["korean grilled meat"],
        days_ago=1,
    )

    profile = aggregate_user_profile(
        USER_ID,
        [old_sparse_sweet, recent_rich_spicy],
        generated_at=NOW,
        short_term_entry_count=1,
    )
    repeat = aggregate_user_profile(
        USER_ID,
        [old_sparse_sweet, recent_rich_spicy],
        generated_at=NOW,
        short_term_entry_count=1,
    )

    assert profile.source_entry_count == 2
    assert (
        profile.long_term_profile["taste"]["spicy"]
        > profile.long_term_profile["taste"]["sweet"]
    )
    assert "sweet" not in profile.short_term_profile["taste"]
    assert profile.category_rating_vector == {"Bakery": 5.0, "Korean BBQ": 4.5}
    assert profile.confidence["taste"] < profile.confidence["temporal_feature"]
    assert "note: spicy" in profile.evidence["taste"]
    assert "spicy" in profile.profile_text
    assert profile.long_term_embedding
    assert profile.short_term_embedding
    assert profile.long_term_embedding == repeat.long_term_embedding
    assert profile.short_term_embedding == repeat.short_term_embedding


def test_taste_report_uses_deterministic_profile_stats() -> None:
    entries = [
        entry(
            1,
            category="Noodles",
            signature_dish="Clam noodle soup",
            rating=4.5,
            note="Savory broth and chewy noodles.",
            image_labels=["noodle soup"],
            days_ago=0,
        ),
        entry(
            2,
            category="Noodles",
            signature_dish="Clam noodle soup",
            rating=5.0,
            note="Umami soup, quick lunch.",
            image_labels=["noodle soup"],
            days_ago=2,
        ),
        entry(
            3,
            category="Chinese",
            signature_dish="Mapo tofu",
            rating=3.5,
            note="Spicy tofu.",
            image_labels=["chinese tofu"],
            days_ago=8,
        ),
    ]

    report = generate_taste_report(
        USER_ID,
        entries,
        min_entries_required=len(entries),
        generated_at=NOW,
    )

    assert isinstance(report, TasteProfileReady)
    assert report.rating_distribution == {
        "0.5": 0,
        "1.0": 0,
        "1.5": 0,
        "2.0": 0,
        "2.5": 0,
        "3.0": 0,
        "3.5": 1,
        "4.0": 0,
        "4.5": 1,
        "5.0": 1,
    }
    assert report.categories[0].name == "Noodles"
    assert report.categories[0].visits == 2
    assert report.flavor_lean.umami > report.flavor_lean.sweet
    assert report.flavor_lean.spicy > 0
    assert report.top_dishes[0].name == "Clam noodle soup"
    assert report.type.label
    assert report.type.blurb
