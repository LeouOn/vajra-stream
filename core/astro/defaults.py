"""Default location for astrology calculations, and where it came from.

WHY THIS MODULE EXISTS
    The learner confirmed on 2026-10-08 that a missing location may default
    to San Francisco. That default was applied inconsistently and silently:
    some call sites used San Francisco, and others fell back to ``(0.0, 0.0)``
    - the equator at the prime meridian, in the Gulf of Guinea - without saying
    so. This module gives the project ONE default, and makes the fallback
    visible: a resolved location always records whether it was given or
    defaulted, and a defaulted one carries a warning.

PROVISIONAL DEFAULTS (learner decisions)
    The single default is ``DEFAULT_LOCATION`` = (37.7749, -122.4194),
    San Francisco, California, USA - the value the learner confirmed on
    2026-10-08 and the value the project already used in several places.
    It is PROVISIONAL in the sense that it is a swappable constant, not a
    claim that San Francisco is the right location for any particular user:
    change ``DEFAULT_LOCATION`` and every caller follows.

CONTRACT
    ``resolve_location`` never clamps, coerces or guesses. A coordinate that
    is out of range, not finite, not a number, or only half-given is a
    ``ValueError`` whose message names the field. A location that is simply
    absent is the ONE case that is defaulted, and it is reported in
    ``warnings`` with ``source`` set to ``"default_sf"``.

PURITY
    This is a pure module: no database, no network, no import-time side
    effects, no module-level mutable state, and no dependency on
    ``core.astrology`` internals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

#: The single default location: San Francisco, California, USA.
#:
#: PROVISIONAL, learner-confirmed on 2026-10-08.
#: Latitude 37.7749 N, longitude -122.4194 W.
DEFAULT_LOCATION: tuple[float, float] = (37.7749, -122.4194)

#: ``source`` values: the caller gave a location, or the default was used.
LocationSource = Literal["given", "default_sf"]

SOURCE_GIVEN: LocationSource = "given"
SOURCE_DEFAULT_SF: LocationSource = "default_sf"

#: The warning added when the default is used.
DEFAULT_LOCATION_WARNING = "location not given: using the default (San Francisco)"

_LATITUDE_RANGE = (-90.0, 90.0)
_LONGITUDE_RANGE = (-180.0, 180.0)


@dataclass(frozen=True)
class ResolvedLocation:
    """A location to calculate with, and where it came from.

    Attributes:
        lat: Latitude in degrees, north positive.
        lon: Longitude in degrees, east positive.
        source: ``"given"`` when the caller supplied the location,
            ``"default_sf"`` when :data:`DEFAULT_LOCATION` was used.
        warnings: Human-readable notes about how this was resolved. Empty when
            the location was given; one entry when the default was used.
    """

    lat: float
    lon: float
    source: LocationSource
    warnings: tuple[str, ...] = ()


def _short(value: object) -> str:
    """A short rendering of a value for an error message.

    A rejected coordinate can be a 4,000-digit integer, and echoing it whole
    would put a 4,000-character message in the log.
    """
    text = repr(value)
    return text if len(text) <= 40 else text[:37] + "..."


def _validate_latitude(value: object) -> float:
    """Return ``value`` as a float, or raise ``ValueError`` naming latitude."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"latitude must be a number, got {type(value).__name__}: {_short(value)}")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        # A huge int cannot be converted to a float at all; that is still just
        # an invalid coordinate, so it is reported the same way.
        raise ValueError(f"latitude must be a finite number, got {_short(value)}") from exc
    if not math.isfinite(number):
        raise ValueError(f"latitude must be a finite number, got {_short(value)}")
    low, high = _LATITUDE_RANGE
    if not low <= number <= high:
        raise ValueError(f"latitude must be in [{low:g}, {high:g}], got {_short(value)}")
    return number


def _validate_longitude(value: object) -> float:
    """Return ``value`` as a float, or raise ``ValueError`` naming longitude."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"longitude must be a number, got {type(value).__name__}: {_short(value)}")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        # A huge int cannot be converted to a float at all; that is still just
        # an invalid coordinate, so it is reported the same way.
        raise ValueError(f"longitude must be a finite number, got {_short(value)}") from exc
    if not math.isfinite(number):
        raise ValueError(f"longitude must be a finite number, got {_short(value)}")
    low, high = _LONGITUDE_RANGE
    if not low <= number <= high:
        raise ValueError(f"longitude must be in [{low:g}, {high:g}], got {_short(value)}")
    return number


def resolve_location(
    location: tuple[float, float] | None,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> ResolvedLocation:
    """Resolve the location to calculate with, and report how it was chosen.

    Args:
        location: A ``(lat, lon)`` pair, or ``None`` when the caller has no
            location. When given it takes precedence over ``lat``/``lon``.
        lat: Latitude, used only when ``location`` is ``None``.
        lon: Longitude, used only when ``location`` is ``None``.

    Returns:
        A frozen :class:`ResolvedLocation`. ``source`` is ``"given"`` for a
        caller-supplied location and ``"default_sf"`` for the default; the
        defaulted case also carries one warning.

    Raises:
        ValueError: If a supplied coordinate is not a number, is not finite,
            is out of range, or if only one of ``lat``/``lon`` was given. The
            message names the offending field. Nothing is clamped or coerced.
    """
    if location is not None:
        if not isinstance(location, tuple | list) or len(location) != 2:
            raise ValueError(f"location must be a (lat, lon) pair, got {location!r}")
        return ResolvedLocation(
            lat=_validate_latitude(location[0]),
            lon=_validate_longitude(location[1]),
            source=SOURCE_GIVEN,
            warnings=(),
        )

    if lat is None and lon is None:
        default_lat, default_lon = DEFAULT_LOCATION
        return ResolvedLocation(
            lat=default_lat,
            lon=default_lon,
            source=SOURCE_DEFAULT_SF,
            warnings=(DEFAULT_LOCATION_WARNING,),
        )

    if lat is None:
        raise ValueError("latitude was not given but longitude was; give both or neither")
    if lon is None:
        raise ValueError("longitude was not given but latitude was; give both or neither")

    return ResolvedLocation(
        lat=_validate_latitude(lat),
        lon=_validate_longitude(lon),
        source=SOURCE_GIVEN,
        warnings=(),
    )
