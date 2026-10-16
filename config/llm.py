"""
LLM provider configuration for the ``core/llm/`` provider layer.

Loaded from env vars with the ``LLM_`` prefix, e.g. ``LLM_DEFAULT_PROVIDER``.
A separate concern from the canonical audio/hardware constants in
``config/settings.py``; relocated here verbatim from ``backend/app/config.py``
when ADR 002 step 3 deleted that shim (2026-10-16).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration loaded from env vars (LLM_ prefix)."""

    default_provider: str = "auto"
    health_check_interval_seconds: int = 30
    model_cache_ttl_seconds: int = 60
    request_timeout_seconds: int = 120
    max_retries: int = 1
    retry_initial_backoff: float = 0.5
    provider_priority: list[str] = [
        "openrouter",
        "lm_studio",
        "deepseek",
        "anthropic",
        "openai",
        "minimax",
        "local",
    ]
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    deepseek_api_key: str | None = None
    minimax_api_key: str | None = None
    lm_studio_base_url: str | None = None
    local_models_dir: str = "./models"

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
    )


_llm_config_instance: LLMConfig | None = None


def get_llm_config() -> LLMConfig:
    """Return the process-wide LLMConfig singleton (lazily instantiated)."""
    global _llm_config_instance
    if _llm_config_instance is None:
        _llm_config_instance = LLMConfig()
    return _llm_config_instance
