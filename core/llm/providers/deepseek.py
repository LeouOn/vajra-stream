# core/llm/providers/deepseek.py
"""DeepSeek provider (deepseek-v4-flash default — user's preferred fallback)."""

import os

from core.llm.base import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """Provider for DeepSeek's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "deepseek-v4-flash",
        priority: int = 70,
    ) -> None:
        super().__init__(
            name="deepseek",
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            default_model=default_model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            timeout_seconds=120,
            priority=priority,
        )
