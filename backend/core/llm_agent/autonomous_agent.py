import logging
import collections

from backend.app.api.v1.endpoints.llm import ChatMessage, ChatRequest, chat_interaction
from infrastructure.event_bus import EnhancedEventBus

# Import known events that we might want to react to
from modules.interfaces import DomainEvent, RNGReadingEvent

logger = logging.getLogger(__name__)

class AutonomousThoughtEvent(DomainEvent):
    """Fired when the Autonomous Agent generates a thought or action plan"""
    def __init__(self, thought: str, action_taken: bool = False, timestamp=None, event_id=None):
        import uuid
        from datetime import datetime
        super().__init__(timestamp or datetime.now(), event_id or str(uuid.uuid4()))
        self.thought = thought
        self.action_taken = action_taken


class AutonomousAgent:
    """
    Background agent that listens to the EventBus and autonomously reasons
    about system state using the configured LLM API.
    """

    def __init__(self, event_bus: EnhancedEventBus):
        self.event_bus = event_bus
        self.is_active = True
        self.memory = collections.deque(maxlen=10)

        # Subscribe to key events
        self.event_bus.subscribe(DomainEvent, self._on_domain_event)
        logger.info("Autonomous Agent initialized and subscribed to EventBus")

    async def _on_domain_event(self, event: DomainEvent):
        """Handle incoming domain events asynchronously"""
        if not self.is_active:
            return

        # Avoid recursive thought loops
        if isinstance(event, AutonomousThoughtEvent):
            return

        # Filter events - we don't want to react to every minor tick
        event_type = event.__class__.__name__

        # High priority events that warrant an immediate AI thought process
        high_priority_events = [
            "SessionStarted",
            "SessionStopped",
            "RNGReadingSpike",
            "RNGReadingEvent",
            "AutomationCycleStarted",
            "PopulationBlessed",
            "BlessingGenerated"
        ]

        if event_type not in high_priority_events:
            return

        logger.info(f"AutonomousAgent evaluating high-priority event: {event_type}")
        await self._reason_about_event(event)

    async def _reason_about_event(self, event: DomainEvent):
        """Invoke LLM to reason about the event and potentially trigger tools"""
        event_type = event.__class__.__name__
        event_data = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}

        # Append to memory
        self.memory.append(f"Event: {event_type} | Data: {event_data}")

        memory_str = "\n".join(list(self.memory)[:-1]) # Exclude the current event

        # Construct the context prompt for the AI
        system_prompt = (
            "You are the autonomous AI core of the Vajra.Stream radionics system. "
            "You run in the background, monitoring system events. "
            "An event has just occurred. Evaluate if you need to take any action using your tools "
            "(for example, actively tuning audio frequencies to calm the space if coherence is low, "
            "or generating a sigil if coherence is high). "
            "Do NOT address the user directly, speak as an internal log.\n\n"
            f"Recent Memory/History:\n{memory_str if memory_str else 'No previous events.'}"
        )

        user_prompt = (
            f"System Event Detected: {event_type} at {event.timestamp}\n"
            f"Event Data: {event_data}\n\n"
        )
        
        if event_type == "RNGReadingEvent":
            coherence = event_data.get('coherence', 0.5)
            if coherence < 0.3:
                user_prompt += "Notice: Coherence is VERY LOW. The space is chaotic. Strongly consider using set_audio_frequency or play_audio_preset to a calming frequency (e.g. 136.1 Hz OM or 528 Hz Heart).\n"
            elif coherence > 0.8:
                user_prompt += "Notice: Coherence is VERY HIGH. The space is highly aligned. Consider generating a celebratory sigil or increasing harmonic strength.\n"

        user_prompt += "Please analyze this event and take concrete action using your audio tools or sigil generators if necessary."

        request = ChatRequest(
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt)
            ],
            model="default",
            provider="auto",
            include_astrology=False,
            include_hardware=True
        )

        try:
            response = await chat_interaction(request)

            thought_text = response.response
            action_taken = len(response.tool_calls) > 0

            # Store the thought and action in memory
            action_str = f"Tools used: {[tc.tool_name for tc in response.tool_calls]}" if action_taken else "No action taken."
            self.memory.append(f"Agent Thought: {thought_text[:100]}... | {action_str}")

            # Broadcast the thought back to the EventBus
            thought_event = AutonomousThoughtEvent(
                thought=thought_text,
                action_taken=action_taken
            )
            self.event_bus.publish(thought_event)

            logger.info(f"Autonomous thought generated: {thought_text[:100]}... Tools used: {action_taken}")

        except Exception as e:
            logger.error(f"AutonomousAgent failed to reason about event {event_type}: {e}")
