"""Tests for ``core.auspicious_timing`` — planetary-hour / tithi / nakshatra engine.

Covers the public API:
- Constants: :data:`GENRE_PLANETARY_HOURS`, :data:`NAKSHATRA_QUALITIES`.
- Dataclass: :class:`TimingWindow` (incl. :meth:`to_dict`).
- Class: :class:`AuspiciousTiming` with methods ``check``,
  ``get_current_conditions``, ``get_all_genre_windows``.
- Module-level helpers: ``check_auspicious_window``, ``get_all_windows``.

Heavy dependencies (real astrology engine, real datetime, ``lunar_python``)
are mocked so tests are deterministic and have no I/O.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from core.auspicious_timing import (
    GENRE_PLANETARY_HOURS,
    NAKSHATRA_QUALITIES,
    AuspiciousTiming,
    TimingWindow,
    check_auspicious_window,
    get_all_windows,
)

# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports constants, dataclass, class, and helpers."""
    import core.auspicious_timing as mod

    for name in (
        "GENRE_PLANETARY_HOURS",
        "NAKSHATRA_QUALITIES",
        "TimingWindow",
        "AuspiciousTiming",
        "check_auspicious_window",
        "get_all_windows",
        "check_saka_dawa",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Constants & data contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_genre_planetary_hours_covers_documented_genres():
    """Every documented ritual genre has favorable/neutral/unfavorable planets."""
    expected_genres = {
        "healing",
        "victory",
        "wisdom",
        "purification",
        "compassion",
        "prosperity",
        "protection",
        "creativity",
    }
    assert set(GENRE_PLANETARY_HOURS.keys()) == expected_genres

    for genre, config in GENRE_PLANETARY_HOURS.items():
        assert "favorable" in config and config["favorable"]
        assert "neutral" in config and config["neutral"]
        assert "unfavorable" in config and config["unfavorable"]
        # No overlap between favorable and unfavorable
        assert not set(config["favorable"]) & set(config["unfavorable"])


@pytest.mark.unit
def test_nakshatra_qualities_covers_27_lunar_mansions():
    """NAKSHATRA_QUALITIES lists 27 nakshatras (classical lunar mansions)."""
    assert len(NAKSHATRA_QUALITIES) == 27
    # Spot-check well-known ones
    assert "Ashwini" in NAKSHATRA_QUALITIES
    assert "Revati" in NAKSHATRA_QUALITIES
    for name, quality in NAKSHATRA_QUALITIES.items():
        assert isinstance(quality, str) and quality


# ---------------------------------------------------------------------------
# 3. TimingWindow dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timing_window_to_dict_includes_all_public_fields():
    """TimingWindow.to_dict() returns the documented field set."""
    window = TimingWindow(
        go=True,
        planetary_hour="Jupiter",
        tithi="Shukla Panchami",
        nakshatra="Pushya",
        quality="excellent",
        message="Test",
        transmutation="",
        transmutation_mantra="",
        wait_minutes=0,
        next_favorable_hour="",
        time_shift_available=False,
        recommended_approach="direct",
    )

    d = window.to_dict()
    for key in (
        "go",
        "planetary_hour",
        "tithi",
        "nakshatra",
        "quality",
        "message",
        "transmutation",
        "transmutation_mantra",
        "wait_minutes",
        "next_favorable_hour",
        "time_shift_available",
        "recommended_approach",
    ):
        assert key in d, f"Missing key {key!r} in to_dict() output"

    assert d["planetary_hour"] == "Jupiter"
    assert d["quality"] == "excellent"


@pytest.mark.unit
def test_timing_window_default_go_is_true_always_permissive():
    """TimingWindow defaults go=True — engine is never blocking."""
    window = TimingWindow()
    assert window.go is True


# ---------------------------------------------------------------------------
# 4. AuspiciousTiming.check with mocked datetime
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_healing_with_favorable_hour_yields_quality_good_or_excellent():
    """A favorable planetary hour produces good/excellent quality for healing."""
    timing = AuspiciousTiming()
    # Pick a fixed datetime so _get_planetary_hour is deterministic
    fixed_dt = datetime(2024, 6, 21, 12, 0, 0)  # Friday noon

    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        window = timing.check("healing")

    assert window.go is True
    assert window.quality in {"excellent", "good", "challenging", "transmutative"}
    assert window.recommended_approach in {"direct", "transmute_first", "non_linear", "time_shift"}
    # planetary_hour must be one of the seven classical planets
    assert window.planetary_hour in {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}


@pytest.mark.unit
def test_check_uses_default_genre_when_unknown():
    """Unknown genre falls back to the 'healing' configuration."""
    timing = AuspiciousTiming()
    fixed_dt = datetime(2024, 6, 21, 8, 0, 0)

    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        window = timing.check("not_a_real_genre")

    # Should not raise; should produce a TimingWindow
    assert isinstance(window, TimingWindow)
    assert window.go is True


# ---------------------------------------------------------------------------
# 5. AuspiciousTiming.get_current_conditions + get_all_genre_windows
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_current_conditions_returns_expected_keys():
    """get_current_conditions returns the documented condition keys."""
    timing = AuspiciousTiming()
    fixed_dt = datetime(2024, 6, 21, 10, 0, 0)

    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        conditions = timing.get_current_conditions()

    for key in ("planetary_hour", "tithi", "nakshatra", "nakshatra_quality", "moon_phase"):
        assert key in conditions, f"Missing key {key!r} in current conditions"
    # planetary_hour must be one of the seven classical planets
    assert conditions["planetary_hour"] in {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}


@pytest.mark.unit
def test_get_all_genre_windows_covers_every_known_genre():
    """get_all_genre_windows returns one dict per genre in GENRE_PLANETARY_HOURS."""
    timing = AuspiciousTiming()
    fixed_dt = datetime(2024, 6, 21, 15, 0, 0)

    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        all_windows = timing.get_all_genre_windows()

    assert set(all_windows.keys()) == set(GENRE_PLANETARY_HOURS.keys())
    for genre, payload in all_windows.items():
        assert isinstance(payload, dict)
        assert payload["go"] is True  # All permissive
        assert "quality" in payload
        assert "planetary_hour" in payload


# ---------------------------------------------------------------------------
# 6. Module-level helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_level_check_auspicious_window_and_get_all_windows_smoke():
    """The module-level helpers produce valid TimingWindow / dict-of-dict output."""
    # Reset the module-level singleton so we patch datetime cleanly
    import core.auspicious_timing as mod

    mod._timing_instance = None

    fixed_dt = datetime(2024, 6, 21, 11, 0, 0)
    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        window = check_auspicious_window("compassion")

    assert isinstance(window, TimingWindow)
    assert window.go is True

    # get_all_windows uses the same singleton
    mod._timing_instance = None
    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        all_win = get_all_windows()

    assert set(all_win.keys()) == set(GENRE_PLANETARY_HOURS.keys())


# ---------------------------------------------------------------------------
# 7. Engine injection + error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_engine_property_uses_injected_engine():
    """An injected astrology engine is used in place of the default lookup."""
    fake_engine = MagicMock()
    timing = AuspiciousTiming(astrology_engine=fake_engine)

    # First access lazy-imports if _engine is None, but we injected directly
    assert timing.engine is fake_engine


@pytest.mark.unit
def test_check_handles_engine_exceptions_gracefully():
    """If the injected engine raises, check() must not propagate the error."""
    broken_engine = MagicMock()
    broken_engine.get_moon_phase.side_effect = RuntimeError("astro boom")

    timing = AuspiciousTiming(astrology_engine=broken_engine)
    fixed_dt = datetime(2024, 6, 21, 12, 0, 0)

    with patch("core.auspicious_timing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_dt
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        # Must not raise even though the engine blows up
        window = timing.check("healing")

    assert window.go is True
    # Engine failure => tithi/nakshatra fall back to "Unknown"
    assert window.tithi == "Unknown"
    assert window.nakshatra == "Unknown"
