"""W3-J tests for GET /astrology/planetary-hour.

The route answers "which planetary hour is it at (latitude, longitude) at this instant": ruler, day or night hour,
its start and end, and the exact time left. It wraps the engine's solar-day maths (``_solar_day``, the primitive
``calculate_exact_planetary_hours`` is built on) with the strict parsing and range rules of ``/sun-events``.

Why not ``/timing-wheel`` (checked on the real routes): its payload is ~28 KB for a handful of needed fields, a
malformed ``date`` answers *now*, and at a polar place (or without the engine) it silently substitutes a 06:00 /
18:00 estimate that its ``provenance`` still calls ``computed``, with nothing in the payload to tell the two apart.
Why not ``calculate_exact_planetary_hours`` itself: at a polar place it returns a hard-coded ``"Sun"`` hour, and it
truncates the time left to whole seconds. Here a polar day or night is ``hour: null`` with a reason, never a guess.

The expected hours are NOT taken from the engine. They are derived in this file by the classical rule from the
independent W3-O sunrise and sunset literals (docs/notes/earthsky/wave3/oracle/oracle_sun_events.json, swisseph;
the JSON is never imported):

* a solar day runs from one sunrise to the next; its daytime (sunrise to sunset) is twelve equal hours and its
  night (sunset to the next sunrise) is twelve equal hours;
* the day ruler is the weekday of the LOCAL MEAN SOLAR DATE of the sunrise that began the solar day;
* hour rulers follow the Chaldean order Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon from the day ruler,
  continuing through the night (the first night hour is the thirteenth).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest
import swisseph as swe
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import astrology
from core.astrology import AstrologicalCalculator

UTC = timezone.utc
URL = "/astrology/planetary-hour"
CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
WEEKDAY_RULER = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]  # Monday .. Sunday
MS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

# (place, lat, lon, instant, previous_sunrise, next_sunrise, previous_sunset, next_sunset), swisseph, whole seconds.
# Rule for the subset: 13 of the oracle's 126 cases, one per place, alternating day and night instants, at least
# 120 s away from every hour boundary (the oracle rounds to whole seconds), spanning both hemispheres, the date
# line (Kiritimati, Apia, Auckland, Anadyr: where the weekday rule is easy to get wrong) and two high latitudes.
# fmt: off
ORACLE_CASES = (
    ("San Francisco", 37.7749, -122.4194, "2026-06-21T00:00:00Z", "2026-06-20T12:47:38Z", "2026-06-21T12:47:51Z", "2026-06-20T03:34:50Z", "2026-06-21T03:35:04Z"),
    ("Tokyo", 35.6762, 139.6503, "2026-03-20T12:00:00Z", "2026-03-19T20:45:33Z", "2026-03-20T20:44:07Z", "2026-03-20T08:52:55Z", "2026-03-21T08:53:45Z"),
    ("Sydney", -33.8688, 151.2093, "2026-06-21T00:00:00Z", "2026-06-20T20:59:44Z", "2026-06-21T20:59:57Z", "2026-06-20T06:53:50Z", "2026-06-21T06:54:02Z"),
    ("Kiritimati", 1.87, -157.4, "2026-03-20T12:00:00Z", "2026-03-19T16:33:49Z", "2026-03-20T16:33:28Z", "2026-03-20T04:40:37Z", "2026-03-21T04:40:22Z"),
    ("Apia", -13.8333, -171.7667, "2026-06-21T00:00:00Z", "2026-06-20T17:49:18Z", "2026-06-21T17:49:31Z", "2026-06-20T05:08:02Z", "2026-06-21T05:08:15Z"),
    ("Reykjavik", 64.15, -21.94, "2026-09-23T06:00:00Z", "2026-09-22T07:10:15Z", "2026-09-23T07:13:07Z", "2026-09-22T19:29:01Z", "2026-09-23T19:25:28Z"),
    ("London", 51.5074, -0.1278, "2026-03-20T12:00:00Z", "2026-03-20T06:03:06Z", "2026-03-21T06:00:49Z", "2026-03-19T18:12:06Z", "2026-03-20T18:13:48Z"),
    ("Quito", -0.1807, -78.4678, "2026-06-21T00:00:00Z", "2026-06-20T11:11:58Z", "2026-06-21T11:12:12Z", "2026-06-20T23:19:04Z", "2026-06-21T23:19:17Z"),
    ("Cape Town", -33.9249, 18.4241, "2026-03-20T12:00:00Z", "2026-03-20T04:49:09Z", "2026-03-21T04:49:56Z", "2026-03-19T16:59:10Z", "2026-03-20T16:57:49Z"),
    ("Nairobi", -1.2921, 36.8219, "2026-06-21T00:00:00Z", "2026-06-20T03:32:40Z", "2026-06-21T03:32:53Z", "2026-06-20T15:35:54Z", "2026-06-21T15:36:07Z"),
    ("Honolulu", 21.3069, -157.8583, "2026-06-21T00:00:00Z", "2026-06-20T15:49:59Z", "2026-06-21T15:50:12Z", "2026-06-20T05:16:03Z", "2026-06-21T05:16:17Z"),
    ("Anadyr", 64.7314, 177.5097, "2026-03-20T12:00:00Z", "2026-03-19T18:12:16Z", "2026-03-20T18:08:38Z", "2026-03-20T06:24:31Z", "2026-03-21T06:27:35Z"),
    ("Auckland", -36.8485, 174.7633, "2026-03-20T12:00:00Z", "2026-03-19T18:23:12Z", "2026-03-20T18:24:06Z", "2026-03-20T06:33:15Z", "2026-03-21T06:31:46Z"),
)
# fmt: on


def parse_z(text: str) -> datetime:
    assert text.endswith("Z"), text
    return datetime.fromisoformat(text[:-1] + "+00:00")


def expected_hour(case: tuple) -> dict:
    """The classical rule, written out; nothing here calls the engine."""
    _place, _lat, lon, instant, prev_rise, next_rise, prev_set, next_set = case
    t, sunrise, next_sunrise = parse_z(instant), parse_z(prev_rise), parse_z(next_rise)
    sunsets = [x for x in (parse_z(prev_set), parse_z(next_set)) if sunrise < x < next_sunrise]
    assert len(sunsets) == 1, "the oracle gives exactly one sunset inside the solar day"
    sunset = sunsets[0]
    day_ruler = WEEKDAY_RULER[(sunrise + timedelta(hours=lon / 15.0)).weekday()]
    first = CHALDEAN.index(day_ruler)
    if sunrise <= t < sunset:
        unit = (sunset - sunrise) / 12
        index = min(int((t - sunrise) / unit), 11)
        start, ruler, is_day = sunrise + unit * index, CHALDEAN[(first + index) % 7], True
    else:
        unit = (next_sunrise - sunset) / 12
        index = min(int((t - sunset) / unit), 11)
        start, ruler, is_day = sunset + unit * index, CHALDEAN[(first + 12 + index) % 7], False
    end = start + unit
    return {
        "day_ruler": day_ruler,
        "ruler": ruler,
        "is_daytime": is_day,
        "index": index + 1,
        "starts_at": start,
        "ends_at": end,
        "time_remaining": (end - t).total_seconds(),
        "length": unit.total_seconds(),
        "sunrise": sunrise,
        "sunset": sunset,
        "next_sunrise": next_sunrise,
    }


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(astrology.router, prefix="/astrology")
    return TestClient(app)


@pytest.fixture(scope="module")
def engine() -> AstrologicalCalculator:
    return AstrologicalCalculator()


def get(client: TestClient, lat: float, lon: float, moment: str | None = "2026-10-24T09:00:00Z", **extra):
    params: dict = {"latitude": lat, "longitude": lon}
    if moment is not None:
        params["datetime_str"] = moment
    params.update(extra)
    return client.get(URL, params=params)


class TestShape:
    def test_a_normal_answer_has_exactly_these_keys(self, client):
        response = get(client, 37.7749, -122.4194)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"at", "latitude", "longitude", "solar_day", "hour", "reason", "provenance"}
        assert set(body["solar_day"]) == {"sunrise", "sunset", "next_sunrise", "day_ruler"}
        assert set(body["hour"]) == {
            "ruler",
            "is_daytime",
            "index",
            "starts_at",
            "ends_at",
            "length_seconds",
            "time_remaining_seconds",
        }
        assert body["reason"] is None
        assert body["latitude"] == 37.7749 and body["longitude"] == -122.4194
        assert parse_z(body["at"]) == datetime(2026, 10, 24, 9, 0, tzinfo=UTC)
        assert set(body["provenance"]) >= {"at", "solar_day", "hour"}
        assert set(body["provenance"].values()) == {"computed"}

    def test_instants_are_utc_with_milliseconds_and_z(self, client):
        body = get(client, 37.7749, -122.4194).json()
        for key in ("sunrise", "sunset", "next_sunrise"):
            assert MS_Z.match(body["solar_day"][key]), body["solar_day"][key]
        for key in ("starts_at", "ends_at"):
            assert MS_Z.match(body["hour"][key]), body["hour"][key]

    def test_value_ranges(self, client):
        hour = get(client, 37.7749, -122.4194).json()["hour"]
        assert hour["ruler"] in CHALDEAN
        assert isinstance(hour["is_daytime"], bool)
        assert 1 <= hour["index"] <= 12
        assert 0 <= hour["time_remaining_seconds"] <= hour["length_seconds"]
        assert parse_z(hour["starts_at"]) < parse_z(hour["ends_at"])
        assert (
            abs((parse_z(hour["ends_at"]) - parse_z(hour["starts_at"])).total_seconds() - hour["length_seconds"]) < 0.01
        )

    def test_omitted_datetime_means_now_and_is_echoed(self, client):
        before = datetime.now(UTC)
        body = get(client, 37.7749, -122.4194, moment=None).json()
        after = datetime.now(UTC)
        assert before - timedelta(seconds=1) <= parse_z(body["at"]) <= after + timedelta(seconds=1)

    def test_z_naive_and_offset_spellings_agree(self, client):
        z = get(client, 35.68, 139.69, "2026-10-24T09:00:00Z")
        naive = get(client, 35.68, 139.69, "2026-10-24T09:00:00")
        offset = get(client, 35.68, 139.69, "2026-10-24T18:00:00+09:00")
        assert z.status_code == naive.status_code == offset.status_code == 200
        assert z.json() == naive.json() == offset.json()


class TestAgainstTheOracleRule:
    """13 (place, instant) pairs: the route against the rule applied to independent sunrise and sunset literals."""

    @pytest.mark.parametrize("case", ORACLE_CASES, ids=lambda c: f"{c[0]}@{c[3]}")
    def test_ruler_index_day_night_and_the_exact_times(self, client, case):
        place, lat, lon, instant = case[:4]
        want = expected_hour(case)
        response = get(client, lat, lon, instant)
        assert response.status_code == 200
        body = response.json()
        hour, day = body["hour"], body["solar_day"]
        assert hour["ruler"] == want["ruler"], (place, instant)
        assert hour["is_daytime"] is want["is_daytime"], (place, instant)
        assert hour["index"] == want["index"], (place, instant)
        assert day["day_ruler"] == want["day_ruler"], (place, instant)
        # the oracle writes whole seconds (+-0.5 s each); the hour is a twelfth of a span, so 1.5 s is generous
        tolerance = timedelta(seconds=1.5)
        assert abs(parse_z(hour["starts_at"]) - want["starts_at"]) <= tolerance, (place, instant)
        assert abs(parse_z(hour["ends_at"]) - want["ends_at"]) <= tolerance, (place, instant)
        assert abs(hour["time_remaining_seconds"] - want["time_remaining"]) <= 1.5, (place, instant)
        assert abs(hour["length_seconds"] - want["length"]) <= 1.5, (place, instant)
        assert abs(parse_z(day["sunrise"]) - want["sunrise"]) <= tolerance, (place, instant)
        assert abs(parse_z(day["sunset"]) - want["sunset"]) <= tolerance, (place, instant)
        assert abs(parse_z(day["next_sunrise"]) - want["next_sunrise"]) <= tolerance, (place, instant)

    def test_the_cases_cover_day_and_night_hours_and_several_rulers(self):
        wants = [expected_hour(case) for case in ORACLE_CASES]
        assert {w["is_daytime"] for w in wants} == {True, False}
        assert len({w["ruler"] for w in wants}) >= 5
        assert len({w["day_ruler"] for w in wants}) >= 3

    def test_a_hand_derived_anchor_not_taken_from_any_rule_code(self, client):
        """2026-06-20 was a Saturday, so the solar day that began at San Francisco's sunrise (2026-06-20T12:47Z) is
        ruled by Saturn. At 2026-06-21T00:00Z, 11 h 12 m after sunrise of a 14 h 47 m day, it is daytime hour 10;
        counting Saturn(1) Jupiter(2) Mars(3) Sun(4) Venus(5) Mercury(6) Moon(7) Saturn(8) Jupiter(9) Mars(10)."""
        body = get(client, 37.7749, -122.4194, "2026-06-21T00:00:00Z").json()
        assert body["solar_day"]["day_ruler"] == "Saturn"
        assert (body["hour"]["is_daytime"], body["hour"]["index"], body["hour"]["ruler"]) == (True, 10, "Mars")


class TestAgreesWithTheEngine:
    """Where the engine's public wrapper is honest (not polar), the route says the same thing, more precisely."""

    @pytest.mark.parametrize("case", ORACLE_CASES, ids=lambda c: c[0])
    def test_same_ruler_hour_and_boundaries_as_calculate_exact_planetary_hours(self, client, engine, case):
        _place, lat, lon, instant = case[:4]
        moment = parse_z(instant)
        engine_hour = engine.calculate_exact_planetary_hours(moment, (lat, lon))
        assert engine_hour["status"] == "success"
        hour = get(client, lat, lon, instant).json()["hour"]
        assert hour["ruler"] == engine_hour["current_planetary_hour"]
        assert hour["index"] == engine_hour["hour_index"]
        assert hour["is_daytime"] == engine_hour["is_daytime"]
        assert abs(parse_z(hour["starts_at"]) - datetime.fromisoformat(engine_hour["start_time"])) < timedelta(
            milliseconds=1
        )
        assert abs(parse_z(hour["ends_at"]) - datetime.fromisoformat(engine_hour["end_time"])) < timedelta(
            milliseconds=1
        )
        # the engine truncates to whole seconds; the route keeps the fraction
        assert abs(hour["time_remaining_seconds"] - engine_hour["time_remaining_seconds"]) < 1.0


class TestBoundaries:
    def test_an_hour_ends_where_the_next_begins(self, client):
        first = get(client, 37.7749, -122.4194, "2026-10-24T20:00:00Z").json()["hour"]
        second = get(client, 37.7749, -122.4194, first["ends_at"]).json()["hour"]
        assert second["starts_at"] == first["ends_at"]
        assert second["time_remaining_seconds"] == pytest.approx(second["length_seconds"], abs=0.002)
        assert second["index"] == first["index"] % 12 + 1 or second["is_daytime"] != first["is_daytime"]
        assert second["ruler"] == CHALDEAN[(CHALDEAN.index(first["ruler"]) + 1) % 7]

    def test_asking_at_ends_at_always_lands_in_the_next_hour(self, client):
        """Boundaries are printed rounded UP to the millisecond, so there is no instant that is "at the end" yet
        still inside the hour. A client that refetches when `now >= ends_at` can never loop on the same hour."""
        moment = "2026-10-24T00:00:00Z"
        for _ in range(30):
            hour = get(client, 37.7749, -122.4194, moment).json()["hour"]
            nxt = get(client, 37.7749, -122.4194, hour["ends_at"]).json()["hour"]
            assert nxt["starts_at"] == hour["ends_at"], (moment, hour, nxt)
            moment = nxt["ends_at"]

    def test_one_millisecond_before_the_end_is_still_the_same_hour_with_almost_no_time_left(self, client):
        first = get(client, 35.68, 139.69, "2026-10-24T03:00:00Z").json()["hour"]
        just_before = (parse_z(first["ends_at"]) - timedelta(milliseconds=1)).isoformat().replace("+00:00", "Z")
        again = get(client, 35.68, 139.69, just_before).json()["hour"]
        assert again["starts_at"] == first["starts_at"]
        assert 0 <= again["time_remaining_seconds"] <= 0.002

    def test_time_left_is_never_negative_around_sunrise_and_sunset(self, client):
        day = get(client, 37.7749, -122.4194, "2026-10-24T09:00:00Z").json()["solar_day"]
        for key in ("sunrise", "sunset", "next_sunrise"):
            edge = parse_z(day[key])
            for offset in (-1.5, -0.4, -0.001, 0.0, 0.001, 0.3, 0.9, 1.5):
                moment = (edge + timedelta(seconds=offset)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                response = get(client, 37.7749, -122.4194, moment)
                assert response.status_code == 200, (key, offset)
                hour = response.json()["hour"]
                assert hour is not None and hour["time_remaining_seconds"] >= 0, (key, offset, hour)

    def test_asking_at_the_printed_sunrise_is_the_first_day_hour_of_the_new_day(self, client):
        """The engine alone answers the previous night's last hour for the fraction of a second after a sunrise."""
        day = get(client, 37.7749, -122.4194, "2026-10-24T09:00:00Z").json()["solar_day"]
        hour = get(client, 37.7749, -122.4194, day["next_sunrise"]).json()["hour"]
        assert (hour["is_daytime"], hour["index"]) == (True, 1)
        assert hour["starts_at"] == day["next_sunrise"]
        assert hour["time_remaining_seconds"] == pytest.approx(hour["length_seconds"], abs=0.002)

    def test_a_sub_second_instant_is_accepted_and_echoed(self, client):
        body = get(client, 37.7749, -122.4194, "2026-10-24T09:00:00.250Z").json()
        assert parse_z(body["at"]) == datetime(2026, 10, 24, 9, 0, 0, 250_000, tzinfo=UTC)


class TestPolarAndHonesty:
    @pytest.mark.parametrize(
        ("name", "lat", "lon", "moment"),
        [
            ("Tromso midnight sun", 69.65, 18.96, "2026-06-21T12:00:00Z"),
            ("Tromso polar night", 69.65, 18.96, "2026-12-21T12:00:00Z"),
            ("South Pole", -90.0, 0.0, "2026-12-21T12:00:00Z"),
            ("North Pole", 90.0, 180.0, "2026-06-21T12:00:00Z"),
            ("Alert, Nunavut", 82.5, -62.3, "2026-06-21T12:00:00Z"),
        ],
    )
    def test_no_sunrise_here_is_a_null_hour_with_a_reason_never_an_invented_hour(self, client, name, lat, lon, moment):
        response = get(client, lat, lon, moment)
        assert response.status_code == 200, name
        body = response.json()
        assert body["hour"] is None and body["solar_day"] is None, name
        assert isinstance(body["reason"], str) and "sunrise" in body["reason"].lower(), name
        assert "Sun" not in str(body["hour"])  # the engine wrapper's hard-coded polar "Sun" hour never leaks
        assert set(body["provenance"].values()) == {"computed"}

    def test_the_partial_case_at_the_north_pole_near_the_equinox_is_also_null(self, client):
        """One real sunrise (18 March) exists, but no sunrise-to-sunrise day brackets the instant: no hour."""
        body = get(client, 90.0, 0.0, "2026-03-20T12:00:00Z").json()
        assert body["hour"] is None and body["reason"]

    def test_the_wheels_fallback_is_not_reachable_from_here(self, client, monkeypatch):
        """If the engine cannot answer, the route says so (503); it never substitutes a 6 AM / 6 PM guess."""
        monkeypatch.setattr(astrology, "AstrologicalCalculator", None)
        response = get(client, 37.7749, -122.4194)
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}


class TestStrictValidation:
    @pytest.mark.parametrize("lat", ["90.0001", "-90.0001", "91", "-1000", "nan", "inf", "-inf", "abc", "", "  "])
    def test_bad_latitude_is_422_with_a_string_detail(self, client, lat):
        response = client.get(URL, params={"latitude": lat, "longitude": "10"})
        assert response.status_code == 422, lat
        assert isinstance(response.json()["detail"], str) and "latitude" in response.json()["detail"]

    @pytest.mark.parametrize("lon", ["180.0001", "-180.0001", "360", "nan", "inf", "abc", "", "  "])
    def test_bad_longitude_is_422_with_a_string_detail(self, client, lon):
        response = client.get(URL, params={"latitude": "10", "longitude": lon})
        assert response.status_code == 422, lon
        assert isinstance(response.json()["detail"], str) and "longitude" in response.json()["detail"]

    def test_latitude_and_longitude_are_required_no_silent_default_place(self, client):
        for params in ({}, {"latitude": "10"}, {"longitude": "10"}):
            response = client.get(URL, params=params)
            assert response.status_code == 422, params
            assert isinstance(response.json()["detail"], str)

    @pytest.mark.parametrize(
        "moment",
        [
            "not-a-date",
            "2026-13-45T99:99:99Z",
            "2026-03-20T14:46:00+25:00",
            "",
            "   ",
            "1799-12-31T23:59:59Z",
            "2201-01-01T00:00:00Z",
        ],
    )
    def test_bad_or_unsupported_instants_are_422(self, client, moment):
        response = client.get(URL, params={"latitude": "10", "longitude": "10", "datetime_str": moment})
        assert response.status_code == 422, moment
        assert isinstance(response.json()["detail"], str)

    @pytest.mark.parametrize("extreme", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
    def test_extreme_offsets_are_422_not_an_overflow_500(self, client, extreme):
        response = client.get(URL, params={"latitude": "10", "longitude": "10", "datetime_str": extreme})
        assert response.status_code == 422

    @pytest.mark.parametrize("moment", ["1800-01-01T00:00:00Z", "2200-12-31T23:59:59Z"])
    def test_supported_range_edges_pass(self, client, moment):
        assert get(client, 51.5, 0.0, moment).status_code == 200

    def test_boundary_places_are_accepted(self, client):
        for lat, lon in ((90, 180), (-90, -180), (0, 0)):
            assert get(client, lat, lon, "2026-03-20T12:00:00Z").status_code == 200, (lat, lon)

    def test_validation_wins_over_an_unavailable_ephemeris(self, client, monkeypatch):
        monkeypatch.setattr(astrology, "AstrologicalCalculator", None)
        assert client.get(URL, params={"latitude": "95", "longitude": "10"}).status_code == 422


class TestUnavailable:
    def test_engine_error_is_503(self, client, monkeypatch):
        class Broken:
            def _solar_day(self, dt, location):
                raise swe.Error("ephemeris file not found")

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Broken)
        response = get(client, 37.7749, -122.4194)
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}

    def test_a_bug_in_the_engine_is_not_called_unavailable(self, client, monkeypatch):
        class Buggy:
            def _solar_day(self, dt, location):
                raise KeyError("a real bug")

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Buggy)
        with pytest.raises(KeyError):
            get(client, 37.7749, -122.4194)

    def test_engine_none_is_a_null_hour_not_a_time(self, client, monkeypatch):
        class Silent:
            def _solar_day(self, dt, location):
                return None

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Silent)
        body = get(client, 37.7749, -122.4194).json()
        assert body["hour"] is None and body["solar_day"] is None and body["reason"]
