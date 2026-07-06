"""
Tests for core/astrology.py — the main astrological calculation engine.

Covers smoke import + behavior of the public API on the AstrologicalCalculator
class. Heavy numerical work is delegated to the Swiss Ephemeris (swisseph),
which is treated as a real dependency since it's installed in the dev env.
"""
from __future__ import annotations

from datetime import datetime

import pytest
import pytz

# Skip cleanly when ``swisseph`` is missing — ``core.astrology`` does an
# unguarded ``import swisseph as swe`` at module load time. Same pattern as
# tests/core/test_astrocartography.py:30.
swisseph = pytest.importorskip("swisseph")

from core.astrology import (  # noqa: E402  (guarded by importorskip above)
    AstrologicalCalculator,
    __version__,
    format_astrological_report,
)

# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def calculator() -> AstrologicalCalculator:
    """Fresh calculator instance for each test."""
    return AstrologicalCalculator()


@pytest.fixture
def fixed_dt() -> datetime:
    """A fixed, well-known datetime (J2000.0 epoch: 2000-01-01 12:00 UTC)."""
    return datetime(2000, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)


@pytest.fixture
def tokyo_location() -> tuple[float, float]:
    """Tokyo coordinates (lat, lon) for house-cusp dependent tests."""
    return (35.6762, 139.6503)


# ─── Smoke ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_module_imports():
    """Smoke test: the module imports and exposes expected public symbols."""
    assert __version__ == "1.0.0"
    assert callable(AstrologicalCalculator)


@pytest.mark.unit
def test_calculator_init_exposes_constants(calculator: AstrologicalCalculator):
    """Constructor populates zodiac signs, planets, Chaldean order, weekday rulers."""
    # 12 Western zodiac signs
    assert len(calculator.SIGNS) == 12
    assert calculator.SIGNS[0] == "Aries"
    assert calculator.SIGNS[-1] == "Pisces"

    # 10 main planets + chiron + north node
    assert "sun" in calculator.PLANETS
    assert "moon" in calculator.PLANETS
    assert "pluto" in calculator.PLANETS

    # Chaldean order is the descending-speed sequence of classical 7
    assert calculator.CHALDEAN_ORDER == [
        "Saturn",
        "Jupiter",
        "Mars",
        "Sun",
        "Venus",
        "Mercury",
        "Moon",
    ]

    # Monday → Moon, Sunday → Sun (the standard Chaldean weekday rulers)
    assert calculator.WEEKDAY_RULERS[0] == "Moon"  # Monday
    assert calculator.WEEKDAY_RULERS[6] == "Sun"  # Sunday


# ─── Behavior: get_julian_day ───────────────────────────────────────────────


@pytest.mark.unit
def test_get_julian_day_handles_naive_and_aware(calculator: AstrologicalCalculator):
    """get_julian_day accepts both tz-aware and naive datetimes.

    Naive datetimes are treated as UTC.
    """
    aware = datetime(2024, 6, 15, 12, 0, 0, tzinfo=pytz.UTC)
    naive = datetime(2024, 6, 15, 12, 0, 0)

    jd_aware = calculator.get_julian_day(aware)
    jd_naive = calculator.get_julian_day(naive)

    # Both should produce the same Julian Day (since naive is treated as UTC).
    assert jd_aware == pytest.approx(jd_naive, rel=1e-9)
    # JD for 2024-06-15 12:00 UTC is 2460477.0 (UTC, swisseph convention).
    assert 2_460_000 < jd_aware < 2_470_000  # sanity: 2024-ish range


# ─── Behavior: get_planetary_positions ─────────────────────────────────────


@pytest.mark.unit
def test_get_planetary_positions_returns_all_main_planets(
    calculator: AstrologicalCalculator, fixed_dt: datetime
):
    """get_planetary_positions returns longitude, sign, degree, formatted for each planet."""
    positions = calculator.get_planetary_positions(fixed_dt)

    # Every non-chiron planet must be present.
    for planet in ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"):
        assert planet in positions, f"missing planet: {planet}"

    # Each entry has the documented shape.
    for name, info in positions.items():
        assert "longitude" in info
        assert "sign" in info
        assert info["sign"] in calculator.SIGNS
        assert 0 <= info["degree"] < 30
        assert "formatted" in info
        assert isinstance(info["retrograde"], bool)


@pytest.mark.unit
def test_get_planetary_positions_sun_at_j2000_is_in_capricorn(
    calculator: AstrologicalCalculator, fixed_dt: datetime
):
    """At J2000.0 (2000-01-01 12:00 UTC) the Sun sits at ~280.46° tropical
    longitude, which falls in Capricorn (sign index 9, 270°–300°). This anchors
    the calculation to a known astronomical reference point.
    """
    positions = calculator.get_planetary_positions(fixed_dt)
    sun = positions["sun"]

    # 280° ± 1° tropical longitude is the well-known J2000 Sun position.
    assert 278 <= sun["longitude"] <= 282
    # 280° → sign index int(280/30)=9 → Capricorn
    assert sun["sign"] == "Capricorn"
    # Degree in sign: ~10° (280 mod 30)
    assert 8 <= sun["degree"] <= 12


# ─── Behavior: get_moon_phase ──────────────────────────────────────────────


@pytest.mark.unit
def test_get_moon_phase_returns_expected_shape(
    calculator: AstrologicalCalculator, fixed_dt: datetime
):
    """get_moon_phase returns dict with phase_name, illumination, phase_angle, is_*_moon."""
    phase = calculator.get_moon_phase(fixed_dt)

    assert "phase_name" in phase
    assert phase["phase_name"] in {
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    }
    assert 0 <= phase["illumination"] <= 100
    assert 0 <= phase["phase_angle"] < 360
    assert isinstance(phase["is_new_moon"], bool)
    assert isinstance(phase["is_full_moon"], bool)


# ─── Error handling ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_get_hellenistic_lots_rejects_invalid_sect(calculator: AstrologicalCalculator):
    """get_hellenistic_lots raises ValueError for any sect other than 'day' or 'night'."""
    with pytest.raises(ValueError, match="sect must be"):
        calculator.get_hellenistic_lots(datetime(2024, 1, 1, tzinfo=pytz.UTC), sect="dawn")


# ─── format_astrological_report ───────────────────────────────────────────
#
# Regression: scripts/vajra_orchestrator.py and scripts/radionics_operation.py
# both ``from core.astrology import format_astrological_report`` — and that
# free function was never defined anywhere, breaking module-level import on
# both scripts. The function was re-added in core/astrology.py (after the
# AstrologyEngine alias) with defensive handling for the
# ``get_current_energetics`` payload shape. The tests below pin:
#   1. Symbol is importable (would fail with ImportError if missing).
#   2. Empty / falsy payload returns the sentinel string rather than raising.
#   3. Illumination is rendered 0–100, NOT multiplied by 100 again (an early
#      implementation had this bug — see commit history of the fix).
#   4. Retrograde marker (R) is present when ``info.retrograde`` is True.
#   5. Non-dict planet positions (the same crash class as the replay tab bug)
#      are skipped without raising.


@pytest.mark.unit
def test_format_astrological_report_is_importable():
    """Regression: the symbol must exist as a module-level function.
    Previously undefined, breaking ``scripts/vajra_orchestrator.py`` and
    ``scripts/radionics_operation.py`` at import time."""
    assert callable(format_astrological_report)


@pytest.mark.unit
def test_format_astrological_report_empty_payload_returns_sentinel():
    """An empty dict produces the no-data sentinel rather than raising."""
    assert format_astrological_report({}) == "(no astrological data available)"
    assert format_astrological_report(None or {}) == "(no astrological data available)"


@pytest.mark.unit
def test_format_astrological_report_full_energetics_payload():
    """Format a realistic ``get_current_energetics``-shaped dict and verify
    every section header + a sample planet line + the planetary-hour line
    render correctly. Also pins that illumination is NOT double-multiplied."""
    data = {
        "datetime": "2026-07-05T21:00:00+00:00",
        "moon_phase": {"phase_name": "Waning Gibbous", "illumination": 69.9},
        "lunar_mansion": {"name": "Purva Bhadrapada"},
        "planetary_positions": {
            "sun":   {"sign": "Cancer", "degree": 13.86, "retrograde": False},
            "mercury": {"sign": "Cancer", "degree": 24.86, "retrograde": True},
            "moon":  {"sign": "Pisces", "degree": 20.41, "retrograde": False},
        },
        "auspicious_times": {"sunrise": "06:12", "sunset": "20:30"},
        "planetary_hours": {"current_planetary_hour": "Moon", "day_planet": "Moon"},
    }
    out = format_astrological_report(data)

    assert "Timestamp: 2026-07-05T21:00:00+00:00" in out
    assert "Waning Gibbous (69.9% illuminated)" in out
    # Critical: 69.9 is already 0–100 — it must NOT render as "6990.7%"
    # (the bug present in an earlier draft of this function).
    assert "6990" not in out
    assert "Lunar Mansion: Purva Bhadrapada" in out
    assert "Sun: Cancer 13.86°" in out
    assert "Mercury: Cancer 24.86° (R)" in out
    assert "Moon: Pisces 20.41°" in out
    assert "Auspicious Times" in out
    assert "Sunrise: 06:12" in out
    assert "Planetary Hour: Moon (day ruler: Moon)" in out


@pytest.mark.unit
def test_format_astrological_report_skips_non_dict_planet_positions():
    """Defensive: if a sidereal/planet position is not a dict (transient backend
    failure), the function skips it rather than crashing. Same crash class as
    AstrologyExtractionPanel's ``runs.some is not a function`` audit."""
    data = {
        "planetary_positions": {
            "sun":   {"sign": "Cancer", "degree": 13.86},
            "moon":  None,                      # transient failure shape
            "mercury": "not-an-object",          # transient failure shape
            "venus": {"sign": "Leo", "degree": 25.71},
        },
    }
    out = format_astrological_report(data)
    assert "Sun: Cancer 13.86°" in out
    assert "Venus: Leo 25.71°" in out
    # Null/string positions must NOT appear in the rendered output (we skip
    # them gracefully instead of crashing on ``info.sign``).
    assert "Moon:" not in out.split("Sun:")[1]  # no Moon: line after the header
    assert "Mercury:" not in out


@pytest.mark.unit
def test_format_astrological_report_handles_missing_degree():
    """If ``degree`` is absent, the planet line falls back to ``—`` instead of
    rendering ``undefined°``."""
    data = {"planetary_positions": {"sun": {"sign": "Cancer"}}}  # no degree
    out = format_astrological_report(data)
    assert "Sun: Cancer —" in out
    assert "undefined" not in out


@pytest.mark.unit
def test_format_astrological_report_handles_auspicious_times_string_values():
    """Auspicious times may be strings (``"morning"``) or dicts in fallback mode;
    either should render without crashing."""
    data = {"auspicious_times": {"sunrise": "morning", "sunset": "evening"}}
    out = format_astrological_report(data)
    assert "Sunrise: morning" in out
    assert "Sunset: evening" in out
