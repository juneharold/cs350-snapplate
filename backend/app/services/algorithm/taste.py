from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from algorithm import aggregate_user_profile, generate_taste_report
from algorithm.entry_profiling import profile_diary_entry
from algorithm.providers import ProfileProvider
from algorithm.schemas import (
    DiaryEntryInput,
    EntryProfileArtifact,
    TasteProfileResponse,
    UserProfileArtifact,
)
from algorithm.user_profiling import build_weighted_entry_profiles


@dataclass(frozen=True)
class TasteRefreshArtifacts:
    report: TasteProfileResponse
    entry_profiles: list[EntryProfileArtifact]
    user_profile: UserProfileArtifact | None


def build_taste_refresh_artifacts(
    user_id: str,
    diary_entries: Sequence[DiaryEntryInput],
    *,
    generated_at: datetime,
    profile_provider: ProfileProvider,
    min_entries_required: int,
) -> TasteRefreshArtifacts:
    entries = list(diary_entries)
    if len(entries) < min_entries_required:
        report = generate_taste_report(
            user_id,
            entries,
            min_entries_required=min_entries_required,
            generated_at=generated_at,
            profile_provider=profile_provider,
        )
        return TasteRefreshArtifacts(report=report, entry_profiles=[], user_profile=None)

    entry_profiles = [profile_diary_entry(entry, profile_provider=profile_provider) for entry in entries]
    weighted_entries = build_weighted_entry_profiles(
        user_id,
        entries,
        entry_profiles=entry_profiles,
        profile_provider=profile_provider,
    )
    user_profile = aggregate_user_profile(
        user_id,
        entries,
        generated_at=generated_at,
        weighted_entries=weighted_entries,
        profile_provider=profile_provider,
    )
    report = generate_taste_report(
        user_id,
        entries,
        min_entries_required=min_entries_required,
        generated_at=generated_at,
        profile_provider=profile_provider,
        entry_profiles=entry_profiles,
        user_profile=user_profile,
    )
    return TasteRefreshArtifacts(
        report=report,
        entry_profiles=entry_profiles,
        user_profile=user_profile,
    )
