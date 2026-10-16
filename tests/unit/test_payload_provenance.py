"""Derived values in API payloads carry provenance (Phase 2, the honest instrument).

Covers the payloads the UI shows most: the astrology snapshot (computed, or
decorative placeholders without an ephemeris), sealed folios (records whose
sealed values say how they were made), divination casts (draws), the journey
character's stats (draws) and the Saka Dawa status (computed).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.provenance import PROVENANCE_KINDS


def _assert_valid(mapping: dict) -> None:
    assert mapping, "expected a non-empty provenance map"
    assert set(mapping.values()) <= PROVENANCE_KINDS


class _StubAstrology:
    """Just enough of AstrologicalCalculator for ``_get_astrology_data``."""

    def get_comprehensive_astrology(self, dt, loc):
        return {
            "datetime": dt.isoformat(),
            "location": {"latitude": loc[0], "longitude": loc[1]},
            "western": {"positions": {"sun": {"longitude": 10.0, "sign": "Aries", "degree": 10.0}}},
            "indian": {"panchanga": {"nakshatra": {"name": "Ashwini"}}},
            "chinese": {"zodiac_animal": "Horse"},
            "planetary_hours": {"current_planetary_hour": "Venus"},
        }

    def get_moon_phase(self, dt):
        return {"phase_name": "Waxing Crescent", "illumination": 12.5}

    def calculate_auspicious_times(self, dt, loc):
        return {"sunrise": dt}


@pytest.mark.unit
def test_astrology_snapshot_is_computed(monkeypatch: pytest.MonkeyPatch):
    from backend.core.services.vajra_service import vajra_service

    monkeypatch.setattr(vajra_service, "astrology", _StubAstrology())
    data = asyncio.run(vajra_service._get_astrology_data())
    _assert_valid(data["provenance"])
    for block in ("western", "indian", "chinese", "planetary_hours", "moon_phase", "planetary_positions"):
        assert data["provenance"][block] == "computed", block
    assert "fallback" not in data


@pytest.mark.unit
def test_astrology_placeholder_is_decorative(monkeypatch: pytest.MonkeyPatch):
    from backend.core.services.vajra_service import vajra_service

    monkeypatch.setattr(vajra_service, "astrology", None)
    data = asyncio.run(vajra_service._get_astrology_data())
    assert data["fallback"] is True
    assert data["provenance"]["moon_phase"] == "decorative"
    assert data["provenance"]["planetary_positions"] == "decorative"


@pytest.mark.unit
def test_astrology_endpoint_blocks_follow_the_snapshot():
    from backend.app.api.v1.endpoints.astrology import _snapshot_kind

    snapshot = {"western": {}, "provenance": {"western": "computed", "moon_phase": "decorative"}, "moon_phase": {}}
    assert _snapshot_kind(snapshot, "western") == "computed"
    assert _snapshot_kind(snapshot, "moon_phase") == "decorative"
    # A block the snapshot lacks is replaced by a default: decorative.
    assert _snapshot_kind(snapshot, "indian") == "decorative"


@pytest.mark.unit
def test_saved_chart_rows_label_record_and_computed():
    from backend.app.api.v1.endpoints.astrology import SavedChartResponse

    row = SavedChartResponse(
        id=1,
        name="A",
        birth_time_iso="2000-01-01T00:00:00",
        city="London",
        latitude=51.5,
        longitude=-0.1,
        timezone="Europe/London",
        created_at="x",
        updated_at="y",
    )
    assert row.provenance["birth_time_iso"] == "record"
    assert row.provenance["cached_chart_data"] == "computed"


@pytest.mark.unit
def test_sealed_folio_labels_its_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working(
        "peace for the watershed",
        broadcast=False,
        divination={"system": "tarot", "cards": [{"name": "The Star"}]},
    )
    _assert_valid(folio["provenance"])
    assert folio["provenance"]["sealed_at"] == "record"
    assert folio["provenance"]["rate_values"] == "computed"
    assert folio["provenance"]["divination"] == "draw"

    loaded = working.load_working(folio["working_id"])
    assert loaded is not None
    assert loaded["provenance"]["rate_values"] == "computed"

    rows = working.list_workings()
    assert rows[0]["provenance"]["rate_values"] == "computed"
    assert rows[0]["provenance"]["sealed_at"] == "record"


@pytest.mark.unit
def test_hand_set_dials_are_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    folio = working.run_working("clear water for the river", broadcast=False)
    retuned = working.update_working_rates(folio["working_id"], [11, 22, 33, 44, 55])
    assert retuned is not None
    assert retuned["provenance"]["rate_values"] == "record"
    # The carriers still follow the dials by formula.
    assert retuned["provenance"]["frequencies"] == "computed"
    reloaded = working.load_working(folio["working_id"])
    assert reloaded is not None and reloaded["provenance"]["rate_values"] == "record"
    assert working.list_workings()[0]["provenance"]["rate_values"] == "record"


@pytest.mark.unit
def test_legacy_folio_without_labels_is_labeled_on_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import json

    import core.working as working

    monkeypatch.setattr(working, "WORKINGS_DIR", tmp_path)
    (tmp_path / "wrk_legacy000001.json").write_text(
        json.dumps({"working_id": "wrk_legacy000001", "intention": "x", "rate_values": [1, 2, 3, 4, 5]}),
        encoding="utf-8",
    )
    loaded = working.load_working("wrk_legacy000001")
    assert loaded is not None
    assert loaded["provenance"]["rate_values"] == "computed"


@pytest.mark.unit
def test_divination_casts_are_draws():
    from backend.app.api.v1.endpoints import divination

    tarot = asyncio.run(divination.draw_tarot(divination.DrawTarotRequest(count=1)))
    assert tarot["provenance"] == {"cards": "draw"}
    cast = asyncio.run(divination.cast_iching())
    assert cast["provenance"] == {"cast": "draw"}
    shield = asyncio.run(divination.cast_geomancy())
    assert shield["provenance"] == {"chart": "draw"}


@pytest.mark.unit
def test_journey_character_stats_are_draws():
    from core.character_generator import CharacterGenerator

    sheet = CharacterGenerator().generate()
    assert sheet.to_dict()["provenance"]["stats"] == "draw"


@pytest.mark.unit
def test_saka_dawa_status_is_computed():
    from core.auspicious_timing import check_saka_dawa

    status = check_saka_dawa()
    _assert_valid(status["provenance"])
    assert set(status["provenance"].values()) == {"computed"}


@pytest.mark.unit
def test_recitation_and_practice_counts_are_records():
    from core.buddha_recitation_loop import BuddhaRecitationLoop
    from core.practice_engine import PracticeSession

    status = BuddhaRecitationLoop().get_status()
    assert status["provenance"]["total_recited"] == "record"
    practice = PracticeSession(practice_id="p", practice_name="P", intention="i", target_count=108).to_status_dict()
    assert practice["provenance"]["total_recited"] == "record"
