from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.config.algorithm import (
    DAY_NAMES,
    HEATMAP_COLS,
    HEATMAP_ROWS,
    MIN_ENTRIES_FOR_PERSONALIZATION,
)
from app.schemas.algorithm import (
    CategoryStats,
    DiaryEntryInput,
    EntryProfileArtifact,
    FlavorLean,
    TasteCategory,
    TasteProfileInsufficient,
    TasteProfileReady,
    TasteProfileResponse,
    TasteSummary,
    TasteType,
    TimeHeatmap,
    TopDish,
    UserProfileArtifact,
    WeightedEntryProfile,
)
from app.services.algorithm.providers import ProfileProvider
from app.services.algorithm.user_profiling import (
    aggregate_user_profile,
    build_weighted_entry_profiles,
)
from app.types.restaurant import FoodTone


def generate_taste_report(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
    *,
    profile_provider: ProfileProvider,
    min_entries_required: int = MIN_ENTRIES_FOR_PERSONALIZATION,
    generated_at: datetime | None = None,
    entry_profiles: Sequence[EntryProfileArtifact] | None = None,
    user_profile: UserProfileArtifact | None = None,
) -> TasteProfileResponse:
    entries = _entries_for_user(user_id, diary_entries)
    if len(entries) < min_entries_required:
        return TasteProfileInsufficient(
            has_enough_data=False,
            min_entries_required=min_entries_required,
            current_entries=len(entries),
        )

    computed_at = generated_at or datetime.now(UTC)
    weighted_entries = build_weighted_entry_profiles(
        user_id,
        entries,
        profile_provider=profile_provider,
        entry_profiles=entry_profiles,
    )
    if user_profile is None:
        user_profile = aggregate_user_profile(
            user_id,
            entries,
            profile_provider=profile_provider,
            generated_at=computed_at,
            weighted_entries=weighted_entries,
        )
    else:
        _validate_user_profile_artifact(user_id, len(entries), user_profile)
    profile_summary = profile_provider.generate_profile_summary(user_profile.profile_text)
    category_stats = _weighted_category_stats(weighted_entries)
    categories = _taste_categories(category_stats)

    return TasteProfileReady(
        has_enough_data=True,
        min_entries_required=min_entries_required,
        current_entries=len(entries),
        computed_at=computed_at,
        type=TasteType(label=profile_summary.label, blurb=profile_summary.blurb),
        summary=_taste_summary(entries, computed_at),
        categories=categories,
        rating_distribution=_rating_distribution(entries),
        time_heatmap=_time_heatmap(entries),
        flavor_lean=_flavor_lean(user_profile),
        top_dishes=_top_dishes(weighted_entries),
        insights=profile_summary.insights,
    )


def _validate_user_profile_artifact(
    user_id: str,
    source_entry_count: int,
    user_profile: UserProfileArtifact,
) -> None:
    if user_profile.user_id != user_id:
        raise ValueError("user_profile must match user_id")
    if user_profile.source_entry_count != source_entry_count:
        raise ValueError("user_profile source_entry_count must match diary_entries")


def _entries_for_user(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
) -> list[DiaryEntryInput]:
    entries = list(diary_entries)
    mismatched = [entry.id for entry in entries if entry.user_id != user_id]
    if mismatched:
        raise ValueError(f"diary_entries include entries for a different user: {mismatched}")
    return entries


def _weighted_category_stats(
    weighted_entries: Sequence[WeightedEntryProfile],
) -> dict[str, CategoryStats]:
    stats: dict[str, CategoryStats] = {}
    for item in weighted_entries:
        entry = item.entry
        category = entry.restaurant.category
        current = stats.get(category, CategoryStats(tone=entry.restaurant.thumbnail_tone))
        rating = entry.rating
        rating_factor = (rating / 5.0) if rating is not None else 0.6
        stats[category] = CategoryStats(
            visits=current.visits + 1,
            rating_sum=current.rating_sum + (rating or 0.0),
            rating_count=current.rating_count + (1 if rating is not None else 0),
            tone=current.tone,
            weight_sum=current.weight_sum + item.weight * rating_factor,
        )
    return stats


def _taste_categories(category_stats: dict[str, CategoryStats]) -> list[TasteCategory]:
    max_weight = max((stats.weight_sum for stats in category_stats.values()), default=1.0)
    categories = [
        TasteCategory(
            name=name,
            weight=round(stats.weight_sum / max_weight, 2),
            visits=stats.visits,
            tone=stats.tone,
        )
        for name, stats in category_stats.items()
    ]
    return sorted(categories, key=lambda category: (-category.weight, category.name))


def _taste_summary(entries: Sequence[DiaryEntryInput], generated_at: datetime) -> TasteSummary:
    ratings = [entry.rating for entry in entries if entry.rating is not None]
    avg_rating = _round_one_decimal(sum(ratings) / len(ratings)) if ratings else 0.0
    place_ids = {entry.restaurant.id for entry in entries}
    this_month_place_ids = {
        entry.restaurant.id
        for entry in entries
        if (
            entry.captured_at.year == generated_at.year
            and entry.captured_at.month == generated_at.month
        )
    }
    day_totals = [0] * 7
    for entry in entries:
        day_totals[entry.captured_at.weekday()] += 1
    top_day = DAY_NAMES[day_totals.index(max(day_totals))]
    return TasteSummary(
        avg_rating=avg_rating,
        avg_rating_delta_month=0.0,
        places_count=len(place_ids),
        new_places_month=len(this_month_place_ids),
        top_day_of_week=top_day,
    )


def _time_heatmap(entries: Sequence[DiaryEntryInput]) -> TimeHeatmap:
    data = [[0 for _ in range(7)] for _ in range(5)]
    for entry in entries:
        data[_hour_bucket(entry.captured_at.hour)][entry.captured_at.weekday()] += 1
    return TimeHeatmap(rows=HEATMAP_ROWS, cols=HEATMAP_COLS, data=data)


def _rating_distribution(entries: Sequence[DiaryEntryInput]) -> dict[str, int]:
    distribution = {f"{step / 2:.1f}": 0 for step in range(1, 11)}
    for entry in entries:
        if entry.rating is None:
            continue
        key = f"{round(entry.rating * 2) / 2:.1f}"
        if key in distribution:
            distribution[key] += 1
    return distribution


def _hour_bucket(hour: int) -> int:
    if hour < 11:
        return 0
    if hour < 14:
        return 1
    if hour < 17:
        return 2
    if hour < 21:
        return 3
    return 4


def _flavor_lean(user_profile: UserProfileArtifact) -> FlavorLean:
    buckets = {
        "umami": 0.0,
        "sweet": 0.0,
        "salty": 0.0,
        "sour": 0.0,
        "spicy": 0.0,
        "bitter": 0.0,
    }
    for term, score in user_profile.long_term_profile.get("taste", {}).items():
        if term in {"savory", "umami", "smoky"}:
            buckets["umami"] += score
        elif term in {"sweet", "buttery"}:
            buckets["sweet"] += score
        elif term in buckets:
            buckets[term] += score

    max_score = max(buckets.values()) or 1.0
    return FlavorLean(
        umami=round(buckets["umami"] / max_score, 2),
        sweet=round(buckets["sweet"] / max_score, 2),
        salty=round(buckets["salty"] / max_score, 2),
        sour=round(buckets["sour"] / max_score, 2),
        spicy=round(buckets["spicy"] / max_score, 2),
        bitter=round(buckets["bitter"] / max_score, 2),
    )


def _top_dishes(weighted_entries: Sequence[WeightedEntryProfile]) -> list[TopDish]:
    grouped: dict[str, tuple[int, float, int, FoodTone, float]] = {}
    for item in weighted_entries:
        entry = item.entry
        dish = entry.restaurant.signature_dish
        if not dish:
            continue
        visits, rating_sum, rating_count, tone, weight_sum = grouped.get(
            dish,
            (0, 0.0, 0, entry.restaurant.thumbnail_tone, 0.0),
        )
        rating_factor = (entry.rating / 5.0) if entry.rating is not None else 0.6
        grouped[dish] = (
            visits + 1,
            rating_sum + (entry.rating or 0.0),
            rating_count + (1 if entry.rating is not None else 0),
            tone,
            weight_sum + item.weight * rating_factor,
        )
    dishes = [
        (
            weight_sum,
            TopDish(
                name=name,
                visits=visits,
                rating=_round_one_decimal(rating_sum / rating_count) if rating_count else 0.0,
                tone=tone,
            ),
        )
        for name, (visits, rating_sum, rating_count, tone, weight_sum) in grouped.items()
    ]
    return [
        dish
        for _, dish in sorted(
            dishes,
            key=lambda item: (-item[0], -item[1].rating, item[1].name),
        )[:3]
    ]


def _round_one_decimal(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
