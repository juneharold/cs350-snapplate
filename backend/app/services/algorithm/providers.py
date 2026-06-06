from __future__ import annotations

import re
from typing import Any, Protocol, TypeVar

from app.config.algorithm import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    IMAGE_PROFILE_MODEL,
    OPENAI_TIMEOUT_SECONDS,
    SUMMARY_MODEL,
    TEXT_PROFILE_MODEL,
)
from app.config.algorithm_taxonomy import INTERNAL_PROFILE_TAXONOMY
from app.schemas.algorithm import ProfileExtractionResult, ProfileSummaryResult
from app.services.algorithm.embedding import deterministic_text_embedding

TParsed = TypeVar("TParsed", ProfileExtractionResult, ProfileSummaryResult)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_RE = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
COORDINATE_RE = re.compile(r"\b-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}\b")
ID_TOKEN_RE = re.compile(
    r"\b(?:user|u|entry|e|restaurant|r|kakao)_[A-Za-z0-9-]+\b",
    re.IGNORECASE,
)


class ProfileProvider(Protocol):
    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        raise NotImplementedError

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        raise NotImplementedError

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        raise NotImplementedError

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicProvider:
    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        _require_text(text, "diary text")
        return _deterministic_text_profile(text)

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        _require_text(image_reference, "image reference")
        return _deterministic_image_profile(image_reference)

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        _require_text(profile_text, "profile text")
        first_signal = _first_profile_signal(profile_text)
        blurb = "Your profile is based on deterministic structured taste signals."
        if first_signal:
            blurb = f"{blurb} The clearest signal is {first_signal}."
        return ProfileSummaryResult(
            label="The Curious Plate",
            blurb=blurb,
            insights=["Your strongest patterns come from your logged meals and ratings."],
        )

    def embed_text(self, text: str) -> list[float]:
        _require_embedding_text(text)
        return deterministic_text_embedding(text, dimensions=EMBEDDING_DIMENSIONS)


class OpenAIProvider:
    def __init__(
        self,
        *,
        client: Any,
        model: str | None = None,
        text_model: str = TEXT_PROFILE_MODEL,
        image_model: str = IMAGE_PROFILE_MODEL,
        summary_model: str = SUMMARY_MODEL,
        embedding_model: str | None = None,
        dimensions: int = EMBEDDING_DIMENSIONS,
        timeout_seconds: float = OPENAI_TIMEOUT_SECONDS,
    ) -> None:
        if client is None:
            raise ValueError("client is required")
        self._client = client
        self._text_model = text_model
        self._image_model = image_model
        self._summary_model = summary_model
        self._embedding_model = embedding_model or model or EMBEDDING_MODEL
        self._dimensions = dimensions
        self._timeout_seconds = timeout_seconds

    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        redacted_text = _redacted_external_text(text, "diary text")
        response = self._client.responses.parse(
            model=self._text_model,
            instructions=_text_profile_instructions(),
            input=f"Diary text:\n{redacted_text}",
            text_format=ProfileExtractionResult,
            temperature=0,
            store=False,
            timeout=self._timeout_seconds,
        )
        return _validated_parsed_response(response, ProfileExtractionResult)

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        file_id = image_reference.strip()
        if not file_id.startswith("file-"):
            raise ValueError("image_reference must be an OpenAI file ID beginning with 'file-'")
        response = self._client.responses.parse(
            model=self._image_model,
            instructions=_image_profile_instructions(),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Extract normalized food profile terms from this image.",
                        },
                        {
                            "type": "input_image",
                            "file_id": file_id,
                            "detail": "low",
                        },
                    ],
                }
            ],
            text_format=ProfileExtractionResult,
            temperature=0,
            store=False,
            timeout=self._timeout_seconds,
        )
        return _validated_parsed_response(response, ProfileExtractionResult)

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        redacted_text = _redacted_external_text(profile_text, "profile text")
        response = self._client.responses.parse(
            model=self._summary_model,
            instructions=_summary_instructions(),
            input=f"Structured profile text:\n{redacted_text}",
            text_format=ProfileSummaryResult,
            temperature=0,
            store=False,
            timeout=self._timeout_seconds,
        )
        return _validated_parsed_response(response, ProfileSummaryResult)

    def embed_text(self, text: str) -> list[float]:
        _require_embedding_text(text)
        response = self._client.embeddings.create(
            model=self._embedding_model,
            input=text,
            dimensions=self._dimensions,
            encoding_format="float",
        )
        return _validated_embedding(_response_embedding(response), self._dimensions)


def _require_embedding_text(text: str) -> None:
    _require_text(text, "embedding text")


def _require_text(text: str, label: str) -> None:
    if not text.strip():
        raise ValueError(f"{label} must not be empty")


def _redacted_external_text(text: str, label: str) -> str:
    _require_text(text, label)
    redacted = COORDINATE_RE.sub("[coordinate]", text)
    redacted = EMAIL_RE.sub("[email]", redacted)
    redacted = URL_RE.sub("[url]", redacted)
    redacted = PHONE_RE.sub("[phone]", redacted)
    redacted = ID_TOKEN_RE.sub("[id]", redacted)
    return " ".join(redacted.split())


def _validated_parsed_response(response: object, result_type: type[TParsed]) -> TParsed:
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise ValueError("OpenAI structured output did not contain parsed data")
    return result_type.model_validate(parsed)


def _text_profile_instructions() -> str:
    return "\n".join(
        [
            "Extract a SnapPlate diary text profile.",
            "Return only terms supported by the schema.",
            "Allowed profile fields: taste, context, emotion.",
            _allowed_terms_text(("taste", "context", "emotion")),
            "Omit unsupported or weakly evidenced terms.",
            "Every non-empty field must include confidence and evidence.",
            "Evidence must be short and must not include personal identifiers.",
        ]
    )


def _image_profile_instructions() -> str:
    return "\n".join(
        [
            "Extract a SnapPlate food image profile.",
            "Return only terms supported by the schema.",
            "Allowed profile fields: cuisine, food_type.",
            _allowed_terms_text(("cuisine", "food_type")),
            "Omit unsupported or weakly evidenced terms.",
            "Every non-empty field must include confidence and evidence.",
        ]
    )


def _summary_instructions() -> str:
    return (
        "Generate a concise user-facing SnapPlate taste profile summary. "
        "Return a short label, one blurb, and one to three insights. "
        "Ground every claim in the structured profile text and do not mention scores, "
        "raw confidence values, user ids, or backend details."
    )


def _allowed_terms_text(field_names: tuple[str, ...]) -> str:
    sections = [
        f"{field_name}: {', '.join(INTERNAL_PROFILE_TAXONOMY[field_name])}"
        for field_name in field_names
    ]
    return "Allowed terms: " + "; ".join(sections) + "."


DETERMINISTIC_TEXT_TASTES = (
    ("spicy", "spicy", 0.76),
    ("savory", "savory", 0.74),
    ("umami", "umami", 0.74),
    ("sweet", "sweet", 0.72),
    ("salty", "salty", 0.72),
    ("sour", "sour", 0.72),
    ("bitter", "bitter", 0.72),
    ("buttery", "buttery", 0.72),
    ("smoky", "smoky", 0.72),
    ("crisp", "crisp", 0.7),
    ("rich", "rich", 0.7),
    ("light", "light", 0.7),
    ("fresh", "fresh", 0.7),
    ("creamy", "creamy", 0.7),
    ("chewy", "chewy", 0.7),
)

DETERMINISTIC_TEXT_CONTEXTS = (
    ("quick", "quick_meal", 0.72),
    ("solo", "solo_meal", 0.72),
    ("group", "group_meal", 0.72),
    ("casual", "casual", 0.7),
    ("date", "date", 0.7),
    ("study", "study_work", 0.7),
    ("work", "study_work", 0.7),
    ("takeout", "takeout", 0.7),
    ("take-out", "takeout", 0.7),
    ("late night", "late_night", 0.7),
    ("comfort", "comfort_meal", 0.7),
    ("special", "special_occasion", 0.7),
)

DETERMINISTIC_TEXT_EMOTIONS = (
    ("satisfying", "satisfied", 0.78),
    ("satisfied", "satisfied", 0.78),
    ("delighted", "delighted", 0.78),
    ("reliable", "reliable", 0.68),
    ("craving", "craving", 0.68),
    ("disappointed", "disappointed", 0.72),
)

DETERMINISTIC_IMAGE_CUISINES = (
    ("korean", "korean", 0.72),
    ("chinese", "chinese", 0.72),
    ("japanese", "japanese", 0.72),
    ("western", "western", 0.72),
    ("italian", "italian", 0.72),
)

DETERMINISTIC_IMAGE_FOOD_TYPES = (
    ("stew", "stew", 0.72),
    ("rice bowl", "rice_bowl", 0.72),
    ("noodle", "noodle", 0.72),
    ("soba", "noodle", 0.72),
    ("grilled meat", "bbq", 0.72),
    ("bbq", "bbq", 0.72),
    ("pastry", "pastry", 0.72),
    ("croissant", "pastry", 0.72),
    ("bread", "bread", 0.72),
    ("latte", "coffee", 0.72),
    ("coffee", "coffee", 0.72),
    ("dessert", "dessert", 0.72),
    ("cake", "dessert", 0.72),
    ("snack", "snack", 0.72),
    ("tea", "drink", 0.72),
    ("juice", "drink", 0.72),
)


def _deterministic_text_profile(text: str) -> ProfileExtractionResult:
    normalized = text.lower()
    profile: dict[str, dict[str, float]] = {}
    confidence: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}
    for keyword, term, score in DETERMINISTIC_TEXT_TASTES:
        if keyword in normalized:
            _add_deterministic_term(profile, confidence, evidence, "taste", term, score, keyword)
    for keyword, term, score in DETERMINISTIC_TEXT_CONTEXTS:
        if keyword in normalized:
            _add_deterministic_term(profile, confidence, evidence, "context", term, score, keyword)
    for keyword, term, score in DETERMINISTIC_TEXT_EMOTIONS:
        if keyword in normalized:
            _add_deterministic_term(profile, confidence, evidence, "emotion", term, score, keyword)
    return ProfileExtractionResult(profile=profile, confidence=confidence, evidence=evidence)


def _deterministic_image_profile(image_reference: str) -> ProfileExtractionResult:
    normalized = image_reference.lower()
    profile: dict[str, dict[str, float]] = {}
    confidence: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}
    for keyword, term, score in DETERMINISTIC_IMAGE_CUISINES:
        if keyword in normalized:
            _add_deterministic_term(profile, confidence, evidence, "cuisine", term, score, keyword)
    for keyword, term, score in DETERMINISTIC_IMAGE_FOOD_TYPES:
        if keyword in normalized:
            _add_deterministic_term(profile, confidence, evidence, "food_type", term, score, keyword)
    return ProfileExtractionResult(profile=profile, confidence=confidence, evidence=evidence)


def _add_deterministic_term(
    profile: dict[str, dict[str, float]],
    confidence: dict[str, float],
    evidence: dict[str, list[str]],
    field_name: str,
    term: str,
    score: float,
    keyword: str,
) -> None:
    terms = profile.setdefault(field_name, {})
    terms[term] = max(terms.get(term, 0.0), score)
    confidence[field_name] = max(confidence.get(field_name, 0.0), score)
    source = f"note: {keyword}" if field_name in {"taste", "context", "emotion"} else f"image: {keyword}"
    sources = evidence.setdefault(field_name, [])
    if source not in sources:
        sources.append(source)


def _first_profile_signal(profile_text: str) -> str:
    for section in profile_text.split("."):
        if ":" in section:
            _, value = section.split(":", 1)
            signal = value.strip().split(",", 1)[0].strip()
            if signal:
                return signal
    return ""


def _response_embedding(response: object) -> object:
    data = getattr(response, "data", None)
    if not data:
        raise ValueError("embedding response did not contain data")
    first = data[0]
    if isinstance(first, dict):
        return first.get("embedding")
    return getattr(first, "embedding", None)


def _validated_embedding(embedding: object, expected_dimensions: int) -> list[float]:
    if not isinstance(embedding, list):
        raise ValueError("embedding response did not contain a list embedding")
    if len(embedding) != expected_dimensions:
        raise ValueError(
            f"embedding response had {len(embedding)} dimensions; "
            f"expected {expected_dimensions}"
        )
    values: list[float] = []
    for value in embedding:
        if not isinstance(value, (int, float)):
            raise ValueError("embedding response contained a non-numeric value")
        values.append(float(value))
    return values
