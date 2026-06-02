import os
import time
import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_e2e_batch_to_results(tmp_path):
    """Full E2E: launch batch, poll run, fetch results in markdown + JSON + JSONL."""
    db_path = str(tmp_path / "test_e2e.db")
    os.environ["VAJRA_DB_PATH"] = db_path

    from backend.app.main import app
    from core.schema import init_db
    init_db(db_path=db_path)

    client = TestClient(app)

    # Step 1: POST /astrology/extract with 5 tuples and 3 systems
    r = client.post("/api/v1/astrology/extract", json={
        "tuples": [
            {"date_iso": f"2026-{i+1:02d}-01T12:00:00Z", "lat": i*5.0, "lon": i*5.0}
            for i in range(5)
        ],
        "config": {"systems": ["western"]}
    })
    assert r.status_code == 200, f"extract failed: {r.text}"
    data = r.json()
    run_id = data["run_id"]
    assert data["status"] == "queued"
    assert data["total_tuples"] == 5

    # Step 2: Poll until done (up to 120s — western system only is faster)
    deadline = time.time() + 120
    while time.time() < deadline:
        r2 = client.get(f"/api/v1/astrology/runs/{run_id}")
        assert r2.status_code == 200
        if r2.json()["status"] in ("done", "partial", "error"):
            break
        time.sleep(1.0)
    else:
        pytest.fail(f"Run {run_id} did not complete within 120s")

    final_status = r2.json()["status"]
    assert final_status in ("done", "partial"), f"Unexpected status: {final_status}"

    # Step 3: GET results in markdown
    r3 = client.get(f"/api/v1/astrology/runs/{run_id}/results?format=markdown")
    assert r3.status_code == 200
    md = r3.text
    for i in range(5):
        assert f"## Tuple {i}" in md, f"Missing Tuple {i} in markdown"
    assert "Positions" in md or "Western" in md

    # Step 4: GET results in JSON
    r4 = client.get(f"/api/v1/astrology/runs/{run_id}/results?format=json")
    assert r4.status_code == 200
    import json
    j = json.loads(r4.text)
    assert "schema_version" in j
    assert len(j.get("tuples", [])) == 5

    # Step 5: GET export as JSONL
    r5 = client.get(f"/api/v1/astrology/runs/{run_id}/results/export?fmt=jsonl")
    assert r5.status_code == 200
    lines = [l for l in r5.text.strip().split("\n") if l]
    assert len(lines) == 5
    for line in lines:
        json.loads(line)  # must be valid JSON
