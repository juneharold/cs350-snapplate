from __future__ import annotations

import tomllib
from datetime import datetime, timezone
from pathlib import Path

import algorithm
import pytest
from algorithm import (
    MIN_ENTRIES_FOR_PERSONALIZATION,
    RECOMMENDATION_LIMIT,
    __version__,
    generate_recommendations,
    generate_taste_report,
)
from algorithm.config import RECOMMENDATION_SCORE_WEIGHTS
from algorithm.fixtures import DEMO_USER_ID, load_demo_recommendation_context
from algorithm.schemas import RecommendationContext, TasteProfileReady


def test_public_imports_expose_stable_scaffold_metadata() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())

    assert __version__ == pyproject["project"]["version"]
    assert algorithm.__version__ == __version__
    assert algorithm.ALGORITHM_VERSION
    assert algorithm.MIN_ENTRIES_FOR_PERSONALIZATION == MIN_ENTRIES_FOR_PERSONALIZATION
    assert algorithm.RECOMMENDATION_LIMIT == RECOMMENDATION_LIMIT
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
        generated_at=datetime(2026, 5, 24, 12, 43, tzinfo=timezone.utc),
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
