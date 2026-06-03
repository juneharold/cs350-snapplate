from __future__ import annotations

import pytest

from algorithm.evaluation import (
    category_diversity,
    ndcg_at_k,
    precision_at_k,
    repeat_exposure_rate,
)


def test_precision_at_k_counts_relevant_recommendations_in_the_window() -> None:
    assert precision_at_k(["r1", "r2", "r3"], {"r2", "r4"}, 3) == pytest.approx(1 / 3)


def test_ndcg_at_k_rewards_relevant_items_near_the_top() -> None:
    best = ndcg_at_k(["r1", "r2", "r3"], {"r1", "r2"}, 3)
    weaker = ndcg_at_k(["r3", "r2", "r1"], {"r1", "r2"}, 3)

    assert best == pytest.approx(1.0)
    assert 0 < weaker < best


def test_category_diversity_measures_distinct_categories_in_the_window() -> None:
    assert category_diversity(["Noodles", "Noodles", "Bakery", "Cafe"], 4) == pytest.approx(0.75)


def test_repeat_exposure_rate_measures_recently_seen_recommendations() -> None:
    assert repeat_exposure_rate(["r1", "r2", "r3"], ["r3", "r4"], 3) == pytest.approx(1 / 3)


def test_evaluation_metrics_reject_non_positive_k() -> None:
    with pytest.raises(ValueError, match="k"):
        precision_at_k(["r1"], {"r1"}, 0)

