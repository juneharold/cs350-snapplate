from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from algorithm.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL
from algorithm.providers import (
    DeterministicMLProvider,
    OpenAIProvider,
    get_configured_ml_provider,
)
from algorithm.schemas import ProfileExtractionResult


class FakeEmbeddingClient:
    def __init__(self, embedding: list[float] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.embedding = embedding or [0.001] * EMBEDDING_DIMENSIONS
        self.embeddings = self

    def create(
        self,
        *,
        model: str,
        input: str,
        dimensions: int,
        encoding_format: str,
    ) -> SimpleNamespace:
        self.calls.append(
            {
                "model": model,
                "input": input,
                "dimensions": dimensions,
                "encoding_format": encoding_format,
            }
        )
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=self.embedding,
                )
            ]
        )


def test_deterministic_provider_returns_stable_configured_embeddings() -> None:
    provider = DeterministicMLProvider()

    first = provider.embed_text("Savory noodle profile.")
    second = provider.embed_text("Savory noodle profile.")

    assert len(first) == EMBEDDING_DIMENSIONS
    assert first == second
    assert any(value != 0 for value in first)


def test_configured_provider_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_configured_ml_provider()


def test_openai_provider_sends_embedding_request_shape() -> None:
    client = FakeEmbeddingClient()
    provider = OpenAIProvider(client=client)

    embedding = provider.embed_text("User profile text.")

    assert len(embedding) == EMBEDDING_DIMENSIONS
    assert client.calls == [
        {
            "model": EMBEDDING_MODEL,
            "input": "User profile text.",
            "dimensions": EMBEDDING_DIMENSIONS,
            "encoding_format": "float",
        }
    ]


def test_openai_provider_rejects_wrong_dimension_embedding() -> None:
    client = FakeEmbeddingClient(embedding=[0.001] * (EMBEDDING_DIMENSIONS - 1))
    provider = OpenAIProvider(client=client)

    with pytest.raises(ValueError, match=f"expected {EMBEDDING_DIMENSIONS}"):
        provider.embed_text("User profile text.")


def test_profile_extraction_result_requires_supported_terms_confidence_and_evidence() -> None:
    result = ProfileExtractionResult(
        profile={"taste": {"spicy": 0.82}},
        confidence={"taste": 0.9},
        evidence={"taste": ["model: detected spicy wording"]},
    )

    assert result.profile == {"taste": {"spicy": 0.82}}

    with pytest.raises(ValidationError):
        ProfileExtractionResult(
            profile={"taste": {"garlicky": 0.82}},
            confidence={"taste": 0.9},
            evidence={"taste": ["model: detected unsupported wording"]},
        )

    with pytest.raises(ValidationError):
        ProfileExtractionResult(
            profile={"taste": {"spicy": 0.82}},
            confidence={"taste": 0.9},
            evidence={},
        )
