from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone

from algorithm.embedding import deterministic_text_embedding
from algorithm.entry_profiling import (
    CATEGORY_CUISINES,
    CATEGORY_FOOD_TYPES,
    DISH_FOOD_TYPES,
    TEXT_TASTES,
)
from algorithm.schemas import KakaoRestaurantMetadata, RestaurantProfileArtifact


def profile_kakao_restaurant(
    restaurant: KakaoRestaurantMetadata,
    *,
    generated_at: datetime | None = None,
) -> RestaurantProfileArtifact:
    values: dict[str, dict[str, float]] = defaultdict(dict)
    confidence: dict[str, float] = {}
    evidence: dict[str, list[str]] = defaultdict(list)

    _extract_category_signal(restaurant, values, confidence, evidence)
    _extract_dish_signal(restaurant, values, confidence, evidence)
    _extract_tag_signal(restaurant, values, confidence, evidence)
    _extract_location_signal(restaurant, values, confidence, evidence)

    profile = {
        field_name: dict(sorted(terms.items(), key=lambda item: (-item[1], item[0])))
        for field_name, terms in values.items()
        if terms
    }
    generated = generated_at or datetime.now(timezone.utc)
    profile_text = _profile_text(restaurant, profile)

    return RestaurantProfileArtifact(
        restaurant_id=restaurant.id,
        generated_at=generated,
        profile=profile,
        confidence=confidence,
        evidence=dict(evidence),
        profile_text=profile_text,
        embedding=deterministic_text_embedding(profile_text),
    )


def _extract_category_signal(
    restaurant: KakaoRestaurantMetadata,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    category, source_name = _category_source(restaurant)
    if not category:
        return
    normalized = category.lower()
    source = f"{source_name}: {category}"

    for keyword, cuisine in CATEGORY_CUISINES:
        if keyword in normalized:
            _add(values, confidence, evidence, "cuisine", cuisine, 0.85, 0.85, source)

    for keyword, food_type in CATEGORY_FOOD_TYPES:
        if keyword in normalized:
            _add(values, confidence, evidence, "food_type", food_type, 0.8, 0.8, source)

    venue = _venue_term(category)
    if venue:
        _add(values, confidence, evidence, "venue", venue, 0.8, 0.8, source)


def _extract_dish_signal(
    restaurant: KakaoRestaurantMetadata,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    dishes = [restaurant.signature_dish or "", *restaurant.popular_dishes]
    for dish in dishes:
        normalized = dish.lower()
        if not normalized:
            continue
        for keyword, food_type in DISH_FOOD_TYPES:
            if keyword in normalized:
                _add(
                    values,
                    confidence,
                    evidence,
                    "food_type",
                    food_type,
                    0.68,
                    0.68,
                    f"dish: {dish}",
                )


def _extract_tag_signal(
    restaurant: KakaoRestaurantMetadata,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    for tag in restaurant.tags:
        normalized = tag.lower()
        matched_taste = False
        for keyword, term, _ in TEXT_TASTES:
            if keyword in normalized:
                _add(values, confidence, evidence, "taste", term, 0.62, 0.62, f"tag: {tag}")
                matched_taste = True
        if not matched_taste:
            _add(
                values,
                confidence,
                evidence,
                "context",
                _slug(tag),
                0.62,
                0.62,
                f"tag: {tag}",
            )


def _extract_location_signal(
    restaurant: KakaoRestaurantMetadata,
    values: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
) -> None:
    address = restaurant.road_address_name or restaurant.address_name
    if not address:
        return
    term = _location_term(address)
    if term:
        _add(
            values,
            confidence,
            evidence,
            "location_feature",
            term,
            0.55,
            0.55,
            f"address: {address}",
        )


def _category_source(restaurant: KakaoRestaurantMetadata) -> tuple[str, str]:
    if restaurant.category_name:
        return restaurant.category_name, "category_name"
    if restaurant.category:
        return restaurant.category, "category"
    if restaurant.category_group_name:
        return restaurant.category_group_name, "category_group_name"
    return "", "category"


def _venue_term(category: str) -> str:
    segment = category.split(">")[-1].strip()
    term = _slug(segment)
    if term in {"", "food", "restaurant", "restaurants"}:
        return ""
    return term


def _location_term(address: str) -> str:
    tokens = _slug(address).split("_")
    for index, token in enumerate(tokens):
        if token == "dong":
            return "_".join(tokens[: index + 1])
    for token in tokens:
        if not token.isdigit():
            return token
    return ""


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
    values[field_name][term] = max(values[field_name].get(term, 0.0), score)
    confidence[field_name] = max(confidence.get(field_name, 0.0), field_confidence)
    if source not in evidence[field_name]:
        evidence[field_name].append(source)


def _profile_text(
    restaurant: KakaoRestaurantMetadata,
    profile: dict[str, dict[str, float]],
) -> str:
    name = restaurant.place_name or restaurant.name or restaurant.id
    sections = [f"Restaurant {name} profile."]
    for field_name in ("cuisine", "food_type", "taste", "context", "venue", "location_feature"):
        if profile.get(field_name):
            sections.append(f"{field_name}: {_term_text(profile[field_name])}.")
    if len(sections) == 1:
        sections.append("Kakao metadata is sparse; no unsupported taste attributes inferred.")
    return " ".join(sections)


def _term_text(terms: dict[str, float]) -> str:
    return ", ".join(f"{term} {score:.2f}" for term, score in list(terms.items())[:4])


def _slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")
