from __future__ import annotations

import re
from collections import defaultdict

from algorithm.schemas import DiaryEntryInput, EntryProfileArtifact


FIELD_NAMES = (
    "cuisine",
    "food_type",
    "taste",
    "context",
    "venue",
    "emotion",
    "location_feature",
    "temporal_feature",
)

CATEGORY_CUISINES = (
    ("korean", "korean"),
    ("chinese", "chinese"),
    ("japanese", "japanese"),
    ("soba", "japanese"),
)

CATEGORY_FOOD_TYPES = (
    ("bbq", "bbq"),
    ("noodles", "noodle"),
    ("bakery", "bakery"),
    ("cafe", "cafe"),
    ("set meal", "set_meal"),
    ("diner", "set_meal"),
)

DISH_FOOD_TYPES = (
    ("noodle", "noodle"),
    ("soba", "noodle"),
    ("soup", "soup"),
    ("stew", "stew"),
    ("bun", "bread"),
    ("roll", "bread"),
    ("bread", "bread"),
    ("croissant", "pastry"),
    ("latte", "coffee"),
    ("coffee", "coffee"),
    ("rib", "bbq"),
)

TEXT_TASTES = (
    ("spicy", "spicy", 0.76),
    ("savory", "savory", 0.74),
    ("umami", "savory", 0.74),
    ("sweet", "sweet", 0.72),
    ("buttery", "buttery", 0.72),
    ("smoky", "smoky", 0.72),
    ("crisp", "crisp", 0.7),
)

TEXT_CONTEXTS = (
    ("quick", "quick_meal", 0.72),
)

TEXT_EMOTIONS = (
    ("satisfying", "satisfied", 0.78),
    ("satisfied", "satisfied", 0.78),
    ("reliable", "positive", 0.68),
)

IMAGE_CUISINES = (
    ("korean", "korean"),
    ("chinese", "chinese"),
    ("japanese", "japanese"),
)

IMAGE_FOOD_TYPES = (
    ("stew", "stew"),
    ("rice bowl", "rice_bowl"),
    ("noodle", "noodle"),
    ("soba", "noodle"),
    ("grilled meat", "bbq"),
    ("bbq", "bbq"),
    ("pastry", "pastry"),
    ("croissant", "pastry"),
    ("bread", "bread"),
    ("latte", "coffee"),
    ("coffee", "coffee"),
)


def profile_diary_entry(entry: DiaryEntryInput) -> EntryProfileArtifact:
    values: dict[str, dict[str, float]] = {field_name: {} for field_name in FIELD_NAMES}
    confidence: dict[str, float] = {}
    evidence: dict[str, list[str]] = defaultdict(list)

    _extract_temporal_features(entry, values, confidence, evidence)
    _extract_location_features(entry, values, confidence, evidence)
    _extract_restaurant_metadata(entry, values, confidence, evidence)
    _extract_rating_signal(entry, values, confidence, evidence)
    _extract_text_signal(entry, values, confidence, evidence)
    _extract_image_labels(entry, values, confidence, evidence)

    return EntryProfileArtifact(
        entry_id=entry.id,
        user_id=entry.user_id,
        captured_at=entry.captured_at,
        rating=entry.rating,
        cuisine=values["cuisine"],
        food_type=values["food_type"],
        taste=values["taste"],
        context=values["context"],
        venue=values["venue"],
        emotion=values["emotion"],
        location_feature=values["location_feature"],
        temporal_feature=values["temporal_feature"],
        confidence=confidence,
        evidence=dict(evidence),
    )


def _extract_temporal_features(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    captured_at = entry.captured_at
    if captured_at.hour < 11:
        meal_period = "breakfast"
    elif captured_at.hour < 14:
        meal_period = "lunch"
    elif captured_at.hour < 17:
        meal_period = "afternoon"
    elif captured_at.hour < 21:
        meal_period = "dinner"
    else:
        meal_period = "late_night"

    day_type = "weekend" if captured_at.weekday() >= 5 else "weekday"
    source = f"captured_at: {captured_at.isoformat()}"
    _add(values, confidence, evidence, "temporal_feature", meal_period, 1.0, 1.0, source)
    _add(values, confidence, evidence, "temporal_feature", day_type, 1.0, 1.0, source)


def _extract_location_features(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    restaurant = entry.restaurant
    if restaurant.neighborhood:
        _add(
            values,
            confidence,
            evidence,
            "location_feature",
            _slug(restaurant.neighborhood),
            0.9,
            0.9,
            f"restaurant.neighborhood: {restaurant.neighborhood}",
        )
    if restaurant.distance_m <= 800:
        _add(
            values,
            confidence,
            evidence,
            "location_feature",
            "nearby",
            0.8,
            0.8,
            f"restaurant.distance_m: {restaurant.distance_m}",
        )


def _extract_restaurant_metadata(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    restaurant = entry.restaurant
    category = restaurant.category.lower()
    signature_dish = (restaurant.signature_dish or "").lower()

    for keyword, cuisine in CATEGORY_CUISINES:
        if keyword in category:
            _add(
                values,
                confidence,
                evidence,
                "cuisine",
                cuisine,
                0.85,
                0.85,
                f"restaurant.category: {restaurant.category}",
            )

    for keyword, food_type in CATEGORY_FOOD_TYPES:
        if keyword in category:
            _add(
                values,
                confidence,
                evidence,
                "food_type",
                food_type,
                0.8,
                0.8,
                f"restaurant.category: {restaurant.category}",
            )

    for keyword, food_type in DISH_FOOD_TYPES:
        if keyword in signature_dish:
            _add(
                values,
                confidence,
                evidence,
                "food_type",
                food_type,
                0.76,
                0.76,
                f"restaurant.signature_dish: {restaurant.signature_dish}",
            )

    if restaurant.category and category != "restaurant":
        _add(
            values,
            confidence,
            evidence,
            "venue",
            _slug(restaurant.category),
            0.8,
            0.8,
            f"restaurant.category: {restaurant.category}",
        )


def _extract_rating_signal(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    if entry.rating is None:
        return
    if entry.rating >= 4.5:
        _add(
            values,
            confidence,
            evidence,
            "emotion",
            "satisfied",
            0.8,
            0.8,
            f"rating: {entry.rating}",
        )
    elif entry.rating >= 4.0:
        _add(
            values,
            confidence,
            evidence,
            "emotion",
            "positive",
            0.65,
            0.65,
            f"rating: {entry.rating}",
        )
    elif entry.rating <= 2.0:
        _add(
            values,
            confidence,
            evidence,
            "emotion",
            "disappointed",
            0.75,
            0.75,
            f"rating: {entry.rating}",
        )


def _extract_text_signal(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    note = entry.note.lower()
    if not note:
        return

    for keyword, term, score in TEXT_TASTES:
        if keyword in note:
            _add(values, confidence, evidence, "taste", term, score, score, f"note: {keyword}")
    for keyword, term, score in TEXT_CONTEXTS:
        if keyword in note:
            _add(values, confidence, evidence, "context", term, score, score, f"note: {keyword}")
    for keyword, term, score in TEXT_EMOTIONS:
        if keyword in note:
            _add(values, confidence, evidence, "emotion", term, score, score, f"note: {keyword}")


def _extract_image_labels(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    for label in entry.image_labels:
        normalized = label.lower()
        for keyword, cuisine in IMAGE_CUISINES:
            if keyword in normalized:
                _add(
                    values,
                    confidence,
                    evidence,
                    "cuisine",
                    cuisine,
                    0.72,
                    0.72,
                    f"image_label: {label}",
                )
        for keyword, food_type in IMAGE_FOOD_TYPES:
            if keyword in normalized:
                _add(
                    values,
                    confidence,
                    evidence,
                    "food_type",
                    food_type,
                    0.72,
                    0.72,
                    f"image_label: {label}",
                )


def _add(
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
    field_name: str,
    term: str,
    score: float,
    field_confidence: float,
    source: str,
) -> None:
    current_score = values[field_name].get(term, 0.0)
    values[field_name][term] = max(current_score, score)
    confidence[field_name] = max(confidence.get(field_name, 0.0), field_confidence)
    if source not in evidence[field_name]:
        evidence[field_name].append(source)


def _slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")
