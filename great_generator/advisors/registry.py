"""Advisor registry."""

from __future__ import annotations

from pathlib import Path

from great_generator.advisors.base import Advisor
from great_generator.advisors.noop import NoOpAdvisor


def get_advisor(
    spec: str | None,
    *,
    cache_path: str | Path = ".gg_cache/",
    refresh_cache: bool = False,
) -> Advisor:
    """Return an advisor from a compact string spec."""

    if spec is None or str(spec).strip().lower() in {"", "none"}:
        return NoOpAdvisor()

    text = str(spec).strip()
    provider, separator, model_id = text.partition(":")
    provider = provider.lower()
    if not separator:
        raise ValueError(
            "Advisor spec must be one of none, anthropic:<model>, openai:<model>, "
            "ollama:<model>, transformers:<model-or-path>, or llamacpp:<path>."
        )
    if provider == "anthropic":
        from great_generator.advisors.anthropic import AnthropicAdvisor

        return AnthropicAdvisor(
            model_id=model_id,
            cache_path=cache_path,
            refresh_cache=refresh_cache,
        )
    if provider == "ollama":
        from great_generator.advisors.ollama import OllamaAdvisor

        return OllamaAdvisor(
            model_id=model_id,
            cache_path=cache_path,
            refresh_cache=refresh_cache,
        )
    if provider == "openai":
        from great_generator.advisors.openai import OpenAIAdvisor

        return OpenAIAdvisor(model_id=model_id, cache_path=cache_path, refresh_cache=refresh_cache)
    if provider == "llamacpp":
        from great_generator.advisors.llamacpp import LlamaCppAdvisor

        return LlamaCppAdvisor(
            model_id=model_id, cache_path=cache_path, refresh_cache=refresh_cache
        )
    if provider == "transformers":
        from great_generator.advisors.transformers import TransformersAdvisor

        return TransformersAdvisor(
            model_id=model_id,
            cache_path=cache_path,
            refresh_cache=refresh_cache,
        )
    raise ValueError(
        "Unknown advisor provider "
        f"'{provider}'. Expected none, anthropic, openai, ollama, transformers, or llamacpp."
    )
