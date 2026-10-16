"""
Backend deployment settings: env-var driven (pydantic-settings).

This is the *environment* half of configuration: things that differ between
machines and deployments and are read from the process environment or
``.env`` (database URL, CORS origins, provider API keys, ComfyUI endpoint).
User-editable tuning constants (audio, prayer bowl, hardware) are NOT here;
they live in ``config/settings.py``, the canonical source per ADR 002
(``docs/decisions/002-settings-canonical.md``). Do not mirror those constants
into this class; ``tests/unit/test_backend_settings.py`` fails if you do.

History: these fields used to live in ``backend/app/config.py``, which ADR 002
step 2 turned into a re-export shim and step 3 (2026-10-16) deleted. They sit
in ``config/`` so the lowest layer owns them: ``core/schema.py`` reads
``DATABASE_URL`` without importing ``backend/``.

Import-time contract (relied on by ``tests/conftest.py``):
    ``backend_settings`` is built once, when this module is first imported,
    and pydantic-settings resolves every field at construction. Later changes
    to ``os.environ`` do not move it. The test suite sets ``DATABASE_URL``
    before anything imports this module so every consumer sees the temp DB.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vajra.Stream API"

    # Database
    DATABASE_URL: str = "sqlite:///./vajra_stream.db"

    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # LLM API keys (optional)
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

    # TTS API keys (optional)
    ELEVENLABS_API_KEY: str = ""
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Usage tracking
    LLM_USAGE_TRACKING: str = "true"
    LLM_USAGE_LOG_PATH: str = "./logs/llm_usage.jsonl"

    # ComfyUI: local render engine (backend/core/services/render/)
    COMFYUI_BASE_URL: str = "http://127.0.0.1:8188"
    # Seconds a render job may wait for ComfyUI before it fails (cold model loads are slow).
    RENDER_TIMEOUT_SECONDS: float = 1800.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # Allow extra env vars not defined here
    )


backend_settings = BackendSettings()
