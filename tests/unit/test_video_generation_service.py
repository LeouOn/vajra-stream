"""Tests for VideoGenerationService.

Standalone tests — no Vajra.Stream container, event bus, settings, or DB
required. Mirrors the structural pattern of
``test_image_generation_service.py``.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from backend.core.services.video_generation_service import (
    DEFAULT_CONFIG,
    MODEL_SPECS,
    VideoGenerationService,
    create_service_from_env,
)

# ── Construction & config ───────────────────────────────────────────────


def test_default_config_has_safe_defaults():
    assert DEFAULT_CONFIG["enabled"] is False
    assert DEFAULT_CONFIG["default_model"] == "T2V-01"
    assert DEFAULT_CONFIG["daily_cost_cap_usd"] == 2.0
    assert DEFAULT_CONFIG["max_per_hour"] == 2
    assert DEFAULT_CONFIG["default_duration"] == 6
    assert DEFAULT_CONFIG["default_resolution"] == "720P"


def test_model_specs_covers_all_required_models():
    assert "T2V-01" in MODEL_SPECS
    assert "MiniMax-Hailuo-2.3" in MODEL_SPECS
    assert "MiniMax-H3" in MODEL_SPECS

    t2v = MODEL_SPECS["T2V-01"]
    assert t2v["api_version"] == "v1"
    assert t2v["cost_usd"] == 0.50
    assert 6 in t2v["durations"]
    assert "720P" in t2v["resolutions"]

    hailuo = MODEL_SPECS["MiniMax-Hailuo-2.3"]
    assert hailuo["api_version"] == "v1"
    assert hailuo["cost_usd"] == 0.85
    assert 6 in hailuo["durations"]
    assert 10 in hailuo["durations"]

    h3 = MODEL_SPECS["MiniMax-H3"]
    assert h3["api_version"] == "v2"
    assert h3["cost_usd"] == 1.00
    assert "2K" in h3["resolutions"]
    assert "16:9" in h3["ratios"]


def test_constructor_with_no_args_uses_defaults():
    service = VideoGenerationService()
    assert service.config["enabled"] is False
    assert service.config["default_model"] == "T2V-01"
    assert service.config["daily_cost_cap_usd"] == 2.0


def test_constructor_overrides_config():
    service = VideoGenerationService({"enabled": True, "default_model": "MiniMax-H3", "daily_cost_cap_usd": 5.0})
    assert service.config["enabled"] is True
    assert service.config["default_model"] == "MiniMax-H3"
    assert service.config["daily_cost_cap_usd"] == 5.0
    # Other defaults preserved
    assert service.config["max_per_hour"] == DEFAULT_CONFIG["max_per_hour"]


def test_update_config_merges_known_keys():
    service = VideoGenerationService({"enabled": True, "daily_cost_cap_usd": 1.0})
    result = service.update_config({"daily_cost_cap_usd": 3.0})
    assert service.config["daily_cost_cap_usd"] == 3.0
    assert service.config["enabled"] is True  # preserved
    assert result["daily_cost_cap_usd"] == 3.0


def test_update_config_rejects_unknown_keys():
    service = VideoGenerationService()
    with pytest.raises(ValueError, match="unknown config key"):
        service.update_config({"nonsense_key": "value"})


# ── Cost & rate tracking ────────────────────────────────────────────────


def test_cost_stats_initial_zero():
    service = VideoGenerationService()
    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.0
    assert stats["hourly_calls"] == 0


# ── Prompt validation ───────────────────────────────────────────────────


def test_validate_prompt_empty_rejected():
    service = VideoGenerationService()
    result = service.validate_prompt("")
    assert result["ok"] is False


def test_validate_prompt_whitespace_only_rejected():
    service = VideoGenerationService()
    result = service.validate_prompt("   \n\t  ")
    assert result["ok"] is False


def test_validate_prompt_too_short_rejected():
    service = VideoGenerationService()
    result = service.validate_prompt("hi")
    assert result["ok"] is False


def test_validate_prompt_normal_ok():
    service = VideoGenerationService()
    result = service.validate_prompt("A gentle prayer bowl vibration in soft morning light")
    assert result["ok"] is True


def test_validate_prompt_over_length_rejected():
    service = VideoGenerationService({"max_prompt_chars": 50})
    result = service.validate_prompt("word " * 30)  # 150 chars
    assert result["ok"] is False
    assert "char" in result["error"].lower() or "length" in result["error"].lower()


# ── Cost guard ──────────────────────────────────────────────────────────


def test_check_cost_guard_daily_cap_exceeded():
    service = VideoGenerationService({"daily_cost_cap_usd": 0.10})
    # Simulate prior spend that already equals the cap; T2V-01 costs $0.50
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    service._daily_spend[today] = 0.10
    with pytest.raises(RuntimeError, match="daily cost cap"):
        service._check_cost_guard("T2V-01")


def test_check_cost_guard_hourly_limit_exceeded():
    service = VideoGenerationService({"max_per_hour": 2})
    # Simulate 2 calls within the past hour
    now = time.time()
    service._hourly_calls = [now - 100, now - 50]
    with pytest.raises(RuntimeError, match="max_per_hour"):
        service._check_cost_guard("T2V-01")


def test_check_cost_guard_under_limits_passes():
    service = VideoGenerationService({"daily_cost_cap_usd": 2.0, "max_per_hour": 2})
    # No prior spend and no prior calls
    service._check_cost_guard("T2V-01")  # should not raise


# ── Env factory ─────────────────────────────────────────────────────────


def test_create_service_from_env_reads_minimax_key(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-mm-from-env")
    service = create_service_from_env()
    assert service._config["minimax_api_key"] == "sk-mm-from-env"


def test_create_service_from_env_overrides_take_precedence(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-mm-from-env")
    service = create_service_from_env({"minimax_api_key": "sk-mm-override"})
    assert service._config["minimax_api_key"] == "sk-mm-override"
