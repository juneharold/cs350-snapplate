from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from snapplate_algorithm.schemas import (
    DiaryEntryInput,
    FlavorLean,
    RecommendationContext,
    RecommendedResponse,
    RecommendedRestaurant,
    RestaurantInput,
    TasteCategory,
    TasteProfileInsufficient,
    TasteProfileReady,
    TasteProfileResponse,
    TasteSummary,
    TasteType,
    TimeHeatmap,
    TopDish,
)


MIN_ENTRIES_FOR_PERSONALIZATION = 10
HEATMAP_ROWS = ["8 AM", "12 PM", "3 PM", "7 PM", "10 PM"]
HEATMAP_COLS = ["M", "T", "W", "T", "F", "S", "S"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class CategoryStats:
    visits: int = 0
    rating_sum: float = 0.0
    rating_count: int = 0
    tone: str = "bone"

    @property
    def avg_rating(self) -> float:
        return self.rating_sum / self.rating_count if self.rating_count else 0.0


def generate_taste_report(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
    *,
    min_entries_required: int = MIN_ENTRIES_FOR_PERSONALIZATION,
    generated_at: datetime | None = None,
) -> TasteProfileResponse:
    entries = _entries_for_user(user_id, diary_entries)
    if len(entries) < min_entries_required:
        return TasteProfileInsufficient(
            has_enough_data=False,
            min_entries_required=min_entries_required,
            current_entries=len(entries),
        )

    computed_at = generated_at or datetime.now(timezone.utc)
    category_stats = _category_stats(entries)
    categories = _taste_categories(category_stats)
    top_category = categories[0].name if categories else "Food"

    return TasteProfileReady(
        has_enough_data=True,
        min_entries_required=min_entries_required,
        current_entries=len(entries),
        computed_at=computed_at,
        type=_taste_type(top_category),
        summary=_taste_summary(entries, computed_at),
        categories=categories,
        time_heatmap=_time_heatmap(entries),
        flavor_lean=_flavor_lean(category_stats),
        top_dishes=_top_dishes(entries),
        insights=[_primary_insight(entries, top_category)],
    )


def generate_recommendations(
    user_id: str,
    context: RecommendationContext,
    *,
    limit: int = MIN_ENTRIES_FOR_PERSONALIZATION,
    min_entries_required: int = MIN_ENTRIES_FOR_PERSONALIZATION,
) -> RecommendedResponse:
    entries = _entries_for_user(user_id, context.diary_entries)
    based_on_entries = len(entries)
    if based_on_entries < min_entries_required:
        return RecommendedResponse(
            items=[],
            based_on_entries=based_on_entries,
            has_enough_data=False,
        )

    category_stats = _category_stats(entries)
    visited = {entry.restaurant.id for entry in entries}
    exposure_history = set(context.exposure_history)
    scored = []
    for candidate in context.candidate_restaurants:
        if candidate.id in visited:
            continue
        score = _recommendation_score(candidate, category_stats, exposure_history)
        scored.append((score, candidate))

    scored.sort(key=lambda item: (-item[0], item[1].distance_m, item[1].name))
    items = [
        RecommendedRestaurant(
            **candidate.model_dump(),
            reason=_recommendation_reason(candidate, category_stats),
        )
        for _, candidate in scored[:limit]
    ]
    return RecommendedResponse(
        items=items,
        based_on_entries=based_on_entries,
        has_enough_data=True,
    )


def _entries_for_user(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
) -> list[DiaryEntryInput]:
    entries = list(diary_entries)
    mismatched = [entry.id for entry in entries if entry.user_id != user_id]
    if mismatched:
        raise ValueError(f"diary_entries include entries for a different user: {mismatched}")
    return entries


def _category_stats(entries: Sequence[DiaryEntryInput]) -> dict[str, CategoryStats]:
    stats: dict[str, CategoryStats] = {}
    for entry in entries:
        category = entry.restaurant.category
        current = stats.get(category, CategoryStats(tone=entry.restaurant.thumbnail_tone))
        rating = entry.rating
        stats[category] = CategoryStats(
            visits=current.visits + 1,
            rating_sum=current.rating_sum + (rating or 0.0),
            rating_count=current.rating_count + (1 if rating is not None else 0),
            tone=current.tone,
        )
    return stats


def _taste_categories(category_stats: dict[str, CategoryStats]) -> list[TasteCategory]:
    max_visits = max((stats.visits for stats in category_stats.values()), default=1)
    categories = [
        TasteCategory(
            name=name,
            weight=round(stats.visits / max_visits, 2),
            visits=stats.visits,
            tone=stats.tone,
        )
        for name, stats in category_stats.items()
    ]
    return sorted(categories, key=lambda category: (-category.weight, category.name))


def _taste_type(top_category: str) -> TasteType:
    labels = {
        "Noodles": (
            "The Broth-Seeker",
            "You're drawn to warm, simmered dishes where texture matters as much as flavor.",
        ),
        "Bakery": (
            "The Golden-Crust Hunter",
            "You come back to buttery, crisp, gently sweet places more than most.",
        ),
        "Cafe": (
            "The Cafe Regular",
            "You prefer comfortable places with steady drinks, snacks, and repeatable rituals.",
        ),
    }
    label, blurb = labels.get(
        top_category,
        (
            "The Curious Plate",
            f"Your diary leans toward {top_category.lower()}, with room for new favorites.",
        ),
    )
    return TasteType(label=label, blurb=blurb)


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


def _flavor_lean(category_stats: dict[str, CategoryStats]) -> FlavorLean:
    weighted = sum(stats.visits * max(stats.avg_rating, 1.0) for stats in category_stats.values())
    total_visits = sum(stats.visits for stats in category_stats.values()) or 1
    base = min(1.0, weighted / (total_visits * 5.0))
    return FlavorLean(
        umami=round(min(1.0, base + 0.18), 2),
        sweet=round(min(1.0, base + 0.02), 2),
        salty=round(min(1.0, base + 0.08), 2),
        sour=round(max(0.0, base - 0.12), 2),
        spicy=round(max(0.0, base - 0.04), 2),
        bitter=round(max(0.0, base - 0.18), 2),
    )


def _top_dishes(entries: Sequence[DiaryEntryInput]) -> list[TopDish]:
    grouped: dict[str, tuple[int, float, int, str]] = {}
    for entry in entries:
        dish = entry.restaurant.signature_dish
        if not dish:
            continue
        visits, rating_sum, rating_count, tone = grouped.get(
            dish,
            (0, 0.0, 0, entry.restaurant.thumbnail_tone),
        )
        grouped[dish] = (
            visits + 1,
            rating_sum + (entry.rating or 0.0),
            rating_count + (1 if entry.rating is not None else 0),
            tone,
        )
    dishes = [
        TopDish(
            name=name,
            visits=visits,
            rating=_round_one_decimal(rating_sum / rating_count) if rating_count else 0.0,
            tone=tone,
        )
        for name, (visits, rating_sum, rating_count, tone) in grouped.items()
    ]
    return sorted(dishes, key=lambda dish: (-(dish.visits * dish.rating), dish.name))[:3]


def _primary_insight(entries: Sequence[DiaryEntryInput], top_category: str) -> str:
    ratings = [entry.rating for entry in entries if entry.rating is not None]
    avg_rating = _round_one_decimal(sum(ratings) / len(ratings)) if ratings else 0.0
    return (
        f"Your strongest pattern is {top_category.lower()}, "
        f"with an average logged rating of {avg_rating}."
    )


def _round_one_decimal(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _recommendation_score(
    candidate: RestaurantInput,
    category_stats: dict[str, CategoryStats],
    exposure_history: set[str],
) -> float:
    max_visits = max((stats.visits for stats in category_stats.values()), default=1)
    stats = category_stats.get(candidate.category)
    content_score = (stats.visits / max_visits) if stats else 0.0
    collaborative_score = 0.0
    context_score = max(0.0, min(1.0, 1.0 - candidate.distance_m / 5000))
    quality_score = candidate.rating / 5.0
    novelty_score = 0.2 if candidate.id in exposure_history else 1.0
    final_score = (
        0.45 * content_score
        + 0.25 * collaborative_score
        + 0.15 * context_score
        + 0.10 * quality_score
        + 0.05 * novelty_score
    )
    return round(final_score, 6)


def _recommendation_reason(
    candidate: RestaurantInput,
    category_stats: dict[str, CategoryStats],
) -> str:
    stats = category_stats.get(candidate.category)
    if stats:
        return (
            f"You logged {stats.visits} {candidate.category.lower()} "
            f"meal{'s' if stats.visits != 1 else ''} with strong ratings."
        )
    if candidate.rating >= 4.5:
        return "Highly rated near you."
    return "Adds variety outside your usual categories."
