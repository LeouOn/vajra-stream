from fastapi.testclient import TestClient

import pytest


@pytest.fixture
def client():
    from backend.app.main import app
    return TestClient(app)


@pytest.mark.integration
class TestServerHealth:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
