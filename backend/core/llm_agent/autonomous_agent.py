import collections
import logging
import os
import threading
import time
from types import SimpleNamespace
from typing import Any

from starlette.requests import Request

from infrastructure.event_bus import EnhancedEventBus

# Import known events that we might want to react to
from modules.interfaces import DomainEvent

logger = logging.getLogger(__name__)

# VAJRA_AUTONOMOUS_AGENT=1 is not "enable logging". It is permission for an
# autonomous background process to take real actions and spend real money
# without a human in the loop.
#
# What the flag actually switches on:
#   * PAID LLM calls. Every admitted thought is a provider request.
#   * TOOL USE. The agent reaches the same tool surface as chat, which includes
#     audio tools -- play_chakra_healing_audio, set_audio_frequency,
#     set_audio_modulation, play_audio_preset (core/tool_registry/catalog.py).
#   * AUDIO PLAYBACK. The agent audio path (_audio_play in
#     backend/core/llm_agent/tools.py) defaults to hardware_level=2 and
#     consults NO separate audio opt-in of its own; that module reads no
#     environment variables at all. So this flag is also the speaker switch.
#
# What the default OFF buys you: an agent that is merely constructed and
# subscribed never spends and never plays. That is the whole of the safety
# story -- it is a flag, not a budget.
_AUTONOMOUS_AGENT_ENV = "VAJRA_AUTONOMOUS_AGENT"

# Even when enabled, an agent must not think on every event: some events are
# published on a tick (RNGReadingEvent), so without a floor an enabled agent
# would make one paid call per tick. The floor is per event type.
#
# Read this as a THROUGHT-ADMISSION floor, not a spend cap. It limits how often
# a given event TYPE may open a thought; it does not limit how expensive any
# thought is. One admitted thought may involve several provider requests,
# follow-ups and tool actions, and nothing here bounds the total.
# With seven high-priority event types the ceiling is therefore up to seven
# admitted thoughts per minute PER INSTANCE, each of unbounded cost, with no
# monetary ceiling anywhere. Counters are per instance and reset on restart.
_MIN_THOUGHT_INTERVAL_SECONDS = 60.0


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

    def __init__(self, event_bus: EnhancedEventBus, llm_registry: Any = None):
        """Create the agent.

        ``llm_registry`` is the provider registry the chat path needs. It is
        optional: the agent runs in the background and may have no HTTP
        request of its own, so a caller that HAS a registry (the FastAPI app
        keeps one on ``app.state.llm_registry``) can hand it over.

        When no registry can be found the agent does NOT skip the thought. It
        still builds a synthetic request, still calls the real chat path, logs
        a warning that the lookup will find nothing, and the resulting
        ``AttributeError`` is caught and logged by the caller. No provider is
        invented and nothing is generated -- the attempt fails, visibly, in the
        log -- rather than being quietly skipped.
        """
        self.event_bus = event_bus
        self.llm_registry = llm_registry
        self.is_active = True
        self.memory = collections.deque(maxlen=10)
        # Last time a thought was attempted, per event type, for the rate limit.
        self._last_thought_at: dict[str, float] = {}
        # Guards the check-and-update in _interval_elapsed. A threading.Lock and
        # not an asyncio.Lock: EnhancedEventBus.publish runs coroutine
        # subscribers on WORKER-thread event loops when published from a
        # thread (core/tool_registry offloads sync tools), so two handlers for
        # the same event type can be on different loops and an asyncio lock
        # would not be shared between them. Without this, both threads read
        # "absent" and both admit -- two paid thoughts for one interval.
        self._interval_lock = threading.Lock()

        # Subscribe to key events
        self.event_bus.subscribe(DomainEvent, self._on_domain_event)
        logger.info("Autonomous Agent initialized and subscribed to EventBus")

    def _spending_enabled(self) -> bool:
        """Whether the agent may call the LLM and act on its own at all.

        Default OFF. The agent is wired into the live event bus and some
        events are published on every tick, so an always-on agent would make a
        paid call per tick. The flag is read per call so it can be turned on
        without rebuilding the agent.

        ON is a blank cheque, not a throttle. It authorises paid provider calls
        and tool use, including the audio tools that default to hardware_level=2
        playback with no separate audio opt-in on the agent path. What limits
        that is the per-event-type admission floor in
        :data:`_MIN_THOUGHT_INTERVAL_SECONDS`, which counts THOUGHTS -- not
        requests, not tool actions, not money. One admitted thought can cost
        several requests and any number of actions; there is no monetary
        ceiling, and the counters are per instance and reset on restart.
        """
        return os.environ.get(_AUTONOMOUS_AGENT_ENV) == "1"

    def _interval_elapsed(self, event_type: str) -> bool:
        """Whether enough time has passed to think about this event type.

        The clock is advanced when the gate passes, not when the call
        succeeds, so a failing call cannot be retried in a tight loop.

        The read and the write are one critical section. On a single event loop
        there is no await between them and they cannot interleave, but
        ``EnhancedEventBus.publish`` runs coroutine subscribers on worker-thread
        loops when it is published from a thread, so real threads can reach
        this method at once. The lock is a :class:`threading.Lock` because those
        threads are on different event loops and would not share an asyncio
        lock.
        """
        now = time.monotonic()
        with self._interval_lock:
            last = self._last_thought_at.get(event_type)
            if last is not None and (now - last) < _MIN_THOUGHT_INTERVAL_SECONDS:
                return False
            self._last_thought_at[event_type] = now
            return True

    def _resolved_registry(self):
        """The provider registry the chat path needs, or None.

        The injected one wins. Otherwise the live FastAPI application's is
        used, because the lifespan puts it on ``app.state.llm_registry``.

        Returning None does NOT mean the thought is skipped: the caller still
        builds the request and calls the real chat path, logs a warning, and
        lets the lookup fail inside its own error handling. This method only
        reports whether a registry is reachable.

        Why the fallback is kept rather than injection-only: the agent is
        constructed by the orchestrator with only an event bus
        (``AutonomousAgent(self.event_bus)``), so an injected registry would
        always be None in production and the opt-in flag would be useless. The
        fallback is confined to this one method and is overridable, so a
        caller - or a test - can pin the behaviour; the agent's own tests
        stub it out so they never depend on global application state.
        """
        if self.llm_registry is not None:
            return self.llm_registry
        app = self._live_app()
        if app is None:
            return None
        return getattr(app.state, "llm_registry", None)

    def _live_app(self):
        """The running FastAPI application, or None.

        Imported lazily: backend.app.main pulls in the whole application and
        importing it at module level would create an import cycle.
        """
        try:
            from backend.app.main import app as fastapi_app

            return fastapi_app
        except Exception:  # noqa: BLE001 - the app is optional here
            return None

    def _provider_request(self):
        """Build the minimal Request the provider lookup needs.

        ``chat_compat`` reads the provider registry from
        ``http_request.app.state.llm_registry``; the agent has no HTTP request
        of its own, so it builds a minimal Starlette scope around whichever
        registry it can reach: the one injected at construction, else the live
        FastAPI application's. The scope is deliberately minimal - it carries
        only what the provider lookup reads.

        Always returns a Request. When no registry can be found the scope still
        carries the live application if it is importable, or a minimal stand-in
        otherwise, and the caller's provider lookup fails inside its own error
        handling. Returning a Request unconditionally is deliberate: returning
        None would make the arity of the chat call depend on global application
        state, which is exactly the class of bug this file's tests exist to
        prevent.
        """
        registry = self._resolved_registry()
        if registry is not None:
            state = SimpleNamespace(llm_registry=registry)
            app = SimpleNamespace(state=state)
        else:
            # No registry anywhere: carry the live application when it is
            # importable, so the scope is the real thing, and a minimal
            # stand-in otherwise. Nothing is invented either way.
            app = self._live_app()
            if app is None:
                app = SimpleNamespace(state=SimpleNamespace(llm_registry=None))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "client": ("localhost", 0),
            "server": ("localhost", 80),
            "app": app,
        }
        return Request(scope)

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
            "BlessingGenerated",
        ]

        if event_type not in high_priority_events:
            return

        if not self._spending_enabled():
            logger.debug("AutonomousAgent is disabled (opt-in via %s); ignoring %s", _AUTONOMOUS_AGENT_ENV, event_type)
            return

        if not self._interval_elapsed(event_type):
            logger.debug(
                "AutonomousAgent throttled for %s (min interval %ss)", event_type, _MIN_THOUGHT_INTERVAL_SECONDS
            )
            return

        logger.info(f"AutonomousAgent evaluating high-priority event: {event_type}")
        await self._reason_about_event(event)

    async def _reason_about_event(self, event: DomainEvent):
        """Invoke LLM to reason about the event and potentially trigger tools"""
        event_type = event.__class__.__name__
        event_data = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}

        # Append to memory
        self.memory.append(f"Event: {event_type} | Data: {event_data}")

        memory_str = "\n".join(list(self.memory)[:-1])  # Exclude the current event

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

        user_prompt = f"System Event Detected: {event_type} at {event.timestamp}\nEvent Data: {event_data}\n\n"

        if event_type == "RNGReadingEvent":
            coherence = event_data.get("coherence", 0.5)
            if coherence < 0.3:
                user_prompt += "Notice: Coherence is VERY LOW. The space is chaotic. Strongly consider using set_audio_frequency or play_audio_preset to a calming frequency (e.g. 136.1 Hz OM or 528 Hz Heart).\n"
            elif coherence > 0.8:
                user_prompt += "Notice: Coherence is VERY HIGH. The space is highly aligned. Consider generating a celebratory sigil or increasing harmonic strength.\n"

        user_prompt += "Please analyze this event and take concrete action using your audio tools or sigil generators if necessary."

        # Function-level by design: this service must not import the API layer at
        # module level. backend.app.api's package __init__ loads every endpoint,
        # and endpoints/radionics -> orchestrator_bridge -> scripts.unified_orchestrator
        # imports this module, so a module-level import here is an import cycle
        # (Phase 3; tests/unit/test_import_layering.py).
        from backend.app.api.v1.endpoints.llm import ChatMessage, ChatRequest, chat_interaction

        request = ChatRequest(
            messages=[ChatMessage(role="system", content=system_prompt), ChatMessage(role="user", content=user_prompt)],
            model="default",
            provider="auto",
            include_astrology=False,
            include_hardware=True,
        )

        http_request = self._provider_request()
        if self._resolved_registry() is None:
            logger.warning(
                "Autonomous agent has no LLM provider registry; the provider lookup " "for %s will not find one",
                event_type,
            )

        try:
            # chat_interaction aliases chat_compat, which needs (request,
            # http_request): the provider registry is read off
            # http_request.app.state. Passing only the request raised TypeError
            # and every autonomous thought died silently.
            response = await chat_interaction(request, http_request)

            thought_text = response.response
            action_taken = len(response.tool_calls) > 0

            # Store the thought and action in memory
            action_str = (
                f"Tools used: {[tc.tool_name for tc in response.tool_calls]}" if action_taken else "No action taken."
            )
            self.memory.append(f"Agent Thought: {thought_text[:100]}... | {action_str}")

            # Broadcast the thought back to the EventBus
            thought_event = AutonomousThoughtEvent(thought=thought_text, action_taken=action_taken)
            self.event_bus.publish(thought_event)

            logger.info(f"Autonomous thought generated: {thought_text[:100]}... Tools used: {action_taken}")

        except Exception as e:
            logger.error(f"AutonomousAgent failed to reason about event {event_type}: {e}")
