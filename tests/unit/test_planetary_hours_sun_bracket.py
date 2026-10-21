"""PH-1: the planetary hour is measured inside the solar day containing the instant.

A solar day runs sunrise to sunrise. Its DAY part (sunrise to sunset) is twelve
equal hours and its NIGHT part (sunset to the next sunrise) is twelve equal
hours; the instant falls in exactly one of them. The day ruler is the VARA: the
weekday of the local mean solar date of the sunrise that began the solar day,
so an instant after local midnight but before sunrise belongs to the PREVIOUS
day's ruler.

The expectations here are hand-computed from the calendar and cross-checked
against independently written oracles. They disagree in one narrow case, which
is pinned explicitly below: a check that takes "the first rise at or after
(instant - 24h)" as the start of the solar day lands on the PREVIOUS day's rise
whenever the rise-to-rise interval is under 24 hours and the instant is shortly
after its own sunrise. The implementation uses the latest sunrise at or before
the instant, which is the definition.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from core.astrology import AstrologicalCalculator

SAN_FRANCISCO = (37.7749, -122.4194)
TOKYO = (35.68, 139.69)
SYDNEY = (-33.87, 151.21)
LONDON = (51.51, -0.13)
REYKJAVIK = (64.15, -21.94)  # high, but not polar

PACIFIC = ZoneInfo("America/Los_Angeles")
JST = ZoneInfo("Asia/Tokyo")
SYDNEY_TZ = ZoneInfo("Australia/Sydney")
LONDON_TZ = ZoneInfo("Europe/London")
REYKJAVIK_TZ = ZoneInfo("Atlantic/Reykjavik")

VARA_NAMES = [
    "Somavara (Monday)",
    "Mangalavara (Tuesday)",
    "Budhavara (Wednesday)",
    "Guruvara (Thursday)",
    "Sukravara (Friday)",
    "Sanivara (Saturday)",
    "Ravivara (Sunday)",
]
WEEKDAY_RULERS = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
CHALDEAN_ORDER = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]


@pytest.fixture(scope="module")
def calculator() -> AstrologicalCalculator:
    return AstrologicalCalculator()


def _hours(calculator: AstrologicalCalculator, moment: datetime, location: tuple[float, float]) -> dict:
    return calculator.calculate_exact_planetary_hours(moment, location)


def _sun_events(calculator: AstrologicalCalculator, moment: datetime, location: tuple[float, float]) -> dict:
    return calculator._sun_events_around(moment, location)


# ---------------------------------------------------------------------------
# the day is bracketed by the sunrises around the instant
# ---------------------------------------------------------------------------


def test_the_daytime_hours_are_measured_from_sunrise(calculator: AstrologicalCalculator) -> None:
    """At San Francisco the first day hour starts AT the sunrise.

    2026-10-20: sunrise 07:22 PDT, sunset 18:25 PDT, so the day is about
    eleven hours and each of its twelve hours is about 55 minutes.
    """
    events = _sun_events(calculator, datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC), SAN_FRANCISCO)
    sunrise = events["previous_sunrise"]
    assert sunrise.astimezone(PACIFIC).strftime("%Y-%m-%d %H:%M") == "2026-10-20 07:22"

    result = _hours(calculator, datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC), SAN_FRANCISCO)
    assert result["is_daytime"] is True
    # Noon is about four and a half hours after sunrise, so the sixth hour.
    assert result["hour_index"] == 6
    start = datetime.fromisoformat(result["start_time"])
    end = datetime.fromisoformat(result["end_time"])
    assert start <= datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC) < end
    # The day hours are about 55 minutes, not the 3-hour hours the old
    # next-sunrise anchor produced.
    assert 50 <= (end - start).total_seconds() / 60 <= 60


def test_the_night_hours_are_measured_from_the_sunset(calculator: AstrologicalCalculator) -> None:
    """After sunset the night part runs to the NEXT sunrise."""
    result = _hours(calculator, datetime(2026, 10, 20, 20, 0, tzinfo=PACIFIC), SAN_FRANCISCO)
    assert result["is_daytime"] is False
    start = datetime.fromisoformat(result["start_time"])
    end = datetime.fromisoformat(result["end_time"])
    assert start <= datetime(2026, 10, 20, 20, 0, tzinfo=PACIFIC) < end
    # The night is about thirteen hours, so its hours are about 65 minutes.
    assert 60 <= (end - start).total_seconds() / 60 <= 75


def test_the_day_ruler_before_sunrise_is_the_previous_day(calculator: AstrologicalCalculator) -> None:
    """An instant after local midnight but before sunrise belongs to yesterday.

    2026-10-20 03:00 PDT is before that day's 07:22 sunrise, so it is still
    inside the solar day that began on Monday 2026-10-19's sunrise, and the day
    ruler is Monday's (the Moon).
    """
    result = _hours(calculator, datetime(2026, 10, 20, 3, 0, tzinfo=PACIFIC), SAN_FRANCISCO)
    assert result["is_daytime"] is False
    assert result["day_planet"] == WEEKDAY_RULERS[0]  # Monday
    assert result["day_planet"] == "Moon"

    # An hour later, after the sunrise, the ruler is Tuesday's (Mars).
    later = _hours(calculator, datetime(2026, 10, 20, 8, 0, tzinfo=PACIFIC), SAN_FRANCISCO)
    assert later["day_planet"] == WEEKDAY_RULERS[1]  # Tuesday
    assert later["day_planet"] == "Mars"


def test_the_ruler_sequence_follows_the_chaldean_order(calculator: AstrologicalCalculator) -> None:
    """The day ruler starts the sequence and the night continues it."""
    result = _hours(calculator, datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC), SAN_FRANCISCO)
    start = CHALDEAN_ORDER.index(result["day_planet"])
    assert result["day_rulers"] == [CHALDEAN_ORDER[(start + i) % 7] for i in range(12)]
    assert result["night_rulers"] == [CHALDEAN_ORDER[(start + 12 + i) % 7] for i in range(12)]
    # The first night hour is the thirteenth of the sequence.
    assert result["night_rulers"][0] == CHALDEAN_ORDER[(start + 12) % 7]


def test_the_time_remaining_is_consistent_with_the_end(calculator: AstrologicalCalculator) -> None:
    """time_remaining_seconds must match the reported end_time."""
    moment = datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC)
    result = _hours(calculator, moment, SAN_FRANCISCO)
    end = datetime.fromisoformat(result["end_time"])
    assert result["time_remaining_seconds"] == int((end - moment).total_seconds())


# ---------------------------------------------------------------------------
# the spelling of the instant must not matter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("city", "location", "zone"),
    [
        ("SanFrancisco", SAN_FRANCISCO, PACIFIC),
        ("Tokyo", TOKYO, JST),
        ("Sydney", SYDNEY, SYDNEY_TZ),
        ("London", LONDON, LONDON_TZ),
    ],
)
def test_the_hour_does_not_depend_on_how_the_instant_is_spelled(
    calculator: AstrologicalCalculator,
    city: str,
    location: tuple[float, float],
    zone: ZoneInfo,
) -> None:
    """UTC-aware, naive-UTC, the location's zone and two far zones all agree."""
    moment_utc = datetime(2026, 6, 15, 4, 30, tzinfo=timezone.utc)
    spellings = [
        moment_utc,
        moment_utc.replace(tzinfo=None),
        moment_utc.astimezone(zone),
        moment_utc.astimezone(timezone(timedelta(hours=14))),
        moment_utc.astimezone(timezone(timedelta(hours=-11))),
    ]
    results = [_hours(calculator, spelling, location) for spelling in spellings]
    assert len({r["hour_index"] for r in results}) == 1, city
    assert len({r["current_planetary_hour"] for r in results}) == 1, city
    assert len({r["day_planet"] for r in results}) == 1, city
    assert len({r["is_daytime"] for r in results}) == 1, city


def test_a_high_but_not_polar_city(calculator: AstrologicalCalculator) -> None:
    """Reykjavik is high but not polar: it has a sunrise and a sunset.

    The date matters: at the June solstice the sun does not set at all there
    (the midnight sun), so there is no solar day to split and the polar
    fallback is the right answer. In October the day is a normal 64 degree
    one, with a sunrise at 08:32 and a sunset at 17:51 local.
    """
    result = _hours(calculator, datetime(2026, 10, 20, 12, 0, tzinfo=REYKJAVIK_TZ), REYKJAVIK)
    assert result["status"] == "success"
    assert result["is_daytime"] is True
    start = datetime.fromisoformat(result["start_time"])
    end = datetime.fromisoformat(result["end_time"])
    assert end > start


# ---------------------------------------------------------------------------
# the wheel
# ---------------------------------------------------------------------------


def test_the_wheel_slices_tile_the_solar_day(calculator: AstrologicalCalculator) -> None:
    """The 24 slices cover sunrise to the next sunrise with no gap."""
    from core.auspicious_timing import AuspiciousTiming

    engine = AuspiciousTiming(astrology_engine=calculator)
    moment = datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC)
    wheel = engine.get_timing_wheel_data(lat=37.7749, lon=-122.4194, target_dt=moment)
    slices = wheel["hourly_slices"]
    assert len(slices) == 24
    assert sum(1 for s in slices if s["period"] == "day") == 12
    assert sum(1 for s in slices if s["period"] == "night") == 12

    events = _sun_events(calculator, moment, SAN_FRANCISCO)
    first = datetime.fromisoformat(slices[0]["start_time"])
    last = datetime.fromisoformat(slices[-1]["end_time"])
    assert abs((first - events["previous_sunrise"]).total_seconds()) < 1.0
    assert abs((last - events["next_sunrise"]).total_seconds()) < 1.0

    # The slices are contiguous. The tolerance is there because the day part is
    # built as sunrise + (sunset - sunrise) / 12 * i while the night part
    # starts at the sunset itself, so the two meet with a float-division
    # rounding difference of a microsecond or so.
    for before, after in zip(slices, slices[1:]):
        gap = (datetime.fromisoformat(after["start_time"]) - datetime.fromisoformat(before["end_time"])).total_seconds()
        assert abs(gap) < 0.001, f"gap or overlap of {gap:.6f}s between {before} and {after}"


def test_the_wheel_marks_the_slice_containing_the_instant(calculator: AstrologicalCalculator) -> None:
    """Exactly one slice is current, and it is the one holding the instant."""
    from core.auspicious_timing import AuspiciousTiming

    engine = AuspiciousTiming(astrology_engine=calculator)
    for hour in (8, 12, 20):
        moment = datetime(2026, 10, 20, hour, 0, tzinfo=PACIFIC)
        wheel = engine.get_timing_wheel_data(lat=37.7749, lon=-122.4194, target_dt=moment)
        current = [s for s in wheel["hourly_slices"] if s["is_current"]]
        assert len(current) == 1, wheel["hourly_slices"]
        start = datetime.fromisoformat(current[0]["start_time"])
        end = datetime.fromisoformat(current[0]["end_time"])
        assert start <= moment < end


# ---------------------------------------------------------------------------
# internet_context
# ---------------------------------------------------------------------------


def test_internet_context_uses_the_day_planet_from_the_result(
    calculator: AstrologicalCalculator, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The day ruler must come from the engine, not from the civil weekday."""
    from core import internet_context

    seen: dict[str, object] = {}

    def fake_exact(self, dt, location):  # noqa: ANN001
        seen["dt"] = dt
        return {
            "status": "success",
            "current_planetary_hour": "Jupiter",
            "day_planet": "Moon",
            "hour_index": 3,
            "is_daytime": True,
        }

    monkeypatch.setattr("core.astrology.AstrologyEngine.calculate_exact_planetary_hours", fake_exact, raising=True)

    # 2026-08-23 is a SUNDAY, so the civil weekday of the instant would give
    # the Sun as the day ruler, while the engine says the solar day began on
    # Saturday and its ruler is the Moon. A caller that took the ruler from
    # the civil weekday would answer "Sun" here.
    hour, ruler = internet_context.get_planetary_hour(datetime(2026, 8, 23, 6, 0))
    assert hour == "Jupiter"
    assert ruler == "Moon", "the day ruler must come from the result's day_planet"
    # The instant handed to the engine must be aware and in UTC.
    assert seen["dt"].tzinfo is not None
    assert seen["dt"].utcoffset() == timedelta(0)


# ---------------------------------------------------------------------------
# the one case where a 24-hour look-back and the implementation differ
# ---------------------------------------------------------------------------


def test_an_instant_just_after_a_sunrise_is_in_the_day_part(
    calculator: AstrologicalCalculator,
) -> None:
    """Auckland 2026-07-29 19:21:41Z is 32 s AFTER that day's sunrise.

    A look-back that takes the first rise at or after (instant - 24h) as the
    day's start gets this wrong: Auckland's rise-to-rise interval is just under
    24 hours in July, so that marker lands after the true previous rise, the
    window spans two days, and the answer is "night". The definition is the
    latest sunrise at or before the instant, so the instant is in the DAY part.
    """
    auckland = (-36.85, 174.76)
    moment = datetime(2026, 7, 29, 19, 21, 41, tzinfo=timezone.utc)
    events = _sun_events(calculator, moment, auckland)
    delta = (moment - events["previous_sunrise"]).total_seconds()
    assert 0 < delta < 120, f"the fixture moved: {delta:.1f}s after the sunrise"

    result = _hours(calculator, moment, auckland)
    assert result["is_daytime"] is True
    assert result["hour_index"] == 1
    start = datetime.fromisoformat(result["start_time"])
    assert abs((start - events["previous_sunrise"]).total_seconds()) < 1.0


# ---------------------------------------------------------------------------
# PH-1b: the sun-event search must not drop one of two events in a UT day.
#
# When an event's time of day drifts EARLIER across 00:00 UT, two events of the
# same kind land in the same UT day (Fairbanks sunsets at 2026-12-02T00:00:40Z AND
# 2026-12-02T23:58:31Z). Bucketing the events by UT day and keeping one of
# them drops an event, so the surrounding solar day is missing a sunrise or a
# sunset. The search has to CHAIN: start before the instant and search again
# from just after each event found, because a forward search can step over an
# event that is only minutes away.
#
# The expected values are pasted CONSTANTS from an independent oracle;
# nothing is imported from docs/ at test time.
# ---------------------------------------------------------------------------

CHICAGO = (41.8781, -87.6298)
MEXICO_CITY = (19.4326, -99.1332)
FAIRBANKS = (64.8378, -147.7164)
DHAKA = (23.8103, 90.4125)
DELHI = (28.6139, 77.209)

# label, location, instant UTC, is_daytime, hour_index, ruler, day_planet,
# hour start, hour end, sunrise, sunset, next sunrise
LITERALS = [
    (
        "Chicago 2026-09-16T12:17:31Z",
        CHICAGO,
        "2026-09-16T12:17:31+00:00",
        True,
        1,
        "Mercury",
        "Mercury",
        "2026-09-16T11:31:35.821000+00:00",
        "2026-09-16T12:33:49.204000+00:00",
        "2026-09-16T11:31:35.821000+00:00",
        "2026-09-16T23:58:16.418000+00:00",
        "2026-09-17T11:32:37.882000+00:00",
    ),
    (
        "Chicago 2026-09-17T06:17:31Z",
        CHICAGO,
        "2026-09-17T06:17:31+00:00",
        False,
        7,
        "Mars",
        "Mercury",
        "2026-09-17T05:45:27.150000+00:00",
        "2026-09-17T06:43:18.939000+00:00",
        "2026-09-16T11:31:35.821000+00:00",
        "2026-09-16T23:58:16.418000+00:00",
        "2026-09-17T11:32:37.882000+00:00",
    ),
    (
        "MexicoCity 2026-11-08T18:17:31Z",
        MEXICO_CITY,
        "2026-11-08T18:17:31+00:00",
        True,
        6,
        "Jupiter",
        "Sun",
        "2026-11-08T17:23:35.545000+00:00",
        "2026-11-08T18:20:11.360000+00:00",
        "2026-11-08T12:40:36.466000+00:00",
        "2026-11-08T23:59:46.254000+00:00",
        "2026-11-09T12:41:07.505000+00:00",
    ),
    (
        "Fairbanks 2026-12-03T16:17:31Z",
        FAIRBANKS,
        "2026-12-03T16:17:31+00:00",
        False,
        11,
        "Moon",
        "Mercury",
        "2026-12-03T16:10:18.777000+00:00",
        "2026-12-03T17:47:29.461000+00:00",
        "2026-12-02T19:21:48.563000+00:00",
        "2026-12-02T23:58:31.939000+00:00",
        "2026-12-03T19:24:40.144000+00:00",
    ),
    (
        "Dhaka 2026-03-23T00:17:31Z",
        DHAKA,
        "2026-03-23T00:17:31+00:00",
        True,
        1,
        "Moon",
        "Moon",
        "2026-03-22T23:59:32.694000+00:00",
        "2026-03-23T01:00:28.699000+00:00",
        "2026-03-22T23:59:32.694000+00:00",
        "2026-03-23T12:10:44.754000+00:00",
        "2026-03-23T23:58:32.960000+00:00",
    ),
    (
        "Dhaka 2026-03-22T12:17:31Z",
        DHAKA,
        "2026-03-22T12:17:31+00:00",
        False,
        1,
        "Jupiter",
        "Sun",
        "2026-03-22T12:10:20.871000+00:00",
        "2026-03-22T13:09:26.857000+00:00",
        "2026-03-22T00:00:32.368000+00:00",
        "2026-03-22T12:10:20.871000+00:00",
        "2026-03-22T23:59:32.694000+00:00",
    ),
    (
        "Delhi 2026-05-15T20:00:00Z",
        DELHI,
        "2026-05-15T20:00:00+00:00",
        False,
        8,
        "Mars",
        "Venus",
        "2026-05-15T19:39:26.661000+00:00",
        "2026-05-15T20:31:30.614000+00:00",
        "2026-05-15T00:00:20.921000+00:00",
        "2026-05-15T13:34:58.992000+00:00",
        "2026-05-15T23:59:46.424000+00:00",
    ),
    (
        "Delhi 2026-05-15T04:37:56Z",
        DELHI,
        "2026-05-15T04:37:56+00:00",
        True,
        5,
        "Jupiter",
        "Venus",
        "2026-05-15T04:31:53.611000+00:00",
        "2026-05-15T05:39:46.784000+00:00",
        "2026-05-15T00:00:20.921000+00:00",
        "2026-05-15T13:34:58.992000+00:00",
        "2026-05-15T23:59:46.424000+00:00",
    ),
    (
        "Delhi 2026-05-16T00:30:00Z",
        DELHI,
        "2026-05-16T00:30:00+00:00",
        True,
        1,
        "Saturn",
        "Saturn",
        "2026-05-15T23:59:46.424000+00:00",
        "2026-05-16T01:07:45.496000+00:00",
        "2026-05-15T23:59:46.424000+00:00",
        "2026-05-16T13:35:35.284000+00:00",
        "2026-05-16T23:59:13.190000+00:00",
    ),
]

# city -> (lat, lon); the days on which an event crosses 00:00 UT
CROSSING_CITIES = {
    "Chicago": (CHICAGO, ("2026-09-14", "2026-09-19")),
    "MexicoCity": (MEXICO_CITY, ("2026-11-06", "2026-11-11")),
    "Dhaka": (DHAKA, ("2026-03-20", "2026-03-25")),
    "Delhi": (DELHI, ("2026-05-12", "2026-05-18")),
    "Fairbanks": (FAIRBANKS, ("2026-12-01", "2026-12-05")),
}
INSTANTS_OF_DAY = ("00:17:31", "06:17:31", "12:17:31", "18:17:31")


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _days(first: str, last: str):
    day = datetime.fromisoformat(first).date()
    end = datetime.fromisoformat(last).date()
    while day <= end:
        yield day
        day += timedelta(days=1)


@pytest.mark.parametrize(
    (
        "label",
        "location",
        "instant",
        "daytime",
        "hour",
        "ruler",
        "day_ruler",
        "start",
        "end",
        "sunrise",
        "sunset",
        "next_sunrise",
    ),
    [case for case in LITERALS],
    ids=[case[0] for case in LITERALS],
)
def test_exact_planetary_hours_at_the_crossing_cities(
    calculator: AstrologicalCalculator,
    label: str,
    location: tuple[float, float],
    instant: str,
    daytime: bool,
    hour: int,
    ruler: str,
    day_ruler: str,
    start: str,
    end: str,
    sunrise: str,
    sunset: str,
    next_sunrise: str,
) -> None:
    """The exact target matches the oracle where an event crosses 00:00 UT."""
    result = calculator.calculate_exact_planetary_hours(_instant(instant), location)
    assert result.get("status") == "success", f"{label}: {result}"
    assert result["is_daytime"] is daytime, label
    assert result["hour_index"] == hour, f"{label}: {result}"
    assert result["current_planetary_hour"] == ruler, label
    assert result["day_planet"] == day_ruler, label
    # The boundaries to the second: swisseph moves rise_trans by up to 0.4 s
    # depending on where the search starts.
    assert abs((datetime.fromisoformat(result["start_time"]) - _instant(start)).total_seconds()) < 1.0, label
    assert abs((datetime.fromisoformat(result["end_time"]) - _instant(end)).total_seconds()) < 1.0, label


@pytest.mark.parametrize(
    (
        "label",
        "location",
        "instant",
        "daytime",
        "hour",
        "ruler",
        "day_ruler",
        "start",
        "end",
        "sunrise",
        "sunset",
        "next_sunrise",
    ),
    [case for case in LITERALS],
    ids=[case[0] for case in LITERALS],
)
def test_sun_events_at_the_crossing_cities(
    calculator: AstrologicalCalculator,
    label: str,
    location: tuple[float, float],
    instant: str,
    daytime: bool,
    hour: int,
    ruler: str,
    day_ruler: str,
    start: str,
    end: str,
    sunrise: str,
    sunset: str,
    next_sunrise: str,
) -> None:
    """The bracketing events match the oracle, including the ones a day-bucket loses."""
    events = calculator.get_solar_day_sun_events(_instant(instant), location)
    assert events["sunrise"] is not None, label
    assert abs((events["sunrise"] - _instant(sunrise)).total_seconds()) < 1.0, f"{label}: {events['sunrise']}"
    assert abs((events["sunset"] - _instant(sunset)).total_seconds()) < 1.0, f"{label}: {events['sunset']}"
    assert (
        abs((events["next_sunrise"] - _instant(next_sunrise)).total_seconds()) < 1.0
    ), f"{label}: {events['next_sunrise']}"


@pytest.mark.parametrize("city", sorted(CROSSING_CITIES))
def test_the_solar_day_is_always_well_formed(calculator: AstrologicalCalculator, city: str) -> None:
    """The invariant over the days when an event crosses 00:00 UT.

    For every instant of every day in the window: the target succeeds, the
    instant lies inside the reported hour, the solar day is between 23 and 25
    hours long, and the sunrise precedes the sunset, which precedes the next
    sunrise.
    """
    location, (first_day, last_day) = CROSSING_CITIES[city]
    checked = 0
    for day in _days(first_day, last_day):
        for clock in INSTANTS_OF_DAY:
            moment = datetime.combine(day, datetime.strptime(clock, "%H:%M:%S").time(), tzinfo=timezone.utc)
            result = calculator.calculate_exact_planetary_hours(moment, location)
            assert result.get("status") == "success", f"{city} {moment.isoformat()}: {result}"
            start = datetime.fromisoformat(result["start_time"])
            end = datetime.fromisoformat(result["end_time"])
            assert start <= moment < end, f"{city} {moment.isoformat()}: {start}..{end}"
            events = calculator.get_solar_day_sun_events(moment, location)
            sunrise, sunset, next_sunrise = events["sunrise"], events["sunset"], events["next_sunrise"]
            assert sunrise is not None and sunset is not None and next_sunrise is not None, f"{city} {moment}"
            assert sunrise < sunset < next_sunrise, f"{city} {moment}: {sunrise} {sunset} {next_sunrise}"
            length = (next_sunrise - sunrise).total_seconds() / 3600.0
            assert 23.0 < length < 25.0, f"{city} {moment}: the solar day is {length:.2f} h"
            checked += 1
    assert checked == len(list(_days(first_day, last_day))) * len(
        INSTANTS_OF_DAY
    ), f"only {checked} instants were checked"


@pytest.mark.parametrize("city", sorted(CROSSING_CITIES))
def test_the_wheel_tiles_and_marks_the_current_slice(calculator: AstrologicalCalculator, city: str) -> None:
    """The wheel's 24 slices tile the solar day and mark the instant's slice."""
    from core.auspicious_timing import AuspiciousTiming

    location, (first_day, last_day) = CROSSING_CITIES[city]
    engine = AuspiciousTiming(astrology_engine=calculator)
    for day in _days(first_day, last_day):
        for clock in INSTANTS_OF_DAY:
            moment = datetime.combine(day, datetime.strptime(clock, "%H:%M:%S").time(), tzinfo=timezone.utc)
            wheel = engine.get_timing_wheel_data(lat=location[0], lon=location[1], target_dt=moment)
            slices = wheel["hourly_slices"]
            assert len(slices) == 24, f"{city} {moment}: {len(slices)} slices"
            current = [s for s in slices if s["is_current"]]
            assert len(current) == 1, f"{city} {moment}: {len(current)} current slices"
            start = datetime.fromisoformat(current[0]["start_time"])
            end = datetime.fromisoformat(current[0]["end_time"])
            assert start <= moment < end, f"{city} {moment}: {start}..{end}"
            for before, after in zip(slices, slices[1:]):
                gap = (
                    datetime.fromisoformat(after["start_time"]) - datetime.fromisoformat(before["end_time"])
                ).total_seconds()
                assert abs(gap) < 0.001, f"{city} {moment}: gap {gap:.6f}s"
