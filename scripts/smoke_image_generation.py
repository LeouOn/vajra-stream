"""Smoke test: verify the image-generation endpoints work end-to-end.

Run from project root:
    python scripts/smoke_image_generation.py
"""

from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)

    routes = sorted(r.path for r in app.routes if "/images" in r.path)
    print(f"[1] Image routes registered: {routes}")
    assert routes, "no /images routes registered — api.py wiring broken"

    r = client.get("/api/v1/images/config")
    print(f"[2] GET /config -> {r.status_code}")
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert "config" in cfg and "cost_stats" in cfg
    print(f"    enabled={cfg['config']['enabled']} model={cfg['config']['default_model']}")
    print(f"    cost_stats={cfg['cost_stats']}")

    r = client.get("/api/v1/images/models")
    print(f"[3] GET /models -> {r.status_code}")
    assert r.status_code == 200, r.text
    models = r.json()
    assert "openrouter" in models and "minimax" in models
    print(f"    openrouter={len(models['openrouter'])} models, minimax={len(models['minimax'])}")

    r = client.post("/api/v1/images/validate_prompt", json={"prompt": "heart chakra mandala"})
    print(f"[4] POST /validate_prompt -> {r.status_code}")
    assert r.status_code == 200, r.text
    v = r.json()
    print(f"    ok={v['ok']} estimated_tokens={v['estimated_tokens']}")
    assert v["ok"] is True

    long_prompt = " ".join(["lotus"] * 1500)
    r = client.post("/api/v1/images/validate_prompt", json={"prompt": long_prompt})
    v = r.json()
    print(f"    long prompt ok={v['ok']} error={v.get('error')}")
    assert v["ok"] is False

    r = client.post("/api/v1/images/generate", json={"prompt": "test"})
    print(f"[5] POST /generate (disabled) -> {r.status_code} (expected 503)")
    assert r.status_code == 503, f"expected 503 when disabled, got {r.status_code}: {r.text}"

    r = client.post(
        "/api/v1/images/config",
        json={"enabled": True, "daily_cost_cap_usd": 0.25},
    )
    print(f"[6] POST /config (enable) -> {r.status_code}")
    assert r.status_code == 200, r.text
    assert r.json()["config"]["enabled"] is True
    assert r.json()["config"]["daily_cost_cap_usd"] == 0.25

    r = client.post("/api/v1/images/generate", json={"prompt": "test"})
    print(f"[7] POST /generate (no API key) -> {r.status_code} (expected 503)")
    assert r.status_code == 503, r.text

    r = client.post("/api/v1/images/config", json={"enabled": False})
    print(f"[8] POST /config (disable) -> {r.status_code}")
    assert r.status_code == 200

    r = client.post("/api/v1/images/config", json={"nonsense_field": True})
    print(f"[9] POST /config (unknown field) -> {r.status_code} (expected 400)")
    assert r.status_code == 400, r.text

    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
