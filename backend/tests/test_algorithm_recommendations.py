from datetime import UTC, datetime, timedelta

from algorithm import aggregate_user_profile
from algorithm.providers import DeterministicMLProvider
from algorithm.restaurant_profiling import profile_kakao_restaurant
from algorithm.schemas import DiaryEntryInput, KakaoRestaurantMetadata, RestaurantInput

NOW = datetime(2026, 5, 24, 12, 43, tzinfo=UTC)
USER_ID = "u_recommendation"


def _restaurant(restaurant_id: str, category: str) -> RestaurantInput:
    return RestaurantInput(
        id=restaurant_id,
        name=f"{category} Place",
        category=category,
        signature_dish="Signature",
        rating=4.6,
        rating_count=120,
        distance_m=300,
        thumbnail_url=None,
        thumbnail_tone="bone",
        thumbnail_label=category,
        tags=[],
        lat=36.371,
        lng=127.361,
        kakao_id=f"k_{restaurant_id}",
        neighborhood="Eoeun-dong",
        is_bookmarked=False,
    )


def _entry(index: int, user_id: str = USER_ID) -> DiaryEntryInput:
    return DiaryEntryInput(
        id=f"e_recommendation_{user_id}_{index}",
        user_id=user_id,
        captured_at=NOW - timedelta(days=index),
        restaurant=_restaurant(f"r_visited_{index}", "Noodles"),
        rating=4.5,
        note="Savory noodles.",
    )


def test_recommendation_context_from_stored_artifacts() -> None:
    from app.services.algorithm.recommendations import recommendation_context_from_artifacts

    provider = DeterministicMLProvider()
    entries = [_entry(index) for index in range(10)]
    user_profile = aggregate_user_profile(
        USER_ID,
        entries,
        generated_at=NOW,
        ml_provider=provider,
    )
    candidate = _restaurant("r_candidate", "Noodles")
    restaurant_profile = profile_kakao_restaurant(
        KakaoRestaurantMetadata(
            id=candidate.id,
            place_name=candidate.name,
            category_name=candidate.category,
            signature_dish=candidate.signature_dish,
        ),
        generated_at=NOW,
        ml_provider=provider,
    )

    context = recommendation_context_from_artifacts(
        diary_entries=entries,
        peer_diary_entries=[_entry(1, "u_peer")],
        candidate_restaurants=[candidate],
        user_profile_payload=user_profile.model_dump(mode="json"),
        restaurant_profile_payloads=[restaurant_profile.model_dump(mode="json")],
        exposure_history=["r_candidate"],
        lat=36.371,
        lng=127.361,
        requested_at=NOW,
    )

    assert context.user_profile == user_profile
    assert context.restaurant_profiles == [restaurant_profile]
    assert context.peer_diary_entries[0].user_id == "u_peer"
    assert context.exposure_history == ["r_candidate"]
