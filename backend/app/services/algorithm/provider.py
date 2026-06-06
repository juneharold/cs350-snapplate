from __future__ import annotations

from algorithm.providers import DeterministicMLProvider, MLProvider, OpenAIProvider
from openai import OpenAI

from app.config.env import Env


def build_algorithm_provider() -> MLProvider:
    provider = (
        Env.raw_get("ALGORITHM_PROVIDER")
        or Env.raw_get(Env.ALGORITHM_PROVIDER.value)
        or "openai"
    )
    match provider.strip().casefold():
        case "openai":
            api_key = (
                Env.raw_get("OPENAI_API_KEY")
                or Env.raw_get(Env.OPENAI_API_KEY.value)
                or ""
            )
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required when ALGORITHM_PROVIDER=openai")
            return OpenAIProvider(client=OpenAI(api_key=api_key))
        case "deterministic":
            return DeterministicMLProvider()
        case _:
            raise RuntimeError(f"unsupported ALGORITHM_PROVIDER: {provider}")
