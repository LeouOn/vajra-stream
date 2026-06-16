"""Integration tests for the /charts/{chart_id}/natal-export endpoint.

Validates the LLM-optimized natal export payload: Western positions,
elements, modalities, aspects, flattened Vedic data, and the dual
Placidus / Whole Sign house map.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


def _create_test_chart(client):
    """Create a natal chart via the API and return its id."""
    payload = {
        "name": "__natal_export_test__",
        "birth_time_iso": "1990-06-15T12:00:00",
        "city": "New York",
    }
    resp = client.post("/api/v1/astrology/charts", json=payload)
    assert resp.status_code == 200
    chart = resp.json()
    return chart["id"]


@pytest.mark.integration
class TestNatalExportEndpoint:
    def test_natal_export_endpoint_returns_expected_shape(self, client):
        chart_id = _create_test_chart(client)
        try:
            resp = client.post(
                f"/api/v1/astrology/charts/{chart_id}/natal-export",
                json={},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"

            data = body["data"]
            # Top-level fields
            for field in [
                "name",
                "birth_time_iso",
                "birth_location",
                "western",
                "vedic",
                "houses",
            ]:
                assert field in data, f"missing top-level field {field}"

            # birth_location structure
            assert "latitude" in data["birth_location"]
            assert "longitude" in data["birth_location"]

            # Western block
            western = data["western"]
            for field in ["positions", "elements", "modalities", "aspects"]:
                assert field in western, f"missing western field {field}"
            # Core planets must be present in positions
            for planet in ["sun", "moon", "mercury", "venus", "mars"]:
                assert planet in western["positions"], f"missing planet {planet}"
            # Elements cover the four classical elements
            for el in ["Fire", "Earth", "Air", "Water"]:
                assert el in western["elements"], f"missing element {el}"
            # Modalities present
            for mod in ["Cardinal", "Fixed", "Mutable"]:
                assert mod in western["modalities"], f"missing modality {mod}"
            # Aspects is a list of dicts with planet1/planet2/aspect
            assert isinstance(western["aspects"], list)
            if western["aspects"]:
                a = western["aspects"][0]
                assert "planet1" in a and "planet2" in a and "aspect" in a

            # Vedic block — flattened shape (panchanga factors at top level,
            # ascendant + planets split out)
            vedic = data["vedic"]
            for field in ["tithi", "nakshatra", "yoga", "karana", "vara"]:
                assert field in vedic, f"missing vedic field {field}"
            assert "ascendant" in vedic
            assert "planets" in vedic
            assert "sun" in vedic["planets"]
            # tithi carries at least a name
            assert "name" in vedic["tithi"]

            # Houses — dual Placidus / Whole Sign
            houses = data["houses"]
            assert "sun" in houses
            assert "house_placidus" in houses["sun"]
            assert "house_whole_sign" in houses["sun"]
            # Ascendant always in house 1 in both systems
            assert houses["ascendant"]["house_placidus"] == 1
            assert houses["ascendant"]["house_whole_sign"] == 1
        finally:
            client.delete(f"/api/v1/astrology/charts/{chart_id}")

    def test_natal_export_404_for_missing_chart(self, client):
        resp = client.post(
            "/api/v1/astrology/charts/99999/natal-export",
            json={},
        )
        assert resp.status_code == 404
