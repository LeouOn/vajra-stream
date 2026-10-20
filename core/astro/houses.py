"""Configurable house systems with an explicit, reported polar fallback.

Pure wrapper over :func:`swisseph.houses_ex`. It never returns a degenerate
chart without saying so, and never raises ``swisseph.Error`` at a polar
latitude for a system that cannot be computed there.

WHY THIS EXISTS
---------------
Wave W0 (``docs/notes/w0-astrology-audit-accuracy.md`` section 6, VERIFIED)
measured three distinct failure modes, all re-verified at HEAD ``9640f99``:

1. **Raising.** ``swe.houses_ex`` raises ``swisseph.Error`` for Placidus and
   Koch at |lat| >= 66.57, in *both* hemispheres (re-measured on a 0.01 deg
   grid at lon 30 deg E, JD 2459205.0: first raise at exactly +66.57 N and
   -66.57 S; 66.56 still returns a chart). The message is the bare
   string ``swisseph.houses_ex: error`` -- no latitude, no house system, no
   hint that the polar circle is the cause. ``core.astrology.py`` calls it
   with ``b"P"`` and no guard, so a birth in Tromso or an Antarctic station
   fails with an opaque HTTP 500.
2. **Quietly degenerate.** Just below that band the call *succeeds* and the
   cusps are structurally fine, but the chart is empty: at 66.5 deg N Placidus
   gives a minimum cusp step of 2.94 deg, cramming three houses into a few
   degrees of longitude. No error, no warning, plausible-looking output. This
   is the dangerous one.
3. **Structurally broken, silently.** Campanus and Regiomontanus do not raise
   at all above ~69.65 N. They return cusps whose twelve mod-360 steps sum to
   3960 deg -- the circle wrapped eleven extra times -- so the house widths are
   meaningless and there is no signal whatsoever.

THE INVARIANT THIS MODULE ENFORCES
----------------------------------
House cusps come back from swe in *house order*, not sorted, so "cusps must
be strictly increasing" cannot be tested by comparing adjacent values. The
correct invariant is that the twelve mod-360 steps must partition the circle
exactly once::

    steps = [(cusps[(i + 1) % 12] - cusps[i]) % 360.0 for i in range(12)]

A sound chart has ``sum(steps) == 360`` and every step ``> 0``. A broken one
has ``sum(steps) == 3960`` (or any multiple) -- every individual step is still
a "positive" number, which is precisely why a naive wrapper ships nonsense.
:func:`cusp_steps` is that computation, exported so callers and tests use the
same definition.

NEEDS-LEARNER-DECISION (all provisional, all swappable)
------------------------------------------------------
None of the values in :data:`PROVISIONAL_DEFAULTS` are universal. They are a
plain data table, not module state, and each is overridable per call.

* **Default house system -- PROVISIONAL: Placidus.** Chosen only because it is
  what ``core.astrology.py`` already hardcodes, so this module changes no
  existing behaviour below the polar circle. Placidus is a modern Western
  default and is *not* the traditional default for most Indian practice;
  ``core/astrology.py`` already uses Whole Sign on its Indian path. The two
  coexisting defaults are a genuine product inconsistency, not a settled
  choice.
* **Polar fallback -- PROVISIONAL: Porphyry.** Porphyry stays structurally
  sound at every latitude tested, including +/-90. The alternative is Whole
  Sign (or Equal), which are perfectly regular everywhere but discard the
  horizon entirely: Whole Sign cusps depend only on the Ascendant's sign, so
  a fallback to it silently changes what the chart *means*. Porphyry keeps
  cusp-on-horizon structure while degrading gracefully.
* **Minimum cusp step -- PROVISIONAL: 5.0 deg.** Chosen to separate the
  measured cases with margin: 66.5 deg N Placidus measures 2.94 deg (flag
  degenerate) while Reykjavik at 64.1466 N measures 7.03 deg (use as-is). A
  threshold anywhere in (2.94, 7.03] behaves identically on every location in
  this module's tests; the exact number is a judgement call about how much a
  practitioner cares about house-width realism at high latitude.

Note the asymmetry that this forces, and which is deliberate: the minimum-step
threshold is applied to the **requested** system only. Porphyry itself bunches
to 0.21 deg at 69.65 N, so applying the same threshold to the fallback would
reject every fallback and leave a polar birth with no chart at all. A bunched
*fallback* is returned, but only with a warning saying so.

CONTRACT
--------
* Pure: imports :mod:`swisseph` only. No database, no network, no ephemeris
  download, no import-time side effects, no module-level mutable state.
* Latitude is validated to [-90, 90] and longitude to [-180, 180] with
  :class:`InvalidCoordinateError` (a ``ValueError``) before any call.
* Failures are either a typed exception or an entry in ``warnings``. There is
  no bare ``except`` and no ``except: pass``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

import swisseph as swe

__all__ = [
    "HouseCalculationError",
    "HouseResult",
    "InvalidCoordinateError",
    "InvalidCuspStepError",
    "InvalidJulianDayError",
    "PROVISIONAL_DEFAULTS",
    "SUPPORTED_SYSTEMS",
    "UnknownHouseSystemError",
    "compute_houses",
    "cusp_steps",
]

#: swisseph house-system codes. Names are the public spelling used by the API
#: surface; the bytes are what ``swe.houses_ex`` expects.
SUPPORTED_SYSTEMS: dict[str, bytes] = {
    "Placidus": b"P",
    "Koch": b"K",
    "Regiomontanus": b"R",
    "Campanus": b"C",
    "Porphyry": b"O",
    "Equal": b"E",
    "WholeSign": b"W",
}

#: PROVISIONAL defaults -- every entry is needs-learner-decision. Plain data,
#: held here so a caller can override any of them per call instead of editing
#: code. See the module docstring for why each provisional value was picked.
PROVISIONAL_DEFAULTS: dict[str, object] = {
    "default_system": "Placidus",
    "polar_fallback": "Porphyry",
    "min_cusp_step_deg": 5.0,
    "needs_learner_decision": True,
}

#: A sound chart's twelve mod-360 steps sum to exactly this.
_FULL_CIRCLE_DEG = 360.0
#: Tolerance for that sum, absorbing float round-off in swe's own arithmetic.
_CIRCLE_TOLERANCE_DEG = 1e-6


class InvalidCoordinateError(ValueError):
    """Latitude outside [-90, 90] or longitude outside [-180, 180]."""


class UnknownHouseSystemError(ValueError):
    """A house-system name that is not in :data:`SUPPORTED_SYSTEMS`."""


class HouseCalculationError(RuntimeError):
    """Neither the requested system nor the fallback could produce a chart."""


class InvalidJulianDayError(ValueError):
    """Julian day is NaN or infinite.

    Deliberately *not* a range check. ``swe.houses_ex`` needs no ephemeris
    files and happily accepts a JD of 0.0 or 1e9, so inventing a plausible
    calendar range here would reject inputs swe handles correctly. Only the
    non-finite values are rejected: with a NaN JD swe raises, and that raise
    used to be reported as a *latitude* problem.
    """


class InvalidCuspStepError(ValueError):
    """``min_cusp_step_deg`` is NaN, negative, or non-finite.

    A NaN threshold silently disables the bunching check (every comparison
    against NaN is false), which returns a degenerate 66.5 deg chart with no
    warning at all. Zero is legal and means exactly that: disable the check.
    """


@dataclass(frozen=True)
class HouseResult:
    """One computed set of house cusps, with an honest account of how it got there.

    Attributes:
        cusps: The twelve house cusps in *house order* (index 0 is the 1st
            house cusp), each a longitude in degrees in [0, 360). Not sorted.
        asc: Ascendant longitude in degrees.
        mc: Midheaven (MC) longitude in degrees.
        system_requested: The house system the caller asked for, always
            reported verbatim even when it could not be used.
        system_used: The house system actually used, which equals
            ``system_requested`` unless ``fallback_used`` is true.
        fallback_used: Whether ``system_used`` differs from ``system_requested``.
        warnings: Short human-readable notes. Non-empty whenever the chart is
            not simply the requested system, and whenever it is bunched.
    """

    cusps: tuple[float, ...]
    asc: float
    mc: float
    system_requested: str
    system_used: str
    fallback_used: bool
    warnings: list[str] = field(default_factory=list)


def cusp_steps(cusps: tuple[float, ...] | list[float]) -> list[float]:
    """Return the twelve mod-360 gaps between consecutive house cusps.

    The cusps arrive in house order and may wrap past 360 between any two
    houses, so each step is taken mod 360. Index 11 wraps back to index 0.

    For a sound chart the twelve steps are all positive and sum to 360. For a
    structurally broken chart every step is still a positive number but the
    sum is a multiple of 360 larger than 360.

    Args:
        cusps: Exactly twelve cusps in house order.

    Returns:
        Twelve gaps in degrees.

    Raises:
        ValueError: If ``cusps`` does not have exactly twelve entries.
    """
    if len(cusps) != 12:
        raise ValueError(f"expected 12 house cusps, got {len(cusps)}")
    return [(cusps[(index + 1) % 12] - cusps[index]) % _FULL_CIRCLE_DEG for index in range(12)]


def _validate_coordinates(latitude: float, longitude: float) -> None:
    """Reject out-of-range or non-finite coordinates before calling swe.

    NaN is rejected too: every comparison against NaN is false, so a naive
    range check would let it through into swe.
    """
    if not -90.0 <= latitude <= 90.0:
        raise InvalidCoordinateError(f"latitude {latitude!r} is outside the valid range [-90, 90] degrees")
    if not -180.0 <= longitude <= 180.0:
        raise InvalidCoordinateError(f"longitude {longitude!r} is outside the valid range [-180, 180] degrees")


def _resolve_system(name: str) -> bytes:
    """Map a public house-system name to its swisseph code."""
    try:
        return SUPPORTED_SYSTEMS[name]
    except KeyError:
        known = ", ".join(sorted(SUPPORTED_SYSTEMS))
        raise UnknownHouseSystemError(f"unknown house system {name!r}; supported: {known}") from None


def _fetch(julian_day: float, latitude: float, longitude: float, name: str) -> tuple[list[float], float, float]:
    """Call swe for one system.

    Raises:
        swe.Error: Propagated unchanged so the caller can distinguish a
            computational failure from a validation failure.
    """
    cusps, ascmc = swe.houses_ex(julian_day, latitude, longitude, _resolve_system(name))
    return list(cusps), float(ascmc[0]), float(ascmc[1])


def _non_finite_report(cusps: list[float], asc: float | None = None, mc: float | None = None) -> list[str]:
    """Name every non-finite output in a chart, or return [] if they are all finite.

    swe does not always raise on a Julian day it cannot handle. At JD 1e100 and
    1e300 it returns a *mixed* chart for most house systems -- some cusps
    finite, some NaN, a finite mc -- which is more dangerous than an all-NaN
    result because half of it looks plausible.
    """
    labels = [f"cusp {index + 1}" for index, cusp in enumerate(cusps) if not isfinite(cusp)]
    if asc is not None and not isfinite(asc):
        labels.append("asc")
    if mc is not None and not isfinite(mc):
        labels.append("mc")
    if not labels:
        return []
    shown = ", ".join(labels[:6])
    remainder = f" (+{len(labels) - 6} more)" if len(labels) > 6 else ""
    return [f"non-finite values in {len(labels)} output(s): {shown}{remainder}"]


def _structural_problems(cusps: list[float], asc: float | None = None, mc: float | None = None) -> list[str]:
    """Reasons this chart is unusable, independent of house widths.

    Three checks: no output may be non-finite; the twelve mod-360 steps must
    partition the circle exactly once; and every step must be strictly positive
    (a zero-width house means two cusps coincide, which happens to
    Regiomontanus at the south pole).

    The non-finite check runs first and short-circuits the rest, because every
    statistic below is meaningless against NaN: the span sums to NaN and every
    comparison against NaN is False, so a chart full of NaN used to pass all
    three checks and look perfect.
    """
    non_finite = _non_finite_report(cusps, asc, mc)
    if non_finite:
        return non_finite

    steps = cusp_steps(cusps)
    problems: list[str] = []
    span = sum(steps)
    if abs(span - _FULL_CIRCLE_DEG) > _CIRCLE_TOLERANCE_DEG:
        problems.append(f"cusps do not span 360 deg (they span {span:.2f} deg)")
    if any(step <= 0.0 for step in steps):
        narrowest = min(steps)
        problems.append(f"cusps are not strictly increasing (minimum cusp step {narrowest:.2f} deg)")
    return problems


def compute_houses(
    julian_day: float,
    latitude: float,
    longitude: float,
    *,
    system: str | None = None,
    fallback: str | None = None,
    min_cusp_step_deg: float | None = None,
) -> HouseResult:
    """Compute house cusps, falling back when the requested system cannot cope.

    The requested system is used as-is unless one of the following holds, in
    which case the configured fallback is used and the reason is recorded in
    ``warnings``:

    1. ``swe.houses_ex`` raised (Placidus and Koch at |lat| >= 66.57,
       measured on a 0.01 deg grid in both hemispheres);
    2. the cusps do not partition the circle (Campanus and Regiomontanus
       above ~69.65 N, which raise nothing at all);
    3. any cusp step is not strictly positive (Regiomontanus at -90 deg);
    4. the minimum cusp step is below ``min_cusp_step_deg`` (Placidus at
       66.5 N: 2.94 deg).

    Check 4 applies to the *requested* system only. Porphyry, the provisional
    fallback, is itself bunched to 0.21 deg at 69.65 N; applying the same
    threshold to it would reject every fallback and leave a polar birth with
    no chart. A bunched fallback is returned anyway, with a warning.

    Args:
        julian_day: UT Julian day. swe applies Delta-T internally.
        latitude: Degrees north, in [-90, 90].
        longitude: Degrees east, in [-180, 180].
        system: Requested house system, a key of :data:`SUPPORTED_SYSTEMS`.
            Defaults to ``PROVISIONAL_DEFAULTS["default_system"]``.
        fallback: House system to use when the requested one is unusable.
            Defaults to ``PROVISIONAL_DEFAULTS["polar_fallback"]``.
        min_cusp_step_deg: Bunching threshold in degrees. Defaults to
            ``PROVISIONAL_DEFAULTS["min_cusp_step_deg"]``.

    Returns:
        A frozen :class:`HouseResult`. ``system_requested`` always names what
        the caller asked for, so a caller can tell a real Placidus chart from
        a silently substituted one.

    Raises:
        InvalidCoordinateError: Latitude or longitude out of range or NaN.
        InvalidJulianDayError: ``julian_day`` is NaN or infinite. No range is
            imposed: swe.houses_ex needs no ephemeris files and accepts a wide
            span of Julian days.
        InvalidCuspStepError: ``min_cusp_step_deg`` is NaN, infinite, or
            negative. Zero is allowed and disables the bunching check.
        UnknownHouseSystemError: ``system`` or ``fallback`` not recognised.
        HouseCalculationError: There is no chart to return -- either the
            requested system raised and no distinct fallback was configured,
            or the requested system was unusable *and* the fallback could not
            produce a structurally sound chart either.
        swe.Error: swisseph raised an error that is not a houses computation
            failure.
    """
    _validate_coordinates(latitude, longitude)
    if not isfinite(julian_day):
        raise InvalidJulianDayError(
            f"julian_day {julian_day!r} is not a finite number; a NaN or infinite "
            f"Julian day makes swisseph fail for reasons unrelated to latitude"
        )

    requested = system if system is not None else str(PROVISIONAL_DEFAULTS["default_system"])
    fallback_name = fallback if fallback is not None else str(PROVISIONAL_DEFAULTS["polar_fallback"])
    threshold = (
        min_cusp_step_deg if min_cusp_step_deg is not None else float(PROVISIONAL_DEFAULTS["min_cusp_step_deg"])  # type: ignore[arg-type]
    )
    if not isfinite(threshold) or threshold < 0.0:
        raise InvalidCuspStepError(
            f"min_cusp_step_deg {threshold!r} must be a finite, non-negative number of "
            f"degrees; 0 is allowed and means 'disable the bunching check'"
        )
    # Resolve both names up front so a typo fails fast, before any swe call.
    _resolve_system(requested)
    _resolve_system(fallback_name)

    warnings: list[str] = []
    # Either a complete chart or nothing at all. Keeping this as one value
    # removes the possibility of reading cusps/asc/mc that were never bound,
    # which is what made fallback == requested blow up with UnboundLocalError
    # whenever the requested system had raised in swe.
    chart: tuple[list[float], float, float] | None = None
    swe_message: str | None = None
    try:
        chart = _fetch(julian_day, latitude, longitude, requested)
    except swe.Error as exc:
        swe_message = str(exc)

    if chart is None:
        # swe could not compute this system at this latitude at all, so there
        # is no chart to warn about -- only a chart to substitute.
        if fallback_name == requested:
            raise HouseCalculationError(
                f"{requested} cannot be computed at latitude {latitude:+.2f} deg "
                f"(swisseph raised: {swe_message}) and no distinct fallback was "
                f"configured, so there is no chart to return"
            )
        warnings.append(
            f"{requested} cannot be computed at latitude {latitude:+.2f} deg "
            f"(swisseph raised: {swe_message}); using {fallback_name} instead"
        )
    else:
        cusps, asc, mc = chart
        problems = _structural_problems(cusps, asc, mc)
        # A chart with non-finite values is not a poor chart, it is not a chart.
        # A bunched or irregular one is poor but real, and worth handing back.
        non_finite = bool(_non_finite_report(cusps, asc, mc))
        if not non_finite:
            minimum_step = min(cusp_steps(cusps))
            if minimum_step < threshold:
                problems.append(
                    f"{requested} cusps are bunched at latitude {latitude:+.2f} deg "
                    f"(minimum cusp step {minimum_step:.2f} deg < {threshold:.2f} deg)"
                )
        if not problems:
            return HouseResult(
                cusps=tuple(cusps),
                asc=asc,
                mc=mc,
                system_requested=requested,
                system_used=requested,
                fallback_used=False,
                warnings=[],
            )
        warnings.append(f"{requested} unusable at latitude {latitude:+.2f} deg: {'; '.join(problems)}")
        if non_finite and fallback_name == requested:
            # swe returned something that is not a chart, and there is no other
            # system to try. Saying so beats returning NaN longitude data.
            raise HouseCalculationError(
                f"{requested} returned non-finite values at latitude {latitude:+.2f} deg "
                f"(Julian day {julian_day:g}) and no distinct fallback was configured, "
                f"so there is no chart to return"
            )
        if not non_finite and fallback_name == requested:
            # The chart exists but is poor. Saying so and handing it back beats
            # recursing forever or pretending the chart is fine.
            warnings.append(f"no fallback is available ({requested} is both the requested system " f"and the fallback)")
            return HouseResult(
                cusps=tuple(cusps),
                asc=asc,
                mc=mc,
                system_requested=requested,
                system_used=requested,
                fallback_used=False,
                warnings=warnings,
            )

    try:
        fallback_cusps, fallback_asc, fallback_mc = _fetch(julian_day, latitude, longitude, fallback_name)
    except swe.Error as exc:
        raise HouseCalculationError(
            f"{requested} is unusable at latitude {latitude:+.2f} deg and "
            f"fallback {fallback_name} also failed: {exc}"
        ) from exc

    fallback_problems = _structural_problems(fallback_cusps, fallback_asc, fallback_mc)
    if fallback_problems:
        raise HouseCalculationError(
            f"{requested} is unusable at latitude {latitude:+.2f} deg and "
            f"fallback {fallback_name} returned a broken chart: {'; '.join(fallback_problems)}"
        )

    fallback_minimum_step = min(cusp_steps(fallback_cusps))
    if fallback_minimum_step < threshold:
        warnings.append(
            f"{fallback_name} cusps are also bunched at latitude {latitude:+.2f} deg "
            f"(minimum cusp step {fallback_minimum_step:.2f} deg < {threshold:.2f} deg); "
            f"this chart is structural but house widths are not realistic"
        )

    return HouseResult(
        cusps=tuple(fallback_cusps),
        asc=fallback_asc,
        mc=fallback_mc,
        system_requested=requested,
        system_used=fallback_name,
        fallback_used=True,
        warnings=warnings,
    )
