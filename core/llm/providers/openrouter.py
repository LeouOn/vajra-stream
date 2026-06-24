# core/llm/providers/openrouter.py
"""OpenRouter provider (aggregator for many models).

Note: OpenRouter is now lowest-priority so LM Studio (local) wins when running.
The hardcoded default model was removed — google/gemini-2.0-flash-001 returned 404.
Set OPENROUTER_MODEL env var to pick a specific model, or pass default_model explicitly.
"""
import os

from core.llm.base import OpenAICompatibleProvider

# Safe free-tier default that exists on OpenRouter today. Override via
# OPENROUTER_MODEL env var or by passing default_model to the constructor.
_OPENROUTER_DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


class OpenRouterProvider(OpenAICompatibleProvider):
    """Provider for OpenRouter — aggregates multiple model vendors."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        priority: int = 50,
    ) -> None:
        super().__init__(
            name="openrouter",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY", ""),
            base_url=base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=default_model or os.getenv("OPENROUTER_MODEL", _OPENROUTER_DEFAULT_MODEL),
            timeout_seconds=120,
            priority=priority,
        )
