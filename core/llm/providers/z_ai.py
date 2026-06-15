# core/llm/providers/z_ai.py
"""Z.AI / GLM provider (OpenAI-compatible)."""
from __future__ import annotations

import os

from core.llm.base import OpenAICompatibleProvider


class ZAIProvider(OpenAICompatibleProvider):
    """Provider for Z.AI's OpenAI-compatible API (GLM 4.5 / 4.6 / etc.).

    Endpoint: https://api.z.ai/api/paas/v4
    Auth: Bearer token via ZAI_API_KEY (also accepts Z_AI_API_KEY).
    Models discovered via GET /models: glm-4.5, glm-4.5-air, glm-4.6, etc.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "glm-4.5",
        priority: int = 65,
    ) -> None:
        # Accept ZAI_API_KEY (current convention) or Z_AI_API_KEY (legacy).
        key = (
            api_key
            or os.getenv("ZAI_API_KEY")
            or os.getenv("Z_AI_API_KEY")
            or ""
        )
        if not key:
            raise ValueError(
                "Z.AI provider requires ZAI_API_KEY or Z_AI_API_KEY "
                "env var (or api_key argument)"
            )
        super().__init__(
            name="z_ai",
            api_key=key,
            base_url=base_url
            or os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4"),
            default_model=default_model,
            timeout_seconds=120,
            priority=priority,
        )
