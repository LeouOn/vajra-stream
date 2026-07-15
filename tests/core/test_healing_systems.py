"""Tests for ``core.healing_systems`` — Vedic, Chinese, Tibetan healing models.

Covers the public API:
- :class:`ChakraSystem` — 7-chakra Vedic/Tantric model.
- :class:`MeridianSystem` — 12 primary meridians + 8 extraordinary vessels.
- :class:`TibetanChannelSystem` — Tsa/Lung/Thigle subtle body.
- :class:`IntegratedHealingProtocol` — cross-system protocol generator.

This module is pure data/lookup logic — no I/O, no DB, no LLM. All tests
exercise the in-memory behavior contract.
"""

from __future__ import annotations

import pytest

from core.healing_systems import (
    ChakraSystem,
    IntegratedHealingProtocol,
    MeridianSystem,
    TibetanChannelSystem,
)

# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all four expected public classes."""
    import core.healing_systems as mod

    for name in (
        "ChakraSystem",
        "MeridianSystem",
        "TibetanChannelSystem",
        "IntegratedHealingProtocol",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. ChakraSystem data + lookup
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chakra_system_has_all_seven_chakras_with_solfeggio_frequencies():
    """ChakraSystem populates the classic 7 chakras with Solfeggio frequencies."""
    sys = ChakraSystem()
    expected_names = {
        "muladhara",
        "svadhisthana",
        "manipura",
        "anahata",
        "vishuddha",
        "ajna",
        "sahasrara",
    }
    assert set(sys.chakras.keys()) == expected_names

    # Each chakra must have the canonical Solfeggio frequency used in
    # healing work; cross-check against the documented module summary.
    expected_freq = {
        "muladhara": 396,
        "svadhisthana": 417,
        "manipura": 528,
        "anahata": 639,
        "vishuddha": 741,
        "ajna": 852,
        "sahasrara": 963,
    }
    for name, freq in expected_freq.items():
        assert sys.chakras[name]["frequency"] == freq
        assert sys.chakras[name]["seed_mantra"], f"{name} missing seed mantra"


@pytest.mark.unit
def test_chakra_get_chakra_for_condition_known_and_unknown():
    """get_chakra_for_condition maps known conditions; returns [] for unknown."""
    sys = ChakraSystem()

    # Known physical
    assert sys.get_chakra_for_condition("heart_disease") == ["anahata"]
    assert sys.get_chakra_for_condition("headache") == ["ajna"]

    # Known emotional — anxiety maps to two chakras
    assert sys.get_chakra_for_condition("anxiety") == ["muladhara", "anahata"]

    # Case-insensitive lookup
    assert sys.get_chakra_for_condition("DEPRESSION") == ["sahasrara", "anahata"]

    # Unknown condition returns an empty list
    assert sys.get_chakra_for_condition("never_heard_of_this") == []


@pytest.mark.unit
def test_chakra_get_healing_protocol_returns_structured_dict():
    """get_healing_protocol returns frequencies/mantra/color/element/practices."""
    sys = ChakraSystem()

    # Known chakra
    proto = sys.get_healing_protocol("anahata")
    assert isinstance(proto, dict)
    assert proto["frequencies"] == [639]
    assert proto["mantra"] == "YAM"
    assert "Green" in proto["color"] or "Pink" in proto["color"]
    assert proto["element"] == "Air"
    assert isinstance(proto["practices"], list) and proto["practices"]

    # Unknown chakra returns empty dict (not an error)
    assert sys.get_healing_protocol("nonexistent_chakra") == {}


# ---------------------------------------------------------------------------
# 3. MeridianSystem
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_meridian_get_meridian_for_time_covers_chinese_medicine_clock():
    """get_meridian_for_time returns the correct meridian for canonical hours."""
    sys = MeridianSystem()

    # Canonical mapping from Chinese Medicine Clock
    cases = {
        4: "lung",  # 3-5 AM
        6: "large_intestine",  # 5-7 AM
        8: "stomach",  # 7-9 AM
        10: "spleen",  # 9-11 AM
        12: "heart",  # 11-13
        14: "small_intestine",  # 13-15
        16: "bladder",  # 15-17
        18: "kidney",  # 17-19
        20: "pericardium",  # 19-21
        22: "triple_warmer",  # 21-23
        0: "gallbladder",  # 23-1
        2: "liver",  # 1-3
    }
    for hour, expected_meridian in cases.items():
        assert sys.get_meridian_for_time(hour) == expected_meridian, f"Hour {hour} should map to {expected_meridian}"


@pytest.mark.unit
def test_meridian_get_meridian_for_condition_returns_list():
    """get_meridian_for_condition returns a list (possibly empty) for any input."""
    sys = MeridianSystem()

    # Known conditions return at least one meridian
    assert sys.get_meridian_for_condition("headache") == ["liver", "gallbladder", "stomach"]
    assert sys.get_meridian_for_condition("respiratory") == ["lung"]

    # Unknown condition returns empty list, never raises
    assert sys.get_meridian_for_condition("unknown_xyz") == []


# ---------------------------------------------------------------------------
# 4. TibetanChannelSystem data shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tibetan_channel_system_has_channels_wheels_and_winds():
    """TibetanChannelSystem populates three channels, four wheels, five winds."""
    sys = TibetanChannelSystem()

    # Three main channels: central (uma), right (roma), left (kyangma)
    assert set(sys.main_channels.keys()) == {"central", "right", "left"}
    assert sys.main_channels["central"]["tibetan"] == "uma"
    assert sys.main_channels["right"]["tibetan"] == "roma"
    assert sys.main_channels["left"]["tibetan"] == "kyangma"

    # Channel wheels: crown, throat, heart, navel
    assert set(sys.channel_wheels.keys()) >= {"crown", "throat", "heart", "navel"}

    # Five winds (lung)
    assert len(sys.five_winds) == 5
    assert "life_bearing" in sys.five_winds


# ---------------------------------------------------------------------------
# 5. IntegratedHealingProtocol
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_integrated_protocol_generate_protocol_aggregates_chakra_data():
    """generate_protocol for a known condition pulls frequencies from chakras."""
    proto = IntegratedHealingProtocol()

    # anxiety -> muladhara (396) + anahata (639)
    result = proto.generate_protocol("anxiety", include_astrology=False)

    assert isinstance(result, dict)
    assert result["condition"] == "anxiety"
    assert result["chakras_involved"] == ["muladhara", "anahata"]
    assert 396 in result["frequencies"]
    assert 639 in result["frequencies"]
    # Should also aggregate healing practices from each chakra
    assert isinstance(result["practices"], list) and result["practices"]


@pytest.mark.unit
def test_integrated_protocol_create_session_plan_has_three_phases():
    """create_session_plan returns a plan with opening/main/closing phases."""
    proto = IntegratedHealingProtocol()

    plan = proto.create_session_plan(intention="grounding", duration_minutes=45)

    assert plan["intention"] == "grounding"
    assert plan["duration"] == 45
    assert isinstance(plan["phases"], list) and len(plan["phases"]) == 3

    phase_names = [p["name"] for p in plan["phases"]]
    assert "Opening/Grounding" in phase_names
    assert "Main Practice" in phase_names
    assert "Closing/Integration" in phase_names

    # Phase durations must sum to the total duration
    assert sum(p["duration"] for p in plan["phases"]) == 45


# ---------------------------------------------------------------------------
# 6. Error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_integrated_protocol_generate_protocol_unknown_condition_safe():
    """generate_protocol with an unknown condition must not raise."""
    proto = IntegratedHealingProtocol()

    # Should return a populated protocol structure with empty aggregations
    result = proto.generate_protocol("totally_made_up_condition")

    assert result["condition"] == "totally_made_up_condition"
    assert result["chakras_involved"] == []
    assert result["meridians_involved"] == []
    assert result["frequencies"] == []
    assert result["mantras"] == []
    # Practices may be empty, but the dict must always be returned
    assert isinstance(result, dict)
