"""Tests for :mod:`core.astro.timezone_policy` (wave W1 ticket W1-2).

The behaviour this module replaces is still in the tree and is not edited
here. Re-verified before these tests were written:

* ``pytz.timezone.localize`` defaults to ``is_dst=False``. It does not raise
  on a spring-forward gap or a fall-back overlap. For
  ``2024-11-03 01:30 America/New_York`` it silently returns standard time
  (``01:30-05:00``, 06:30Z). Same silent path as
  ``backend/app/api/v1/endpoints/astrology.py`` ``localize(dt)`` calls.
* ``GET /current`` still guesses an offset from longitude
  (``astrology.py`` endpoint, ``offset_hours = round(longitude * 2.0 / 15.0) / 2.0``).
* ``AstrologyCalculator.get_chinese_astrology`` and ``get_bazi_detailed``
  still call ``dt.astimezone(...)`` on the caller's datetime, which treats a
  naive value as the host zone. ``get_indian_astrology`` still compares a
  naive ``local_date`` with an aware sunrise.

These tests are offline and deterministic. ``pytz`` is a cross-check only.
The authority for offsets is the system IANA data via :mod:`zoneinfo`.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import pytz

from core.astro.timezone_policy import (
    PROVISIONAL_DEFAULTS,
    AmbiguousLocalTime,
    LocalTimeOutOfRange,
    NaiveDatetimeNotAllowed,
    NonexistentLocalTime,
    TimezonePolicyError,
    TimezoneResolution,
    UnknownTimezone,
    require_aware,
    resolve_local,
)

NY_GAP = datetime(2024, 3, 10, 2, 30)
NY_OVERLAP = datetime(2024, 11, 3, 1, 30)
NY = "America/New_York"

# Unambiguous instants. None of these sits in a gap or an overlap
# (checked against tzdata 2026.4 before the sample was frozen).
ROUND_TRIPS: tuple[tuple[str, datetime], ...] = (
    ("America/New_York", datetime(2024, 7, 4, 12, 0, 1, 2)),
    ("America/New_York", datetime(2024, 1, 15, 12, 0)),
    ("America/New_York", datetime(2024, 3, 10, 1, 30)),
    ("America/New_York", datetime(2024, 3, 10, 3, 30)),
    ("America/New_York", datetime(1942, 12, 15, 12, 0)),
    ("America/New_York", datetime(1850, 6, 15, 12, 0)),
    ("Australia/Adelaide", datetime(2024, 1, 15, 12, 0)),
    ("Australia/Adelaide", datetime(2024, 7, 15, 12, 30)),
    ("Australia/Lord_Howe", datetime(2024, 1, 15, 12, 0)),
    ("Australia/Lord_Howe", datetime(2024, 7, 15, 8, 0)),
    ("Asia/Kolkata", datetime(2024, 6, 1, 12, 0)),
    ("Asia/Kolkata", datetime(1942, 9, 1, 12, 0)),
    ("Asia/Kolkata", datetime(1905, 6, 1, 12, 0)),
    ("Europe/Rome", datetime(1990, 7, 15, 15, 30, 45)),
    ("Europe/Rome", datetime(1990, 1, 15, 15, 30)),
    ("UTC", datetime(2020, 1, 1, 0, 0)),
)

# Cases where pytz and zoneinfo agree to the second. Local-mean-time
# entries are excluded: pytz rounds New York 1850 to the minute.
PYTZ_AGREES: tuple[tuple[str, datetime], ...] = (
    ("America/New_York", datetime(2024, 7, 4, 12, 0)),
    ("America/New_York", datetime(2024, 1, 15, 12, 0)),
    ("America/New_York", datetime(1942, 12, 15, 12, 0)),
    ("America/New_York", datetime(1941, 12, 15, 12, 0)),
    ("Australia/Adelaide", datetime(2024, 1, 15, 12, 0)),
    ("Australia/Adelaide", datetime(2024, 7, 15, 12, 0)),
    ("Australia/Lord_Howe", datetime(2024, 1, 15, 12, 0)),
    ("Australia/Lord_Howe", datetime(2024, 7, 15, 12, 0)),
    ("Asia/Kolkata", datetime(2024, 6, 1, 12, 0)),
    ("Europe/Rome", datetime(1990, 7, 15, 12, 0)),
    ("Europe/Rome", datetime(1990, 1, 15, 12, 0)),
    ("UTC", datetime(2020, 1, 1, 0, 0)),
)


def _utc(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# The behaviour being replaced: pytz.localize does not raise
# ---------------------------------------------------------------------------


def test_pytz_localize_default_silently_picks_standard_time():
    """What the project does today. Default ``is_dst=False`` never raises.

    Spring gap ``2024-03-10 02:30`` becomes ``02:30-05:00`` (07:30Z).
    Fall overlap ``2024-11-03 01:30`` becomes ``01:30-05:00`` (06:30Z),
    discarding the daylight occurrence at 05:30Z.
    """
    ny = pytz.timezone(NY)
    gap = ny.localize(NY_GAP)
    overlap = ny.localize(NY_OVERLAP)
    assert gap.utcoffset() == timedelta(hours=-5)
    assert overlap.utcoffset() == timedelta(hours=-5)
    assert gap.astimezone(pytz.UTC).replace(tzinfo=None) == datetime(2024, 3, 10, 7, 30)
    assert overlap.astimezone(pytz.UTC).replace(tzinfo=None) == datetime(2024, 11, 3, 6, 30)


def test_ambiguous_new_york_is_rejected_instead_of_standardized():
    """The fall-back hour is two instants. Default policy must not pick one."""
    silent = pytz.timezone(NY).localize(NY_OVERLAP)
    assert silent.utcoffset() == timedelta(hours=-5)
    with pytest.raises(AmbiguousLocalTime, match="America/New_York") as excinfo:
        resolve_local(NY_OVERLAP, NY)
    err = excinfo.value
    assert isinstance(err, TimezonePolicyError)
    assert err.earlier_utc == _utc(2024, 11, 3, 5, 30)
    assert err.later_utc == _utc(2024, 11, 3, 6, 30)
    assert "01:30" in str(err)
    assert "earlier" in str(err)
    assert "later" in str(err)


def test_nonexistent_new_york_is_rejected_instead_of_labeled():
    """The spring-forward gap is not a real wall time. Do not invent an offset."""
    silent = pytz.timezone(NY).localize(NY_GAP)
    assert silent.utcoffset() == timedelta(hours=-5)
    with pytest.raises(NonexistentLocalTime, match="America/New_York") as excinfo:
        resolve_local(NY_GAP, NY)
    err = excinfo.value
    assert isinstance(err, TimezonePolicyError)
    assert "02:30" in str(err)
    assert "shift_forward" in str(err)


def test_ambiguous_opt_in_picks_an_instant_and_says_so():
    earlier = resolve_local(NY_OVERLAP, NY, ambiguous="earlier")
    later = resolve_local(NY_OVERLAP, NY, ambiguous="later")
    assert earlier.utc == _utc(2024, 11, 3, 5, 30)
    assert later.utc == _utc(2024, 11, 3, 6, 30)
    assert earlier.utc_offset == timedelta(hours=-4)
    assert later.utc_offset == timedelta(hours=-5)
    assert earlier.is_dst is True
    assert later.is_dst is False
    assert earlier.fold == 0
    assert later.fold == 1
    assert earlier.utc < later.utc
    assert any("earlier" in note for note in earlier.warnings)
    assert any("later" in note for note in later.warnings)
    assert earlier.local.replace(tzinfo=None) == NY_OVERLAP
    assert later.local.replace(tzinfo=None) == NY_OVERLAP


def test_nonexistent_shift_forward_lands_on_the_post_gap_wall_time():
    """02:30 does not exist. One hour later, 03:30 EDT, is 07:30Z.

    That is the same instant ``pytz.localize`` labels as ``02:30-05:00``,
    but the wall time we return is the time the clock actually showed.
    """
    shifted = resolve_local(NY_GAP, NY, nonexistent="shift_forward")
    assert shifted.local.replace(tzinfo=None) == datetime(2024, 3, 10, 3, 30)
    assert shifted.utc == _utc(2024, 3, 10, 7, 30)
    assert shifted.utc_offset == timedelta(hours=-4)
    assert shifted.is_dst is True
    assert shifted.fold == 0
    assert any("shift_forward" in note for note in shifted.warnings)
    assert any("02:30" in note and "03:30" in note for note in shifted.warnings)
    back = shifted.utc.astimezone(ZoneInfo(NY))
    assert back.replace(tzinfo=None) == datetime(2024, 3, 10, 3, 30)


# ---------------------------------------------------------------------------
# Half-hour zones, 30-minute DST, historical rules
# ---------------------------------------------------------------------------


def test_adelaide_uses_half_hour_standard_and_daylight_offsets():
    summer = resolve_local(datetime(2024, 1, 15, 12, 0), "Australia/Adelaide")
    winter = resolve_local(datetime(2024, 7, 15, 12, 0), "Australia/Adelaide")
    assert summer.utc_offset == timedelta(hours=10, minutes=30)
    assert summer.is_dst is True
    assert summer.utc == _utc(2024, 1, 15, 1, 30)
    assert winter.utc_offset == timedelta(hours=9, minutes=30)
    assert winter.is_dst is False
    assert winter.utc == _utc(2024, 7, 15, 2, 30)
    assert summer.warnings == ()
    assert winter.warnings == ()


def test_lord_howe_dst_shift_is_thirty_minutes():
    summer = resolve_local(datetime(2024, 1, 15, 12, 0), "Australia/Lord_Howe")
    winter = resolve_local(datetime(2024, 7, 15, 12, 0), "Australia/Lord_Howe")
    assert summer.utc_offset == timedelta(hours=11)
    assert summer.is_dst is True
    assert winter.utc_offset == timedelta(hours=10, minutes=30)
    assert winter.is_dst is False
    assert summer.utc_offset - winter.utc_offset == timedelta(minutes=30)
    assert summer.utc == _utc(2024, 1, 15, 1, 0)
    assert winter.utc == _utc(2024, 7, 15, 1, 30)

    gap = datetime(2024, 10, 6, 2, 15)
    with pytest.raises(NonexistentLocalTime, match="Lord_Howe"):
        resolve_local(gap, "Australia/Lord_Howe")
    shifted = resolve_local(gap, "Australia/Lord_Howe", nonexistent="shift_forward")
    assert shifted.local.replace(tzinfo=None) == datetime(2024, 10, 6, 2, 45)
    assert shifted.utc_offset == timedelta(hours=11)
    assert shifted.utc == _utc(2024, 10, 5, 15, 45)

    overlap = datetime(2024, 4, 7, 1, 45)
    with pytest.raises(AmbiguousLocalTime, match="Lord_Howe"):
        resolve_local(overlap, "Australia/Lord_Howe")
    earlier = resolve_local(overlap, "Australia/Lord_Howe", ambiguous="earlier")
    later = resolve_local(overlap, "Australia/Lord_Howe", ambiguous="later")
    assert earlier.utc_offset == timedelta(hours=11)
    assert later.utc_offset == timedelta(hours=10, minutes=30)
    assert later.utc - earlier.utc == timedelta(minutes=30)
    assert earlier.utc == _utc(2024, 4, 6, 14, 45)
    assert later.utc == _utc(2024, 4, 6, 15, 15)


def test_kolkata_half_hour_offset_and_historical_changes():
    modern = resolve_local(datetime(2024, 6, 1, 12, 0), "Asia/Kolkata")
    assert modern.utc_offset == timedelta(hours=5, minutes=30)
    assert modern.is_dst is False
    assert modern.utc == _utc(2024, 6, 1, 6, 30)

    # 1942 is inside India's wartime +06:30 fast time, not modern IST.
    wartime = resolve_local(datetime(1942, 9, 1, 12, 0), "Asia/Kolkata")
    assert wartime.utc_offset == timedelta(hours=6, minutes=30)
    assert wartime.is_dst is True
    assert wartime.utc == _utc(1942, 9, 1, 5, 30)

    # 1905 is before Indian Standard Time (1906-01-01 in tzdata). Not +05:30.
    before_ist = resolve_local(datetime(1905, 6, 1, 12, 0), "Asia/Kolkata")
    assert before_ist.utc_offset == timedelta(hours=5, minutes=21, seconds=10)
    assert before_ist.utc_offset != timedelta(hours=5, minutes=30)
    assert before_ist.is_dst is False


def test_us_eastern_war_time_in_december_1942_is_utc_minus_4():
    """December 1942 was Eastern War Time all day. A modern 'winter means
    standard time' rule would silently return UTC-5.
    """
    war = resolve_local(datetime(1942, 12, 15, 12, 0), NY)
    prewar = resolve_local(datetime(1941, 12, 15, 12, 0), NY)
    postwar = resolve_local(datetime(1946, 1, 15, 12, 0), NY)
    assert war.utc_offset == timedelta(hours=-4)
    assert war.is_dst is True
    assert war.utc == _utc(1942, 12, 15, 16, 0)
    assert prewar.utc_offset == timedelta(hours=-5)
    assert prewar.is_dst is False
    assert prewar.utc == _utc(1941, 12, 15, 17, 0)
    assert postwar.utc_offset == timedelta(hours=-5)
    assert postwar.is_dst is False


def test_rome_summer_1990_is_two_hours_ahead_of_utc():
    summer = resolve_local(datetime(1990, 7, 15, 12, 0), "Europe/Rome")
    winter = resolve_local(datetime(1990, 1, 15, 12, 0), "Europe/Rome")
    assert summer.utc_offset == timedelta(hours=2)
    assert summer.is_dst is True
    assert summer.utc == _utc(1990, 7, 15, 10, 0)
    assert winter.utc_offset == timedelta(hours=1)
    assert winter.is_dst is False
    assert winter.utc == _utc(1990, 1, 15, 11, 0)


def test_pre_1900_local_mean_time_keeps_the_seconds_pytz_rounds_away():
    """America/New_York before 1883-11-18 is local mean time, UTC-4:56:02.

    ``pytz.localize`` on this date returns UTC-4:56, dropping two seconds.
    The policy follows zoneinfo.
    """
    naive = datetime(1850, 6, 15, 12, 0)
    result = resolve_local(naive, NY)
    assert result.utc_offset == timedelta(hours=-4, minutes=-56, seconds=-2)
    assert result.is_dst is False
    assert result.utc == _utc(1850, 6, 15, 16, 56, 2)
    assert result.warnings == ()
    pytz_offset = pytz.timezone(NY).localize(naive).utcoffset()
    assert pytz_offset == timedelta(hours=-4, minutes=-56)
    assert result.utc_offset != pytz_offset


# ---------------------------------------------------------------------------
# Refusal cases and the provisional bare-naive decision
# ---------------------------------------------------------------------------


def test_unknown_zone_raises_unknown_timezone():
    with pytest.raises(TimezonePolicyError, match="Not/ARealZone") as excinfo:
        resolve_local(datetime(2024, 6, 1, 12, 0), "Not/ARealZone")
    assert isinstance(excinfo.value, UnknownTimezone)


# ZoneInfo raises ValueError or OSError for these, not ZoneInfoNotFoundError.
# An HTTP parameter must still come back as UnknownTimezone, and the message
# must not grow with the input or repeat a filesystem path.
_HOSTILE_ZONES = [
    ("empty", ""),
    ("trailing-slash", "America/"),
    ("double-slash", "America//New_York"),
    ("parent-traversal", "../etc/passwd"),
    ("absolute", "/etc/passwd"),
    ("dot", "."),
    ("dotdot", ".."),
    ("embedded-nul", "America/New_York\x00"),
    ("overlong", "a" * 5000),
    ("tzdata-zi", "tzdata.zi"),
    ("zone-tab", "zone.tab"),
]


@pytest.mark.parametrize(("label", "zone"), _HOSTILE_ZONES, ids=[name for name, _zone in _HOSTILE_ZONES])
def test_hostile_zone_string_is_unknown_timezone(label: str, zone: str):
    del label
    with pytest.raises(UnknownTimezone) as excinfo:
        resolve_local(datetime(2024, 6, 1, 12, 0), zone)
    message = str(excinfo.value)
    assert len(message) < 200
    assert "/home" not in message
    assert "\x00" not in message
    assert excinfo.value.zone == zone


def test_datetime_outside_supported_range_is_typed():
    """Year 1 in a positive offset, and year 9999 in a negative offset, overflow."""
    with pytest.raises(LocalTimeOutOfRange, match="Asia/Tokyo") as tokyo:
        resolve_local(datetime(1, 1, 1, 0, 0), "Asia/Tokyo")
    assert "0001-01-01" in str(tokyo.value)
    with pytest.raises(LocalTimeOutOfRange, match="America/New_York") as new_york:
        resolve_local(datetime(9999, 12, 31, 23, 59), "America/New_York")
    assert "9999-12-31" in str(new_york.value)


def test_kiritimati_last_minute_of_year_9999_still_resolves():
    result = resolve_local(datetime(9999, 12, 31, 23, 59), "Pacific/Kiritimati")
    assert result.utc == datetime(9999, 12, 31, 9, 59, tzinfo=timezone.utc)
    assert result.utc_offset == timedelta(hours=14)
    assert result.warnings == ()


def test_every_typed_policy_error_is_a_value_error():
    raised: list[BaseException] = []
    with pytest.raises(AmbiguousLocalTime) as ambiguous:
        resolve_local(datetime(2024, 11, 3, 1, 30), NY)
    raised.append(ambiguous.value)
    with pytest.raises(NonexistentLocalTime) as missing:
        resolve_local(datetime(2024, 3, 10, 2, 30), NY)
    raised.append(missing.value)
    with pytest.raises(UnknownTimezone) as unknown:
        resolve_local(datetime(2024, 6, 1, 12, 0), "Mars/Phobos")
    raised.append(unknown.value)
    with pytest.raises(NaiveDatetimeNotAllowed) as naive:
        require_aware(datetime(2024, 1, 1, 12, 0))
    raised.append(naive.value)
    with pytest.raises(LocalTimeOutOfRange) as out_of_range:
        resolve_local(datetime(1, 1, 1, 0, 0), "Asia/Tokyo")
    raised.append(out_of_range.value)
    with pytest.raises(TimezonePolicyError) as aware:
        resolve_local(datetime(2024, 7, 4, 12, 0, tzinfo=timezone.utc), NY)
    raised.append(aware.value)
    assert len(raised) == 6
    for exc in raised:
        assert isinstance(exc, ValueError)
        assert isinstance(exc, TimezonePolicyError)


def test_bare_naive_timestamp_is_rejected():
    """needs-learner-decision. Provisional default is ``reject``."""
    assert PROVISIONAL_DEFAULTS["bare_naive_timestamp"] == "reject"
    assert PROVISIONAL_DEFAULTS["needs_learner_decision"] is True
    naive = datetime(2024, 1, 1, 12, 0)
    with pytest.raises(NaiveDatetimeNotAllowed, match="Naive") as excinfo:
        require_aware(naive)
    assert isinstance(excinfo.value, TimezonePolicyError)
    assert "reject" in str(excinfo.value)
    aware = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert require_aware(aware) is aware


def test_resolve_local_refuses_an_aware_datetime():
    aware = datetime(2024, 7, 4, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(TimezonePolicyError, match="naive"):
        resolve_local(aware, NY)


def test_unknown_policy_value_is_rejected_on_an_ordinary_instant():
    ordinary = datetime(2024, 7, 4, 12, 0)
    with pytest.raises(TimezonePolicyError, match="ambiguous"):
        resolve_local(ordinary, NY, ambiguous="guess")
    with pytest.raises(TimezonePolicyError, match="nonexistent"):
        resolve_local(ordinary, NY, nonexistent="skip")


def test_defaults_come_from_the_provisional_table():
    assert PROVISIONAL_DEFAULTS["ambiguous"] == "error"
    assert PROVISIONAL_DEFAULTS["nonexistent"] == "error"
    # An ordinary instant resolves with no warning under those defaults.
    result = resolve_local(datetime(2024, 7, 4, 12, 0), NY)
    assert isinstance(result, TimezoneResolution)
    assert result.warnings == ()
    assert result.zone == NY
    assert result.utc.tzinfo is timezone.utc
    assert result.fold == 0
    assert result.is_dst is True
    assert result.utc_offset == timedelta(hours=-4)


def test_opt_in_flags_do_not_warn_when_the_instant_is_unique():
    result = resolve_local(
        datetime(2024, 7, 4, 12, 0),
        NY,
        ambiguous="earlier",
        nonexistent="shift_forward",
    )
    assert result.warnings == ()
    assert result.utc == _utc(2024, 7, 4, 16, 0)


# ---------------------------------------------------------------------------
# Round trip: local -> UTC -> local
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("zone", "local_naive"), ROUND_TRIPS)
def test_local_utc_local_round_trip(zone: str, local_naive: datetime):
    result = resolve_local(local_naive, zone)
    assert result.warnings == ()
    assert result.utc.tzinfo is timezone.utc
    assert result.local.replace(tzinfo=None) == local_naive
    assert result.local.fold == result.fold
    assert result.local.utcoffset() == result.utc_offset
    back = result.utc.astimezone(ZoneInfo(zone))
    assert back.replace(tzinfo=None) == local_naive
    assert back.fold == result.fold
    assert result.local.astimezone(timezone.utc) == result.utc


def test_opt_in_ambiguous_round_trips_with_the_fold_that_was_used():
    for choice, fold, expected in (
        ("earlier", 0, _utc(2024, 11, 3, 5, 30)),
        ("later", 1, _utc(2024, 11, 3, 6, 30)),
    ):
        result = resolve_local(NY_OVERLAP, NY, ambiguous=choice)
        back = result.utc.astimezone(ZoneInfo(NY))
        assert back.replace(tzinfo=None) == NY_OVERLAP
        assert back.fold == fold
        assert result.utc == expected


@pytest.mark.parametrize(("zone", "local_naive"), PYTZ_AGREES)
def test_pytz_cross_check_on_unambiguous_instants(zone: str, local_naive: datetime):
    result = resolve_local(local_naive, zone)
    localized = pytz.timezone(zone).localize(local_naive)
    pytz_utc = localized.astimezone(timezone.utc)
    assert result.utc == pytz_utc
    assert result.utc_offset == localized.utcoffset()


def test_module_does_not_import_pytz_or_the_database():
    """Production code is stdlib only. pytz stays in this test file."""
    import core.astro.timezone_policy as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    banned_prefixes = ("pytz", "sqlite3", "sqlalchemy", "requests", "core.", "swisseph", "socket")
    offenders = [name for name in imported if name.startswith(banned_prefixes)]
    assert offenders == []
    assert "needs-learner-decision" in (mod.__doc__ or "")
