"""Smoke + behaviour tests for ``core.ritual_sequencer``.

Covers :class:`core.ritual_sequencer.RitualSequencer`, its phase
:class:`Enum`, the :class:`RitualState` dataclass, and the public
state-machine lifecycle: ``start`` → ``tick`` → ``advance`` → ``abort``.

Heavy dependencies (astrology, auspicious timing, event bus, outlook
generator) are mocked or guarded via ``try/except`` inside the module
under test; tests do not require any of them.
"""
from __future__ import annotations

import pytest

from core.ritual_sequencer import (
    RitualContext,  # backward-compat alias
    RitualPhase,
    RitualSequencer,
    RitualState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sequencer():
    """A bare RitualSequencer with no operator / generator / event bus."""
    return RitualSequencer()


@pytest.fixture
def sequencer_with_callbacks():
    """A sequencer with two simple tracking callbacks wired up."""
    seq = RitualSequencer()
    events: list[tuple[str, str]] = []

    def _record(event, state, operator):  # noqa: ANN001
        events.append((event, state.phase.value))

    for phase in (RitualPhase.PREPARATION, RitualPhase.INVOCATION):
        seq.on_phase(phase, _record)
    return seq, events


# ---------------------------------------------------------------------------
# 1. Import smoke + public API
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_phase_enum():
    """The module imports and exposes the phase enum, state, and sequencer."""
    import core.ritual_sequencer as mod

    # Enum members
    expected = {"IDLE", "PREPARATION", "INVOCATION", "BROADCAST",
                "DEDICATION", "COMPLETED", "ABORTED"}
    actual = {p.name for p in RitualPhase}
    assert actual == expected

    # Backward-compat alias
    assert RitualContext is RitualState

    # RitualState must have to_dict
    state = RitualState()
    d = state.to_dict()
    assert d["phase"] == "idle"
    assert d["blessings_count"] == 0
    assert d["rng_readings_count"] == 0
    assert "phase_durations" in d


# ---------------------------------------------------------------------------
# 2. start() creates a ritual_id and advances into PREPARATION
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_start_initialises_state_and_enters_preparation(sequencer):
    """``start`` assigns a ritual_id, intention, tradition, and enters PREPARATION."""
    state = sequencer.start(intention="Healing for the world", tradition="buddhist")

    assert state.ritual_id.startswith("ritual_")
    assert state.intention == "Healing for the world"
    assert state.tradition == "buddhist"
    assert state.phase == RitualPhase.PREPARATION
    assert state.created_at != ""
    assert sequencer.is_running is True
    assert sequencer.is_complete is False


# ---------------------------------------------------------------------------
# 3. tick() fires on_tick callbacks for the current phase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tick_fires_registered_callbacks(sequencer_with_callbacks):
    """``tick`` runs every callback registered for the current phase."""
    seq, events = sequencer_with_callbacks
    seq.start(intention="test", tradition="universal")

    # We're in PREPARATION → tick should record ("tick", "preparation")
    seq.tick()
    assert ("tick", "preparation") in events

    # Advance to INVOCATION → tick there should also be recorded
    seq.advance()
    assert seq.state.phase == RitualPhase.INVOCATION
    seq.tick()
    assert ("tick", "invocation") in events


# ---------------------------------------------------------------------------
# 4. advance() walks the full lifecycle to COMPLETED
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_advance_walks_full_phase_order(sequencer):
    """Four advances from PREPARATION → COMPLETED; is_complete becomes True."""
    sequencer.start(intention="", tradition="universal")

    # start() already moved us to PREPARATION; we need 3 more advances
    # (PREPARATION → INVOCATION → BROADCAST → DEDICATION → COMPLETED).
    assert sequencer.state.phase == RitualPhase.PREPARATION

    seen_phases = [sequencer.state.phase]
    while not sequencer.is_complete:
        sequencer.advance()
        if not sequencer.is_complete:
            seen_phases.append(sequencer.state.phase)

    assert sequencer.state.phase == RitualPhase.COMPLETED
    # Each of the 4 working phases must have been entered exactly once
    assert RitualPhase.PREPARATION in seen_phases
    assert RitualPhase.INVOCATION in seen_phases
    assert RitualPhase.BROADCAST in seen_phases
    assert RitualPhase.DEDICATION in seen_phases
    # Phase durations recorded for all four working phases
    for p in ("preparation", "invocation", "broadcast", "dedication"):
        assert p in sequencer.state.phase_durations


# ---------------------------------------------------------------------------
# 5. abort() short-circuits the lifecycle and records the reason
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_abort_sets_phase_and_metadata(sequencer):
    """``abort`` halts the sequencer and stores ``abort_reason`` in metadata."""
    sequencer.start(intention="test", tradition="universal")
    sequencer.advance()  # INVOCATION
    sequencer.abort(reason="user cancelled")

    assert sequencer.state.phase == RitualPhase.ABORTED
    assert sequencer.is_complete is True
    assert sequencer.is_running is False
    assert sequencer.state.metadata.get("abort_reason") == "user cancelled"


# ---------------------------------------------------------------------------
# 6. tick()/advance() on a finished ritual are no-ops
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tick_and_advance_noop_after_completion(sequencer):
    """After ``advance`` reaches COMPLETED, further ticks/advances are ignored."""
    sequencer.start(intention="", tradition="universal")
    while not sequencer.is_complete:
        sequencer.advance()
    assert sequencer.state.phase == RitualPhase.COMPLETED

    phase_before = sequencer.state.phase
    sequencer.tick()
    sequencer.advance()
    assert sequencer.state.phase == phase_before


# ---------------------------------------------------------------------------
# 7. inject_operator + on_phase registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_inject_operator_and_on_phase_registration(sequencer):
    """``inject_operator`` stores the operator; ``on_phase`` appends callbacks."""
    class _Op:
        pass

    op = _Op()
    sequencer.inject_operator(op)
    assert sequencer._operator is op

    calls: list[str] = []
    sequencer.on_phase(RitualPhase.PREPARATION, lambda e, s, o: calls.append(e))
    sequencer.start(intention="", tradition="universal")
    # The "enter" callback must have fired for PREPARATION during start()
    assert "enter" in calls
