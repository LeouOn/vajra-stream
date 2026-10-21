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

# Two exact-value switches. Neither is "enable logging".
#
# VAJRA_AUTONOMOUS_AGENT=1 lets the agent think and observe. An admitted
# thought is a paid provider call, and the only tools it may run are the
# read-only allowlist below. It does not grant audio, hardware, file or
# database writes, network calls, or session start/stop.
#
# VAJRA_AUTONOMOUS_AGENT_ACTIONS=1 additionally lets that thought act. The
# tool surface is then the same one chat uses, including the audio tools
# (play_chakra_healing_audio, set_audio_frequency, set_audio_modulation,
# play_audio_preset). The agent audio path (_audio_play in
# backend/core/llm_agent/tools.py) defaults to hardware_level=2 and reads no
# environment variable of its own, so ACTIONS=1 is also the speaker switch.
#
# With ACTIONS unset, or set to anything other than the exact value "1",
# the thought stays observe-only even when AGENT=1. A tool outside the
# allowlist is refused before it runs.
#
# What the default OFF buys you: an agent that is merely constructed and
# subscribed never spends and never acts. The flags are not a budget.
_AUTONOMOUS_AGENT_ENV = "VAJRA_AUTONOMOUS_AGENT"
_AUTONOMOUS_AGENT_ACTIONS_ENV = "VAJRA_AUTONOMOUS_AGENT_ACTIONS"

# Read-only allowlist. A tool that is not in this set is acting (default-deny).
# A name is read-only only when calling it does not play audio, touch hardware,
# write a file or database, make a network or paid call, or start or stop a
# session, and does not change what a later call returns. This is the smallest
# set that stays clean when each tool is executed under a scratch home with
# sockets blocked. get_narrative_loop_status is acting: the call imports the
# outlook stack, which creates ~/.vajra-stream/sigils and requests the ANU QRNG.
READ_ONLY_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "cast_geomancy",
        "cast_i_ching",
        "cast_tarot_spread",
        "check_saka_dawa",
        "find_balancing_rates",
        "generate_character",
        "get_88_buddhas_liturgy",
        "get_blessing_traditions",
        "get_buddha_recitation_status",
        "get_chakra_info",
        "get_current_slide",
        "get_dharani_text",
        "get_healing_modalities",
        "get_journey_status",
        "get_meridian_info",
        "get_ritual_schedule",
        "list_practices",
        "measure_general_vitality",
        "search_grimoire_correspondences",
        "search_knowledge",
        "search_rate_database",
        "text_to_rate",
    }
)

# Every other registry tool, named so a newly added tool is a test failure
# until someone classifies it. Observe-only mode never consults this set:
# it allows READ_ONLY_TOOL_NAMES and refuses the rest.
ACTING_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "add_agent_suggestion",
        "advance_journey",
        "broadcast_healing",
        "broadcast_liberation",
        "calculate_natal_chart",
        "chakra_balancing_protocol",
        "check_auspicious_timing",
        "create_blessing_slideshow",
        "create_healing_session",
        "create_narrative_character",
        "create_narrative_location",
        "create_population",
        "create_rng_session",
        "forge_sigil",
        "forge_witness",
        "generate_audio",
        "generate_blessing",
        "generate_buddha_narrative",
        "generate_epic_outlook",
        "generate_image",
        "generate_meditation_script",
        "generate_prayer",
        "generate_scalar_waves",
        "generate_single_outlook",
        "generate_teaching",
        "get_active_world_crises",
        "get_all_genre_windows",
        "get_auspicious_timing_details",
        "get_automation_stats",
        "get_automation_status",
        "get_available_intentions",
        "get_celestial_night_sky",
        "get_current_conditions",
        "get_narrative_loop_status",
        "get_planetary_hours_and_transits",
        "get_planetary_positions",
        "get_population_statistics",
        "get_random_buddha",
        "get_ritual_status",
        "get_rng_reading",
        "get_rng_summary",
        "get_sacred_frequencies",
        "get_system_status",
        "get_world_context",
        "list_narrative_characters",
        "list_narrative_locations",
        "list_populations",
        "pause_automation",
        "play_audio_preset",
        "play_chakra_healing_audio",
        "prepare_crystal_broadcast",
        "recite_buddha_name",
        "resume_automation",
        "run_full_journey",
        "run_working",
        "set_audio_frequency",
        "set_audio_modulation",
        "speak_text",
        "start_automation",
        "start_buddha_recitation",
        "start_character_journey",
        "start_narrative_loop",
        "start_ritual_engine",
        "stop_automation",
        "stop_buddha_recitation",
        "stop_narrative_loop",
        "stop_rng_session",
        "stop_ritual_engine",
        "stop_slideshow",
        "trigger_living_ritual_broadcast",
        "trigger_ritual",
        "update_population",
        "web_fetch",
        "web_search",
    }
)

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


def _observe_tool_schemas() -> list[dict[str, Any]]:
    """Chat tools the observe-only thought may be shown.

    The advertised list is today's chat list filtered by the allowlist, in
    chat order. Tools that exist only on other surfaces stay unadvertised,
    which is today's behaviour, and the executor still refuses them when
    they are acting.
    """
    from core import tool_registry

    allowed = READ_ONLY_TOOL_NAMES
    return [schema for schema in tool_registry.chat_tool_schemas() if schema["name"] in allowed]


class ObserveOnlyRefusal(PermissionError):
    """The observe-only gate refused a tool before its handler ran.

    The chat loop already catches ``PermissionError``, and this is one, so a
    refusal is still logged as a failed tool call. A handler's own
    ``PermissionError`` is a different failure: it is not this class, it is
    not recorded as a refusal, and it propagates unchanged.
    """


async def _observe_only_executor(name: str, args: dict) -> Any:
    """Run a tool only when its canonical name is on the read-only allowlist.

    Aliases are resolved first, so an alias of an acting tool cannot slip
    through and an alias of a read-only tool still runs. Anything else raises
    ``ObserveOnlyRefusal`` before the handler is touched. The chat tool loop
    catches ``PermissionError``, so that refusal is logged and does not
    change the world. A ``PermissionError`` raised by the handler itself
    takes the same chat-loop path and is not relabelled as a gate refusal.
    """
    from backend.app.api.v1.endpoints.llm import execute_tool_locally
    from core import tool_registry

    canonical = tool_registry.resolve_name(name)
    if canonical not in READ_ONLY_TOOL_NAMES:
        raise ObserveOnlyRefusal(f"observe-only mode refuses tool {name!r}")
    return await execute_tool_locally(name, args)


async def _observe_chat(request: Any, http_request: Any) -> tuple[Any, list[str]]:
    """The chat path with a filtered tool list and a refusing executor.

    ``chat_interaction`` always advertises the full chat list and ignores
    ``ChatRequest.tools``, so observe-only cannot use it. Provider selection
    matches that function; the schemas and the executor do not.

    The second value is the canonical name of each tool the executor refused
    during this call. It stays empty when every requested tool was allowed.
    The list is local to the call: nothing is stored on the module.
    """
    from backend.app.api.v1.endpoints import llm as llm_module
    from core import tool_registry

    refused: list[str] = []

    async def _recording_executor(name: str, args: dict) -> Any:
        try:
            return await _observe_only_executor(name, args)
        except ObserveOnlyRefusal:
            refused.append(tool_registry.resolve_name(name))
            raise

    provider_name = llm_module._resolve_provider_name(request, http_request)
    if provider_name == "auto":
        registry_choice = await llm_module._select_provider_via_registry(http_request, "auto")
        if registry_choice:
            provider_name = registry_choice
    response = await llm_module._chat_via_registry(
        http_request,
        request,
        provider_name,
        tool_schemas=_observe_tool_schemas(),
        tool_executor=_recording_executor,
    )
    return response, refused


class AutonomousThoughtEvent(DomainEvent):
    """Fired when the Autonomous Agent generates a thought or action plan.

    ``refused_tools`` is set only when observe-only mode refused one or more
    tool names. An absent attribute means nothing was refused.
    """

    def __init__(
        self,
        thought: str,
        action_taken: bool = False,
        timestamp=None,
        event_id=None,
        refused_tools: list[str] | None = None,
    ):
        import uuid
        from datetime import datetime

        super().__init__(timestamp or datetime.now(), event_id or str(uuid.uuid4()))
        self.thought = thought
        self.action_taken = action_taken
        if refused_tools:
            self.refused_tools = list(refused_tools)


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

        ON admits a paid thought. With the actions switch off, the only tools
        that thought may run are the read-only allowlist. Audio, hardware,
        writes, network, and session changes need :meth:`_actions_enabled`
        as well (``VAJRA_AUTONOMOUS_AGENT_ACTIONS=1``). What limits the spend
        is the per-event-type admission floor in
        :data:`_MIN_THOUGHT_INTERVAL_SECONDS`, which counts THOUGHTS -- not
        requests, not tool actions, not money. One admitted thought can cost
        several requests and any number of actions; there is no monetary
        ceiling, and the counters are per instance and reset on restart.
        """
        return os.environ.get(_AUTONOMOUS_AGENT_ENV) == "1"

    def _actions_enabled(self) -> bool:
        """Whether an admitted thought may change the world.

        Default OFF, and independent of :meth:`_spending_enabled`. The agent
        flag admits the paid thought. This flag admits audio, hardware,
        writes, network and session changes. Read per call, exact value
        ``"1"``.
        """
        return os.environ.get(_AUTONOMOUS_AGENT_ACTIONS_ENV) == "1"

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

    def _thought_prompts(
        self,
        event: DomainEvent,
        event_type: str,
        event_data: dict[str, Any],
        memory_str: str,
        *,
        observe_only: bool,
    ) -> tuple[str, str]:
        """Build the system and user prompts for one thought.

        Actions-on keeps the historical wording. Observe-only tells the model
        to state what it WOULD do and does not name an acting tool.
        """
        history = f"Recent Memory/History:\n{memory_str if memory_str else 'No previous events.'}"
        if observe_only:
            system_prompt = (
                "You are the autonomous AI core of the Vajra.Stream system. "
                "You run in the background, monitoring system events. "
                "You are in observe-only mode. You may read and compute. "
                "You must not play sound, change hardware, write files or databases, "
                "start or stop a session, or call a paid or networked service. "
                "State what you WOULD do, as an internal log. Do not address the user directly.\n\n"
                f"{history}"
            )
            user_prompt = f"System Event Detected: {event_type} at {event.timestamp}\nEvent Data: {event_data}\n\n"
            if event_type == "RNGReadingEvent":
                coherence = event_data.get("coherence", 0.5)
                if coherence < 0.3:
                    user_prompt += (
                        "Notice: Coherence is VERY LOW. The space is chaotic. "
                        "State that you WOULD choose a calming tone such as 136.1 Hz or 528 Hz. "
                        "Do not play sound.\n"
                    )
                elif coherence > 0.8:
                    user_prompt += (
                        "Notice: Coherence is VERY HIGH. The space is highly aligned. "
                        "State that you WOULD mark the moment. Do not create an image.\n"
                    )
            user_prompt += (
                "You are in observe-only mode. Analyze this event and state what you WOULD do. "
                "Do not call a tool that changes the world."
            )
            return system_prompt, user_prompt

        system_prompt = (
            "You are the autonomous AI core of the Vajra.Stream radionics system. "
            "You run in the background, monitoring system events. "
            "An event has just occurred. Evaluate if you need to take any action using your tools "
            "(for example, actively tuning audio frequencies to calm the space if coherence is low, "
            "or generating a sigil if coherence is high). "
            "Do NOT address the user directly, speak as an internal log.\n\n"
            f"{history}"
        )
        user_prompt = f"System Event Detected: {event_type} at {event.timestamp}\nEvent Data: {event_data}\n\n"
        if event_type == "RNGReadingEvent":
            coherence = event_data.get("coherence", 0.5)
            if coherence < 0.3:
                user_prompt += (
                    "Notice: Coherence is VERY LOW. The space is chaotic. "
                    "Strongly consider using set_audio_frequency or play_audio_preset to a calming frequency "
                    "(e.g. 136.1 Hz OM or 528 Hz Heart).\n"
                )
            elif coherence > 0.8:
                user_prompt += (
                    "Notice: Coherence is VERY HIGH. The space is highly aligned. "
                    "Consider generating a celebratory sigil or increasing harmonic strength.\n"
                )
        user_prompt += (
            "Please analyze this event and take concrete action using your audio tools "
            "or sigil generators if necessary."
        )
        return system_prompt, user_prompt

    async def _reason_about_event(self, event: DomainEvent):
        """Invoke LLM to reason about the event and potentially trigger tools"""
        event_type = event.__class__.__name__
        event_data = {k: v for k, v in event.__dict__.items() if not k.startswith("_")}

        # Append to memory
        self.memory.append(f"Event: {event_type} | Data: {event_data}")

        memory_str = "\n".join(list(self.memory)[:-1])  # Exclude the current event
        observe_only = not self._actions_enabled()
        system_prompt, user_prompt = self._thought_prompts(
            event, event_type, event_data, memory_str, observe_only=observe_only
        )

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
            include_hardware=not observe_only,
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
            # and every autonomous thought died silently. Observe-only cannot
            # use it: that path advertises every chat tool and ignores
            # request.tools. Actions-on keeps the call unchanged.
            if observe_only:
                response, refused_tools = await _observe_chat(request, http_request)
                # No acting tool can run here. A refusal and a completed
                # read-only call are both not an action.
                action_taken = False
            else:
                response = await chat_interaction(request, http_request)
                action_taken = len(response.tool_calls) > 0
                refused_tools = ()

            thought_text = response.response

            # Store the thought and action in memory
            action_str = (
                f"Tools used: {[tc.tool_name for tc in response.tool_calls]}" if action_taken else "No action taken."
            )
            self.memory.append(f"Agent Thought: {thought_text[:100]}... | {action_str}")

            # Broadcast the thought back to the EventBus. The refusal list is
            # attached only when it has names, so an empty report stays absent.
            if refused_tools:
                thought_event = AutonomousThoughtEvent(
                    thought=thought_text,
                    action_taken=action_taken,
                    refused_tools=list(refused_tools),
                )
            else:
                thought_event = AutonomousThoughtEvent(thought=thought_text, action_taken=action_taken)
            self.event_bus.publish(thought_event)

            logger.info(f"Autonomous thought generated: {thought_text[:100]}... Tools used: {action_taken}")

        except Exception as e:
            logger.error(f"AutonomousAgent failed to reason about event {event_type}: {e}")
