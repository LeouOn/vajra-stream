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
