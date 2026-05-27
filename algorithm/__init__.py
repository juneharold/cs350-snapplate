from algorithm.contract import generate_recommendations, generate_taste_report
from algorithm.schemas import (
    ALGORITHM_VERSION,
    DiaryEntryInput,
    EntryProfileArtifact,
    RecommendationArtifact,
    RecommendationContext,
    RecommendedResponse,
    RecommendedRestaurant,
    RestaurantInput,
    RestaurantProfileArtifact,
    ScoredRecommendationArtifact,
    TasteProfileInsufficient,
    TasteProfileReady,
    TasteProfileResponse,
    UserProfileArtifact,
)


__all__ = [
    "ALGORITHM_VERSION",
    "DiaryEntryInput",
    "EntryProfileArtifact",
    "RecommendationArtifact",
    "RecommendationContext",
    "RecommendedResponse",
    "RecommendedRestaurant",
    "RestaurantInput",
    "RestaurantProfileArtifact",
    "ScoredRecommendationArtifact",
    "TasteProfileInsufficient",
    "TasteProfileReady",
    "TasteProfileResponse",
    "UserProfileArtifact",
    "generate_recommendations",
    "generate_taste_report",
]
