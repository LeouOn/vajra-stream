# core/llm/providers/minimax.py
"""MiniMax provider (MiniMax M3 default — user's preferred fallback)."""

import os

from core.llm.base import OpenAICompatibleProvider


class MinimaxProvider(OpenAICompatibleProvider):
    """Provider for MiniMax's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "MiniMax-M3",
        priority: int = 40,
    ) -> None:
        super().__init__(
            name="minimax",
            api_key=api_key or os.getenv("MINIMAX_API_KEY", ""),
            base_url=base_url or os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1"),
            default_model=default_model or os.getenv("MINIMAX_MODEL", "MiniMax-M3"),
            timeout_seconds=120,
            priority=priority,
        )
