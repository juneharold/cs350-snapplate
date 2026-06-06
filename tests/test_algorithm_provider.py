from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from algorithm.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    IMAGE_PROFILE_MODEL,
    SUMMARY_MODEL,
    TEXT_PROFILE_MODEL,
)
from algorithm.providers import (
    DeterministicMLProvider,
    OpenAIProvider,
    get_configured_ml_provider,
)
from algorithm.schemas import ProfileExtractionResult, ProfileSummaryResult


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


class FakeResponses:
    def __init__(self, parsed: object) -> None:
        self.calls: list[dict[str, object]] = []
        self.parsed = parsed

    def parse(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.parsed)


class FakeOpenAIClient:
    def __init__(self, parsed: object) -> None:
        self.responses = FakeResponses(parsed)


def test_deterministic_provider_returns_stable_configured_embeddings() -> None:
    provider = DeterministicMLProvider()

    first = provider.embed_text("Savory noodle profile.")
    second = provider.embed_text("Savory noodle profile.")

    assert len(first) == EMBEDDING_DIMENSIONS
    assert first == second
    assert any(value != 0 for value in first)


def test_deterministic_provider_generates_stable_profile_summary() -> None:
    provider = DeterministicMLProvider()

    summary = provider.generate_profile_summary("taste: spicy 0.80, savory 0.70.")

    assert summary.label
    assert summary.blurb
    assert summary.insights


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


def test_openai_provider_extracts_text_profile_with_redacted_input() -> None:
    parsed = ProfileExtractionResult(
        profile={"taste": {"spicy": 0.82}, "context": {"solo_meal": 0.7}},
        confidence={"taste": 0.9, "context": 0.75},
        evidence={"taste": ["model: spicy wording"], "context": ["model: solo meal"]},
    )
    client = FakeOpenAIClient(parsed)
    provider = OpenAIProvider(client=client)

    result = provider.extract_text_profile(
        "Email june@example.com or call 010-1234-5678. "
        "https://private.example says this was a spicy solo dinner."
    )

    assert result == parsed
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == TEXT_PROFILE_MODEL
    assert call["store"] is False
    request_text = str(call["input"])
    assert "june@example.com" not in request_text
    assert "010-1234-5678" not in request_text
    assert "https://private.example" not in request_text
    assert "spicy solo dinner" in request_text


def test_openai_provider_extracts_image_profile_from_file_id_only() -> None:
    parsed = ProfileExtractionResult(
        profile={"cuisine": {"korean": 0.84}, "food_type": {"stew": 0.74}},
        confidence={"cuisine": 0.86, "food_type": 0.78},
        evidence={"cuisine": ["image: Korean food"], "food_type": ["image: stew bowl"]},
    )
    client = FakeOpenAIClient(parsed)
    provider = OpenAIProvider(client=client)

    result = provider.extract_image_profile("file-food-image-123")

    assert result == parsed
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == IMAGE_PROFILE_MODEL
    request_payload = str(call["input"])
    assert "input_image" in request_payload
    assert "file-food-image-123" in request_payload


def test_openai_provider_rejects_non_file_image_reference() -> None:
    client = FakeOpenAIClient(
        ProfileExtractionResult(
            profile={"food_type": {"noodle": 0.7}},
            confidence={"food_type": 0.7},
            evidence={"food_type": ["image: noodle bowl"]},
        )
    )
    provider = OpenAIProvider(client=client)

    with pytest.raises(ValueError, match="OpenAI file ID"):
        provider.extract_image_profile("https://example.com/noodle.jpg")

    assert client.responses.calls == []


def test_openai_provider_generates_profile_summary_with_redacted_input() -> None:
    parsed = ProfileSummaryResult(
        label="The Spicy Regular",
        blurb="You favor savory meals with a clear spicy lean.",
        insights=["Spicy and savory signals dominate your recent entries."],
    )
    client = FakeOpenAIClient(parsed)
    provider = OpenAIProvider(client=client)

    result = provider.generate_profile_summary(
        "User u_123 taste profile. Contact june@example.com. taste: spicy 0.80."
    )

    assert result == parsed
    call = client.responses.calls[0]
    assert call["model"] == SUMMARY_MODEL
    request_text = str(call["input"])
    assert "june@example.com" not in request_text
    assert "u_123" not in request_text
    assert "taste: spicy 0.80" in request_text


def test_openai_provider_revalidates_malformed_parsed_outputs() -> None:
    client = FakeOpenAIClient(
        {
            "profile": {"taste": {"garlicky": 0.82}},
            "confidence": {"taste": 0.9},
            "evidence": {"taste": ["model: unsupported term"]},
        }
    )
    provider = OpenAIProvider(client=client)

    with pytest.raises(ValidationError):
        provider.extract_text_profile("garlicky pasta")


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
