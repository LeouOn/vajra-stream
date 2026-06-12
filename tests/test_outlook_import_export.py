import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1.endpoints.outlook import get_db_connection
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Clean the outlook narratives table before and after test execution."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM outlook_narratives")
    conn.commit()
    conn.close()
    yield
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM outlook_narratives")
    conn.commit()
    conn.close()


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
