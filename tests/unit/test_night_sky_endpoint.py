"""W2-A route tests: GET /astrology/night-sky datetime_str semantics.

A malformed ``datetime_str`` used to be swallowed and answered with *now*;
per the wave-2 contract it is now 422 with an exact message. Every other
response key and type is unchanged (pinned here). The router is mounted bare
and receives its /astrology prefix at include time, like the app does.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import astrology


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(astrology.router, prefix="/astrology")
    return TestClient(app)


class TestNightSkyDatetime:
    def test_malformed_datetime_is_422_with_exact_detail(self, client: TestClient):
        for bad in ("not-a-date", "2026-13-45T99:99:99Z", "2026-03-20T14:46:00+25:00", "banana"):
            response = client.get("/astrology/night-sky", params={"datetime_str": bad})
            assert response.status_code == 422, bad
            assert response.json() == {"detail": "malformed datetime_str; expected ISO-8601"}

    def test_absent_datetime_is_200_now(self, client: TestClient):
        response = client.get("/astrology/night-sky")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_valid_datetime_is_200(self, client: TestClient):
        response = client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_z_suffix_and_naive_both_work(self, client: TestClient):
        z = client.get("/astrology/night-sky", params={"datetime_str": "2027-07-01T12:00:00Z"})
        naive = client.get("/astrology/night-sky", params={"datetime_str": "2027-07-01T12:00:00"})
        assert z.status_code == naive.status_code == 200
        assert z.json() == naive.json()

    def test_observer_keys_are_pinned(self, client: TestClient):
        observer = client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"}).json()[
            "observer"
        ]
        assert set(observer) == {
            "latitude",
            "longitude",
            "local_sidereal_time_deg",
            "local_sidereal_time_hms",
        }

    def test_response_key_set_is_pinned_and_unchanged(self, client: TestClient):
        payload = client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"}).json()
        assert set(payload) == {
            "status",
            "timestamp_utc",
            "observer",
            "moon",
            "planets",
            "visible_planets_count",
            "sacred_stars",
            "visible_stars_count",
            "provenance",
        }


class TestNightSkySupportedRange:
    """W2-H: /night-sky enforces the same supported range as /earth-state (1800-2200 UTC).

    Found by W2-R1: 5400-01-01 and 9999-12-31 answered 500 (swisseph.Error
    escaped: no ephemeris file that far out), while 2201 and 3000 answered 200
    and 0001-01-01 answered 200 with positions far outside anything the app
    supports. The detail is byte-identical to /earth-state's for the same input.
    """

    OUT_OF_RANGE = [
        "1799-12-31T23:59:59Z",
        "2201-01-01T00:00:00Z",
        "0001-01-01T00:00:00Z",
        "3000-01-01T00:00:00Z",
        "5400-01-01T00:00:00Z",
        "9999-12-31T23:59:59Z",
    ]

    @pytest.mark.parametrize("moment", OUT_OF_RANGE)
    def test_out_of_range_is_422_with_the_earth_state_detail(self, client: TestClient, moment: str):
        night = client.get("/astrology/night-sky", params={"datetime_str": moment})
        earth = client.get("/astrology/earth-state", params={"datetime_str": moment})
        assert night.status_code == 422, moment
        assert earth.status_code == 422, moment
        assert night.json() == earth.json()
        assert night.json()["detail"].startswith("time outside supported range 1800-01-01..2200-12-31 UTC")

    @pytest.mark.parametrize("moment", ["1800-01-01T00:00:00Z", "2200-12-31T23:59:59Z"])
    def test_the_supported_edges_answer_200(self, client: TestClient, moment: str):
        response = client.get("/astrology/night-sky", params={"datetime_str": moment})
        assert response.status_code == 200, moment
        assert response.json()["status"] == "success"

    @pytest.mark.parametrize("extreme", ["0001-01-01T00:00:00+14:00", "9999-12-31T23:59:59-14:00"])
    def test_extreme_offsets_are_422_not_an_overflow(self, client: TestClient, extreme: str):
        response = client.get("/astrology/night-sky", params={"datetime_str": extreme})
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], str)

    def test_the_range_is_judged_in_utc_not_in_the_written_offset(self, client: TestClient):
        # 1800-01-01T05:00+14:00 is 1799-12-31T15:00Z: outside; 1799-12-31T23:00-14:00 is 1800-01-01T13:00Z: inside
        outside = client.get("/astrology/night-sky", params={"datetime_str": "1800-01-01T05:00:00+14:00"})
        inside = client.get("/astrology/night-sky", params={"datetime_str": "1799-12-31T23:00:00-14:00"})
        assert outside.status_code == 422
        assert inside.status_code == 200

    def test_the_guard_runs_before_any_computation(self, client: TestClient, monkeypatch):
        from core import celestial_sky

        def must_not_run(**_kwargs):
            raise AssertionError("calculate_night_sky must not run for an unsupported instant")

        monkeypatch.setattr(celestial_sky, "calculate_night_sky", must_not_run)
        response = client.get("/astrology/night-sky", params={"datetime_str": "5400-01-01T00:00:00Z"})
        assert response.status_code == 422

    def test_absent_and_blank_datetime_still_mean_now(self, client: TestClient):
        assert client.get("/astrology/night-sky").status_code == 200
        assert client.get("/astrology/night-sky", params={"datetime_str": ""}).status_code == 200

    def test_a_swisseph_error_is_a_clean_503(self, client: TestClient, monkeypatch):
        import swisseph as swe

        from core import celestial_sky

        def boom(**_kwargs):
            raise swe.Error("SwissEph file 'sepl_96.se1' not found")

        monkeypatch.setattr(celestial_sky, "calculate_night_sky", boom)
        response = client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"})
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}

    def test_a_real_bug_is_not_called_unavailable(self, client: TestClient, monkeypatch):
        from core import celestial_sky

        def bug(**_kwargs):
            raise KeyError("a real bug")

        monkeypatch.setattr(celestial_sky, "calculate_night_sky", bug)
        with pytest.raises(KeyError):
            client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"})

    def test_a_200_keeps_exactly_the_same_keys_at_the_edges(self, client: TestClient):
        middle = client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"}).json()
        for moment in ("1800-01-01T00:00:00Z", "2200-12-31T23:59:59Z"):
            edge = client.get("/astrology/night-sky", params={"datetime_str": moment}).json()
            assert set(edge) == set(middle), moment
            assert set(edge["observer"]) == set(middle["observer"]), moment


class TestNightSkyPlaceRange:
    """W3-R3 (F3): /night-sky refuses places that do not exist, before any computation.

    It used to answer 200 for latitude=95 or longitude=1000000 and echo the nonsense, which the client
    validator then rejected as an invalid response. Same wording and plain-string detail as /sun-events.
    """

    @pytest.mark.parametrize("latitude", ["95", "90.0001", "-91", "-1000", "nan", "inf", "-inf"])
    def test_bad_latitude_is_422_with_a_string_detail(self, client: TestClient, latitude: str):
        response = client.get("/astrology/night-sky", params={"latitude": latitude, "longitude": "10"})
        assert response.status_code == 422, latitude
        assert response.json() == {"detail": "latitude must be a number between -90 and 90"}

    @pytest.mark.parametrize("longitude", ["181", "180.0001", "-180.0001", "1000000", "-720", "nan", "inf", "-inf"])
    def test_bad_longitude_is_422_with_a_string_detail(self, client: TestClient, longitude: str):
        response = client.get("/astrology/night-sky", params={"latitude": "10", "longitude": longitude})
        assert response.status_code == 422, longitude
        assert response.json() == {"detail": "longitude must be a number between -180 and 180"}

    @pytest.mark.parametrize(("latitude", "longitude"), [(90, 180), (-90, -180), (0, 0), (89.9999, 179.9999)])
    def test_the_boundaries_are_accepted(self, client: TestClient, latitude, longitude):
        response = client.get(
            "/astrology/night-sky",
            params={"latitude": latitude, "longitude": longitude, "datetime_str": "2026-03-20T14:46:00Z"},
        )
        assert response.status_code == 200, (latitude, longitude)

    def test_the_place_is_judged_before_any_computation(self, client: TestClient, monkeypatch):
        from core import celestial_sky

        def must_not_run(**_kwargs):
            raise AssertionError("calculate_night_sky must not run for an impossible place")

        monkeypatch.setattr(celestial_sky, "calculate_night_sky", must_not_run)
        for params in ({"latitude": "95"}, {"longitude": "181"}, {"latitude": "nan"}):
            assert client.get("/astrology/night-sky", params=params).status_code == 422, params

    def test_the_default_place_still_answers_200(self, client: TestClient):
        response = client.get("/astrology/night-sky", params={"datetime_str": "2026-03-20T14:46:00Z"})
        assert response.status_code == 200
        assert response.json()["observer"]["latitude"] == 37.7749
