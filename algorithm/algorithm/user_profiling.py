from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone

from algorithm.config import SHORT_TERM_ENTRY_COUNT
from algorithm.entry_profiling import FIELD_NAMES, profile_diary_entry
from algorithm.providers import ProfileProvider
from algorithm.schemas import (
    DiaryEntryInput,
    EntryProfileArtifact,
    UserProfileArtifact,
    WeightedEntryProfile,
)


def build_weighted_entry_profiles(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
    *,
    profile_provider: ProfileProvider,
    entry_profiles: Sequence[EntryProfileArtifact] | None = None,
) -> list[WeightedEntryProfile]:
    entries = _entries_for_user(user_id, diary_entries)
    profiles = _entry_profiles_for_entries(
        user_id,
        entries,
        entry_profiles,
        profile_provider,
    )
    newest = max((entry.captured_at for entry in entries), default=None)
    return [
        WeightedEntryProfile(
            entry=entry,
            profile=profile,
            weight=round(_entry_weight(entry, profile, newest), 6),
        )
        for entry, profile in zip(entries, profiles, strict=True)
    ]


def aggregate_user_profile(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
    *,
    profile_provider: ProfileProvider,
    generated_at: datetime | None = None,
    short_term_entry_count: int = SHORT_TERM_ENTRY_COUNT,
    entry_profiles: Sequence[EntryProfileArtifact] | None = None,
    weighted_entries: Sequence[WeightedEntryProfile] | None = None,
) -> UserProfileArtifact:
    if entry_profiles is not None and weighted_entries is not None:
        raise ValueError("pass either entry_profiles or weighted_entries, not both")
    if weighted_entries is None:
        weighted = build_weighted_entry_profiles(
            user_id,
            diary_entries,
            profile_provider=profile_provider,
            entry_profiles=entry_profiles,
        )
    else:
        weighted = list(weighted_entries)
    entries = [item.entry for item in weighted]
    _entries_for_user(user_id, entries)

    generated = generated_at or datetime.now(timezone.utc)
    long_term_profile, confidence, evidence = _aggregate_terms(weighted)
    short_term = sorted(weighted, key=lambda item: item.entry.captured_at, reverse=True)[
        :short_term_entry_count
    ]
    short_term_profile, _, _ = _aggregate_terms(short_term)
    category_rating_vector = _category_rating_vector(weighted)
    profile_text = _profile_text(user_id, len(entries), long_term_profile, category_rating_vector)
    short_term_text = _profile_text(user_id, len(short_term), short_term_profile, {})
    return UserProfileArtifact(
        user_id=user_id,
        generated_at=generated,
        source_entry_count=len(entries),
        long_term_profile=long_term_profile,
        short_term_profile=short_term_profile,
        confidence=confidence,
        evidence=evidence,
        profile_text=profile_text,
        long_term_embedding=profile_provider.embed_text(profile_text),
        short_term_embedding=profile_provider.embed_text(short_term_text),
        category_rating_vector=category_rating_vector,
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


def _entry_profiles_for_entries(
    user_id: str,
    entries: Sequence[DiaryEntryInput],
    entry_profiles: Sequence[EntryProfileArtifact] | None,
    profile_provider: ProfileProvider,
) -> list[EntryProfileArtifact]:
    if entry_profiles is None:
        return [profile_diary_entry(entry, profile_provider=profile_provider) for entry in entries]

    profiles = list(entry_profiles)
    if len(profiles) != len(entries):
        raise ValueError("entry_profiles must match diary_entries")
    for entry, profile in zip(entries, profiles, strict=True):
        if profile.entry_id != entry.id or profile.user_id != user_id:
            raise ValueError("entry_profiles must match diary_entries")
    return profiles


def _entry_weight(
    entry: DiaryEntryInput,
    profile: EntryProfileArtifact,
    newest: datetime | None,
) -> float:
    return (
        _recency_weight(entry, newest)
        * _richness_weight(entry, profile)
        * _confidence_weight(profile)
    )


def _recency_weight(entry: DiaryEntryInput, newest: datetime | None) -> float:
    if newest is None:
        return 1.0
    age_days = max(0.0, (newest - entry.captured_at).total_seconds() / 86_400)
    return max(0.25, 1.0 / (1.0 + age_days / 45.0))


def _richness_weight(entry: DiaryEntryInput, profile: EntryProfileArtifact) -> float:
    signals = [
        bool(entry.note.strip()),
        bool(entry.image_labels),
        entry.rating is not None,
        bool(entry.restaurant.signature_dish),
        bool(entry.restaurant.category and entry.restaurant.category.lower() != "restaurant"),
        bool(entry.restaurant.neighborhood),
    ]
    profiled_field_count = sum(1 for field_name in FIELD_NAMES if getattr(profile, field_name))
    ratio = (sum(signals) + min(profiled_field_count, len(FIELD_NAMES))) / (
        len(signals) + len(FIELD_NAMES)
    )
    return 0.5 + 0.5 * ratio


def _confidence_weight(profile: EntryProfileArtifact) -> float:
    if not profile.confidence:
        return 0.25
    return sum(profile.confidence.values()) / len(profile.confidence)


def _aggregate_terms(
    weighted_entries: Sequence[WeightedEntryProfile],
) -> tuple[dict[str, dict[str, float]], dict[str, float], dict[str, list[str]]]:
    term_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    denominators: dict[str, float] = defaultdict(float)
    total_weight = sum(item.weight for item in weighted_entries) or 1.0
    evidence: dict[str, list[str]] = defaultdict(list)

    for item in weighted_entries:
        for field_name in FIELD_NAMES:
            terms = getattr(item.profile, field_name)
            if not terms:
                continue
            field_confidence = item.profile.confidence.get(field_name, 0.0)
            weighted_confidence = item.weight * field_confidence
            denominators[field_name] += weighted_confidence
            for term, score in terms.items():
                term_totals[field_name][term] += weighted_confidence * score
            for source in item.profile.evidence.get(field_name, []):
                if source not in evidence[field_name]:
                    evidence[field_name].append(source)

    profile: dict[str, dict[str, float]] = {}
    confidence: dict[str, float] = {}
    for field_name, terms in term_totals.items():
        denominator = denominators[field_name]
        normalized = {
            term: round(value / denominator, 4)
            for term, value in terms.items()
            if denominator > 0
        }
        profile[field_name] = dict(
            sorted(normalized.items(), key=lambda item: (-item[1], item[0]))
        )
        confidence[field_name] = round(min(1.0, denominator / total_weight), 4)

    return profile, confidence, dict(evidence)


def _category_rating_vector(
    weighted_entries: Sequence[WeightedEntryProfile],
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    weights: dict[str, float] = defaultdict(float)
    for item in weighted_entries:
        if item.entry.rating is None:
            continue
        category = item.entry.restaurant.category
        totals[category] += item.weight * item.entry.rating
        weights[category] += item.weight

    return {
        category: round(totals[category] / weights[category], 3)
        for category in sorted(totals)
        if weights[category] > 0
    }


def _profile_text(
    user_id: str,
    source_entry_count: int,
    profile: dict[str, dict[str, float]],
    category_rating_vector: dict[str, float],
) -> str:
    sections = [
        f"User {user_id} taste profile from {source_entry_count} entries.",
    ]
    for field_name in ("cuisine", "food_type", "taste", "context", "venue"):
        if profile.get(field_name):
            sections.append(f"{field_name}: {_term_text(profile[field_name])}.")
    if category_rating_vector:
        category_text = ", ".join(
            f"{category} {rating:.1f}"
            for category, rating in sorted(category_rating_vector.items())
        )
        sections.append(f"category ratings: {category_text}.")
    if len(sections) == 1:
        sections.append("No stable preference signals yet.")
    return " ".join(sections)


def _term_text(terms: dict[str, float]) -> str:
    return ", ".join(
        f"{term} {score:.2f}"
        for term, score in list(terms.items())[:4]
    )
