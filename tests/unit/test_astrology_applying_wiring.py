# tests/unit/test_astrology_applying_wiring.py
"""ADP-1: core/astrology.py must delegate applying/separating to core.astro.aspects.

WHY THIS FILE EXISTS
--------------------
``core/astrology.py`` computed applying/separating itself in two places, with two
different - and in both cases angle-blind - formulas:

* ``get_transits_to_natal``: ``d_sep_dt = t_speed - n_speed`` and a sign test
  against the offset from the CONJUNCTION.
* ``get_natal_aspects``: ``d_sep_dt = speed2 - speed1``, which does track the gap
  between the two bodies and is therefore correct for conjunctions, but is still
  measured from 0 deg rather than from the aspect angle.

Both are replaced by :func:`core.astro.aspects.aspect_state`. The physics and its
derivation live in that module and are proven by ``test_astro_aspects.py``; this
file proves the WIRING, by driving the two real project loops.

HOW THE EXPECTED VALUES ARE OBTAINED
-------------------------------------
Never from ``aspect_state``. Every expectation is computed here by brute force:
step both bodies forward by a small dt and observe whether the orb shrinks,
grows, or is unchanged. If the module and the loops ever disagree, the module is
wrong - which is the whole point of the check.

Offline: the ephemeris is stubbed out, so no Swiss Ephemeris file is read.
"""

from __future__ import annotations

import datetime as _dt

import pytest

import core.astrology as ast

ANGLES = {"Conjunction": 0.0, "Sextile": 60.0, "Square": 90.0, "Trine": 120.0, "Opposition": 180.0}
LOW_TO_TITLE = {
    "conjunction": "Conjunction",
    "sextile": "Sextile",
    "square": "Square",
    "trine": "Trine",
    "opposition": "Opposition",
}

NATAL_DT = _dt.datetime(2026, 1, 1)
TRANSIT_DT = _dt.datetime(2026, 1, 2)
DT = 1e-4


# --------------------------------------------------------------------------- #
# The independent oracle.
# --------------------------------------------------------------------------- #
def _orb(lon_a: float, lon_b: float, angle: float) -> float:
    sep = abs(((lon_a - lon_b + 180.0) % 360.0) - 180.0)
    return abs(sep - angle)


def oracle_applying(lon_a, speed_a, lon_b, speed_b, angle, *, static_target: bool) -> bool | None:
    """True = orb shrinks, False = orb grows, None = the orb never changes.

    Brute force by finite difference; it shares no code with aspect_state.
    """
    eff_b = 0.0 if static_target else speed_b
    now = _orb(lon_a, lon_b, angle)
    after = _orb(lon_a + speed_a * DT, lon_b + eff_b * DT, angle)
    if abs(after - now) <= 1e-12:
        return None
    return after < now


# --------------------------------------------------------------------------- #
# Stubbed-ephemeris drivers for the two real loops.
# --------------------------------------------------------------------------- #
def _calculator() -> ast.AstrologicalCalculator:
    calc = ast.AstrologicalCalculator.__new__(ast.AstrologicalCalculator)
    calc.SIGNS = ["Aries"] * 12
    calc.get_julian_day = lambda dt: 2451545.0
    return calc


def _transit_loop(lon_t, speed_t, lon_n, speed_n) -> dict[str, bool | None]:
    """Drive the REAL get_transits_to_natal. Returns {AspectName: applying}."""
    calc = _calculator()
    calc.get_planetary_positions = lambda dt, loc: (
        {"Sun": {"longitude": lon_t, "speed": speed_t}}
        if dt == TRANSIT_DT
        else {"Moon": {"longitude": lon_n, "speed": speed_n}}
    )
    out = calc.get_transits_to_natal(NATAL_DT, (0.0, 0.0), TRANSIT_DT)
    return {r["aspect"]: r["applying"] for r in out if r["transit_planet"] == "Sun" and r["natal_planet"] == "Moon"}


def _natal_loop(lon1, speed1, lon2, speed2) -> dict[str, bool | None]:
    """Drive the REAL get_natal_aspects. Returns {AspectName: applying}."""
    calc = _calculator()
    calc.get_planetary_positions = lambda dt, loc: {
        "venus": {"longitude": lon1, "speed": speed1},
        "mars": {"longitude": lon2, "speed": speed2},
    }
    out = calc.get_natal_aspects(NATAL_DT)
    return {LOW_TO_TITLE[r["aspect"]]: r["applying"] for r in out}


# --------------------------------------------------------------------------- #
# 1. Loop 1: get_transits_to_natal, the natal point is STATIC.
# --------------------------------------------------------------------------- #
_GRID = [
    (name, offset, speed_t, speed_n)
    for name in ANGLES
    for offset in (-5.0, 5.0)
    for speed_t in (1.0, -1.0)
    for speed_n in (0.0, 1.0)
]
_GRID_IDS = [f"{n}-off{o:+.0f}-t{s:+.0f}-n{ns:+.0f}" for n, o, s, ns in _GRID]


@pytest.mark.parametrize(("name", "offset", "speed_t", "speed_n"), _GRID, ids=_GRID_IDS)
def test_transit_loop_matches_the_oracle(name, offset, speed_t, speed_n):
    lon_n = 0.0
    lon_t = (name and ANGLES[name] + offset) % 360.0
    got = _transit_loop(lon_t, speed_t, lon_n, speed_n)[name]
    expected = oracle_applying(lon_t, speed_t, lon_n, speed_n, ANGLES[name], static_target=True)
    assert got == expected, (
        f"get_transits_to_natal {name} off{offset:+.0f} t={speed_t:+.1f} n={speed_n:+.1f}: "
        f"got {got!r}, brute-force oracle says {expected!r}"
    )


@pytest.mark.parametrize(
    ("name", "offset", "speed_t"),
    [(n, o, s) for n in ANGLES for o in (-5.0, 5.0) for s in (1.0, -1.0)],
    ids=[f"{n}-off{o:+.0f}-t{s:+.0f}" for n in ANGLES for o in (-5.0, 5.0) for s in (1.0, -1.0)],
)
def test_transit_loop_ignores_the_natal_speed_entirely(name, offset, speed_t):
    """A natal body is static: its birth-time speed must not move the answer at all.

    The natal speed is varied over four orders of magnitude, including a fast
    retrograde one. Before ADP-1 the old code subtracted it and the answer moved.
    """
    lon_n = 0.0
    lon_t = (ANGLES[name] + offset) % 360.0
    baseline = _transit_loop(lon_t, speed_t, lon_n, 0.0)[name]
    expected = oracle_applying(lon_t, speed_t, lon_n, 0.0, ANGLES[name], static_target=True)

    assert baseline == expected, f"baseline itself is wrong: {baseline!r} != {expected!r}"
    for speed_n in (-12.0, -0.5, 0.5, 12.0, 1e6):
        got = _transit_loop(lon_t, speed_t, lon_n, speed_n)[name]
        assert got == baseline, (
            f"natal speed {speed_n:+.1e} deg/day changed the answer from {baseline!r} to "
            f"{got!r}; a natal body is static during a transit"
        )


def test_transit_loop_reports_none_when_the_transit_is_stationary():
    """A stationary transit cannot be applying or separating."""
    assert _transit_loop(85.0, 0.0, 0.0, 0.0)["Square"] is None


def test_transit_loop_keeps_the_shape_of_the_payload():
    """ADP-1 must not touch detection, keys, rounding or exactness - only `applying`."""
    calc = _calculator()
    calc.get_planetary_positions = lambda dt, loc: (
        {"Sun": {"longitude": 85.0, "speed": 1.0}} if dt == TRANSIT_DT else {"Moon": {"longitude": 0.0, "speed": 0.0}}
    )
    rows = [
        r
        for r in calc.get_transits_to_natal(NATAL_DT, (0.0, 0.0), TRANSIT_DT)
        if r["transit_planet"] == "Sun" and r["natal_planet"] == "Moon"
    ]
    assert rows
    assert set(rows[0]) == {
        "transit_planet",
        "natal_planet",
        "aspect",
        "angle",
        "orb",
        "exactness",
        "applying",
        "description",
    }, f"payload keys changed: {sorted(rows[0])}"
    square = next(r for r in rows if r["aspect"] == "Square")
    assert square["angle"] == 85.0
    assert square["orb"] == 5.0
    assert square["exactness"] == 0.38, (
        "exactness is round(1 - orb/aspect_orb, 2) = round(0.375, 2); a 5.0 square orb "
        "in an 8.0 table must give 0.38, not 0.375"
    )
    assert square["applying"] is True


# --------------------------------------------------------------------------- #
# 2. Loop 2: get_natal_aspects, BOTH bodies move.
# --------------------------------------------------------------------------- #
_NATAL_GRID = [
    (name, offset, speed1, speed2)
    for name in ANGLES
    for offset in (-5.0, 5.0)
    for speed1 in (1.0, -1.0)
    for speed2 in (0.0, 1.0)
]
_NATAL_IDS = [f"{n}-off{o:+.0f}-s1{a:+.0f}-s2{b:+.0f}" for n, o, a, b in _NATAL_GRID]


@pytest.mark.parametrize(("name", "offset", "speed1", "speed2"), _NATAL_GRID, ids=_NATAL_IDS)
def test_natal_loop_matches_the_oracle(name, offset, speed1, speed2):
    lon2 = 0.0
    lon1 = (ANGLES[name] + offset) % 360.0
    got = _natal_loop(lon1, speed1, lon2, speed2)[name]
    expected = oracle_applying(lon1, speed1, lon2, speed2, ANGLES[name], static_target=False)
    assert got == expected, (
        f"get_natal_aspects {name} off{offset:+.0f} s1={speed1:+.1f} s2={speed2:+.1f}: "
        f"got {got!r}, brute-force oracle says {expected!r}"
    )


def test_natal_loop_reports_none_for_equal_speeds():
    """Both bodies moving together keep a constant separation: no direction."""
    assert _natal_loop(85.0, 1.0, 0.0, 1.0)["Square"] is None


def test_natal_loop_still_gets_conjunctions_right():
    """The old loop 2 formula tracked the gap lon2-lon1, so conjunctions were already
    correct. This is a regression guard: the replacement must not break them."""
    for offset in (-5.0, 5.0):
        for s1, s2 in ((1.0, 0.0), (-1.0, 0.0), (1.0, 1.0), (-1.0, 1.0)):
            lon1 = (offset) % 360.0
            got = _natal_loop(lon1, s1, 0.0, s2)["Conjunction"]
            expected = oracle_applying(lon1, s1, 0.0, s2, 0.0, static_target=False)
            assert got == expected, f"conjunction regressed: {got!r} != {expected!r}"


def test_natal_loop_keeps_the_shape_of_the_payload():
    calc = _calculator()
    calc.get_planetary_positions = lambda dt, loc: {
        "venus": {"longitude": 85.0, "speed": 1.0},
        "mars": {"longitude": 0.0, "speed": 0.0},
    }
    rows = calc.get_natal_aspects(NATAL_DT)
    assert rows
    assert set(rows[0]) == {
        "planet_a",
        "planet_b",
        "aspect",
        "orb",
        "applying",
    }, f"payload keys changed: {sorted(rows[0])}"
    square = next(r for r in rows if r["aspect"] == "square")
    assert square["planet_a"] == "venus"
    assert square["planet_b"] == "mars"
    assert square["orb"] == pytest.approx(5.0)
    assert square["applying"] is True


# --------------------------------------------------------------------------- #
# 3. The seam itself.
# --------------------------------------------------------------------------- #
def test_core_astrology_delegates_to_the_aspects_module(monkeypatch):
    """core/astrology.py must import and call aspect_state, not reimplement it.

    The delegation is proved BEHAVIOURALLY, by replacing the imported name with a
    recorder and watching the real loops call it. An earlier version of this test
    read the SOURCE TEXT of core/astrology.py, which made it fail whenever
    another seat was halfway through editing that file - a transient failure I
    saw in a full-suite run and could not reproduce alone. Behaviour does not
    move under a concurrent edit.
    """
    from core.astro import aspects as aspects_mod

    assert (
        ast.aspect_state is aspects_mod.aspect_state
    ), "core/astrology.py has its own aspect_state; it must be the one from core.astro.aspects"

    calls: list[dict] = []

    def recorder(lon_a, speed_a, lon_b, speed_b, aspect_angle, **kwargs):
        calls.append(
            {
                "lon_a": lon_a,
                "speed_a": speed_a,
                "lon_b": lon_b,
                "speed_b": speed_b,
                "aspect_angle": aspect_angle,
                "kwargs": kwargs,
            }
        )
        return aspects_mod.aspect_state(lon_a, speed_a, lon_b, speed_b, aspect_angle, **kwargs)

    monkeypatch.setattr(ast, "aspect_state", recorder)

    _transit_loop(85.0, 1.0, 0.0, 0.0)
    assert calls, "get_transits_to_natal did not call aspect_state"
    assert calls[0]["kwargs"].get("static_target") is True, "transit-to-natal must pin the natal speed to 0"

    calls.clear()
    calc = _calculator()
    calc.get_planetary_positions = lambda dt, loc: {
        "venus": {"longitude": 85.0, "speed": 1.0},
        "mars": {"longitude": 0.0, "speed": 0.0},
    }
    calc.get_natal_aspects(_dt.datetime(2026, 1, 1))
    assert calls, "get_natal_aspects did not call aspect_state"
    assert "static_target" not in calls[0]["kwargs"], "both natal bodies move; static_target must not be forced here"


def test_no_astro_module_imports_core_astrology():
    """Guards the import direction: core.astro must stay a leaf.

    Matches real IMPORT STATEMENTS only. A docstring that merely mentions
    ``core.astrology`` (several do, to explain why a module exists) is not a cycle.
    """
    import pathlib
    import re

    package = pathlib.Path(ast.__file__).resolve().parent / "astro"
    pattern = re.compile(r"^\s*(?:import\s+core|from\s+core)\b", re.MULTILINE)
    offenders = [p.name for p in sorted(package.glob("*.py")) if pattern.search(p.read_text())]
    assert not offenders, f"core/astro modules importing core.*: {offenders}"


# --------------------------------------------------------------------------- #
# W1-5b: a bad speed must not raise through a whole chart.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bad_speed",
    [float("nan"), float("inf"), float("-inf"), True, False],
    ids=["nan", "inf", "-inf", "true", "false"],
)
def test_an_unusable_speed_makes_applying_none_not_an_exception(monkeypatch, bad_speed):
    """One bad number in a position table must not take the chart down.

    ``isinstance(nan, int | float)`` is True, so the old guard let NaN through
    and the row silently reported ``applying False``. A bool is an int, so
    ``True`` was read as a speed of 1 degree per day.
    """
    result = _transit_loop(85.0, bad_speed, 0.0, 0.0)
    assert result["Square"] is None, f"a speed of {bad_speed!r} must be treated as 'no speed', got {result['Square']!r}"


@pytest.mark.parametrize(
    "bad_speed",
    [float("nan"), float("inf"), True],
    ids=["nan", "inf", "true"],
)
def test_an_unusable_natal_speed_makes_applying_none(bad_speed):
    result = _transit_loop(85.0, 1.0, 0.0, bad_speed)
    assert result["Square"] is None


def test_a_string_speed_is_treated_as_no_speed():
    """A string is not a number; the row must not raise."""
    result = _transit_loop(85.0, "fast", 0.0, 0.0)
    assert result["Square"] is None


def test_a_good_speed_still_produces_a_direction():
    """The guard must not swallow real speeds."""
    assert _transit_loop(85.0, 1.0, 0.0, 0.0)["Square"] is True
    assert _transit_loop(85.0, -1.0, 0.0, 0.0)["Square"] is False


def test_a_nan_longitude_does_not_take_the_chart_down():
    """A NaN LONGITUDE is a different thing: it breaks the separation itself.

    The pure module refuses it with AspectError, so the chart cannot be built.
    The point of this test is that the failure is a clean refusal, not a NaN
    orb with a confident ``applying``.
    """
    from core.astro.aspects import AspectError

    with pytest.raises(AspectError):
        from core.astro.aspects import aspect_state

        aspect_state(float("nan"), 1.0, 0.0, 0.0, 90.0)
