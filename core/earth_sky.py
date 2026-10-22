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

from datetime import datetime, timezone

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
    elif at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    else:
        at = at.astimezone(timezone.utc)
    if not (_RANGE_START <= at <= _RANGE_END):
        raise ValueError(f"time outside supported range 1800-01-01..2200-12-31 UTC: {at.isoformat()}")
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
