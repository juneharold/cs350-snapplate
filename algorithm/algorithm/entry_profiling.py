from __future__ import annotations

from collections import defaultdict

from algorithm.providers import MLProvider, get_configured_ml_provider
from algorithm.schemas import DiaryEntryInput, EntryProfileArtifact
from algorithm.taxonomy import PROFILE_FIELD_NAMES


FIELD_NAMES = PROFILE_FIELD_NAMES

CATEGORY_CUISINES = (
    ("korean", "korean"),
    ("chinese", "chinese"),
    ("japanese", "japanese"),
    ("soba", "japanese"),
    ("western", "western"),
    ("italian", "italian"),
    ("cafe", "cafe_bakery"),
    ("bakery", "cafe_bakery"),
)

CATEGORY_FOOD_TYPES = (
    ("bbq", "bbq"),
    ("noodles", "noodle"),
    ("bakery", "pastry"),
    ("cafe", "coffee"),
    ("set meal", "set_meal"),
    ("diner", "set_meal"),
    ("snacks", "snack"),
    ("dessert", "dessert"),
    ("bar", "drink"),
)

CATEGORY_VENUES = (
    ("korean bbq", "bbq_place"),
    ("bbq", "bbq_place"),
    ("diner", "diner"),
    ("set meal", "diner"),
    ("cafe", "cafe"),
    ("bakery", "bakery"),
    ("bar", "bar"),
    ("dessert", "dessert_shop"),
    ("snacks", "fast_casual"),
    ("noodles", "casual"),
    ("korean", "sit_down"),
    ("chinese", "sit_down"),
    ("japanese", "sit_down"),
    ("western", "sit_down"),
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
    ("fried", "fried"),
    ("dessert", "dessert"),
    ("cake", "dessert"),
    ("snack", "snack"),
    ("tea", "drink"),
    ("juice", "drink"),
)

TEXT_TASTES = (
    ("spicy", "spicy", 0.76),
    ("savory", "savory", 0.74),
    ("umami", "umami", 0.74),
    ("sweet", "sweet", 0.72),
    ("salty", "salty", 0.72),
    ("sour", "sour", 0.72),
    ("bitter", "bitter", 0.72),
    ("buttery", "buttery", 0.72),
    ("smoky", "smoky", 0.72),
    ("crisp", "crisp", 0.7),
    ("rich", "rich", 0.7),
    ("light", "light", 0.7),
    ("fresh", "fresh", 0.7),
    ("creamy", "creamy", 0.7),
    ("chewy", "chewy", 0.7),
)

TEXT_CONTEXTS = (
    ("quick", "quick_meal", 0.72),
    ("solo", "solo_meal", 0.72),
    ("group", "group_meal", 0.72),
    ("casual", "casual", 0.7),
    ("date", "date", 0.7),
    ("study", "study_work", 0.7),
    ("work", "study_work", 0.7),
    ("takeout", "takeout", 0.7),
    ("take-out", "takeout", 0.7),
    ("late night", "late_night", 0.7),
    ("comfort", "comfort_meal", 0.7),
    ("special", "special_occasion", 0.7),
)

TEXT_EMOTIONS = (
    ("satisfying", "satisfied", 0.78),
    ("satisfied", "satisfied", 0.78),
    ("delighted", "delighted", 0.78),
    ("reliable", "reliable", 0.68),
    ("craving", "craving", 0.68),
    ("disappointed", "disappointed", 0.72),
)

IMAGE_CUISINES = (
    ("korean", "korean"),
    ("chinese", "chinese"),
    ("japanese", "japanese"),
    ("western", "western"),
    ("italian", "italian"),
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
    ("dessert", "dessert"),
    ("cake", "dessert"),
    ("snack", "snack"),
    ("tea", "drink"),
    ("juice", "drink"),
)


def profile_diary_entry(
    entry: DiaryEntryInput,
    *,
    ml_provider: MLProvider | None = None,
) -> EntryProfileArtifact:
    values: dict[str, dict[str, float]] = {field_name: {} for field_name in FIELD_NAMES}
    confidence: dict[str, float] = {}
    evidence: dict[str, list[str]] = defaultdict(list)

    _extract_temporal_features(entry, values, confidence, evidence)
    _extract_location_features(entry, values, confidence, evidence)
    _extract_restaurant_metadata(entry, values, confidence, evidence)
    _extract_rating_signal(entry, values, confidence, evidence)
    _extract_text_signal(entry, values, confidence, evidence, ml_provider)
    _extract_image_references(entry, values, confidence, evidence, ml_provider)
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
    if _is_near_campus(restaurant.neighborhood):
        _add(
            values,
            confidence,
            evidence,
            "location_feature",
            "near_campus",
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

    for keyword, venue in CATEGORY_VENUES:
        if keyword in category:
            _add(
                values,
                confidence,
                evidence,
                "venue",
                venue,
                0.8,
                0.8,
                f"restaurant.category: {restaurant.category}",
            )
            break


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
            "delighted",
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
            "satisfied",
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
    ml_provider: MLProvider | None,
) -> None:
    note = entry.note.strip()
    if not note:
        return

    provider = ml_provider or get_configured_ml_provider()
    result = provider.extract_text_profile(_text_profile_input(entry))
    _merge_profile_result(values, confidence, evidence, result)


def _extract_image_references(
    entry: DiaryEntryInput,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
    ml_provider: MLProvider | None,
) -> None:
    if not entry.image_references:
        return

    provider = ml_provider or get_configured_ml_provider()
    for image_reference in entry.image_references:
        result = provider.extract_image_profile(image_reference)
        _merge_profile_result(values, confidence, evidence, result)


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


def _merge_profile_result(
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
    result: object,
) -> None:
    profile = getattr(result, "profile")
    field_confidence = getattr(result, "confidence")
    field_evidence = getattr(result, "evidence")
    for field_name, terms in profile.items():
        for term, score in terms.items():
            sources = field_evidence.get(field_name, [])
            for source in sources:
                _add(
                    values,
                    confidence,
                    evidence,
                    field_name,
                    term,
                    score,
                    field_confidence[field_name],
                    source,
                )


def _text_profile_input(entry: DiaryEntryInput) -> str:
    restaurant = entry.restaurant
    context = [
        f"diary.note: {entry.note.strip()}",
        f"rating: {entry.rating}" if entry.rating is not None else "",
        f"restaurant.name: {restaurant.name}",
        f"restaurant.category: {restaurant.category}",
        f"restaurant.signature_dish: {restaurant.signature_dish}"
        if restaurant.signature_dish
        else "",
    ]
    return "\n".join(item for item in context if item)


def _is_near_campus(value: str) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in ("eoeun", "kaist", "campus"))
