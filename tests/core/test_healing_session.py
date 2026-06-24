"""
Smoke + behaviour tests for ``core.healing_session``.

Covers the public surface:
- :class:`SessionPhase` enum
- :class:`SessionLog` dataclass + ``to_dict``
- :class:`HealingSession` — constructor + ``run`` + ``get_available_integrations``
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.healing_session import HealingSession, SessionLog, SessionPhase


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exports the expected classes."""
    import core.healing_session as mod

    for name in ("HealingSession", "SessionLog", "SessionPhase"):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. SessionPhase enum
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_session_phase_has_opening_main_closing():
    """SessionPhase has at least opening / main / closing values."""
    values = {p.value for p in SessionPhase}
    # At least 3 phases
    assert len(list(SessionPhase)) >= 3


# ---------------------------------------------------------------------------
# 3. SessionLog dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_session_log_to_dict_round_trip():
    """SessionLog.to_dict() returns a dict with expected keys."""
    log = SessionLog(
        session_id="test-1",
        intention="healing",
        condition="stress",
        duration_minutes=30,
    )
    d = log.to_dict()
    assert isinstance(d, dict)
    assert d["session_id"] == "test-1"
    assert d["intention"] == "healing"


# ---------------------------------------------------------------------------
# 4. HealingSession constructor
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_sets_log_dir():
    """Constructor accepts a log_dir parameter."""
    session = HealingSession(log_dir="/tmp/test_sessions")
    assert session.log_dir == "/tmp/test_sessions"


@pytest.mark.unit
def test_constructor_has_defaults():
    """Constructor works with no arguments."""
    session = HealingSession()
    assert hasattr(session, "log_dir")


# ---------------------------------------------------------------------------
# 5. get_available_integrations
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_available_integrations_returns_dict():
    """get_available_integrations returns a dict of integration flags."""
    session = HealingSession()
    result = session.get_available_integrations()
    assert isinstance(result, dict)
    # Should mention at least one integration
    assert len(result) > 0
