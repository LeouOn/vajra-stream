# core/llm/providers/openrouter.py
"""OpenRouter provider (aggregator for many models).

OpenRouter hosts hundreds of models from many vendors. We configure a
model-level fallback chain so that when the primary model fails (rate
limit, timeout, etc.), the provider tries the next model before giving
up and falling to the next provider in the registry.

The chain is configurable via the OPENROUTER_MODEL and
OPENROUTER_FALLBACK_MODELS env vars. Defaults:
    Primary:   deepseek/deepseek-v4-pro
    Fallback:  deepseek/deepseek-v4-flash
    Last resort: meta-llama/llama-3.1-8b-instruct:free

Override with:
    OPENROUTER_MODEL=minimax/minimax-m3
    OPENROUTER_FALLBACK_MODELS=deepseek/deepseek-v4-flash,nvidia/nemotron:free
"""
import os

from core.llm.base import OpenAICompatibleProvider

_OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-v4-pro"

_OPENROUTER_DEFAULT_FALLBACKS = [
    "deepseek/deepseek-v4-flash",
    "meta-llama/llama-3.1-8b-instruct:free",
]


class OpenRouterProvider(OpenAICompatibleProvider):
    """Provider for OpenRouter — aggregates multiple model vendors.

    Supports a model-level fallback chain: when the primary model fails,
    each model in ``fallback_models`` is tried in sequence before the
    provider gives up and lets the registry try the next provider.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        priority: int = 90,
        fallback_models: list[str] | None = None,
    ) -> None:
        # Parse fallback models from env var or use defaults
        env_fallbacks = os.getenv("OPENROUTER_FALLBACK_MODELS", "")
        resolved_fallbacks = (
            [m.strip() for m in env_fallbacks.split(",") if m.strip()]
            if env_fallbacks
            else (fallback_models or _OPENROUTER_DEFAULT_FALLBACKS)
        )

        super().__init__(
            name="openrouter",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY", ""),
            base_url=base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=default_model or os.getenv("OPENROUTER_MODEL", _OPENROUTER_DEFAULT_MODEL),
            timeout_seconds=120,
            priority=priority,
            fallback_models=resolved_fallbacks,
        )
