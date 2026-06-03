from __future__ import annotations

import os
import re
from typing import Protocol, TypeVar

from algorithm.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    IMAGE_PROFILE_MODEL,
    ML_PROVIDER,
    SUMMARY_MODEL,
    TEXT_PROFILE_MODEL,
)
from algorithm.embedding import deterministic_text_embedding
from algorithm.schemas import ProfileExtractionResult, ProfileSummaryResult
from algorithm.taxonomy import INTERNAL_PROFILE_TAXONOMY


TParsed = TypeVar("TParsed", ProfileExtractionResult, ProfileSummaryResult)

OPENAI_TIMEOUT_SECONDS = 30.0

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_RE = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
COORDINATE_RE = re.compile(r"\b-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}\b")
ID_TOKEN_RE = re.compile(
    r"\b(?:user|u|entry|e|restaurant|r|kakao)_[A-Za-z0-9-]+\b",
    re.IGNORECASE,
)


class _OpenAIProfileExtractionResult(ProfileExtractionResult):
    pass


class _OpenAIProfileSummaryResult(ProfileSummaryResult):
    pass


class MLProvider(Protocol):
    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        raise NotImplementedError

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        raise NotImplementedError

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        raise NotImplementedError

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicMLProvider:
    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        raise NotImplementedError("deterministic text extraction is not implemented")

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        raise NotImplementedError("deterministic image extraction is not implemented")

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
        client: object | None = None,
        model: str | None = None,
        text_model: str = TEXT_PROFILE_MODEL,
        image_model: str = IMAGE_PROFILE_MODEL,
        summary_model: str = SUMMARY_MODEL,
        embedding_model: str | None = None,
        dimensions: int = EMBEDDING_DIMENSIONS,
        timeout_seconds: float = OPENAI_TIMEOUT_SECONDS,
    ) -> None:
        self._client = client or _build_openai_client()
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
            text_format=_OpenAIProfileExtractionResult,
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
            text_format=_OpenAIProfileExtractionResult,
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
            text_format=_OpenAIProfileSummaryResult,
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


def get_configured_ml_provider() -> MLProvider:
    if ML_PROVIDER == "openai":
        return OpenAIProvider()
    raise RuntimeError(f"unsupported ML_PROVIDER: {ML_PROVIDER}")


def _build_openai_client() -> object:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to use the OpenAI ML provider")
    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError("openai package is required to use the OpenAI ML provider") from exc
    return OpenAI(api_key=api_key)


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
