"""
Integration tests for Vajra Stream API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from backend.app.main import app

client = TestClient(app)


class TestBasicEndpoints:
    """Test basic API endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "Vajra.Stream" in data["message"]

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "vajra-stream"


class TestScalarWavesAPI:
    """Test scalar waves endpoints"""

    def test_generate_scalar_waves_qrng(self):
        """Test QRNG scalar wave generation"""
        response = client.post(
            "/api/v1/scalar/generate",
            json={
                "method": "qrng",
                "count": 1000,
                "intensity": 0.5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["method"] == "qrng"
        assert data["count"] == 1000
        assert "mops" in data
        assert "thermal_status" in data

    def test_generate_scalar_waves_hybrid(self):
        """Test hybrid scalar wave generation"""
        response = client.post(
            "/api/v1/scalar/generate",
            json={
                "method": "hybrid",
                "count": 1000,
                "intensity": 1.0
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["method"] == "hybrid"

    def test_list_scalar_methods(self):
        """Test listing available methods"""
        response = client.get("/api/v1/scalar/methods")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "methods" in data
        assert len(data["methods"]) >= 8

    def test_thermal_status(self):
        """Test thermal monitoring"""
        response = client.get("/api/v1/scalar/thermal-status")
        assert response.status_code == 200
        data = response.json()
        assert "temperature" in data
        assert "throttle_factor" in data
        assert "status" in data

    def test_mops_metrics(self):
        """Test MOPS metrics"""
        response = client.get("/api/v1/scalar/mops-metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "current_mmops" in data
        assert "target_terra_mops" in data


class TestRadionicsAPI:
    """Test radionics endpoints"""

    def test_list_intentions(self):
        """Test listing intentions"""
        response = client.get("/api/v1/radionics/intentions")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "intentions" in data
        assert len(data["intentions"]) >= 8

    def test_list_frequencies(self):
        """Test listing frequencies"""
        response = client.get("/api/v1/radionics/frequencies")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "solfeggio_frequencies" in data
        assert "planetary_frequencies" in data

    def test_broadcast_request(self):
        """Test radionics broadcast"""
        response = client.post(
            "/api/v1/radionics/broadcast",
            json={
                "intention": "healing",
                "target_names": ["Test Target"],
                "duration_minutes": 1,
                "scalar_intensity": 0.5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "session_id" in data
        assert data["intention"] == "healing"

    def test_healing_protocol(self):
        """Test healing protocol"""
        response = client.post(
            "/api/v1/radionics/healing-protocol",
            json={
                "target_name": "Test Person",
                "duration_minutes": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["protocol"] == "healing"


class TestAnatomyAPI:
    """Test anatomy endpoints"""

    def test_list_traditions(self):
        """Test listing traditions"""
        response = client.get("/api/v1/anatomy/traditions")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "traditions" in data

    def test_list_chakras(self):
        """Test listing chakras"""
        response = client.get("/api/v1/anatomy/chakras")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "chakras" in data
        assert len(data["chakras"]) == 7

    def test_list_meridians(self):
        """Test listing meridians"""
        response = client.get("/api/v1/anatomy/meridians")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "meridians" in data
        assert len(data["meridians"]) == 12

    def test_visualize_chakras(self):
        """Test chakra visualization"""
        response = client.post(
            "/api/v1/anatomy/visualize/chakras",
            json={
                "width": 800,
                "height": 1000,
                "format": "png"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "image_data" in data
        assert len(data["image_data"]) > 0


class TestBlessingsAPI:
    """Test blessings endpoints"""

    def test_list_traditions(self):
        """Test listing traditions"""
        response = client.get("/api/v1/blessings/traditions")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "traditions" in data

    def test_list_templates(self):
        """Test listing templates"""
        response = client.get("/api/v1/blessings/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_generate_blessing_narrative(self):
        """Test blessing narrative generation"""
        response = client.post(
            "/api/v1/blessings/generate-narrative",
            json={
                "target_name": "All Beings",
                "target_type": "group",
                "intention": "peace and happiness",
                "tradition": "universal"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "blessing_text" in data
        assert len(data["blessing_text"]) > 0

    def test_compassionate_blessing(self):
        """Test compassionate blessing"""
        response = client.post(
            "/api/v1/blessings/compassionate",
            json={
                "recipients": ["Person 1", "Person 2"],
                "intention": "healing and peace",
                "tradition": "buddhist"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "blessing_text" in data


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests combining multiple endpoints"""

    async def test_complete_healing_session(self):
        """Test a complete healing session workflow"""

        # 1. Generate scalar waves
        scalar_response = client.post(
            "/api/v1/scalar/generate",
            json={"method": "hybrid", "count": 1000, "intensity": 0.8}
        )
        assert scalar_response.status_code == 200

        # 2. Start radionics broadcast
        radionics_response = client.post(
            "/api/v1/radionics/healing-protocol",
            json={"target_name": "Test Session", "duration_minutes": 1}
        )
        assert radionics_response.status_code == 200

        # 3. Generate blessing
        blessing_response = client.post(
            "/api/v1/blessings/generate-narrative",
            json={
                "target_name": "Test Session",
                "target_type": "session",
                "intention": "healing",
                "tradition": "universal"
            }
        )
        assert blessing_response.status_code == 200

        # 4. Get chakra info
        chakra_response = client.get("/api/v1/anatomy/chakras")
        assert chakra_response.status_code == 200

        # All steps completed successfully
        assert True

    async def test_visualization_pipeline(self):
        """Test visualization generation pipeline"""

        # Generate different visualizations
        visualizations = ["chakras", "meridians", "central-channel"]

        for viz_type in visualizations:
            response = client.post(
                f"/api/v1/anatomy/visualize/{viz_type}",
                json={"width": 600, "height": 800, "format": "png"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "image_data" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
