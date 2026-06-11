"""
E2E tests for the Astrology module.
Tests complete user flows: chart CRUD, transit analysis, synastry,
import/export, Vedic Dasha, and error handling.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

ASTRO_BASE = "/api/v1/astrology"


@pytest.fixture(autouse=True)
def _cleanup_after():
    """Remove test charts created during E2E runs."""
    yield
    # List all charts and delete any test-created ones
    resp = client.get(f"{ASTRO_BASE}/charts")
    if resp.status_code == 200:
        for chart in resp.json():
            if chart["name"].startswith("E2E_"):
                client.delete(f"{ASTRO_BASE}/charts/{chart['id']}")


@pytest.mark.e2e
class TestAstrologyE2E:
    """End-to-end astrology workflows."""

    # ------------------------------------------------------------------
    # Chart CRUD lifecycle
    # ------------------------------------------------------------------
    def test_chart_crud_lifecycle(self):
        """Create → read → update → delete a saved natal chart."""
        # 1. Create
        payload = {
            "name": "E2E_CRUD_Test",
            "birth_time_iso": "1990-06-15T08:30:00",
            "city": "London",
            "description": "E2E test chart",
            "tags": "E2E,Test",
            "notes": "Created during E2E run",
        }
        create_resp = client.post(f"{ASTRO_BASE}/charts", json=payload)
        assert create_resp.status_code == 200, create_resp.text
        created = create_resp.json()
        assert created["name"] == "E2E_CRUD_Test"
        assert "London" in created["city"]
        assert created["id"] > 0
        assert created["cached_chart_data"] is not None  # pre-calculated
        chart_id = created["id"]

        # 2. Read
        get_resp = client.get(f"{ASTRO_BASE}/charts/{chart_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["name"] == "E2E_CRUD_Test"
        assert fetched["tags"] == "E2E,Test"

        # 3. Update
        update_payload = {
            "name": "E2E_CRUD_Updated",
            "birth_time_iso": "1990-06-15T08:30:00",
            "city": "Paris",
            "description": "Updated description",
            "tags": "E2E,Updated",
            "notes": "Updated notes",
        }
        update_resp = client.put(f"{ASTRO_BASE}/charts/{chart_id}", json=update_payload)
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["name"] == "E2E_CRUD_Updated"
        assert "Paris" in updated["city"]

        # 4. List — verify it appears
        list_resp = client.get(f"{ASTRO_BASE}/charts")
        assert list_resp.status_code == 200
        charts = list_resp.json()
        assert any(c["id"] == chart_id for c in charts)

        # 5. Delete
        del_resp = client.delete(f"{ASTRO_BASE}/charts/{chart_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"

        # 6. Verify deletion
        get_after = client.get(f"{ASTRO_BASE}/charts/{chart_id}")
        assert get_after.status_code == 404

    # ------------------------------------------------------------------
    # Transit-to-natal flow
    # ------------------------------------------------------------------
    def test_transit_to_natal_flow(self):
        """Create a chart → request transits → verify three-system coverage."""
        # Create
        payload = {
            "name": "E2E_Transit_Test",
            "birth_time_iso": "1995-10-15T08:30:00",
            "city": "New Delhi",
        }
        create_resp = client.post(f"{ASTRO_BASE}/charts", json=payload)
        assert create_resp.status_code == 200
        chart_id = create_resp.json()["id"]

        # Request transits
        transit_payload = {"transit_time_iso": "2026-06-02T12:00:00"}
        transit_resp = client.post(f"{ASTRO_BASE}/charts/{chart_id}/transits", json=transit_payload)
        assert transit_resp.status_code == 200
        data = transit_resp.json()["data"]

        # Verify all three systems are present
        assert data["name"] == "E2E_Transit_Test"
        assert "aspects" in data  # Western transit-to-natal
        assert isinstance(data["aspects"], list)
        assert "gochara" in data  # Vedic gochara
        assert isinstance(data["gochara"], dict)
        assert "bazi_clashes" in data  # Chinese pillar clashes
        assert "interactions" in data["bazi_clashes"]

        # Verify aspect structure if any exist
        if data["aspects"]:
            asp = data["aspects"][0]
            assert "transit_planet" in asp
            assert "natal_planet" in asp
            assert "aspect" in asp
            assert "orb" in asp
            assert "exactness" in asp

        # Verify gochara structure
        if data["gochara"]:
            planet_key = next(iter(data["gochara"]))
            g = data["gochara"][planet_key]
            assert "gochara_house" in g
            assert "transit_rashi" in g

        # Cleanup
        client.delete(f"{ASTRO_BASE}/charts/{chart_id}")

    # ------------------------------------------------------------------
    # Synastry comparison flow
    # ------------------------------------------------------------------
    def test_synastry_comparison_flow(self):
        """Create two charts → compare → verify scoring."""
        # Create Subject A
        a_resp = client.post(
            f"{ASTRO_BASE}/charts",
            json={
                "name": "E2E_Synastry_A",
                "birth_time_iso": "1995-10-15T08:30:00",
                "city": "New Delhi",
            },
        )
        assert a_resp.status_code == 200
        id_a = a_resp.json()["id"]

        # Create Subject B
        b_resp = client.post(
            f"{ASTRO_BASE}/charts",
            json={
                "name": "E2E_Synastry_B",
                "birth_time_iso": "1997-03-20T14:15:00",
                "city": "Tokyo",
            },
        )
        assert b_resp.status_code == 200
        id_b = b_resp.json()["id"]

        # Compare
        compare_resp = client.post(
            f"{ASTRO_BASE}/charts/compare",
            json={
                "chart_id_a": id_a,
                "chart_id_b": id_b,
            },
        )
        assert compare_resp.status_code == 200
        result = compare_resp.json()
        assert result["status"] == "success"
        assert "aspects" in result["data"]
        assert "scoring" in result["data"]

        scoring = result["data"]["scoring"]
        assert "compatibility_score" in scoring
        assert 0 <= scoring["compatibility_score"] <= 100
        assert "harmony_count" in scoring
        assert "tension_count" in scoring
        assert "description" in scoring

        # Cleanup
        client.delete(f"{ASTRO_BASE}/charts/{id_a}")
        client.delete(f"{ASTRO_BASE}/charts/{id_b}")

    # ------------------------------------------------------------------
    # Import / Export round-trip
    # ------------------------------------------------------------------
    def test_import_export_roundtrip(self):
        """Create charts → export → delete → import → verify recovery."""
        # Create two charts
        c1 = client.post(
            f"{ASTRO_BASE}/charts",
            json={
                "name": "E2E_Export_A",
                "birth_time_iso": "2000-01-01T12:00:00",
                "city": "San Francisco",
            },
        )
        c2 = client.post(
            f"{ASTRO_BASE}/charts",
            json={
                "name": "E2E_Export_B",
                "birth_time_iso": "1985-07-20T06:00:00",
                "city": "Beijing",
            },
        )
        assert c1.status_code == 200 and c2.status_code == 200
        id_a, id_b = c1.json()["id"], c2.json()["id"]

        # Export
        export_resp = client.get(f"{ASTRO_BASE}/charts/export")
        assert export_resp.status_code == 200
        backup = export_resp.json()
        assert backup["version"] == "2.0"
        assert backup["system"] == "vajra-stream-astrology"
        chart_names = [c["name"] for c in backup["charts"]]
        assert "E2E_Export_A" in chart_names
        assert "E2E_Export_B" in chart_names

        # Verify cached_data is included in export
        for chart in backup["charts"]:
            if chart["name"] in ("E2E_Export_A", "E2E_Export_B"):
                assert chart.get("cached_data") is not None

        # Delete both
        client.delete(f"{ASTRO_BASE}/charts/{id_a}")
        client.delete(f"{ASTRO_BASE}/charts/{id_b}")

        # Verify deletion
        list_after_del = client.get(f"{ASTRO_BASE}/charts")
        remaining = [c["name"] for c in list_after_del.json()]
        assert "E2E_Export_A" not in remaining
        assert "E2E_Export_B" not in remaining

        # Import backup
        import_resp = client.post(f"{ASTRO_BASE}/charts/import", json=backup)
        assert import_resp.status_code == 200
        assert import_resp.json()["imported"] >= 2

        # Verify recovered
        list_recovered = client.get(f"{ASTRO_BASE}/charts")
        recovered_names = [c["name"] for c in list_recovered.json()]
        assert "E2E_Export_A" in recovered_names
        assert "E2E_Export_B" in recovered_names

    # ------------------------------------------------------------------
    # Vedic Dasha calculation
    # ------------------------------------------------------------------
    def test_vedic_dasha_calculation(self):
        """Verify Vimshottari Dasha periods are computed correctly."""
        payload = {
            "name": "E2E_Dasha_Test",
            "birth_time_iso": "1995-10-15T08:30:00",
            "city": "Mumbai",
        }
        create_resp = client.post(f"{ASTRO_BASE}/charts", json=payload)
        assert create_resp.status_code == 200
        chart_id = create_resp.json()["id"]

        dasha_resp = client.get(f"{ASTRO_BASE}/charts/{chart_id}/vedic-dasha")
        assert dasha_resp.status_code == 200
        dashas = dasha_resp.json()["dashas"]
        assert len(dashas) >= 1

        # First dasha should have remaining_years_at_birth > 0
        first = dashas[0]
        assert first["remaining_years_at_birth"] > 0
        assert first["ruler"] in [
            "Ketu",
            "Venus",
            "Sun",
            "Moon",
            "Mars",
            "Rahu",
            "Jupiter",
            "Saturn",
            "Mercury",
        ]
        assert first["duration_years"] > 0

        # Cleanup
        client.delete(f"{ASTRO_BASE}/charts/{chart_id}")

    # ------------------------------------------------------------------
    # Chart recalculate
    # ------------------------------------------------------------------
    def test_chart_recalculation(self):
        """Recalculate should refresh cached_chart_data."""
        payload = {
            "name": "E2E_Recalc_Test",
            "birth_time_iso": "1990-01-01T00:00:00",
            "city": "London",
        }
        create_resp = client.post(f"{ASTRO_BASE}/charts", json=payload)
        assert create_resp.status_code == 200
        chart_id = create_resp.json()["id"]

        recalc_resp = client.post(f"{ASTRO_BASE}/charts/{chart_id}/recalculate")
        assert recalc_resp.status_code == 200
        assert recalc_resp.json()["status"] == "success"
        assert "cached_chart_data" in recalc_resp.json()
        cached = recalc_resp.json()["cached_chart_data"]
        assert "western" in cached
        assert "indian" in cached
        assert "chinese" in cached

        # Cleanup
        client.delete(f"{ASTRO_BASE}/charts/{chart_id}")

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------
    def test_404_on_missing_chart(self):
        resp = client.get(f"{ASTRO_BASE}/charts/99999")
        assert resp.status_code == 404

    def test_404_on_missing_chart_transits(self):
        resp = client.post(f"{ASTRO_BASE}/charts/99999/transits", json={})
        assert resp.status_code == 404

    def test_400_on_bad_geocode(self):
        resp = client.post(
            f"{ASTRO_BASE}/charts",
            json={
                "name": "Bad City",
                "birth_time_iso": "2000-01-01T12:00:00",
                "city": "XyzzyNoSuchPlace999",
            },
        )
        # Should fail because geocoding won't find this city
        assert resp.status_code in (400, 500)

    def test_live_astrology_returns_all_systems(self):
        """The /current endpoint should return western, indian, and chinese."""
        resp = client.get(f"{ASTRO_BASE}/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        astro = data["astrology"]
        assert "western" in astro
        assert "indian" in astro
        assert "chinese" in astro
        assert "planetary_hours" in astro

    def test_moon_phase_endpoint(self):
        resp = client.get(f"{ASTRO_BASE}/moon-phase")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "moon_phase" in data
        assert "description" in data

    def test_elements_endpoint(self):
        resp = client.get(f"{ASTRO_BASE}/elements")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "elements" in data
        assert "dominant_element" in data
        assert data["balance"] in ("harmonious", "imbalanced")
