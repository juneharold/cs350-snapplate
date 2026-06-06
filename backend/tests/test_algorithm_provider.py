import pytest


def test_configured_algorithm_provider_can_be_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from algorithm.providers import DeterministicMLProvider

    from app.services.algorithm.provider import configured_algorithm_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "deterministic")

    assert isinstance(configured_algorithm_provider(), DeterministicMLProvider)


def test_configured_algorithm_provider_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.algorithm.provider import configured_algorithm_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "made-up")

    with pytest.raises(RuntimeError, match="unsupported ALGORITHM_PROVIDER"):
        configured_algorithm_provider()
