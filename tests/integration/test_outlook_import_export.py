import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.app.api.v1.endpoints.outlook as outlook_endpoint
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Run these tests against a throwaway database.

    The endpoint's real resolver points at the project ledger — an
    unpatched ``DELETE FROM outlook_narratives`` here would erase the
    practitioner's actual history.
    """
    db_file = tmp_path / "outlook_history_test.db"
    from core.schema import init_db

    init_db(str(db_file)).close()

    def _connect():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(outlook_endpoint, "get_db_connection", _connect)
    yield


def test_export_import_workflow():
    # 1. Export initial (should be empty after clean_db)
    res_export_init = client.get("/api/v1/outlook/export")
    assert res_export_init.status_code == 200
    data_export_init = res_export_init.json()
    assert data_export_init["status"] == "success"
    assert len(data_export_init["narratives"]) == 0

    # 2. Import dummy narratives
    dummy_narrative = {
        "type": "single",
        "genre": "healing",
        "languages": ["English", "Tibetan"],
        "lat": 34.0522,
        "lon": -118.2437,
        "date_generated": "2026-05-30T12:00:00",
        "content": "A beautiful test blessing cycles transmission.",
        "astrology_context": "Sun conjunct Jupiter",
        "divination_context": "Hexagram 1: The Creative",
        "divination_raw": {"hexagram": 1, "lines": [9, 9, 9, 9, 9, 9]},
        "entities_invoked": "Tara, Medicine Buddha",
    }

    res_import = client.post("/api/v1/outlook/import", json=[dummy_narrative])
    assert res_import.status_code == 200
    data_import = res_import.json()
    assert data_import["status"] == "success"
    assert data_import["imported"] == 1

    # 3. Export again and verify contents
    res_export = client.get("/api/v1/outlook/export")
    assert res_export.status_code == 200
    data_export = res_export.json()
    assert data_export["status"] == "success"
    assert len(data_export["narratives"]) == 1

    exported = data_export["narratives"][0]
    assert exported["type"] == dummy_narrative["type"]
    assert exported["genre"] == dummy_narrative["genre"]
    assert exported["languages"] == dummy_narrative["languages"]
    assert exported["lat"] == dummy_narrative["lat"]
    assert exported["lon"] == dummy_narrative["lon"]
    assert exported["content"] == dummy_narrative["content"]
    assert exported["astrology_context"] == dummy_narrative["astrology_context"]
    assert exported["divination_context"] == dummy_narrative["divination_context"]
    assert exported["divination_raw"] == dummy_narrative["divination_raw"]
    assert exported["entities_invoked"] == dummy_narrative["entities_invoked"]

    # 4. Verify in history endpoint
    res_history = client.get("/api/v1/outlook/history")
    assert res_history.status_code == 200
    data_history = res_history.json()
    assert data_history["status"] == "success"
    assert len(data_history["history"]) == 1
    assert data_history["history"][0]["content"] == dummy_narrative["content"]


def test_export_import_carries_model_fields():
    dummy = {
        "type": "single",
        "genre": "healing",
        "content": "Model-badge round trip.",
        "model_used": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider_used": "openrouter",
    }
    res_import = client.post("/api/v1/outlook/import", json=[dummy])
    assert res_import.status_code == 200

    res_export = client.get("/api/v1/outlook/export")
    exported = res_export.json()["narratives"][0]
    assert exported["model_used"] == dummy["model_used"]
    assert exported["provider_used"] == dummy["provider_used"]

    res_history = client.get("/api/v1/outlook/history")
    item = res_history.json()["history"][0]
    assert item["model_used"] == dummy["model_used"]
    assert item["provider_used"] == dummy["provider_used"]


def test_history_filters_genre_type_and_search():
    rows = [
        {"type": "single", "genre": "healing", "content": "May all beings be at ease."},
        {"type": "single", "genre": "victory", "content": "Obstacles dissolve into wisdom."},
        {"type": "epic", "genre": "alchemist", "content": "The lead becomes gold slowly."},
    ]
    res_import = client.post("/api/v1/outlook/import", json=rows)
    assert res_import.status_code == 200

    base = client.get("/api/v1/outlook/history").json()["history"]
    assert len(base) == 3

    healing = client.get("/api/v1/outlook/history", params={"genre": "Healing"}).json()["history"]
    assert len(healing) == 1
    assert healing[0]["genre"] == "healing"

    epics = client.get("/api/v1/outlook/history", params={"narrative_type": "epic"}).json()["history"]
    assert len(epics) == 1
    assert epics[0]["type"] == "epic"

    gold = client.get("/api/v1/outlook/history", params={"q": "GOLD"}).json()["history"]
    assert len(gold) == 1
    assert "gold" in gold[0]["content"].lower()

    none_match = client.get("/api/v1/outlook/history", params={"q": "xyzzy-nothing"}).json()["history"]
    assert none_match == []

    combined = client.get("/api/v1/outlook/history", params={"genre": "victory", "q": "obstacles"}).json()["history"]
    assert len(combined) == 1


def test_delete_history_item():
    rows = [
        {"type": "single", "genre": "healing", "content": "Delete me."},
        {"type": "single", "genre": "healing", "content": "Keep me."},
    ]
    client.post("/api/v1/outlook/import", json=rows)
    items = client.get("/api/v1/outlook/history", params={"limit": 50}).json()["history"]
    assert len(items) == 2

    target = next(i for i in items if i["content"] == "Delete me.")
    res_delete = client.delete(f"/api/v1/outlook/history/{target['id']}")
    assert res_delete.status_code == 200
    assert res_delete.json()["deleted"] == target["id"]

    remaining = client.get("/api/v1/outlook/history", params={"limit": 50}).json()["history"]
    assert len(remaining) == 1
    assert remaining[0]["content"] == "Keep me."

    res_missing = client.delete(f"/api/v1/outlook/history/{target['id']}")
    assert res_missing.status_code == 404
