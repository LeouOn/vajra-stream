# core/llm/bootstrap.py
"""Build a default :class:`ProviderRegistry` from environment variables.

This helper exists so that non-FastAPI callers (scripts, core modules, tests,
the :class:`LegacyLLMIntegration` adapter) can construct a registry without
having access to ``app.state.llm_registry``. The FastAPI lifespan in
``backend/app/main.py`` builds its own registry inline; this function
encapsulates the same env-var-driven registration logic for reuse.

Registration order mirrors provider priority (highest first):

    OpenRouter (90) > LM Studio (80) > DeepSeek (70) > Z.AI (65) >
    Anthropic (60) > OpenAI (50) > MiniMax (40) > Local GGUF (30)

Providers that require credentials are only registered when the relevant
env var is set. Providers that may fail to construct (e.g. missing
optional deps, unreachable endpoints) are wrapped in ``try/except`` so
that a single misconfigured provider never blocks the rest of the chain.
"""
from __future__ import annotations

import logging
import os

from core.llm.providers import (
    AnthropicProvider,
    DeepSeekProvider,
    LMStudioProvider,
    LocalGGUFProvider,
    MinimaxProvider,
    OpenAIProvider,
    OpenRouterProvider,
    ZAIProvider,
)
from core.llm.registry import ProviderRegistry

logger = logging.getLogger(__name__)


def build_default_registry() -> ProviderRegistry:
    """Build a :class:`ProviderRegistry` from env vars.

    Used by non-FastAPI callers (scripts, core modules, tests, and the
    :class:`~core.llm.legacy_adapter.LegacyLLMIntegration` sync adapter).

    Returns:
        A populated :class:`ProviderRegistry`. May contain zero providers
        if no credentials or local models are configured.
    """
    registry = ProviderRegistry(health_cache_ttl=60)

    # OpenRouter — aggregator, highest priority (key required)
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            registry.register(OpenRouterProvider(priority=90))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("OpenRouterProvider registration skipped: %s", e)

    # LM Studio — local server, no API key required. Always attempt
    # registration (the `or True` mirrors the legacy auto-detect behaviour);
    # if the server is unreachable the provider is simply marked unhealthy
    # at health-check time rather than rejected at construction time.
    if os.getenv("LM_STUDIO_BASE_URL") or True:
        try:
            registry.register(LMStudioProvider(priority=80))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("LMStudioProvider registration skipped: %s", e)

    # DeepSeek — OpenAI-compatible cloud API
    if os.getenv("DEEPSEEK_API_KEY"):
        try:
            registry.register(DeepSeekProvider(priority=70))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("DeepSeekProvider registration skipped: %s", e)

    # Z.AI coding plan — Anthropic-protocol endpoint; accepts ZAI_API_KEY,
    # Z_AI_API_KEY (legacy), or ANTHROPIC_AUTH_TOKEN.
    if (
        os.getenv("ZAI_API_KEY")
        or os.getenv("Z_AI_API_KEY")
        or os.getenv("ANTHROPIC_AUTH_TOKEN")
    ):
        try:
            registry.register(ZAIProvider(priority=65))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("ZAIProvider registration skipped: %s", e)

    # Anthropic — native Claude API
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"):
        try:
            registry.register(AnthropicProvider(priority=60))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("AnthropicProvider registration skipped: %s", e)

    # OpenAI — GPT-4o family (also honours OPENAI_BASE_URL for compatible endpoints)
    if os.getenv("OPENAI_API_KEY"):
        try:
            registry.register(OpenAIProvider(priority=50))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("OpenAIProvider registration skipped: %s", e)

    # MiniMax
    if os.getenv("MINIMAX_API_KEY"):
        try:
            registry.register(MinimaxProvider(priority=40))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("MinimaxProvider registration skipped: %s", e)

    # Local GGUF — llama-cpp-python; requires actual model files on disk
    if os.path.isdir(os.getenv("LLM_LOCAL_MODELS_DIR", "./models")):
        try:
            registry.register(LocalGGUFProvider(priority=30))
        except Exception as e:  # pragma: no cover - defensive
            logger.debug("LocalGGUFProvider registration skipped: %s", e)

    return registry


__all__ = ["build_default_registry"]
