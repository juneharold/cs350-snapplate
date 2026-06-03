from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from algorithm.taxonomy import INTERNAL_PROFILE_TAXONOMY, PUBLIC_RESTAURANT_CATEGORIES
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
    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]
    kakao_id: str
    neighborhood: str
    is_bookmarked: bool = False

    @field_validator("category")
    @classmethod
    def require_public_category(cls, value: str) -> str:
        if value not in PUBLIC_RESTAURANT_CATEGORIES:
            raise ValueError(f"unsupported public restaurant category: {value}")
        return value


class DiaryEntryInput(ContractModel):
    id: str
    user_id: str
    captured_at: datetime
    restaurant: RestaurantInput
    rating: Rating | None = None
    note: str = ""
    image_labels: list[str] = Field(default_factory=list)
    image_references: list[str] = Field(default_factory=list)


class SyntheticUser(ContractModel):
    id: str
    label: str
    primary_categories: list[str]


class SyntheticFixtureSet(ContractModel):
    is_synthetic: Literal[True] = True
    generated_at: datetime
    users: list[SyntheticUser]
    restaurants: list[RestaurantInput]
    diary_entries: list[DiaryEntryInput]
    exposure_history: dict[str, list[str]]


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

    @field_validator("name")
    @classmethod
    def require_public_category(cls, value: str) -> str:
        if value not in PUBLIC_RESTAURANT_CATEGORIES:
            raise ValueError(f"unsupported public restaurant category: {value}")
        return value


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


RatingDistribution = dict[str, PositiveInt]


class ProfileExtractionResult(ContractModel):
    profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    confidence: dict[str, Score] = Field(default_factory=dict)
    evidence: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_supported_terms_confidence_and_evidence(self) -> "ProfileExtractionResult":
        _validate_profile_map("profile", self.profile)
        for field_name, terms in self.profile.items():
            if not terms:
                continue
            if field_name not in self.confidence:
                raise ValueError(f"{field_name} requires confidence")
            if not self.evidence.get(field_name):
                raise ValueError(f"{field_name} requires evidence")
        return self


class ProfileSummaryResult(ContractModel):
    label: str
    blurb: str
    insights: list[str] = Field(default_factory=list)


class TasteProfileReady(ContractModel):
    has_enough_data: Literal[True]
    min_entries_required: PositiveInt
    current_entries: PositiveInt
    computed_at: datetime
    type: TasteType
    summary: TasteSummary
    categories: list[TasteCategory]
    rating_distribution: RatingDistribution
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
    peer_diary_entries: list[DiaryEntryInput] = Field(default_factory=list)
    candidate_restaurants: list[RestaurantInput]
    user_profile: UserProfileArtifact | None = None
    restaurant_profiles: list[RestaurantProfileArtifact] = Field(default_factory=list)
    lat: float | None = None
    lng: float | None = None
    exposure_history: list[str] = Field(default_factory=list)
    requested_at: datetime | None = None
    category_filters: list[str] = Field(default_factory=list)
    neighborhood_filters: list[str] = Field(default_factory=list)
    max_distance_m: PositiveInt | None = None

    @field_validator("category_filters")
    @classmethod
    def require_public_category_filters(cls, value: list[str]) -> list[str]:
        unsupported = sorted(set(value) - set(PUBLIC_RESTAURANT_CATEGORIES))
        if unsupported:
            raise ValueError(f"unsupported public restaurant categories: {unsupported}")
        return value


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
        for field_name in INTERNAL_PROFILE_TAXONOMY:
            terms = getattr(self, field_name)
            if not terms:
                continue
            _validate_profile_terms(field_name, terms)
            if field_name not in self.confidence:
                raise ValueError(f"{field_name} requires confidence")
            if not self.evidence.get(field_name):
                raise ValueError(f"{field_name} requires evidence")
        return self


class KakaoRestaurantMetadata(ContractModel):
    id: str
    place_name: str | None = None
    name: str | None = None
    category_name: str | None = None
    category: str | None = None
    category_group_name: str | None = None
    address_name: str | None = None
    road_address_name: str | None = None
    x: str | float | None = None
    y: str | float | None = None
    place_url: str | None = None
    phone: str | None = None
    distance: str | int | None = None
    signature_dish: str | None = None
    popular_dishes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rating: Rating | None = None
    rating_count: PositiveInt | None = None


class UserProfileArtifact(ContractModel):
    user_id: str
    generated_at: datetime
    source_entry_count: PositiveInt
    long_term_profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    short_term_profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    confidence: dict[str, Score] = Field(default_factory=dict)
    evidence: dict[str, list[str]] = Field(default_factory=dict)
    profile_text: str
    long_term_embedding: list[float] = Field(default_factory=list)
    short_term_embedding: list[float] = Field(default_factory=list)
    category_rating_vector: dict[str, float] = Field(default_factory=dict)
    algorithm_version: str = ALGORITHM_VERSION

    @model_validator(mode="after")
    def require_supported_profile_terms(self) -> "UserProfileArtifact":
        _validate_profile_map("long_term_profile", self.long_term_profile)
        _validate_profile_map("short_term_profile", self.short_term_profile)
        return self


class RestaurantProfileArtifact(ContractModel):
    restaurant_id: str
    generated_at: datetime
    profile: dict[str, WeightedTerms] = Field(default_factory=dict)
    confidence: dict[str, Score] = Field(default_factory=dict)
    evidence: dict[str, list[str]] = Field(default_factory=dict)
    profile_text: str
    embedding: list[float] = Field(default_factory=list)
    algorithm_version: str = ALGORITHM_VERSION

    @model_validator(mode="after")
    def require_supported_profile_terms(self) -> "RestaurantProfileArtifact":
        _validate_profile_map("profile", self.profile)
        return self


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
    reason_category: Literal["content", "collaborative", "context", "quality", "novelty"]
    scores: RecommendationScoreBreakdown


class RecommendationArtifact(ContractModel):
    user_id: str
    generated_at: datetime
    based_on_entries: PositiveInt
    has_enough_data: bool
    ranked_items: list[ScoredRecommendationArtifact] = Field(default_factory=list)
    algorithm_version: str = ALGORITHM_VERSION


def _validate_profile_map(
    map_name: str,
    profile: dict[str, WeightedTerms],
) -> None:
    for field_name, terms in profile.items():
        if field_name not in INTERNAL_PROFILE_TAXONOMY:
            raise ValueError(f"{map_name} contains unsupported profile field: {field_name}")
        _validate_profile_terms(f"{map_name}.{field_name}", terms, field_name)


def _validate_profile_terms(
    label: str,
    terms: WeightedTerms,
    taxonomy_field_name: str | None = None,
) -> None:
    field_name = taxonomy_field_name or label
    allowed = set(INTERNAL_PROFILE_TAXONOMY[field_name])
    unsupported = sorted(set(terms) - allowed)
    if unsupported:
        raise ValueError(f"{label} contains unsupported terms: {unsupported}")
