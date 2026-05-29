from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from algorithm.schemas import DiaryEntryInput, RecommendationContext, RestaurantInput


DEMO_USER_ID = "u_demo_algorithm"


def load_demo_diary_entries() -> list[DiaryEntryInput]:
    payload = _load_demo_payload()
    return [DiaryEntryInput.model_validate(item) for item in payload["diary_entries"]]


def load_demo_candidate_restaurants() -> list[RestaurantInput]:
    payload = _load_demo_payload()
    return [RestaurantInput.model_validate(item) for item in payload["candidate_restaurants"]]


def load_demo_recommendation_context() -> RecommendationContext:
    payload = _load_demo_payload()
    return RecommendationContext.model_validate(
        {
            "diary_entries": payload["diary_entries"],
            "candidate_restaurants": payload["candidate_restaurants"],
            "lat": payload["lat"],
            "lng": payload["lng"],
            "exposure_history": payload["exposure_history"],
        }
    )


def _load_demo_payload() -> dict[str, Any]:
    fixture_path = files(__package__).joinpath("demo_context.json")
    return json.loads(fixture_path.read_text(encoding="utf-8"))
