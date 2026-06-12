from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_massive_mops():
    payload = {"method": "hybrid", "count": 1000, "intensity": 1.0, "duration": 5.0}

    # Initialize container to ensure EventBus is active
    # EventBus is active on import

    response = client.post("/api/v1/scalar/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    print("Response data:", data)
    assert data["status"] == "success"
    assert data["count"] == 1000
    assert "mops" in data


if __name__ == "__main__":
    test_massive_mops()
