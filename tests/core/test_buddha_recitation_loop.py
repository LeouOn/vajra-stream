"""Tests for ``core.buddha_recitation_loop`` — public API of the loop.

Covers the public surface:
- :class:`RecitationState` — dataclass defaults.
- :class:`BuddhaRecitationLoop` — constructor, callback registration,
  status shape, buddha-list loading, and the process-wide singleton.

TTS-specific behaviour is intentionally NOT covered here — it lives in
``tests/core/test_buddha_recitation_loop_tts.py``. These tests focus on
general state, lifecycle hooks, and the data the loop streams to subscribers.

The loop is constructed with ``tts_reciter=False`` to skip TTS provider
initialisation in tests; ``sounddevice`` / ``soundfile`` / WebSocket
infrastructure are not invoked in any of the assertions below.
"""
from __future__ import annotations

import pytest

from core.buddha_recitation_loop import (
    BuddhaRecitationLoop,
    RecitationState,
    get_recitation_loop,
)


# ---------------------------------------------------------------------------
# 1. Import smoke + state dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports ``RecitationState``, ``BuddhaRecitationLoop`` and the singleton getter."""
    import core.buddha_recitation_loop as mod

    for name in ("RecitationState", "BuddhaRecitationLoop", "get_recitation_loop"):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


@pytest.mark.unit
def test_recitation_state_default_values():
    """``RecitationState`` defaults: not running, role 'buddhist_chant', no project."""
    state = RecitationState()

    assert state.running is False
    assert state.intention == ""
    assert state.current_index == 0
    assert state.current_cycle == 0
    assert state.total_recited == 0
    assert state.mala_count == 0
    assert state.dedications == 0
    assert state.current_buddha == {}
    assert state.started_at == ""
    assert state.last_recited_at == ""
    assert state.backend == ""
    assert state.speaker == ""
    assert state.role == "buddhist_chant"
    assert state.project_id is None
    assert state.stats == {}


# ---------------------------------------------------------------------------
# 2. Constructor + callback registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_with_tts_disabled_initialises_state_and_callback_lists():
    """Passing ``tts_reciter=False`` skips TTS and the loop still constructs cleanly."""
    loop = BuddhaRecitationLoop(tts_reciter=False)

    # State is a fresh, stopped RecitationState
    assert isinstance(loop.state, RecitationState)
    assert loop.state.running is False

    # Callback lists are empty but usable
    assert loop._on_name == []
    assert loop._on_dedication == []
    assert loop._on_cycle_complete == []

    # TTS sentinels: ``False`` means "explicitly disabled"
    assert loop._tts is False
    # No background task yet
    assert loop._task is None


@pytest.mark.unit
def test_callback_registration_appends_to_internal_lists():
    """``on_name_recited`` / ``on_dedication`` / ``on_cycle_complete`` register callables."""
    loop = BuddhaRecitationLoop(tts_reciter=False)

    name_cb = lambda buddha, state: None  # noqa: E731
    ded_cb = lambda n, state: None  # noqa: E731
    cyc_cb = lambda state: None  # noqa: E731

    loop.on_name_recited(name_cb)
    loop.on_dedication(ded_cb)
    loop.on_cycle_complete(cyc_cb)

    assert loop._on_name == [name_cb]
    assert loop._on_dedication == [ded_cb]
    assert loop._on_cycle_complete == [cyc_cb]

    # Multiple registrations append (no de-dup)
    loop.on_name_recited(name_cb)
    assert loop._on_name == [name_cb, name_cb]


# ---------------------------------------------------------------------------
# 3. Buddha list loading (the data the loop actually recites)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_buddhas_loads_past_and_confession_categories():
    """``_load_buddhas`` populates both past and confession categories from the 88-Buddha data."""
    loop = BuddhaRecitationLoop(tts_reciter=False)
    loop._load_buddhas()

    # Total of 88 entries, 53 past + 35 confession
    assert len(loop._buddhas) == 88
    assert sum(1 for b in loop._buddhas if b["category"] == "past") == 53
    assert sum(1 for b in loop._buddhas if b["category"] == "confession") == 35

    # Each entry has the projected fields the loop relies on
    for entry in loop._buddhas:
        assert set(entry.keys()) == {
            "name_chinese",
            "name_pinyin",
            "name_sanskrit",
            "category",
        }
        assert entry["category"] in {"past", "confession"}
        # The recitation loop speaks the Chinese name; it must be non-empty
        assert entry["name_chinese"]


# ---------------------------------------------------------------------------
# 4. Status shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_status_returns_documented_shape_when_idle():
    """``get_status`` returns the documented dict even with no buddhas loaded."""
    loop = BuddhaRecitationLoop(tts_reciter=False)

    status = loop.get_status()

    assert status == {
        "running": False,
        "intention": "",
        "current_index": 0,
        "current_cycle": 0,
        "total_recited": 0,
        "mala_count": 0,
        "dedications": 0,
        "total_buddhas": 0,
        "current_buddha": {},
        "progress_pct": 0,
        "started_at": "",
        "last_recited_at": "",
        "backend": "",
        "speaker": "",
        "role": "buddhist_chant",
        "project_id": None,
    }


@pytest.mark.unit
def test_get_status_progress_pct_uses_total_buddhas_in_denominator():
    """When buddhas are loaded, ``progress_pct`` divides by their count."""
    loop = BuddhaRecitationLoop(tts_reciter=False)
    loop._load_buddhas()

    # Simulate partial progress
    loop.state.current_index = 44  # half-way

    status = loop.get_status()

    assert status["total_buddhas"] == 88
    assert status["progress_pct"] == 50.0


# ---------------------------------------------------------------------------
# 5. Process-wide singleton
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_recitation_loop_returns_singleton_instance():
    """``get_recitation_loop`` returns the same instance across calls."""
    # Reset the module-level singleton so the test is deterministic
    import core.buddha_recitation_loop as mod

    mod._recitation_loop = None

    first = get_recitation_loop()
    second = get_recitation_loop()

    assert first is second
    assert isinstance(first, BuddhaRecitationLoop)
