# core/llm/providers/openai.py
"""OpenAI provider (official API)."""
import os

from core.llm.base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Provider for the official OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
        priority: int = 50,
    ) -> None:
        super().__init__(
            name="openai",
            api_key=api_key or os.getenv("OPENAI_API_KEY", ""),
            base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            default_model=default_model,
            timeout_seconds=120,
            priority=priority,
        )
