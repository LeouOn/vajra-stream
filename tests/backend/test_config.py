"""Tests for LLMConfig env-var-driven settings (Task 1.10)."""

import os

import backend.app.config as config_module
from backend.app.config import LLMConfig, get_llm_config


def _clear_llm_env(monkeypatch):
    """Remove any LLM_-prefixed env vars so tests are deterministic."""
    for key in list(os.environ):
        if key.startswith("LLM_"):
            monkeypatch.delenv(key, raising=False)


def test_llm_config_defaults(monkeypatch):
    """LLMConfig uses sensible defaults when no env vars are set."""
    _clear_llm_env(monkeypatch)

    cfg = LLMConfig()
    assert cfg.default_provider == "auto"
    assert cfg.health_check_interval_seconds == 30
    assert cfg.model_cache_ttl_seconds == 60
    assert cfg.request_timeout_seconds == 120
    assert cfg.max_retries == 1
    assert cfg.retry_initial_backoff == 0.5
    assert cfg.provider_priority == [
        "openrouter",
        "lm_studio",
        "deepseek",
        "anthropic",
        "openai",
        "minimax",
        "local",
    ]
    assert cfg.openai_api_key is None
    assert cfg.anthropic_api_key is None
    assert cfg.openrouter_api_key is None
    assert cfg.deepseek_api_key is None
    assert cfg.minimax_api_key is None
    assert cfg.lm_studio_base_url is None
    assert cfg.local_models_dir == "./models"


def test_llm_config_env_override(monkeypatch):
    """LLM_-prefixed env vars override the corresponding config fields."""
    _clear_llm_env(monkeypatch)

    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_MAX_RETRIES", "5")
    monkeypatch.setenv("LLM_OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "60")

    cfg = LLMConfig()
    assert cfg.default_provider == "openrouter"
    assert cfg.max_retries == 5
    assert cfg.openai_api_key == "sk-test-123"
    assert cfg.request_timeout_seconds == 60


def test_get_llm_config_singleton():
    """get_llm_config() returns the same instance on repeated calls."""
    # Reset the module-level singleton to ensure a clean test.
    config_module._llm_config_instance = None
    try:
        first = get_llm_config()
        second = get_llm_config()
        assert first is second
        assert isinstance(first, LLMConfig)
    finally:
        # Cleanup so other tests are not affected by a cached instance.
        config_module._llm_config_instance = None
