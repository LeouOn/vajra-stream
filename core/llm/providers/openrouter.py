# core/llm/providers/openrouter.py
"""OpenRouter provider (aggregator for many models)."""

import os

from core.llm.base import OpenAICompatibleProvider
from core.llm.defaults import KNOWN_FEATURED_MODEL_IDS, NEMOTRON_FREE_MODEL_ID


class OpenRouterProvider(OpenAICompatibleProvider):
    """Provider for OpenRouter — aggregates multiple model vendors.

    OpenRouter exposes 300+ models behind a single OpenAI-compatible API.
    Any model id returned by ``GET https://openrouter.ai/api/v1/models``
    is callable; the constants below are the curated, always-known set
    surfaced by the Vajra.Stream model manager UI and the defaults in
    :mod:`core.llm.defaults`.
    """

    #: Free, 550B MoE, 1M context. Default for the blessing loop and
    #: outlook/narrative generation because it costs nothing to run.
    NEMOTRON_FREE_MODEL: str = NEMOTRON_FREE_MODEL_ID

    #: Models Vajra.Stream treats as "always known" regardless of
    #: whether the OpenRouter /models endpoint is currently reachable.
    #: Kept in sync with ``KNOWN_FEATURED_MODEL_IDS`` in
    #: :mod:`core.llm.defaults`.
    KNOWN_FEATURED_MODELS: tuple[str, ...] = tuple(KNOWN_FEATURED_MODEL_IDS)

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = NEMOTRON_FREE_MODEL_ID,
        priority: int = 90,
    ) -> None:
        super().__init__(
            name="openrouter",
            api_key=api_key or os.getenv("OPENROUTER_API_KEY", ""),
            base_url=base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=default_model,
            # 550B reasoning models (Nemotron Ultra) routinely take 1–3 min
            # on the :free pool. 60s used to abort mid-thought and leave
            # Command Center / Outlook looking like they "never returned".
            timeout_seconds=180,
            priority=priority,
            fallback_models=[
                NEMOTRON_FREE_MODEL_ID,
                "poolside/laguna-xs-2.1:free",
                "poolside/laguna-s-2.1:free",
                "deepseek/deepseek-v4-flash",
                "minimax/minimax-m3",
            ],
        )
