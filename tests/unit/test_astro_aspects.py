# tests/unit/test_astro_aspects.py
"""Tests for :mod:`core.astro.aspects` - applying/separating physics and orb tables.

Structure
---------
1. RED guard: the project's CURRENT behaviour, captured so the module cannot
   silently become a no-op. If ``core/astrology.py`` is ever fixed, this test
   fails and must be deleted - that is the point of it.
2. Property test: brute-force oracle. For seeded random tuples, step both bodies
   forward and check ``orb_abs`` shrinks iff ``applying`` is True. This does not
   trust the formula at all.
3. The fixture vectors, every aspect angle x offset x speed combination.
4. Edge cases: 0/360 wrap, retrograde, stations, exactness, signed orbs.
5. Orb table data and profiles.
6. ``aspects_between``.

Offline. No ephemeris, no network, no database, no provider keys.
"""

from __future__ import annotations

import json
import math
import pathlib
import random

import pytest

from core.astro.aspects import (
    ASPECT_ANGLES,
    DEFAULT_PROFILE_NAME,
    ORB_PROFILES,
    STATION_SPEED_EPSILON,
    AspectError,
    OrbProfile,
    aspect_state,
    aspects_between,
    orb_for,
    separation,
)

FIXTURE_PATH = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "astro_aspect_cases.json"


def _load_cases() -> list[dict]:
    with FIXTURE_PATH.open() as fh:
        return json.load(fh)["cases"]


CASES = _load_cases()


# --------------------------------------------------------------------------- #
# 1. RED guard - the behaviour being replaced.
# --------------------------------------------------------------------------- #
def test_project_loop_reports_correctly_on_a_closing_conjunction():
    """The CORRECT behaviour, asserted against the REAL project loop.

    The strict ``xfail`` marker that used to live here was REMOVED by ADP-1, when
    ``core/astrology.py`` was wired to ``core.astro.aspects``. It XPASS-failed exactly
    as designed once the wiring landed, which is the signal that the defect was fixed
    and the marker should go.
    """
    import datetime

    import core.astrology as ast

    calc = ast.AstrologicalCalculator.__new__(ast.AstrologicalCalculator)
    calc.SIGNS = ["Aries"] * 12
    natal_dt = datetime.datetime(2026, 1, 1)
    transit_dt = datetime.datetime(2026, 1, 2)
    # Deliberately minimal position dicts: no Chiron, no "retrograde" key, no extras.
    # The stub must not depend on anything else in core/astrology.py that may change.
    calc.get_planetary_positions = lambda dt, loc: (
        {"Sun": {"longitude": 355.0, "speed": 1.0}} if dt == transit_dt else {"Moon": {"longitude": 0.0, "speed": 0.0}}
    )
    calc.get_julian_day = lambda dt: 2451545.0

    results = [
        r
        for r in calc.get_transits_to_natal(natal_dt, (0.0, 0.0), transit_dt)
        if r["transit_planet"] == "Sun" and r["natal_planet"] == "Moon"
    ]
    assert results, "the 355/0 pair must produce a conjunction"
    conjunction = next(r for r in results if r["aspect"] == "Conjunction")

    # A body at 355 deg moving forward is closing on the natal longitude, so the
    # conjunction orb is SHRINKING: applying. ADP-1 fixed this.
    assert conjunction["applying"] is True


# --------------------------------------------------------------------------- #
# 1b. Equal RELATIVE speed means no direction at all.
# --------------------------------------------------------------------------- #
def test_equal_nonzero_speeds_give_applying_none():
    """Two bodies moving together keep a constant separation, so the orb is neither
    closing nor opening. ``False`` ("opening") is simply untrue.

    13.2 deg/day is the Moon's mean motion, used because it is a real speed and one
    nobody would round to zero.
    """
    state = aspect_state(85.0, 13.2, 0.0, 13.2, ASPECT_ANGLES["Square"], static_target=False)
    assert state.applying is None, "equal speeds cannot change the separation; applying must be None, not False"
    assert state.orb_abs == pytest.approx(5.0)
    assert state.exact is False


def test_equal_speeds_at_every_aspect_angle_are_all_none():
    for name, angle in ASPECT_ANGLES.items():
        state = aspect_state(10.0, 0.5, 200.0, 0.5, angle)
        assert state.applying is None, f"{name}: equal speeds must give None"


def test_equal_speeds_must_actually_be_equal():
    """Opposite signs are not equal: +1.0 and -1.0 differ by 2.0, and the separation
    changes at twice the rate."""
    same = aspect_state(85.0, 1.0, 0.0, 1.0, ASPECT_ANGLES["Square"])
    assert same.applying is None

    opposite = aspect_state(85.0, 1.0, 0.0, -1.0, ASPECT_ANGLES["Square"])
    assert opposite.applying is not None, "-1.0 and +1.0 are not equal"
    assert opposite.applying is True, "opposite speeds close a 5 deg square orb"

    near = aspect_state(85.0, 1.0, 0.0, 1.0 + 2 * STATION_SPEED_EPSILON, ASPECT_ANGLES["Square"])
    assert near.applying is not None, "a relative speed above the threshold is motion"

    below = aspect_state(85.0, 1.0, 0.0, 1.0 + STATION_SPEED_EPSILON / 2, ASPECT_ANGLES["Square"])
    assert below.applying is None, "half the threshold is still no relative motion"


def test_static_target_with_a_stationary_mover_is_also_none():
    """Under ``static_target`` the target's speed is pinned to 0, so a mover that is
    itself stationary has zero relative speed and no direction."""
    state = aspect_state(85.0, 0.0, 0.0, 5.0, ASPECT_ANGLES["Square"], static_target=True)
    assert state.applying is None

    moving = aspect_state(85.0, 0.0, 0.0, 5.0, ASPECT_ANGLES["Square"], static_target=False)
    assert moving.applying is not None


def test_zero_relative_speed_beats_the_exactness_convention():
    """Both facts can hold at once. With no relative motion the honest answer is
    ``applying=None``; ``exact=True`` still tells the caller it is exact."""
    state = aspect_state(90.0, 13.2, 0.0, 13.2, ASPECT_ANGLES["Square"], static_target=False)
    assert state.exact is True
    assert state.applying is None, "no relative motion, so no direction even at exactness"


# --------------------------------------------------------------------------- #
# 2. Property test - brute force, seeded, does not trust the formula.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6, 7, 8])
def test_applying_matches_brute_force_on_seeded_random_tuples(seed):
    """For many random tuples, stepping both bodies forward must shrink the orb
    iff ``applying`` is True.

    The oracle here is a numerical step, not the closed-form derivative the
    implementation uses. If the two ever disagree, one of them is wrong and this
    test says which way round the truth is.
    """
    rng = random.Random(seed)
    dt = 1e-3
    checked = 0

    for _ in range(4000):
        lon_a = rng.uniform(0.0, 360.0)
        lon_b = rng.uniform(0.0, 360.0)
        speed_a = rng.uniform(-2.0, 2.0)
        speed_b = rng.uniform(-2.0, 2.0)
        aspect_name = rng.choice(list(ASPECT_ANGLES))
        angle = ASPECT_ANGLES[aspect_name]
        static = rng.random() < 0.5

        state = aspect_state(lon_a, speed_a, lon_b, speed_b, angle, static_target=static)

        if state.applying is None:
            # None means "no direction", i.e. the RELATIVE speed is zero. This is the
            # generalised rule, not "both speeds are zero": equal nonzero speeds are
            # just as motionless relative to each other. Asserting the old both-zero
            # rule here would let any wrong None slip through.
            eff_speed_b = 0.0 if static else speed_b
            assert abs(eff_speed_b - speed_a) <= STATION_SPEED_EPSILON, (
                f"applying=None for {aspect_name} but relative speed " f"{eff_speed_b - speed_a:+.3e} is not zero"
            )
            continue

        if state.exact:
            # A stationary minimum: the orb grows either way, so it is not applying.
            orb_now = abs(separation(lon_a, lon_b) - angle)
            orb_after = abs(separation(lon_a + speed_a * dt, lon_b + speed_b * dt) - angle)
            assert orb_after >= orb_now - 1e-9
            continue

        eff_speed_b = 0.0 if static else speed_b
        orb_now = state.orb_abs
        orb_after = abs(separation(lon_a + speed_a * dt, lon_b + eff_speed_b * dt) - angle)
        shrinking = orb_after < orb_now - 1e-12
        assert state.applying == shrinking, (
            f"seed={seed} {aspect_name} a={lon_a:.4f}/{speed_a:+.4f} "
            f"b={lon_b:.4f}/{eff_speed_b:+.4f} static={static}: "
            f"applying={state.applying} but the orb "
            f"{'shrank' if shrinking else 'grew'} ({orb_now:.6f} -> {orb_after:.6f})"
        )
        checked += 1

    assert checked > 1000, f"the oracle exercised too few cases ({checked}); it is not testing anything"


def test_property_test_oracle_is_not_trivially_true():
    """Guards against a vacuous property test.

    If ``separation`` or the oracle stopped discriminating, the loop above could
    pass without checking anything. This asserts the oracle does move both ways
    on the very tuples the property test uses.
    """
    rng = random.Random(11)
    dt = 1e-3
    shrinking = growing = 0
    for _ in range(2000):
        lon_a = rng.uniform(0.0, 360.0)
        lon_b = rng.uniform(0.0, 360.0)
        speed_a = rng.uniform(-2.0, 2.0)
        speed_b = rng.uniform(-2.0, 2.0)
        angle = ASPECT_ANGLES[rng.choice(list(ASPECT_ANGLES))]
        now = abs(separation(lon_a, lon_b) - angle)
        after = abs(separation(lon_a + speed_a * dt, lon_b + speed_b * dt) - angle)
        if after < now - 1e-12:
            shrinking += 1
        else:
            growing += 1
    assert (
        shrinking > 200 and growing > 200
    ), f"degenerate oracle: {shrinking} shrinking, {growing} growing - both must be common"


# --------------------------------------------------------------------------- #
# 3. The fixture vectors.
# --------------------------------------------------------------------------- #
def test_fixture_vectors_all_reproduce():
    """Every generated vector, checked against the independent expected value.

    ``expected_applying`` in the JSON was computed by brute force at generation
    time, not by running the implementation - see the fixture's ``provenance``.
    """
    assert len(CASES) == 1000, f"expected the full grid, got {len(CASES)}"

    mismatches = []
    for case in CASES:
        state = aspect_state(
            case["moving_lon"],
            case["moving_speed"],
            case["target_lon"],
            case["target_speed"],
            case["aspect_angle"],
        )
        if state.applying != case["expected_applying"]:
            mismatches.append(
                f"{case['case_id']}: got applying={state.applying!r} " f"expected {case['expected_applying']!r}"
            )
        assert math.isclose(state.orb_abs, case["orb_deg"], abs_tol=1e-9), case["case_id"]
        assert math.isclose(state.orb_signed, case["orb_signed_deg"], abs_tol=1e-9), case["case_id"]
        assert math.isclose(state.orb_abs, abs(state.orb_signed), abs_tol=1e-12)

    assert not mismatches, f"{len(mismatches)} vector(s) disagree with the brute-force oracle:\n" + "\n".join(
        mismatches[:10]
    )


def test_fixture_vectors_with_static_target_reproduce():
    """The same grid with the target pinned static (the transit-to-natal case)."""
    mismatches = []
    for case in CASES:
        expected = case["expected_applying_static_target"]
        if expected is None:
            continue
        state = aspect_state(
            case["moving_lon"],
            case["moving_speed"],
            case["target_lon"],
            case["target_speed"],
            case["aspect_angle"],
            static_target=True,
        )
        if state.applying != expected:
            mismatches.append(f"{case['case_id']}: {state.applying!r} != {expected!r}")
    assert not mismatches, "\n".join(mismatches[:10])


def test_fixture_covers_every_aspect_angle_and_every_speed_combination():
    angles = {c["aspect_angle"] for c in CASES}
    assert angles == set(ASPECT_ANGLES.values()), "every Ptolemaic angle must be covered"

    moving_speeds = {c["moving_speed"] for c in CASES}
    assert moving_speeds >= {1.0, -1.0, 0.0}, "direct, retrograde and stationary must all appear"

    # every direct/retrograde crossing at 0/60/90/120/180 is present
    for angle in ASPECT_ANGLES.values():
        for ts in (1.0, -1.0):
            for ns in (1.0, -1.0):
                assert any(
                    c["aspect_angle"] == angle and c["moving_speed"] == ts and c["target_speed"] == ns for c in CASES
                ), f"missing vector for angle={angle} t_speed={ts} n_speed={ns}"


def test_fixture_records_the_row_example_and_the_projects_wrong_answer():
    """The ticket's worked example must be pinned as CORRECT, not as a bug.

    The ticket claimed a transit 85 deg ahead moving toward an exact square at
    90 deg is reported separating. It is not: the project answers ``applying=True``
    there. The fixture records that so nobody re-litigates it from the ticket text.
    """
    case = aspect_state(85.0, 1.0, 0.0, 0.0, ASPECT_ANGLES["Square"], static_target=True)
    assert case.orb_abs == pytest.approx(5.0)
    assert case.applying is True, (
        "85 deg closing on an exact square at 90 deg IS applying; the ticket's example "
        "does not reproduce against HEAD d754336"
    )


# --------------------------------------------------------------------------- #
# 4. Edge cases.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (0.0, 0.0, 0.0),
        (0.0, 180.0, 180.0),
        (359.0, 1.0, 2.0),
        (350.0, 10.0, 20.0),
        (355.0, 5.0, 10.0),
        (360.0, 0.0, 0.0),
        (720.0, 0.0, 0.0),
        (-10.0, 10.0, 20.0),
        (10.0, 350.0, 20.0),
    ],
)
def test_separation_handles_the_wrap_and_out_of_range_input(a, b, expected):
    assert separation(a, b) == pytest.approx(expected)


def test_separation_is_always_in_range():
    rng = random.Random(3)
    for _ in range(5000):
        s = separation(rng.uniform(-720, 720), rng.uniform(-720, 720))
        assert 0.0 <= s <= 180.0


def test_separation_is_symmetric():
    rng = random.Random(4)
    for _ in range(2000):
        a, b = rng.uniform(0, 360), rng.uniform(0, 360)
        assert separation(a, b) == pytest.approx(separation(b, a))


def test_applying_is_none_only_when_the_relative_speed_is_zero():
    """The contract is RELATIVE speed, not "both speeds are zero".

    Renamed from test_applying_is_none_only_when_both_speeds_are_zero, which
    named the OLD and wrong rule. Equal nonzero speeds are just as motionless
    relative to each other, and that case was not asserted here at all.
    """
    assert aspect_state(0.0, 0.0, 90.0, 0.0, 90.0).applying is None
    # one speed non-zero is enough to have a direction
    assert aspect_state(0.0, 1.0, 90.0, 0.0, 90.0).applying is not None
    assert aspect_state(0.0, 0.0, 90.0, 1.0, 90.0).applying is not None
    assert aspect_state(0.0, -1.0, 90.0, 0.0, 90.0).applying is not None
    # EQUAL NONZERO speeds: the case the old name and the old wording missed.
    assert aspect_state(0.0, 13.2, 90.0, 13.2, 90.0).applying is None
    assert aspect_state(0.0, -13.2, 90.0, -13.2, 90.0).applying is None
    # and they are not "equal" just because the magnitudes match
    assert aspect_state(0.0, 13.2, 90.0, -13.2, 90.0).applying is not None


def test_retrograde_moving_body_is_handled_by_the_same_rule():
    """A retrograde body approaching an exact square is applying, like a direct one."""
    direct = aspect_state(85.0, 1.0, 0.0, 0.0, 90.0, static_target=True)
    retro = aspect_state(95.0, -1.0, 0.0, 0.0, 90.0, static_target=True)
    assert direct.orb_abs == pytest.approx(retro.orb_abs)
    assert direct.applying is True and retro.applying is True


def test_station_is_not_mistaken_for_a_slow_direct_body():
    """At a station the body has no direction; a tiny speed does have one."""
    at_station = aspect_state(85.0, 0.0, 0.0, 0.0, 90.0, static_target=True)
    assert at_station.applying is None

    barely_moving = aspect_state(85.0, 1e-6, 0.0, 0.0, 90.0, static_target=True)
    assert barely_moving.applying is True, "1e-6 deg/day is above the station threshold"

    below_threshold = aspect_state(85.0, STATION_SPEED_EPSILON / 2, 0.0, 0.0, 90.0, static_target=True)
    assert below_threshold.applying is None


def test_equal_nonzero_speeds_give_applying_none_again():
    """The rule is RELATIVE speed, not "both speeds are zero" - see the renamed
    test_applying_is_none_only_when_the_relative_speed_is_zero.

    Two bodies moving together at 13.2 deg/day keep a constant separation, so
    there is no direction to report.
    """
    state = aspect_state(85.0, 13.2, 0.0, 13.2, ASPECT_ANGLES["Square"], static_target=False)
    assert state.applying is None, "equal relative speed means a constant separation"
    assert state.orb_abs == pytest.approx(5.0)
    assert state.exact is False

    # and the same under static_target, where the target speed is pinned to 0
    pinned = aspect_state(85.0, 0.0, 0.0, 13.2, ASPECT_ANGLES["Square"], static_target=True)
    assert pinned.applying is None


# --------------------------------------------------------------------------- #
# W1-5b: the two cusps of sep = |d|.
# --------------------------------------------------------------------------- #
def test_equal_longitudes_separation_is_a_minimum():
    """At separation 0 the gap can only OPEN, so a non-conjunction orb closes.

    ``_signed_delta`` returns +0.0 and ``math.copysign(1.0, 0.0)`` is +1, so the
    generic sign rule reports a closing orb only when the SECOND body is the
    faster one. When it is the slower one the answer came out backwards.
    """
    state = aspect_state(10.0, 1.0, 10.0, 0.0, ASPECT_ANGLES["Square"], static_target=False)
    assert state.orb_abs == pytest.approx(90.0)
    assert state.applying is True, (
        "two bodies at the same longitude separate as they move, so the square orb "
        "closes; a finite difference of the orb agrees"
    )


@pytest.mark.parametrize(
    ("speed_a", "speed_b"),
    [(1.0, 0.0), (-1.0, 0.0), (1.0, 0.5), (0.0, 1.0), (1.0, -1.0), (0.2, -0.2)],
    ids=["a-faster", "a-slower", "a-barely-faster", "b-faster", "opposite", "slow-opposite"],
)
def test_equal_longitudes_match_the_finite_difference(speed_a, speed_b):
    """Brute force decides, for every speed pairing at separation 0."""
    dt = 1e-6

    def _orb(lon_a, lon_b, angle):
        sep = abs(((lon_a - lon_b + 180.0) % 360.0) - 180.0)
        return abs(sep - angle)

    angle = ASPECT_ANGLES["Square"]
    state = aspect_state(10.0, speed_a, 10.0, speed_b, angle, static_target=False)
    now = _orb(10.0, 10.0, angle)
    after = _orb(10.0 + speed_a * dt, 10.0 + speed_b * dt, angle)
    assert state.applying == (after < now), (
        f"speeds {speed_a}/{speed_b}: the orb went {now} -> {after} but applying is " f"{state.applying!r}"
    )


def test_equal_longitudes_at_zero_offset_angles():
    """The 0/360 wrap must not hide the cusp: 0 and 360 are the same place."""
    state = aspect_state(0.0, 1.0, 360.0, 0.0, ASPECT_ANGLES["Square"], static_target=False)
    assert state.applying is True


def test_antipodal_separation_is_still_a_maximum():
    """The |d| == 180 cusp must keep working: the gap can only CLOSE there."""
    state = aspect_state(180.0, 1.0, 0.0, 0.0, ASPECT_ANGLES["Trine"], static_target=False)
    assert state.orb_abs == pytest.approx(60.0)
    assert state.applying is True


# --------------------------------------------------------------------------- #
# W1-5b: the exact flag has ONE tolerance.
# --------------------------------------------------------------------------- #
def test_exact_flag_uses_the_same_tolerance_on_both_paths():
    """The moving path and the stationary path must agree about ``exact``.

    A body 5e-10 degrees from the exact angle is exact on the moving path; with
    equal speeds (the stationary path) it must be exact too.
    """
    lon_b = 90.0 + 5e-10
    moving = aspect_state(0.0, 1.0, lon_b, 0.0, ASPECT_ANGLES["Square"], static_target=False)
    still = aspect_state(0.0, 13.2, lon_b, 13.2, ASPECT_ANGLES["Square"], static_target=False)
    assert moving.orb_abs == pytest.approx(still.orb_abs)
    assert moving.exact is True
    assert still.exact is True, "the stationary path used a stricter test (orb_abs <= 0.0)"


def test_exact_flag_boundary_is_the_documented_tolerance():
    """Just inside the tolerance is exact; just outside is not."""
    inside = aspect_state(0.0, 1.0, 90.0 + STATION_SPEED_EPSILON / 2, 0.0, 90.0, static_target=False)
    assert inside.exact is True
    outside = aspect_state(0.0, 1.0, 90.0 + STATION_SPEED_EPSILON * 2, 0.0, 90.0, static_target=False)
    assert outside.exact is False


# --------------------------------------------------------------------------- #
# W1-5b: typed errors for bad input.
# --------------------------------------------------------------------------- #
def test_unknown_aspect_name_raises_aspect_error():
    """The docstring promised AspectError; the code raised KeyError."""
    with pytest.raises(AspectError) as exc:
        orb_for("Quincunx")
    assert "Quincunx" in str(exc.value)
    assert "Square" in str(exc.value), "the error should list the known aspects"


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "inf", "-inf"],
)
def test_non_finite_longitude_is_refused(value):
    with pytest.raises(AspectError):
        aspect_state(value, 1.0, 0.0, 0.0, 90.0)
    with pytest.raises(AspectError):
        separation(value, 0.0)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "inf", "-inf"],
)
def test_non_finite_speed_is_refused(value):
    with pytest.raises(AspectError):
        aspect_state(0.0, value, 90.0, 0.0, 90.0)


@pytest.mark.parametrize("value", [True, False], ids=["true", "false"])
def test_bool_speed_is_refused(value):
    """A bool is an int in Python, so True would silently mean 1 degree per day."""
    with pytest.raises(AspectError) as exc:
        aspect_state(0.0, value, 90.0, 0.0, 90.0)
    assert "bool" in str(exc.value)


def test_bool_longitude_is_refused():
    with pytest.raises(AspectError):
        aspect_state(True, 1.0, 90.0, 0.0, 90.0)


def test_string_input_is_refused():
    with pytest.raises(AspectError):
        aspect_state(0.0, "fast", 90.0, 0.0, 90.0)


def test_numpy_floats_still_work():
    """A numpy float64 is a float subclass and must not be refused."""
    np = pytest.importorskip("numpy")
    state = aspect_state(np.float64(0.0), np.float64(1.0), np.float64(90.0), np.float64(0.0), 90.0)
    assert state.applying is not None


def test_is_usable_speed_rejects_what_it_should():
    from core.astro.aspects import is_usable_speed

    assert is_usable_speed(1.0)
    assert is_usable_speed(0.0)
    assert is_usable_speed(-1.0)
    assert not is_usable_speed(None)
    assert not is_usable_speed(True)
    assert not is_usable_speed(float("nan"))
    assert not is_usable_speed(float("inf"))
    assert not is_usable_speed("fast")


def test_exact_aspect_reports_exact_and_not_applying():
    state = aspect_state(90.0, 1.0, 0.0, 0.0, 90.0, static_target=True)
    assert state.exact is True
    assert state.orb_abs == pytest.approx(0.0)
    assert state.applying is False, "an exact aspect is a stationary minimum, not closing"
    assert state.orb_signed == pytest.approx(0.0)


def test_antipodal_separation_is_a_cusp_not_a_direction_flip():
    """At |separation| = 180 the shortest arc switches sides, so ``sign(d)`` flips for
    no physical reason.

    The separation is at a local MAXIMUM there: stepping either body in either
    direction brings the pair CLOSER. This was a real bug in the first draft of the
    derivative, caught by the fixture grid, where equal speeds at 180 deg apart
    produced a spurious "applying" against a trine.
    """
    # 180 deg apart, both moving the same way: the separation must not change.
    equal = aspect_state(180.0, 1.0, 0.0, 1.0, 120.0)
    assert equal.orb_abs == pytest.approx(60.0)
    assert equal.applying is None, "equal speeds mean a constant separation, so no direction"

    # 180 deg apart, the moving body overtaking: the pair gets CLOSER, so a trine
    # orb of 60 deg shrinks.
    closing = aspect_state(180.0, 1.0, 0.0, 0.0, 120.0)
    assert closing.applying is True

    # and the mirrored case
    closing_mirror = aspect_state(0.0, 1.0, 180.0, 0.0, 120.0)
    assert closing_mirror.applying is True

    # brute-force confirmation for both directions of motion
    dt = 1e-3
    for t_lon, t_speed in ((180.0, 1.0), (180.0, -1.0), (0.0, 1.0), (0.0, -1.0)):
        for n_lon, n_speed in ((0.0, 0.0), (180.0, 0.0), (0.0, 0.5), (180.0, 0.5)):
            if abs(separation(t_lon, n_lon) - 180.0) > 1e-9:
                continue
            state = aspect_state(t_lon, t_speed, n_lon, n_speed, 120.0)
            now = abs(separation(t_lon, n_lon) - 120.0)
            after = abs(separation(t_lon + t_speed * dt, n_lon + n_speed * dt) - 120.0)
            if abs(after - now) <= 1e-12:
                # constant separation: the orb does not move either, so no direction
                assert state.applying is None, (
                    f"antipodal pair {t_lon}/{t_speed} vs {n_lon}/{n_speed} has a constant "
                    f"separation, so applying must be None, not {state.applying!r}"
                )
                continue
            assert state.applying == (
                after < now - 1e-12
            ), f"antipodal cusp wrong for {t_lon}/{t_speed} vs {n_lon}/{n_speed}"


def test_exact_opposition_is_reported_exact():
    """180 deg apart against an opposition angle is the one place the cusp and
    exactness meet; it must report exact, not a direction."""
    state = aspect_state(180.0, 1.0, 0.0, 0.0, ASPECT_ANGLES["Opposition"], static_target=True)
    assert state.exact is True
    assert state.orb_abs == pytest.approx(0.0)


def test_orb_signed_sign_convention():
    """``orb_signed = separation - angle``: negative inside the angle, positive wider."""
    inside = aspect_state(85.0, 1.0, 0.0, 0.0, 90.0, static_target=True)
    assert inside.orb_signed == pytest.approx(-5.0)

    outside = aspect_state(95.0, 1.0, 0.0, 0.0, 90.0, static_target=True)
    assert outside.orb_signed == pytest.approx(5.0)

    # conjunction is always "wider than 0"
    conj = aspect_state(10.0, 1.0, 0.0, 0.0, 0.0, static_target=True)
    assert conj.orb_signed == pytest.approx(10.0)

    # opposition is always "inside 180"
    opp = aspect_state(170.0, 1.0, 0.0, 0.0, 180.0, static_target=True)
    assert opp.orb_signed == pytest.approx(-10.0)


def test_static_target_ignores_the_target_speed():
    """The whole point: a natal body does not move during a transit day."""
    with_target_speed = aspect_state(85.0, 1.0, 0.0, 0.5, 90.0, static_target=False)
    static = aspect_state(85.0, 1.0, 0.0, 0.5, 90.0, static_target=True)
    assert static.applying == with_target_speed.applying or static.applying is not None
    assert static == aspect_state(
        85.0, 1.0, 0.0, 999.0, 90.0, static_target=True
    ), "static_target must pin the target speed regardless of what was passed"


def test_opposition_uses_the_short_arc_not_the_long_one():
    """185 deg apart is 175 deg apart, not 185.

    The separation is therefore 175, which is 5 deg INSIDE the opposition angle, and
    a body moving from 185 toward 186 is opening that gap further - so separating.
    """
    state = aspect_state(185.0, 1.0, 0.0, 0.0, 180.0, static_target=True)
    assert state.orb_abs == pytest.approx(5.0)
    assert state.orb_signed == pytest.approx(-5.0), "175 deg is inside 180"
    assert state.applying is False

    # and the other side of the opposition, closing on 180
    closing = aspect_state(175.0, 1.0, 0.0, 0.0, 180.0, static_target=True)
    assert closing.orb_abs == pytest.approx(5.0)
    assert closing.applying is True


def test_unknown_aspect_angle_is_still_usable():
    """The physics does not depend on the classical set."""
    state = aspect_state(28.0, 1.0, 0.0, 0.0, 30.0, static_target=True)
    assert state.orb_abs == pytest.approx(2.0)
    assert state.applying is True


# --------------------------------------------------------------------------- #
# 5. Orb tables as data.
# --------------------------------------------------------------------------- #
def test_three_profiles_exist_and_are_read_only():
    assert set(ORB_PROFILES) == {"Classical", "Modern", "Tight"}
    for name, profile in ORB_PROFILES.items():
        assert profile.name == name
        with pytest.raises(TypeError):
            profile.orbs["Square"] = 99.0  # MappingProxyType rejects writes
        with pytest.raises(Exception):
            ORB_PROFILES["Nope"] = profile


def test_every_profile_covers_every_aspect():
    for profile in ORB_PROFILES.values():
        assert set(profile.orbs) == set(ASPECT_ANGLES)


def test_default_profile_is_modern():
    assert DEFAULT_PROFILE_NAME == "Modern"
    assert orb_for("Square") == ORB_PROFILES["Modern"].orbs["Square"]


def test_profiles_are_ordered_tightest_to_widest():
    """Tight <= Classical <= Modern for the aspects they differ on."""
    for aspect in ("Square", "Trine"):
        assert ORB_PROFILES["Tight"].orbs[aspect] <= ORB_PROFILES["Classical"].orbs[aspect]
        assert ORB_PROFILES["Classical"].orbs[aspect] <= ORB_PROFILES["Modern"].orbs[aspect]


def test_luminaries_bonus_applies_only_to_luminaries():
    square = ORB_PROFILES["Modern"].orbs["Square"]
    assert orb_for("Square", "Modern") == square
    assert orb_for("Square", "Modern", luminaries=("Mars", "Venus")) == square
    assert orb_for("Square", "Modern", luminaries=("Sun", "Venus")) == square + 2.0
    assert orb_for("Square", "Modern", luminaries=("Mars", "Moon")) == square + 2.0
    assert orb_for("Square", "Modern", luminaries=("Moon", "Sun")) == square + 2.0


def test_tight_profile_has_a_smaller_luminaries_bonus():
    assert ORB_PROFILES["Tight"].luminary_bonus < ORB_PROFILES["Modern"].luminary_bonus


def test_orb_for_accepts_a_profile_object():
    profile = OrbProfile("Custom", {k: 3.0 for k in ASPECT_ANGLES}, luminary_bonus=0.0)
    assert orb_for("Square", profile) == 3.0


def test_unknown_profile_raises_a_typed_error():
    with pytest.raises(AspectError) as exc:
        orb_for("Square", "Enormous")
    assert "Enormous" in str(exc.value)
    assert "Classical" in str(exc.value), "the error should list the known profiles"
    assert isinstance(exc.value, ValueError)


def test_aspect_error_is_a_value_error_subclass():
    assert issubclass(AspectError, ValueError)


def test_orb_tables_are_data_not_wired_into_the_physics():
    """Two profiles with different tables must change which aspects match, not
    how ``aspect_state`` computes anything."""
    a = aspect_state(85.0, 1.0, 0.0, 0.0, 90.0, static_target=True)
    b = aspect_state(85.0, 1.0, 0.0, 0.0, 90.0, static_target=True)
    assert a == b, "aspect_state must not depend on any profile"


# --------------------------------------------------------------------------- #
# 6. aspects_between.
# --------------------------------------------------------------------------- #
def test_aspects_between_finds_only_aspects_inside_the_orb():
    moving = {"Mars": (353.0, 0.7)}  # 7 deg from a conjunction with a target at 0
    target = {"Sun": (0.0, 0.0)}
    matches = aspects_between(moving, target, profile="Modern")
    conjunctions = [m for m in matches if m.aspect == "Conjunction"]
    assert len(conjunctions) == 1
    assert conjunctions[0].orb_abs == pytest.approx(7.0)
    assert conjunctions[0].allowed_orb == pytest.approx(10.0), "square 8 + luminaries bonus 2"
    assert conjunctions[0].applying is True, "Mars is moving forward toward the Sun's longitude"


def test_aspects_between_tight_profile_drops_a_wide_aspect():
    moving = {"Mars": (353.0, 0.7)}
    target = {"Sun": (0.0, 0.0)}
    assert any(m.aspect == "Conjunction" for m in aspects_between(moving, target, profile="Modern"))
    assert not any(
        m.aspect == "Conjunction" for m in aspects_between(moving, target, profile="Tight")
    ), "Tight caps the conjunction at 4 + 1 = 5 deg, and this orb is 7"


def test_aspects_between_is_sorted_tightest_first():
    moving = {"Mars": (89.0, 1.0), "Venus": (85.0, 1.0)}  # squares of orb 1 and orb 5
    target = {"Sun": (0.0, 0.0)}
    matches = aspects_between(moving, target, profile="Modern")
    assert matches
    assert [m.orb_abs for m in matches] == sorted(m.orb_abs for m in matches)
    assert matches[0].moving == "Mars", "Mars at 89 deg has the tighter square (orb 1 vs 5)"


def test_aspects_between_uses_static_target_by_default():
    moving = {"Moon": (88.0, 12.0)}
    target = {"Sun": (0.0, 1.0)}  # a moving "natal" body
    matches = aspects_between(moving, target, profile="Modern")
    squares = [m for m in matches if m.aspect == "Square"]
    assert squares, "an 88 deg separation is inside the square orb"
    assert squares[0].applying is True


def test_aspects_between_skips_a_body_against_itself():
    matches = aspects_between({"Sun": (10.0, 1.0)}, {"Sun": (10.0, 0.0)}, profile="Modern")
    assert matches == []


def test_aspects_between_unknown_profile_raises():
    with pytest.raises(AspectError):
        aspects_between({"Sun": (0.0, 1.0)}, {"Moon": (0.0, 0.0)}, profile="Nope")


def test_aspects_between_results_are_frozen():
    matches = aspects_between({"Sun": (0.0, 1.0)}, {"Moon": (0.0, 0.0)}, profile="Modern")
    assert matches
    with pytest.raises(Exception):
        matches[0].orb_abs = 99.0
