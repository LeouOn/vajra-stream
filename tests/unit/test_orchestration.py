from unittest.mock import MagicMock

import pytest

from core.ritual_sequencer import RitualPhase, RitualSequencer, RitualState
from infrastructure.event_bus import EnhancedEventBus
from modules.interfaces import BlessingGenerated


@pytest.mark.asyncio
async def test_ritual_sequencer_orchestration():
    """
    Test that the RitualSequencer can successfully orchestrate a full
    ritual lifecycle (Preparation -> Invocation -> Broadcast -> Dedication)
    and that the RitualState aggregates all data correctly.
    """
    event_bus = EnhancedEventBus()

    # Mock OutlookGenerator
    mock_generator = MagicMock()
    mock_generator.generate_single.return_value = {
        "narrative": "A test epic blessing narrative.",
        "astrology": {"planet": "Mars"},
        "divination": {"hexagram": 1},
    }

    # Setup the sequencer
    sequencer = RitualSequencer(outlook_generator=mock_generator, event_bus=event_bus)

    # Listen for the broadcast event
    emitted_events = []

    def on_blessing(event: BlessingGenerated):
        emitted_events.append(event)

    event_bus.subscribe(BlessingGenerated, on_blessing)

    # Create the initial context
    initial_context = RitualState(intention="Test Orchestration", genre="victory", tradition="universal")

    # Execute the ritual state machine
    final_state = await sequencer.execute_ritual(initial_context)

    # Verify State Machine completed
    assert final_state.phase == RitualPhase.COMPLETED
    assert sequencer.is_complete is True

    # Verify Invocation Phase data was captured
    assert final_state.invocation_narrative == "A test epic blessing narrative."
    assert final_state.astrology_results == {"planet": "Mars"}
    assert final_state.divination_results == {"hexagram": 1}

    # Verify Broadcast Phase correctly emitted the event to the Event Bus
    assert len(emitted_events) == 1
    assert emitted_events[0].target_name == "Test Orchestration"
    assert emitted_events[0].blessing_text == "A test epic blessing narrative."
