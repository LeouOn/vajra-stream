"""W1-A route tests for GET /astrology/earth-state.

The astrology router is mounted bare (``APIRouter()``) and receives its
/astrology prefix at include time, so these tests mount it with the same
prefix the app uses. The route is added directly after get_night_sky and
changes nothing else in that file.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints import astrology
from core import earth_sky


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(astrology.router, prefix="/astrology")
    return TestClient(app)


class TestEarthStateRoute:
    def test_default_now_returns_full_state(self, client: TestClient):
        response = client.get("/astrology/earth-state")
        assert response.status_code == 200
        state = response.json()
        for key in ("at", "ephemeris", "gast_deg", "sun", "moon", "planets", "provenance"):
            assert key in state
        assert [p["id"] for p in state["planets"]] == [
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]
        # provenance marks every computed field as computed
        assert set(state["provenance"]) >= {"at", "gast_deg", "sun", "moon", "planets"}
        assert set(state["provenance"].values()) == {"computed"}

    def test_explicit_instant_with_z_suffix(self, client: TestClient):
        response = client.get("/astrology/earth-state", params={"datetime_str": "2026-03-20T14:46:00Z"})
        assert response.status_code == 200
        assert response.json()["at"].startswith("2026-03-20T14:46:00")

    def test_naive_instant_is_utc(self, client: TestClient):
        naive = client.get("/astrology/earth-state", params={"datetime_str": "2027-07-01T12:00:00"})
        aware = client.get("/astrology/earth-state", params={"datetime_str": "2027-07-01T12:00:00+00:00"})
        assert naive.status_code == aware.status_code == 200
        assert naive.json() == aware.json()

    def test_aware_offset_equals_utc_equivalent(self, client: TestClient):
        utc = client.get("/astrology/earth-state", params={"datetime_str": "2028-01-15T06:30:00+00:00"})
        shifted = client.get("/astrology/earth-state", params={"datetime_str": "2028-01-14T16:30:00-14:00"})
        assert utc.status_code == shifted.status_code == 200
        assert utc.json()["sun"] == shifted.json()["sun"]
        assert utc.json()["gast_deg"] == shifted.json()["gast_deg"]

    def test_malformed_datetime_is_422(self, client: TestClient):
        for bad in ("not-a-date", "2026-13-45T99:99:99Z", "2026-03-20T14:46:00+25:00"):
            response = client.get("/astrology/earth-state", params={"datetime_str": bad})
            assert response.status_code == 422, bad
            assert "detail" in response.json()

    def test_out_of_range_is_422(self, client: TestClient):
        for bad in ("1799-12-31T23:59:59Z", "2201-01-01T00:00:00Z"):
            response = client.get("/astrology/earth-state", params={"datetime_str": bad})
            assert response.status_code == 422, bad

    def test_unavailable_ephemeris_is_503(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(earth_sky, "swe", None)
        response = client.get("/astrology/earth-state", params={"datetime_str": "2026-03-20T14:46:00Z"})
        assert response.status_code == 503
        assert response.json() == {"detail": "ephemeris unavailable"}

    def test_supported_bounds_pass(self, client: TestClient):
        for good in ("1800-01-01T00:00:00Z", "2200-12-31T23:00:00Z"):
            response = client.get("/astrology/earth-state", params={"datetime_str": good})
            assert response.status_code == 200, good

    def test_rounding_to_four_decimals(self, client: TestClient):
        state = client.get(
            "/astrology/earth-state",
            params={"datetime_str": datetime(2026, 10, 22, 2, 0, 0, tzinfo=timezone.utc).isoformat()},
        ).json()
        assert round(state["gast_deg"], 4) == state["gast_deg"]
        assert round(state["sun"]["ra_deg"], 4) == state["sun"]["ra_deg"]
