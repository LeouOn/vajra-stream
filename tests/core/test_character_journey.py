"""
Tests for core/character_journey.py — autonomous 6-stage character progression.

The CharacterJourney class drives a character through 6 stages (Initiation →
Training → Working → Overcoming → Utopia → Multiverse) using the
RitualSequencer and an optional LLM operator. These tests cover the
public lifecycle (begin / advance / harvest / is_complete) using a fake
character and a real RitualSequencer with no external LLM/DB dependencies.
"""

from __future__ import annotations

from typing import Any

import pytest

from core.character_journey import (
    FALLBACK_BLESSINGS,
    FALLBACK_DEDICATIONS,
    STAGE_CONFIG,
    CharacterJourney,
    JourneyStage,
)

# ─── Fixtures ──────────────────────────────────────────────────────────────


class FakeCharacter:
    """Minimal character compatible with CharacterJourney (duck-typed)."""

    def __init__(self, name: str = "TestHero", frequency: float = 528.0) -> None:
        self.name = name
        self.frequency = frequency
        self.stats = {
            "vitality": 1,
            "resonance": 1,
            "focus": 1,
            "wisdom": 1,
            "courage": 1,
            "empathy": 1,
        }
        self.element = {"name": "Fire"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "frequency": self.frequency,
            "stats": self.stats,
            "element": self.element,
        }


@pytest.fixture
def character() -> FakeCharacter:
    """A fresh, in-memory character for the journey."""
    return FakeCharacter()


@pytest.fixture
def journey() -> CharacterJourney:
    """A fresh CharacterJourney with no LLM operator (uses fallbacks)."""
    return CharacterJourney()


# ─── Smoke ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_module_imports():
    """Smoke test: module exposes the JourneyStage enum, STAGE_CONFIG,
    FALLBACK_BLESSINGS, FALLBACK_DEDICATIONS, and CharacterJourney class."""
    assert JourneyStage.INITIATION.value == "initiation"
    assert JourneyStage.MULTIVERSE.value == "multiverse"
    # STAGE_CONFIG is a list of 6 stage dicts, one per JourneyStage value
    assert len(STAGE_CONFIG) == 6
    assert {entry["stage"] for entry in STAGE_CONFIG} == set(JourneyStage)
    # Fallback dict covers all 6 stages
    assert set(FALLBACK_BLESSINGS.keys()) == set(JourneyStage)
    assert len(FALLBACK_DEDICATIONS) > 0
    # Class
    assert callable(CharacterJourney)


# ─── Behavior: initial state ──────────────────────────────────────────────


@pytest.mark.unit
def test_journey_starts_incomplete_at_first_stage(journey: CharacterJourney):
    """A new journey is incomplete, and its current_stage is INITIATION."""
    assert journey.is_complete is False
    assert journey.current_stage == JourneyStage.INITIATION
    assert journey.stage_results == []


# ─── Behavior: begin ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_begin_resets_state_and_returns_first_stage(journey: CharacterJourney, character: FakeCharacter):
    """begin() stores the character, resets stage index, and returns a status dict."""
    result = journey.begin(character)

    assert result["status"] == "journey_begun"
    assert result["character"]["name"] == "TestHero"
    assert result["stages_total"] == 6
    assert result["first_stage"] == "The Awakening"
    assert journey.character is character
    assert journey.is_complete is False


# ─── Behavior: advance + is_complete ───────────────────────────────────────


@pytest.mark.unit
def test_advance_records_one_stage_with_blessings(journey: CharacterJourney, character: FakeCharacter):
    """advance() runs one stage (all 4 ritual phases) and appends a stage_result."""
    journey.begin(character)

    stage_result = journey.advance()

    # The result has the documented shape
    assert stage_result["stage"] == JourneyStage.INITIATION.value
    assert stage_result["name"] == "The Awakening"
    assert "blessing_theme" in stage_result
    assert "blessings_count" in stage_result
    # At least one blessing was produced from the FALLBACK_BLESSINGS
    # (preparation phase + dedication phase = 2 blessings per stage).
    assert stage_result["blessings_count"] >= 1
    assert isinstance(stage_result["blessings"], list)
    # stat_changes copies the configured growth dict
    assert stage_result["stat_changes"] == STAGE_CONFIG[0]["stat_growth"]

    # After one stage, we're 1/6 through; current_stage advances to TRAINING.
    assert journey.is_complete is False
    assert journey.current_stage == JourneyStage.TRAINING
    assert len(journey.stage_results) == 1


# ─── Behavior: run full journey + harvest ──────────────────────────────────


@pytest.mark.unit
@pytest.mark.slow
def test_run_full_journey_completes_all_six_stages(journey: CharacterJourney, character: FakeCharacter):
    """run_full_journey advances through all 6 stages and produces a complete harvest."""
    final = journey.run_full_journey(character)

    assert final["status"] == "complete"
    assert final["stages_completed"] == 6
    assert final["stages_total"] == 6
    assert len(final["stage_results"]) == 6
    # Every stage recorded at least one blessing
    assert final["total_blessings"] >= 6
    # Each stage result has a non-empty blessings list
    for stage in final["stage_results"]:
        assert stage["blessings_count"] >= 1

    assert journey.is_complete is True
    assert journey.current_stage is None  # past the end


# ─── Behavior: advance after completion ────────────────────────────────────


@pytest.mark.unit
def test_advance_after_completion_returns_complete_status(journey: CharacterJourney, character: FakeCharacter):
    """Calling advance() on a finished journey is a no-op that reports completion."""
    journey.run_full_journey(character)
    assert journey.is_complete is True

    extra = journey.advance()
    assert extra["status"] == "complete"
    assert "message" in extra
    # No new stage appended
    assert len(journey.stage_results) == 6
