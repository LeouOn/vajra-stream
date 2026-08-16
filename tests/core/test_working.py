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
def test_same_intention_yields_same_dials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    a = working.run_working("peace for the watershed", broadcast=False)
    b = working.run_working("peace for the watershed", broadcast=False)
    assert a["rate_values"] == b["rate_values"]
    assert b["working_id"] == a["working_id"]
    assert b.get("reused") is True


@pytest.mark.unit
def test_run_working_is_idempotent_within_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    a = working.run_working("peace for the watershed", broadcast=False)
    b = working.run_working("peace for the watershed", broadcast=False)
    assert b["working_id"] == a["working_id"]
    assert b.get("reused") is True
    c = working.run_working("peace for the watershed", target="the children", broadcast=False)
    assert c["working_id"] != a["working_id"]
    assert not c.get("reused")


@pytest.mark.unit
def test_collapse_duplicate_workings_hides_all_but_newest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)

    def mint(working_id: str, intention: str, rates: list[int], day: int) -> None:
        working._persist(
            {
                "working_id": working_id,
                "sealed_at": f"2020-01-{day:02d}T00:00:00+00:00",
                "intention": intention,
                "target": "all beings",
                "rate_values": rates,
                "dials": [],
                "frequencies": [],
                "solfeggio_names": [],
            },
            index=False,
        )

    # Five pre-idempotency auto-chain retries of one sitting, plus one distinct sitting.
    rates = [68, 30, 71, 50, 68]
    for i in range(5):
        mint(f"wrk_dup{i:012x}", "peace for the watershed", rates, i + 1)
    mint("wrk_other000001", "a different sitting", [1, 2, 3, 4, 5], 9)

    result = working.collapse_duplicate_workings()

    assert result["unique_sittings"] == 2
    assert len(result["hidden"]) == 4
    visible = [w["working_id"] for w in working.list_workings()]
    assert len(visible) == 2
    assert f"wrk_dup{4:012x}" in visible  # newest duplicate survives
    for i in range(4):
        folio = working.load_working(f"wrk_dup{i:012x}")
        assert folio is not None
        assert folio["hidden"] is True
        assert folio["duplicate_of"] in visible

    # Idempotent: a second run hides nothing new.
    again = working.collapse_duplicate_workings()
    assert again["hidden"] == []
    assert again["unique_sittings"] == 2


@pytest.mark.unit
def test_list_workings_summary_carries_constellation_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    working._persist(
        {
            "working_id": "wrk_sky00000001",
            "sealed_at": "2026-08-16T00:00:00+00:00",
            "intention": "peace for the watershed",
            "target": "all beings",
            "rate_values": [68, 30, 71, 50, 68],
            "hour_stamp": {"planetary_hour": "Venus", "moon_phase": "Full Moon"},
            "saka_dawa": {"multiplier": 100000},
            "hidden": True,
            "duplicate_of": "wrk_keep000001",
        },
        index=False,
    )

    listed = working.list_workings(include_hidden=True)
    row = next(w for w in listed if w["working_id"] == "wrk_sky00000001")
    assert row["planetary_hour"] == "Venus"
    assert row["moon_phase"] == "Full Moon"
    assert row["saka_dawa_multiplier"] == 100000
    assert row["duplicate_of"] == "wrk_keep000001"


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
@pytest.mark.unit
def test_hide_and_delete_working(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working("a lamp in the dark", broadcast=False)
    hidden = working.set_working_hidden(folio["working_id"], True)
    assert hidden is not None
    assert hidden["hidden"] is True
    assert working.list_workings() == []
    listed = working.list_workings(include_hidden=True)
    assert listed[0]["working_id"] == folio["working_id"]
    updated = working.update_working_rates(folio["working_id"], [10, 20, 30, 40, 50])
    assert updated is not None
    assert updated["rate_values"] == [10, 20, 30, 40, 50]
    assert working.delete_working(folio["working_id"]) is True
    assert working.load_working(folio["working_id"]) is None


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
