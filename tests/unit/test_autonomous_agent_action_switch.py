"""AG-1: the autonomous agent can think without acting.

``VAJRA_AUTONOMOUS_AGENT=1`` admits a paid thought. A second exact-value
switch, ``VAJRA_AUTONOMOUS_AGENT_ACTIONS=1``, is required before that thought
may change the world. With the second switch off, the tool list is the
read-only allowlist and the prompt says what the agent WOULD do.

No real provider call: the chat functions are recording fakes.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from backend.core.llm_agent.autonomous_agent import AutonomousAgent, AutonomousThoughtEvent
from infrastructure.event_bus import EnhancedEventBus
from modules.interfaces import RNGReadingEvent

# Names that play audio, touch hardware, speak, spend on a tool, search the
# network, or start and stop something. Observe-only mode must not advertise
# any of them.
_FORBIDDEN_TOOL_NAMES = (
    "play_chakra_healing_audio",
    "set_audio_frequency",
    "set_audio_modulation",
    "play_audio_preset",
    "generate_audio",
    "speak_text",
    "forge_sigil",
    "generate_image",
    "web_search",
    "web_fetch",
    "run_working",
    "generate_single_outlook",
    "generate_blessing",
    "generate_prayer",
    "start_automation",
    "stop_automation",
    "trigger_living_ritual_broadcast",
    "broadcast_healing",
    "get_active_world_crises",
    "get_world_context",
)

_CONCRETE_ACTION_SENTENCE = (
    "Please analyze this event and take concrete action using your audio tools or sigil generators if necessary."
)


class _EmptyRegistry:
    """A provider registry with nothing selectable. ``len`` is what lookup reads."""

    def __len__(self) -> int:
        return 0


class _FakeResponse:
    def __init__(self, text: str = "observed") -> None:
        self.response = text
        self.tool_calls: list[Any] = []


class _RecordingChat:
    def __init__(self, sink: dict[str, Any], key: str) -> None:
        self._sink = sink
        self._key = key

    async def __call__(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        self._sink[self._key] = {"args": args, "kwargs": kwargs}
        return _FakeResponse()


class _ToolCall:
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name


class _ExecutorCallingChat:
    """Stand-in for the chat loop: run the executor, then keep the tool call.

    ``_chat_via_registry`` catches ``PermissionError``, logs an error tool
    call, and still returns that call on the response. This fake does the
    same. ``error`` keeps the exception so a handler failure stays visible
    instead of being rewritten into a refusal.
    """

    def __init__(self, tool_name: str, args: dict[str, Any] | None = None) -> None:
        self._tool_name = tool_name
        self._args: dict[str, Any] = {} if args is None else args
        self.invoked_executor = False
        self.error: BaseException | None = None

    async def __call__(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        executor = kwargs.get("tool_executor")
        if executor is not None:
            self.invoked_executor = True
            try:
                await executor(self._tool_name, self._args)
            except PermissionError as exc:
                self.error = exc
        response = _FakeResponse()
        response.tool_calls = [_ToolCall(self._tool_name)]
        return response


async def _run_thought(
    monkeypatch: pytest.MonkeyPatch,
    *,
    actions: bool,
    tool_name: str,
    tool_args: dict[str, Any],
    execute_error: BaseException | None = None,
) -> tuple[Any, list[str], dict[str, Any], _ExecutorCallingChat]:
    """Drive one thought with a fake chat that requests ``tool_name``."""
    from backend.app.api.v1.endpoints import llm as llm_module

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    if actions:
        monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    else:
        monkeypatch.delenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", raising=False)

    forwarded: list[str] = []

    async def _fake_execute(name: str, args: dict) -> dict[str, str]:
        forwarded.append(name)
        if execute_error is not None:
            raise execute_error
        return {"name": name}

    monkeypatch.setattr(llm_module, "execute_tool_locally", _fake_execute)
    chat = _ExecutorCallingChat(tool_name, tool_args)
    sink: dict[str, Any] = {}
    if actions:
        monkeypatch.setattr(llm_module, "chat_interaction", chat)
        monkeypatch.setattr(llm_module, "_chat_via_registry", _RecordingChat(sink, "registry"))
    else:
        monkeypatch.setattr(llm_module, "chat_interaction", _RecordingChat(sink, "chat"))
        monkeypatch.setattr(llm_module, "_chat_via_registry", chat)

    bus = EnhancedEventBus()
    thoughts: list[Any] = []
    bus.subscribe(AutonomousThoughtEvent, thoughts.append)
    agent = AutonomousAgent(bus, llm_registry=_EmptyRegistry())
    event = RNGReadingEvent(session_id="s", coherence=0.1, entropy=0.2, floating_needle_score=0.1)
    await agent._reason_about_event(event)
    assert len(thoughts) == 1, "the thought was not published"
    return thoughts[0], forwarded, sink, chat


def _agent_source_head() -> str:
    path = pathlib.Path(__file__).resolve().parents[2] / "backend" / "core" / "llm_agent" / "autonomous_agent.py"
    text = path.read_text(encoding="utf-8")
    return text.split("class AutonomousThoughtEvent", 1)[0]


def _prompt_text(request: Any) -> str:
    return "\n".join(message.content for message in request.messages)


def test_actions_switch_is_documented_and_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both switches are exact-value ``1`` and off unless that value is set."""
    from backend.core.llm_agent import autonomous_agent as agent_module

    monkeypatch.delenv("VAJRA_AUTONOMOUS_AGENT", raising=False)
    monkeypatch.delenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", raising=False)

    assert "VAJRA_AUTONOMOUS_AGENT_ACTIONS" in _agent_source_head()
    assert getattr(agent_module, "_AUTONOMOUS_AGENT_ACTIONS_ENV", None) == "VAJRA_AUTONOMOUS_AGENT_ACTIONS"

    agent = AutonomousAgent(EnhancedEventBus())
    assert agent._spending_enabled() is False
    actions_enabled = getattr(agent, "_actions_enabled", None)
    assert actions_enabled is not None
    assert actions_enabled() is False

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "true")
    assert agent._actions_enabled() is False
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    assert agent._actions_enabled() is True
    assert agent._spending_enabled() is False

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "0")
    assert agent._spending_enabled() is True
    assert agent._actions_enabled() is False


def test_every_exposed_tool_is_classified_exactly_once() -> None:
    """A new registry tool fails this test until it is marked read-only or acting.

    Default-deny lives in the allowlist: a name that is not read-only is acting,
    and a name in neither set is a test failure rather than a silent observe tool.
    """
    from backend.core.llm_agent import autonomous_agent as agent_module
    from core import tool_registry

    read_only = getattr(agent_module, "READ_ONLY_TOOL_NAMES", None)
    acting = getattr(agent_module, "ACTING_TOOL_NAMES", None)
    assert isinstance(read_only, frozenset)
    assert isinstance(acting, frozenset)

    exposed = set(tool_registry.tool_names())
    assert exposed, "the registry exposed no tools"
    missing = sorted(exposed - read_only - acting)
    extra = sorted((read_only | acting) - exposed)
    overlap = sorted(read_only & acting)
    assert not missing, f"unclassified tools: {missing}"
    assert not extra, f"names that are not tools: {extra}"
    assert not overlap, f"classified both ways: {overlap}"
    # The observe set is the tools an executed call left side-effect free.
    # get_narrative_loop_status is acting: importing its outlook stack creates
    # ~/.vajra-stream/sigils and requests the ANU QRNG.
    assert read_only == frozenset(
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
    assert "get_narrative_loop_status" in acting

    for name in _FORBIDDEN_TOOL_NAMES:
        assert name in acting, name
        assert name not in read_only, name


@pytest.mark.asyncio
async def test_observe_only_advertises_no_acting_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent on, actions off: the advertised list and the executor stay read-only."""
    from backend.app.api.v1.endpoints import llm as llm_module
    from backend.core.llm_agent import autonomous_agent as agent_module
    from core import tool_registry

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    monkeypatch.delenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", raising=False)

    sink: dict[str, Any] = {}
    monkeypatch.setattr(llm_module, "chat_interaction", _RecordingChat(sink, "chat"))
    monkeypatch.setattr(llm_module, "_chat_via_registry", _RecordingChat(sink, "registry"))

    forwarded: list[str] = []

    async def _fake_execute(name: str, args: dict) -> dict[str, str]:
        forwarded.append(name)
        return {"name": name, "args": str(sorted(args))}

    monkeypatch.setattr(llm_module, "execute_tool_locally", _fake_execute)

    agent = AutonomousAgent(EnhancedEventBus(), llm_registry=_EmptyRegistry())
    event = RNGReadingEvent(session_id="s", coherence=0.1, entropy=0.2, floating_needle_score=0.1)
    await agent._reason_about_event(event)

    assert "chat" not in sink, "observe-only must not use the unfiltered chat path"
    recorded = sink.get("registry")
    assert recorded is not None, "observe-only did not advertise a tool list"
    request = recorded["args"][1]
    assert request.include_hardware is False
    text = _prompt_text(request)
    assert "observe-only" in text
    assert "WOULD" in text
    assert _CONCRETE_ACTION_SENTENCE not in text
    assert "set_audio_frequency" not in text
    assert "sigil" not in text.lower()

    schemas = recorded["kwargs"]["tool_schemas"]
    names = [schema["name"] for schema in schemas]
    read_only = agent_module.READ_ONLY_TOOL_NAMES
    expected = [name for name in tool_registry.tool_names(tool_registry.CHAT) if name in read_only]
    assert names == expected
    assert "search_knowledge" in names
    assert "cast_i_ching" in names
    assert "get_dharani_text" in names
    assert "list_populations" not in names
    assert "get_system_status" not in names
    assert "get_narrative_loop_status" not in names
    assert "get_rng_reading" not in names
    assert "calculate_natal_chart" not in names
    assert set(_FORBIDDEN_TOOL_NAMES).isdisjoint(names)
    assert set(names) <= read_only

    executor = recorded["kwargs"]["tool_executor"]
    with pytest.raises(PermissionError):
        await executor("play_chakra_healing_audio", {"chakra_name": "heart"})
    with pytest.raises(PermissionError):
        await executor("world_crises", {})
    with pytest.raises(PermissionError):
        await executor("set_scalar_frequency", {"freq_hz": 528})
    with pytest.raises(PermissionError):
        await executor("get_system_status", {})
    with pytest.raises(PermissionError):
        await executor("list_targets", {})
    with pytest.raises(PermissionError):
        await executor("get_narrative_loop_status", {})
    assert forwarded == []

    await executor("search_knowledge", {"query": "water"})
    await executor("get_dharani", {})
    assert forwarded == ["search_knowledge", "get_dharani"]


@pytest.mark.asyncio
async def test_actions_on_restores_todays_chat_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """``VAJRA_AUTONOMOUS_AGENT_ACTIONS=1`` keeps today's prompt and full chat list."""
    from backend.app.api.v1.endpoints import llm as llm_module
    from core import tool_registry

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    agent = AutonomousAgent(EnhancedEventBus())
    actions_enabled = getattr(agent, "_actions_enabled", None)
    assert actions_enabled is not None and actions_enabled() is True

    sink: dict[str, Any] = {}
    monkeypatch.setattr(llm_module, "chat_interaction", _RecordingChat(sink, "chat"))
    monkeypatch.setattr(llm_module, "_chat_via_registry", _RecordingChat(sink, "registry"))

    agent = AutonomousAgent(EnhancedEventBus(), llm_registry=_EmptyRegistry())
    event = RNGReadingEvent(session_id="s", coherence=0.1, entropy=0.2, floating_needle_score=0.1)
    await agent._reason_about_event(event)

    assert "registry" not in sink
    recorded = sink["chat"]
    assert len(recorded["args"]) == 2
    request = recorded["args"][0]
    assert request.include_hardware is True
    text = _prompt_text(request)
    assert _CONCRETE_ACTION_SENTENCE in text
    assert "set_audio_frequency" in text
    assert "observe-only" not in text

    full = [schema["name"] for schema in tool_registry.chat_tool_schemas()]
    assert full == list(tool_registry.CHAT_ORDER)
    assert "play_chakra_healing_audio" in full
    assert "search_knowledge" in full


@pytest.mark.asyncio
async def test_observe_refused_acting_tool_is_not_an_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """A refused acting request is not an action. The name is reported on its own."""
    thought, forwarded, sink, chat = await _run_thought(
        monkeypatch,
        actions=False,
        tool_name="play_chakra_healing_audio",
        tool_args={"chakra_name": "heart"},
    )

    assert "chat" not in sink
    assert chat.invoked_executor is True
    assert forwarded == []
    assert thought.action_taken is False
    assert thought.refused_tools == ["play_chakra_healing_audio"]


@pytest.mark.asyncio
async def test_observe_read_only_tool_is_not_an_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """A read-only tool may run in observe mode and still leaves action_taken false."""
    thought, forwarded, sink, chat = await _run_thought(
        monkeypatch,
        actions=False,
        tool_name="cast_i_ching",
        tool_args={},
    )

    assert "chat" not in sink
    assert chat.invoked_executor is True
    assert forwarded == ["cast_i_ching"]
    assert thought.action_taken is False
    assert not hasattr(thought, "refused_tools")


@pytest.mark.asyncio
async def test_actions_on_keeps_action_taken_meaning(monkeypatch: pytest.MonkeyPatch) -> None:
    """ACTIONS=1 still treats any returned tool call as action_taken and adds no refusal field."""
    thought, forwarded, sink, chat = await _run_thought(
        monkeypatch,
        actions=True,
        tool_name="play_chakra_healing_audio",
        tool_args={"chakra_name": "heart"},
    )

    assert "registry" not in sink
    assert chat.invoked_executor is False
    assert forwarded == []
    assert thought.action_taken is True
    assert not hasattr(thought, "refused_tools")


@pytest.mark.asyncio
async def test_observe_handler_permission_error_is_not_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """An admitted handler's PermissionError is not a gate refusal.

    The gate records only its own refusal type. A filesystem PermissionError
    raised after the tool was admitted still propagates, with its message,
    and observe mode still reports no action and no refused tool.
    """
    from backend.core.llm_agent import autonomous_agent as agent_module

    handler_error = PermissionError("corpus unreadable")
    thought, forwarded, sink, chat = await _run_thought(
        monkeypatch,
        actions=False,
        tool_name="get_88_buddhas_liturgy",
        tool_args={},
        execute_error=handler_error,
    )

    assert "chat" not in sink
    assert chat.invoked_executor is True
    assert forwarded == ["get_88_buddhas_liturgy"], "the admitted handler did not run"
    assert chat.error is handler_error
    assert type(chat.error) is PermissionError
    assert str(chat.error) == "corpus unreadable"
    assert thought.action_taken is False
    assert not hasattr(thought, "refused_tools")
    refusal_type = getattr(agent_module, "ObserveOnlyRefusal", None)
    assert refusal_type is not None, "the gate has no refusal type of its own"
    assert not isinstance(chat.error, refusal_type)
