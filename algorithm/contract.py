from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from algorithm.config import (
    DAY_NAMES,
    EMBEDDING_DIMENSIONS,
    HEATMAP_COLS,
    HEATMAP_ROWS,
    MIN_ENTRIES_FOR_PERSONALIZATION,
    MIN_SIMILAR_USERS,
    RECOMMENDATION_EMBEDDING_WEIGHTS,
    RECOMMENDATION_LIMIT,
    RECOMMENDATION_SCORE_WEIGHTS,
    SIMILAR_USER_THRESHOLD,
)
from algorithm.providers import MLProvider, get_configured_ml_provider
from algorithm.schemas import (
    DiaryEntryInput,
    FlavorLean,
    RecommendationContext,
    RecommendedResponse,
    RecommendedRestaurant,
    RestaurantInput,
    RestaurantProfileArtifact,
    TasteCategory,
    TasteProfileInsufficient,
    TasteProfileReady,
    TasteProfileResponse,
    TasteSummary,
    TasteType,
    TimeHeatmap,
    TopDish,
    UserProfileArtifact,
)
from algorithm.user_profiling import (
    WeightedEntryProfile,
    aggregate_user_profile,
    build_weighted_entry_profiles,
)


@dataclass(frozen=True)
class CategoryStats:
    visits: int = 0
    rating_sum: float = 0.0
    rating_count: int = 0
    tone: str = "bone"
    weight_sum: float = 0.0

    @property
    def avg_rating(self) -> float:
        return self.rating_sum / self.rating_count if self.rating_count else 0.0


def generate_taste_report(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
    *,
    min_entries_required: int = MIN_ENTRIES_FOR_PERSONALIZATION,
    generated_at: datetime | None = None,
    ml_provider: MLProvider | None = None,
) -> TasteProfileResponse:
    entries = _entries_for_user(user_id, diary_entries)
    if len(entries) < min_entries_required:
        return TasteProfileInsufficient(
            has_enough_data=False,
            min_entries_required=min_entries_required,
            current_entries=len(entries),
        )

    computed_at = generated_at or datetime.now(timezone.utc)
    provider = ml_provider or get_configured_ml_provider()
    weighted_entries = build_weighted_entry_profiles(
        user_id,
        entries,
        ml_provider=provider,
    )
    user_profile = aggregate_user_profile(
        user_id,
        entries,
        generated_at=computed_at,
        weighted_entries=weighted_entries,
        ml_provider=provider,
    )
    profile_summary = provider.generate_profile_summary(user_profile.profile_text)
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


def generate_recommendations(
    user_id: str,
    context: RecommendationContext,
    *,
    limit: int = RECOMMENDATION_LIMIT,
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
    similar_user_entries = _similar_user_entries(
        user_id,
        entries,
        context.peer_diary_entries,
    )
    artifact_mode = _uses_recommendation_artifacts(context)
    restaurant_profiles = _restaurant_profiles_by_candidate(context) if artifact_mode else {}
    scored = []
    for candidate in context.candidate_restaurants:
        if candidate.id in visited:
            continue
        restaurant_profile = restaurant_profiles.get(candidate.id)
        score = _recommendation_score(
            candidate,
            category_stats,
            exposure_history,
            similar_user_entries,
            context.user_profile,
            restaurant_profile,
        )
        scored.append((score, candidate))

    scored.sort(key=lambda item: (-item[0], item[1].distance_m, item[1].name))
    selected = _category_diverse_candidates(scored, limit)
    items = [
        RecommendedRestaurant(
            **candidate.model_dump(),
            reason=_recommendation_reason(
                candidate,
                category_stats,
                similar_user_entries,
                restaurant_profiles.get(candidate.id),
            ),
        )
        for candidate in selected
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
            weight_sum=current.weight_sum + 1.0,
        )
    return stats


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
    grouped: dict[str, tuple[int, float, int, str, float]] = {}
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


def _recommendation_score(
    candidate: RestaurantInput,
    category_stats: dict[str, CategoryStats],
    exposure_history: set[str],
    similar_user_entries: Sequence[DiaryEntryInput],
    user_profile: UserProfileArtifact | None,
    restaurant_profile: RestaurantProfileArtifact | None,
) -> float:
    max_visits = max((stats.visits for stats in category_stats.values()), default=1)
    content_score = _content_score(
        candidate,
        category_stats,
        max_visits,
        user_profile,
        restaurant_profile,
    )
    collaborative_score = _collaborative_score(candidate, similar_user_entries)
    context_score = max(0.0, min(1.0, 1.0 - candidate.distance_m / 5000))
    quality_score = candidate.rating / 5.0
    novelty_score = 0.2 if candidate.id in exposure_history else 1.0
    final_score = (
        RECOMMENDATION_SCORE_WEIGHTS["content"] * content_score
        + RECOMMENDATION_SCORE_WEIGHTS["collaborative"] * collaborative_score
        + RECOMMENDATION_SCORE_WEIGHTS["context"] * context_score
        + RECOMMENDATION_SCORE_WEIGHTS["quality"] * quality_score
        + RECOMMENDATION_SCORE_WEIGHTS["novelty"] * novelty_score
    )
    return round(final_score, 6)


def _recommendation_reason(
    candidate: RestaurantInput,
    category_stats: dict[str, CategoryStats],
    similar_user_entries: Sequence[DiaryEntryInput],
    restaurant_profile: RestaurantProfileArtifact | None = None,
) -> str:
    if _similar_user_ratings(candidate, similar_user_entries):
        return f"Similar users also liked this {candidate.category.lower()} place."
    if restaurant_profile is not None:
        return "Matches your taste profile."
    stats = category_stats.get(candidate.category)
    if stats:
        return (
            f"You logged {stats.visits} {candidate.category.lower()} "
            f"meal{'s' if stats.visits != 1 else ''} with strong ratings."
        )
    if candidate.rating >= 4.5:
        return "Highly rated near you."
    return "Adds variety outside your usual categories."


def _category_diverse_candidates(
    scored: Sequence[tuple[float, RestaurantInput]],
    limit: int,
) -> list[RestaurantInput]:
    max_per_category = max(1, (limit + 1) // 2)
    selected: list[RestaurantInput] = []
    deferred: list[RestaurantInput] = []
    category_counts: dict[str, int] = {}

    for _, candidate in scored:
        if len(selected) >= limit:
            break
        count = category_counts.get(candidate.category, 0)
        if count < max_per_category:
            selected.append(candidate)
            category_counts[candidate.category] = count + 1
        else:
            deferred.append(candidate)

    for candidate in deferred:
        if len(selected) >= limit:
            break
        selected.append(candidate)

    return selected


def _similar_user_entries(
    user_id: str,
    entries: Sequence[DiaryEntryInput],
    peer_entries: Sequence[DiaryEntryInput],
) -> list[DiaryEntryInput]:
    active_vector = _category_rating_vector_from_entries(entries)
    if not active_vector or not peer_entries:
        return []

    entries_by_user: dict[str, list[DiaryEntryInput]] = defaultdict(list)
    for entry in peer_entries:
        if entry.user_id != user_id:
            entries_by_user[entry.user_id].append(entry)

    similar_groups = [
        user_entries
        for user_entries in entries_by_user.values()
        if _cosine_similarity(
            active_vector,
            _category_rating_vector_from_entries(user_entries),
        )
        >= SIMILAR_USER_THRESHOLD
    ]
    if len(similar_groups) < MIN_SIMILAR_USERS:
        return []

    return [entry for group in similar_groups for entry in group]


def _category_rating_vector_from_entries(
    entries: Sequence[DiaryEntryInput],
) -> dict[str, float]:
    return {
        category: stats.avg_rating
        for category, stats in _category_stats(entries).items()
        if stats.rating_count
    }


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    terms = set(left) | set(right)
    dot_product = sum(left.get(term, 0.0) * right.get(term, 0.0) for term in terms)
    left_norm = sum(value * value for value in left.values()) ** 0.5
    right_norm = sum(value * value for value in right.values()) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _content_score(
    candidate: RestaurantInput,
    category_stats: dict[str, CategoryStats],
    max_visits: int,
    user_profile: UserProfileArtifact | None,
    restaurant_profile: RestaurantProfileArtifact | None,
) -> float:
    if user_profile is None and restaurant_profile is None:
        stats = category_stats.get(candidate.category)
        return (stats.visits / max_visits) if stats else 0.0
    if user_profile is None or restaurant_profile is None:
        raise ValueError("user_profile and restaurant profile are required together")

    long_term = _normalized_embedding_similarity(
        user_profile.long_term_embedding,
        restaurant_profile.embedding,
    )
    short_term = _normalized_embedding_similarity(
        user_profile.short_term_embedding,
        restaurant_profile.embedding,
    )
    return round(
        RECOMMENDATION_EMBEDDING_WEIGHTS["long_term"] * long_term
        + RECOMMENDATION_EMBEDDING_WEIGHTS["short_term"] * short_term,
        6,
    )


def _uses_recommendation_artifacts(context: RecommendationContext) -> bool:
    return context.user_profile is not None or bool(context.restaurant_profiles)


def _restaurant_profiles_by_candidate(
    context: RecommendationContext,
) -> dict[str, RestaurantProfileArtifact]:
    if context.user_profile is None:
        raise ValueError("user_profile is required when restaurant_profiles are supplied")
    _validate_user_profile_embeddings(context.user_profile)
    if not context.restaurant_profiles:
        raise ValueError("restaurant profile artifacts are required when user_profile is supplied")

    profiles_by_candidate: dict[str, RestaurantProfileArtifact] = {}
    for candidate in context.candidate_restaurants:
        matches = [
            profile
            for profile in context.restaurant_profiles
            if profile.restaurant_id in {candidate.id, candidate.kakao_id}
        ]
        if not matches:
            raise ValueError(f"restaurant profile is required for candidate {candidate.id}")
        if len(matches) > 1:
            raise ValueError(f"restaurant profile is ambiguous for candidate {candidate.id}")
        _validate_embedding(matches[0].embedding, f"restaurant profile {matches[0].restaurant_id}")
        profiles_by_candidate[candidate.id] = matches[0]
    return profiles_by_candidate


def _validate_user_profile_embeddings(user_profile: UserProfileArtifact) -> None:
    _validate_embedding(user_profile.long_term_embedding, "user long-term embedding")
    _validate_embedding(user_profile.short_term_embedding, "user short-term embedding")


def _validate_embedding(embedding: Sequence[float], label: str) -> None:
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"{label} must have {EMBEDDING_DIMENSIONS} embedding values; "
            f"got {len(embedding)}"
        )
    if not any(value != 0 for value in embedding):
        raise ValueError(f"{label} embedding must not be all zeros")


def _normalized_embedding_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    _validate_embedding(left, "left embedding")
    _validate_embedding(right, "right embedding")
    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    similarity = dot_product / (left_norm * right_norm)
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def _collaborative_score(
    candidate: RestaurantInput,
    similar_user_entries: Sequence[DiaryEntryInput],
) -> float:
    exact_ratings = _similar_user_ratings(candidate, similar_user_entries)
    if exact_ratings:
        return round(sum(exact_ratings) / len(exact_ratings), 6)

    category_ratings = [
        entry.rating / 5.0
        for entry in similar_user_entries
        if entry.restaurant.category == candidate.category and entry.rating is not None
    ]
    if not category_ratings:
        return 0.0
    return round(0.5 * sum(category_ratings) / len(category_ratings), 6)


def _similar_user_ratings(
    candidate: RestaurantInput,
    similar_user_entries: Sequence[DiaryEntryInput],
) -> list[float]:
    return [
        entry.rating / 5.0
        for entry in similar_user_entries
        if entry.restaurant.id == candidate.id and entry.rating is not None
    ]
