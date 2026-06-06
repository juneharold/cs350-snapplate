from __future__ import annotations

from collections.abc import Iterable, Sequence, Set
from math import log2


def precision_at_k(recommended_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    _require_positive_k(k)
    window = recommended_ids[:k]
    if not window:
        return 0.0
    hits = sum(1 for restaurant_id in window if restaurant_id in relevant_ids)
    return hits / k


def ndcg_at_k(recommended_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    _require_positive_k(k)
    dcg = _discounted_gain(
        1.0 if restaurant_id in relevant_ids else 0.0
        for restaurant_id in recommended_ids[:k]
    )
    ideal_hits = min(len(relevant_ids), k)
    ideal_dcg = _discounted_gain(1.0 for _ in range(ideal_hits))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def category_diversity(categories: Sequence[str], k: int) -> float:
    _require_positive_k(k)
    window = categories[:k]
    if not window:
        return 0.0
    return len(set(window)) / len(window)


def repeat_exposure_rate(
    recommended_ids: Sequence[str],
    exposure_history: Sequence[str],
    k: int,
) -> float:
    _require_positive_k(k)
    window = recommended_ids[:k]
    if not window:
        return 0.0
    exposed = set(exposure_history)
    repeats = sum(1 for restaurant_id in window if restaurant_id in exposed)
    return repeats / len(window)


def _discounted_gain(gains: Iterable[float]) -> float:
    return sum(gain / log2(index + 2) for index, gain in enumerate(gains))


def _require_positive_k(k: int) -> None:
    if k <= 0:
        raise ValueError("k must be positive")
