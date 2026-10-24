"""W3-B tests for GET /astrology/sun-events.

The route is a thin read-only wrapper of ``AstrologicalCalculator._sun_events_around``,
the single source of truth the planetary-hour code already trusts: no sun maths
lives in the route, so the tests check (a) that the route reports what the
engine says, to the millisecond, (b) the ordering properties any correct answer
must have, (c) strict validation, and (d) that nothing is ever invented: polar
day and night are ``null``, a missing ephemeris is 503 (never the 6 AM / 6 PM
estimate the timing wheel falls back to).

Independent swisseph literals for sunrise and sunset (+-1 s) arrive from W3-O
and are added here as literals, never imported. Until then the hand-derived
almanac check below (San Francisco, 2026-06-21: sunrise 05:48 PDT, sunset
20:35 PDT) is the only value pinned, to +-3 minutes.
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
URL = "/astrology/sun-events"
EVENT_KEYS = ("previous_sunrise", "sunset", "next_sunrise", "previous_sunset", "next_sunset")
MS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

SAN_FRANCISCO = (37.7749, -122.4194)
TOKYO = (35.68, 139.69)
SYDNEY = (-33.87, 151.21)
LONDON = (51.51, -0.13)
REYKJAVIK = (64.15, -21.94)
QUITO = (-0.18, -78.47)
FIJI_ON_THE_SEAM = (-17.7, 180.0)
TROMSO = (69.65, 18.96)


def parse_z(text: str) -> datetime:
    assert text.endswith("Z"), text
    return datetime.fromisoformat(text[:-1] + "+00:00")


@pytest.fixture(scope="module")
def engine() -> AstrologicalCalculator:
    return AstrologicalCalculator()


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(astrology.router, prefix="/astrology")
    return TestClient(app)


def get(client: TestClient, place, moment: str | None = "2026-06-21T12:00:00Z", **extra):
    params: dict = {"latitude": place[0], "longitude": place[1]}
    if moment is not None:
        params["datetime_str"] = moment
    params.update(extra)
    return client.get(URL, params=params)


class TestShape:
    def test_key_set_provenance_and_echo(self, client):
        response = get(client, SAN_FRANCISCO)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"at", "latitude", "longitude", *EVENT_KEYS, "provenance"}
        assert body["latitude"] == SAN_FRANCISCO[0]
        assert body["longitude"] == SAN_FRANCISCO[1]
        assert parse_z(body["at"]) == datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
        assert set(body["provenance"]) >= {"at", *EVENT_KEYS}
        assert set(body["provenance"].values()) == {"computed"}

    def test_events_are_utc_instants_with_milliseconds_and_z(self, client):
        body = get(client, SAN_FRANCISCO).json()
        for key in EVENT_KEYS:
            assert MS_Z.match(body[key]), (key, body[key])

    def test_omitted_datetime_means_now_and_is_echoed(self, client):
        before = datetime.now(UTC)
        body = get(client, SAN_FRANCISCO, moment=None).json()
        after = datetime.now(UTC)
        assert before - timedelta(seconds=1) <= parse_z(body["at"]) <= after + timedelta(seconds=1)

    def test_z_naive_and_offset_spellings_agree(self, client):
        z = get(client, TOKYO, "2026-10-24T09:00:00Z")
        naive = get(client, TOKYO, "2026-10-24T09:00:00")
        offset = get(client, TOKYO, "2026-10-24T18:00:00+09:00")
        assert z.status_code == naive.status_code == offset.status_code == 200
        assert z.json() == naive.json() == offset.json()


class TestReportsTheEngine:
    PLACES = [SAN_FRANCISCO, TOKYO, SYDNEY, LONDON, REYKJAVIK, QUITO, FIJI_ON_THE_SEAM]
    MOMENTS = [
        datetime(2026, 3, 20, 14, 46, tzinfo=UTC),
        datetime(2026, 6, 21, 12, 0, tzinfo=UTC),
        datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        datetime(2026, 12, 21, 23, 30, tzinfo=UTC),
    ]

    @pytest.mark.parametrize("place", PLACES, ids=lambda p: f"{p[0]},{p[1]}")
    def test_route_equals_sun_events_around_to_a_millisecond(self, client, engine, place):
        for moment in self.MOMENTS:
            body = get(client, place, moment.strftime("%Y-%m-%dT%H:%M:%SZ")).json()
            expected = engine._sun_events_around(moment, place)
            for key in EVENT_KEYS:
                assert expected[key] is not None, (place, moment, key)
                assert abs(parse_z(body[key]) - expected[key]) < timedelta(milliseconds=1), (place, moment, key)

    @pytest.mark.parametrize("place", PLACES, ids=lambda p: f"{p[0]},{p[1]}")
    def test_ordering_properties(self, client, place):
        for moment in self.MOMENTS:
            at = moment
            body = get(client, place, moment.strftime("%Y-%m-%dT%H:%M:%SZ")).json()
            prev_rise, day_set, next_rise = (parse_z(body[k]) for k in ("previous_sunrise", "sunset", "next_sunrise"))
            prev_set, next_set = parse_z(body["previous_sunset"]), parse_z(body["next_sunset"])
            where = (place, moment)
            assert prev_rise <= at < next_rise, where
            assert prev_set <= at < next_set, where
            assert prev_rise < day_set < next_rise, where
            assert timedelta(hours=23) < next_rise - prev_rise < timedelta(hours=25), where
            assert timedelta(hours=23) < next_set - prev_set < timedelta(hours=25), where

    def test_san_francisco_solstice_against_the_almanac(self, client):
        body = get(client, SAN_FRANCISCO, "2026-06-21T12:00:00Z").json()
        tolerance = timedelta(minutes=3)
        # 05:48 PDT on 2026-06-21 and 20:35 PDT the same evening
        assert abs(parse_z(body["previous_sunrise"]) - datetime(2026, 6, 20, 12, 48, tzinfo=UTC)) < tolerance
        assert abs(parse_z(body["next_sunrise"]) - datetime(2026, 6, 21, 12, 48, tzinfo=UTC)) < tolerance
        assert abs(parse_z(body["sunset"]) - datetime(2026, 6, 21, 3, 35, tzinfo=UTC)) < tolerance
        assert abs(parse_z(body["next_sunset"]) - datetime(2026, 6, 22, 3, 35, tzinfo=UTC)) < tolerance

    @pytest.mark.parametrize("place", PLACES, ids=lambda p: f"{p[0]},{p[1]}")
    def test_solar_day_is_the_one_the_planetary_hour_code_uses(self, client, engine, place):
        """get_solar_day_sun_events is what the planetary hours and the timing wheel are built from."""
        for moment in self.MOMENTS:
            body = get(client, place, moment.strftime("%Y-%m-%dT%H:%M:%SZ")).json()
            day = engine.get_solar_day_sun_events(moment, place)
            for route_key, day_key in (
                ("previous_sunrise", "sunrise"),
                ("sunset", "sunset"),
                ("next_sunrise", "next_sunrise"),
            ):
                assert day[day_key] is not None, (place, moment, day_key)
                assert abs(parse_z(body[route_key]) - day[day_key]) < timedelta(milliseconds=1), (
                    place,
                    moment,
                    route_key,
                )


class TestNothingIsInvented:
    @pytest.mark.parametrize(
        "moment",
        ["2026-06-21T12:00:00Z", "2026-12-21T12:00:00Z"],
        ids=["midnight-sun", "polar-night"],
    )
    def test_tromso_polar_day_and_night_are_all_null(self, client, moment):
        response = get(client, TROMSO, moment)
        assert response.status_code == 200
        body = response.json()
        assert all(body[key] is None for key in EVENT_KEYS), body

    @pytest.mark.parametrize("pole", [(90.0, 0.0), (-90.0, 0.0), (90.0, 180.0), (-90.0, -180.0)])
    @pytest.mark.parametrize("moment", ["2026-06-21T12:00:00Z", "2026-12-21T12:00:00Z"])
    def test_the_poles_and_the_boundaries_are_accepted_and_null_at_the_solstices(self, client, pole, moment):
        response = get(client, pole, moment)
        assert response.status_code == 200
        assert all(response.json()[key] is None for key in EVENT_KEYS)

    def test_a_real_partial_answer_the_pole_near_the_equinox(self, client):
        """The Sun rises once at the North Pole around 18 March (refraction): only that event exists."""
        body = get(client, (90.0, 0.0), "2026-03-20T12:00:00Z").json()
        rise = parse_z(body["previous_sunrise"])
        assert datetime(2026, 3, 17, 12, tzinfo=UTC) < rise < datetime(2026, 3, 20, 12, tzinfo=UTC)
        assert [body[key] for key in EVENT_KEYS if key != "previous_sunrise"] == [None] * 4

    def test_engine_none_becomes_json_null_never_a_time(self, client, monkeypatch):
        class Silent:
            def _sun_events_around(self, dt, location):
                return {key: None for key in EVENT_KEYS}

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Silent)
        body = get(client, SAN_FRANCISCO).json()
        assert all(body[key] is None for key in EVENT_KEYS)

    def test_partial_nulls_pass_through(self, client, monkeypatch):
        rise = datetime(2026, 11, 27, 10, 11, 57, 22330, tzinfo=UTC)

        class Partial:
            def _sun_events_around(self, dt, location):
                return {
                    "previous_sunrise": None,
                    "sunset": None,
                    "next_sunrise": rise,
                    "previous_sunset": None,
                    "next_sunset": None,
                }

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Partial)
        body = get(client, TROMSO).json()
        assert body["next_sunrise"] == "2026-11-27T10:11:57.022Z"
        assert [body[k] for k in EVENT_KEYS if k != "next_sunrise"] == [None] * 4

    def test_missing_calculator_is_503_not_a_six_am_estimate(self, client, monkeypatch):
        monkeypatch.setattr(astrology, "AstrologicalCalculator", None)
        response = get(client, SAN_FRANCISCO)
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}

    def test_engine_error_is_503(self, client, monkeypatch):
        class Broken:
            def _sun_events_around(self, dt, location):
                raise swe.Error("ephemeris file not found")

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Broken)
        response = get(client, SAN_FRANCISCO)
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}

    def test_a_bug_in_the_engine_is_not_called_unavailable(self, client, monkeypatch):
        class Buggy:
            def _sun_events_around(self, dt, location):
                raise KeyError("a real bug")

        monkeypatch.setattr(astrology, "AstrologicalCalculator", Buggy)
        with pytest.raises(KeyError):
            get(client, SAN_FRANCISCO)


class TestStrictValidation:
    @pytest.mark.parametrize("lat", ["90.0001", "-90.0001", "91", "-1000", "nan", "inf", "-inf", "abc", "", "  "])
    def test_bad_latitude_is_422_with_a_string_detail(self, client, lat):
        response = client.get(URL, params={"latitude": lat, "longitude": "10"})
        assert response.status_code == 422, lat
        assert isinstance(response.json()["detail"], str)
        assert "latitude" in response.json()["detail"]

    @pytest.mark.parametrize("lon", ["180.0001", "-180.0001", "360", "nan", "inf", "abc", "", "  "])
    def test_bad_longitude_is_422_with_a_string_detail(self, client, lon):
        response = client.get(URL, params={"latitude": "10", "longitude": lon})
        assert response.status_code == 422, lon
        assert isinstance(response.json()["detail"], str)
        assert "longitude" in response.json()["detail"]

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
        assert isinstance(response.json()["detail"], str)

    @pytest.mark.parametrize("moment", ["1800-01-01T00:00:00Z", "2200-12-31T23:59:59Z"])
    def test_supported_range_edges_pass(self, client, moment):
        assert get(client, LONDON, moment).status_code == 200

    def test_validation_wins_over_an_unavailable_ephemeris(self, client, monkeypatch):
        monkeypatch.setattr(astrology, "AstrologicalCalculator", None)
        response = client.get(URL, params={"latitude": "95", "longitude": "10"})
        assert response.status_code == 422

    def test_boundary_values_are_accepted(self, client):
        for lat, lon in ((90, 180), (-90, -180), (0, 0), (89.9999, 179.9999)):
            assert get(client, (lat, lon), "2026-03-20T12:00:00Z").status_code == 200, (lat, lon)


# fmt: off
# Copied from docs/notes/earthsky/wave3/oracle/oracle_sun_events.json (dev-g1, W3-O): ALL 126 cases, expected_swisseph
# (whole seconds). Row: (place, lat, lon, instant, (previous_sunrise, next_sunrise, previous_sunset, next_sunset)).
# None = no event within the engine's +-2.5 day window (polar day or night).
ORACLE_SUN_CASES = (
    ("San Francisco", 37.7749, -122.4194, "2026-03-20T12:00:00Z", ("2026-03-19T14:14:11Z", "2026-03-20T14:12:40Z", "2026-03-20T02:21:02Z", "2026-03-21T02:21:58Z")),
    ("San Francisco", 37.7749, -122.4194, "2026-06-21T00:00:00Z", ("2026-06-20T12:47:38Z", "2026-06-21T12:47:51Z", "2026-06-20T03:34:50Z", "2026-06-21T03:35:04Z")),
    ("San Francisco", 37.7749, -122.4194, "2026-09-23T06:00:00Z", ("2026-09-22T13:57:26Z", "2026-09-23T13:58:17Z", "2026-09-23T02:06:31Z", "2026-09-24T02:04:58Z")),
    ("San Francisco", 37.7749, -122.4194, "2026-12-21T12:00:00Z", ("2026-12-20T15:20:41Z", "2026-12-21T15:21:12Z", "2026-12-21T00:54:08Z", "2026-12-22T00:54:37Z")),
    ("London", 51.5074, -0.1278, "2026-03-20T12:00:00Z", ("2026-03-20T06:03:06Z", "2026-03-21T06:00:49Z", "2026-03-19T18:12:06Z", "2026-03-20T18:13:48Z")),
    ("London", 51.5074, -0.1278, "2026-06-21T00:00:00Z", ("2026-06-20T03:42:34Z", "2026-06-21T03:42:45Z", "2026-06-20T20:21:41Z", "2026-06-21T20:21:54Z")),
    ("London", 51.5074, -0.1278, "2026-09-23T06:00:00Z", ("2026-09-23T05:47:49Z", "2026-09-24T05:49:25Z", "2026-09-22T17:59:16Z", "2026-09-23T17:56:58Z")),
    ("London", 51.5074, -0.1278, "2026-12-21T12:00:00Z", ("2026-12-21T08:03:20Z", "2026-12-22T08:03:50Z", "2026-12-20T15:53:21Z", "2026-12-21T15:53:48Z")),
    ("New York", 40.7128, -74.006, "2026-03-20T12:00:00Z", ("2026-03-20T10:59:03Z", "2026-03-21T10:57:24Z", "2026-03-19T23:07:22Z", "2026-03-20T23:08:26Z")),
    ("New York", 40.7128, -74.006, "2026-06-21T00:00:00Z", ("2026-06-20T09:24:34Z", "2026-06-21T09:24:46Z", "2026-06-20T00:30:32Z", "2026-06-21T00:30:47Z")),
    ("New York", 40.7128, -74.006, "2026-09-23T06:00:00Z", ("2026-09-22T10:43:24Z", "2026-09-23T10:44:23Z", "2026-09-22T22:53:17Z", "2026-09-23T22:51:35Z")),
    ("New York", 40.7128, -74.006, "2026-12-21T12:00:00Z", ("2026-12-20T12:15:45Z", "2026-12-21T12:16:16Z", "2026-12-20T21:31:38Z", "2026-12-21T21:32:06Z")),
    ("Delhi", 28.6139, 77.209, "2026-03-20T12:00:00Z", ("2026-03-20T00:55:14Z", "2026-03-21T00:54:05Z", "2026-03-19T13:01:57Z", "2026-03-20T13:02:31Z")),
    ("Delhi", 28.6139, 77.209, "2026-06-21T00:00:00Z", ("2026-06-20T23:53:41Z", "2026-06-21T23:53:54Z", "2026-06-20T13:51:58Z", "2026-06-21T13:52:11Z")),
    ("Delhi", 28.6139, 77.209, "2026-09-23T06:00:00Z", ("2026-09-23T00:39:44Z", "2026-09-24T00:40:14Z", "2026-09-22T12:48:16Z", "2026-09-23T12:47:04Z")),
    ("Delhi", 28.6139, 77.209, "2026-12-21T12:00:00Z", ("2026-12-21T01:39:14Z", "2026-12-22T01:39:44Z", "2026-12-21T11:59:00Z", "2026-12-22T11:59:30Z")),
    ("Tokyo", 35.6762, 139.6503, "2026-03-20T12:00:00Z", ("2026-03-19T20:45:33Z", "2026-03-20T20:44:07Z", "2026-03-20T08:52:55Z", "2026-03-21T08:53:45Z")),
    ("Tokyo", 35.6762, 139.6503, "2026-06-21T00:00:00Z", ("2026-06-20T19:25:35Z", "2026-06-21T19:25:48Z", "2026-06-20T10:00:27Z", "2026-06-21T10:00:41Z")),
    ("Tokyo", 35.6762, 139.6503, "2026-09-23T06:00:00Z", ("2026-09-22T20:29:31Z", "2026-09-23T20:30:17Z", "2026-09-22T08:39:12Z", "2026-09-23T08:37:44Z")),
    ("Tokyo", 35.6762, 139.6503, "2026-12-21T12:00:00Z", ("2026-12-20T21:46:44Z", "2026-12-21T21:47:15Z", "2026-12-21T07:31:48Z", "2026-12-22T07:32:17Z")),
    ("Sydney", -33.8688, 151.2093, "2026-03-20T12:00:00Z", ("2026-03-19T19:57:44Z", "2026-03-20T19:58:30Z", "2026-03-20T08:07:10Z", "2026-03-21T08:05:49Z")),
    ("Sydney", -33.8688, 151.2093, "2026-06-21T00:00:00Z", ("2026-06-20T20:59:44Z", "2026-06-21T20:59:57Z", "2026-06-20T06:53:50Z", "2026-06-21T06:54:02Z")),
    ("Sydney", -33.8688, 151.2093, "2026-09-23T06:00:00Z", ("2026-09-22T19:43:45Z", "2026-09-23T19:42:21Z", "2026-09-22T07:51:28Z", "2026-09-23T07:52:09Z")),
    ("Sydney", -33.8688, 151.2093, "2026-12-21T12:00:00Z", ("2026-12-20T18:40:22Z", "2026-12-21T18:40:51Z", "2026-12-21T09:05:41Z", "2026-12-22T09:06:10Z")),
    ("Cape Town", -33.9249, 18.4241, "2026-03-20T12:00:00Z", ("2026-03-20T04:49:09Z", "2026-03-21T04:49:56Z", "2026-03-19T16:59:10Z", "2026-03-20T16:57:49Z")),
    ("Cape Town", -33.9249, 18.4241, "2026-06-21T00:00:00Z", ("2026-06-20T05:50:52Z", "2026-06-21T05:51:06Z", "2026-06-20T15:44:54Z", "2026-06-21T15:45:07Z")),
    ("Cape Town", -33.9249, 18.4241, "2026-09-23T06:00:00Z", ("2026-09-23T04:34:22Z", "2026-09-24T04:32:58Z", "2026-09-22T16:42:51Z", "2026-09-23T16:43:33Z")),
    ("Cape Town", -33.9249, 18.4241, "2026-12-21T12:00:00Z", ("2026-12-21T03:31:32Z", "2026-12-22T03:32:01Z", "2026-12-20T17:56:39Z", "2026-12-21T17:57:09Z")),
    ("Sao Paulo", -23.5505, -46.6333, "2026-03-20T12:00:00Z", ("2026-03-20T09:10:01Z", "2026-03-21T09:10:25Z", "2026-03-19T21:18:29Z", "2026-03-20T21:17:30Z")),
    ("Sao Paulo", -23.5505, -46.6333, "2026-06-21T00:00:00Z", ("2026-06-20T09:47:27Z", "2026-06-21T09:47:41Z", "2026-06-20T20:28:52Z", "2026-06-21T20:29:05Z")),
    ("Sao Paulo", -23.5505, -46.6333, "2026-09-23T06:00:00Z", ("2026-09-22T08:55:55Z", "2026-09-23T08:54:53Z", "2026-09-22T21:02:52Z", "2026-09-23T21:03:11Z")),
    ("Sao Paulo", -23.5505, -46.6333, "2026-12-21T12:00:00Z", ("2026-12-21T08:16:41Z", "2026-12-22T08:17:11Z", "2026-12-20T21:52:08Z", "2026-12-21T21:52:39Z")),
    ("Quito", -0.1807, -78.4678, "2026-03-20T12:00:00Z", ("2026-03-20T11:17:48Z", "2026-03-21T11:17:31Z", "2026-03-19T23:24:59Z", "2026-03-20T23:24:41Z")),
    ("Quito", -0.1807, -78.4678, "2026-06-21T00:00:00Z", ("2026-06-20T11:11:58Z", "2026-06-21T11:12:12Z", "2026-06-20T23:19:04Z", "2026-06-21T23:19:17Z")),
    ("Quito", -0.1807, -78.4678, "2026-09-23T06:00:00Z", ("2026-09-22T11:03:07Z", "2026-09-23T11:02:45Z", "2026-09-22T23:09:56Z", "2026-09-23T23:09:35Z")),
    ("Quito", -0.1807, -78.4678, "2026-12-21T12:00:00Z", ("2026-12-21T11:07:46Z", "2026-12-22T11:08:16Z", "2026-12-20T23:15:50Z", "2026-12-21T23:16:19Z")),
    ("Nairobi", -1.2921, 36.8219, "2026-03-20T12:00:00Z", ("2026-03-20T03:36:43Z", "2026-03-21T03:36:28Z", "2026-03-19T15:43:57Z", "2026-03-20T15:43:37Z")),
    ("Nairobi", -1.2921, 36.8219, "2026-06-21T00:00:00Z", ("2026-06-20T03:32:40Z", "2026-06-21T03:32:53Z", "2026-06-20T15:35:54Z", "2026-06-21T15:36:07Z")),
    ("Nairobi", -1.2921, 36.8219, "2026-09-23T06:00:00Z", ("2026-09-23T03:21:42Z", "2026-09-24T03:21:19Z", "2026-09-22T15:28:53Z", "2026-09-23T15:28:34Z")),
    ("Nairobi", -1.2921, 36.8219, "2026-12-21T12:00:00Z", ("2026-12-21T03:24:31Z", "2026-12-22T03:25:01Z", "2026-12-20T15:36:26Z", "2026-12-21T15:36:56Z")),
    ("Bangkok", 13.7563, 100.5018, "2026-03-20T12:00:00Z", ("2026-03-19T23:22:13Z", "2026-03-20T23:21:32Z", "2026-03-20T11:29:00Z", "2026-03-21T11:29:05Z")),
    ("Bangkok", 13.7563, 100.5018, "2026-06-21T00:00:00Z", ("2026-06-20T22:51:23Z", "2026-06-21T22:51:36Z", "2026-06-20T11:47:54Z", "2026-06-21T11:48:07Z")),
    ("Bangkok", 13.7563, 100.5018, "2026-09-23T06:00:00Z", ("2026-09-22T23:06:56Z", "2026-09-23T23:06:58Z", "2026-09-22T11:14:32Z", "2026-09-23T11:13:48Z")),
    ("Bangkok", 13.7563, 100.5018, "2026-12-21T12:00:00Z", ("2026-12-20T23:36:12Z", "2026-12-21T23:36:42Z", "2026-12-21T10:55:38Z", "2026-12-22T10:56:08Z")),
    ("Cairo", 30.0444, 31.2357, "2026-03-20T12:00:00Z", ("2026-03-20T03:58:57Z", "2026-03-21T03:57:44Z", "2026-03-19T16:05:56Z", "2026-03-20T16:06:33Z")),
    ("Cairo", 30.0444, 31.2357, "2026-06-21T00:00:00Z", ("2026-06-20T02:53:57Z", "2026-06-21T02:54:09Z", "2026-06-20T16:59:20Z", "2026-06-21T16:59:33Z")),
    ("Cairo", 30.0444, 31.2357, "2026-09-23T06:00:00Z", ("2026-09-23T03:43:38Z", "2026-09-24T03:44:11Z", "2026-09-22T15:52:05Z", "2026-09-23T15:50:50Z")),
    ("Cairo", 30.0444, 31.2357, "2026-12-21T12:00:00Z", ("2026-12-21T04:46:29Z", "2026-12-22T04:46:59Z", "2026-12-20T14:59:11Z", "2026-12-21T14:59:40Z")),
    ("Auckland", -36.8485, 174.7633, "2026-03-20T12:00:00Z", ("2026-03-19T18:23:12Z", "2026-03-20T18:24:06Z", "2026-03-20T06:33:15Z", "2026-03-21T06:31:46Z")),
    ("Auckland", -36.8485, 174.7633, "2026-06-21T00:00:00Z", ("2026-06-20T19:33:26Z", "2026-06-21T19:33:40Z", "2026-06-20T05:11:40Z", "2026-06-21T05:11:52Z")),
    ("Auckland", -36.8485, 174.7633, "2026-09-23T06:00:00Z", ("2026-09-22T18:09:30Z", "2026-09-23T18:07:59Z", "2026-09-22T06:17:16Z", "2026-09-23T06:18:05Z")),
    ("Auckland", -36.8485, 174.7633, "2026-12-21T12:00:00Z", ("2026-12-20T16:57:43Z", "2026-12-21T16:58:11Z", "2026-12-21T07:39:51Z", "2026-12-22T07:40:21Z")),
    ("Honolulu", 21.3069, -157.8583, "2026-03-20T12:00:00Z", ("2026-03-19T16:35:55Z", "2026-03-20T16:35:00Z", "2026-03-20T04:42:28Z", "2026-03-21T04:42:47Z")),
    ("Honolulu", 21.3069, -157.8583, "2026-06-21T00:00:00Z", ("2026-06-20T15:49:59Z", "2026-06-21T15:50:12Z", "2026-06-20T05:16:03Z", "2026-06-21T05:16:17Z")),
    ("Honolulu", 21.3069, -157.8583, "2026-09-23T06:00:00Z", ("2026-09-22T16:20:08Z", "2026-09-23T16:20:24Z", "2026-09-23T04:27:34Z", "2026-09-24T04:26:36Z")),
    ("Honolulu", 21.3069, -157.8583, "2026-12-21T12:00:00Z", ("2026-12-20T17:03:52Z", "2026-12-21T17:04:22Z", "2026-12-21T03:54:34Z", "2026-12-22T03:55:04Z")),
    ("Kiritimati", 1.87, -157.4, "2026-03-20T12:00:00Z", ("2026-03-19T16:33:49Z", "2026-03-20T16:33:28Z", "2026-03-20T04:40:37Z", "2026-03-21T04:40:22Z")),
    ("Kiritimati", 1.87, -157.4, "2026-06-21T00:00:00Z", ("2026-06-20T16:24:11Z", "2026-06-21T16:24:24Z", "2026-06-20T04:38:11Z", "2026-06-21T04:38:24Z")),
    ("Kiritimati", 1.87, -157.4, "2026-09-23T06:00:00Z", ("2026-09-22T16:18:44Z", "2026-09-23T16:18:26Z", "2026-09-23T04:25:35Z", "2026-09-24T04:25:11Z")),
    ("Kiritimati", 1.87, -157.4, "2026-12-21T12:00:00Z", ("2026-12-20T16:26:40Z", "2026-12-21T16:27:10Z", "2026-12-21T04:28:06Z", "2026-12-22T04:28:36Z")),
    ("Perth", -31.9523, 115.8613, "2026-03-20T12:00:00Z", ("2026-03-19T22:19:21Z", "2026-03-20T22:20:02Z", "2026-03-20T10:28:19Z", "2026-03-21T10:27:03Z")),
    ("Perth", -31.9523, 115.8613, "2026-06-21T00:00:00Z", ("2026-06-20T23:16:22Z", "2026-06-21T23:16:35Z", "2026-06-20T09:20:02Z", "2026-06-21T09:20:14Z")),
    ("Perth", -31.9523, 115.8613, "2026-09-23T06:00:00Z", ("2026-09-22T22:05:05Z", "2026-09-23T22:03:46Z", "2026-09-22T10:12:52Z", "2026-09-23T10:13:29Z")),
    ("Perth", -31.9523, 115.8613, "2026-12-21T12:00:00Z", ("2026-12-20T21:06:52Z", "2026-12-21T21:07:21Z", "2026-12-21T11:22:04Z", "2026-12-22T11:22:34Z")),
    ("Apia", -13.8333, -171.7667, "2026-03-20T12:00:00Z", ("2026-03-19T17:30:46Z", "2026-03-20T17:30:52Z", "2026-03-20T05:38:21Z", "2026-03-21T05:37:40Z")),
    ("Apia", -13.8333, -171.7667, "2026-06-21T00:00:00Z", ("2026-06-20T17:49:18Z", "2026-06-21T17:49:31Z", "2026-06-20T05:08:02Z", "2026-06-21T05:08:15Z")),
    ("Apia", -13.8333, -171.7667, "2026-09-23T06:00:00Z", ("2026-09-22T17:16:13Z", "2026-09-23T17:15:29Z", "2026-09-23T05:23:14Z", "2026-09-24T05:23:16Z")),
    ("Apia", -13.8333, -171.7667, "2026-12-21T12:00:00Z", ("2026-12-20T16:56:15Z", "2026-12-21T16:56:44Z", "2026-12-21T05:53:30Z", "2026-12-22T05:54:00Z")),
    ("Ushuaia", -54.8019, -68.303, "2026-03-20T12:00:00Z", ("2026-03-20T10:34:11Z", "2026-03-21T10:36:08Z", "2026-03-19T22:48:24Z", "2026-03-20T22:45:52Z")),
    ("Ushuaia", -54.8019, -68.303, "2026-06-21T00:00:00Z", ("2026-06-20T12:58:15Z", "2026-06-21T12:58:29Z", "2026-06-20T20:11:27Z", "2026-06-21T20:11:40Z")),
    ("Ushuaia", -54.8019, -68.303, "2026-09-23T06:00:00Z", ("2026-09-22T10:21:09Z", "2026-09-23T10:18:36Z", "2026-09-22T22:31:43Z", "2026-09-23T22:33:34Z")),
    ("Ushuaia", -54.8019, -68.303, "2026-12-21T12:00:00Z", ("2026-12-21T07:50:57Z", "2026-12-22T07:51:26Z", "2026-12-21T01:11:17Z", "2026-12-22T01:11:48Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-03-20T12:00:00Z", ("2026-03-19T15:53:30Z", "2026-03-20T15:49:51Z", "2026-03-20T04:05:09Z", "2026-03-21T04:08:14Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-06-21T00:00:00Z", ("2026-06-20T10:56:12Z", "2026-06-21T10:56:19Z", "2026-06-20T08:48:45Z", "2026-06-21T08:49:06Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-09-23T06:00:00Z", ("2026-09-22T15:34:07Z", "2026-09-23T15:37:05Z", "2026-09-23T03:51:05Z", "2026-09-24T03:47:25Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-12-21T12:00:00Z", ("2026-12-20T19:56:44Z", "2026-12-21T19:57:19Z", "2026-12-20T23:40:32Z", "2026-12-21T23:40:58Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-06-21T12:00:00Z", ("2026-06-21T10:56:19Z", "2026-06-22T10:56:42Z", "2026-06-21T08:49:06Z", "2026-06-22T08:49:11Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-12-21T00:00:00Z", ("2026-12-20T19:56:44Z", "2026-12-21T19:57:19Z", "2026-12-20T23:40:32Z", "2026-12-21T23:40:58Z")),
    ("Reykjavik", 64.15, -21.94, "2026-03-20T12:00:00Z", ("2026-03-20T07:28:12Z", "2026-03-21T07:24:38Z", "2026-03-19T19:40:51Z", "2026-03-20T19:43:50Z")),
    ("Reykjavik", 64.15, -21.94, "2026-06-21T00:00:00Z", ("2026-06-20T02:53:56Z", "2026-06-21T02:54:01Z", "2026-06-20T00:04:36Z", "2026-06-21T00:04:59Z")),
    ("Reykjavik", 64.15, -21.94, "2026-09-23T06:00:00Z", ("2026-09-22T07:10:15Z", "2026-09-23T07:13:07Z", "2026-09-22T19:29:01Z", "2026-09-23T19:25:28Z")),
    ("Reykjavik", 64.15, -21.94, "2026-12-21T12:00:00Z", ("2026-12-21T11:21:26Z", "2026-12-22T11:21:55Z", "2026-12-20T15:29:54Z", "2026-12-21T15:30:17Z")),
    ("Reykjavik", 64.15, -21.94, "2026-06-21T12:00:00Z", ("2026-06-21T02:54:01Z", "2026-06-22T02:54:17Z", "2026-06-21T00:04:59Z", "2026-06-22T00:05:10Z")),
    ("Reykjavik", 64.15, -21.94, "2026-12-21T00:00:00Z", ("2026-12-20T11:20:48Z", "2026-12-21T11:21:26Z", "2026-12-20T15:29:54Z", "2026-12-21T15:30:17Z")),
    ("Tromso", 69.65, 18.96, "2026-03-20T12:00:00Z", ("2026-03-20T04:43:22Z", "2026-03-21T04:38:50Z", "2026-03-19T16:58:03Z", "2026-03-20T17:02:02Z")),
    ("Tromso", 69.65, 18.96, "2026-06-21T00:00:00Z", (None, None, None, None)),
    ("Tromso", 69.65, 18.96, "2026-09-23T06:00:00Z", ("2026-09-23T04:27:20Z", "2026-09-24T04:31:11Z", "2026-09-22T16:48:10Z", "2026-09-23T16:43:38Z")),
    ("Tromso", 69.65, 18.96, "2026-12-21T12:00:00Z", (None, None, None, None)),
    ("Tromso", 69.65, 18.96, "2026-06-21T12:00:00Z", (None, None, None, None)),
    ("Tromso", 69.65, 18.96, "2026-12-21T00:00:00Z", (None, None, None, None)),
    ("Anadyr", 64.7314, 177.5097, "2026-03-20T12:00:00Z", ("2026-03-19T18:12:16Z", "2026-03-20T18:08:38Z", "2026-03-20T06:24:31Z", "2026-03-21T06:27:35Z")),
    ("Anadyr", 64.7314, 177.5097, "2026-06-21T00:00:00Z", ("2026-06-20T13:19:00Z", "2026-06-21T13:19:09Z", "2026-06-20T11:04:11Z", "2026-06-21T11:04:30Z")),
    ("Anadyr", 64.7314, 177.5097, "2026-09-23T06:00:00Z", ("2026-09-22T17:53:33Z", "2026-09-23T17:56:30Z", "2026-09-22T06:13:26Z", "2026-09-23T06:09:47Z")),
    ("Anadyr", 64.7314, 177.5097, "2026-12-21T12:00:00Z", ("2026-12-20T22:13:49Z", "2026-12-21T22:14:23Z", "2026-12-21T02:01:44Z", "2026-12-22T02:02:11Z")),
    ("Anadyr", 64.7314, 177.5097, "2026-06-21T12:00:00Z", ("2026-06-20T13:19:00Z", "2026-06-21T13:19:09Z", "2026-06-21T11:04:30Z", "2026-06-22T11:04:34Z")),
    ("Anadyr", 64.7314, 177.5097, "2026-12-21T00:00:00Z", ("2026-12-20T22:13:49Z", "2026-12-21T22:14:23Z", "2026-12-20T02:01:27Z", "2026-12-21T02:01:44Z")),
    ("Rovaniemi", 66.5007, 25.7208, "2026-03-20T12:00:00Z", ("2026-03-20T04:17:26Z", "2026-03-21T04:13:30Z", "2026-03-19T16:30:13Z", "2026-03-20T16:33:35Z")),
    ("Rovaniemi", 66.5007, 25.7208, "2026-06-21T00:00:00Z", (None, None, None, None)),
    ("Rovaniemi", 66.5007, 25.7208, "2026-09-23T06:00:00Z", ("2026-09-23T04:01:25Z", "2026-09-24T04:04:39Z", "2026-09-22T16:19:43Z", "2026-09-23T16:15:48Z")),
    ("Rovaniemi", 66.5007, 25.7208, "2026-12-21T12:00:00Z", ("2026-12-21T09:06:06Z", "2026-12-22T09:06:35Z", "2026-12-21T11:24:11Z", "2026-12-22T11:24:43Z")),
    ("Rovaniemi", 66.5007, 25.7208, "2026-06-21T12:00:00Z", (None, None, None, None)),
    ("Rovaniemi", 66.5007, 25.7208, "2026-12-21T00:00:00Z", ("2026-12-20T09:05:19Z", "2026-12-21T09:06:06Z", "2026-12-20T11:23:57Z", "2026-12-21T11:24:11Z")),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-03-20T12:00:00Z", ("2026-03-19T20:35:59Z", "2026-03-20T20:39:22Z", "2026-03-20T08:57:14Z", "2026-03-21T08:53:16Z")),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-06-21T00:00:00Z", ("2026-06-20T01:38:51Z", "2026-06-21T01:39:17Z", "2026-06-20T03:44:09Z", "2026-06-21T03:44:10Z")),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-09-23T06:00:00Z", ("2026-09-22T20:24:19Z", "2026-09-23T20:20:21Z", "2026-09-22T08:39:18Z", "2026-09-23T08:42:34Z")),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-12-21T12:00:00Z", (None, None, None, None)),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-06-21T12:00:00Z", ("2026-06-21T01:39:17Z", "2026-06-22T01:39:27Z", "2026-06-21T03:44:10Z", "2026-06-22T03:44:29Z")),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-12-21T00:00:00Z", (None, None, None, None)),
    ("Longyearbyen", 78.2232, 15.6469, "2026-03-20T12:00:00Z", ("2026-03-20T04:50:52Z", "2026-03-21T04:43:00Z", "2026-03-19T17:15:29Z", "2026-03-20T17:22:50Z")),
    ("Longyearbyen", 78.2232, 15.6469, "2026-06-21T00:00:00Z", (None, None, None, None)),
    ("Longyearbyen", 78.2232, 15.6469, "2026-09-23T06:00:00Z", ("2026-09-23T04:34:07Z", "2026-09-24T04:41:17Z", "2026-09-22T17:09:24Z", "2026-09-23T17:01:36Z")),
    ("Longyearbyen", 78.2232, 15.6469, "2026-12-21T12:00:00Z", (None, None, None, None)),
    ("Longyearbyen", 78.2232, 15.6469, "2026-06-21T12:00:00Z", (None, None, None, None)),
    ("Longyearbyen", 78.2232, 15.6469, "2026-12-21T00:00:00Z", (None, None, None, None)),
    ("Alert", 82.4971, -62.3415, "2026-03-20T12:00:00Z", ("2026-03-20T09:52:21Z", "2026-03-21T09:40:03Z", "2026-03-19T22:35:47Z", "2026-03-20T22:47:40Z")),
    ("Alert", 82.4971, -62.3415, "2026-06-21T00:00:00Z", (None, None, None, None)),
    ("Alert", 82.4971, -62.3415, "2026-09-23T06:00:00Z", ("2026-09-22T09:27:59Z", "2026-09-23T09:39:38Z", "2026-09-22T22:29:36Z", "2026-09-23T22:17:29Z")),
    ("Alert", 82.4971, -62.3415, "2026-12-21T12:00:00Z", (None, None, None, None)),
    ("Alert", 82.4971, -62.3415, "2026-06-21T12:00:00Z", (None, None, None, None)),
    ("Alert", 82.4971, -62.3415, "2026-12-21T00:00:00Z", (None, None, None, None)),
    ("McMurdo", -77.85, 166.67, "2026-03-20T12:00:00Z", ("2026-03-19T18:38:05Z", "2026-03-20T18:45:12Z", "2026-03-20T07:19:47Z", "2026-03-21T07:12:10Z")),
    ("McMurdo", -77.85, 166.67, "2026-06-21T00:00:00Z", (None, None, None, None)),
    ("McMurdo", -77.85, 166.67, "2026-09-23T06:00:00Z", ("2026-09-22T18:30:59Z", "2026-09-23T18:23:25Z", "2026-09-22T06:57:36Z", "2026-09-23T07:04:32Z")),
    ("McMurdo", -77.85, 166.67, "2026-12-21T12:00:00Z", (None, None, None, None)),
    ("McMurdo", -77.85, 166.67, "2026-06-21T12:00:00Z", (None, None, None, None)),
    ("McMurdo", -77.85, 166.67, "2026-12-21T00:00:00Z", (None, None, None, None)),
)

# Same file, noaa_08793 (NOAA formulas, Sun centre at -0.8793 deg): the FIRST case of each place.
ORACLE_SUN_NOAA = (
    ("San Francisco", 37.7749, -122.4194, "2026-03-20T12:00:00Z", ("2026-03-19T14:14:11Z", "2026-03-20T14:12:40Z", "2026-03-20T02:21:05Z", "2026-03-21T02:22:01Z")),
    ("London", 51.5074, -0.1278, "2026-03-20T12:00:00Z", ("2026-03-20T06:03:06Z", "2026-03-21T06:00:49Z", "2026-03-19T18:12:09Z", "2026-03-20T18:13:51Z")),
    ("New York", 40.7128, -74.006, "2026-03-20T12:00:00Z", ("2026-03-20T10:59:04Z", "2026-03-21T10:57:24Z", "2026-03-19T23:07:24Z", "2026-03-20T23:08:28Z")),
    ("Delhi", 28.6139, 77.209, "2026-03-20T12:00:00Z", ("2026-03-20T00:55:15Z", "2026-03-21T00:54:05Z", "2026-03-19T13:02:00Z", "2026-03-20T13:02:33Z")),
    ("Tokyo", 35.6762, 139.6503, "2026-03-20T12:00:00Z", ("2026-03-19T20:45:34Z", "2026-03-20T20:44:08Z", "2026-03-20T08:52:57Z", "2026-03-21T08:53:47Z")),
    ("Sydney", -33.8688, 151.2093, "2026-03-20T12:00:00Z", ("2026-03-19T19:57:45Z", "2026-03-20T19:58:32Z", "2026-03-20T08:07:11Z", "2026-03-21T08:05:50Z")),
    ("Cape Town", -33.9249, 18.4241, "2026-03-20T12:00:00Z", ("2026-03-20T04:49:10Z", "2026-03-21T04:49:57Z", "2026-03-19T16:59:11Z", "2026-03-20T16:57:50Z")),
    ("Sao Paulo", -23.5505, -46.6333, "2026-03-20T12:00:00Z", ("2026-03-20T09:10:02Z", "2026-03-21T09:10:26Z", "2026-03-19T21:18:30Z", "2026-03-20T21:17:31Z")),
    ("Quito", -0.1807, -78.4678, "2026-03-20T12:00:00Z", ("2026-03-20T11:17:49Z", "2026-03-21T11:17:31Z", "2026-03-19T23:25:00Z", "2026-03-20T23:24:43Z")),
    ("Nairobi", -1.2921, 36.8219, "2026-03-20T12:00:00Z", ("2026-03-20T03:36:44Z", "2026-03-21T03:36:29Z", "2026-03-19T15:43:58Z", "2026-03-20T15:43:39Z")),
    ("Bangkok", 13.7563, 100.5018, "2026-03-20T12:00:00Z", ("2026-03-19T23:22:14Z", "2026-03-20T23:21:33Z", "2026-03-20T11:29:02Z", "2026-03-21T11:29:07Z")),
    ("Cairo", 30.0444, 31.2357, "2026-03-20T12:00:00Z", ("2026-03-20T03:58:57Z", "2026-03-21T03:57:45Z", "2026-03-19T16:05:58Z", "2026-03-20T16:06:35Z")),
    ("Auckland", -36.8485, 174.7633, "2026-03-20T12:00:00Z", ("2026-03-19T18:23:13Z", "2026-03-20T18:24:07Z", "2026-03-20T06:33:16Z", "2026-03-21T06:31:47Z")),
    ("Honolulu", 21.3069, -157.8583, "2026-03-20T12:00:00Z", ("2026-03-19T16:35:55Z", "2026-03-20T16:35:01Z", "2026-03-20T04:42:30Z", "2026-03-21T04:42:49Z")),
    ("Kiritimati", 1.87, -157.4, "2026-03-20T12:00:00Z", ("2026-03-19T16:33:49Z", "2026-03-20T16:33:29Z", "2026-03-20T04:40:38Z", "2026-03-21T04:40:24Z")),
    ("Perth", -31.9523, 115.8613, "2026-03-20T12:00:00Z", ("2026-03-19T22:19:22Z", "2026-03-20T22:20:03Z", "2026-03-20T10:28:21Z", "2026-03-21T10:27:04Z")),
    ("Apia", -13.8333, -171.7667, "2026-03-20T12:00:00Z", ("2026-03-19T17:30:47Z", "2026-03-20T17:30:53Z", "2026-03-20T05:38:22Z", "2026-03-21T05:37:41Z")),
    ("Ushuaia", -54.8019, -68.303, "2026-03-20T12:00:00Z", ("2026-03-20T10:34:13Z", "2026-03-21T10:36:09Z", "2026-03-19T22:48:25Z", "2026-03-20T22:45:53Z")),
    ("Fairbanks", 64.8378, -147.7164, "2026-03-20T12:00:00Z", ("2026-03-19T15:53:29Z", "2026-03-20T15:49:50Z", "2026-03-20T04:05:13Z", "2026-03-21T04:08:18Z")),
    ("Reykjavik", 64.15, -21.94, "2026-03-20T12:00:00Z", ("2026-03-20T07:28:11Z", "2026-03-21T07:24:37Z", "2026-03-19T19:40:54Z", "2026-03-20T19:43:53Z")),
    ("Tromso", 69.65, 18.96, "2026-03-20T12:00:00Z", ("2026-03-20T04:43:21Z", "2026-03-21T04:38:48Z", "2026-03-19T16:58:07Z", "2026-03-20T17:02:06Z")),
    ("Anadyr", 64.7314, 177.5097, "2026-03-20T12:00:00Z", ("2026-03-19T18:12:14Z", "2026-03-20T18:08:37Z", "2026-03-20T06:24:34Z", "2026-03-21T06:27:38Z")),
    ("Rovaniemi", 66.5007, 25.7208, "2026-03-20T12:00:00Z", ("2026-03-20T04:17:24Z", "2026-03-21T04:13:29Z", "2026-03-19T16:30:17Z", "2026-03-20T16:33:38Z")),
    ("Dumont d'Urville", -66.6667, 140.0, "2026-03-20T12:00:00Z", ("2026-03-19T20:36:00Z", "2026-03-20T20:39:23Z", "2026-03-20T08:57:15Z", "2026-03-21T08:53:18Z")),
    ("Longyearbyen", 78.2232, 15.6469, "2026-03-20T12:00:00Z", ("2026-03-20T04:50:48Z", "2026-03-21T04:42:57Z", "2026-03-19T17:15:35Z", "2026-03-20T17:22:55Z")),
    ("Alert", 82.4971, -62.3415, "2026-03-20T12:00:00Z", ("2026-03-20T09:52:15Z", "2026-03-21T09:39:57Z", "2026-03-19T22:35:56Z", "2026-03-20T22:47:49Z")),
    ("McMurdo", -77.85, 166.67, "2026-03-20T12:00:00Z", ("2026-03-19T18:38:07Z", "2026-03-20T18:45:14Z", "2026-03-20T07:19:48Z", "2026-03-21T07:12:11Z")),
)
# fmt: on


def _instant(text: str | None) -> datetime | None:
    return None if text is None else parse_z(text)


class TestAgainstTheIndependentOracle:
    """Literals from W3-O (dev-g1's swisseph + NOAA oracle; the JSON is never imported).

    Against swisseph: every one of the 126 cases, each of the four events, to
    1 second. The oracle writes whole seconds, so a faithful route differs by up
    to 0.5 s; measured worst over all 424 events: 0.500 s. A None literal
    means the engine finds no such event (polar day/night) and the route must
    answer null, in both directions (80 nulls, 0 disagreements).

    Against NOAA (Sun centre at -0.8793 degrees, the altitude swisseph's event
    measured at in Wave 1): an independent formula, first case of each place.
    The measured worst difference is 3.9 s below 45 degrees, 4.9 s from 45 to
    60, and up to 26.5 s from 60 to 66 degrees (Fairbanks and Anadyr at the
    June solstice, where the Sun skims the horizon so a tiny altitude
    difference moves the event by tens of seconds). In every one of those the
    route minus NOAA equals the oracle's own recorded swisseph-minus-NOAA gap
    to 0.5 s: the difference lives between the two formulas, not in this route.
    """

    def test_the_literal_table_is_complete(self):
        assert len(ORACLE_SUN_CASES) == 126
        places = {row[0] for row in ORACLE_SUN_CASES}
        assert len(places) == 27
        assert {"Kiritimati", "Tromso", "Alert", "McMurdo", "Apia", "Fairbanks"} <= places
        all_null = [row for row in ORACLE_SUN_CASES if all(v is None for v in row[4])]
        assert len(all_null) == 20
        assert len(ORACLE_SUN_NOAA) == 27

    @pytest.mark.parametrize("row", ORACLE_SUN_CASES, ids=lambda r: f"{r[0]}@{r[3]}")
    def test_route_matches_swisseph_to_one_second(self, client, row):
        place, lat, lon, instant, expected = row
        response = get(client, (lat, lon), instant)
        assert response.status_code == 200
        body = response.json()
        for key, literal in zip(("previous_sunrise", "next_sunrise", "previous_sunset", "next_sunset"), expected):
            if literal is None:
                assert body[key] is None, (place, instant, key)
            else:
                assert body[key] is not None, (place, instant, key)
                assert abs(parse_z(body[key]) - _instant(literal)) <= timedelta(seconds=1), (place, instant, key)
        if all(v is None for v in expected):
            assert body["sunset"] is None, (place, instant)

    @pytest.mark.parametrize("row", ORACLE_SUN_NOAA, ids=lambda r: f"{r[0]}@{r[3]}")
    def test_route_is_close_to_noaa(self, client, row):
        place, lat, lon, instant, expected = row
        tolerance = timedelta(seconds=6 if abs(lat) < 60 else 30)
        body = get(client, (lat, lon), instant).json()
        for key, literal in zip(("previous_sunrise", "next_sunrise", "previous_sunset", "next_sunset"), expected):
            if literal is None:
                continue  # NOAA found no event; the swisseph test above pins the nulls
            assert body[key] is not None, (place, instant, key)
            assert abs(parse_z(body[key]) - _instant(literal)) <= tolerance, (place, instant, key)
