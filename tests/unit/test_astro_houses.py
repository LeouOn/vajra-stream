"""Tests for :mod:`core.astro.houses` (wave W1 ticket W1-3).

Defect under test (measured and VERIFIED in
``docs/notes/w0-astrology-audit-accuracy.md`` section 6, re-verified at HEAD
9640f99 before this module was written):

* ``swe.houses_ex`` RAISES ``swisseph.Error`` for Placidus and Koch at
  |lat| >= 66.57, in both hemispheres (re-measured here on a 0.01 deg grid,
  lon 30 deg E, JD 2459205.0: first raise at exactly +66.57 N and -66.57 S;
  66.56 still returns a chart). ``core.astrology.py`` calls it with
  ``b"P"`` and no guard, so a polar chart fails loudly with the opaque message
  ``swisseph.houses_ex: error``.
* Just below that band the call SUCCEEDS and returns a structurally valid but
  practically empty chart (66.5 deg N: minimum cusp step 2.94 deg), with no
  warning of any kind. This is the genuinely dangerous case.
* Campanus and Regiomontanus do not raise at all above ~69.65 N; they return
  cusps whose twelve mod-360 steps sum to 3960 deg (an extra full revolution),
  i.e. a structurally broken chart with no error and no signal.

These tests are offline and deterministic: a fixed Julian day, fixed
coordinates, no network, no ephemeris download, no randomness.
"""

from __future__ import annotations

from math import isfinite

import pytest
import swisseph as swe

from core.astro import houses as astro_houses
from core.astro.houses import (
    PROVISIONAL_DEFAULTS,
    SUPPORTED_SYSTEMS,
    HouseCalculationError,
    InvalidCoordinateError,
    InvalidCuspStepError,
    InvalidJulianDayError,
    UnknownHouseSystemError,
    _structural_problems,
    compute_houses,
    cusp_steps,
)

# 2020-12-21 12:00 UT. Same instant the W0 audit swept, so the numbers quoted
# in the audit notes are directly comparable with what these tests measure.
JULIAN_DAY = 2459205.0

# (name, latitude, longitude)
REYKJAVIK = (64.1466, -21.9426)
DEGENERATE_BAND = (66.5, 30.0)
TROMSO = (69.6496, 18.9560)
ALERT = (82.5, -62.35)
SYDNEY = (-33.8688, 151.2093)
EQUATOR = (0.0, 30.0)
NORTH_POLE = (90.0, 0.0)
SOUTH_POLE = (-90.0, 0.0)

# Latitude/longitude pairs the row requires coverage for, north to south.
REQUIRED_LOCATIONS = [
    ("reykjavik", REYKJAVIK),
    ("degenerate_band", DEGENERATE_BAND),
    ("tromso", TROMSO),
    ("alert", ALERT),
    ("north_pole", NORTH_POLE),
    ("south_pole", SOUTH_POLE),
    ("sydney", SYDNEY),
    ("equator", EQUATOR),
]

ALL_SYSTEMS = ["Placidus", "Koch", "Regiomontanus", "Campanus", "Porphyry", "Equal", "WholeSign"]


def assert_structurally_valid(cusps: list[float]) -> None:
    """Assert the twelve cusps partition the circle exactly once.

    House cusps come back from swe in *house order*, not sorted, so the
    invariant is that the twelve mod-360 steps sum to 360 and that every one
    of them is strictly positive. A chart that needs 3960 deg (360 x 11) has
    wrapped the circle an extra eleven times and is structurally broken even
    though every individual step is a "positive" number.
    """
    assert len(cusps) == 12
    steps = cusp_steps(cusps)
    assert all(step > 0.0 for step in steps), f"non-positive cusp step in {steps}"
    assert sum(steps) == pytest.approx(360.0, abs=1e-6), f"cusps do not span 360 deg: {sum(steps)}"


# ---------------------------------------------------------------------------
# 1. The defect the ticket exists for, reproduced against the current code path
# ---------------------------------------------------------------------------


def test_project_default_system_raises_unhandled_at_70_north():
    """RED: this is what ``core.astrology.py`` does today, and it blows up.

    Mirrors the unguarded ``swe.houses(jd, lat, lon, b"P")`` call in
    ``AstrologyCalculator.get_western_astrology``. A birth in Tromso,
    Rovaniemi, Ushuaia or any Antarctic station fails with the bare string
    ``swisseph.houses: error`` and no mention of latitude, house system or
    the polar circle.
    """
    with pytest.raises(swe.Error) as excinfo:
        swe.houses(JULIAN_DAY, 70.0, 18.9560, b"P")
    # Asserted rather than merely observed: the message carries no diagnosis.
    assert str(excinfo.value) == "swisseph.houses: error"


def test_campanus_returns_structurally_broken_chart_without_raising():
    """RED: the forward-looking hazard. No exception, no signal, wrong chart."""
    cusps, _ascmc = swe.houses_ex(JULIAN_DAY, 70.0, 30.0, b"C")
    # The call succeeded -- that is the whole problem.
    assert sum(cusp_steps(list(cusps))) == pytest.approx(3960.0, abs=1e-6)


def test_placidus_succeeds_but_is_degenerate_at_66_5_north():
    """RED: the genuinely dangerous case -- plausible output, meaningless chart."""
    cusps, _ascmc = swe.houses_ex(JULIAN_DAY, 66.5, 30.0, b"P")
    minimum_step = min(cusp_steps(list(cusps)))
    # Monotonic and structurally fine ...
    assert sum(cusp_steps(list(cusps))) == pytest.approx(360.0, abs=1e-6)
    # ... but three houses crammed into a few degrees, and nothing says so.
    assert minimum_step < 5.0


# ---------------------------------------------------------------------------
# 2. The wrapper never crashes, and always says what it did
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("system", ALL_SYSTEMS)
@pytest.mark.parametrize("label,location", REQUIRED_LOCATIONS)
def test_every_system_at_every_required_location_returns_a_usable_chart(system, label, location):
    lat, lon = location
    result = compute_houses(JULIAN_DAY, lat, lon, system=system)

    assert_structurally_valid(list(result.cusps))
    assert result.system_requested == system
    assert result.system_used in ALL_SYSTEMS
    assert result.fallback_used == (result.system_used != result.system_requested)
    assert -360.0 <= result.asc < 360.0
    assert -360.0 <= result.mc < 360.0


@pytest.mark.parametrize("system", ALL_SYSTEMS)
@pytest.mark.parametrize("label,location", REQUIRED_LOCATIONS)
def test_warnings_are_only_emitted_when_they_apply(system, label, location):
    """A chart that is quietly degraded must always announce it, and vice versa."""
    lat, lon = location
    result = compute_houses(JULIAN_DAY, lat, lon, system=system)

    if result.fallback_used:
        assert result.warnings, f"{label}/{system}: fell back to {result.system_used} silently"
    for warning in result.warnings:
        assert isinstance(warning, str) and warning


def test_polar_chart_never_raises_for_the_project_default_system():
    """The ticket goal: a polar birth yields a chart, not a traceback."""
    result = compute_houses(JULIAN_DAY, 70.0, 18.9560)  # default system
    assert result.system_requested == PROVISIONAL_DEFAULTS["default_system"]
    assert result.fallback_used is True
    assert result.system_used == PROVISIONAL_DEFAULTS["polar_fallback"]
    assert any("placidus" in w.lower() for w in result.warnings)
    assert_structurally_valid(list(result.cusps))


def test_degenerate_band_at_66_5_north_warns_and_falls_back():
    """Row requirement: 66.5 deg must warn (degenerate) and fall back."""
    result = compute_houses(JULIAN_DAY, *DEGENERATE_BAND, system="Placidus")

    assert result.system_requested == "Placidus"
    assert result.fallback_used is True
    assert result.system_used == PROVISIONAL_DEFAULTS["polar_fallback"]
    assert any("cusp" in w.lower() for w in result.warnings)
    assert_structurally_valid(list(result.cusps))


def test_structurally_broken_system_falls_back_even_though_swe_did_not_raise():
    """Campanus above ~69.65 N returns a broken chart with no error at all."""
    result = compute_houses(JULIAN_DAY, 70.0, 30.0, system="Campanus")

    assert result.system_requested == "Campanus"
    assert result.fallback_used is True
    assert_structurally_valid(list(result.cusps))
    assert any("campanus" in w.lower() for w in result.warnings)


def test_regiomontanus_at_south_pole_has_a_zero_width_house_and_is_rejected():
    """-90 deg gives Regiomontanus a min cusp step of exactly 0.0."""
    cusps, _ = swe.houses_ex(JULIAN_DAY, -90.0, 0.0, b"R")
    assert min(cusp_steps(list(cusps))) == pytest.approx(0.0, abs=1e-9)

    result = compute_houses(JULIAN_DAY, -90.0, 0.0, system="Regiomontanus")
    assert result.fallback_used is True
    assert_structurally_valid(list(result.cusps))


@pytest.mark.parametrize("label,location", REQUIRED_LOCATIONS)
def test_requested_system_is_always_reported_even_when_a_fallback_was_used(label, location):
    lat, lon = location
    result = compute_houses(JULIAN_DAY, lat, lon, system="Placidus")
    assert result.system_requested == "Placidus"
    if result.system_used != "Placidus":
        assert result.fallback_used is True
        assert result.system_used in ALL_SYSTEMS


# ---------------------------------------------------------------------------
# 3. Whole Sign is regular everywhere, by definition
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,location", REQUIRED_LOCATIONS)
def test_whole_sign_cusps_are_exactly_30_degrees_apart(label, location):
    lat, lon = location
    result = compute_houses(JULIAN_DAY, lat, lon, system="WholeSign")

    assert result.system_used == "WholeSign"
    assert result.fallback_used is False
    assert result.warnings == []
    for step in cusp_steps(list(result.cusps)):
        assert step == pytest.approx(30.0, abs=1e-9)


@pytest.mark.parametrize("label,location", REQUIRED_LOCATIONS)
def test_equal_cusps_are_exactly_30_degrees_apart(label, location):
    lat, lon = location
    result = compute_houses(JULIAN_DAY, lat, lon, system="Equal")
    assert result.system_used == "Equal"
    assert result.fallback_used is False


# ---------------------------------------------------------------------------
# 4. Asc / MC agree with swisseph's own ascmc output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("system", ["Placidus", "Koch", "Regiomontanus", "Campanus", "Porphyry", "Equal", "WholeSign"])
@pytest.mark.parametrize("lat", [0.0, 23.5, 45.0, 64.1466, -33.8688])
def test_asc_and_mc_match_swe_ascmc_when_no_fallback_happens(system, lat):
    lon = 30.0
    result = compute_houses(JULIAN_DAY, lat, lon, system=system)
    if result.fallback_used:
        pytest.skip(f"{system} fell back to {result.system_used} at lat={lat}")

    cusps, ascmc = swe.houses_ex(JULIAN_DAY, lat, lon, SUPPORTED_SYSTEMS[result.system_used])
    assert list(result.cusps) == pytest.approx(list(cusps), abs=1e-9)
    assert result.asc == pytest.approx(ascmc[0], abs=1e-9)
    assert result.mc == pytest.approx(ascmc[1], abs=1e-9)


# ---------------------------------------------------------------------------
# 5. Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lat", [90.1, -90.1, 100.0, -1000.0, float("nan")])
def test_latitude_outside_valid_range_raises_a_clear_value_error(lat):
    with pytest.raises(InvalidCoordinateError) as excinfo:
        compute_houses(JULIAN_DAY, lat, 0.0)
    assert "latitude" in str(excinfo.value).lower()


@pytest.mark.parametrize("lon", [180.1, -180.1, 360.0, -720.0, float("nan")])
def test_longitude_outside_valid_range_raises_a_clear_value_error(lon):
    with pytest.raises(InvalidCoordinateError) as excinfo:
        compute_houses(JULIAN_DAY, 0.0, lon)
    assert "longitude" in str(excinfo.value).lower()


@pytest.mark.parametrize("lat", [-90.0, 90.0, 0.0, 45.0, -45.0])
@pytest.mark.parametrize("lon", [-180.0, 180.0, 0.0, 30.0, -21.9426])
def test_boundaries_of_the_valid_ranges_are_accepted(lat, lon):
    result = compute_houses(JULIAN_DAY, lat, lon, system="Equal")
    assert_structurally_valid(list(result.cusps))


def test_unknown_house_system_raises_a_named_error():
    with pytest.raises(UnknownHouseSystemError) as excinfo:
        compute_houses(JULIAN_DAY, 0.0, 0.0, system="Koch-Hemisphere")
    assert "Koch-Hemisphere" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 6. Parameters are parameters, and the data table is swappable
# ---------------------------------------------------------------------------


def test_minimum_cusp_step_threshold_is_a_parameter():
    """A caller that tolerates bunched houses can lower the threshold."""
    lat, lon = DEGENERATE_BAND
    strict = compute_houses(JULIAN_DAY, lat, lon, system="Placidus")
    lax = compute_houses(JULIAN_DAY, lat, lon, system="Placidus", min_cusp_step_deg=0.5)

    assert strict.fallback_used is True
    assert lax.fallback_used is False
    assert lax.system_used == "Placidus"


def test_fallback_system_is_a_parameter():
    lat, lon = TROMSO
    porphyry = compute_houses(JULIAN_DAY, lat, lon, fallback="Porphyry")
    whole_sign = compute_houses(JULIAN_DAY, lat, lon, fallback="WholeSign")

    assert porphyry.system_used == "Porphyry"
    assert whole_sign.system_used == "WholeSign"
    assert porphyry.fallback_used is True
    assert whole_sign.fallback_used is True
    assert_structurally_valid(list(porphyry.cusps))
    assert_structurally_valid(list(whole_sign.cusps))


def test_bunched_fallback_result_is_warned_about_but_still_returned():
    """Porphyry at 70 N is structurally fine but bunches to 0.79 deg.

    Returning nothing would be worse than returning an honest, flagged chart,
    so the bunching is reported rather than triggering an endless fallback
    loop.
    """
    result = compute_houses(JULIAN_DAY, 70.0, 30.0, system="Placidus", fallback="Porphyry")

    assert result.system_used == "Porphyry"
    assert min(cusp_steps(list(result.cusps))) < 5.0
    assert any("bunch" in w.lower() or "narrow" in w.lower() for w in result.warnings)


def test_provisional_defaults_table_is_plain_data():
    """The defaults are swappable data, not hidden state or magic numbers."""
    assert isinstance(PROVISIONAL_DEFAULTS, dict)
    assert PROVISIONAL_DEFAULTS["default_system"] == "Placidus"
    assert PROVISIONAL_DEFAULTS["polar_fallback"] == "Porphyry"
    assert isinstance(PROVISIONAL_DEFAULTS["min_cusp_step_deg"], float)
    assert PROVISIONAL_DEFAULTS["needs_learner_decision"] is True


def test_fallback_that_also_fails_raises_a_typed_error_not_a_bare_exception():
    """If even the fallback cannot produce a chart, say so -- do not return junk."""
    result = compute_houses(JULIAN_DAY, 70.0, 30.0, system="Placidus", fallback="WholeSign")
    assert result.system_used == "WholeSign"
    assert_structurally_valid(list(result.cusps))
    # The typed error exists and is exported for callers that need it.
    assert issubclass(HouseCalculationError, RuntimeError)


# ---------------------------------------------------------------------------
# 7. REWORK 1: fallback == requested, for each way the request can be unusable
# ---------------------------------------------------------------------------
#
# There are three ways a requested system can be unusable, and when
# fallback == requested only two of them have a chart to return:
#
#   swe raised          -> there IS no chart; must raise HouseCalculationError
#   cusps bunched       -> chart exists, is honest if warned about
#   cusps structurally  -> chart exists, is NOT honest; must warn loudly
#
# Getting the first one wrong produced UnboundLocalError: the except branch
# never bound cusps/asc/mc, and the fallback == requested branch then read
# them. UnboundLocalError is a NameError, not a HouseCalculationError, so it
# escaped the module's own contract.


def test_raised_system_with_no_distinct_fallback_raises_a_typed_error():
    """(a) Placidus at 80 N raises in swe, and there is nothing to fall back to."""
    with pytest.raises(HouseCalculationError) as excinfo:
        compute_houses(JULIAN_DAY, 80.0, 30.0, system="Placidus", fallback="Placidus")
    message = str(excinfo.value)
    assert "Placidus" in message
    assert "80.00" in message


def test_raised_system_with_no_distinct_fallback_southern_hemisphere():
    """(b) Koch at -80 N is the same defect reached from the other pole."""
    with pytest.raises(HouseCalculationError) as excinfo:
        compute_houses(JULIAN_DAY, -80.0, 30.0, system="Koch", fallback="Koch")
    message = str(excinfo.value)
    assert "Koch" in message
    assert "-80.00" in message


def test_bunched_system_with_no_distinct_fallback_returns_a_warned_chart():
    """(c) Bunched cusps still ARE a chart, so return it -- and say it is poor."""
    result = compute_houses(JULIAN_DAY, 66.5, 30.0, system="Placidus", fallback="Placidus")
    assert result.system_used == "Placidus"
    assert result.system_requested == "Placidus"
    assert result.fallback_used is False
    assert result.warnings
    assert any("bunched" in w.lower() for w in result.warnings)
    assert_structurally_valid(list(result.cusps))


def test_structurally_broken_system_with_no_distinct_fallback_warns_loudly():
    """(d) Campanus at 80 N spans 3960 deg; there is no better answer here."""
    result = compute_houses(JULIAN_DAY, 80.0, 30.0, system="Campanus", fallback="Campanus")
    assert result.system_used == "Campanus"
    assert result.fallback_used is False
    assert any("span 360" in w for w in result.warnings)
    # The structural defect is still reported honestly, even though there was
    # nowhere else to go.
    assert any("campanus" in w.lower() for w in result.warnings)


def test_no_path_returns_a_chart_that_never_had_one():
    """Guard: a raise must never surface as UnboundLocalError or NameError."""
    for lat, system in ((80.0, "Placidus"), (-80.0, "Koch"), (90.0, "Koch")):
        try:
            compute_houses(JULIAN_DAY, lat, 30.0, system=system, fallback=system)
        except HouseCalculationError:
            continue
        except (NameError, UnboundLocalError) as exc:  # pragma: no cover - the bug
            pytest.fail(f"{system} at {lat} leaked {type(exc).__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - wrong exception type
            pytest.fail(f"{system} at {lat} raised {type(exc).__name__}, not HouseCalculationError")
        pytest.fail(f"{system} at {lat} returned a chart instead of raising")


# ---------------------------------------------------------------------------
# 8. REWORK 1: non-finite Julian day and threshold are rejected, not absorbed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("julian_day", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_julian_day_is_rejected(julian_day):
    """A NaN JD made swe raise, and the warning blamed the LATITUDE."""
    with pytest.raises(InvalidJulianDayError) as excinfo:
        compute_houses(julian_day, 10.0, 30.0)
    assert "julian" in str(excinfo.value).lower()


def test_non_finite_julian_day_is_rejected_before_any_coordinate_check():
    """Coordinate errors still win when both inputs are bad -- one clear fault."""
    with pytest.raises(InvalidCoordinateError):
        compute_houses(float("nan"), 91.0, 30.0)


@pytest.mark.parametrize("julian_day", [0.0, 1.0, 100.0, 100000.0, 1e9, 2451545.0])
def test_finite_julian_days_are_not_rejected_by_us(julian_day):
    """swe.houses_ex needs no ephemeris files and accepts a wide JD range.

    We must not invent a calendar range check and reject inputs that swe
    handles correctly.
    """
    result = compute_houses(julian_day, 10.0, 30.0, system="Equal")
    assert_structurally_valid(list(result.cusps))


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), float("-inf"), -0.1, -5.0])
def test_invalid_min_cusp_step_threshold_is_rejected(threshold):
    """NaN silently disabled the bunching check; a negative threshold is meaningless."""
    with pytest.raises(InvalidCuspStepError) as excinfo:
        compute_houses(JULIAN_DAY, 66.5, 30.0, system="Placidus", min_cusp_step_deg=threshold)
    assert "cusp" in str(excinfo.value).lower()


def test_zero_threshold_is_allowed_and_disables_the_bunching_check():
    """Zero is a legitimate request: "use the system even if the houses bunch"."""
    result = compute_houses(JULIAN_DAY, 66.5, 30.0, system="Placidus", min_cusp_step_deg=0.0)
    assert result.system_used == "Placidus"
    assert result.fallback_used is False
    # Still structurally sound, which is the only guarantee we can make.
    assert_structurally_valid(list(result.cusps))


def test_default_threshold_is_still_five_degrees():
    result = compute_houses(JULIAN_DAY, 66.5, 30.0, system="Placidus")
    assert result.fallback_used is True


# ---------------------------------------------------------------------------
# 9. REWORK 1: the Placidus/Koch raise boundary is 66.57, re-measured
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", [b"P", b"K"])
def test_placidus_and_koch_raise_exactly_at_66_57(flag):
    """Measured on a 0.01 deg grid, lon 30E, JD 2459205.0: first raise 66.57.

    Both hemispheres. 66.56 returns a chart (Placidus min step 2.84, Koch
    4.70); 66.57 raises.
    """
    cusps, _ascmc = swe.houses_ex(JULIAN_DAY, 66.56, 30.0, flag)
    assert sum(cusp_steps(list(cusps))) == pytest.approx(360.0, abs=1e-6)
    with pytest.raises(swe.Error):
        swe.houses_ex(JULIAN_DAY, 66.57, 30.0, flag)
    with pytest.raises(swe.Error):
        swe.houses_ex(JULIAN_DAY, -66.57, 30.0, flag)


def test_degenerate_band_test_latitude_is_still_below_the_raise_boundary():
    """66.5 N is used as the degenerate-band fixture; it must not raise."""
    cusps, _ascmc = swe.houses_ex(JULIAN_DAY, 66.5, 30.0, b"P")
    assert min(cusp_steps(list(cusps))) == pytest.approx(2.9369, abs=1e-3)


def test_polar_latitudes_fall_back_rather_than_raise():
    """Every latitude at or above the boundary yields a chart via the wrapper."""
    for lat in (66.57, 66.58, 66.65, 70.0, 80.0, 90.0, -66.57, -80.0, -90.0):
        result = compute_houses(JULIAN_DAY, lat, 30.0, system="Placidus")
        assert result.fallback_used is True
        assert_structurally_valid(list(result.cusps))


# ---------------------------------------------------------------------------
# 10. REWORK 2: a "successful" chart full of NaN is the worst silent failure
# ---------------------------------------------------------------------------
#
# compute_houses accepts every FINITE Julian day by policy (swe accepts what it
# accepts; we reject only what cannot produce a finite chart). At JD 1e100 and
# 1e300 swe does not raise for most systems -- it returns a MIXED chart, some
# cusps finite and some NaN, with a finite mc. That is more dangerous than an
# all-NaN result, because half the chart looks plausible.
#
# OBSERVED at lat=0.0, lon=180.0, pyswisseph 2.10.03:
#   Placidus  RAISES swe.Error
#   Koch / Regiomontanus / Campanus / Porphyry   10/12 cusps non-finite, asc NaN, mc 270.0
#   Equal / WholeSign                            12/12 cusps non-finite, asc NaN, mc 270.0
# With the default Porphyry fallback, every one of the seven must therefore end
# in HouseCalculationError: Placidus raised, and Porphyry is itself non-finite.

NAN_JULIAN_DAYS = [1e100, 1e300]


@pytest.mark.parametrize("julian_day", NAN_JULIAN_DAYS)
@pytest.mark.parametrize("system", ALL_SYSTEMS)
def test_non_finite_swe_output_never_becomes_a_successful_chart(julian_day, system):
    """Every system, at both absurd Julian days, must raise rather than lie."""
    with pytest.raises(HouseCalculationError):
        compute_houses(julian_day, 0.0, 180.0, system=system)


@pytest.mark.parametrize("julian_day", NAN_JULIAN_DAYS)
def test_no_nan_survives_into_any_returned_chart(julian_day):
    """Belt and braces: nothing non-finite may come back through the public API."""
    for system in ALL_SYSTEMS:
        try:
            result = compute_houses(julian_day, 0.0, 180.0, system=system)
        except HouseCalculationError:
            continue
        values = list(result.cusps) + [result.asc, result.mc]
        assert all(isfinite(value) for value in values), f"{system} returned non-finite"


@pytest.mark.parametrize("julian_day", NAN_JULIAN_DAYS)
def test_non_finite_result_with_no_distinct_fallback_raises(julian_day):
    """fallback == system AND the output is non-finite: there is no chart."""
    with pytest.raises(HouseCalculationError):
        compute_houses(julian_day, 0.0, 180.0, system="Koch", fallback="Koch")


def test_structural_problems_flags_a_nan_cusp():
    problems = _structural_problems([float("nan")] * 12)
    assert problems
    assert "non-finite" in problems[0]
    assert "cusp" in problems[0]


def test_structural_problems_flags_a_single_nan_cusp_among_finite_ones():
    cusps = list(range(0, 360, 30))
    cusps[4] = float("nan")
    problems = _structural_problems(cusps)
    assert problems
    assert "non-finite" in problems[0]
    assert "5" in problems[0]


def test_structural_problems_flags_nan_asc_and_nan_mc():
    cusps = [float(i * 30.0) for i in range(12)]
    assert _structural_problems(cusps) == []
    assert _structural_problems(cusps, asc=float("nan"), mc=270.0)
    assert _structural_problems(cusps, asc=180.0, mc=float("nan"))
    both = _structural_problems(cusps, asc=float("nan"), mc=float("nan"))
    assert "asc" in both[0] and "mc" in both[0]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_structural_problems_flags_infinities(bad):
    assert _structural_problems([bad] * 12)
    assert _structural_problems([0.0] * 12, asc=bad, mc=bad)


def test_structural_problems_ignores_finite_charts():
    """A sound chart must still pass cleanly -- the control for all of the above."""
    result = compute_houses(JULIAN_DAY, 45.0, 30.0, system="Equal")
    assert _structural_problems(list(result.cusps), asc=result.asc, mc=result.mc) == []


def test_finite_chart_at_extreme_but_real_julian_day_still_works():
    """1e9 is absurd but finite, and swe handles it; we must not break it."""
    result = compute_houses(1e9, 10.0, 30.0, system="Equal")
    assert_structurally_valid(list(result.cusps))
    assert all(isfinite(v) for v in list(result.cusps) + [result.asc, result.mc])


# ---------------------------------------------------------------------------
# 11. The non-finite warning path is unreachable with real swe output
# ---------------------------------------------------------------------------
#
# Swept jd = 1e20/1e30/1e40/1e50/1e60/1e70/1e80/1e90/1e100/1e200/1e300/1e308 at
# lat=0 lon=180 (count of non-finite outputs per system; -1 means swe raised):
#
#   jd        Plac  Koch  Regio  Camp  Porph  Equal  Whole
#   1e20      0     0     0     0     0      0      0
#   1e30      0     0     0     0     0      0      0
#   1e40+    -1    11    11    11    11     13     13
#
# So there is NO Julian day at which one system returns non-finite values while
# another returns a sound chart: Placidus either works or raises, and every
# other system turns non-finite together. The "non-finite requested system falls
# back with a warning" branch is therefore unreachable from real swe output and
# is covered here with a stubbed _fetch, so the code path is not merely assumed.


def test_non_finite_requested_system_warns_and_uses_a_sound_fallback(monkeypatch):
    sound_cusps = [float((30 * i + 10) % 360) for i in range(12)]
    real_fetch = astro_houses._fetch

    def fake_fetch(julian_day, latitude, longitude, name):
        if name == "Porphyry":
            cusps = list(sound_cusps)
            cusps[2] = float("nan")
            return cusps, float("nan"), 270.0
        return real_fetch(julian_day, latitude, longitude, name)

    monkeypatch.setattr(astro_houses, "_fetch", fake_fetch)
    result = compute_houses(JULIAN_DAY, 10.0, 30.0, system="Porphyry", fallback="Equal")

    assert result.system_requested == "Porphyry"
    assert result.system_used == "Equal"
    assert result.fallback_used is True
    # The reason must be the non-finite OUTPUT, not a pretend latitude problem.
    assert any("non-finite" in w for w in result.warnings)
    assert not any("cannot be computed at latitude" in w for w in result.warnings)
    assert_structurally_valid(list(result.cusps))


def test_sound_requested_but_non_finite_fallback_raises(monkeypatch):
    """The requested chart is real but bunched, so the fallback is consulted."""

    def fake_fetch(julian_day, latitude, longitude, name):
        if name == "Porphyry":
            return [float("nan")] * 12, float("nan"), float("nan")
        # Sound (spans 360, every step positive) but bunched to 1 deg, which is
        # below the 5 deg threshold, so it is unusable and the fallback runs.
        return [float(i) for i in range(12)], 0.0, 90.0

    monkeypatch.setattr(astro_houses, "_fetch", fake_fetch)
    with pytest.raises(HouseCalculationError) as excinfo:
        compute_houses(JULIAN_DAY, 10.0, 30.0, system="Placidus", fallback="Porphyry")
    assert "non-finite" in str(excinfo.value)


def test_non_finite_output_never_reaches_a_returned_result(monkeypatch):
    """Whatever swe hands back, nothing non-finite may reach a HouseResult."""

    def fake_fetch(julian_day, latitude, longitude, name):
        cusps = [float((30 * i + 10) % 360) for i in range(12)]
        cusps[5] = float("inf")
        return cusps, 10.0, float("-inf")

    monkeypatch.setattr(astro_houses, "_fetch", fake_fetch)
    with pytest.raises(HouseCalculationError):
        compute_houses(JULIAN_DAY, 10.0, 30.0, system="Porphyry", fallback="Porphyry")
