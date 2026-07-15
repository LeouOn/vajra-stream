import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    # Use as context manager so the FastAPI lifespan runs — this initializes
    # app.state.llm_registry via build_default_registry(), which the
    # /providers/register and /providers/unregister endpoints depend on.
    with TestClient(app) as c:
        yield c


def test_providers_health_endpoint(client):
    response = client.get("/api/v1/llm/providers/health")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "healthy_count" in data
    assert "total_count" in data


# ─── Dynamic provider registration endpoints (added in feat/llm-providers) ──


def test_providers_available_returns_catalog(client):
    """GET /providers/available should return the full provider catalog."""
    response = client.get("/api/v1/llm/providers/available")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    catalog = data["providers"]
    # Every supported provider must be listed.
    expected = {"openai", "anthropic", "openrouter", "deepseek", "z_ai", "minimax", "lm_studio", "local_gguf"}
    assert expected.issubset(set(catalog.keys()))
    # Each entry has the shape the UI needs.
    for name, entry in catalog.items():
        assert "label" in entry, f"{name} missing label"
        assert "requires_api_key" in entry, f"{name} missing requires_api_key"
        assert "default_priority" in entry, f"{name} missing default_priority"


def test_providers_discover_returns_shape(client):
    """POST /providers/discover should return discovered + unreachable lists."""
    response = client.post("/api/v1/llm/providers/discover")
    assert response.status_code == 200
    data = response.json()
    assert "discovered" in data
    assert "unreachable" in data
    assert isinstance(data["discovered"], list)
    assert isinstance(data["unreachable"], list)
    # Every entry has the expected shape.
    for ep in data["discovered"] + data["unreachable"]:
        assert "name" in ep
        assert "base_url" in ep
        assert "reachable" in ep
        assert "models" in ep
        assert "error" in ep


def test_providers_test_lm_studio_without_server(client):
    """POST /providers/test with lm_studio config should return unreachable if
    no LM Studio server is running (which is the case in CI / dev)."""
    response = client.post(
        "/api/v1/llm/providers/test",
        json={
            "provider": "lm_studio",
            "base_url": "http://localhost:1234/v1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    # We don't assert reachable since the dev box may or may not have LM Studio.
    # We just assert the shape.
    assert "reachable" in data
    assert "provider" in data or "error" in data


def test_providers_test_unknown_provider_returns_error(client):
    """POST /providers/test with an unsupported provider name should 400."""
    response = client.post(
        "/api/v1/llm/providers/test",
        json={
            "provider": "fictional_provider_xyz",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    # Error message should mention the bad provider name and list supported ones.
    assert "fictional_provider_xyz" in data["detail"]


def test_providers_register_missing_api_key_for_openai(client):
    """POST /providers/register for OpenAI without an API key should 400."""
    # First unregister if already present, to ensure a clean state.
    client.post("/api/v1/llm/providers/unregister", json={"provider": "openai"})
    response = client.post(
        "/api/v1/llm/providers/register",
        json={
            "provider": "openai",
            # No api_key
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "API key" in data["detail"]


def test_providers_register_unregister_round_trip(client):
    """Full round trip: register a no-key provider (lm_studio) then unregister it."""
    # Clean up any prior registration.
    client.post("/api/v1/llm/providers/unregister", json={"provider": "lm_studio"})

    # Register.
    reg = client.post(
        "/api/v1/llm/providers/register",
        json={
            "provider": "lm_studio",
            "base_url": "http://localhost:1234/v1",
            "priority": 80,
        },
    )
    assert reg.status_code == 200
    reg_data = reg.json()
    assert reg_data["registered"] == "lm_studio"
    assert reg_data["priority"] == 80

    # Verify it shows up in /providers/health.
    health = client.get("/api/v1/llm/providers/health").json()
    names = [p["provider"] for p in health["providers"]]
    assert "lm_studio" in names, f"lm_studio missing from {names}"

    # Re-registering the same name should 409.
    dup = client.post(
        "/api/v1/llm/providers/register",
        json={
            "provider": "lm_studio",
        },
    )
    assert dup.status_code == 409

    # Unregister.
    unreg = client.post("/api/v1/llm/providers/unregister", json={"provider": "lm_studio"})
    assert unreg.status_code == 200
    assert unreg.json()["unregistered"] == "lm_studio"

    # Verify it's gone.
    health2 = client.get("/api/v1/llm/providers/health").json()
    names2 = [p["provider"] for p in health2["providers"]]
    assert "lm_studio" not in names2, f"lm_studio still present after unregister: {names2}"


def test_providers_unregister_missing_returns_404(client):
    """POST /providers/unregister for a provider that isn't registered should 404."""
    response = client.post(
        "/api/v1/llm/providers/unregister",
        json={
            "provider": "fictional_provider_xyz",
        },
    )
    assert response.status_code == 404


def test_providers_register_lm_studio_with_priority(client):
    """Register lm_studio with a custom priority — should accept and round-trip."""
    client.post("/api/v1/llm/providers/unregister", json={"provider": "lm_studio"})
    response = client.post(
        "/api/v1/llm/providers/register",
        json={
            "provider": "lm_studio",
            "base_url": "http://localhost:1234/v1",
            "priority": 75,
        },
    )
    # Either 200 (success) or 503 (registry not initialized in CI).
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert response.json()["priority"] == 75
    # Clean up regardless.
    client.post("/api/v1/llm/providers/unregister", json={"provider": "lm_studio"})
