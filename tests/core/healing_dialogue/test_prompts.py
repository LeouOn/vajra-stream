# tests/core/healing_dialogue/test_prompts.py
"""Tests for the healing dialogue system prompt architecture.

Covers:
* :data:`HEALING_DIALOGUE_BASE_PROMPT` contains the key container phrases.
* :data:`PHASE_GUIDANCE` has an entry for every non-terminal phase.
* :func:`build_system_prompt` assembles base + phase guidance for each phase.
* :func:`build_system_prompt` injects astrology context when provided.
* :func:`build_system_prompt` injects somatic findings when provided.
"""

from __future__ import annotations

import pytest

from core.healing_dialogue.phases import DialoguePhase
from core.healing_dialogue.prompts import (
    HEALING_DIALOGUE_BASE_PROMPT,
    PHASE_GUIDANCE,
    build_system_prompt,
)

# ---------------------------------------------------------------------------
# HEALING_DIALOGUE_BASE_PROMPT
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "Vajrayana",
        "compassion",
        "five phases",
        "ARRIVAL",
        "SEEING",
        "MEETING",
        "RELEASE",
        "DEDICATION",
    ],
)
def test_base_prompt_contains_key_phrases(phrase):
    """The base prompt names the tradition, the core stance, and all five phases."""
    assert phrase.lower() in HEALING_DIALOGUE_BASE_PROMPT.lower()


def test_base_prompt_mentions_core_principles():
    """The base prompt spells out the non-negotiables (meet suffering, dedicate merit)."""
    lowered = HEALING_DIALOGUE_BASE_PROMPT.lower()
    assert "meet suffering with compassion" in lowered
    assert "dedicate" in lowered
    assert "merit" in lowered


# ---------------------------------------------------------------------------
# PHASE_GUIDANCE
# ---------------------------------------------------------------------------


def test_phase_guidance_has_entries_for_all_six_phases():
    """PHASE_GUIDANCE covers all six phases (five active phases + COMPLETED)."""
    expected_keys = {
        DialoguePhase.ARRIVAL,
        DialoguePhase.SEEING,
        DialoguePhase.MEETING,
        DialoguePhase.RELEASE,
        DialoguePhase.DEDICATION,
        DialoguePhase.COMPLETED,
    }
    assert set(PHASE_GUIDANCE.keys()) == expected_keys


def test_phase_guidance_includes_completed_terminal_block():
    """COMPLETED has a dedicated 'session is sealed' block in PHASE_GUIDANCE."""
    block = PHASE_GUIDANCE[DialoguePhase.COMPLETED]
    assert "COMPLETE" in block.upper() or "sealed" in block.lower()


@pytest.mark.parametrize("phase", list(DialoguePhase))
def test_phase_guidance_entries_are_non_empty(phase):
    """Each phase guidance block is a non-trivial string (>= 40 chars)."""
    block = PHASE_GUIDANCE[phase]
    assert isinstance(block, str)
    assert len(block) > 40, f"phase {phase} guidance is too short"


def test_phase_guidance_each_active_entry_names_its_role():
    """Each ACTIVE-phase block tells the LLM its role; COMPLETED is the seal."""
    active_phases = [
        DialoguePhase.ARRIVAL,
        DialoguePhase.SEEING,
        DialoguePhase.MEETING,
        DialoguePhase.RELEASE,
        DialoguePhase.DEDICATION,
    ]
    for phase in active_phases:
        block = PHASE_GUIDANCE[phase]
        assert "YOUR ROLE" in block, f"{phase} missing YOUR ROLE marker"


# ---------------------------------------------------------------------------
# build_system_prompt — per-phase assembly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phase",
    [
        DialoguePhase.ARRIVAL,
        DialoguePhase.SEEING,
        DialoguePhase.MEETING,
        DialoguePhase.RELEASE,
        DialoguePhase.DEDICATION,
    ],
)
def test_build_system_prompt_includes_phase_specific_guidance(phase):
    """For each active phase, the prompt carries that phase's guidance block."""
    prompt = build_system_prompt(phase=phase)
    # The phase guidance block is appended verbatim, so a sentinel from it
    # must show up.
    sentinel = PHASE_GUIDANCE[phase][:30]
    assert sentinel in prompt


def test_build_system_prompt_for_completed_phase_uses_completed_block():
    """COMPLETED IS in PHASE_GUIDANCE; build_system_prompt surfaces the sealed-container block."""
    prompt = build_system_prompt(phase=DialoguePhase.COMPLETED)
    # The COMPLETED guidance block says "session is COMPLETE" / "sealed".
    assert "COMPLETE" in prompt.upper()
    # And the base container prompt is still present.
    assert "CORE PRINCIPLES" in prompt


def test_build_system_prompt_contains_base_for_all_phases():
    """Every assembled prompt (active phases + COMPLETED) starts from the base."""
    base_marker = "CORE PRINCIPLES"
    for phase in DialoguePhase:
        prompt = build_system_prompt(phase=phase)
        assert base_marker in prompt, f"{phase} prompt lost the base marker"


def test_build_system_prompt_without_context_has_no_accumulated_section():
    """No insights/astrology/somatic -> no 'Accumulated Context' section."""
    prompt = build_system_prompt(phase=DialoguePhase.ARRIVAL)
    assert "Accumulated Context" not in prompt


# ---------------------------------------------------------------------------
# build_system_prompt — context injection
# ---------------------------------------------------------------------------


def test_build_system_prompt_includes_insights_section():
    """When insights are provided, the prompt surfaces them under 'Accumulated Context'."""
    insights = {
        "emotions": ["grief", "fear"],
        "body_locations": ["chest"],
        "themes": ["cosmic_timing"],
    }
    prompt = build_system_prompt(
        phase=DialoguePhase.MEETING,
        insights=insights,
    )
    assert "Accumulated Context" in prompt
    # Each insight key is rendered with underscores -> spaces + title-cased.
    assert "Emotions" in prompt
    assert "Body Locations" in prompt
    assert "Themes" in prompt


def test_build_system_prompt_includes_astrology_context():
    """When astrology_context is provided, the prompt surfaces it."""
    astrology = {
        "chart_id": 7,
        "natal": {"sun": "Gemini", "moon": "Pisces"},
        "transits": [{"planet": "Saturn", "aspect": "square"}],
    }
    prompt = build_system_prompt(
        phase=DialoguePhase.SEEING,
        astrology_context=astrology,
    )
    assert "Astrology / chart context" in prompt
    assert "Saturn" in prompt
    assert "Gemini" in prompt


def test_build_system_prompt_includes_somatic_findings():
    """When somatic_findings is provided, the prompt surfaces them."""
    somatic = {
        "primary_location": "chest",
        "quality": "tightness",
        "intensity": 7,
    }
    prompt = build_system_prompt(
        phase=DialoguePhase.MEETING,
        somatic_findings=somatic,
    )
    assert "Somatic findings" in prompt
    assert "chest" in prompt
    assert "tightness" in prompt


def test_build_system_prompt_includes_all_three_context_sections():
    """All three context subsections appear when all three are provided."""
    prompt = build_system_prompt(
        phase=DialoguePhase.MEETING,
        insights={"emotions": ["grief"]},
        astrology_context={"chart_id": 1, "natal": {"sun": "Aries"}},
        somatic_findings={"primary": "throat constriction"},
    )
    assert "Accumulated Context" in prompt
    assert "Astrology / chart context" in prompt
    assert "Somatic findings" in prompt


def test_build_system_prompt_empty_dict_context_is_omitted():
    """Empty dict context sections are omitted (truthiness check)."""
    prompt = build_system_prompt(
        phase=DialoguePhase.ARRIVAL,
        insights={},
        astrology_context={},
        somatic_findings={},
    )
    assert "Accumulated Context" not in prompt
    assert "Astrology / chart context" not in prompt
    assert "Somatic findings" not in prompt


def test_build_system_prompt_returns_string():
    """build_system_prompt always returns a non-empty string."""
    prompt = build_system_prompt(phase=DialoguePhase.ARRIVAL)
    assert isinstance(prompt, str)
    assert len(prompt) > len(HEALING_DIALOGUE_BASE_PROMPT)
