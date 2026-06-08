import pytest


def test_build_profile_provider_can_be_deterministic_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config.lifespan import _build_profile_provider
    from app.services.algorithm.providers import DeterministicProvider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "deterministic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert isinstance(_build_profile_provider(), DeterministicProvider)


def test_build_profile_provider_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config.lifespan import _build_profile_provider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "made-up")

    with pytest.raises(RuntimeError, match="unsupported ALGORITHM_PROVIDER"):
        _build_profile_provider()


def test_build_profile_provider_falls_back_to_deterministic_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The openai path with no key falls back to the local provider instead of
    # failing boot, so taste analysis still works in dev/CI/demo without billing.
    from app.config.lifespan import _build_profile_provider
    from app.services.algorithm.providers import DeterministicProvider

    monkeypatch.setenv("ALGORITHM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert isinstance(_build_profile_provider(), DeterministicProvider)
