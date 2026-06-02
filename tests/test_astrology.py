from datetime import datetime

import pytest
import pytz
from fastapi.testclient import TestClient

from core.astrology import AstrologicalCalculator


@pytest.fixture
def client():
    from backend.app.main import app

    return TestClient(app)


@pytest.fixture
def calculator():
    return AstrologicalCalculator()


@pytest.mark.unit
class TestAstrologyCalculator:
    def test_julian_day(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        jd = calculator.get_julian_day(dt)
        assert isinstance(jd, float)
        assert jd > 2400000.0

    def test_planetary_positions(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        positions = calculator.get_planetary_positions(dt)
        assert "sun" in positions
        assert "moon" in positions
        assert "longitude" in positions["sun"]
        assert "sign" in positions["sun"]
        assert "degree" in positions["sun"]
        assert isinstance(positions["sun"]["longitude"], float)
        assert isinstance(positions["sun"]["sign"], str)

    def test_western_astrology(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        location = (37.7749, -122.4194)
        data = calculator.get_western_astrology(dt, location)

        assert "positions" in data
        assert "elements" in data
        assert "modalities" in data
        assert "aspects" in data

        # Check Ascendant and Midheaven are calculated when location is provided
        assert "ascendant" in data["positions"]
        assert "midheaven" in data["positions"]
        assert isinstance(data["positions"]["ascendant"]["longitude"], float)

        # Check aspects list structure
        if len(data["aspects"]) > 0:
            asp = data["aspects"][0]
            assert "planet1" in asp
            assert "planet2" in asp
            assert "aspect" in asp
            assert "exactness" in asp

    def test_indian_astrology(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        location = (37.7749, -122.4194)
        data = calculator.get_indian_astrology(dt, location)

        assert "ayanamsa" in data
        assert "sidereal_positions" in data
        assert "panchanga" in data

        # Check Grahas are present
        grahas = data["sidereal_positions"]
        assert "ascendant" in grahas
        assert "sun" in grahas
        assert "moon" in grahas
        assert "rahu" in grahas
        assert "ketu" in grahas

        # Check Panchanga limbs
        panch = data["panchanga"]
        assert "tithi" in panch
        assert "nakshatra" in panch
        assert "yoga" in panch
        assert "karana" in panch
        assert "vara" in panch

        assert "name" in panch["tithi"]
        assert "progress" in panch["tithi"]
        assert "name" in panch["nakshatra"]

    def test_chinese_astrology(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        data = calculator.get_chinese_astrology(dt)

        assert "lunar_date" in data
        assert "zodiac_animal" in data
        assert "bazi" in data
        assert "shichen" in data
        assert "solar_term" in data

        assert "year" in data["bazi"]
        assert "month" in data["bazi"]
        assert "day" in data["bazi"]
        assert "hour" in data["bazi"]
        assert "branch" in data["shichen"]

    def test_exact_planetary_hours(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        location = (37.7749, -122.4194)
        data = calculator.calculate_exact_planetary_hours(dt, location)

        assert data["status"] == "success"
        assert "current_planetary_hour" in data
        assert "day_planet" in data
        assert "hour_index" in data
        assert isinstance(data["is_daytime"], bool)
        assert isinstance(data["time_remaining_seconds"], int)

    def test_comprehensive_astrology(self, calculator):
        dt = datetime(2026, 5, 24, 19, 29, 45, tzinfo=pytz.UTC)
        location = (37.7749, -122.4194)
        data = calculator.get_comprehensive_astrology(dt, location)

        assert "datetime" in data
        assert "location" in data
        assert "western" in data
        assert "indian" in data
        assert "chinese" in data
        assert "planetary_hours" in data


@pytest.mark.integration
class TestAstrologyAPI:
    def test_api_current_transit(self, client):
        response = client.get("/api/v1/astrology/current")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "astrology" in data
        assert "western" in data["astrology"]
        assert "indian" in data["astrology"]
        assert "chinese" in data["astrology"]

    def test_api_current_natal_calculation(self, client):
        # Calculate custom chart for birth time: 1990-06-15T08:30:00
        # Location: London (51.5074, -0.1278)
        params = {"datetime_str": "1990-06-15T08:30:00", "latitude": 51.5074, "longitude": -0.1278}
        response = client.get("/api/v1/astrology/current", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify custom time and location are reflected in payload
        astro = data["astrology"]
        assert "1990-06-15" in astro["datetime"]
        assert abs(astro["location"]["latitude"] - 51.5074) < 0.001
        assert abs(astro["location"]["longitude"] - (-0.1278)) < 0.001

    def test_api_western_endpoint(self, client):
        response = client.get("/api/v1/astrology/western")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "western" in data
        assert "positions" in data["western"]

    def test_api_indian_endpoint(self, client):
        response = client.get("/api/v1/astrology/indian")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "indian" in data
        assert "panchanga" in data["indian"]

    def test_api_chinese_endpoint(self, client):
        response = client.get("/api/v1/astrology/chinese")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "chinese" in data
        assert "bazi" in data["chinese"]

    def test_api_planetary_hours_endpoint(self, client):
        response = client.get("/api/v1/astrology/planetary-hours")
        assert response.status_code == 200
        data = response.json()
        # Returns raw dict
        assert "current_planetary_hour" in data
        assert "day_planet" in data

    def test_api_saved_charts_workflow(self, client):
        # 1. Create a saved chart
        new_chart = {
            "name": "Test Astrologer Profile",
            "birth_time_iso": "1995-10-15T08:30:00",
            "city": "London",
            "description": "Integration test profile",
            "tags": "Test,Developer",
            "notes": "Verification test notes"
        }
        create_resp = client.post("/api/v1/astrology/charts", json=new_chart)
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["name"] == "Test Astrologer Profile"
        assert "London" in created["city"]
        assert abs(created["latitude"] - 51.5074) < 0.05
        assert abs(created["longitude"] - (-0.1278)) < 0.05
        assert created["timezone"] == "Europe/London"
        chart_id = created["id"]

        # 2. List saved charts
        list_resp = client.get("/api/v1/astrology/charts")
        assert list_resp.status_code == 200
        charts = list_resp.json()
        assert len(charts) > 0
        assert any(c["id"] == chart_id for c in charts)

        # 3. Get specific chart
        get_resp = client.get(f"/api/v1/astrology/charts/{chart_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["name"] == "Test Astrologer Profile"

        # 4. Update saved chart
        update_data = {
            "name": "Updated Test Profile",
            "birth_time_iso": "1995-10-15T08:30:00",
            "city": "Paris",
            "description": "Updated profile",
            "tags": "Test,Updated",
            "notes": "Updated notes"
        }
        update_resp = client.put(f"/api/v1/astrology/charts/{chart_id}", json=update_data)
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["name"] == "Updated Test Profile"
        assert "Paris" in updated["city"]
        assert abs(updated["latitude"] - 48.8566) < 0.05
        assert abs(updated["longitude"] - 2.3522) < 0.05
        assert updated["timezone"] == "Europe/Paris"

        # 5. Check Recalculate Chart
        recalc_resp = client.post(f"/api/v1/astrology/charts/{chart_id}/recalculate")
        assert recalc_resp.status_code == 200
        assert recalc_resp.json()["status"] == "success"

        # 6. Check Transits to Natal
        transit_payload = {"transit_time_iso": "2026-06-02T12:00:00"}
        transit_resp = client.post(f"/api/v1/astrology/charts/{chart_id}/transits", json=transit_payload)
        assert transit_resp.status_code == 200
        t_data = transit_resp.json()["data"]
        assert t_data["name"] == "Updated Test Profile"
        assert "aspects" in t_data
        assert "gochara" in t_data
        assert "bazi_clashes" in t_data

        # 7. Check Vedic Dasha
        dasha_resp = client.get(f"/api/v1/astrology/charts/{chart_id}/vedic-dasha")
        assert dasha_resp.status_code == 200
        dashas = dasha_resp.json()["dashas"]
        assert len(dashas) > 0
        assert dashas[0]["ruler"] in ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

        # 8. Check Synastry Compare
        # Create second profile
        new_chart_b = {
            "name": "Partner Profile",
            "birth_time_iso": "1997-03-20T14:15:00",
            "city": "New York",
            "description": "Partner chart",
            "tags": "Partner",
            "notes": "Second chart"
        }
        create_resp_b = client.post("/api/v1/astrology/charts", json=new_chart_b)
        chart_id_b = create_resp_b.json()["id"]

        compare_resp = client.post("/api/v1/astrology/charts/compare", json={
            "chart_id_a": chart_id,
            "chart_id_b": chart_id_b
        })
        assert compare_resp.status_code == 200
        comp_data = compare_resp.json()
        assert comp_data["status"] == "success"
        assert "scoring" in comp_data["data"]
        assert "compatibility_score" in comp_data["data"]["scoring"]

        # 9. Clean up (delete profiles)
        del_resp_a = client.delete(f"/api/v1/astrology/charts/{chart_id}")
        assert del_resp_a.status_code == 200
        del_resp_b = client.delete(f"/api/v1/astrology/charts/{chart_id_b}")
        assert del_resp_b.status_code == 200

    def test_api_charts_import_export(self, client):
        # Create a temp chart to export
        chart_data = {
            "name": "Export Test Profile",
            "birth_time_iso": "1995-10-15T08:30:00",
            "city": "Tokyo"
        }
        create_resp = client.post("/api/v1/astrology/charts", json=chart_data)
        chart_id = create_resp.json()["id"]

        # Export backup
        export_resp = client.get("/api/v1/astrology/charts/export")
        assert export_resp.status_code == 200
        backup = export_resp.json()
        assert backup["version"] == "2.0"
        assert len(backup["charts"]) > 0
        assert any(c["name"] == "Export Test Profile" for c in backup["charts"])

        # Delete the profile
        client.delete(f"/api/v1/astrology/charts/{chart_id}")

        # Import the backup file back
        import_resp = client.post("/api/v1/astrology/charts/import", json=backup)
        assert import_resp.status_code == 200
        assert import_resp.json()["imported"] > 0

        # Verify it got re-created
        list_resp = client.get("/api/v1/astrology/charts")
        charts = list_resp.json()
        imported_chart = next((c for c in charts if c["name"] == "Export Test Profile"), None)
        assert imported_chart is not None

        # Cleanup imported profile
        client.delete(f"/api/v1/astrology/charts/{imported_chart['id']}")


@pytest.mark.unit
class TestAstrologyService:
    def test_astrology_service_methods(self):
        from modules.astrology import AstrologyService
        
        svc = AstrologyService()
        
        # Test get_status
        status = svc.get_status()
        assert status["astrology_engine"] is True
        assert status["astrocartography"] is True
        
        # Test get_planetary_positions
        positions = svc.get_planetary_positions()
        assert positions["status"] == "success"
        assert "positions" in positions
        
        # Test calculate_natal_chart
        dt = datetime(1990, 6, 15, 8, 30)
        chart = svc.calculate_natal_chart(dt, 51.5074, -0.1278)
        assert chart["status"] == "success"
        assert "chart" in chart
        
        # Test get_current_transits
        transits = svc.get_current_transits(chart["chart"])
        assert transits["status"] == "success"
        assert "transits" in transits
        
        # Test analyze_location_energy
        analysis = svc.analyze_location_energy(chart["chart"], 37.7749, -122.4194)
        assert analysis["status"] == "success"
        assert "analysis" in analysis
        
        # Test find_power_places
        places = svc.find_power_places(chart["chart"], "benefic")
        assert places["status"] == "success"
        assert "power_places" in places
