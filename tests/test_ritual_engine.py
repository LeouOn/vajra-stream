"""Tests for core/ritual_engine.py — the testable surface.

Covers:
- RitualPhase / EngineState enum values
- PracticeScore / RitualRecord dataclass construction
- PracticeSelector._score_practice (pure scoring function with 4
  weighted components: timing 40%, merit 30%, recency 20%, diversity 10%)
- PracticeSelector.select (selection + recency tracking)
- get_ritual_engine() factory
"""
import pytest
from dataclasses import dataclass, field
from typing import Any

from core.ritual_engine import (
    RitualPhase, EngineState, PracticeScore, RitualRecord,
    PracticeSelector, get_ritual_engine,
)


@dataclass
class MockPractice:
    id: str = "test_practice"
    name: str = "Test Practice"
    genre: str = "healing"
    merit_multiplier: int = 1
    preferred_planetary_hours: list = field(default_factory=list)


def test_ritual_phase_values():
    assert RitualPhase.IDLE.value == "idle"
    assert RitualPhase.PREPARATION.value == "preparation"
    assert RitualPhase.INVOCATION.value == "invocation"
    assert RitualPhase.BROADCAST.value == "broadcast"
    assert RitualPhase.DEDICATION.value == "dedication"
    assert RitualPhase.COMPLETED.value == "completed"
    assert len(RitualPhase) == 6


def test_ritual_phase_is_str_based():
    assert isinstance(RitualPhase.IDLE, str)
    assert RitualPhase.IDLE == "idle"
    assert RitualPhase.BROADCAST.value == "broadcast"


def test_engine_state_values():
    assert EngineState.STOPPED.value == "stopped"
    assert EngineState.RUNNING.value == "running"
    assert EngineState.PAUSED.value == "paused"
    assert EngineState.EXECUTING.value == "executing"
    assert len(EngineState) == 4


def test_engine_state_is_str_based():
    assert isinstance(EngineState.STOPPED, str)
    assert EngineState.STOPPED == "stopped"


def test_practice_score_construction():
    p = MockPractice()
    s = PracticeScore(practice=p, score=0.85, timing_quality="excellent", reason="test")
    assert s.practice is p
    assert s.score == 0.85
    assert s.timing_quality == "excellent"
    assert s.reason == "test"


def test_ritual_record_construction():
    from datetime import datetime
    p = MockPractice()
    now = datetime.now()
    r = RitualRecord(
        id=1, practice_name="Test", practice_id="test_id", genre="healing",
        planetary_hour="Sun", timing_quality="good", merit_multiplier=10,
        narrative_length=500, tts_generated=True,
        started_at=now, completed_at=now, narrative_preview="Once upon a time...",
    )
    assert r.id == 1
    assert r.genre == "healing"
    assert r.merit_multiplier == 10
    assert r.narrative_preview == "Once upon a time..."


def test_score_practice_unknown_genre_gets_default():
    selector = PracticeSelector()
    p = MockPractice(genre="unknown_genre", merit_multiplier=1)
    score, quality, reason = selector._score_practice(p, "Sun", {}, max_recent=3)
    assert quality == "neutral"
    assert "timing: unknown" in reason
    assert 0.0 < score < 1.0


def test_score_practice_excellent_timing():
    selector = PracticeSelector()
    p = MockPractice(genre="healing", merit_multiplier=1)
    windows = {"healing": {"quality": "excellent"}}
    score, quality, reason = selector._score_practice(p, "Sun", windows, max_recent=3)
    assert quality == "excellent"
    assert "timing: excellent" in reason
    assert score >= 0.4


def test_score_practice_preferred_hour_bonus():
    selector = PracticeSelector()
    p_no_pref = MockPractice(genre="healing", merit_multiplier=1, preferred_planetary_hours=[])
    p_with_pref = MockPractice(genre="healing", merit_multiplier=1, preferred_planetary_hours=["Sun"])
    windows = {"healing": {"quality": "good"}}
    s_no, _, _ = selector._score_practice(p_no_pref, "Sun", windows, max_recent=3)
    s_yes, _, _ = selector._score_practice(p_with_pref, "Sun", windows, max_recent=3)
    assert s_yes > s_no, f"preferred hour should boost score: {s_no} vs {s_yes}"


def test_score_practice_high_merit_bonus():
    selector = PracticeSelector()
    p_low = MockPractice(merit_multiplier=1)
    p_high = MockPractice(merit_multiplier=108)
    windows = {"healing": {"quality": "excellent"}}
    s_low, _, _ = selector._score_practice(p_low, "Sun", windows, max_recent=3)
    s_high, _, _ = selector._score_practice(p_high, "Sun", windows, max_recent=3)
    assert s_high > s_low


def test_score_practice_merit_caps_at_108x():
    selector = PracticeSelector()
    p_huge = MockPractice(merit_multiplier=10000)
    windows = {"healing": {"quality": "excellent"}}
    s_huge, _, _ = selector._score_practice(p_huge, "Sun", windows, max_recent=3)
    assert s_huge <= 1.0


def test_select_empty_practices_returns_none():
    selector = PracticeSelector()
    assert selector.select([], "Sun", {"healing": {"quality": "good"}}) is None


def test_select_threshold_check_exists():
    selector = PracticeSelector()
    selector._score_practice = lambda *a, **kw: (0.05, "neutral", "mocked low")
    p = MockPractice()
    result = selector.select([p], "Sun", {"healing": {"quality": "good"}})
    assert result is None, "select should return None when best score is below the threshold"


def test_select_picks_highest_scored():
    selector = PracticeSelector()
    p_low = MockPractice(id="low", merit_multiplier=1)
    p_high = MockPractice(id="high", merit_multiplier=108)
    windows = {"healing": {"quality": "excellent"}}
    result = selector.select([p_low, p_high], "Sun", windows)
    assert result is not None
    assert result.practice.id == "high"


def test_select_tracks_recent_practices():
    selector = PracticeSelector()
    p1 = MockPractice(id="a")
    p2 = MockPractice(id="b")
    windows = {"healing": {"quality": "good"}}
    selector.select([p1, p2], "Sun", windows)
    assert "a" in selector._recent_practices or "b" in selector._recent_practices
    assert len(selector._recent_practices) <= 20


def test_select_penalizes_recently_used():
    selector = PracticeSelector()
    p = MockPractice(id="a", merit_multiplier=108)
    windows = {"healing": {"quality": "excellent"}}
    first = selector.select([p], "Sun", windows)
    assert first is not None
    second = selector.select([p], "Sun", windows)
    assert second is None or second.score < first.score, (
        "second select of same practice should be penalized"
    )


def test_select_recent_practices_capped_at_20():
    selector = PracticeSelector()
    windows = {"healing": {"quality": "good"}}
    for i in range(25):
        p = MockPractice(id=f"p{i}")
        selector.select([p], "Sun", windows)
    assert len(selector._recent_practices) <= 20


def test_get_ritual_engine_returns_scheduler():
    engine = get_ritual_engine()
    assert engine is not None


def test_get_ritual_engine_returns_singleton():
    e1 = get_ritual_engine()
    e2 = get_ritual_engine()
    assert e1 is e2
