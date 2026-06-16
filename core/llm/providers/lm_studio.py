# core/llm/providers/lm_studio.py
"""LM Studio local provider (no API key required)."""
import os

from core.llm.base import OpenAICompatibleProvider


class LMStudioProvider(OpenAICompatibleProvider):
    """Provider for LM Studio — local OpenAI-compatible server.

    LM Studio does not require an API key, so a dummy value is used.
    The default timeout is 300s to accommodate slow local inference.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "local-model",
        priority: int = 80,
    ) -> None:
        super().__init__(
            name="lm_studio",
            api_key=api_key or "lm-studio",
            base_url=base_url or os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
            default_model=default_model,
            timeout_seconds=300,
            priority=priority,
        )
