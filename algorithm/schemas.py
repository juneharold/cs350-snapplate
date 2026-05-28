from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from algorithm.version import ALGORITHM_VERSION


Score = Annotated[float, Field(ge=0.0, le=1.0)]
Rating = Annotated[float, Field(ge=0.0, le=5.0)]
PositiveInt = Annotated[int, Field(ge=0)]
WeightedTerms = dict[str, Score]

FoodTone = Literal[
    "terra",
    "ochre",
    "rust",
    "moss",
    "cream",
    "char",
    "berry",
    "forest",
    "paprika",
    "butter",
    "hay",
    "bone",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RestaurantInput(ContractModel):
    id: str
    name: str
    category: str
    signature_dish: str | None = None
    rating: Rating
    rating_count: PositiveInt
    distance_m: PositiveInt
    thumbnail_url: str | None = None
    thumbnail_tone: FoodTone
    thumbnail_label: str
    tags: list[str] = Field(default_factory=list)
    lat: float
    lng: float
    kakao_id: str
    neighborhood: str
    is_bookmarked: bool = False


class DiaryEntryInput(ContractModel):
    id: str
    user_id: str
    captured_at: datetime
    restaurant: RestaurantInput
    rating: Rating | None = None
    note: str = ""


class TasteType(ContractModel):
    label: str
    blurb: str


class TasteSummary(ContractModel):
    avg_rating: float
    avg_rating_delta_month: float
    places_count: PositiveInt
    new_places_month: PositiveInt
    top_day_of_week: str


class TasteCategory(ContractModel):
    name: str
    weight: Score
    visits: PositiveInt
    tone: FoodTone


class TimeHeatmap(ContractModel):
    rows: list[str]
    cols: list[str]
    data: list[list[int]]


class FlavorLean(ContractModel):
    umami: Score
    sweet: Score
    salty: Score
    sour: Score
    spicy: Score
    bitter: Score


class TopDish(ContractModel):
    name: str
    rating: float
    visits: PositiveInt
    tone: FoodTone


class TasteProfileReady(ContractModel):
    has_enough_data: Literal[True]
    min_entries_required: PositiveInt
    current_entries: PositiveInt
    computed_at: datetime
    type: TasteType
    summary: TasteSummary
    categories: list[TasteCategory]
    time_heatmap: TimeHeatmap
    flavor_lean: FlavorLean
    top_dishes: list[TopDish]
    insights: list[str]


class TasteProfileInsufficient(ContractModel):
    has_enough_data: Literal[False]
    min_entries_required: PositiveInt
    current_entries: PositiveInt


TasteProfileResponse = TasteProfileReady | TasteProfileInsufficient


class RecommendedRestaurant(RestaurantInput):
    reason: str


class RecommendedResponse(ContractModel):
    items: list[RecommendedRestaurant]
    based_on_entries: PositiveInt
    has_enough_data: bool


class RecommendationContext(ContractModel):
    diary_entries: list[DiaryEntryInput]
    candidate_restaurants: list[RestaurantInput]
    lat: float | None = None
    lng: float | None = None
    exposure_history: list[str] = Field(default_factory=list)


class EntryProfileArtifact(ContractModel):
    entry_id: str
    user_id: str
    captured_at: datetime
    rating: Rating | None = None
    cuisine: WeightedTerms = Field(default_factory=dict)
    food_type: WeightedTerms = Field(default_factory=dict)
    taste: WeightedTerms = Field(default_factory=dict)
    context: WeightedTerms = Field(default_factory=dict)
    venue: WeightedTerms = Field(default_factory=dict)
    emotion: WeightedTerms = Field(default_factory=dict)
    location_feature: WeightedTerms = Field(default_factory=dict)
    temporal_feature: WeightedTerms = Field(default_factory=dict)
    confidence: dict[str, Score] = Field(default_factory=dict)
    evidence: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_confidence_and_evidence(self) -> "EntryProfileArtifact":
        for field_name in (
            "cuisine",
            "food_type",
            "taste",
            "context",
            "venue",
            "emotion",
            "location_feature",
            "temporal_feature",
        ):
            if not getattr(self, field_name):
                continue
            if field_name not in self.confidence:
                raise ValueError(f"{field_name} requires confidence")
            if not self.evidence.get(field_name):
                raise ValueError(f"{field_name} requires evidence")
        return self


class UserProfileArtifact(ContractModel):
    user_id: str
    generated_at: datetime
    source_entry_count: PositiveInt
    long_term_profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    short_term_profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    profile_text: str
    long_term_embedding: list[float] = Field(default_factory=list)
    short_term_embedding: list[float] = Field(default_factory=list)
    category_rating_vector: dict[str, float] = Field(default_factory=dict)
    algorithm_version: str = ALGORITHM_VERSION


class RestaurantProfileArtifact(ContractModel):
    restaurant_id: str
    generated_at: datetime
    profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    profile_text: str
    embedding: list[float] = Field(default_factory=list)
    algorithm_version: str = ALGORITHM_VERSION


class RecommendationScoreBreakdown(ContractModel):
    content_score: Score
    collaborative_score: Score
    context_score: Score
    quality_score: Score
    novelty_score: Score
    final_score: Score


class ScoredRecommendationArtifact(ContractModel):
    restaurant_id: str
    reason: str
    scores: RecommendationScoreBreakdown


class RecommendationArtifact(ContractModel):
    user_id: str
    generated_at: datetime
    based_on_entries: PositiveInt
    has_enough_data: bool
    ranked_items: list[ScoredRecommendationArtifact] = Field(default_factory=list)
    algorithm_version: str = ALGORITHM_VERSION
