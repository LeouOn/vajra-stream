"""
Smoke + behaviour tests for ``core.astrocartography``.

The module wraps the Swiss Ephemeris (``swisseph``) C extension to provide:

* Julian/Gregorian calendar conversion (:class:`CalendarConverter`)
* Planetary ACG lines (:class:`AstrocartographyCalculator`)
* Local-space astrology (:class:`LocalSpaceCalculator`)
* Historical chart calculation (:class:`HistoricalChartCalculator`)
* Module-level helpers :func:`quick_astrocartography`, :func:`find_power_places`

The tests below cover stable, easily-verifiable contracts:

* module imports
* constants and class attributes
* round-tripping a Gregorian date through ``date_to_julian_day`` /
  ``julian_day_to_date``
* historical date handling via the Julian calendar
* a small ``calculate_planetary_lines`` call returns a well-formed payload
* ``calculate_parans`` returns a list (possibly empty)
* ``quick_astrocartography`` convenience helper delegates correctly

``swisseph`` is required at import time; tests will be skipped if it is not
installed, since the module cannot run without it.
"""

from __future__ import annotations

import pytest

swisseph = pytest.importorskip("swisseph")

from core.astrocartography import (  # noqa: E402
    ANGLES,
    PLANETS,
    AstrocartographyCalculator,
    CalendarConverter,
    HistoricalChartCalculator,
    find_power_places,
    quick_astrocartography,
)

# ---------------------------------------------------------------------------
# 1. Import smoke + constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """The module imports cleanly and exposes its main public names."""
    # Re-exported names from module
    assert callable(CalendarConverter.date_to_julian_day)
    assert callable(CalendarConverter.julian_day_to_date)
    assert callable(CalendarConverter.is_julian_date)

    # Module-level constants
    assert isinstance(PLANETS, dict)
    assert "sun" in PLANETS
    assert "moon" in PLANETS
    assert ANGLES == {"ASC": "Ascendant", "DSC": "Descendant", "MC": "Midheaven", "IC": "Imum Coeli"}


# ---------------------------------------------------------------------------
# 2. Calendar round-trip â€” Gregorian
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calendar_roundtrip_gregorian():
    """Converting a date â†’ JD â†’ date returns the original components."""
    jd = CalendarConverter.date_to_julian_day(2000, 1, 1, 12, 0, 0, "gregorian")
    info = CalendarConverter.julian_day_to_date(jd, "gregorian")

    assert info["year"] == 2000
    assert info["month"] == 1
    assert info["day"] == 1
    assert info["calendar"] == "gregorian"


# ---------------------------------------------------------------------------
# 3. Calendar â€” Julian adoption rule
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_is_julian_date_for_catholic_countries_pre_adoption():
    """Dates before 1582-10-15 use the Julian calendar in catholic countries."""
    # 15 March 1000 CE is well before the Gregorian reform
    assert CalendarConverter.is_julian_date(1000, 3, 15, "catholic_countries") is True


@pytest.mark.unit
def test_is_julian_date_post_gregorian_reform():
    """A date after the 1582-10-15 Gregorian reform is no longer Julian
    in catholic countries."""
    assert CalendarConverter.is_julian_date(2000, 1, 1, "catholic_countries") is False


# ---------------------------------------------------------------------------
# 4. Planetary lines â€” happy path with a tiny subset
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_planetary_lines_returns_four_angles_per_planet():
    """Each planet in the result has the four standard ACG angles.

    NOTE: The module normalises IC/DSC to ``[-180, 180]`` but leaves MC/ASC as
    raw planetary longitudes (which can exceed 180Â°).  We therefore only assert
    the documented IC/DSC range and check MC/ASC are finite degrees.
    """
    calc = AstrocartographyCalculator()
    result = calc.calculate_planetary_lines(2025, 1, 1, 12, 0, 0, ["sun", "moon"], "gregorian")

    assert "julian_day" in result
    assert "date" in result
    assert "lines" in result

    for planet in ("sun", "moon"):
        assert planet in result["lines"]
        for angle in ("ASC", "DSC", "MC", "IC"):
            assert angle in result["lines"][planet]
            entry = result["lines"][planet][angle]
            assert "longitude" in entry
            assert "description" in entry
            assert "meaning" in entry
            # Longitude is a finite degree value
            import math

            assert math.isfinite(entry["longitude"])
            # IC/DSC are documented as normalised to [-180, 180]
            if angle in ("IC", "DSC"):
                assert -180.0 <= entry["longitude"] <= 180.0


# ---------------------------------------------------------------------------
# 5. Parans â€” return type contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_parans_returns_list():
    """``calculate_parans`` returns a list (possibly empty) of crossings."""
    calc = AstrocartographyCalculator()
    parans = calc.calculate_parans(2025, 1, 1, 12, 0, "gregorian")

    assert isinstance(parans, list)
    # Any non-empty entry must conform to the documented schema
    for entry in parans:
        assert "planet1" in entry
        assert "planet2" in entry
        assert "angle1" in entry
        assert "angle2" in entry
        assert "longitude" in entry
        assert "orb" in entry
        # Orb should be non-negative and within the documented 5Â° threshold
        assert 0.0 <= entry["orb"] <= 5.0


# ---------------------------------------------------------------------------
# 6. Historical chart â€” Julian calendar for ancient date
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_historical_chart_returns_planets_houses_and_location():
    """``HistoricalChartCalculator.calculate_chart`` returns the documented
    payload (planets, houses, location, date) for a BCE/Julian-era date."""
    chart_calc = HistoricalChartCalculator()
    chart = chart_calc.calculate_chart(100, 3, 21, 12, 0, 0, 31.2, 29.9, "Alexandria", "julian")

    assert chart["location"]["name"] == "Alexandria"
    assert chart["location"]["latitude"] == 31.2
    assert chart["location"]["longitude"] == 29.9
    assert chart["calendar_type"] == "julian"

    assert "planets" in chart
    assert "sun" in chart["planets"]
    sun = chart["planets"]["sun"]
    # Sign is one of the 12 zodiac names; degree is in [0, 30)
    assert sun["sign"] in {
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    }
    assert 0.0 <= sun["degree"] < 30.0

    assert "houses" in chart
    assert "cusps" in chart["houses"]
    assert chart["houses"]["system"] == "Placidus"


# ---------------------------------------------------------------------------
# 7. Module-level convenience helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quick_astrocartography_delegates_to_calculator():
    """``quick_astrocartography`` returns the same shape as the calculator."""
    result = quick_astrocartography(2025, 1, 1, 12, 0, ["sun"])
    assert "julian_day" in result
    assert "lines" in result
    assert "sun" in result["lines"]


@pytest.mark.unit
def test_find_power_places_filters_by_focus():
    """``find_power_places`` returns a list of location entries, sorted by
    descending strength when populated."""
    # 'benefic' focuses on jupiter/venus
    benefic = find_power_places(2025, 1, 1, 12, 0, focus="benefic")
    assert isinstance(benefic, list)
    for entry in benefic:
        assert entry["planet"] in {"jupiter", "venus"}
        assert "longitude" in entry
        assert "strength" in entry

    strengths = [e["strength"] for e in benefic]
    assert strengths == sorted(strengths, reverse=True)

