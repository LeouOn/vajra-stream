"""Sun and Moon rise, set, transit and Sun twilight events (W7-2).

Pure ephemeris maths for ``GET /astrology/sky-events``: every event of the
Sun and the Moon inside the fixed window ``[at - 24 h, at + 48 h]`` at a
place, plus the ``always`` answer for a body that neither rises nor sets
there in the window (polar day/night, a circumpolar Moon). No FastAPI here;
the route in ``backend/app/api/v1/endpoints/astrology.py`` validates and
wraps.

Ephemeris: pyswisseph ``rise_trans`` on the Moshier fallback (``set_ephe_path("")``,
``FLG_MOSEPH``), the same setup ``core/celestial_sky.py`` uses — no ephemeris
files exist. Rise/set use the ``rise_trans`` DEFAULT convention (upper limb,
standard refraction); twilight uses the ``BIT_*_TWILIGHT`` flags (Sun centre at
-6/-12/-18 deg, no refraction); transit is ``CALC_MTRANSIT`` (upper
culmination). Each chain walks the window from 1 s before its start
(``_EDGE_MARGIN_DAYS``: an event stamped exactly on either edge is kept) and
restarts just after every event found (``+0.01 d``, the chaining convention
``core/astrology.py``'s sun-event engine documents), so an event is never
counted twice. ``rise_trans`` only looks about one day ahead, so when it reports
nothing the chain moves on by half a day (``_RESCAN_STEP_DAYS``) until it passes
the window end: two events more than a day apart (a high-latitude Moon) are not
lost. Events land whole-second-rounded, de-duplicated, inside the window
inclusive at the level of the rounded stamps, sorted ascending.

Honesty notes: an event that does not happen in the window is simply absent —
nothing is invented for polar cases. ``always`` is derived from the body's
TOPOCENTRIC centre altitude at ``at`` (``core.celestial_sky.topocentric_horizontal``,
the same frame ``/night-sky`` reports) compared with the same threshold the
rise/set events use (standard refraction plus the disc's semidiameter, the
Moon's from its live distance): a Moon whose centre is a little below the
geometric horizon can still be ``"up"`` because its upper edge is above the
apparent horizon — the verdict then agrees with the events beside it.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from core.celestial_sky import topocentric_horizontal

try:
    import swisseph as swe

    swe.set_ephe_path("")
except ImportError:  # pragma: no cover - environment dependent
    swe = None  # type: ignore[assignment]

#: Shown verbatim by the UI (docs/notes/earthsky/wave7/plan.md).
CONVENTION = (
    "Rise and set: upper edge of the disc at the apparent horizon, standard refraction (34 arcmin). "
    "Twilight: centre of the Sun at -6, -12 and -18 degrees, no refraction. Transit: meridian passage (upper culmination)."
)

_WINDOW_BEFORE = timedelta(hours=24)
_WINDOW_AFTER = timedelta(hours=48)
# The rise/set convention in degrees below the horizon for the body's CENTRE:
# standard refraction plus the semidiameter of the disc whose UPPER EDGE the
# events use (the Sun's is fixed at 16'; the Moon's comes from its distance).
REFRACTION_DEG = 34.0 / 60.0
SUN_SEMIDIAMETER_DEG = 16.0 / 60.0
SUN_HORIZON_DEG = REFRACTION_DEG + SUN_SEMIDIAMETER_DEG
MOON_RADIUS_KM = 1737.4
KM_PER_AU = 149_597_870.7
_CHAIN_STEP_DAYS = 0.01
# `rise_trans` only searches ~one day ahead of its start and reports "no event"
# when the next one is farther (real at high latitudes: a Moon set can lag the
# previous rise by >24 h). A not-found therefore advances the start by a step
# SHORTER than that search span and tries again, until the start itself passes
# the window end — the chain never stops early inside the window (W7-2b).
_RESCAN_STEP_DAYS = 0.5
# The chain searches ~1 s past both window edges so an event whose TRUE
# instant sits a fraction of a second outside but whose ROUNDED whole-second
# stamp equals the edge is found and kept by the inclusive filter (W7-2c).
_EDGE_MARGIN_DAYS = 1.0 / 86400.0
_MAX_PER_CHAIN = 8


class EphemerisUnavailable(RuntimeError):
    """swisseph is not importable, so no event can be computed."""


def _jd(at: datetime) -> float:
    # The same expression core.earth_sky uses, so instants agree across modules.
    return swe.julday(
        at.year,
        at.month,
        at.day,
        at.hour + at.minute / 60.0 + at.second / 3600.0 + at.microsecond / 3.6e9,
    )


def _instant_of_jd(jd: float) -> str:
    """A Julian day as a UTC ISO-8601 string with whole seconds, ending ``Z``."""
    year, month, day, hours = swe.revjul(jd)
    moment = datetime(year, month, day, tzinfo=timezone.utc) + timedelta(seconds=round(hours * 3600.0))
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _chain(body_id: int, rsmi: int, jd_start: float, jd_end: float, lon: float, lat: float) -> list[float]:
    """Every event of one kind in ``[jd_start, jd_end]``, chained forward.

    ``rise_trans`` returns the NEXT event after a time; restarting just after
    each found event (``+0.01 d``, the engine convention) walks dense event
    sequences without repeats. When it reports NO event, the next one may
    simply be more than its ~1-day search span away (not "never"): the start
    advances by ``_RESCAN_STEP_DAYS`` and the search repeats, so the whole
    window is covered however sparse the events are. A negative return right
    past the window end still ends the chain (weeks-long polar gaps terminate
    in ~6 half-day steps for this 3-day window). ``_MAX_PER_CHAIN`` guards
    against runaway loops.
    """
    found: list[float] = []
    start = jd_start
    while len(found) < _MAX_PER_CHAIN:
        result = swe.rise_trans(start, body_id, rsmi, [lon, lat, 0], flags=swe.FLG_MOSEPH)
        if result[0] < 0:
            start += _RESCAN_STEP_DAYS
            if start > jd_end:
                break
            continue
        event = result[1][0]
        if event > jd_end:
            break
        if not found or event > found[-1]:
            found.append(event)
        start = event + _CHAIN_STEP_DAYS
    return found


def _horizon_state(topo_alt_deg: float, horizon_deg: float) -> str:
    """``"up"`` when the topocentric CENTRE altitude is above the rise/set threshold.

    ``horizon_deg`` is the body's threshold as a POSITIVE depression (e.g. the
    Sun's ``34' + 16' = 0.8333`` deg): a body whose centre is a little below 0
    can still be ``"up"`` — its upper edge is above the apparent horizon,
    exactly the convention the events beside this verdict use.
    """
    return "up" if topo_alt_deg > -horizon_deg else "down"


def _topocentric_altitude_deg(body_id: int, jd: float, lat: float, lng: float) -> float:
    """The body's TOPOCENTRIC centre altitude (the `/night-sky` frame, Meeus ch. 40)."""
    position, _flags = swe.calc_ut(jd, body_id, swe.FLG_MOSEPH | swe.FLG_EQUATORIAL)
    ra, dec, distance_au = position[0], position[1], position[2]
    lst_deg = (swe.sidtime(jd) * 15.0 + lng) % 360.0
    return topocentric_horizontal(ra, dec, distance_au, lst_deg, lat)[0]


def _moon_horizon_deg(jd: float) -> float:
    """The Moon's threshold: refraction plus its semidiameter from its distance."""
    position, _flags = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH | swe.FLG_EQUATORIAL)
    distance_au = position[2]
    semidiameter = math.degrees(math.asin(MOON_RADIUS_KM / KM_PER_AU / distance_au))
    return REFRACTION_DEG + semidiameter


# (body, swe id, kind, rise_trans rsmi). Order defines nothing the caller
# sees: events are sorted by instant before returning. Empty when swisseph is
# unavailable — compute_sky_events raises before using it.
if swe is not None:
    _KINDS: tuple[tuple[str, int, str, int], ...] = (
        ("sun", swe.SUN, "rise", swe.CALC_RISE),
        ("sun", swe.SUN, "set", swe.CALC_SET),
        ("sun", swe.SUN, "transit", swe.CALC_MTRANSIT),
        ("sun", swe.SUN, "civil_dawn", swe.CALC_RISE | swe.BIT_CIVIL_TWILIGHT),
        ("sun", swe.SUN, "civil_dusk", swe.CALC_SET | swe.BIT_CIVIL_TWILIGHT),
        ("sun", swe.SUN, "nautical_dawn", swe.CALC_RISE | swe.BIT_NAUTIC_TWILIGHT),
        ("sun", swe.SUN, "nautical_dusk", swe.CALC_SET | swe.BIT_NAUTIC_TWILIGHT),
        ("sun", swe.SUN, "astronomical_dawn", swe.CALC_RISE | swe.BIT_ASTRO_TWILIGHT),
        ("sun", swe.SUN, "astronomical_dusk", swe.CALC_SET | swe.BIT_ASTRO_TWILIGHT),
        ("moon", swe.MOON, "rise", swe.CALC_RISE),
        ("moon", swe.MOON, "set", swe.CALC_SET),
        ("moon", swe.MOON, "transit", swe.CALC_MTRANSIT),
    )
else:  # pragma: no cover - environment dependent
    _KINDS = ()


def compute_sky_events(lat: float, lng: float, at: datetime) -> dict:
    """Sun and Moon events inside ``[at - 24 h, at + 48 h]`` at ``(lat, lng)``.

    ``at`` is a timezone-aware instant (naive is rejected: a window without a
    zone is meaningless); the answer is a plain dict with ``window``,
    ``observer``, ``events`` (sorted, whole seconds, ``...Z``) and ``always``.
    """
    if swe is None:
        raise EphemerisUnavailable("swisseph import failed")
    if at.tzinfo is None:
        raise ValueError("at must be timezone-aware (naive times are ambiguous)")
    at = at.astimezone(timezone.utc).replace(microsecond=0)
    window_from = at - _WINDOW_BEFORE
    window_to = at + _WINDOW_AFTER
    jd_from = _jd(window_from) - _EDGE_MARGIN_DAYS
    jd_to = _jd(window_to) + _EDGE_MARGIN_DAYS

    rows: list[tuple[datetime, str, str]] = []
    for body, body_id, kind, rsmi in _KINDS:
        for jd in _chain(body_id, rsmi, jd_from, jd_to, lng, lat):
            stamp = _instant_of_jd(jd)
            moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if window_from <= moment <= window_to:
                rows.append((moment, body, kind))

    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    seen: set[tuple[datetime, str, str]] = set()
    events: list[dict[str, str]] = []
    for moment, body, kind in rows:
        if (moment, body, kind) in seen:
            continue
        seen.add((moment, body, kind))
        events.append({"body": body, "kind": kind, "at": moment.isoformat(timespec="seconds").replace("+00:00", "Z")})

    always: dict[str, str | None] = {}
    jd_at = _jd(at)
    for body, body_id in (("sun", 0), ("moon", 1)):
        has_rise_or_set = any(e["body"] == body and e["kind"] in ("rise", "set") for e in events)
        if has_rise_or_set:
            always[body] = None
        else:
            horizon = SUN_HORIZON_DEG if body == "sun" else _moon_horizon_deg(jd_at)
            always[body] = _horizon_state(_topocentric_altitude_deg(body_id, jd_at, lat, lng), horizon)

    return {
        "window": {
            "from": window_from.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "to": window_to.isoformat(timespec="seconds").replace("+00:00", "Z"),
        },
        "observer": {"latitude": lat, "longitude": lng},
        "convention": CONVENTION,
        "events": events,
        "always": always,
    }
