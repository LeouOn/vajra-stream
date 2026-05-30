import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.core.llm_agent.autonomous_agent import AutonomousAgent, AutonomousThoughtEvent
from infrastructure.event_bus import EnhancedEventBus
from modules.interfaces import DomainEvent


# Create a mock RNG spike event
class RNGReadingSpike(DomainEvent):
    def __init__(self, spike_value, timestamp=None, event_id=None):
        super().__init__(timestamp or datetime.now(), event_id)
        self.spike_value = spike_value

@pytest.mark.asyncio
async def test_autonomous_agent_event_reaction():
    """
    Test that the Autonomous Agent wakes up on a high priority event,
    reasons about it, and triggers the audio tool.
    """
    bus = EnhancedEventBus()
    _agent = AutonomousAgent(event_bus=bus)

    # We will mock the chat_interaction response instead of executing the full LLM
    # We want to simulate the LLM deciding to call 'play_chakra_healing_audio'

    with patch("backend.core.llm_agent.autonomous_agent.chat_interaction") as mock_chat:
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.response = "The energy is chaotic, I will play the heart chakra audio."

        # Simulate that the tool was called
        mock_response.tool_calls = [
            MagicMock(
                tool_name="play_chakra_healing_audio",
                arguments={"chakra_name": "heart", "duration": 30.0},
                status="success"
            )
        ]

        # Make the mock async
        async def async_chat(*args, **kwargs):
            return mock_response

        mock_chat.side_effect = async_chat

        # We need to capture the thought event broadcasted by the agent
        thoughts = []
        def thought_handler(event):
            thoughts.append(event)

        bus.subscribe(AutonomousThoughtEvent, thought_handler)

        # Fire the event
        spike_event = RNGReadingSpike(spike_value=0.9)
        bus.publish(spike_event)

        # Since AutonomousAgent handles it asynchronously via event bus,
        # and the EnhancedEventBus in this project might fire synchronously or we might need to yield:
        await asyncio.sleep(0.1)

        # The chat interaction should have been called
        assert mock_chat.called

        # The agent should have broadcasted a thought
        assert len(thoughts) > 0
        thought = thoughts[0]
        assert thought.action_taken is True
        assert "heart chakra" in thought.thought

