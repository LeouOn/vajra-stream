"""ADR 002 step 3: the ``backend/app/config.py`` shim is gone.

``config/settings.py`` is the single source for the user-editable audio /
hardware / prayer-bowl constants. The env-driven deployment settings live in
``config/backend_settings.py`` and the LLM provider settings in
``config/llm.py``. These tests lock that split in so the historical drift
(``MAX_VOLUME`` 0.5 canonical vs 0.8 in a pydantic mirror) cannot come back.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import config.settings as canonical
from config.backend_settings import BackendSettings, backend_settings
from config.llm import LLMConfig, get_llm_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shim_is_deleted():
    assert not (REPO_ROOT / "backend" / "app" / "config.py").exists()
    assert importlib.util.find_spec("backend.app.config") is None


def test_backend_settings_do_not_mirror_canonical_constants():
    """No field may shadow a config.settings constant (that is how drift starts)."""
    canonical_names = {name for name in vars(canonical) if name.isupper()}
    mirrored = canonical_names & set(BackendSettings.model_fields)
    assert not mirrored, (
        f"BackendSettings re-declares canonical constants {sorted(mirrored)}; "
        "read them from config.settings instead (ADR 002)"
    )


def test_backend_settings_singleton_is_a_backend_settings():
    assert isinstance(backend_settings, BackendSettings)
    assert backend_settings.DATABASE_URL.startswith("sqlite:///")


def test_database_url_env_override(monkeypatch):
    """DATABASE_URL stays env-var driven (a deployment concern, not a constant)."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./override_test.db")
    assert BackendSettings().DATABASE_URL == "sqlite:///./override_test.db"


def test_llm_config_lives_in_config_llm():
    assert isinstance(get_llm_config(), LLMConfig)
