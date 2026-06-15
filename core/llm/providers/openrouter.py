# core/llm/providers/openrouter.py
"""OpenRouter provider (aggregator for many models)."""
import os

from core.llm.base import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Provider for OpenRouter — aggregates multiple model vendors."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "google/gemini-2.0-flash-001",
        priority: int = 90,
    ) -> None:
        super().__init__(
            name="openrouter",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY", ""),
            base_url=base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=default_model,
            timeout_seconds=120,
            priority=priority,
        )
