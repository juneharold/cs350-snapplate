import pytest


def test_build_algorithm_provider_can_be_deterministic_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from algorithm.providers import DeterministicMLProvider

    from app.services.algorithm.provider import build_algorithm_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "deterministic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert isinstance(build_algorithm_provider(), DeterministicMLProvider)


def test_build_algorithm_provider_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.algorithm.provider import build_algorithm_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "made-up")

    with pytest.raises(RuntimeError, match="unsupported ALGORITHM_PROVIDER"):
        build_algorithm_provider()


def test_build_algorithm_provider_requires_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.algorithm.provider import build_algorithm_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_algorithm_provider()
