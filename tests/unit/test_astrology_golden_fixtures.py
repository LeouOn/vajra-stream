"""Golden-chart regression harness for ``core.astrology.AstrologicalCalculator``.

Why this exists
---------------
Wave W0-B audited the ephemeris arithmetic and found it accurate (Sun <= 1.3", Moon
<= 15.2", worst planet 62.6", ASC/MC <= 21.4"). That verdict is only trustworthy if
something keeps re-checking it. This module freezes 10 reference charts in
``tests/fixtures/astrology_golden_charts.json`` and asserts the project still lands on
them, so any future change that quietly moves a position, a sign, a retrograde flag or
a cusp fails here instead of in a user's chart.

The expected values are INDEPENDENT of the project
--------------------------------------------------
They were computed with astropy's BUILTIN ERFA ephemeris (VSOP87/PLAN94), by a
derivation that shares no code with the pyswisseph path under test. Storing
project-derived numbers here would make every assertion a tautology -- the project
would be compared with itself. Provenance, library versions, time scale and the
rationale for each tolerance are recorded in the fixture itself.

Tolerances (from W0-B; see fixture ``provenance.tolerance_rationale``)
---------------------------------------------------------------------
Sun <= 5", Moon <= 30", planets <= 90", ASC/MC <= 40". They are per-entry in the
fixture, not hard-coded here, so a fixture edit is visible in a diff.

Known defects
-------------
Four defects found in W0 are pinned as ``pytest.mark.xfail(strict=True)`` so that the
day one is fixed the suite reports XPASS(strict) and fails, forcing the stale
expectation to be removed deliberately rather than left to rot. Each reason names the
specific code path, and each marker carries an explicit ``raises=`` clause: without it
a strict xfail tolerates ANY exception, so an unrelated crash inside the calculator
would be silently reported as "the known defect" and the real error would be hidden.
The ``raises=`` values were not guessed - they were read off a ``--runxfail`` run of all
27 markers. They are grouped at the bottom of this file under ``known_defects_...``.

Offline and side-effect free
----------------------------
No network, no ephemeris download, no server, no audio. The repository's
``tests/conftest.py`` already exports a session scratch ``DATABASE_URL`` and installs
a hard ``sqlite3.connect`` guard that refuses to open the live repository database, so
this module *cooperates* with it: it only supplies a scratch URL when conftest has not
(one is needed for a bare ``python``/``pytest --confcutdir`` invocation outside the
suite). The relative three-slash form ``sqlite:///tmp/x.db`` resolves into the
repository root, so any URL this module does supply is written with four slashes.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import swisseph

# --------------------------------------------------------------------------- #
# Environment. Must happen before any project import (ADR 002 backend_settings).
# tests/conftest.py normally sets this first; never clobber a scratch URL it chose,
# and never let an unset value fall through to the live repository database.
# --------------------------------------------------------------------------- #
if not os.environ.get("DATABASE_URL"):
    _OWN_SCRATCH_DB = Path(tempfile.gettempdir()) / "vajra_golden_charts_scratch.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{_OWN_SCRATCH_DB}"  # 4 slashes -> absolute
for _key in (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "LMSTUDIO_API_KEY",
    "DEEPSEEK_API_KEY",
    "ELEVENLABS_API_KEY",
):
    if os.environ.get(_key):
        os.environ[_key] = ""

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "astrology_golden_charts.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
CHARTS = FIXTURE["charts"]
BY_ID = {c["id"]: c for c in CHARTS}

UTC = timezone.utc
ANGLE_BODIES = ("ASC", "MC")  # names as used in the fixture's "expected" mapping

# Charts that carry a geographic location (ASC/MC/houses are undefined without one).
LOCATED = [c for c in CHARTS if c["location"] is not None]
# C8 sits above the polar circle: Placidus/Koch cannot be computed there.
POLAR_FAILING = [c for c in LOCATED if abs(c["location"]["latitude"]) >= 67.0]

_NODE_REASON = (
    "KNOWN DEFECT (W0-B): core/astrology.py exposes only north_node via "
    "swe.MEAN_NODE. There is no south node and no true node anywhere in the module, "
    "so the antipodal pairing cannot be asserted. Expected value is deliberately "
    "absent rather than invented."
)
_CHIRON_REASON = (
    "KNOWN DEFECT (W0-B): get_planetary_positions returns 11 bodies, not 12. "
    "core/astrology.py calls swe.set_ephe_path('') and no .se1 asteroid files are "
    "present, so swe.calc_ut(jd, swe.CHIRON) raises \"SwissEph file 'seas_18.se1' not "
    'found in PATH" and the surrounding `except Exception: pass` discards it silently. '
    "A user asking for Chiron gets no Chiron and no warning."
)
_POLAR_REASON = (
    "KNOWN DEFECT (W0-B): get_western_astrology hardcodes Placidus (b'P') and ignores "
    "the Swiss Ephemeris return flag. Above |lat| >= 67 deg swe.houses returns "
    "EFLG_ERROR and raises, and the exception propagates uncaught out of the "
    "calculator instead of falling back to an equal/whole-sign house system."
)
_KERYKEION_REASON = (
    "KNOWN DEFECT (W0-B): backend/core/services/astrology_chart_service.py builds a "
    "Kerykeion subject and asks it for 'mean_node'/'true_node', but Kerykeion 6.0.4 "
    "names those attributes mean_north_lunar_node / true_north_lunar_node. getattr(x, "
    "'mean_node', None) therefore yields None and /natal-chart returns a chart with no "
    "lunar nodes and no error. Only the attribute names are asserted here; the HTTP "
    "route is out of scope for this ticket."
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _s360(x: float) -> float:
    """Wrap to [-180, 180) so a delta is never measured the long way round."""
    return ((x + 180.0) % 360.0) - 180.0


def _delta_arcsec(a: float, b: float) -> float:
    return abs(_s360(a - b)) * 3600.0


def _instant(chart: dict) -> datetime:
    return datetime.fromisoformat(chart["instant_utc"]).astimezone(UTC)


def _loc(chart: dict):
    if chart["location"] is None:
        return None
    return (chart["location"]["latitude"], chart["location"]["longitude"])


#: Keys get_western_astrology uses for the two chart angles. They are excluded from
#: planet-level assertions (no speed, no house) because the angle-assignment loop in
#: core/astrology.py skips them explicitly.
ANGLE_KEYS = ("ascendant", "midheaven")


def _located_params() -> list:
    """Parametrisation over located charts, marking the above-polar-circle ones xfail.

    ``raises=swisseph.Error`` is required, not decorative: without it a strict xfail
    tolerates ANY exception, so an unrelated RuntimeError raised inside the calculator
    would be reported as "known polar-circle defect" and the real error would be hidden.
    Observed with ``--runxfail`` on 2026-10-20: all six polar markers raise
    ``swisseph.houses: error`` out of swe.houses at |lat| >= 67.
    """
    return [
        pytest.param(
            c,
            id=c["id"],
            marks=pytest.mark.xfail(strict=True, reason=_POLAR_REASON, raises=swisseph.Error),
        )
        if c in POLAR_FAILING
        else pytest.param(c, id=c["id"])
        for c in LOCATED
    ]


def _calc():
    from core.astrology import AstrologicalCalculator

    return AstrologicalCalculator()


@pytest.fixture(scope="module")
def calculator():
    return _calc()


# --------------------------------------------------------------------------- #
# Fixture self-validation: the provenance is part of the contract.
# --------------------------------------------------------------------------- #
def test_fixture_records_its_provenance():
    prov = FIXTURE["provenance"]
    for key in (
        "astropy_version",
        "erfa_version",
        "pyswisseph_version",
        "time_scale",
        "method",
        "tolerances_arcsec",
        "tolerance_rationale",
        "known_limits",
    ):
        assert prov.get(key), f"provenance.{key} is missing"
    assert "astropy" in prov["method"].lower()
    assert prov["tolerance_rationale"].strip()


def test_fixture_covers_the_required_events():
    ids = set(BY_ID)
    assert len(CHARTS) == 10, "W1-1 specifies 10 reference charts"
    for required in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"):
        assert required in ids, f"chart {required} is missing"
    assert BY_ID["C1"]["instant_utc"].startswith("2000-01-01T11:58:5")
    assert BY_ID["C5"]["location"]["latitude"] < 0, "C5 must be a southern-hemisphere chart"
    assert BY_ID["C6"]["instant_utc"].startswith("1901"), "C6 must pre-date 1950"
    assert 60 <= BY_ID["C7"]["location"]["latitude"] < 67
    assert BY_ID["C8"]["location"]["latitude"] >= 67


def test_every_chart_entry_states_a_tolerance_or_why_it_cannot():
    for chart in CHARTS:
        assert chart["expected"], f"{chart['id']} has no expected values"
        for name, spec in chart["expected"].items():
            if "unverifiable" in spec:
                assert spec["unverifiable"].strip(), f"{chart['id']}/{name} has no reason"
                continue
            assert isinstance(spec["tolerance_arcsec"], int)
            assert spec["tolerance_arcsec"] > 0
            assert isinstance(spec["longitude_of_date_deg"], float)
            assert 0.0 <= spec["longitude_of_date_deg"] < 360.0


def _db_path() -> Path:
    """Filesystem path the current DATABASE_URL points at."""
    return Path(os.path.realpath(os.environ["DATABASE_URL"].replace("sqlite:///", "", 1)))


def _live_db_paths() -> set[str]:
    repo_root = Path(__file__).resolve().parents[2]
    return {
        Path(os.path.realpath(repo_root / "vajra_stream.db")).as_posix(),
        Path(os.path.realpath(repo_root / "backend" / "app" / "vajra_stream.db")).as_posix(),
    }


def _allowed_scratch_roots() -> tuple[Path, ...]:
    """Mirror the allowlist in ``tests/conftest.py::_is_scratch_db_path``.

    There are TWO sanctioned scratch roots, not one: the session temp dir that
    conftest creates, and ``tests/integration/.pytest_tmp`` used by the extraction
    tests, which may leave ``DATABASE_URL`` pointing at its own scratch file.
    """
    repo_root = Path(__file__).resolve().parents[2]
    return (
        Path(os.path.realpath(tempfile.gettempdir())),
        Path(os.path.realpath(repo_root / "tests" / "integration" / ".pytest_tmp")),
    )


def test_runs_against_a_scratch_database():
    """Guardrail: this module must never open the repository's live vajra_stream.db."""
    assert (
        _db_path().as_posix() not in _live_db_paths()
    ), f"DATABASE_URL points at a live repository database: {_db_path()}"
    assert any(_db_path().is_relative_to(root) for root in _allowed_scratch_roots()), (
        f"scratch database {str(_db_path())!r} is under none of the allowed scratch "
        f"roots: {[str(r) for r in _allowed_scratch_roots()]}"
    )


# --------------------------------------------------------------------------- #
# The golden assertions: project vs INDEPENDENT reference.
# --------------------------------------------------------------------------- #
_POSITION_CASES = [
    pytest.param(c, body, id=f"{c['id']}-{body}")
    for c in CHARTS
    for body, spec in c["expected"].items()
    if body not in ANGLE_BODIES and "unverifiable" not in spec
]


@pytest.mark.parametrize("chart,body", _POSITION_CASES)
def test_longitude_matches_independent_reference(calculator, chart, body):
    spec = chart["expected"][body]
    got = calculator.get_planetary_positions(_instant(chart), _loc(chart))[body]["longitude"]
    delta = _delta_arcsec(got, spec["longitude_of_date_deg"])
    assert delta <= spec["tolerance_arcsec"], (
        f"{chart['id']} {body}: project {got:.6f} deg vs independent "
        f"{spec['longitude_of_date_deg']:.6f} deg -> {delta:.1f}\" "
        f"(tolerance {spec['tolerance_arcsec']}\")"
    )


_ASC_CASES = _located_params()
_MC_CASES = _located_params()


@pytest.mark.parametrize("chart", _ASC_CASES)
def test_ascendant_matches_independent_reference(calculator, chart):
    spec = chart["expected"]["ASC"]
    got = calculator.get_western_astrology(_instant(chart), _loc(chart))["positions"]["ascendant"]["longitude"]
    delta = _delta_arcsec(got, spec["longitude_of_date_deg"])
    assert delta <= spec["tolerance_arcsec"], (
        f"{chart['id']} ASC: project {got:.6f} vs independent "
        f"{spec['longitude_of_date_deg']:.6f} -> {delta:.1f}\" "
        f"(tolerance {spec['tolerance_arcsec']}\")"
    )


@pytest.mark.parametrize("chart", _MC_CASES)
def test_midheaven_matches_independent_reference(calculator, chart):
    spec = chart["expected"]["MC"]
    got = calculator.get_western_astrology(_instant(chart), _loc(chart))["positions"]["midheaven"]["longitude"]
    delta = _delta_arcsec(got, spec["longitude_of_date_deg"])
    assert delta <= spec["tolerance_arcsec"], (
        f"{chart['id']} MC: project {got:.6f} vs independent "
        f"{spec['longitude_of_date_deg']:.6f} -> {delta:.1f}\" "
        f"(tolerance {spec['tolerance_arcsec']}\")"
    )


# --------------------------------------------------------------------------- #
# Analytic event checks: these need no published table at all, so they are the
# strongest statements in the file.
# --------------------------------------------------------------------------- #
def test_march_equinox_chart_has_sun_at_zero_longitude(calculator):
    chart = BY_ID["C2"]
    got = calculator.get_planetary_positions(_instant(chart), None)["sun"]["longitude"]
    assert (
        abs(_s360(got)) * 3600.0 <= chart["expected"]["sun"]["tolerance_arcsec"]
    ), f"Sun longitude {got:.6f} deg is not within tolerance of 0 deg (equinox)"


def test_june_solstice_chart_has_sun_at_ninety_longitudes(calculator):
    chart = BY_ID["C3"]
    got = calculator.get_planetary_positions(_instant(chart), None)["sun"]["longitude"]
    assert (
        abs(_s360(got - 90.0)) * 3600.0 <= chart["expected"]["sun"]["tolerance_arcsec"]
    ), f"Sun longitude {got:.6f} deg is not within tolerance of 90 deg (solstice)"


def test_new_moon_chart_has_sun_and_moon_conjoined(calculator):
    chart = BY_ID["C4"]
    pos = calculator.get_planetary_positions(_instant(chart), None)
    separation = _delta_arcsec(pos["sun"]["longitude"], pos["moon"]["longitude"])
    assert separation <= 3600.0, (
        f"new-moon chart: Sun and Moon are {separation / 3600:.4f} deg apart, expected " f"conjunction within 1 deg"
    )


def test_j2000_chart_uses_the_ut_instant_of_j2000_tt(calculator):
    """2000-01-01 12:00:00 TT is 11:58:55.8166 UT; the fixture must say UT, not TT."""
    assert BY_ID["C1"]["instant_utc"] == "2000-01-01T11:58:55.816000+00:00"
    got = calculator.get_planetary_positions(_instant(BY_ID["C1"]), None)["sun"]["longitude"]
    expected = BY_ID["C1"]["expected"]["sun"]["longitude_of_date_deg"]
    assert _delta_arcsec(got, expected) <= BY_ID["C1"]["expected"]["sun"]["tolerance_arcsec"]


# --------------------------------------------------------------------------- #
# Self-consistency: true for every chart, independent of any reference table.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chart", [pytest.param(c, id=c["id"]) for c in CHARTS])
def test_retrograde_flag_agrees_with_the_sign_of_the_speed(calculator, chart):
    for name, info in calculator.get_planetary_positions(_instant(chart), _loc(chart)).items():
        assert info["retrograde"] == (
            info["speed"] < 0
        ), f"{chart['id']} {name}: retrograde={info['retrograde']} but speed={info['speed']}"


@pytest.mark.parametrize("chart", [pytest.param(c, id=c["id"]) for c in CHARTS])
def test_sign_and_degree_reconstruct_the_longitude(calculator, chart):
    zodiac = [
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
    ]
    for name, info in calculator.get_planetary_positions(_instant(chart), _loc(chart)).items():
        index = zodiac.index(info["sign"])
        reconstructed = index * 30.0 + info["degree"]
        assert abs(_s360(reconstructed - info["longitude"])) * 3600.0 < 1.0, (
            f"{chart['id']} {name}: sign/degree {info['sign']} {info['degree']:.4f} "
            f"reconstructs {reconstructed:.4f}, not {info['longitude']:.4f}"
        )


@pytest.mark.parametrize("chart", _located_params())
def _cusp_steps(cusps: list[float]) -> list[float]:
    """The twelve mod-360 steps around the closed cusp ring."""
    return [(cusps[(i + 1) % 12] - cusps[i]) % 360.0 for i in range(12)]


def _assert_cusp_ring(cusps: list[float], label: str) -> None:
    """Assert the cusps form exactly ONE increasing lap of the zodiac.

    The invariant is the mod-360 step between consecutive cusps, INCLUDING the closing
    step from cusp 12 back to cusp 1: every step must be > 0 and the steps must total
    360. A list that runs backwards fails on a non-positive step; a list that wraps the
    zodiac several times fails on the total.

    Nothing is unwrapped. An unwrap loop ("while value <= previous: value += 360")
    constructs monotonicity instead of testing it: it makes any input look increasing,
    so a chart wrapping the zodiac eleven times would sail through. That was a real
    tautology in this file and is what these helpers replace.
    """
    assert len(cusps) == 12, f"{label}: expected 12 cusps, got {len(cusps)}"
    steps = _cusp_steps(cusps)
    backwards = [i for i, step in enumerate(steps) if step <= 0.0]
    assert not backwards, f"{label}: non-positive cusp step(s) at index {backwards}; steps={steps}"
    total = sum(steps)
    assert abs(total - 360.0) < 1e-6, (
        f"{label}: cusp steps total {total:.9f}, not 360 - the ring wraps " f"{total / 360.0:.3f} times instead of once"
    )


def _assert_whole_sign_cusps(cusps: list[float], ascendant: float, label: str) -> None:
    """Whole Sign houses: one lap, every step exactly 30 deg, cusp 1 = start of the
    Ascendant's SIGN (not the Ascendant's degree)."""
    _assert_cusp_ring(cusps, label)
    steps = _cusp_steps(cusps)
    assert all(
        abs(step - 30.0) < 1e-6 for step in steps
    ), f"{label}: whole-sign cusp steps must all be 30 deg, got {steps}"
    sign_start = (int(ascendant // 30) % 12) * 30.0
    assert abs(_s360(cusps[0] - sign_start)) < 1e-9, (
        f"{label}: whole-sign cusp 1 must be the START OF THE ASCENDANT'S SIGN "
        f"({sign_start}), not the Ascendant degree itself ({ascendant})"
    )


@pytest.mark.parametrize("chart", _located_params())
def test_whole_sign_cusps_form_one_lap_at_thirty_degrees(calculator, chart):
    """Whole Sign houses guarantee cusps at +30 deg; this must hold for every chart."""
    cusps = calculator.get_house_cusps(_instant(chart), _loc(chart))["whole_sign"]
    ascendant = calculator.get_western_astrology(_instant(chart), _loc(chart))["positions"]["ascendant"]["longitude"]
    _assert_whole_sign_cusps(cusps, ascendant, f"{chart['id']} whole-sign")


@pytest.mark.parametrize("chart", _located_params())
def test_placidus_cusps_form_one_lap_and_start_at_the_ascendant(calculator, chart):
    chart_data = calculator.get_western_astrology(_instant(chart), _loc(chart))
    cusps = calculator.get_house_cusps(_instant(chart), _loc(chart))["placidus"]
    _assert_cusp_ring(cusps, f"{chart['id']} placidus")
    assert (
        abs(_s360(cusps[0] - chart_data["positions"]["ascendant"]["longitude"])) < 1e-9
    ), f"{chart['id']}: Placidus cusp 1 must equal the Ascendant"


# --------------------------------------------------------------------------- #
# Guard tests for the invariants above.
#
# A regression test that cannot fail is worse than no regression test, because it
# reads as coverage. These pin the two pathological shapes that used to pass:
# a cusp list that wraps the zodiac backwards many times, and an "equal from the
# Ascendant" list that puts cusp 1 on the Ascendant's degree instead of the start
# of its sign.
# --------------------------------------------------------------------------- #
def test_cusp_ring_invariant_rejects_a_backward_multiwrap_list():
    """The exact list from review: it runs backwards and wraps eleven times."""
    backwards = [0, 330, 300, 270, 240, 210, 180, 150, 120, 90, 60, 30]
    with pytest.raises(AssertionError):
        _assert_cusp_ring(backwards, "backward-multiwrap")


def test_cusp_ring_invariant_accepts_a_real_single_lap():
    genuine = [161.872, 185.17, 213.971, 247.89, 283.25, 315.012, 341.872, 5.17, 33.971, 67.89, 103.25, 135.012]
    _assert_cusp_ring(genuine, "genuine-placidus-ring")


def test_whole_sign_invariant_rejects_equal_from_ascendant_cusps():
    """An 'equal from the Ascendant' list is a valid one-lap ring but is NOT whole sign."""
    ascendant = 161.872  # Aries 11 deg 52 min - not on a sign boundary
    equal_from_asc = [(ascendant + 30.0 * i) % 360.0 for i in range(12)]
    with pytest.raises(AssertionError):
        _assert_whole_sign_cusps(equal_from_asc, ascendant, "equal-from-ascendant")


def test_whole_sign_invariant_accepts_sign_start_cusps():
    ascendant = 161.872
    sign_start = (int(ascendant // 30) % 12) * 30.0  # 150.0
    whole_sign = [(sign_start + 30.0 * i) % 360.0 for i in range(12)]
    _assert_whole_sign_cusps(whole_sign, ascendant, "genuine-whole-sign")


@pytest.mark.parametrize("chart", [pytest.param(c, id=c["id"]) for c in CHARTS])
def test_north_node_longitude_is_a_normal_ecliptic_longitude(calculator, chart):
    node = calculator.get_planetary_positions(_instant(chart), _loc(chart))["north_node"]
    assert 0.0 <= node["longitude"] < 360.0


@pytest.mark.parametrize("chart", _located_params())
def test_every_planet_receives_a_house_number_between_one_and_twelve(calculator, chart):
    positions = calculator.get_western_astrology(_instant(chart), _loc(chart))["positions"]
    for name, info in positions.items():
        if name in ANGLE_KEYS:
            continue
        assert "house" in info, f"{chart['id']} {name} has no house assignment"
        assert 1 <= info["house"] <= 12, f"{chart['id']} {name} house is {info['house']}"


# --------------------------------------------------------------------------- #
# Known defects from W0, pinned as strict xfails.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chart", [pytest.param(c, id=c["id"]) for c in CHARTS])
@pytest.mark.xfail(strict=True, reason=_CHIRON_REASON, raises=AssertionError)
def test_chiron_is_present_in_the_position_table(calculator, chart):
    positions = calculator.get_planetary_positions(_instant(chart), _loc(chart))
    assert "chiron" in positions, (
        f"{chart['id']}: Chiron is missing; get_planetary_positions returned "
        f"{len(positions)} bodies: {sorted(positions)}"
    )


@pytest.mark.parametrize("chart", [pytest.param(c, id=c["id"]) for c in CHARTS])
@pytest.mark.xfail(strict=True, reason=_NODE_REASON, raises=AssertionError)
def test_south_node_is_present_and_exactly_opposite_the_north_node(calculator, chart):
    positions = calculator.get_planetary_positions(_instant(chart), _loc(chart))
    assert "south_node" in positions, f"{chart['id']}: no south node is reported at all"
    separation = _delta_arcsec(positions["north_node"]["longitude"], positions["south_node"]["longitude"])
    assert (
        abs(separation - 180.0 * 3600.0) < 1.0
    ), f"{chart['id']}: nodes are {separation / 3600:.6f} deg apart, expected 180"


@pytest.mark.xfail(strict=True, reason=_POLAR_REASON, raises=swisseph.Error)
@pytest.mark.parametrize("chart", [pytest.param(c, id=c["id"]) for c in POLAR_FAILING])
def test_high_latitude_chart_fails_cleanly_or_returns_a_chart(calculator, chart):
    """Above the polar circle the calculator must degrade deliberately, not raise."""
    chart_data = calculator.get_western_astrology(_instant(chart), _loc(chart))
    assert chart_data["positions"]["ascendant"]["longitude"] is not None


@pytest.mark.xfail(strict=True, reason=_KERYKEION_REASON, raises=AssertionError)
def test_kerykeion_subject_exposes_the_lunar_nodes_the_service_asks_for():
    """backend/core/services/astrology_chart_service.py reads .mean_node / .true_node."""
    from kerykeion import AstrologicalSubjectFactory

    subject = AstrologicalSubjectFactory.from_birth_data(
        name="Golden",
        year=1990,
        month=7,
        day=4,
        hour=9,
        minute=0,
        lng=9.0,
        lat=45.0,
        tz_str="Europe/Rome",
        online=False,
        suppress_geonames_warning=True,
    )
    missing = [n for n in ("mean_node", "true_node") if not hasattr(subject, n)]
    assert not missing, (
        f"Kerykeion subject has no {missing!r}; Kerykeion 6.0.4 names these "
        f"mean_north_lunar_node / true_north_lunar_node, so the natal chart service "
        f"silently returns a chart with no lunar nodes"
    )
