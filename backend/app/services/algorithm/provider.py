from __future__ import annotations

from algorithm.providers import DeterministicMLProvider, MLProvider, OpenAIProvider

from app.config.env import Env


def configured_algorithm_provider() -> MLProvider:
    provider = (
        Env.raw_get("ALGORITHM_PROVIDER") or Env.raw_get(Env.ALGORITHM_PROVIDER.value) or "openai"
    )
    match provider.strip().casefold():
        case "openai":
            return OpenAIProvider()
        case "deterministic":
            return DeterministicMLProvider()
        case _:
            raise RuntimeError(f"unsupported ALGORITHM_PROVIDER: {provider}")
