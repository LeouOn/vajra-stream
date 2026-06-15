import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_providers_health_endpoint(client):
    response = client.get("/api/v1/llm/providers/health")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "healthy_count" in data
    assert "total_count" in data
