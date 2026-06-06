from __future__ import annotations

from typing import Final


MIN_ENTRIES_FOR_PERSONALIZATION: Final[int] = 10
SHORT_TERM_ENTRY_COUNT: Final[int] = 20
SIMILAR_USER_THRESHOLD: Final[float] = 0.70
MIN_SIMILAR_USERS: Final[int] = 3
RECOMMENDATION_LIMIT: Final[int] = 10
RECOMMENDATION_COOLDOWN_REQUESTS: Final[int] = 20

TEXT_PROFILE_MODEL: Final[str] = "gpt-5.4-mini"
IMAGE_PROFILE_MODEL: Final[str] = "gpt-5.4-mini"
SUMMARY_MODEL: Final[str] = "gpt-5.4-mini"
EMBEDDING_MODEL: Final[str] = "text-embedding-3-large"
EMBEDDING_DIMENSIONS: Final[int] = 1024

RECOMMENDATION_SCORE_WEIGHTS: Final[dict[str, float]] = {
    "content": 0.45,
    "collaborative": 0.25,
    "context": 0.15,
    "quality": 0.10,
    "novelty": 0.05,
}

RECOMMENDATION_EMBEDDING_WEIGHTS: Final[dict[str, float]] = {
    "long_term": 0.70,
    "short_term": 0.30,
}

HEATMAP_ROWS: Final[list[str]] = ["8 AM", "12 PM", "3 PM", "7 PM", "10 PM"]
HEATMAP_COLS: Final[list[str]] = ["M", "T", "W", "T", "F", "S", "S"]
DAY_NAMES: Final[list[str]] = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
