from __future__ import annotations

import os
from typing import Protocol

from algorithm.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    ML_PROVIDER,
)
from algorithm.embedding import deterministic_text_embedding
from algorithm.schemas import ProfileExtractionResult, ProfileSummaryResult


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
        raise NotImplementedError("deterministic profile summaries are not implemented")

    def embed_text(self, text: str) -> list[float]:
        _require_embedding_text(text)
        return deterministic_text_embedding(text, dimensions=EMBEDDING_DIMENSIONS)


class OpenAIProvider:
    def __init__(
        self,
        *,
        client: object | None = None,
        model: str = EMBEDDING_MODEL,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        self._client = client or _build_openai_client()
        self._model = model
        self._dimensions = dimensions

    def extract_text_profile(self, text: str) -> ProfileExtractionResult:
        raise NotImplementedError("OpenAI text profile extraction is not implemented yet")

    def extract_image_profile(self, image_reference: str) -> ProfileExtractionResult:
        raise NotImplementedError("OpenAI image profile extraction is not implemented yet")

    def generate_profile_summary(self, profile_text: str) -> ProfileSummaryResult:
        raise NotImplementedError("OpenAI profile summary generation is not implemented yet")

    def embed_text(self, text: str) -> list[float]:
        _require_embedding_text(text)
        response = self._client.embeddings.create(
            model=self._model,
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
    if not text.strip():
        raise ValueError("embedding text must not be empty")


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
