import pytest


def test_build_profile_provider_can_be_deterministic_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.algorithm.provider import build_profile_provider
    from app.services.algorithm.providers import DeterministicProvider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "deterministic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert isinstance(build_profile_provider(), DeterministicProvider)


def test_build_profile_provider_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.algorithm.provider import build_profile_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "made-up")

    with pytest.raises(RuntimeError, match="unsupported ALGORITHM_PROVIDER"):
        build_profile_provider()


def test_build_profile_provider_requires_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.algorithm.provider import build_profile_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_profile_provider()
