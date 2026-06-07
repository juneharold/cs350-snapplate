from datetime import UTC, datetime, timedelta

from app.schemas.algorithm import DiaryEntryInput, RestaurantInput
from app.services.algorithm.providers import DeterministicProvider

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)
USER_ID = "u_backend_taste"


def _restaurant() -> RestaurantInput:
    return RestaurantInput(
        id="r_backend_taste",
        name="Noodle House",
        category="Noodles",
        signature_dish="Clam noodle soup",
        rating=4.6,
        rating_count=120,
        distance_m=400,
        thumbnail_url=None,
        thumbnail_tone="bone",
        thumbnail_label="noodles",
        tags=[],
        lat=36.371,
        lng=127.361,
        kakao_id="k_backend_taste",
        neighborhood="Eoeun-dong",
        is_bookmarked=False,
    )


def _entry(index: int) -> DiaryEntryInput:
    return DiaryEntryInput(
        id=f"e_backend_taste_{index}",
        user_id=USER_ID,
        captured_at=NOW - timedelta(days=index),
        restaurant=_restaurant(),
        rating=4.5,
        note="Savory broth and chewy noodles.",
    )


def test_build_taste_refresh_artifacts_for_ready_profile() -> None:
    from app.services.algorithm.taste import build_taste_refresh_artifacts

    result = build_taste_refresh_artifacts(
        USER_ID,
        [_entry(i) for i in range(10)],
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
        min_entries_required=10,
    )

    assert result.report.has_enough_data is True
    assert len(result.entry_profiles) == 10
    assert result.user_profile is not None
    assert result.user_profile.source_entry_count == 10


def test_build_taste_refresh_artifacts_for_insufficient_profile() -> None:
    from app.services.algorithm.taste import build_taste_refresh_artifacts

    result = build_taste_refresh_artifacts(
        USER_ID,
        [_entry(i) for i in range(3)],
        generated_at=NOW,
        profile_provider=DeterministicProvider(),
        min_entries_required=10,
    )

    assert result.report.has_enough_data is False
    assert result.entry_profiles == []
    assert result.user_profile is None
