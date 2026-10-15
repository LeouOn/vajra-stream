"""Draws must never pose as measurements (docs/DEVELOPMENT_ROADMAP.md, Phase 2).

RNG-based radionics stays: it is the digital analog of the stick pad or
pendulum. These tests pin the contract that every drawn value says so:

- GV / potency structures carry ``provenance`` with ``draw``.
- GV wording is a reading of a draw, never a diagnosis or a measurement.
- The WebSocket rate broadcast is computed, with no jitter.
- The crystal-broadcast fallback rate is flagged as a fallback.
- Attunement (e-meter) readings carry ``draw`` provenance everywhere they leave the service.
"""

import random
import re
from unittest.mock import MagicMock

import pytest

from core.operations import PROVENANCE_KINDS
from core.radionics_engine import (
    GeneralVitalityMeter,
    RadionicsAnalyzer,
    RadionicsRate,
    RandomNumberGenerator,
    SignatureCalculator,
    gv_band,
)

pytestmark = pytest.mark.unit

# Words that turn a drawn number into a claim of measurement, verdict or diagnosis.
DIAGNOSTIC_PATTERN = re.compile(
    r"excellent|intervention|attention recommended|depletion|diagnos|detected|measured|"
    r"weakened|significant|improvement possible",
    re.IGNORECASE,
)


def _assert_valid_provenance(mapping: dict) -> None:
    assert mapping, "provenance map must not be empty"
    for key, kind in mapping.items():
        assert kind in PROVENANCE_KINDS, f"{key!r} has unknown provenance {kind!r}"


# ---------------------------------------------------------------------------
# GV and potency (core/radionics_engine.py)
# ---------------------------------------------------------------------------


def test_gv_stats_are_labeled_draws():
    stats = GeneralVitalityMeter().measure_multiple(count=5, subject="Tara")
    _assert_valid_provenance(stats["provenance"])
    for key in ("mean", "median", "std", "min", "max", "measurements"):
        assert stats["provenance"][key] == "draw"


def test_gv_history_entries_are_labeled_draws():
    meter = GeneralVitalityMeter()
    meter.measure("Tara")
    assert meter.history[-1]["provenance"] == {"gv": "draw"}


@pytest.mark.parametrize("gv", [0, 150, 199.9, 200, 399, 400, 599, 600, 799, 800, 1000])
def test_interpret_gv_is_a_reading_of_a_draw_not_a_diagnosis(gv):
    text = GeneralVitalityMeter().interpret_gv(gv)
    assert text.startswith(f"Drawn GV {gv:.0f}")
    assert "stick-pad tradition" in text
    assert f"reads as {gv_band(gv)} vitality" in text
    assert not DIAGNOSTIC_PATTERN.search(text), text


def test_balancing_rates_carry_draw_provenance():
    rates = RadionicsAnalyzer().find_balancing_rates("Stress Relief", num_rates=3)
    for rate in rates:
        assert rate.provenance == {"values": "draw", "potency": "draw"}
        assert rate.to_dict()["provenance"] == {"values": "draw", "potency": "draw"}


def test_signature_rates_are_computed_not_drawn():
    calc = SignatureCalculator()
    for algorithm in ("hash", "gematria", "phonetic", "mixed"):
        rate = calc.text_to_rate("World Peace", num_dials=3, algorithm=algorithm)
        assert rate.provenance == {"values": "computed"}, algorithm
        # Computed means deterministic from the same input.
        assert calc.text_to_rate("World Peace", num_dials=3, algorithm=algorithm).values == rate.values


def test_rate_provenance_round_trips_through_dict():
    rate = RadionicsRate([1, 2, 3], name="r", potency=0.5, provenance={"values": "draw", "potency": "draw"})
    restored = RadionicsRate.from_dict(rate.to_dict())
    assert restored.provenance == {"values": "draw", "potency": "draw"}
    # Legacy payloads without provenance still load.
    legacy = RadionicsRate.from_dict({"values": [1], "name": "old"})
    assert legacy.provenance == {}


def test_analysis_labels_every_drawn_field(capsys):
    result = RadionicsAnalyzer().analyze_subject("Healing for Earth", num_rates=3)
    _assert_valid_provenance(result["provenance"])
    assert result["provenance"]["baseline_gv"] == "draw"
    assert result["provenance"]["resonant_rates"] == "draw"
    assert result["provenance"]["signature_rate"] == "computed"
    for rate in result["resonant_rates"]:
        assert rate["provenance"]["potency"] == "draw"
    assert not DIAGNOSTIC_PATTERN.search(result["interpretation"])
    assert "not a measurement" in result["note"]


def test_broadcast_with_feedback_says_nothing_was_emitted(capsys):
    analyzer = RadionicsAnalyzer()
    result = analyzer.broadcast_with_feedback("Tara", RadionicsRate([1, 2, 3]), duration_seconds=0)
    assert result["emitted"] is False
    _assert_valid_provenance(result["provenance"])
    assert result["provenance"]["gv_trend"] == "draw"


def test_rng_draws_do_not_reseed_the_global_random_module():
    random.seed(1234)
    expected = random.random()

    random.seed(1234)
    RandomNumberGenerator(mode="intention").generate(0, 100, 3, intention="compassion")
    RandomNumberGenerator(mode="quantum").generate(0, 100, 3)
    RandomNumberGenerator(mode="quantum").generate_float(0.0, 1.0, 2)
    assert random.random() == expected


def test_intention_mode_is_still_reproducible():
    a = RandomNumberGenerator(mode="intention").generate(0, 100, 5, intention="compassion")
    b = RandomNumberGenerator(mode="intention").generate(0, 100, 5, intention="compassion")
    assert a == b


# ---------------------------------------------------------------------------
# LLM tool outputs (modules/radionics_operator.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def dispatcher():
    from modules.radionics_operator import ToolDispatcher

    # These tools never touch the container; a stand-in passes the guard.
    return ToolDispatcher(container=MagicMock())


def test_gv_tool_output_is_labeled_a_draw(dispatcher):
    out = dispatcher.dispatch("measure_general_vitality", {"subject": "Tara", "samples": 4})
    assert out["method"] == "draw"
    _assert_valid_provenance(out["provenance"])
    for key in ("gv_mean", "gv_median", "gv_std", "gv_min", "gv_max", "interpretation"):
        assert out["provenance"][key] == "draw"
    assert out["interpretation"].startswith("Drawn GV ")
    assert not DIAGNOSTIC_PATTERN.search(out["interpretation"])
    assert "not a measurement" in out["note"]


def test_balancing_tool_output_is_labeled_a_draw(dispatcher):
    out = dispatcher.dispatch("find_balancing_rates", {"subject": "Grief", "num_rates": 2})
    assert out["provenance"] == {"balancing_rates": "draw"}
    for rate in out["balancing_rates"]:
        assert rate["provenance"]["potency"] == "draw"


def test_gv_tool_description_does_not_promise_a_measurement():
    from core.radionics_tools import RADIONICS_TOOLS

    by_name = {t["function"]["name"]: t["function"] for t in RADIONICS_TOOLS}
    desc = by_name["measure_general_vitality"]["description"]
    assert "DRAW" in desc
    assert "not a measurement" in desc
    assert "excellent" not in desc.lower()


def test_system_prompt_frames_gv_as_a_draw():
    from core.context_builder import build_system_prompt

    prompt = build_system_prompt({"gv_measurement": 640, "rng_state": {"state": "floating", "coherence": 0.7}})
    assert "General Vitality (drawn)" in prompt
    assert "RNG Needle (drawn)" in prompt
    assert "never a measurement" in prompt


@pytest.fixture
def operator():
    from modules.radionics_operator import RadionicsOperator

    op = RadionicsOperator(container=None, event_bus=None, llm=MagicMock())
    op._llm.client = None
    op._llm.local_model = None
    op._creative_llm = MagicMock()
    op._creative_llm.client = None
    op._creative_llm.local_model = None
    return op


@pytest.mark.parametrize(
    "state",
    [
        {"gv_measurement": 900},
        {"gv_measurement": 500},
        {"gv_measurement": 100},
        {"rng_state": {"state": "floating"}},
        {"rng_state": {"state": "rock_slam"}},
        {"rng_state": {"state": "rising"}},
    ],
)
def test_rule_based_insight_reads_draws_without_claiming_detection(operator, state):
    text = operator._fallback_insight(state)["insight"]
    assert "drawn" in text.lower() or "draw" in text.lower()
    assert not DIAGNOSTIC_PATTERN.search(text), text


def test_crystal_broadcast_flags_the_fallback_rate(operator, monkeypatch):
    monkeypatch.setattr(operator, "analyze_intention", lambda intention: {"suggested_rates": [], "analysis": {}})
    result = operator.prepare_crystal_broadcast("May all beings be free", duration_minutes=5)
    config = result["broadcast_config"]
    assert result["rate_is_fallback"] is True
    assert config["rate_is_fallback"] is True
    assert config["rate_source"] == "fallback_default"
    assert config["rate_values"] == [50, 50, 50]
    _assert_valid_provenance(config["provenance"])


def test_crystal_broadcast_derived_rate_is_not_flagged(operator):
    result = operator.prepare_crystal_broadcast("Send love and protection to all beings", duration_minutes=5)
    config = result["broadcast_config"]
    assert result["rate_is_fallback"] is False
    assert config["rate_is_fallback"] is False
    assert config["rate_source"] != "fallback_default"
    _assert_valid_provenance(config["provenance"])


# ---------------------------------------------------------------------------
# WebSocket rate broadcast (backend/core/services/vajra_service.py)
# ---------------------------------------------------------------------------


def _session(freq: float) -> dict:
    cfg = MagicMock()
    cfg.audio_config.frequency = freq
    return {"id": "s1", "config": cfg}


def test_rate_broadcast_has_no_jitter():
    from backend.core.services.vajra_service import rate_broadcast_message, session_rate

    assert session_rate(528.0) == 28.0
    assert session_rate(639.0) == 39.0
    rates = {rate_broadcast_message(_session(741.0))["data"]["rate"] for _ in range(50)}
    assert rates == {41.0}


def test_rate_broadcast_message_shape_is_compatible():
    from backend.core.services.vajra_service import rate_broadcast_message

    msg = rate_broadcast_message(_session(528.0))
    assert msg["type"] == "RADIONICS_RATE_BROADCAST"
    assert msg["data"]["rate"] == 28.0
    assert msg["data"]["session_id"] == "s1"
    assert msg["data"]["frequency"] == 528.0
    assert msg["data"]["provenance"] == {"rate": "computed"}
    assert isinstance(msg["timestamp"], float)


def test_rate_broadcast_defaults_without_audio_config():
    from backend.core.services.vajra_service import rate_broadcast_message

    msg = rate_broadcast_message({"id": "s2", "config": None})
    assert msg["data"]["frequency"] == 528.0
    assert msg["data"]["rate"] == 28.0


# ---------------------------------------------------------------------------
# Attunement e-meter (backend/core/services/rng_attunement_service.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def attunement():
    from backend.core.services.rng_attunement_service import RNGAttunementService

    svc = RNGAttunementService()
    sid = svc.create_session()
    return svc, sid


def test_attunement_reading_dict_is_labeled_a_draw(attunement):
    svc, sid = attunement
    data = svc.get_reading(sid).to_dict()
    _assert_valid_provenance(data["provenance"])
    for key in ("raw_value", "tone_arm", "needle_position", "needle_state", "coherence", "floating_needle_score"):
        assert data["provenance"][key] == "draw"
    assert isinstance(data["needle_state"], str)


def test_attunement_summary_is_labeled(attunement):
    svc, sid = attunement
    svc.get_reading(sid)
    summary = svc.get_session_summary(sid)
    _assert_valid_provenance(summary["provenance"])
    assert summary["provenance"]["avg_coherence"] == "draw"
    assert "not measurements" in summary["note"]


def test_attunement_endpoint_model_defaults_to_draw_provenance():
    from backend.app.api.v1.endpoints.rng_attunement import ReadingResponse

    resp = ReadingResponse(
        timestamp=0.0,
        raw_value=0.5,
        tone_arm=5.0,
        needle_position=0.0,
        needle_state="stuck",
        quality="fair",
        entropy=0.5,
        coherence=0.5,
        trend=0.0,
        floating_needle_score=0.1,
    )
    assert resp.provenance["floating_needle_score"] == "draw"
    assert "not measurements" in resp.note


def test_rng_tool_reading_is_labeled_a_draw(dispatcher, attunement):
    from backend.core.services import rng_attunement_service

    svc, sid = attunement
    original = rng_attunement_service._rng_service
    rng_attunement_service._rng_service = svc
    try:
        out = dispatcher.dispatch("get_rng_reading", {"session_id": sid})
    finally:
        rng_attunement_service._rng_service = original
    assert out["provenance"]["floating_needle_score"] == "draw"
    assert "not measurements" in out["note"]
