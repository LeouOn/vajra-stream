"""Applying/separating aspect physics with configurable orb tables.

Pure module. No import-time side effects, no module-level mutable state, no
database, no ephemeris access, no network.

WHY THIS EXISTS
---------------
Wave W0 (``docs/notes/w0-astrology-audit-accuracy.md``) and a re-verification at
HEAD ``d754336`` both found that ``core/astrology.py`` decides applying vs
separating with::

    signed_delta = _angular_delta_signed(t_lon, n_lon)   # offset from the CONJUNCTION
    d_sep_dt = t_speed - n_speed
    applying = d_sep_dt < 0 if signed_delta >= 0 else d_sep_dt > 0

That is wrong in two independent ways.

1. **It measures from the conjunction, not from the aspect angle.** The sign of
   ``signed_delta`` says which side of 0 deg the pair is on, not which side of
   the aspect angle it is on. Measured against a brute-force "step both bodies
   forward and see whether the orb shrinks" oracle, the current code gets 10 of
   20 (aspect angle x offset x direction) cases wrong. See ``TEST VECTORS`` in
   ``tests/fixtures/astro_aspect_cases.json``.

   The error is not "right only for conjunctions". Measured over the five
   Ptolemaic angles at +/-5 deg from exact, with a static target:

   ==========  =========================  =========================
   Aspect      correct when               correct when
   ==========  =========================  =========================
   Conjunction NEVER (0/4)                (the branch always inverts)
   Sextile     5 deg short of exact       5 deg PAST exact -> wrong
   Square      5 deg short of exact       5 deg PAST exact -> wrong
   Trine       5 deg short of exact       5 deg PAST exact -> wrong
   Opposition  always (4/4)               the wrap works out
   ==========  =========================  =========================

   So the ticket's premise ("only right for conjunctions") is inverted, and its
   worked example (transit 85 deg ahead moving toward an exact square at 90 deg)
   does NOT reproduce: the current code answers ``applying=True`` there, which
   is correct. The defect is real; the description of it is not. Both facts are
   recorded in ``tests/fixtures/astro_aspect_cases.json`` under ``w0_findings``.

2. **It subtracts the natal body's birth-time speed.** A natal planet does not
   move during a transit day - it is effectively static - yet the code computes
   ``t_speed - n_speed``. ``aspect_state(..., static_target=True)`` forces the
   target's speed to zero instead.

THE RULE ENFORCED HERE
----------------------
Let ``d`` be the signed shortest longitude difference from A to B in
``[-180, 180]`` and ``sep = |d|``. Over a small ``dt`` (no wrap can occur
because ``|d| < 180`` by construction)::

    d(sep)/dt    = sign(d) * (speed_b - speed_a)
    d(orb)/dt    = sign(sep - angle) * d(sep)/dt
    applying     <=> d(orb)/dt < 0

At exactness ``sep == angle`` the orb is at a stationary minimum, so
``applying is False`` and ``exact is True``; the consumer can tell the two cases
apart with the ``exact`` flag. This is the convention the brute-force property
test in ``tests/unit/test_astro_aspects.py`` pins down.

WHEN ``applying`` IS ``None``
-----------------------------
When the RELATIVE speed ``speed_b - speed_a`` is within
:data:`STATION_SPEED_EPSILON` of zero the separation is constant, the orb is
constant, and there is no direction to report. ``None`` is the honest answer;
``False`` ("opening") would be false. This generalises the obvious both-zero case:

* both speeds zero -> relative speed zero -> ``None``;
* both speeds 13.2 deg/day -> relative speed zero -> ``None``;
* ``static_target`` with a stationary mover -> relative speed zero -> ``None``;
* speeds +1.0 and -1.0 -> relative speed -2.0 -> a real direction, not ``None``.

That check runs BEFORE the exactness check, so a pair which is both exact and
relatively motionless reports ``applying=None, exact=True``: no motion is a
stronger statement than "not closing".

TOLERANCES
----------
:data:`STATION_SPEED_EPSILON` (1e-9) serves two independent purposes, and both are
absolute constants, NOT derived from either body's speed:

* as a SPEED threshold, to decide whether there is a direction at all;
* as an ANGLE threshold on ``orb_abs``, to set ``exact``.

The angular use means ``exact`` means "within 1e-9 degrees of the angle", which
for the fastest body in the system is far finer than any ephemeris is accurate to.
It is a floating-point identity test, not a physical one.

NEEDS-LEARNER-DECISION
----------------------
Everything in :data:`ORB_PROFILES` and :data:`DEFAULT_PROFILE_NAME` is
PROVISIONAL and needs a maintainer decision. The values are exposed as swappable
data, never hardcoded into the physics, so changing them is a one-line data
edit and not a logic change.

* ``DEFAULT_PROFILE_NAME`` is **"Modern"**. Provisional.
* The **luminaries bonus is +2 deg** for Sun and Moon. Provisional.
* The three profile values themselves are provisional.
* ``_DEFAULT_PROFILE_NAME`` and the bonus are the only defaults; a caller who
  disagrees passes ``profile=``.

PUBLIC API
----------
* :func:`separation` -- shortest angular distance, in ``[0, 180]``.
* :func:`aspect_state` -- orb and applying/separating for one pair.
* :func:`orb_for` -- allowed orb for an aspect under a profile.
* :func:`aspects_between` -- all matching aspects between two longitude sets.
* :data:`ORB_PROFILES`, :data:`ASPECT_ANGLES`, :data:`DEFAULT_PROFILE_NAME`.
* :class:`AspectError`, :class:`AspectState`, :class:`AspectMatch`,
  :class:`OrbProfile`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

__all__ = [
    "ASPECT_ANGLES",
    "DEFAULT_PROFILE_NAME",
    "LUMINARIES",
    "ORB_PROFILES",
    "STATION_SPEED_EPSILON",
    "AspectError",
    "AspectMatch",
    "AspectState",
    "OrbProfile",
    "aspect_state",
    "aspects_between",
    "orb_for",
    "separation",
]


class AspectError(ValueError):
    """Raised for an unknown aspect name or an unknown orb profile.

    Subclasses :class:`ValueError` so existing ``except ValueError`` handlers in
    callers keep working.
    """


#: The five Ptolemaic angles, in degrees. Classical scope is PROVISIONAL: a
#: maintainer decision may add the Quintile (30) or the Semisextile (150).
ASPECT_ANGLES: Mapping[str, float] = MappingProxyType(
    {
        "Conjunction": 0.0,
        "Sextile": 60.0,
        "Square": 90.0,
        "Trine": 120.0,
        "Opposition": 180.0,
    }
)

#: Bodies granted the luminaries bonus. PROVISIONAL, needs a maintainer decision.
LUMINARIES: frozenset[str] = frozenset({"Sun", "Moon"})

#: Speeds at or below this magnitude (deg/day) are treated as stationary.
#: Mercury and the Moon genuinely stop at stations; the Moon turns a station
#: around in well under a day, so this is a physics threshold, not a rounding
#: convenience. PROVISIONAL.
STATION_SPEED_EPSILON: float = 1e-9


@dataclass(frozen=True)
class OrbProfile:
    """Allowed orb in degrees per aspect name, plus a luminaries bonus.

    Attributes
    ----------
    name:
        Selectable profile name.
    orbs:
        Read-only mapping of aspect name to allowed orb in degrees.
    luminary_bonus:
        Degrees added to ``orbs`` when either body is a luminary.
    """

    name: str
    orbs: Mapping[str, float]
    luminary_bonus: float = 0.0


def _profile(name: str, orbs: dict[str, float], bonus: float) -> OrbProfile:
    for aspect_name in orbs:
        if aspect_name not in ASPECT_ANGLES:
            raise AspectError(f"unknown aspect name in orb table: {aspect_name!r}")
    return OrbProfile(name=name, orbs=MappingProxyType(dict(orbs)), luminary_bonus=bonus)


# PROVISIONAL orb tables - every number here needs a maintainer decision. They are
# DATA, deliberately, so that changing them never touches the physics below.
# Built straight into the proxy: no module-level mutable dict is left behind.
ORB_PROFILES: Mapping[str, OrbProfile] = MappingProxyType(
    {
        # Ptolemaic set: squares and trines held tighter than modern practice, which
        # is the traditional reading of the five classical "pavings".
        "Classical": _profile(
            "Classical",
            {"Conjunction": 8.0, "Sextile": 6.0, "Square": 6.0, "Trine": 6.0, "Opposition": 8.0},
            bonus=2.0,
        ),
        # Wider squares and trines; the set most modern software defaults to.
        "Modern": _profile(
            "Modern",
            {"Conjunction": 8.0, "Sextile": 6.0, "Square": 8.0, "Trine": 8.0, "Opposition": 8.0},
            bonus=2.0,
        ),
        # Deliberately tight, for callers who want only close aspects.
        "Tight": _profile(
            "Tight",
            {"Conjunction": 4.0, "Sextile": 3.0, "Square": 4.0, "Trine": 4.0, "Opposition": 6.0},
            bonus=1.0,
        ),
    }
)

#: PROVISIONAL default profile. NEEDS-LEARNER-DECISION.
DEFAULT_PROFILE_NAME: str = "Modern"


@dataclass(frozen=True)
class AspectState:
    """Result of comparing one body pair against one aspect angle.

    Attributes
    ----------
    orb_signed:
        ``separation - aspect_angle``. Negative means the bodies are closer
        together than the exact angle (inside it), positive means wider. At
        exactness it is ``0.0``. For "Conjunction" it is always
        ``+separation``; for "Opposition" always ``separation - 180 <= 0``.
    orb_abs:
        ``abs(orb_signed)``, the distance from exactness in degrees.
    applying:
        ``True`` when the orb is closing, ``False`` when opening, and ``None`` when
        there is no direction to report - that is, when the RELATIVE speed
        (``speed_b - speed_a``, with ``speed_b`` pinned to 0 under ``static_target``)
        is within :data:`STATION_SPEED_EPSILON` of zero. Two bodies moving together at
        13.2 deg/day each hold a constant separation, so their orb is neither closing
        nor opening; reporting ``False`` would be false. The both-speeds-zero case is
        the special case of this. At exactness WITH relative motion the orb is at a
        stationary minimum, so ``applying`` is ``False`` and ``exact`` is ``True``.
    exact:
        ``True`` when ``orb_abs`` is within :data:`STATION_SPEED_EPSILON` of zero.
        That tolerance is an ABSOLUTE angle, deliberately not derived from either
        speed - see the module docstring.
    """

    orb_signed: float
    orb_abs: float
    applying: bool | None
    exact: bool


@dataclass(frozen=True)
class AspectMatch:
    """One aspect found between a moving body and a target body."""

    moving: str
    target: str
    aspect: str
    angle: float
    allowed_orb: float
    orb_signed: float
    orb_abs: float
    applying: bool | None
    exact: bool
    profile: str


def _normalise_lon(lon: float) -> float:
    """Fold an arbitrary longitude into ``[0, 360)``."""
    return math.fmod(lon, 360.0) % 360.0


def _check_number(value: Any, name: str) -> float:
    """Validate one numeric input and return it as a float.

    Rejects, with :class:`AspectError`:

    * ``bool`` - it is an ``int`` in Python, so ``True`` would silently mean a
      speed of 1 degree per day;
    * anything that is not a real number (a string, ``None``, an object);
    * NaN and infinity - they produce a NaN orb and a meaningless direction
      rather than an error, which is worse than refusing them.

    A ``numpy.float64`` is a ``float`` subclass and passes; a ``numpy.float32``
    passes too, because it converts to float cleanly.
    """
    if isinstance(value, bool):
        raise AspectError(
            f"{name} must be a real number, not a bool ({value!r}); "
            "a bool is an int in Python and would be read as a speed of 1"
        )
    if isinstance(value, str):
        raise AspectError(f"{name} must be a real number, not a string ({value!r})")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AspectError(f"{name} must be a real number, got {type(value).__name__}") from exc
    if not math.isfinite(number):
        raise AspectError(f"{name} must be finite, got {value!r}")
    return number


def is_usable_speed(value: Any) -> bool:
    """Whether ``value`` can be used as a longitudinal speed.

    ``False`` for ``None``, for a bool, for a non-number, and for NaN or
    infinity. Callers that receive speeds from an untrusted source use this to
    treat an unusable value as "this body has no speed" rather than as a number,
    so one bad field cannot raise through a whole chart.

    ``numpy.float64`` is a ``float`` subclass and is usable.
    """
    if value is None or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except TypeError:
        return False


def separation(a_lon: float, b_lon: float) -> float:
    """Shortest angular distance between two longitudes, in ``[0, 180]``.

    Parameters
    ----------
    a_lon, b_lon:
        Longitudes in degrees. Values outside ``[0, 360)`` are folded, so the
        0/360 wrap needs no special handling by the caller.

    Returns
    -------
    float
        The separation, always in ``[0.0, 180.0]``.

    Examples
    --------
    >>> separation(350.0, 10.0)
    20.0
    >>> separation(0.0, 180.0)
    180.0
    """
    a = _check_number(a_lon, "a_lon")
    b = _check_number(b_lon, "b_lon")
    delta = abs(a - b) % 360.0
    return min(delta, 360.0 - delta)


def _signed_delta(lon_a: float, lon_b: float) -> float:
    """Signed shortest difference ``a -> b`` in ``[-180, 180]``.

    The sign is what tells us which way the separation is growing, so this must
    be the *shortest* arc: an arc of 350 deg would make a closing pair look like
    a wildly opening one.
    """
    return (_normalise_lon(lon_b) - _normalise_lon(lon_a) + 180.0) % 360.0 - 180.0


def aspect_state(
    lon_a: float,
    speed_a: float,
    lon_b: float,
    speed_b: float,
    aspect_angle: float,
    *,
    static_target: bool = False,
) -> AspectState:
    """Orb and applying/separating for one pair of bodies at one aspect angle.

    Parameters
    ----------
    lon_a, lon_b:
        Ecliptic longitudes in degrees. Folded internally, so the 0/360 wrap is
        handled.
    speed_a, speed_b:
        Longitudinal speeds in degrees per day. Negative means retrograde.
        A magnitude at or below :data:`STATION_SPEED_EPSILON` is a station.
    aspect_angle:
        The exact angle for the aspect, in degrees. Conventionally one of
        :data:`ASPECT_ANGLES`, but any value in ``[0, 180]`` is accepted so the
        function is not tied to the classical set.
    static_target:
        When ``True``, ``speed_b`` is forced to zero. Use this for
        transit-to-natal: a natal body does not move over a transit day, and
        subtracting its birth-time speed is what made the project code wrong.

    Returns
    -------
    AspectState
        ``applying`` is ``None`` when the RELATIVE speed is zero - that is, when
        ``speed_b - speed_a`` is within :data:`STATION_SPEED_EPSILON` of zero, so
        the two bodies keep a constant separation and there is no direction to
        report. The both-speeds-zero case is the special case of this.

    Raises
    ------
    AspectError
        If any longitude, speed or the aspect angle is not a finite real
        number, or is a bool. A NaN would otherwise produce a NaN orb and a
        meaningless ``applying``.

    Notes
    -----
    The sign rule is derived, not tabulated::

        d(sep)/dt = sign(d) * (speed_b - speed_a)
        d(orb)/dt = sign(sep - angle) * d(sep)/dt
        applying  <=> d(orb)/dt < 0

    which is why a retrograde body (negative speed) is handled by the same
    expression as a direct one rather than by a special case. The two cusps of
    ``sep = |d|`` are handled explicitly, because ``sign`` is not a direction
    at either of them: see the comments in the body.
    """
    lon_a = _check_number(lon_a, "lon_a")
    lon_b = _check_number(lon_b, "lon_b")
    speed_a = _check_number(speed_a, "speed_a")
    speed_b = _check_number(speed_b, "speed_b")
    aspect_angle = _check_number(aspect_angle, "aspect_angle")
    if static_target:
        # Validated first, so a bad speed_b is refused even when it would have
        # been ignored. The override happens once, after the checks.
        speed_b = 0.0

    d = _signed_delta(lon_a, lon_b)
    sep = abs(d)
    orb_signed = sep - aspect_angle
    orb_abs = abs(orb_signed)

    # Relative speed: what actually changes the separation. Under static_target the
    # target's contribution is already zero, so this is the transit speed alone.
    relative_speed = speed_b - speed_a

    if abs(relative_speed) <= STATION_SPEED_EPSILON:
        # The two bodies keep a CONSTANT separation, so the orb is neither closing nor
        # opening. There is no direction to report, and calling that "opening" is false.
        # This generalises the both-speeds-zero case: equal nonzero speeds (13.2 and
        # 13.2 deg/day, say) are just as motionless relative to each other.
        return AspectState(
            orb_signed=orb_signed,
            orb_abs=orb_abs,
            applying=None,
            exact=orb_abs <= STATION_SPEED_EPSILON,
        )

    # d(sep)/dt, in degrees per day.
    #
    # Away from the two cusps, sep = |d| with d the signed shortest arc, so
    # d(sep)/dt = sign(d) * (speed_b - speed_a).
    #
    # At |d| == 180 the shortest-arc representation switches sides and |d| is at a
    # cusp (a local MAXIMUM): stepping d from 180 to 180+dt wraps to -(180-dt), so
    # the separation shrinks whichever way d moves. Without this branch the sign of
    # d would flip the answer for no physical reason.
    #
    # At d == 0 the separation is at a local MINIMUM: any motion opens the gap.
    # sign(0) is not a direction - math.copysign(1.0, 0.0) is +1 by convention -
    # so the generic formula would report a CLOSING orb whenever the second body
    # is the slower one, which is exactly backwards. The separation grows at
    # |relative_speed| whichever way d moves.
    if d == 0.0:
        d_sep_dt = abs(relative_speed)
    elif abs(abs(d) - 180.0) <= STATION_SPEED_EPSILON:
        d_sep_dt = -abs(relative_speed)
    else:
        d_sep_dt = math.copysign(1.0, d) * relative_speed

    if orb_abs <= STATION_SPEED_EPSILON:
        # Stationary minimum: the orb is not shrinking and not growing. Report it
        # as not applying and let the caller see `exact=True`.
        return AspectState(orb_signed=orb_signed, orb_abs=orb_abs, applying=False, exact=True)

    # d(orb)/dt = sign(orb_signed) * d(sep)/dt
    d_orb_dt = math.copysign(1.0, orb_signed) * d_sep_dt
    return AspectState(
        orb_signed=orb_signed,
        orb_abs=orb_abs,
        applying=d_orb_dt < 0.0,
        exact=False,
    )


def _resolve_profile(profile: str | OrbProfile) -> OrbProfile:
    if isinstance(profile, OrbProfile):
        return profile
    try:
        return ORB_PROFILES[profile]
    except KeyError:
        known = ", ".join(sorted(ORB_PROFILES))
        raise AspectError(f"unknown orb profile {profile!r}; known profiles: {known}") from None


def orb_for(aspect: str, profile: str | OrbProfile = DEFAULT_PROFILE_NAME, *, luminaries: Sequence[str] = ()) -> float:
    """Allowed orb in degrees for ``aspect`` under ``profile``.

    Parameters
    ----------
    aspect:
        An aspect name, e.g. ``"Square"``.
    profile:
        A profile name from :data:`ORB_PROFILES`, or an :class:`OrbProfile`.
        Defaults to :data:`DEFAULT_PROFILE_NAME`.
    luminaries:
        Names of the two bodies. If either is in :data:`LUMINARIES`, the
        profile's ``luminary_bonus`` is added.

    Returns
    -------
    float
        The allowed orb in degrees.

    Raises
    ------
    AspectError
        For an unknown aspect name or an unknown profile name.
    """
    resolved = _resolve_profile(profile)
    if aspect not in resolved.orbs:
        known = ", ".join(sorted(resolved.orbs))
        raise AspectError(f"unknown aspect name {aspect!r}; known aspects: {known}")
    if luminaries and any(name in LUMINARIES for name in luminaries):
        return resolved.orbs[aspect] + resolved.luminary_bonus
    return resolved.orbs[aspect]


def aspects_between(
    moving: Mapping[str, tuple[float, float]],
    target: Mapping[str, tuple[float, float]],
    *,
    profile: str | OrbProfile = DEFAULT_PROFILE_NAME,
    static_target: bool = True,
) -> list[AspectMatch]:
    """Every aspect between two longitude sets, under one orb profile.

    Parameters
    ----------
    moving:
        ``{body_name: (longitude_deg, speed_deg_per_day)}`` for the bodies that
        move, e.g. transits. Speeds may be negative (retrograde) or zero
        (station).
    target:
        ``{body_name: (longitude_deg, speed_deg_per_day)}`` for the fixed bodies,
        e.g. natal positions. When ``static_target`` is ``True`` (the default)
        the speed component is ignored, which is correct for natal positions.
    profile:
        A profile name from :data:`ORB_PROFILES`, or an :class:`OrbProfile`.
    static_target:
        Force every target speed to zero. Default ``True`` because that is the
        transit-to-natal case, which is what the project code got wrong.

    Returns
    -------
    list[AspectMatch]
        Sorted by ``orb_abs`` ascending, so the tightest aspects come first.
        Ties break on ``moving`` then ``target`` then ``aspect``, so the order
        is deterministic and testable.

    Raises
    ------
    AspectError
        For an unknown profile name.
    """
    resolved = _resolve_profile(profile)

    matches: list[AspectMatch] = []
    for m_name, (m_lon, m_speed) in moving.items():
        for t_name, (t_lon, t_speed) in target.items():
            if m_name == t_name:
                continue
            for aspect, angle in ASPECT_ANGLES.items():
                allowed = resolved.orbs[aspect] + (
                    resolved.luminary_bonus if (m_name in LUMINARIES or t_name in LUMINARIES) else 0.0
                )
                state = aspect_state(
                    m_lon,
                    m_speed,
                    t_lon,
                    t_speed,
                    angle,
                    static_target=static_target,
                )
                if state.orb_abs <= allowed:
                    matches.append(
                        AspectMatch(
                            moving=m_name,
                            target=t_name,
                            aspect=aspect,
                            angle=angle,
                            allowed_orb=allowed,
                            orb_signed=state.orb_signed,
                            orb_abs=state.orb_abs,
                            applying=state.applying,
                            exact=state.exact,
                            profile=resolved.name,
                        )
                    )

    matches.sort(key=lambda m: (m.orb_abs, m.moving, m.target, m.aspect))
    return matches
