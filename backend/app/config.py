"""
Vajra.Stream Backend Configuration — DEPRECATED SHIM.

Canonical source: ``config/settings.py`` (per ADR 002,
``docs/decisions/002-settings-canonical.md``).

This module is a thin re-export shim kept for one release cycle so existing
importers (`backend/app/main.py`, `backend/app/api/v1/endpoints/outlook.py`,
`backend/app/api/v1/endpoints/locations.py`,
`backend/app/api/v1/endpoints/agent_suggestions.py`,
`backend/core/services/vajra_service.py`, `core/schema.py`,
`modules/outlook.py`) keep working without a flag-day rewrite. It will be
deleted in the release after Task 27 — see ADR 002 Step 3.

Contract preserved here:
  * Audio / hardware / prayer-bowl constants are re-exported verbatim from
    ``config.settings`` — drift is now impossible by construction.
  * The pydantic :class:`Settings` class wraps those same constants so
    ``settings.SAMPLE_RATE`` and friends agree with the canonical module.
    Env-var overrides for these audio/hardware constants are intentionally
    dropped (ADR 002 Consequences); edit ``config/settings.py`` instead.
  * Backend-only concerns (DATABASE_URL, CORS, LLM / TTS / ComfyUI keys,
    LLMConfig / get_llm_config) remain pydantic-driven and env-var
    overridable — they are a *different concern* and have no canonical
    equivalent.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# 1. Re-export the canonical constants.
# ---------------------------------------------------------------------------
# `from config.settings import *` brings in every module-level constant from
# the canonical file. We list the audio/hardware names explicitly as well so
# IDEs / mypy / grep can resolve them (star-import alone is too opaque for a
# public shim). The explicit imports also guard against accidental name
# shadowing lower in this file.
from config.settings import *  # noqa: F401,F403 — re-export canonical constants
from config.settings import (  # noqa: F401 — explicit re-export for tooling
    AMPLIFIER_CONNECTED,
    AUDIO_DEVICE,
    BASS_SHAKER_CONNECTED,
    BLESSING_FREQUENCIES,
    CRYSTAL_COUNT,
    DB_PATH,
    DEFAULT_DURATION,
    DEFAULT_INTENTION,
    GENERATED_CONTENT_PATH,
    GRID_PATTERN,
    HARDWARE_LEVEL,
    KNOWLEDGE_PATH,
    MAX_VOLUME,
    PRAYER_BOWL_ATTACK,
    PRAYER_BOWL_CONFIG,
    PRAYER_BOWL_DECAY,
    PRAYER_BOWL_ENVELOPES,
    PRAYER_BOWL_HARMONICS,
    PRAYER_BOWL_MODE,
    PRAYER_BOWL_MODULATION,
    PRAYER_BOWL_RELEASE,
    PRAYER_BOWL_SUSTAIN,
    PURE_SINE_MODE,
    SAMPLE_RATE,
    SESSION_LOGS_PATH,
    SHOW_FREQUENCIES,
    SHOW_TIMER,
    VISUAL_MODE,
    WARNING_ENABLED,
)

# ---------------------------------------------------------------------------
# 2. Pydantic Settings — wraps the canonical constants so legacy importers
#    that do `settings.SAMPLE_RATE` keep working. Audio/hardware defaults
#    come from `config.settings` (env-var override intentionally dropped,
#    per ADR 002). Backend-only fields (DATABASE_URL, CORS, LLM/TTS keys)
#    remain env-var driven.
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    # API Settings (backend-only)
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vajra.Stream API"

    # Database (backend-only — env-var driven)
    DATABASE_URL: str = "sqlite:///./vajra_stream.db"

    # Audio Settings — sourced from config.settings (canonical)
    SAMPLE_RATE: int = SAMPLE_RATE
    AUDIO_DEVICE: str = AUDIO_DEVICE
    MAX_VOLUME: float = MAX_VOLUME

    # Prayer Bowl Settings — sourced from config.settings (canonical)
    PRAYER_BOWL_MODE: bool = PRAYER_BOWL_MODE
    PRAYER_BOWL_HARMONICS: bool = PRAYER_BOWL_HARMONICS
    PRAYER_BOWL_ENVELOPES: bool = PRAYER_BOWL_ENVELOPES

    # Hardware — sourced from config.settings (canonical)
    HARDWARE_LEVEL: int = HARDWARE_LEVEL
    AMPLIFIER_CONNECTED: bool = AMPLIFIER_CONNECTED

    # Default Frequencies — sourced from config.settings (canonical)
    BLESSING_FREQUENCIES: list = list(BLESSING_FREQUENCIES)

    # CORS (backend-only — env-var driven)
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # LLM API Keys (backend-only, optional — used by core/llm_integration.py)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = ""
    ANTHROPIC_API_KEY: str = ""
    LM_STUDIO_BASE_URL: str = "http://127.0.0.1:1234"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = ""

    # TTS API Keys (backend-only, optional)
    ELEVENLABS_API_KEY: str = ""
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Usage Tracking (backend-only)
    LLM_USAGE_TRACKING: str = "true"
    LLM_USAGE_LOG_PATH: str = "./logs/llm_usage.jsonl"

    # ComfyUI (backend-only)
    COMFYUI_BASE_URL: str = "http://127.0.0.1:8188"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",  # Allow extra env vars not defined here
    }


settings = Settings()


# ---------------------------------------------------------------------------
# 3. LLMConfig: env-var-driven settings for the core/llm/ provider layer.
# Loaded from env vars with the LLM_ prefix, e.g. LLM_DEFAULT_PROVIDER.
# Separate concern from the canonical audio/hardware constants — preserved
# verbatim from the pre-shim module.
# ---------------------------------------------------------------------------


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

    class Config:
        env_prefix = "LLM_"
        case_sensitive = False


_llm_config_instance: LLMConfig | None = None


def get_llm_config() -> LLMConfig:
    """Return the process-wide LLMConfig singleton (lazily instantiated)."""
    global _llm_config_instance
    if _llm_config_instance is None:
        _llm_config_instance = LLMConfig()
    return _llm_config_instance
