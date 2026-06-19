from datetime import datetime

import pytest
import pytz
from fastapi.testclient import TestClient

from core.astrology import AstrologicalCalculator

EXPECTED_PLANETS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto", "north_node",
]


@pytest.fixture
def calculator():
    return AstrologicalCalculator()


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests – get_planet_house_map
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlanetHouseMapPlacidus:
    def test_planet_house_map_placidus(self, calculator):
        dt = datetime(1990, 1, 15, 12, 0, tzinfo=pytz.timezone("America/New_York"))
        location = (40.7128, -74.0060)  # NYC

        result = calculator.get_planet_house_map(dt, location)

        # All expected planet keys present
        for planet in EXPECTED_PLANETS:
            assert planet in result, f"missing planet {planet}"

        # Each planet has house_placidus integer 1-12
        for planet in EXPECTED_PLANETS:
            hp = result[planet]["house_placidus"]
            assert isinstance(hp, int), f"{planet}.house_placidus is not int: {hp}"
            assert 1 <= hp <= 12, f"{planet}.house_placidus out of range: {hp}"

        # Ascendant present and always in house 1
        assert "ascendant" in result
        assert result["ascendant"]["house_placidus"] == 1

        # Midheaven present with valid house number
        assert "midheaven" in result
        assert 1 <= result["midheaven"]["house_placidus"] <= 12


@pytest.mark.unit
class TestPlanetHouseMapWholeSign:
    def test_planet_house_map_whole_sign(self, calculator):
        dt = datetime(1990, 1, 15, 12, 0, tzinfo=pytz.timezone("America/New_York"))
        location = (40.7128, -74.0060)

        result = calculator.get_planet_house_map(dt, location)

        # Each planet has house_whole_sign integer 1-12
        for planet in EXPECTED_PLANETS:
            hw = result[planet]["house_whole_sign"]
            assert isinstance(hw, int), f"{planet}.house_whole_sign is not int: {hw}"
            assert 1 <= hw <= 12, f"{planet}.house_whole_sign out of range: {hw}"

        # Ascendant always house 1
        assert result["ascendant"]["house_whole_sign"] == 1

        # Spot-check Whole Sign formula for sun
        asc_sign_index = int(result["ascendant"]["longitude"] / 30) % 12
        sun_sign_index = int(result["sun"]["longitude"] / 30) % 12
        expected_whole = (sun_sign_index - asc_sign_index) % 12 + 1
        assert result["sun"]["house_whole_sign"] == expected_whole


@pytest.mark.unit
class TestPlanetHouseMapNoLocation:
    def test_planet_house_map_no_location(self, calculator):
        dt = datetime(1990, 1, 15, 12, 0, tzinfo=pytz.UTC)

        result = calculator.get_planet_house_map(dt, None)

        # Still has planet keys
        for planet in EXPECTED_PLANETS:
            assert planet in result, f"missing planet {planet}"

        # house fields are None
        for planet in EXPECTED_PLANETS:
            assert result[planet]["house_placidus"] is None, f"{planet}.house_placidus should be None"
            assert result[planet]["house_whole_sign"] is None, f"{planet}.house_whole_sign should be None"

        # No ascendant or midheaven entries
        assert "ascendant" not in result
        assert "midheaven" not in result


# ---------------------------------------------------------------------------
# Integration tests – transit-export endpoint
# ---------------------------------------------------------------------------


def _create_test_chart(client):
    """Helper: create a natal chart via the API, return (chart_id, cleanup callable)."""
    payload = {
        "name": "__transit_export_test__",
        "birth_time_iso": "1990-06-15T12:00:00",
        "city": "New York",
    }
    resp = client.post("/api/v1/astrology/charts", json=payload)
    assert resp.status_code == 200
    chart = resp.json()
    return chart["id"]


@pytest.mark.integration
class TestTransitExportEndpoint:
    def test_transit_export_endpoint(self, client):
        chart_id = _create_test_chart(client)
        try:
            resp = client.post(
                f"/api/v1/astrology/charts/{chart_id}/transit-export",
                json={"transit_time_iso": "2026-06-01T12:00:00"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"

            data = body["data"]
            expected_fields = [
                "name", "birth_time_iso", "transit_time",
                "natal_houses", "transit_houses",
                "top_harmonious", "top_challenging",
                "gochara", "bazi_clashes", "house_systems",
            ]
            for field in expected_fields:
                assert field in data, f"missing field {field}"

            assert data["house_systems"] == ["Placidus", "Whole Sign"]
            assert isinstance(data["top_harmonious"], list)
            assert isinstance(data["top_challenging"], list)
        finally:
            client.delete(f"/api/v1/astrology/charts/{chart_id}")

    def test_transit_export_top10_sorting(self, client):
        chart_id = _create_test_chart(client)
        try:
            resp = client.post(
                f"/api/v1/astrology/charts/{chart_id}/transit-export",
                json={"transit_time_iso": "2026-06-01T12:00:00"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]

            harmonious = data["top_harmonious"]
            challenging = data["top_challenging"]

            assert len(harmonious) <= 10
            assert len(challenging) <= 10

            harmonious_aspects = {"Conjunction", "Trine", "Sextile"}
            for item in harmonious:
                assert item["aspect"] in harmonious_aspects, f"unexpected harmonious aspect: {item['aspect']}"

            challenging_aspects = {"Square", "Opposition"}
            for item in challenging:
                assert item["aspect"] in challenging_aspects, f"unexpected challenging aspect: {item['aspect']}"

            # Verify descending exactness sort
            if len(harmonious) > 1:
                for i in range(len(harmonious) - 1):
                    assert harmonious[i]["exactness"] >= harmonious[i + 1]["exactness"]

            if len(challenging) > 1:
                for i in range(len(challenging) - 1):
                    assert challenging[i]["exactness"] >= challenging[i + 1]["exactness"]
        finally:
            client.delete(f"/api/v1/astrology/charts/{chart_id}")

    def test_transit_export_404(self, client):
        resp = client.post(
            "/api/v1/astrology/charts/99999/transit-export",
            json={"transit_time_iso": "2026-06-01T12:00:00"},
        )
        assert resp.status_code == 404
