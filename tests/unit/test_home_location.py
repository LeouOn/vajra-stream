"""Workings remember where they were sealed: the home location store, its API, and privacy.

The store is the suite's temp file (tests/conftest.py ``_isolated_home_location``),
geocoding is the conftest stub, and folios live in a tmp dir. Nothing here
contacts ComfyUI, a geocoder or an LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.working as working
from backend.app.api.v1.endpoints import operator as operator_endpoint
from backend.app.api.v1.endpoints import user_settings
from core import home_location, sky
from core.provenance import RECORD

KATHMANDU = {"latitude": 27.717245, "longitude": 85.323961, "label": "Kathmandu", "source": "browser"}


@pytest.fixture
def workings_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path / "workings")
    return tmp_path / "workings"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(user_settings.router, prefix="/api/v1/settings")
    app.include_router(operator_endpoint.router, prefix="/api/v1/operator")
    return TestClient(app)


# -- the store -------------------------------------------------------------------------


def test_store_is_isolated_and_starts_empty():
    assert home_location.store_path().name == "home_location.json"
    assert ".vajra-stream" not in str(home_location.store_path())
    assert home_location.get_home_location() is None


def test_set_get_clear_round_trip():
    stored = home_location.set_home_location(KATHMANDU)
    assert stored["latitude"] == 27.7172 and stored["longitude"] == 85.324  # 4 places kept
    assert stored["label"] == "Kathmandu" and stored["source"] == "browser"
    got = home_location.get_home_location()
    assert got is not None and got["latitude"] == 27.7172 and got["updated_at"]
    raw = home_location.store_path().read_bytes()
    assert b"\r\n" not in raw  # LF on disk
    assert home_location.clear_home_location() is True
    assert home_location.get_home_location() is None
    assert home_location.clear_home_location() is False


@pytest.mark.parametrize(
    "raw",
    [
        {"latitude": 91, "longitude": 0},
        {"latitude": 0, "longitude": -180.5},
        {"latitude": "north", "longitude": 0},
        {"latitude": float("nan"), "longitude": 0},
        {"latitude": True, "longitude": 0},
        {"longitude": 10},
        {"latitude": 1, "longitude": 2, "source": "satellite"},
    ],
)
def test_invalid_locations_are_rejected(raw):
    with pytest.raises(ValueError):
        home_location.normalize_location(raw)


def test_lat_lon_spellings_and_label_cleanup():
    loc = home_location.normalize_location({"lat": -33.9, "lng": 151.2, "label": "  Sydney \n NSW "})
    assert loc == {"latitude": -33.9, "longitude": 151.2, "label": "Sydney NSW", "source": "typed"}
    assert home_location.normalize_location({"lat": 1, "lon": 2, "label": ""})["label"] is None


def test_a_corrupt_store_reads_as_unset():
    path = home_location.store_path()
    path.write_text("{not json", encoding="utf-8")
    assert home_location.get_home_location() is None


def test_setting_does_not_log_coordinates(caplog):
    with caplog.at_level(logging.DEBUG, logger="core.home_location"):
        home_location.set_home_location(KATHMANDU)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "27.7" not in text and "85.3" not in text


# -- the API ---------------------------------------------------------------------------


def test_api_put_get_delete(client):
    assert client.get("/api/v1/settings/location").json()["location"] is None
    res = client.put(
        "/api/v1/settings/location",
        json={"latitude": 27.717245, "longitude": 85.323961, "label": "Kathmandu", "source": "browser"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["location"]["source"] == "browser"
    assert body["display"] == "Kathmandu (27.7°, 85.3°)"
    assert body["default"] == {"latitude": 37.7749, "longitude": -122.4194}
    assert client.get("/api/v1/settings/location").json()["location"]["label"] == "Kathmandu"
    gone = client.delete("/api/v1/settings/location").json()
    assert gone["cleared"] is True and gone["location"] is None
    assert home_location.get_home_location() is None


@pytest.mark.parametrize(
    "body",
    [
        {"latitude": 95, "longitude": 0},
        {"latitude": 10, "longitude": 200},
        {"latitude": 10},
        {},
        {"place": "   "},
        {"latitude": 1, "longitude": 1, "source": "geocoded"},  # only the server geocodes
    ],
)
def test_api_validates(client, body):
    assert client.put("/api/v1/settings/location", json=body).status_code == 422
    assert home_location.get_home_location() is None


def test_api_geocodes_a_typed_place(client):
    res = client.put("/api/v1/settings/location", json={"place": "Tokyo"})
    assert res.status_code == 200, res.text
    loc = res.json()["location"]
    assert loc["source"] == "geocoded" and loc["label"] == "Tokyo"
    assert (loc["latitude"], loc["longitude"]) == (35.6762, 139.6503)


def test_api_unknown_place_is_a_400(client):
    res = client.put("/api/v1/settings/location", json={"place": "Xyzzy Nowhere"})
    assert res.status_code == 400
    assert home_location.get_home_location() is None


def test_settings_router_is_registered_in_the_app():
    from backend.app.api.v1.api import api_router

    paths = {getattr(r, "path", "") for r in api_router.routes}
    assert "/settings/location" in paths


# -- workings remember where they were sealed ------------------------------------------


def test_explicit_location_wins_over_home(workings_dir):
    home_location.set_home_location({"latitude": 51.5074, "longitude": -0.1278, "label": "London"})
    folio = working.run_working("peace for the river", broadcast=False, location=KATHMANDU)
    assert folio["location"] == {"latitude": 27.7172, "longitude": 85.324, "label": "Kathmandu", "source": "browser"}
    assert folio["provenance"]["location"] == RECORD
    assert json.loads((workings_dir / f"{folio['working_id']}.json").read_text(encoding="utf-8"))["location"]


def test_home_location_applies_when_none_is_given(workings_dir):
    home_location.set_home_location({"latitude": 51.5074, "longitude": -0.1278, "label": "London"})
    folio = working.run_working("peace for the hills", broadcast=False)
    assert folio["location"] == {"latitude": 51.5074, "longitude": -0.1278, "label": "London", "source": "typed"}
    assert working.load_working(folio["working_id"])["provenance"]["location"] == RECORD


def test_no_location_falls_back_to_the_default(workings_dir):
    folio = working.run_working("peace for the valley", broadcast=False)
    assert folio["location"] is None
    assert sky.observer_for(folio)[2] == "default"


def test_an_invalid_explicit_location_seals_nothing(workings_dir):
    with pytest.raises(ValueError):
        working.run_working("peace", broadcast=False, location={"latitude": 300, "longitude": 0})
    assert not workings_dir.exists() or not list(workings_dir.glob("wrk_*.json"))


def test_observer_uses_the_sealed_location():
    folio = {"location": {"latitude": 27.7172, "longitude": 85.324, "label": "Kathmandu", "source": "typed"}}
    assert sky.observer_for(folio) == (27.7172, 85.324, "folio")
    assert sky.observer_label(folio) == "Kathmandu"


def test_operator_request_threads_location(client, workings_dir):
    res = client.post(
        "/api/v1/operator/working",
        json={"intention": "clear water", "broadcast": False, "location": KATHMANDU},
    )
    assert res.status_code == 200, res.text
    assert res.json()["location"]["label"] == "Kathmandu"
    bad = client.post(
        "/api/v1/operator/working",
        json={"intention": "clear water", "broadcast": False, "location": {"latitude": 100, "longitude": 0}},
    )
    assert bad.status_code == 422


def test_llm_tool_drops_a_bad_location_and_uses_home(workings_dir):
    from backend.core.llm_agent.tools import run_working as tool_run_working

    home_location.set_home_location({"latitude": 48.8566, "longitude": 2.3522, "label": "Paris"})
    not_a_place: Any = "somewhere"
    folio = tool_run_working("peace for the hills", broadcast=False, location=not_a_place)
    assert "location_note" in folio and folio["location"]["label"] == "Paris"
    folio = tool_run_working("peace for the coast", broadcast=False, location={"latitude": 1.5, "longitude": 2.5})
    assert folio["location"]["latitude"] == 1.5 and "location_note" not in folio


def test_tool_spec_advertises_an_optional_location():
    from core import tool_registry

    spec = tool_registry.get_spec("run_working")
    assert "location" in spec.parameters["properties"]
    assert "location" not in spec.parameters["required"]


# -- privacy ---------------------------------------------------------------------------


def test_caption_shows_label_and_rounded_coordinates_only():
    fact = sky.observer_fact(27.717245, 85.323961, "folio", "Kathmandu")
    assert fact["value"] == "Kathmandu (27.7°, 85.3°), the folio's location"
    assert "27.717" not in fact["value"]
    default = sky.observer_fact(37.7749, -122.4194, "default")["value"]
    assert "default location" in default and "37.8°, -122.4°" in default


def test_public_sky_rounds_observer_and_sidereal_time():
    computed = {"observer": {"lat": 27.717245, "lon": 85.323961}, "local_sidereal_deg": 123.456}
    out = sky.public_sky(computed, "folio", "Kathmandu")
    assert out["observer"] == {"lat": 27.7, "lon": 85.3, "source": "folio", "label": "Kathmandu"}
    assert out["local_sidereal_deg"] == 123.5
    assert computed["observer"]["lat"] == 27.717245  # the input is not mutated


def test_witness_caption_facts_never_show_full_precision(workings_dir):
    pytest.importorskip("swisseph")
    folio = working.run_working("peace for the river", broadcast=False, location=KATHMANDU)
    facts = {f["label"]: f["value"] for f in working.witness_caption_facts(folio)}
    assert facts["Sky observer"] == "Kathmandu (27.7°, 85.3°), the folio's location"
    computed = working._folio_sky(folio)
    assert computed is not None
    assert computed["observer"] == {"lat": 27.7, "lon": 85.3, "source": "folio", "label": "Kathmandu"}
    assert "27.717" not in json.dumps(computed) and "85.32" not in json.dumps(computed)


def test_strip_pii_omits_the_location():
    folio = {
        "working_id": "wrk_abc",
        "intention": "peace",
        "location": dict(KATHMANDU),
        "provenance": {"location": RECORD, "sealed_at": RECORD},
        "witness": {
            "caption_facts": [
                {"label": "Sky observer", "value": "Kathmandu (27.7°, 85.3°), the folio's location"},
                {"label": "Moon at sealing", "value": "40% illuminated"},
            ],
            "sky": {"observer": {"lat": 27.7, "lon": 85.3, "source": "folio", "label": "Kathmandu"}, "moon": {}},
        },
    }
    out = home_location.strip_location_pii(folio)
    text = json.dumps(out)
    assert "location" not in out and "Kathmandu" not in text and "27.7" not in text and "85.3" not in text
    assert out["witness"]["caption_facts"][1]["value"] == "40% illuminated"
    assert out["witness"]["sky"]["observer"] == {"source": "folio", "redacted": True}
    assert folio["location"]["label"] == "Kathmandu"  # the original is untouched


def test_get_working_strip_pii(client, workings_dir):
    folio = working.run_working("peace for the river", broadcast=False, location=KATHMANDU)
    full = client.get(f"/api/v1/operator/workings/{folio['working_id']}").json()
    assert full["location"]["label"] == "Kathmandu"
    stripped = client.get(f"/api/v1/operator/workings/{folio['working_id']}?strip_pii=true").json()
    assert "location" not in stripped and "Kathmandu" not in json.dumps(stripped)
