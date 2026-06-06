from __future__ import annotations

from datetime import UTC, datetime

import pytest

import app.services.algorithm as algorithm
from app.config.algorithm import (
    EMBEDDING_MODEL,
    IMAGE_PROFILE_MODEL,
    RECOMMENDATION_SCORE_WEIGHTS,
    TEXT_PROFILE_MODEL,
)
from app.schemas.algorithm import (
    RecommendationContext,
    RecommendationScoreBreakdown,
    TasteProfileReady,
)
from app.services.algorithm import (
    EMBEDDING_DIMENSIONS,
    MIN_ENTRIES_FOR_PERSONALIZATION,
    RECOMMENDATION_LIMIT,
    SUMMARY_MODEL,
    __version__,
    generate_recommendation_artifact,
    generate_recommendations,
    generate_taste_report,
)
from app.services.algorithm.providers import DeterministicProvider
from tests.helpers.demo_fixtures import DEMO_USER_ID, load_demo_recommendation_context


def test_public_imports_expose_stable_scaffold_metadata() -> None:
    assert algorithm.__version__ == __version__
    assert algorithm.ALGORITHM_VERSION
    assert algorithm.MIN_ENTRIES_FOR_PERSONALIZATION == MIN_ENTRIES_FOR_PERSONALIZATION
    assert algorithm.RECOMMENDATION_LIMIT == RECOMMENDATION_LIMIT
    assert algorithm.generate_recommendation_artifact == generate_recommendation_artifact
    assert algorithm.RecommendationScoreBreakdown == RecommendationScoreBreakdown
    assert algorithm.TEXT_PROFILE_MODEL == TEXT_PROFILE_MODEL == "gpt-5.4-mini"
    assert algorithm.IMAGE_PROFILE_MODEL == IMAGE_PROFILE_MODEL == "gpt-5.4-mini"
    assert algorithm.SUMMARY_MODEL == SUMMARY_MODEL == "gpt-5.4-mini"
    assert algorithm.EMBEDDING_MODEL == EMBEDDING_MODEL == "text-embedding-3-large"
    assert algorithm.EMBEDDING_DIMENSIONS == EMBEDDING_DIMENSIONS == 1024
    assert MIN_ENTRIES_FOR_PERSONALIZATION > 0
    assert RECOMMENDATION_LIMIT > 0
    assert set(RECOMMENDATION_SCORE_WEIGHTS) == {
        "content",
        "collaborative",
        "context",
        "quality",
        "novelty",
    }
    assert all(weight >= 0 for weight in RECOMMENDATION_SCORE_WEIGHTS.values())
    assert sum(RECOMMENDATION_SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_demo_fixture_data_validates_and_drives_public_entrypoints() -> None:
    context = load_demo_recommendation_context()
    min_entries_required = len(context.diary_entries)
    recommendation_limit = min(3, len(context.candidate_restaurants))

    assert isinstance(context, RecommendationContext)
    assert min_entries_required > 0
    assert recommendation_limit > 0

    report = generate_taste_report(
        DEMO_USER_ID,
        context.diary_entries,
        min_entries_required=min_entries_required,
        generated_at=datetime(2026, 5, 24, 12, 43, tzinfo=UTC),
        profile_provider=DeterministicProvider(),
    )
    recommendations = generate_recommendations(
        DEMO_USER_ID,
        context,
        limit=recommendation_limit,
        min_entries_required=min_entries_required,
    )

    assert isinstance(report, TasteProfileReady)
    assert report.current_entries == min_entries_required
    assert recommendations.has_enough_data is True
    assert recommendations.based_on_entries == min_entries_required
    assert len(recommendations.items) == recommendation_limit
    assert all("score" not in item.model_dump() for item in recommendations.items)
