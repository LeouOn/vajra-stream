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

from core.astrology import AstrologicalCalculator, __version__

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
