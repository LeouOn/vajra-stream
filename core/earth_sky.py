"""Earth & Sky wave 1 — sub-points and Greenwich apparent sidereal time.

Pure computation on top of swisseph: no I/O, no database, no network, no
global mutable state beyond the module-level ``swisseph`` import. Conventions
come from docs/notes/earthsky/wave1/contract.md:

* positions are geocentric apparent, true equator and equinox of date
  (``swe.calc_ut(jd, body, FLG_EQUATORIAL)``);
* GAST is ``swe.sidtime(jd)`` (hours) times 15, in degrees;
* a body's sub-point latitude is its declination, its longitude is
  ``wrap180(ra - gast)``;
* naive datetimes are UTC; the supported range is 1800-01-01..2200-12-31;
* degrees are rounded to 4 decimals (about 11 m);
* there are NO fallback positions: without swisseph, ``earth_state`` raises
  :class:`EphemerisUnavailable`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

SUPPORTED_YEARS = (1800, 2200)

try:  # pragma: no cover - trivial import guard
    import swisseph as swe
except ImportError as _import_error:  # pragma: no cover
    swe = None
    _IMPORT_ERROR = _import_error
else:
    _IMPORT_ERROR = None


class EphemerisUnavailable(RuntimeError):
    """swisseph could not be imported; no fallback positions exist."""


# (id, display name, swisseph planet number). Ids/names copied from
# core/celestial_sky.py PLANET_INFO (importing that module pulls in the whole
# sky renderer, so the ten constants are copied instead).
_BODIES: tuple[tuple[str, str, int], ...] = (
    ("sun", "Sun", 0),
    ("moon", "Moon", 1),
    ("mercury", "Mercury", 2),
    ("venus", "Venus", 3),
    ("mars", "Mars", 4),
    ("jupiter", "Jupiter", 5),
    ("saturn", "Saturn", 6),
    ("uranus", "Uranus", 7),
    ("neptune", "Neptune", 8),
    ("pluto", "Pluto", 9),
)

_RANGE_START = datetime(1800, 1, 1, tzinfo=timezone.utc)
_RANGE_END = datetime(2200, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def _wrap180(value: float) -> float:
    return ((value + 180.0) % 360.0) - 180.0


def _body(jd: float, gast_deg: float, body_id: str, name: str, swe_id: int) -> dict:
    (pos, _flags) = swe.calc_ut(jd, swe_id, swe.FLG_EQUATORIAL)
    ra_deg = pos[0]
    dec_deg = pos[1]
    return {
        "id": body_id,
        "name": name,
        "ra_deg": round(ra_deg, 4),
        "dec_deg": round(dec_deg, 4),
        "lat": round(dec_deg, 4),
        "lon": round(_wrap180(ra_deg - gast_deg), 4),
    }


def earth_state(at: datetime | None = None) -> dict:
    """Compute the earth-state payload for one instant.

    Args:
        at: Naive datetimes are taken as UTC; aware datetimes are converted
            to UTC; ``None`` means now (UTC).

    Returns:
        The contract payload: ``at``, ``ephemeris``, ``gast_deg``, ``sun``,
        ``moon``, ``planets`` (mercury..pluto in order). The route adds the
        ``provenance`` map via ``with_provenance``.

    Raises:
        EphemerisUnavailable: swisseph is not importable.
        ValueError: the instant is outside 1800-01-01..2200-12-31 UTC.
    """
    if swe is None:  # pragma: no cover - environment dependent
        raise EphemerisUnavailable(f"swisseph import failed: {_IMPORT_ERROR}")
    if at is None:
        at = datetime.now(timezone.utc)
    at = as_supported_utc(at, "time")
    jd = swe.julday(
        at.year,
        at.month,
        at.day,
        at.hour + at.minute / 60.0 + at.second / 3600.0 + at.microsecond / 3_600_000_000.0,
    )
    gast_deg = swe.sidtime(jd) * 15.0
    bodies = [_body(jd, gast_deg, *spec) for spec in _BODIES]
    return {
        "at": at.isoformat(),
        "ephemeris": "swisseph",
        "gast_deg": round(gast_deg, 4),
        "sun": bodies[0],
        "moon": bodies[1],
        "planets": bodies[2:],
    }


# --------------------------------------------------------------------------
# Wave 3 (W3-B): the series
# --------------------------------------------------------------------------

SERIES_MAX_SAMPLES = 288
SERIES_STEP_SECONDS = (60, 3600)


def as_supported_utc(at: datetime, label: str = "time") -> datetime:
    """The instant as an aware UTC datetime; ``ValueError`` outside the supported range.

    Naive datetimes are UTC, the same rule ``earth_state`` applies. ``label``
    names the parameter in the error text.
    """
    try:
        at = at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at.astimezone(timezone.utc)
    except OverflowError:
        # an extreme offset pushed the UTC instant past year 1 / 9999
        raise ValueError(f"{label} outside supported range 1800-01-01..2200-12-31 UTC") from None
    if not (_RANGE_START <= at <= _RANGE_END):
        raise ValueError(f"{label} outside supported range 1800-01-01..2200-12-31 UTC: {at.isoformat()}")
    return at


def format_instant(at: datetime, timespec: str = "auto") -> str:
    """An aware datetime as an ISO-8601 UTC string ending in ``Z``.

    ``timespec`` is ``datetime.isoformat``'s: ``"auto"`` drops the fraction when
    it is zero, ``"milliseconds"`` always writes three digits (truncated).
    """
    return at.astimezone(timezone.utc).isoformat(timespec=timespec).replace("+00:00", "Z")


def _julian_day(at: datetime) -> float:
    # Same expression ``earth_state`` uses, so a series sample and an
    # ``earth_state`` call for the same instant share one Julian day.
    return swe.julday(
        at.year,
        at.month,
        at.day,
        at.hour + at.minute / 60.0 + at.second / 3600.0 + at.microsecond / 3_600_000_000.0,
    )


def _series_body(jd: float, gast_deg: float, body_id: str, swe_id: int) -> dict:
    (pos, _flags) = swe.calc_ut(jd, swe_id, swe.FLG_EQUATORIAL)
    return {"id": body_id, "lat": pos[1], "lon": _wrap180(pos[0] - gast_deg)}


def earth_state_series(start: datetime, end: datetime, step_seconds: int) -> dict:
    """Sub-points of the Sun, Moon and planets at fixed steps from ``start`` to ``end``.

    One request instead of one per frame: a client scrubbing time takes the
    samples around the instant it wants and interpolates.

    Shape::

        {"ephemeris": "swisseph", "sidereal_time": "apparent",
         "start": "...Z", "end": "...Z", "step_seconds": 603, "count": 288,
         "samples": [{"at": "...Z", "gast_deg": 12.3...,
                      "sun": {"id": "sun", "lat": ..., "lon": ...},
                      "moon": {...},
                      "planets": [{"id": "mercury", ...}, ... "pluto"]}, ...]}

    The route adds ``provenance``. A sample is an ``earth_state`` payload
    without ``name``, ``ra_deg`` and ``dec_deg``, and unrounded (``earth_state``
    rounds to 4 decimals; here the raw doubles are kept so that the relation
    below holds to floating-point precision).

    **Reading a sample.**

    * declination ``dec = lat``;
    * right ascension ``ra = (lon + gast_deg) mod 360`` - apparent, true
      equator and equinox of date, with ``gast_deg`` the Greenwich *apparent*
      sidereal time (``swe.sidtime``, nutation included; NOT mean). The
      positions are apparent too, so the pair is consistent;
    * hour angle at an observer with east longitude ``L``: ``H = L - lon``.
      No sidereal time is needed for the Sun, Moon and planets.

    **Interpolating.** ``lon`` runs from +180 to -180 about once a day, so a
    plain average of two neighbours across the seam is ~180 degrees wrong.
    Step the short way round: ``d = wrap180(b - a)`` then
    ``wrap180(a + f * d)`` for ``f`` in [0, 1]; the same for ``gast_deg`` and
    for ``ra`` (with ``mod 360``). That is unambiguous for every allowed step
    because no body moves 180 degrees in 3600 s. ``lat`` interpolates
    linearly.

    **Error budget.** Linear interpolation adds at most 1.3e-5 degrees at the
    client's 603 s step (W3-O ``interp_error.md``: a whole year, every interval,
    quarter points; always the Moon, at its monthly declination maximum);
    midpoint-only runs over 4 windows from 1800 to 2200 gave 1.2e-7 at 60 s,
    7.2e-6 at 603 s and 2.8e-4 at 3600 s. Against the W3-O swisseph oracle
    (same Moshier ephemeris, 6 decimals) every compared value differs by at
    most 5.0e-7 degrees, which is the oracle's own rounding; its astropy study
    puts the ephemeris-convention difference at 0.0034 degrees (GAST) and 0.0004
    (declination). Sub-second starts are honoured: microseconds enter the
    Julian day.

    **Cost** (measured under load average ~20, 288 samples): p50 16 ms, p95
    19 ms in this function; the response is 213 KB unrounded (63 KB gzipped).
    Rounding to 1e-6 would save only 24% and would turn the exact relation
    above into one good to 5e-7, so it is not done; compress the response if
    size matters.

    **Limits** (all ``ValueError`` -> 422 in the route): ``step_seconds`` an
    integer in [60, 3600]; ``end`` not before ``start`` and exactly ``start +
    k * step_seconds`` (no silent truncation); at most 288 samples, both ends
    included (``k <= 287``); both ends inside 1800-01-01..2200-12-31 UTC.
    Naive datetimes are UTC. Validation runs before the ephemeris check, so
    bad input is 422 even when swisseph is missing.

    Raises:
        ValueError: any limit above.
        EphemerisUnavailable: swisseph is not importable.
    """
    low, high = SERIES_STEP_SECONDS
    if isinstance(step_seconds, bool) or not isinstance(step_seconds, int):
        raise ValueError(f"step_seconds must be an integer number of seconds, got {step_seconds!r}")
    if not (low <= step_seconds <= high):
        raise ValueError(f"step_seconds must be between {low} and {high}, got {step_seconds}")
    start = as_supported_utc(start, "start")
    end = as_supported_utc(end, "end")
    if end < start:
        raise ValueError("end is before start")
    steps, remainder = divmod(end - start, timedelta(seconds=step_seconds))
    if remainder:
        raise ValueError(f"end must be start plus a whole number of steps of step_seconds={step_seconds}")
    count = steps + 1
    if count > SERIES_MAX_SAMPLES:
        raise ValueError(
            f"too many samples: {count} requested, the cap is {SERIES_MAX_SAMPLES} (both ends included); "
            f"widen step_seconds or shorten the window"
        )
    if swe is None:  # pragma: no cover - environment dependent
        raise EphemerisUnavailable(f"swisseph import failed: {_IMPORT_ERROR}")

    samples = []
    for k in range(count):
        at = start + timedelta(seconds=step_seconds * k)
        jd = _julian_day(at)
        gast_deg = swe.sidtime(jd) * 15.0
        bodies = [_series_body(jd, gast_deg, body_id, swe_id) for (body_id, _name, swe_id) in _BODIES]
        samples.append(
            {
                "at": format_instant(at),
                "gast_deg": gast_deg,
                "sun": bodies[0],
                "moon": bodies[1],
                "planets": bodies[2:],
            }
        )
    return {
        "ephemeris": "swisseph",
        "sidereal_time": "apparent",
        "start": format_instant(start),
        "end": format_instant(end),
        "step_seconds": step_seconds,
        "count": count,
        "samples": samples,
    }
