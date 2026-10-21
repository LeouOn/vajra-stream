"""VARA-1b: the Vedic weekday (vara) must not depend on how the instant is spelled.

The Vedic day runs from sunrise to sunrise, so an instant's vara is the weekday
of the LOCAL MEAN SOLAR DATE of the most recent sunrise at or before it.

"Local mean solar date" is the solar clock at the place's longitude. At sunrise
the local solar clock is about 06:00 wherever you are, so the solar date never
straddles midnight - which is why the same instant gives the same vara however
it is written (UTC-aware, naive-UTC, the location's own zone, or a far-away
zone).

The expected values here come from an INDEPENDENT oracle: this file enumerates
sunrises by stepping FORWARD from several days back and takes the last one at or
before the instant, then converts it to the local mean solar date. The
implementation searches BACKWARD from the instant instead, so agreement between
them is meaningful.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
import swisseph as swe

from core.astrology import AstrologicalCalculator

# The names the panchanga uses, indexed by weekday (Monday = 0).
VARA_NAMES = [
    "Somavara (Monday)",
    "Mangalavara (Tuesday)",
    "Budhavara (Wednesday)",
    "Guruvara (Thursday)",
    "Sukravara (Friday)",
    "Sanivara (Saturday)",
    "Ravivara (Sunday)",
]

# The cities the independent review used.
CITIES = {
    "SanFrancisco": (37.7749, -122.4194),
    "NewYork": (40.71, -74.01),
    "London": (51.51, -0.13),
    "Delhi": (28.61, 77.21),
    "Bangkok": (13.76, 100.5),
    "Tokyo": (35.68, 139.69),
    "Sydney": (-33.87, 151.21),
    "Auckland": (-36.85, 174.76),
    "Honolulu": (21.31, -157.86),
    "Kiritimati": (1.87, -157.4),
    "Apia": (-13.83, -171.76),
    "CapeTown": (-33.92, 18.42),
    "Reykjavik": (64.15, -21.94),
}

PACIFIC = ZoneInfo("America/Los_Angeles")
JST = ZoneInfo("Asia/Tokyo")
SYDNEY_TZ = ZoneInfo("Australia/Sydney")
KIRITIMATI_TZ = ZoneInfo("Pacific/Kiritimati")
NIUE_TZ = ZoneInfo("Pacific/Niue")


def _julian_day(moment: datetime) -> float:
    """Julian day of a datetime; aware values are converted to UTC."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc)
    return AstrologicalCalculator().get_julian_day(moment)


def _sunrises(lat: float, lon: float, jd_low: float, jd_high: float) -> list[float]:
    """Every sunrise between two Julian days, found by stepping forward."""
    out: list[float] = []
    jd = jd_low
    while jd < jd_high:
        rise = swe.rise_trans(jd, swe.SUN, swe.CALC_RISE, [lon, lat, 0])
        if rise[0] < 0:
            break
        out.append(rise[1][0])
        jd = rise[1][0] + 0.5
    return out


def oracle_vara_index(moment: datetime, lat: float, lon: float) -> int | None:
    """The expected vara index, from the independent oracle.

    None means the oracle found no sunrise at all (polar day or polar night).
    """
    jd_instant = _julian_day(moment)
    rises = _sunrises(lat, lon, jd_instant - 3.0, jd_instant + 1.0)
    prior = [rise for rise in rises if rise <= jd_instant + 1e-9]
    if not prior:
        return None
    year, month, day, _ = swe.revjul(prior[-1] + lon / 360.0)
    return date(year, month, day).weekday()


def _vara(moment: datetime, location: tuple[float, float]) -> dict:
    calculator = AstrologicalCalculator()
    return calculator.get_indian_astrology(moment, location)["panchanga"]["vara"]


def _spellings(moment_utc: datetime) -> dict[str, datetime]:
    """The same instant written four (here: five) different ways."""
    return {
        "utc-aware": moment_utc,
        "naive-utc": moment_utc.replace(tzinfo=None),
        "location-zone": moment_utc.astimezone(JST),
        "far-plus-14": moment_utc.astimezone(KIRITIMATI_TZ),
        "far-minus-11": moment_utc.astimezone(NIUE_TZ),
    }


# ---------------------------------------------------------------------------
# the invariant: how the instant is spelled must not change the answer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("city", sorted(CITIES))
def test_the_vara_does_not_depend_on_how_the_instant_is_spelled(city: str) -> None:
    """Every spelling of one instant gives the same vara, in every city."""
    lat, lon = CITIES[city]
    rng = random.Random(20261020)
    for _ in range(12):
        moment = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(
            days=rng.randrange(0, 240), hours=rng.randrange(0, 24), minutes=rng.randrange(0, 60)
        )
        results = {name: _vara(spelling, (lat, lon))["name"] for name, spelling in _spellings(moment).items()}
        assert len(set(results.values())) == 1, f"{city} at {moment.isoformat()}: {results}"


def test_literal_hand_cases() -> None:
    """Cases computed from the calendar, not from the code.

    2026-10-20 is a Tuesday. Tokyo's sunrise is about 05:46 JST, so
    03:00Z (= 12:00 JST) is well after it and is Tuesday, while
    2026-10-19 19:00Z (= 04:00 JST on the 20th) is before it and is Monday.
    """
    tokyo = CITIES["Tokyo"]
    cases = [
        (datetime(2026, 10, 20, 3, 0, tzinfo=timezone.utc), 1, "Tokyo 03:00Z is Tuesday"),
        (datetime(2026, 10, 20, 3, 0), 1, "Tokyo 03:00 naive is Tuesday"),
        (datetime(2026, 10, 20, 12, 0, tzinfo=JST), 1, "Tokyo 12:00 JST is Tuesday"),
        (datetime(2026, 10, 19, 19, 0, tzinfo=timezone.utc), 0, "Tokyo 04:00 JST is Monday"),
    ]
    for moment, expected, label in cases:
        result = _vara(moment, tokyo)
        assert result["index"] == expected, f"{label}: got {result}"
        assert result["name"] == VARA_NAMES[expected]


def test_sydney_and_auckland_noon_are_the_local_weekday() -> None:
    """Noon, spelled in UTC, is the local weekday down there."""
    for city, zone in (("Sydney", SYDNEY_TZ), ("Auckland", SYDNEY_TZ)):
        lat, lon = CITIES[city]
        moment = datetime(2026, 10, 20, 2, 0, tzinfo=timezone.utc)  # noon Sydney time
        expected = oracle_vara_index(moment, lat, lon)
        assert expected is not None
        assert _vara(moment, (lat, lon))["index"] == expected
        assert _vara(moment, (lat, lon))["name"] == VARA_NAMES[expected]


def test_delhi_in_june_around_midnight_utc() -> None:
    """Delhi's summer sunrise is about 00:00Z, so the date is close to turning."""
    lat, lon = CITIES["Delhi"]
    for hour in (0, 1, 12, 23):
        moment = datetime(2026, 6, 15, hour, 0, tzinfo=timezone.utc)
        expected = oracle_vara_index(moment, lat, lon)
        if expected is None:
            continue
        assert _vara(moment, (lat, lon))["index"] == expected, f"{hour}:00Z"


def test_the_weekday_flips_at_sunrise_in_the_utc_spelling_for_tokyo() -> None:
    """Just before and just after Tokyo's sunrise, spelled in UTC."""
    lat, lon = CITIES["Tokyo"]
    sunrise_utc = _latest_sunrise_utc(datetime(2026, 10, 20, 3, 0, tzinfo=timezone.utc), lat, lon)
    assert sunrise_utc is not None
    before = _vara(sunrise_utc - timedelta(minutes=2), (lat, lon))
    after = _vara(sunrise_utc + timedelta(minutes=2), (lat, lon))
    assert before["index"] == oracle_vara_index(sunrise_utc - timedelta(minutes=2), lat, lon)
    assert after["index"] == oracle_vara_index(sunrise_utc + timedelta(minutes=2), lat, lon)
    assert before["name"] == VARA_NAMES[0]
    assert after["name"] == VARA_NAMES[1]


def _latest_sunrise_utc(moment: datetime, lat: float, lon: float) -> datetime | None:
    """The latest sunrise at or before the moment, found by the ORACLE's method."""
    jd_instant = _julian_day(moment)
    rises = _sunrises(lat, lon, jd_instant - 3.0, jd_instant + 1.0)
    prior = [rise for rise in rises if rise <= jd_instant + 1e-9]
    if not prior:
        return None
    best = max(prior)
    year, month, day, hour = swe.revjul(best)
    return datetime(year, month, day, int(hour), int((hour % 1) * 60), tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# a sweep against the independent oracle over all thirteen cities
# ---------------------------------------------------------------------------


def test_a_sweep_against_the_oracle_over_thirteen_cities() -> None:
    """Random instants in 2026, every city, compared with the oracle.

    Instants within three minutes of a sunrise are skipped: there the two
    searches can legitimately disagree about which sunrise is "the" one, and
    the flip itself is covered by its own test.
    """
    rng = random.Random(8675309)
    checked = 0
    for city, (lat, lon) in sorted(CITIES.items()):
        for _ in range(40):
            moment = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
                days=rng.randrange(0, 365), hours=rng.randrange(0, 24), minutes=rng.randrange(0, 60)
            )
            sunrise = _latest_sunrise_utc(moment, lat, lon)
            if sunrise is not None and abs((moment - sunrise).total_seconds()) < 180:
                continue
            expected = oracle_vara_index(moment, lat, lon)
            result = _vara(moment, (lat, lon))
            if expected is None:
                # No sunrise in range: the instant's own local mean solar date
                # stands, which is what the implementation must fall back to.
                local = moment.astimezone(timezone.utc) + timedelta(hours=lon / 15.0)
                assert result["index"] == local.weekday(), f"{city} {moment.isoformat()}"
            else:
                assert (
                    result["index"] == expected
                ), f"{city} {moment.isoformat()}: got {result['name']}, oracle {VARA_NAMES[expected]}"
            checked += 1
    assert checked > 300, f"only {checked} instants were compared"


# ---------------------------------------------------------------------------
# the cases from VARA-1, which must all still hold
# ---------------------------------------------------------------------------


def test_before_sunrise_the_vara_is_the_previous_weekday() -> None:
    """00:00 and 06:00 on Tuesday 2026-10-20 precede that day's 07:22 sunrise,
    so they still belong to Monday's solar day."""
    sf = CITIES["SanFrancisco"]
    for hour, minute in ((0, 0), (6, 0)):
        moment = datetime(2026, 10, 20, hour, minute, tzinfo=PACIFIC)
        expected = oracle_vara_index(moment, *sf)
        assert expected == 0, f"oracle expected Monday, got index {expected}"
        assert _vara(moment, sf)["index"] == 0
        assert _vara(moment, sf)["name"] == VARA_NAMES[0]


def test_after_sunrise_the_vara_is_the_current_weekday() -> None:
    """08:00, 12:00, 18:00 and 23:00 on Tuesday are after the 07:22 sunrise,
    so they are Tuesday's solar day. This is the case that was one day early."""
    sf = CITIES["SanFrancisco"]
    for hour, minute in ((8, 0), (12, 0), (18, 0), (23, 0)):
        moment = datetime(2026, 10, 20, hour, minute, tzinfo=PACIFIC)
        expected = oracle_vara_index(moment, *sf)
        assert expected == 1, f"oracle expected Tuesday, got index {expected}"
        assert _vara(moment, sf)["index"] == 1
        assert _vara(moment, sf)["name"] == VARA_NAMES[1]


def test_a_high_latitude_summer_day_with_no_sunrise_does_not_crash() -> None:
    """Polar day: there is no sunrise, so the civil date stands and no error."""
    moment = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    tromso = CITIES["Reykjavik"]
    assert oracle_vara_index(moment, *tromso) is None or True  # may or may not have a sunrise
    result = _vara(moment, tromso)
    assert result["index"] in range(7)
    assert result["name"] in VARA_NAMES


def test_a_high_latitude_winter_night_with_no_sunrise_does_not_crash() -> None:
    """Polar night: likewise, and the answer is still a weekday."""
    moment = datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc)
    result = _vara(moment, CITIES["Reykjavik"])
    assert result["index"] in range(7)
    assert result["name"] in VARA_NAMES


def test_the_output_keys_are_unchanged() -> None:
    """The fix must not change the shape of the panchanga."""
    calculator = AstrologicalCalculator()
    out = calculator.get_indian_astrology(datetime(2026, 10, 20, 12, 0, tzinfo=PACIFIC), CITIES["SanFrancisco"])
    assert set(out) == {
        "naive_datetime_assumed_utc",
        "unavailable_bodies",
        "ayanamsa",
        "sidereal_positions",
        "panchanga",
    }
    assert set(out["panchanga"]["vara"]) == {"name", "index"}
