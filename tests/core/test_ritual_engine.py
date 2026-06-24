"""
Tests for ``core.ritual_engine`` — autonomous 24/7 ritual orchestrator.

Covers the public API:
- Enums: :class:`RitualPhase` and :class:`EngineState`.
- Dataclass: :class:`RitualRecord` (incl. ``to_dict`` contract).
- :class:`RitualExecutionEngine` — text-only pure helpers
  (``_get_opening_invocation`` / ``_get_dedication``) that don't require
  any TTS / WS / DB / container wiring.
- :class:`RitualScheduler` — ``status`` shape, ``update_config``,
  ``get_history`` / ``get_merit_stats`` with the DB replaced by a stub.
- :func:`get_ritual_engine` — module-level singleton factory.

Network/TTS/WS/container/auspicious-timing calls are out of scope for
this file (they have their own test coverage in ``tests/unit/``).
"""
from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from core.ritual_engine import (
    EngineState,
    PracticeSelector,
    RitualExecutionEngine,
    RitualPhase,
    RitualRecord,
    RitualScheduler,
    get_ritual_engine,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@dataclass
class _MockPractice:
    """Duck-typed Practice — enough surface for ``RitualRecord`` ctor."""

    id: str = "test_practice"
    name: str = "Test Practice"
    genre: str = "healing"
    merit_multiplier: int = 1
    preferred_planetary_hours: list = field(default_factory=list)


def _make_record(**overrides) -> RitualRecord:
    """Build a fully-populated RitualRecord for to_dict tests."""
    defaults = dict(
        id=7,
        practice_name="Heart Blessing",
        practice_id="heart_blessing",
        genre="healing",
        planetary_hour="Sun",
        timing_quality="excellent",
        merit_multiplier=10,
        narrative_length=420,
        tts_generated=True,
        started_at="2024-06-15T10:00:00",
        completed_at="2024-06-15T10:08:00",
        narrative_preview="May all beings find peace...",
    )
    defaults.update(overrides)
    return RitualRecord(**defaults)


class _StubExecutor:
    """Replaces ``RitualExecutionEngine`` with a no-op init that points at
    a temp DB.

    The real ``_init_db`` writes to ``~/.vajra-stream/ritual_history.db``,
    which is undesirable from a test. The stub exposes a ``_init_db``
    method (the attribute actually called by the scheduler) that is a
    no-op — the schema is initialised once in the constructor instead.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        conn = sqlite3.connect(self._db_path)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ritual_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_name TEXT, practice_id TEXT, genre TEXT,
                planetary_hour TEXT, timing_quality TEXT,
                merit_multiplier INTEGER DEFAULT 1,
                narrative_length INTEGER DEFAULT 0,
                tts_generated INTEGER DEFAULT 0,
                narrative_preview TEXT,
                started_at TEXT, completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS merit_tracker (
                date TEXT PRIMARY KEY,
                total_merit INTEGER DEFAULT 0,
                rituals_count INTEGER DEFAULT 0,
                practices TEXT DEFAULT '[]'
            );
            """
        )
        conn.commit()
        conn.close()

    def _init_db(self):
        # Schema already initialised in __init__; this is a no-op.
        return None


@pytest.fixture
def fresh_singleton() -> Any:
    """Force ``get_ritual_engine`` to return a brand-new RitualScheduler.

    The real factory caches a module-level singleton; we save/restore it
    around each test so tests don't pollute each other.
    """
    import core.ritual_engine as re_mod

    original = re_mod._ritual_engine
    re_mod._ritual_engine = None
    try:
        yield re_mod
    finally:
        re_mod._ritual_engine = original


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.ritual_engine as mod

    expected = (
        "RitualPhase",
        "EngineState",
        "RitualRecord",
        "PracticeScore",
        "PracticeSelector",
        "RitualExecutionEngine",
        "RitualScheduler",
        "get_ritual_engine",
    )
    for name in expected:
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Enums + RitualRecord.to_dict contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ritual_phase_enum_has_six_doc_phases():
    """RitualPhase covers the four execution phases plus IDLE and COMPLETED."""
    assert len(RitualPhase) == 6
    values = {p.value for p in RitualPhase}
    assert values == {
        "idle",
        "preparation",
        "invocation",
        "broadcast",
        "dedication",
        "completed",
    }
    # Phases are str-subclass enums (safe to use as JSON values)
    assert RitualPhase.PREPARATION == "preparation"


@pytest.mark.unit
def test_ritual_record_to_dict_serialises_every_field():
    """``RitualRecord.to_dict`` produces a plain dict with the same keys as
    the dataclass fields, plus the values are JSON-friendly."""
    record = _make_record()
    d = record.to_dict()

    # Same set of keys as the dataclass (via __dataclass_fields__)
    import dataclasses

    expected_keys = {f.name for f in dataclasses.fields(RitualRecord)}
    assert set(d.keys()) == expected_keys, (
        f"to_dict keys drift from dataclass fields.\n"
        f"  Missing: {expected_keys - set(d.keys())}\n"
        f"  Extra:   {set(d.keys()) - expected_keys}"
    )

    # Spot-check values
    assert d["id"] == 7
    assert d["practice_name"] == "Heart Blessing"
    assert d["genre"] == "healing"
    assert d["merit_multiplier"] == 10
    assert d["narrative_length"] == 420
    assert d["tts_generated"] is True


# ---------------------------------------------------------------------------
# 3. RitualExecutionEngine — pure text helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_executor_opening_invocation_mentions_practice_and_hour():
    """``_get_opening_invocation`` includes the practice name, the
    planetary hour, and the merit multiplier in the TTS-ready string."""
    executor = RitualExecutionEngine()
    record = _make_record(
        practice_name="Avalokiteshvara Recitation",
        planetary_hour="Venus",
        merit_multiplier=108,
    )
    text = executor._get_opening_invocation(record)

    assert isinstance(text, str)
    assert "Avalokiteshvara Recitation" in text
    assert "Venus" in text
    assert "108" in text
    # Conventional blessing closer
    assert "Om Ah Hum" in text or "May all beings" in text


@pytest.mark.unit
def test_executor_dedication_mentions_practice_and_includes_bodhicitta_lines():
    """``_get_dedication`` references the practice name and includes the
    four-line bodhicitta dedication used by the scheduler."""
    executor = RitualExecutionEngine()
    record = _make_record(practice_name="Tara Practice")
    text = executor._get_dedication(record)

    assert isinstance(text, str)
    assert "Tara Practice" in text
    # Both happiness and suffering causes are mentioned
    assert "happiness" in text
    assert "suffering" in text
    # Conventional closure
    assert "Sarva Mangalam" in text


# ---------------------------------------------------------------------------
# 4. RitualScheduler — status / update_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scheduler_status_shape_reflects_initial_state(fresh_singleton):
    """A freshly-created scheduler reports STOPPED, zero counters, and the
    default config block — and never throws even with no rituals run."""
    scheduler = get_ritual_engine()
    status = scheduler.status

    assert isinstance(status, dict)
    assert status["state"] == EngineState.STOPPED.value
    assert status["current_ritual"] is None
    assert status["rituals_today"] == 0
    assert status["total_merit_today"] == 0
    assert status["rituals_this_hour"] == 0
    # Config block carries the documented defaults
    assert "config" in status
    assert "enabled" in status["config"]
    assert "max_per_hour" in status["config"]
    # History + schedule are present (possibly empty)
    assert "history" in status
    assert isinstance(status["history"], list)
    assert "schedule" in status
    assert isinstance(status["schedule"], list)


@pytest.mark.unit
def test_scheduler_update_config_merges_without_clobbering(fresh_singleton):
    """``update_config`` merges new keys into the existing config dict
    and leaves untouched keys intact."""
    scheduler = get_ritual_engine()
    original_min = scheduler._config["min_timing_quality"]

    scheduler.update_config(tts_enabled=False, max_per_hour=7, custom_flag="x")

    # New keys applied
    assert scheduler._config["tts_enabled"] is False
    assert scheduler._config["max_per_hour"] == 7
    assert scheduler._config["custom_flag"] == "x"
    # Unspecified key preserved
    assert scheduler._config["min_timing_quality"] == original_min


# ---------------------------------------------------------------------------
# 5. RitualScheduler — DB-backed lookups with a stubbed executor
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scheduler_get_history_returns_empty_when_db_empty(fresh_singleton, tmp_path):
    """``get_history`` returns an empty list (not raises) when the
    underlying ritual_history table has no rows."""
    scheduler = get_ritual_engine()
    db_path = str(tmp_path / "ritual_history.db")
    _StubExecutor(db_path)  # initialise schema in temp file

    # Swap in our stub executor pointing at the temp DB
    scheduler.executor = _StubExecutor(db_path)

    history = scheduler.get_history(limit=10)
    assert history == []


@pytest.mark.unit
def test_scheduler_get_merit_stats_returns_zeros_when_db_empty(fresh_singleton, tmp_path):
    """``get_merit_stats`` returns the zero-valued dict when there is no
    merit_tracker row for today or any other date."""
    scheduler = get_ritual_engine()
    db_path = str(tmp_path / "ritual_history.db")
    _StubExecutor(db_path)
    scheduler.executor = _StubExecutor(db_path)

    stats = scheduler.get_merit_stats()
    assert stats == {
        "today_merit": 0,
        "today_rituals": 0,
        "total_merit": 0,
        "total_rituals": 0,
    }


@pytest.mark.unit
def test_scheduler_get_history_returns_inserted_row(fresh_singleton, tmp_path):
    """After a record is written to the DB, ``get_history`` reads it back
    in reverse-chronological order with the columns populated."""
    scheduler = get_ritual_engine()
    db_path = str(tmp_path / "ritual_history.db")
    _StubExecutor(db_path)
    scheduler.executor = _StubExecutor(db_path)

    # Insert a row directly so we don't have to run a full ritual
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO ritual_history
           (practice_name, practice_id, genre, planetary_hour, timing_quality,
            merit_multiplier, narrative_length, tts_generated,
            narrative_preview, started_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Heart Blessing",
            "heart_blessing",
            "healing",
            "Sun",
            "excellent",
            10,
            420,
            1,
            "May all beings find peace",
            "2024-06-15T10:00:00",
            "2024-06-15T10:08:00",
        ),
    )
    conn.commit()
    conn.close()

    history = scheduler.get_history(limit=10)
    assert len(history) == 1
    row = history[0]
    assert row["practice_name"] == "Heart Blessing"
    assert row["genre"] == "healing"
    assert row["merit_multiplier"] == 10
    assert row["narrative_length"] == 420
    assert row["narrative_preview"] == "May all beings find peace"


# ---------------------------------------------------------------------------
# 6. Error handling — get_history / get_merit_stats swallow DB errors
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scheduler_get_history_returns_empty_on_db_error(fresh_singleton, monkeypatch):
    """If the DB lookup raises (e.g. file missing, permission denied),
    ``get_history`` must swallow the exception and return ``[]`` so that
    API endpoints don't 500 just because the DB hasn't been initialised."""
    scheduler = get_ritual_engine()

    def _raise(*args, **kwargs):
        raise sqlite3.OperationalError("simulated db failure")

    # Patch the real method on the underlying executor so _init_db blows up
    monkeypatch.setattr(scheduler.executor, "_init_db", _raise)

    assert scheduler.get_history() == []


@pytest.mark.unit
def test_scheduler_get_merit_stats_returns_zeros_on_db_error(fresh_singleton, monkeypatch):
    """``get_merit_stats`` returns the zero-valued dict on DB error."""
    scheduler = get_ritual_engine()

    def _raise(*args, **kwargs):
        raise sqlite3.OperationalError("simulated db failure")

    monkeypatch.setattr(scheduler.executor, "_init_db", _raise)

    assert scheduler.get_merit_stats() == {
        "today_merit": 0,
        "today_rituals": 0,
        "total_merit": 0,
        "total_rituals": 0,
    }


# ---------------------------------------------------------------------------
# 7. get_ritual_engine — singleton contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_ritual_engine_returns_same_instance_across_calls(fresh_singleton):
    """``get_ritual_engine`` is a singleton: two calls return the same
    object. The fixture resets the cache so the assertion is honest."""
    e1 = get_ritual_engine()
    e2 = get_ritual_engine()
    assert e1 is e2
    assert isinstance(e1, RitualScheduler)
