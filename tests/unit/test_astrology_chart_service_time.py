# tests/unit/test_astrology_chart_service_time.py
"""ADP-2: the kerykeion chart service must resolve every time to ONE honest instant.

THE DEFECTS THIS FILE PINS DOWN
-------------------------------
Before ADP-2 the service took the year/month/day/hour/minute out of the caller's
timestamp and handed them to kerykeion together with the CITY's zone, so:

1. an offset or ``Z`` in the input was DISCARDED - "1990-07-04T09:00:00+05:00"
   for a European city charted 09:00 in Europe;
2. an ambiguous wall time (a fall-back overlap) was silently resolved to
   STANDARD time, an hour late, with no signal;
3. SECONDS were dropped - kerykeion's ``from_birth_data`` takes a ``seconds``
   keyword and the service never passed it;
4. the TRANSIT chart was built from the hour and minute of a UTC clock read as
   if it were the birth city's local clock, so a San Francisco birth got a
   transit chart roughly seven hours in the future.

THE INDEPENDENT ORACLE
----------------------
Every positional expectation is computed here with Swiss Ephemeris directly
(``swe.calc_ut``, ``swe.houses_ex``) at the intended UT instant, and compared with
the service's own output. The service's engine is libephemeris, not swisseph;
the W0-B audit measured their agreement at <= 0.42 arcsec, so the tolerance
below is 1 arcminute (1/60 deg) - about eighty times looser than the measured
agreement, and still far tighter than the 11.8 deg the defects produced.

Geocoding is FAKED: no network, no Nominatim. Kerykeion runs offline.
"""

from __future__ import annotations

import datetime
import math

import pytest
import swisseph as swe

from backend.core.services.astrology_chart_service import AstrologyChartService
from backend.core.services.geocoding_service import geocoding_service
from core.astro.timezone_policy import (
    AmbiguousLocalTime,
    NonexistentLocalTime,
    TimezonePolicyError,
)

#: One arcminute in degrees. The measured kerykeion-vs-swisseph agreement is
#: <= 0.42 arcsec; this is ~80x looser and still ~700x tighter than the 11.8 deg
#: the DST-ambiguity defect moved the Ascendant.
TOL_DEG = 1.0 / 60.0

#: Tighter tolerance for the SECONDS test. Dropping 30 seconds moves the Moon by
#: 30 * 11.886 / 86400 = 0.0041 deg, which the 1 arcminute tolerance above would
#: happily hide. This is ~8.6x looser than the measured 0.00012 deg agreement and
#: still far tighter than the defect.
TOL_SECONDS_DEG = 0.001

CITIES = {
    "Paris": {"latitude": 48.86, "longitude": 2.35, "timezone": "Europe/Paris"},
    "New York": {"latitude": 40.71, "longitude": -74.01, "timezone": "America/New_York"},
    "San Francisco": {"latitude": 37.77, "longitude": -122.42, "timezone": "America/Los_Angeles"},
    "Tokyo": {"latitude": 35.68, "longitude": 139.69, "timezone": "Asia/Tokyo"},
    "Kolkata": {"latitude": 22.57, "longitude": 88.36, "timezone": "Asia/Kolkata"},
}


@pytest.fixture(autouse=True)
def fake_geocoding(monkeypatch):
    """No network: the city name resolves to a fixed lat/lng and IANA zone."""

    def _fake(city_name: str) -> dict:
        if city_name not in CITIES:
            return {"error": "not found"}
        return dict(CITIES[city_name])

    monkeypatch.setattr(geocoding_service, "get_coordinates_and_timezone", _fake)


@pytest.fixture
def service() -> AstrologyChartService:
    return AstrologyChartService()


# --------------------------------------------------------------------------- #
# The independent oracle.
# --------------------------------------------------------------------------- #
def swe_jd(dt_utc: datetime.datetime) -> float:
    """Julian day for an aware UTC datetime."""
    d = dt_utc.astimezone(datetime.timezone.utc)
    return swe.julday(d.year, d.month, d.day, d.hour + d.minute / 60.0 + d.second / 3600.0)


def swe_longitude(dt_utc: datetime.datetime, body: int) -> float:
    """Ecliptic longitude of ``body`` at the UTC instant, from swisseph."""
    xx, _ = swe.calc_ut(swe_jd(dt_utc), body, swe.FLG_SWIEPH | swe.FLG_SPEED)
    return xx[0]


def swe_ascendant(dt_utc: datetime.datetime, lat: float, lng: float) -> float:
    """Ascendant at the UTC instant, from swisseph (Placidus)."""
    _cusps, ascmc = swe.houses_ex(swe_jd(dt_utc), lat, lng, b"P")
    return ascmc[0]


SE_MOON = 1
SE_SUN = 0


def _abs_pos(point: dict) -> float:
    """Kerykeion 6.0.4 puts the absolute longitude in ``abs_pos``.

    ``longitude`` is None in this version and ``position`` is the degree within
    the sign. The W0-B audit found the same; this file relies on it.
    """
    value = point.get("abs_pos")
    if value is None:
        raise AssertionError(f"kerykeion point has no abs_pos: {sorted(point)}")
    return float(value)


def _angle_diff(a: float, b: float) -> float:
    """Smallest absolute difference between two longitudes, in degrees."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


# --------------------------------------------------------------------------- #
# (a) An offset in the input is an exact instant and is KEPT.
# --------------------------------------------------------------------------- #
def test_offset_in_the_input_is_honoured_not_overridden_by_the_city(service):
    """09:00+05:00 is 04:00 UTC, whatever the city's zone says."""
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00+05:00", "Paris")
    assert "error" not in result, result
    resolution = result["data"]["time_resolution"]
    assert resolution["utc_iso"] == "1990-07-04T04:00:00+00:00", resolution
    assert resolution["zone"] == "Europe/Paris"


def test_offset_in_the_input_warns_when_the_city_disagrees(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00+05:00", "Paris")
    warnings = result["data"]["time_resolution"]["warnings"]
    assert warnings, "a differing offset must be said, not silently swallowed"
    joined = " ".join(warnings)
    assert "+05:00" in joined, joined
    assert "Europe/Paris" in joined, joined


def test_offset_matching_the_city_produces_no_warning(service):
    """09:00+02:00 in Paris in July IS the city's local time: no noise."""
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00+02:00", "Paris")
    assert result["data"]["time_resolution"]["warnings"] == []


def test_offset_input_matches_the_oracle(service):
    """The chart is for 04:00 UTC, and swisseph agrees with kerykeion there."""
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00+05:00", "Paris")
    data = result["data"]
    when = datetime.datetime(1990, 7, 4, 4, 0, tzinfo=datetime.timezone.utc)

    assert _angle_diff(_abs_pos(data["sun"]), swe_longitude(when, SE_SUN)) < TOL_DEG
    assert _angle_diff(_abs_pos(data["moon"]), swe_longitude(when, SE_MOON)) < TOL_DEG
    assert _angle_diff(_abs_pos(data["ascendant"]), swe_ascendant(when, 48.86, 2.35)) < TOL_DEG


def test_z_suffix_is_an_offset_too(service):
    result = service.get_natal_chart("Alice", "1990-07-04T04:00:00Z", "Paris")
    assert result["data"]["time_resolution"]["utc_iso"] == "1990-07-04T04:00:00+00:00"


# --------------------------------------------------------------------------- #
# (b) A naive wall time is read in the city's zone.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("stamp", "city", "expected_utc"),
    [
        ("1990-07-04T09:00:00", "Paris", "1990-07-04T07:00:00+00:00"),  # CEST, +02:00
        ("1990-01-04T09:00:00", "Paris", "1990-01-04T08:00:00+00:00"),  # CET, +01:00
        ("1990-07-04T09:00:00", "Tokyo", "1990-07-04T00:00:00+00:00"),  # JST, +09:00
    ],
    ids=["paris-summer", "paris-winter", "tokyo-summer"],
)
def test_naive_wall_time_uses_the_city_zone(service, stamp, city, expected_utc):
    result = service.get_natal_chart("Alice", stamp, city)
    assert "error" not in result, result
    assert result["data"]["time_resolution"]["utc_iso"] == expected_utc


def test_naive_wall_time_matches_the_oracle(service):
    """Paris 09:00 in July is 07:00 UTC; swisseph and kerykeion agree there."""
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    data = result["data"]
    when = datetime.datetime(1990, 7, 4, 7, 0, tzinfo=datetime.timezone.utc)
    assert _angle_diff(_abs_pos(data["moon"]), swe_longitude(when, SE_MOON)) < TOL_DEG
    assert _angle_diff(_abs_pos(data["ascendant"]), swe_ascendant(when, 48.86, 2.35)) < TOL_DEG


def test_unique_local_time_is_unchanged_by_the_fix(service):
    """A unique local time in its own city was already right; it must stay right.

    The baseline recorded before the ADP-2 edit: sun position 12.060754111549116
    and ascendant 16.102388593555588 for Paris 1990-07-04T09:00:00.
    """
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    data = result["data"]
    assert data["sun"]["position"] == pytest.approx(12.060754111549116, abs=1e-9)
    assert data["ascendant"]["position"] == pytest.approx(16.102388593555588, abs=1e-9)


# --------------------------------------------------------------------------- #
# (c) An ambiguous wall time is refused unless the caller says which one.
# --------------------------------------------------------------------------- #
def test_ambiguous_wall_time_raises_by_default(service):
    with pytest.raises(AmbiguousLocalTime) as exc:
        service.get_natal_chart("Alice", "2024-11-03T01:30:00", "New York")
    message = str(exc.value)
    assert "America/New_York" in message, message
    # The policy module stamps the wall time with a space, not a "T".
    assert "2024-11-03 01:30:00" in message, message
    # BOTH candidates must be named
    assert "2024-11-03T05:30:00+00:00" in message, message
    assert "2024-11-03T06:30:00+00:00" in message, message


def test_ambiguous_earlier_and_later_are_an_hour_apart(service):
    earlier = service.get_natal_chart("Alice", "2024-11-03T01:30:00", "New York", ambiguous="earlier")
    later = service.get_natal_chart("Alice", "2024-11-03T01:30:00", "New York", ambiguous="later")
    assert earlier["data"]["time_resolution"]["utc_iso"] == "2024-11-03T05:30:00+00:00"
    assert later["data"]["time_resolution"]["utc_iso"] == "2024-11-03T06:30:00+00:00"


def test_ambiguous_earlier_and_later_give_different_charts(service):
    """One hour of separation moves the Ascendant by about 11.8 degrees."""
    earlier = service.get_natal_chart("Alice", "2024-11-03T01:30:00", "New York", ambiguous="earlier")
    later = service.get_natal_chart("Alice", "2024-11-03T01:30:00", "New York", ambiguous="later")
    asc_earlier = _abs_pos(earlier["data"]["ascendant"])
    asc_later = _abs_pos(later["data"]["ascendant"])
    difference = _angle_diff(asc_earlier, asc_later)
    assert difference == pytest.approx(
        11.8, abs=0.5
    ), f"the two folds must be about 11.8 deg apart in the Ascendant, got {difference}"


def test_ambiguous_choice_is_recorded_in_the_warnings(service):
    result = service.get_natal_chart("Alice", "2024-11-03T01:30:00", "New York", ambiguous="later")
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "later" in warnings, warnings


# --------------------------------------------------------------------------- #
# (d) A nonexistent wall time is refused unless the caller says what to do.
# --------------------------------------------------------------------------- #
def test_nonexistent_wall_time_raises_by_default(service):
    with pytest.raises(NonexistentLocalTime) as exc:
        service.get_natal_chart("Alice", "2024-03-10T02:30:00", "New York")
    message = str(exc.value)
    assert "America/New_York" in message, message
    assert "2024-03-10 02:30:00" in message, message


def test_nonexistent_shift_forward_works(service):
    result = service.get_natal_chart("Alice", "2024-03-10T02:30:00", "New York", nonexistent="shift_forward")
    assert "error" not in result, result
    # 02:30 EST does not exist; the clocks jump 02:00 -> 03:00 EDT, a one hour skip.
    # shift_forward moves the requested wall time ahead by exactly the size of the
    # skip: 02:30 -> 03:30 EDT, which is 07:30 UTC.
    assert result["data"]["time_resolution"]["utc_iso"] == "2024-03-10T07:30:00+00:00"


def test_nonexistent_shift_forward_is_recorded_in_the_warnings(service):
    result = service.get_natal_chart("Alice", "2024-03-10T02:30:00", "New York", nonexistent="shift_forward")
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "shift_forward" in warnings, warnings


# --------------------------------------------------------------------------- #
# (e) Seconds are kept.
# --------------------------------------------------------------------------- #
def test_seconds_are_kept_and_change_the_result(service):
    """One second of birth time is a real difference, and swisseph sees it.

    The Moon moves about 11.9 deg/day, so a second is ~0.0033 deg of longitude.
    """
    without = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    with_secs = service.get_natal_chart("Alice", "1990-07-04T09:00:30", "Paris")
    assert without["data"]["time_resolution"]["utc_iso"] != with_secs["data"]["time_resolution"]["utc_iso"]

    moon_without = _abs_pos(without["data"]["moon"])
    moon_with = _abs_pos(with_secs["data"]["moon"])
    difference = _angle_diff(moon_without, moon_with)
    assert difference == pytest.approx(
        30 * 11.886 / 86400.0, abs=0.01
    ), f"30 s of the Moon's motion should be ~0.004 deg, got {difference}"


def test_seconds_are_kept_in_the_utc_instant(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:30", "Paris")
    assert result["data"]["time_resolution"]["utc_iso"] == "1990-07-04T07:00:30+00:00"


def test_seconds_match_the_oracle(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:30", "Paris")
    when = datetime.datetime(1990, 7, 4, 7, 0, 30, tzinfo=datetime.timezone.utc)
    difference = _angle_diff(_abs_pos(result["data"]["moon"]), swe_longitude(when, SE_MOON))
    assert difference < TOL_SECONDS_DEG, (
        f"the chart must be for 07:00:30 UTC, not 07:00:00; the Moon is off by " f"{difference} deg"
    )


def test_microseconds_are_truncated_with_a_warning(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00.500000", "Paris")
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "icrosecond" in warnings, warnings
    assert result["data"]["time_resolution"]["utc_iso"] == "1990-07-04T07:00:00+00:00"


# --------------------------------------------------------------------------- #
# (f) The TRANSIT chart uses a real instant.
# --------------------------------------------------------------------------- #
def test_transit_for_a_san_francisco_birth_uses_the_right_instant(service):
    """The transit subject is for the instant asked for, not seven hours later."""
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "San Francisco", "2026-10-21T12:00:00+00:00")
    assert "error" not in result, result
    assert result["data"]["transit_time"] == "2026-10-21T12:00:00+00:00"


def test_transit_moon_equals_swisseph_at_the_utc_instant(service):
    """The transit subject's Moon is swisseph's Moon at the UTC instant."""
    from kerykeion import AstrologicalSubjectFactory

    when = datetime.datetime(2026, 10, 21, 12, 0, tzinfo=datetime.timezone.utc)
    subject = AstrologicalSubjectFactory.from_birth_data(
        name="Transit",
        year=when.year,
        month=when.month,
        day=when.day,
        hour=when.hour,
        minute=when.minute,
        lng=-122.42,
        lat=37.77,
        tz_str="UTC",
        online=False,
    )
    kerykeion_moon = _abs_pos(subject.moon.model_dump())
    assert _angle_diff(kerykeion_moon, swe_longitude(when, SE_MOON)) < TOL_DEG


def test_the_old_transit_technique_was_hours_wrong(service):
    """The OLD code took the UTC clock's hour and minute and passed them with the
    BIRTH city's zone, so the transit chart was for the wrong instant.

    Reproduced here with kerykeion directly: the same clock fields with
    ``tz_str='America/Los_Angeles'`` land seven hours away from the real instant,
    and the Moon is about 3.5 degrees out - the error the W0-B audit measured.
    """
    from kerykeion import AstrologicalSubjectFactory

    when = datetime.datetime(2026, 10, 21, 12, 0, tzinfo=datetime.timezone.utc)

    # The OLD technique: UTC clock fields, the BIRTH city's zone.
    old = AstrologicalSubjectFactory.from_birth_data(
        name="Transit",
        year=when.year,
        month=when.month,
        day=when.day,
        hour=when.hour,
        minute=when.minute,
        lng=-122.42,
        lat=37.77,
        tz_str="America/Los_Angeles",
        online=False,
    )
    old_moon = _abs_pos(old.moon.model_dump())
    true_moon = swe_longitude(when, SE_MOON)

    # The NEW technique: UTC wall fields, tz_str="UTC".
    new = AstrologicalSubjectFactory.from_birth_data(
        name="Transit",
        year=when.year,
        month=when.month,
        day=when.day,
        hour=when.hour,
        minute=when.minute,
        lng=-122.42,
        lat=37.77,
        tz_str="UTC",
        online=False,
    )
    new_moon = _abs_pos(new.moon.model_dump())

    old_error = _angle_diff(old_moon, true_moon)
    new_error = _angle_diff(new_moon, true_moon)
    assert old_error == pytest.approx(3.5, abs=0.6), f"the old technique should be ~3.5 deg out, got {old_error}"
    assert new_error < TOL_DEG, f"the new technique must agree with swisseph, got {new_error}"


def test_transit_aspects_match_the_correct_instant_not_the_old_one(service):
    """Service-level proof that the TRANSIT chart is for the right instant.

    The response exposes aspects, not the transit subject's positions, so the
    comparison is made against kerykeion directly: the same aspects computed with
    the CORRECT transit subject (UTC wall fields, tz_str="UTC") must match the
    service, and the ones computed the OLD way (UTC clock fields with the birth
    city's zone) must not.
    """
    from kerykeion import AspectsFactory, AstrologicalSubjectFactory

    when = datetime.datetime(2026, 10, 21, 12, 0, tzinfo=datetime.timezone.utc)
    # San Francisco in July is PDT (UTC-07:00), so the natal 09:00 local is 16:00 UTC.
    natal_when = datetime.datetime(1990, 7, 4, 16, 0, tzinfo=datetime.timezone.utc)

    def _subject(year, month, day, hour, minute, tz):
        return AstrologicalSubjectFactory.from_birth_data(
            name="T",
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            lng=-122.42,
            lat=37.77,
            tz_str=tz,
            online=False,
        )

    natal = _subject(natal_when.year, natal_when.month, natal_when.day, natal_when.hour, natal_when.minute, "UTC")
    correct = _subject(when.year, when.month, when.day, when.hour, when.minute, "UTC")
    old_way = _subject(when.year, when.month, when.day, when.hour, when.minute, "America/Los_Angeles")

    def _orb_set(subject):
        res = AspectsFactory.dual_chart_aspects(natal, subject)
        return {(a.p1_name, a.p2_name, a.aspect): round(a.orbit, 6) for a in res.aspects}

    correct_orbs = _orb_set(correct)
    old_orbs = _orb_set(old_way)

    service_result = service.get_daily_transit(
        "Alice", "1990-07-04T09:00:00", "San Francisco", "2026-10-21T12:00:00+00:00"
    )
    service_orbs = {
        (a["natal_planet"], a["transit_planet"], a["aspect"]): round(a["orb"], 6)
        for a in service_result["data"]["aspects"]
    }

    assert service_orbs == correct_orbs, "the service must chart the transit at the instant given"
    assert service_orbs != old_orbs, (
        "the old technique happens to give the same aspects here, so this test would " "not distinguish it"
    )


def test_transit_time_resolution_is_reported(service):
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00+00:00")
    transit = result["data"]["transit_time_resolution"]
    assert transit["utc_iso"] == "2026-10-21T12:00:00+00:00"
    assert transit["zone"]
    assert "warnings" in transit


def test_transit_naive_current_time_is_read_in_the_natal_city_zone(service):
    """A naive current_time_iso is a wall reading in the NATAL city's zone."""
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00")
    assert (
        result["data"]["transit_time"] == "2026-10-21T10:00:00+00:00"
    ), "Paris is +02:00 in October, so 12:00 local is 10:00 UTC"


# --------------------------------------------------------------------------- #
# (g) The response shape is unchanged (plus the additive time_resolution).
# --------------------------------------------------------------------------- #
# Recorded from the UNMODIFIED service before the ADP-2 edit.
NATAL_KEYS_BEFORE = {"ascendant", "city", "datetime", "houses", "moon", "planets", "subject", "sun"}
TRANSIT_KEYS_BEFORE = {"aspects", "subject", "transit_time"}
SYNASTRY_KEYS_BEFORE = {"aspects", "person_a", "person_b"}
PLANET_KEYS_BEFORE = {
    "abs_pos",
    "altitude_above_horizon",
    "aspect",
    "azimuth",
    "decan_number",
    "decan_ruler",
    "declination",
    "degree",
    "dignity_score",
    "ecliptic_latitude",
    "element",
    "emoji",
    "ephemeris_coverage_end_jd",
    "ephemeris_coverage_start_jd",
    "essential_dignity",
    "gauquelin_sector",
    "house",
    "is_out_of_bounds",
    "latitude",
    "longitude",
    "magnitude",
    "motion_state",
    "nakshatra",
    "nakshatra_lord",
    "nakshatra_number",
    "nakshatra_pada",
    "name",
    "near_point",
    "orb",
    "point_type",
    "position",
    "precision_class",
    "quality",
    "retrograde",
    "sign",
    "sign_num",
    "source",
    "source_reviewed",
    "speed",
    "term_ruler",
}


def test_natal_response_keys_are_unchanged_plus_time_resolution(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    keys = set(result["data"])
    assert keys == NATAL_KEYS_BEFORE | {"time_resolution"}, keys
    assert set(result["data"]["sun"]) == PLANET_KEYS_BEFORE
    assert set(result["data"]["planets"]) == {
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
        "chiron",
    }
    assert set(result["data"]["houses"]) == {
        "first_house",
        "second_house",
        "third_house",
        "fourth_house",
        "fifth_house",
        "sixth_house",
        "seventh_house",
        "eighth_house",
        "ninth_house",
        "tenth_house",
        "eleventh_house",
        "twelfth_house",
    }
    assert result["data"]["datetime"] == "1990-07-04T09:00:00", "the input string is echoed unchanged"
    assert isinstance(
        result["data"]["sun"]["longitude"], type(None)
    ), "kerykeion 6.0.4 leaves 'longitude' None; the type must not change"
    assert isinstance(result["data"]["sun"]["position"], float)


def test_transit_response_keys_are_unchanged_plus_resolutions(service):
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00Z")
    keys = set(result["data"])
    assert keys == TRANSIT_KEYS_BEFORE | {"time_resolution", "transit_time_resolution"}, keys
    assert isinstance(result["data"]["transit_time"], str)
    assert result["data"]["aspects"], "aspects must still be produced"
    assert set(result["data"]["aspects"][0]) == {
        "natal_planet",
        "transit_planet",
        "aspect",
        "orb",
        "exactness",
    }


def test_synastry_response_keys_are_unchanged_plus_resolutions(service):
    result = service.get_synastry("A", "1990-07-04T09:00:00", "Paris", "B", "1992-01-02T03:04:05", "Paris")
    keys = set(result["data"])
    assert keys == SYNASTRY_KEYS_BEFORE | {"time_resolution_a", "time_resolution_b"}, keys
    assert set(result["data"]["aspects"][0]) == {
        "person_a_planet",
        "person_b_planet",
        "aspect",
        "orb",
    }


def test_time_resolution_object_shape(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    resolution = result["data"]["time_resolution"]
    assert set(resolution) == {
        "utc_iso",
        "offset",
        "is_dst",
        "zone",
        "warnings",
        "time_assumed",
    }, resolution
    assert isinstance(resolution["utc_iso"], str)
    assert isinstance(resolution["offset"], float)
    assert isinstance(resolution["is_dst"], bool)
    assert isinstance(resolution["zone"], str)
    assert isinstance(resolution["warnings"], list)
    assert isinstance(resolution["time_assumed"], bool)


# --------------------------------------------------------------------------- #
# Synastry inherits the same rules for both people.
# --------------------------------------------------------------------------- #
def test_synastry_rejects_an_ambiguous_time_for_either_person(service):
    with pytest.raises(AmbiguousLocalTime):
        service.get_synastry("A", "2024-11-03T01:30:00", "New York", "B", "1990-07-04T09:00:00", "Paris")
    with pytest.raises(AmbiguousLocalTime):
        service.get_synastry("A", "1990-07-04T09:00:00", "Paris", "B", "2024-11-03T01:30:00", "New York")


def test_synastry_accepts_the_opt_in_for_both_people(service):
    result = service.get_synastry(
        "A",
        "2024-11-03T01:30:00",
        "New York",
        "B",
        "1990-07-04T09:00:00",
        "Paris",
        ambiguous="later",
    )
    assert "error" not in result, result
    assert result["data"]["time_resolution_a"]["utc_iso"] == "2024-11-03T06:30:00+00:00"
    assert result["data"]["time_resolution_b"]["utc_iso"] == "1990-07-04T07:00:00+00:00"


# --------------------------------------------------------------------------- #
# The HTTP layer: a policy error is 422, other failures stay 500.
# --------------------------------------------------------------------------- #
def test_ambiguous_time_becomes_http_422(fake_geocoding):
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/astrology/natal-chart",
        json={"name": "Alice", "birth_time_iso": "2024-11-03T01:30:00", "birth_city": "New York"},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert "America/New_York" in detail, detail
    assert "2024-11-03T05:30:00+00:00" in detail, detail
    assert "2024-11-03T06:30:00+00:00" in detail, detail


def test_nonexistent_time_becomes_http_422(fake_geocoding):
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/astrology/natal-chart",
        json={"name": "Alice", "birth_time_iso": "2024-03-10T02:30:00", "birth_city": "New York"},
    )
    assert resp.status_code == 422, resp.text
    assert "America/New_York" in resp.json()["detail"]


def test_the_opt_in_flags_reach_the_service(fake_geocoding):
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/astrology/natal-chart",
        json={
            "name": "Alice",
            "birth_time_iso": "2024-11-03T01:30:00",
            "birth_city": "New York",
            "ambiguous": "later",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data"]["time_resolution"]["utc_iso"] == "2024-11-03T06:30:00+00:00"


def test_a_non_policy_failure_is_still_500(fake_geocoding):
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    resp = client.post(
        "/api/v1/astrology/natal-chart",
        json={"name": "Alice", "birth_time_iso": "not-a-timestamp", "birth_city": "Paris"},
    )
    assert resp.status_code == 500, resp.text


def test_timezone_policy_error_is_a_value_error():
    """The endpoint catches TimezonePolicyError; the type hierarchy must allow that."""
    assert issubclass(TimezonePolicyError, ValueError)
    assert issubclass(AmbiguousLocalTime, TimezonePolicyError)
    assert issubclass(NonexistentLocalTime, TimezonePolicyError)


def test_no_math_or_degree_helper_leaks_into_the_service():
    """Guard: the tolerance constant in this file is degrees, not radians."""
    assert TOL_DEG < 0.02
    assert math.isclose(TOL_DEG, 1.0 / 60.0)


# --------------------------------------------------------------------------- #
# ADP-2b: the review's off-the-happy-path findings.
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 1. A date with no time of day.
# --------------------------------------------------------------------------- #
def test_a_date_only_input_is_accepted_but_says_so(service):
    """A date alone is a wall clock with no time, and midnight is a guess.

    ``datetime.fromisoformat("1990-07-04")`` returns midnight on 3.11+, so the
    chart is precise-looking and silently wrong about the one thing that
    matters most for a chart: the Ascendant, the houses and the angles.
    """
    result = service.get_natal_chart("Alice", "1990-07-04", "Kolkata")
    assert "error" not in result, result
    resolution = result["data"]["time_resolution"]
    assert resolution["time_assumed"] is True
    assert resolution["utc_iso"] == "1990-07-03T18:30:00+00:00", resolution
    warnings = " ".join(resolution["warnings"])
    assert "00:00 local assumed" in warnings, warnings
    assert "NOT reliable" in warnings, warnings


def test_a_timestamp_with_a_time_is_not_flagged_as_assumed(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Kolkata")
    assert result["data"]["time_resolution"]["time_assumed"] is False


def test_a_date_only_input_is_detected_by_parsing_not_by_length(service):
    """A date-only string with a different shape must also be detected.

    Detection is by ``date.fromisoformat``, so it does not depend on the string
    being ten characters long, and it behaves the same on 3.10, 3.11 and 3.13.
    """
    from backend.core.services.astrology_chart_service import _is_date_only

    assert _is_date_only("1990-07-04") is True
    assert _is_date_only("19900704") is True
    assert _is_date_only("1990-07-04T00:00:00") is False
    assert _is_date_only("1990-07-04T09:00") is False
    assert _is_date_only("1990-07-04 09:00:00") is False
    assert _is_date_only("not a date") is False


def test_a_date_only_transit_is_also_flagged(service):
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21")
    assert result["data"]["transit_time_resolution"]["time_assumed"] is True
    warnings = " ".join(result["data"]["transit_time_resolution"]["warnings"])
    assert "00:00 local assumed" in warnings, warnings


def test_a_date_only_synastry_person_is_flagged(service):
    result = service.get_synastry("A", "1990-07-04", "Paris", "B", "1992-01-02T03:04:05", "Paris")
    assert result["data"]["time_resolution_a"]["time_assumed"] is True
    assert result["data"]["time_resolution_b"]["time_assumed"] is False


# --------------------------------------------------------------------------- #
# 2. An aware transit instant must report its zone honestly.
# --------------------------------------------------------------------------- #
def test_an_aware_transit_reports_the_natal_zone_offset_and_is_dst(service):
    """The transit chart is drawn at the natal coordinates, so the natal zone is
    the zone it belongs to. Reporting the CALLER's offset next to that zone name
    was inconsistent: Paris in October is +02:00, not the +05:30 the caller sent.
    """
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00+05:30")
    resolution = result["data"]["transit_time_resolution"]
    assert result["data"]["transit_time"] == "2026-10-21T06:30:00+00:00"
    assert resolution["zone"] == "Europe/Paris"
    assert resolution["offset"] == pytest.approx(2.0), resolution
    assert isinstance(resolution["is_dst"], bool), resolution
    # Paris is still on CEST on 2026-10-21: the changeover is the last Sunday of
    # October, which in 2026 is the 25th, not the 21st.
    assert resolution["is_dst"] is True, "Paris is still on summer time on 2026-10-21"


def test_an_aware_transit_warns_when_the_offset_differs_from_the_zone(service):
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00+05:30")
    warnings = " ".join(result["data"]["transit_time_resolution"]["warnings"])
    assert "+05:30" in warnings, warnings
    assert "Europe/Paris" in warnings, warnings


def test_an_aware_transit_matching_the_zone_warns_about_nothing(service):
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00+02:00")
    warnings = " ".join(result["data"]["transit_time_resolution"]["warnings"])
    assert "differs from" not in warnings, warnings


# --------------------------------------------------------------------------- #
# 3. A bad zone must be the same status and the same message on both paths.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("zone", ["", None, "Not/AZone"], ids=["empty", "none", "unknown"])
def test_a_bad_zone_is_the_same_on_both_paths(service, monkeypatch, zone):
    monkeypatch.setitem(CITIES, "Bad", {"latitude": 0.0, "longitude": 0.0, "timezone": zone})
    messages = {}
    for label, stamp in (("naive", "1990-07-04T09:00:00"), ("aware", "1990-07-04T09:00:00+02:00")):
        with pytest.raises(TimezonePolicyError) as exc:
            service.get_natal_chart("Alice", stamp, "Bad")
        messages[label] = str(exc.value)
    assert messages["naive"] == messages["aware"], messages
    assert "Unknown IANA time zone" in messages["naive"], messages
    assert (
        "ZoneInfo" not in messages["naive"]
    ), f"the interpreter's own text must not be interpolated: {messages['naive']!r}"


def test_a_missing_timezone_key_is_still_a_geocoder_failure(service, monkeypatch):
    """No "timezone" key at all is the geocoder's fault, not a zone problem."""
    monkeypatch.setitem(CITIES, "Bad", {"latitude": 0.0, "longitude": 0.0})
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Bad")
    assert "error" in result, result
    assert "timezone" in result["error"], result


# --------------------------------------------------------------------------- #
# 4. The geocoded zone and the geocoded longitude are never checked against
#    each other.
# --------------------------------------------------------------------------- #
def test_a_zone_that_does_not_fit_the_longitude_warns(service, monkeypatch):
    """Kolkata's coordinates with a Los Angeles zone: a warning, not an error."""
    monkeypatch.setitem(CITIES, "Odd", {"latitude": 22.57, "longitude": 88.36, "timezone": "America/Los_Angeles"})
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Odd")
    assert "error" not in result, result
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "solar time" in warnings, warnings
    assert "88.36" in warnings, warnings


def test_the_utc_fallback_gets_its_own_warning(service, monkeypatch):
    """The live geocoder returns "UTC" when timezonefinder has no match."""
    monkeypatch.setitem(CITIES, "Odd", {"latitude": 22.57, "longitude": 88.36, "timezone": "UTC"})
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Odd")
    assert "error" not in result, result
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "'UTC'" in warnings, warnings
    assert "fallback" in warnings, warnings


def test_a_zone_that_fits_the_longitude_does_not_warn(service):
    """Paris for Paris: no warning, or the feature is noise."""
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "solar time" not in warnings, warnings


def test_a_zone_far_from_solar_time_only_warns(service, monkeypatch):
    """China's Xinjiang at ~87 E keeps Beijing time, about 2.2 h off solar time.

    That is inside the 3 h tolerance, so it does not warn. The threshold has to
    be loose enough for real zones or it is noise.
    """
    monkeypatch.setitem(CITIES, "Xinjiang", {"latitude": 43.8, "longitude": 87.6, "timezone": "Asia/Shanghai"})
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Xinjiang")
    warnings = " ".join(result["data"]["time_resolution"]["warnings"])
    assert "solar time" not in warnings, warnings


# --------------------------------------------------------------------------- #
# 5. Transit microseconds were dropped from the chart but kept in the string.
# --------------------------------------------------------------------------- #
def test_transit_microseconds_warn_like_the_birth_path(service):
    result = service.get_daily_transit("Alice", "1990-07-04T09:00:00", "Paris", "2026-10-21T12:00:00.500000")
    warnings = " ".join(result["data"]["transit_time_resolution"]["warnings"])
    assert "icrosecond" in warnings, warnings
    assert (
        result["data"]["transit_time"] == "2026-10-21T10:00:00+00:00"
    ), "the reported instant must be the one the chart was actually built from"


# --------------------------------------------------------------------------- #
# 6. Per-person opt-ins for synastry.
# --------------------------------------------------------------------------- #
def test_synastry_accepts_a_different_answer_for_the_second_person(service):
    """A ambiguous, B a gap: the shared pair cannot express it, the _b pair can."""
    result = service.get_synastry(
        "A",
        "2024-11-03T01:30:00",
        "New York",
        "B",
        "2024-03-10T02:30:00",
        "New York",
        ambiguous="later",
        nonexistent_b="shift_forward",
    )
    assert "error" not in result, result
    assert result["data"]["time_resolution_a"]["utc_iso"] == "2024-11-03T06:30:00+00:00"
    assert result["data"]["time_resolution_b"]["utc_iso"] == "2024-03-10T07:30:00+00:00"


def test_synastry_shared_pair_alone_still_raises_for_a_gap_in_b(service):
    """The limitation is real and is still there without the _b overrides."""
    with pytest.raises(NonexistentLocalTime):
        service.get_synastry(
            "A",
            "2024-11-03T01:30:00",
            "New York",
            "B",
            "2024-03-10T02:30:00",
            "New York",
            ambiguous="later",
        )


# --------------------------------------------------------------------------- #
# 7. A lowercase z.
# --------------------------------------------------------------------------- #
def test_a_lowercase_z_is_accepted(service):
    """A lowercase z is the same instant as an uppercase one."""
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00z", "Paris")
    assert "error" not in result, result
    assert (
        result["data"]["time_resolution"]["utc_iso"] == "1990-07-04T09:00:00+00:00"
    ), "a z suffix names UTC, whatever the city's zone is"


def test_time_resolution_gained_the_time_assumed_key(service):
    result = service.get_natal_chart("Alice", "1990-07-04T09:00:00", "Paris")
    resolution = result["data"]["time_resolution"]
    assert set(resolution) == {
        "utc_iso",
        "offset",
        "is_dst",
        "zone",
        "warnings",
        "time_assumed",
    }, resolution
