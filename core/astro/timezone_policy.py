"""Strict local-time policy for astrology instants.

A local clock reading plus an IANA zone name becomes one UTC instant, or a
typed error a caller can turn into HTTP 422. Nothing in this module guesses.

WHY THIS EXISTS
---------------
Wave W0 measured three silent time bugs. They are still in the tree; this
module does not edit those files. Later waves are meant to call here instead.

* ``pytz.timezone.localize`` defaults to ``is_dst=False``, so a fall-back
  overlap such as ``2024-11-03 01:30 America/New_York`` becomes standard
  time with no signal. The astrology endpoint calls ``localize(dt)``.
* A missing zone on ``GET /current`` becomes ``round(longitude * 2 / 15) / 2``
  hours. That is 1.5 h off for Adelaide.
* ``get_chinese_astrology`` and ``get_bazi_detailed`` call ``datetime.astimezone``
  on the value they were given. A naive value is read in the host zone.
  ``get_indian_astrology`` compares that naive value with an aware sunrise
  and raises ``TypeError``.

CONTRACT
--------
* :func:`resolve_local` takes a naive wall time and an IANA name. It returns
  a :class:`TimezoneResolution`: aware UTC, the UTC offset, whether the zone
  database calls the instant daylight time, the fold that was used, the aware
  local time actually kept, and a tuple of warnings.
* Default policy raises :class:`AmbiguousLocalTime` on a fall-back overlap and
  :class:`NonexistentLocalTime` on a spring-forward gap.
* Opt in with ``ambiguous='earlier'`` or ``'later'``, or
  ``nonexistent='shift_forward'``. The choice is written into ``warnings``.
  Passing either flag on a unique instant does not warn.
* :func:`require_aware` is the door for a datetime that is already zoned.
  A naive value is refused. See the provisional decision below.
* :class:`UnknownTimezone` is an unknown IANA name. An aware datetime passed
  to :func:`resolve_local` raises :class:`TimezonePolicyError`: the wall time
  and the attached offset would otherwise compete.
* Every exception above is a :class:`TimezonePolicyError` and a ``ValueError``.
  The message names the zone and the clock time. There is no bare ``except``
  and no ``except: pass``.
* Pure: :mod:`datetime` and :mod:`zoneinfo` only. No pytz, no database, no
  network, no import-time work, no cache of our own. ``ZoneInfo`` may cache
  inside the standard library; this module does not.

DETECTION
---------
The two questions are the ones PEP 495 and the W0-B note are about. Re-checked
on CPython 3.13 and tzdata 2026.4 before this module was written.

Attach the zone twice, ``fold=0`` and ``fold=1`` (PEP 495). Then:

1. Fold disagreement. ``utcoffset()`` differs between the two folds. The clock
   reading is not a single offset.
2. UTC round-trip. ``aware.astimezone(timezone.utc).astimezone(zone)`` does not
   come back to the same wall time. The reading is not a moment that happened.

A round-trip that fails on either fold is a gap (nonexistent). A fold
disagreement whose round-trip succeeds on both folds is an overlap
(ambiguous). Anything else is unique. Ordinary summer and winter instants
are unique, including zones whose offset is not a whole hour.

The one-liner in the W0-B note spells the second test as
``d.replace(tzinfo=timezone.utc).astimezone(zone)``. That relabels the wall
numbers as UTC instead of converting them. On this runtime it is true for
every zone except UTC, so it cannot separate a gap from a normal afternoon.
The conversion that matches the note's own truth table is ``astimezone``.
``fold`` offsets also differ inside a gap on this runtime, so a fold
disagreement alone is not enough to call a time ambiguous. The gap test has
to run first.

``earlier`` is the fold whose UTC instant comes first, ``later`` the other.
On current zoneinfo that is fold 0 and fold 1. The instants are what we
compare, not the integers.

``shift_forward`` takes the UTC-round-trip wall that is strictly later than
the requested clock time and resolves that wall time as an ordinary instant.
Measured gaps move ahead by exactly the size of the skip: one hour in
``America/New_York`` and ``Australia/Adelaide``, thirty minutes in
``Australia/Lord_Howe``. The returned local time is the time the clock showed
after the skip, and the warning names both clock times.

Offsets, including local mean time and wartime daylight, come from the system
IANA data through ``ZoneInfo.utcoffset``. This module has no offset formula
of its own. ``is_dst`` is ``tzinfo.dst() != timedelta(0)``: the database's
daylight adjustment, not a season. US Eastern War Time in December 1942 is
daylight time under that rule. ``dst() is None`` leaves ``is_dst`` as ``None``
and adds a warning; zoneinfo does not do that.

NEEDS-LEARNER-DECISION
----------------------
needs-learner-decision: a bare naive timestamp with no zone and no offset has
no single meaning.
:data:`PROVISIONAL_DEFAULTS` ``bare_naive_timestamp`` is ``reject``, so
:func:`require_aware` raises :class:`NaiveDatetimeNotAllowed`. That is a
provisional choice, not a universal rule. The only bare-naive value this
module implements is ``reject``.

``ambiguous`` and ``nonexistent`` default to ``error``. That default is the
required policy, not an open decision. Pass ``earlier``, ``later``, or
``shift_forward`` to opt in for one call. The table holds those defaults so
the call site can read them; it is not a second copy of the naive-timestamp
decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "PROVISIONAL_DEFAULTS",
    "AmbiguousLocalTime",
    "LocalTimeOutOfRange",
    "NaiveDatetimeNotAllowed",
    "NonexistentLocalTime",
    "TimezonePolicyError",
    "TimezoneResolution",
    "UnknownTimezone",
    "require_aware",
    "resolve_local",
]

#: Defaults read on each call. ``bare_naive_timestamp`` is provisional
#: (needs-learner-decision). ``ambiguous`` and ``nonexistent`` are the
#: required error policy. Not a cache.
PROVISIONAL_DEFAULTS: dict[str, object] = {
    "bare_naive_timestamp": "reject",
    "ambiguous": "error",
    "nonexistent": "error",
    "needs_learner_decision": True,
}

_AMBIGUOUS = frozenset({"error", "earlier", "later"})
_NONEXISTENT = frozenset({"error", "shift_forward"})


class TimezonePolicyError(ValueError):
    """A local time could not be given one honest UTC instant.

    Subclasses are the cases an HTTP layer should return as 422. The message
    is the response detail: it names the clock time, the zone, and the choice
    that would resolve it.
    """


class AmbiguousLocalTime(TimezonePolicyError):
    """The wall time happened twice, at the two UTC instants named here."""

    def __init__(self, local: datetime, zone: str, earlier_utc: datetime, later_utc: datetime) -> None:
        self.local = local
        self.zone = zone
        self.earlier_utc = earlier_utc
        self.later_utc = later_utc
        super().__init__(
            f"Ambiguous local time {_stamp(local)} in {zone}: "
            f"this wall time occurs twice, earlier {earlier_utc.isoformat()} "
            f"and later {later_utc.isoformat()}. "
            "Pass ambiguous='earlier' or ambiguous='later'."
        )


class NonexistentLocalTime(TimezonePolicyError):
    """The wall time was skipped by a spring-forward transition."""

    def __init__(self, local: datetime, zone: str, forward_wall: datetime) -> None:
        self.local = local
        self.zone = zone
        self.forward_wall = forward_wall
        super().__init__(
            f"Nonexistent local time {_stamp(local)} in {zone}: "
            "the clocks skipped this wall time during a spring-forward transition. "
            f"nonexistent='shift_forward' would use {_stamp(forward_wall)}."
        )


class UnknownTimezone(TimezonePolicyError):
    """``zone`` is not a name in the system IANA time zone database.

    The message shows ``repr(zone)`` cut at 64 characters. It does not include
    the interpreter's own error text, which can contain a filesystem path.
    ``zone`` itself is the full string the caller passed.
    """

    def __init__(self, zone: str) -> None:
        self.zone = zone
        super().__init__(
            f"Unknown IANA time zone {_zone_label(zone)}. "
            "Use a zone name from the system time zone database, for example 'America/New_York'."
        )


class LocalTimeOutOfRange(TimezonePolicyError):
    """The zone offset would place this wall time outside ``datetime``'s range."""

    def __init__(self, local: datetime, zone: str) -> None:
        self.local = local
        self.zone = zone
        super().__init__(f"Local time {_stamp(local)} in {zone} is outside the supported datetime range.")


class NaiveDatetimeNotAllowed(TimezonePolicyError):
    """A naive timestamp arrived with no zone.

    Provisional policy ``bare_naive_timestamp='reject'`` (needs-learner-decision).
    """

    def __init__(self, moment: datetime) -> None:
        self.dt = moment
        super().__init__(
            "Naive datetime is not allowed without an IANA zone. "
            f"Got {_stamp(moment)}. "
            "PROVISIONAL policy bare_naive_timestamp='reject' (needs-learner-decision). "
            "Pass an aware datetime to require_aware, or pass the wall time and a zone name to resolve_local."
        )


@dataclass(frozen=True)
class TimezoneResolution:
    """One resolved local time.

    Attributes:
        utc: The instant, aware, ``tzinfo`` is ``timezone.utc``.
        utc_offset: Offset of ``local`` from UTC, taken from the zone database.
        is_dst: True when the database's daylight adjustment is not zero.
            None only when ``dst()`` itself returned None.
        fold: The PEP 495 fold of ``local``. 0 on a unique instant, 0 for
            ``earlier``, 1 for ``later`` on current zoneinfo.
        zone: The IANA name the caller passed.
        local: Aware local datetime that was kept. After ``shift_forward``
            this is the post-gap wall time, not the skipped one.
        warnings: Empty when the input was a unique instant. Otherwise one
            note naming the opt-in that was applied.
    """

    utc: datetime
    utc_offset: timedelta
    is_dst: bool | None
    fold: int
    zone: str
    local: datetime
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Reading:
    """Fold pair for one wall time, plus what the UTC round-trip came back as."""

    kind: str
    fold0: datetime
    fold1: datetime
    wall0: datetime
    wall1: datetime


def require_aware(dt: datetime, *, policy: str | None = None) -> datetime:
    """Return ``dt`` if it already carries an offset.

    A naive ``dt`` is refused when the effective policy is ``reject``.
    The default comes from :data:`PROVISIONAL_DEFAULTS` ``bare_naive_timestamp``
    and is provisional (needs-learner-decision). ``policy`` overrides the table
    for this call. The only implemented value is ``reject``.
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"require_aware expected a datetime, got {type(dt).__name__}")
    chosen = PROVISIONAL_DEFAULTS["bare_naive_timestamp"] if policy is None else policy
    if not isinstance(chosen, str):
        raise TimezonePolicyError(f"Bare-naive policy must be a string, got {chosen!r}.")
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt
    if chosen == "reject":
        raise NaiveDatetimeNotAllowed(dt)
    raise TimezonePolicyError(
        f"Bare-naive policy {chosen!r} is not implemented. "
        "The only implemented value is 'reject' "
        "(PROVISIONAL_DEFAULTS['bare_naive_timestamp'], needs-learner-decision)."
    )


def resolve_local(
    local: datetime,
    zone: str,
    *,
    ambiguous: str | None = None,
    nonexistent: str | None = None,
) -> TimezoneResolution:
    """Resolve one naive local time in an IANA zone to a single UTC instant.

    A fold set on the naive input is ignored: the wall time is normalised to
    fold 0, and an overlap is resolved only by ``ambiguous``.

    ``ambiguous`` and ``nonexistent`` default to the provisional table, which
    is ``error``. ``earlier`` / ``later`` and ``shift_forward`` are opt-in and
    are recorded in ``warnings``. See the module docstring for the fold and
    UTC round-trip rules.
    """
    if not isinstance(local, datetime):
        raise TypeError(f"resolve_local expected a datetime, got {type(local).__name__}")
    ambiguous_policy = _choice("ambiguous", ambiguous, _AMBIGUOUS)
    nonexistent_policy = _choice("nonexistent", nonexistent, _NONEXISTENT)
    if local.tzinfo is not None:
        offset = local.utcoffset()
        raise TimezonePolicyError(
            "resolve_local requires a naive local datetime plus an IANA zone. "
            f"Got an aware datetime {_stamp(local)} (offset {offset}). "
            "Pass the wall time without tzinfo, or call require_aware when the "
            "datetime is already zoned. Combining both would guess which one wins."
        )
    wall = local.replace(fold=0)
    zi = _load_zone(zone)
    try:
        reading = _read(wall, zi)
        if reading.kind == "nonexistent":
            return _resolve_gap(wall, zone, zi, reading, nonexistent_policy)
        if reading.kind == "ambiguous":
            return _resolve_overlap(wall, zone, reading, ambiguous_policy)
        return _finish(reading.fold0, zone, ())
    except OverflowError as exc:
        raise LocalTimeOutOfRange(wall, zone) from exc


def _choice(name: str, value: str | None, allowed: frozenset[str]) -> str:
    if value is None:
        raw = PROVISIONAL_DEFAULTS[name]
        if not isinstance(raw, str):
            raise TimezonePolicyError(f"PROVISIONAL_DEFAULTS[{name!r}] must be a string, got {raw!r}.")
        value = raw
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise TimezonePolicyError(f"Unknown {name} policy {value!r}. Choose one of: {choices}.")
    return value


def _load_zone(zone: str) -> ZoneInfo:
    if not isinstance(zone, str):
        raise TypeError(f"zone must be an IANA name string, got {type(zone).__name__}")
    try:
        return ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise UnknownTimezone(zone) from exc


def _zone_label(zone: str) -> str:
    """``repr(zone)`` trimmed to 64 characters, plus an ellipsis when cut.

    ``repr`` escapes control characters. Callers that need the raw name read
    ``UnknownTimezone.zone``; this string is the HTTP message.
    """
    shown = repr(zone)
    if len(shown) <= 64:
        return shown
    return shown[:64] + "..."


def _read(wall: datetime, zi: ZoneInfo) -> _Reading:
    """Classify ``wall`` by the fold pair and the UTC round-trip.

    Gap first. On tzdata 2026.4 a spring gap makes the two folds disagree
    on ``utcoffset`` and both folds fail the round-trip, so the fold test
    alone would call the gap ambiguous.
    """
    fold0 = wall.replace(tzinfo=zi, fold=0)
    fold1 = wall.replace(tzinfo=zi, fold=1)
    offset0 = fold0.utcoffset()
    offset1 = fold1.utcoffset()
    if offset0 is None or offset1 is None:
        raise TimezonePolicyError(f"No UTC offset for {_stamp(wall)} in {zi.key}.")
    wall0 = _round_trip_wall(fold0)
    wall1 = _round_trip_wall(fold1)
    if wall0 != wall or wall1 != wall:
        kind = "nonexistent"
    elif offset0 != offset1:
        kind = "ambiguous"
    else:
        kind = "unique"
    return _Reading(kind=kind, fold0=fold0, fold1=fold1, wall0=wall0, wall1=wall1)


def _round_trip_wall(aware: datetime) -> datetime:
    """Wall time of ``aware`` after converting to UTC and back to its zone."""
    if aware.tzinfo is None:
        raise TimezonePolicyError("UTC round-trip requires an aware datetime.")
    return aware.astimezone(timezone.utc).astimezone(aware.tzinfo).replace(tzinfo=None, fold=0)


def _resolve_gap(
    wall: datetime,
    zone: str,
    zi: ZoneInfo,
    reading: _Reading,
    policy: str,
) -> TimezoneResolution:
    forward = _forward_wall(wall, zone, reading)
    if policy == "error":
        raise NonexistentLocalTime(wall, zone, forward)
    shifted = _read(forward, zi)
    if shifted.kind != "unique":
        raise NonexistentLocalTime(wall, zone, forward)
    note = (
        f"nonexistent local time {_stamp(wall)} shifted forward to {_stamp(forward)} "
        f"in {zone} because nonexistent='shift_forward'"
    )
    return _finish(shifted.fold0, zone, (note,))


def _forward_wall(wall: datetime, zone: str, reading: _Reading) -> datetime:
    """The post-gap clock time: the later image of the two UTC round-trips."""
    later = [candidate for candidate in (reading.wall0, reading.wall1) if candidate > wall]
    if not later:
        raise TimezonePolicyError(
            f"Cannot shift {_stamp(wall)} forward in {zone}: " "the UTC round-trip produced no later wall time."
        )
    return min(later)


def _resolve_overlap(
    wall: datetime,
    zone: str,
    reading: _Reading,
    policy: str,
) -> TimezoneResolution:
    earlier, later = _by_instant(reading.fold0, reading.fold1)
    earlier_utc = earlier.astimezone(timezone.utc)
    later_utc = later.astimezone(timezone.utc)
    if policy == "error":
        raise AmbiguousLocalTime(wall, zone, earlier_utc, later_utc)
    chosen = earlier if policy == "earlier" else later
    offset = chosen.utcoffset()
    note = (
        f"ambiguous local time {_stamp(wall)} in {zone} resolved with ambiguous={policy!r} "
        f"(fold={chosen.fold}, utc_offset={_format_offset(offset)}, utc={chosen.astimezone(timezone.utc).isoformat()})"
    )
    return _finish(chosen, zone, (note,))


def _by_instant(fold0: datetime, fold1: datetime) -> tuple[datetime, datetime]:
    if fold0.astimezone(timezone.utc) <= fold1.astimezone(timezone.utc):
        return fold0, fold1
    return fold1, fold0


def _finish(aware: datetime, zone: str, warnings: tuple[str, ...]) -> TimezoneResolution:
    offset = aware.utcoffset()
    if offset is None:
        raise TimezonePolicyError(f"No UTC offset for {aware.isoformat()} in {zone}.")
    dst = aware.dst()
    if dst is None:
        is_dst: bool | None = None
        warnings = warnings + ("DST offset is unknown for this instant; is_dst was not guessed.",)
    else:
        is_dst = dst != timedelta(0)
    return TimezoneResolution(
        utc=aware.astimezone(timezone.utc),
        utc_offset=offset,
        is_dst=is_dst,
        fold=aware.fold,
        zone=zone,
        local=aware,
        warnings=warnings,
    )


def _stamp(moment: datetime) -> str:
    return moment.isoformat(sep=" ")


def _format_offset(delta: timedelta | None) -> str:
    if delta is None:
        return "unknown"
    total = int(delta.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if seconds:
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{sign}{hours:02d}:{minutes:02d}"
