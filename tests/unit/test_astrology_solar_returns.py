"""Test scripts for Task 10 (solar returns + profections)."""

from datetime import datetime, timezone

import pytest

# Skip cleanly when ``swisseph`` is missing — see tests/unit/test_astrology.py.
swisseph = pytest.importorskip("swisseph")

from core.astrology import AstrologicalCalculator  # noqa: E402  (guarded by importorskip)


def test_imports():
    """Test 1: basic import + class attribute present."""
    calc = AstrologicalCalculator()
    assert hasattr(calc, "get_solar_return"), "missing get_solar_return"
    assert hasattr(calc, "get_profection"), "missing get_profection"
    assert hasattr(calc, "PROFECTION_LORDS"), "missing PROFECTION_LORDS"
    assert len(calc.PROFECTION_LORDS) == 12, f"expected 12 lords, got {len(calc.PROFECTION_LORDS)}"
    assert calc.PROFECTION_LORDS["Aries"] == "Mars"
    assert calc.PROFECTION_LORDS["Leo"] == "Sun"
    assert calc.PROFECTION_LORDS["Aquarius"] == "Saturn"  # traditional, not Uranus


def test_solar_return_sun_match():
    """Test 2: solar return Sun should match natal Sun within 0.5°."""
    calc = AstrologicalCalculator()
    n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_sun_lon = calc.get_planetary_positions(n)["sun"]["longitude"]
    sr = calc.get_solar_return(n, (0, 0), 2026)
    sr_sun_lon = sr["positions"]["sun"]["longitude"]
    diff = abs(sr_sun_lon - natal_sun_lon)
    assert diff < 0.5, f"diff {diff:.6f}° exceeds 0.5°"
    for p in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]:
        assert p in sr["positions"], f"missing planet {p}"
    assert "asc" in sr["angles"] and "mc" in sr["angles"]
    assert sr["location"] == (0, 0)
    assert sr["exact_moment"].startswith("2026-") or sr["exact_moment"].startswith("2027-")


def test_solar_return_other_years():
    """Test 3: solar return should work for various years."""
    calc = AstrologicalCalculator()
    n = datetime(1990, 6, 15, 14, 30, tzinfo=timezone.utc)
    natal_sun_lon = calc.get_planetary_positions(n)["sun"]["longitude"]

    for year in [2000, 2025, 2030, 2050]:
        sr = calc.get_solar_return(n, (51.5, -0.13), year)
        sr_sun_lon = sr["positions"]["sun"]["longitude"]
        diff = abs(sr_sun_lon - natal_sun_lon)
        diff = min(diff, 360.0 - diff)
        assert diff < 0.5, f"year {year} diff {diff:.6f}° exceeds 0.5°"


def test_profection_age_zero():
    """Test 4: at age 0, profected sign = natal sign."""
    calc = AstrologicalCalculator()
    n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    p = calc.get_profection(n, 2000, natal_location=(51.5, -0.13))
    assert p["age"] == 0
    assert p["profected_asc_sign"] == p["natal_asc_sign"]
    assert p["house_ruled"] == 1


def test_profection_cycle():
    """Test 5: at age 12, profected sign returns to natal sign (12-year cycle)."""
    calc = AstrologicalCalculator()
    n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    p0 = calc.get_profection(n, 2000, natal_location=(51.5, -0.13))
    p12 = calc.get_profection(n, 2012, natal_location=(51.5, -0.13))
    p24 = calc.get_profection(n, 2024, natal_location=(51.5, -0.13))
    assert p0["profected_asc_sign"] == p12["profected_asc_sign"]
    assert p0["profected_asc_sign"] == p24["profected_asc_sign"]
    assert p12["house_ruled"] == 1
    assert p24["house_ruled"] == 1


def test_profection_all_lords_valid():
    """Test 6: profection_lord is always a valid planet name."""
    calc = AstrologicalCalculator()
    valid_planets = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    for year in range(2000, 2015):
        p = calc.get_profection(n, year, natal_location=(51.5, -0.13))
        assert p["profection_lord"] in valid_planets, f"year {year} lord {p['profection_lord']!r} not valid"


def test_profection_house_offset():
    """Test 7: house_ruled increments by 1 each year of age."""
    calc = AstrologicalCalculator()
    n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    for i, year in enumerate(range(2000, 2013)):
        p = calc.get_profection(n, year, natal_location=(51.5, -0.13))
        expected_house = (i % 12) + 1
        assert (
            p["house_ruled"] == expected_house
        ), f"year {year} expected house {expected_house}, got {p['house_ruled']}"


def test_solar_return_location_override():
    """Test 8: return_location override should change the angles but not the Sun."""
    calc = AstrologicalCalculator()
    n = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    sr_natal = calc.get_solar_return(n, (51.5, -0.13), 2026)
    sr_other = calc.get_solar_return(n, (51.5, -0.13), 2026, return_location=(40.7, -74.0))
    sun_diff = abs(sr_natal["positions"]["sun"]["longitude"] - sr_other["positions"]["sun"]["longitude"])
    asc_natal = sr_natal["positions"]["ascendant"]["longitude"]
    asc_other = sr_other["positions"]["ascendant"]["longitude"]
    assert sun_diff < 0.001, "Sun should be at the same longitude regardless of location"
    assert abs(asc_natal - asc_other) > 1.0, "Asc should change with location"


if __name__ == "__main__":
    print("=" * 60)
    print("Task 10: Solar Returns + Profections")
    print("=" * 60)

    test_imports()
    print()

    sr1 = test_solar_return_sun_match()
    print()

    test_solar_return_other_years()
    print()

    test_profection_age_zero()
    print()

    cycle = test_profection_cycle()
    print()

    test_profection_all_lords_valid()
    print()

    test_profection_house_offset()
    print()

    test_solar_return_location_override()
    print()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
