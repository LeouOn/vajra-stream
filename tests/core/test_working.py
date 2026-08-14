"""Compound working: intention → 5-dial rate → Saka Dawa folio."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.working import run_working


@pytest.mark.unit
def test_run_working_seals_folio_without_broadcast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)

    folio = run_working(
        intention="May all beings be free from suffering",
        target="all beings",
        broadcast=False,
    )

    assert folio["working_id"].startswith("wrk_")
    assert folio["intention"].startswith("May all beings")
    assert folio["target"] == "all beings"
    assert len(folio["rate_values"]) == 5
    assert all(0 <= v <= 100 for v in folio["rate_values"])
    assert folio["saka_dawa"]["saka_dawa_duchen"]
    assert folio["spoken_charge"]
    assert folio["source"] == "command-center"
    assert folio["image_prompt"]
    assert "Manifestation" in folio["image_prompt"]
    assert folio["broadcast"] is None
    assert folio["saved"] is True
    saved = tmp_path / f"{folio['working_id']}.json"
    assert saved.exists()


@pytest.mark.unit
def test_run_working_keeps_hour_and_divination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working(
        "peace for the watershed",
        broadcast=False,
        source="cosmic-clock",
        chart_name="live sky",
        planetary_hour="Venus",
        moon_phase="Waxing Gibbous",
        divination={"system": "tarot", "cards": [{"name": "The Star"}]},
    )
    assert folio["source"] == "cosmic-clock"
    assert folio["chart_name"] == "live sky"
    assert folio["hour_stamp"]["planetary_hour"] == "Venus"
    assert folio["hour_stamp"]["moon_phase"] == "Waxing Gibbous"
    assert folio["divination"]["system"] == "tarot"


@pytest.mark.unit
def test_same_intention_yields_same_dials():
    a = run_working("peace for the watershed", broadcast=False)
    b = run_working("peace for the watershed", broadcast=False)
    assert a["rate_values"] == b["rate_values"]
    assert a["working_id"] != b["working_id"]


@pytest.mark.unit
def test_list_and_load_working(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working("peace for the watershed", broadcast=False)
    listed = working.list_workings()
    assert listed[0]["working_id"] == folio["working_id"]
    assert listed[0]["has_witness"] is False
    loaded = working.load_working(folio["working_id"])
    assert loaded is not None
    assert loaded["intention"] == folio["intention"]
    assert working.load_working("wrk_missing") is None


@pytest.mark.unit
def test_attach_witness_persists_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working("a quiet lamp", broadcast=False)

    def fake_generate_image(prompt: str, **kwargs):
        return {"image_data_url": "data:image/png;base64,QQ==", "model": "test", "cost_usd": 0}

    monkeypatch.setattr("backend.core.llm_agent.tools.generate_image", fake_generate_image)
    updated = working.attach_witness_image(folio["working_id"])
    assert updated["witness"]["status"] == "ok"
    assert updated["witness"]["image_data_url"].startswith("data:image")
    reloaded = working.load_working(folio["working_id"])
    assert reloaded is not None
    assert reloaded["witness"]["image_data_url"].startswith("data:image")


@pytest.mark.unit
def test_video_prompt_is_long_enough_for_minimax():
    from core.working import video_prompt_for

    prompt = video_prompt_for(
        {
            "intention": "peace for the watershed",
            "target": "the river",
            "spoken_charge": "For the river: peace.",
            "image_prompt": "A quiet ritual still life with brass bowls on dark wood.",
        }
    )
    assert len(prompt) >= 50


@pytest.mark.unit
def test_record_spoken_and_charge_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working("a lamp in the dark", broadcast=False)
    updated = working.record_spoken(folio["working_id"], {"status": "ok", "audio_path": "x.mp3"})
    assert updated["spoken"]["status"] == "ok"
    assert working.charge_audio_path(folio["working_id"]).name.endswith("_charge.mp3")


@pytest.mark.unit
def test_run_working_is_on_the_chat_allowlist():
    from backend.core.llm_agent.tools import ESSENTIAL_TOOL_ORDER, get_tool_schemas

    assert ESSENTIAL_TOOL_ORDER[0] == "run_working"
    assert "forge_witness" in ESSENTIAL_TOOL_ORDER
    names = {s["name"] for s in get_tool_schemas()}
    assert "run_working" in names
    assert "forge_witness" in names


@pytest.mark.unit
def test_run_working_request_accepts_hour_and_divination():
    from backend.app.api.v1.endpoints.operator import RunWorkingRequest

    req = RunWorkingRequest(
        intention="peace for the watershed",
        source="cosmic-clock",
        chart_name="live sky",
        planetary_hour="Venus",
        moon_phase="Waxing Gibbous",
        divination={"system": "tarot", "cards": [{"name": "The Star"}]},
    )
    assert req.source == "cosmic-clock"
    assert req.chart_name == "live sky"
    assert req.planetary_hour == "Venus"
    assert req.divination["system"] == "tarot"
