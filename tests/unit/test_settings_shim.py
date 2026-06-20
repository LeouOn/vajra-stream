"""
Wave 4 Task 27 — Settings consolidation guard (RED → GREEN).

Per ADR 002 (`docs/decisions/002-settings-canonical.md`) the canonical source
for audio / hardware / prayer-bowl constants is `config/settings.py`.
`backend/app/config.py` is a thin re-export shim: its pydantic ``Settings``
class must agree with the canonical constants — no silent drift.

This test locks in the contract. Before Task 27 the two systems disagreed
(e.g. ``MAX_VOLUME`` was ``0.5`` canonical vs ``0.8`` in the pydantic
mirror), so the assertions below failed. After Task 27 the pydantic
``Settings`` reads its audio/hardware defaults from ``config.settings`` and
the test passes.
"""

from __future__ import annotations

import pytest

# Legacy shim — must agree with canonical for shared constants.
from backend.app.config import (
    LLMConfig,
    Settings,
    get_llm_config,
    settings,
)

# Canonical constants — the single source of truth per ADR 002.
from config.settings import (
    AMPLIFIER_CONNECTED,
    AUDIO_DEVICE,
    BLESSING_FREQUENCIES,
    HARDWARE_LEVEL,
    MAX_VOLUME,
    PRAYER_BOWL_ENVELOPES,
    PRAYER_BOWL_HARMONICS,
    PRAYER_BOWL_MODE,
    SAMPLE_RATE,
)

# ---------------------------------------------------------------------------
# 1. Pydantic Settings mirrors config.settings for shared audio/hardware
#    constants (the drift-hazard set per ADR 002).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field, canonical",
    [
        ("SAMPLE_RATE", SAMPLE_RATE),
        ("AUDIO_DEVICE", AUDIO_DEVICE),
        ("MAX_VOLUME", MAX_VOLUME),  # the historical drift point: 0.5 vs 0.8
        ("PRAYER_BOWL_MODE", PRAYER_BOWL_MODE),
        ("PRAYER_BOWL_HARMONICS", PRAYER_BOWL_HARMONICS),
        ("PRAYER_BOWL_ENVELOPES", PRAYER_BOWL_ENVELOPES),
        ("HARDWARE_LEVEL", HARDWARE_LEVEL),
        ("AMPLIFIER_CONNECTED", AMPLIFIER_CONNECTED),
        ("BLESSING_FREQUENCIES", BLESSING_FREQUENCIES),
    ],
)
def test_settings_field_matches_canonical(field, canonical):
    """Each shared constant must match `config.settings` (ADR 002)."""
    assert getattr(Settings(), field) == canonical, (
        f"Settings().{field} drifted from config.settings.{field}: "
        f"backend has {getattr(Settings(), field)!r}, canonical is {canonical!r}"
    )


# ---------------------------------------------------------------------------
# 2. The instance alias `settings` exposes the same values as the class.
# ---------------------------------------------------------------------------


def test_settings_instance_matches_class():
    assert settings.SAMPLE_RATE == Settings().SAMPLE_RATE
    assert settings.MAX_VOLUME == Settings().MAX_VOLUME
    assert settings.PRAYER_BOWL_MODE == Settings().PRAYER_BOWL_MODE


# ---------------------------------------------------------------------------
# 3. Canonical constants are re-exported from the shim (so legacy importers
#    that do `from backend.app.config import MAX_VOLUME` keep working).
# ---------------------------------------------------------------------------


def test_canonical_constants_re_exported():
    import backend.app.config as cfg

    # These come in via `from config.settings import *`.
    for name in (
        "SAMPLE_RATE",
        "AUDIO_DEVICE",
        "MAX_VOLUME",
        "PRAYER_BOWL_MODE",
        "PRAYER_BOWL_HARMONICS",
        "PRAYER_BOWL_ENVELOPES",
        "HARDWARE_LEVEL",
        "AMPLIFIER_CONNECTED",
        "BLESSING_FREQUENCIES",
    ):
        assert hasattr(cfg, name), f"backend.app.config should re-export {name}"
        assert getattr(cfg, name) == getattr(__import__("config.settings", fromlist=[name]), name)


# ---------------------------------------------------------------------------
# 4. Backend-only concerns (LLM, DB) are preserved — not in canonical scope.
# ---------------------------------------------------------------------------


def test_llm_config_preserved():
    """LLMConfig / get_llm_config remain in backend.app.config (different concern)."""
    assert isinstance(get_llm_config(), LLMConfig)
    assert Settings().DATABASE_URL.startswith("sqlite:///")  # still pydantic-driven


def test_database_url_env_override(monkeypatch):
    """DATABASE_URL remains env-var-driven (not a canonical audio constant)."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./override_test.db")
    assert Settings().DATABASE_URL == "sqlite:///./override_test.db"
