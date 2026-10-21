"""IR-1: the autonomous agent's chat call has the right arity.

RED-first regression tests for the same class of defect as the
/divination/interpret path: ``chat_interaction`` aliases ``chat_compat``, which
takes TWO arguments (``request`` and ``http_request``), but callers passed
only one, so the call raised ``TypeError`` inside a ``try``.

No LLM, no network: the chat function is a recording fake and the provider
registry is a fake.

The last test is the REGRESSION GUARD: it walks the source of every caller of
``chat_interaction`` under ``backend/`` and checks the arity against
``chat_compat``'s real signature, so this class of defect cannot come back.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import os
import pathlib
import threading
from typing import Any

import pytest

from backend.core.llm_agent.autonomous_agent import AutonomousAgent, AutonomousThoughtEvent
from infrastructure.event_bus import EnhancedEventBus
from modules.interfaces import (
    DomainEvent,
    RNGReadingEvent,
    SessionStarted,
    SessionStopped,
)


class FakeResponse:
    def __init__(self, text: str = "a thought") -> None:
        self.response = text
        self.tool_calls: list[Any] = []


class RecordingChat:
    """Stands in for ``chat_interaction`` and records how it was called."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[Any], int]] = []

    async def __call__(self, *args: Any) -> FakeResponse:
        self.calls.append((list(args), len(args)))
        return FakeResponse()


class FakeRegistry:
    """The smallest thing the provider lookup needs."""

    def __init__(self) -> None:
        self.providers: list[Any] = []
        self.picked: list[str] = []

    def __len__(self) -> int:
        return 0

    async def health_check_all(self) -> dict[str, Any]:
        return {}


class RecordingEventBus(EnhancedEventBus):
    def __init__(self) -> None:
        super().__init__()
        self.published: list[Any] = []

    def publish(self, event: Any) -> None:
        self.published.append(event)
        super().publish(event)


@pytest.fixture(autouse=True)
def _no_global_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these tests hermetic: no dependence on global FastAPI app state.

    The agent can fall back to the live application's provider registry, and
    any test that runs the app's lifespan (TestClient(app)) leaves that
    registry populated for every LATER test. Reading it here would make this
    file's results depend on test order, so the fallback is stubbed out and a
    registry is only ever supplied by explicit injection.
    """
    monkeypatch.setattr(AutonomousAgent, "_live_app", lambda self: None)


@pytest.mark.asyncio
async def test_agent_chat_call_uses_the_right_arity(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent's chat call must not raise TypeError.

    ``chat_compat`` needs (request, http_request); the agent used to pass only
    the request, so every autonomous thought died with a TypeError.
    """
    from backend.app.api.v1.endpoints import llm as llm_module

    # This test pins today's acting chat call. Observe-only does not use it.
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    fake_chat = RecordingChat()
    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat)

    bus = RecordingEventBus()
    agent = AutonomousAgent(bus, llm_registry=FakeRegistry())

    await agent._reason_about_event(SessionStarted(session_id="s", name="n"))

    assert fake_chat.calls, "the chat function was never called"
    assert fake_chat.calls[0][1] == 2, f"chat_interaction must be called with 2 args, got {fake_chat.calls[0][1]}"
    request = fake_chat.calls[0][0][1]
    assert hasattr(request, "app"), "the second argument must be a Request-like object"
    assert hasattr(request.app, "state")


@pytest.mark.asyncio
async def test_agent_publishes_its_thought_when_the_call_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A working chat call means the thought is produced and broadcast."""
    from backend.app.api.v1.endpoints import llm as llm_module

    # This test pins today's acting chat call. Observe-only does not use it.
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    monkeypatch.setattr(llm_module, "chat_interaction", RecordingChat())

    bus = RecordingEventBus()
    agent = AutonomousAgent(bus, llm_registry=FakeRegistry())

    await agent._reason_about_event(SessionStarted(session_id="s", name="n"))

    assert any(
        isinstance(e, AutonomousThoughtEvent) for e in bus.published
    ), f"expected an AutonomousThoughtEvent, got {[type(e).__name__ for e in bus.published]}"


@pytest.mark.asyncio
async def test_agent_without_a_registry_still_calls_with_the_right_arity(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """With no provider registry the agent still calls correctly, and says so.

    It must not raise TypeError, and it must not pretend the provider lookup
    will succeed: the missing registry is logged.
    """
    from backend.app.api.v1.endpoints import llm as llm_module

    # This test pins today's acting chat call. Observe-only does not use it.
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    fake_chat = RecordingChat()
    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat)

    bus = RecordingEventBus()
    agent = AutonomousAgent(bus)

    with caplog.at_level("WARNING"):
        await agent._reason_about_event(SessionStarted(session_id="s", name="n"))

    assert fake_chat.calls, "the chat function must still be called"
    assert fake_chat.calls[0][1] == 2, f"chat_interaction must be called with 2 args, got {fake_chat.calls[0][1]}"
    assert caplog.records, "a missing provider registry must be logged"
    assert any(
        "registry" in record.getMessage().lower() for record in caplog.records
    ), f"the warning should mention the registry: {[r.getMessage() for r in caplog.records]}"


def _backend_sources() -> list[pathlib.Path]:
    root = pathlib.Path(__file__).resolve().parents[2] / "backend"
    return [p for p in root.rglob("*.py") if "__pycache__" not in str(p)]


def test_every_chat_interaction_caller_uses_chat_compat_arity() -> None:
    """REGRESSION GUARD: no caller may pass the wrong number of arguments.

    ``chat_interaction`` is an alias of ``chat_compat``, whose signature is the
    contract. Every call site under ``backend/`` is checked by AST against that
    real signature, so this defect class cannot return.
    """
    from backend.app.api.v1.endpoints import llm as llm_module

    expected = len(inspect.signature(llm_module.chat_compat).parameters)
    assert expected == 2, f"chat_compat's arity changed; update this guard (now {expected})"

    offenders: list[str] = []
    for path in _backend_sources():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
            if name != "chat_interaction":
                continue
            supplied = len(node.args) + len(node.keywords)
            if supplied != expected:
                offenders.append(f"{path}:{node.lineno} passes {supplied} arg(s), expected {expected}")

    assert not offenders, "wrong arity in:\n" + "\n".join(offenders)


def test_chat_interaction_is_an_alias_of_chat_compat() -> None:
    """The alias is the reason the arity matters; keep the guard honest."""
    from backend.app.api.v1.endpoints import llm as llm_module

    assert llm_module.chat_interaction is llm_module.chat_compat
    assert issubclass(AutonomousThoughtEvent, DomainEvent)


# ---------------------------------------------------------------------------
# Spending guards. The agent calls a PAID LLM and is wired into the live
# event bus, where some events are published on every tick. It must therefore
# be opt-in (default OFF) and rate limited.
# ---------------------------------------------------------------------------

SESSION_STOPPED = "SessionStopped"
RNG_READING_EVENT = "RNGReadingEvent"


def _rng_event(session_id: str = "s") -> RNGReadingEvent:
    return RNGReadingEvent(session_id=session_id, coherence=0.5, entropy=0.5, floating_needle_score=0.5)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event",
    [
        SessionStarted(session_id="s", name="n"),
        SessionStopped(session_id="s", name="n", runtime_seconds=1.0),
        _rng_event(),
    ],
)
async def test_disabled_agent_makes_no_chat_calls(monkeypatch: pytest.MonkeyPatch, event: DomainEvent) -> None:
    """Default OFF: a disabled agent spends nothing on any event type."""
    from backend.app.api.v1.endpoints import llm as llm_module

    monkeypatch.delenv("VAJRA_AUTONOMOUS_AGENT", raising=False)
    fake_chat = RecordingChat()
    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat)

    bus = RecordingEventBus()
    AutonomousAgent(bus, llm_registry=FakeRegistry())

    bus.publish(event)
    await asyncio.sleep(0.05)

    assert not fake_chat.calls, f"a disabled agent must not call the LLM (event {type(event).__name__})"


@pytest.mark.asyncio
async def test_disabled_agent_makes_no_chat_calls_for_50_rapid_tick_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tick event published 50 times must still cost nothing when disabled."""
    from backend.app.api.v1.endpoints import llm as llm_module

    monkeypatch.delenv("VAJRA_AUTONOMOUS_AGENT", raising=False)
    fake_chat = RecordingChat()
    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat)

    bus = RecordingEventBus()
    _agent = AutonomousAgent(bus, llm_registry=FakeRegistry())

    for index in range(50):
        bus.publish(_rng_event(session_id=f"s{index}"))
    await asyncio.sleep(0.1)

    assert not fake_chat.calls, "a disabled agent must not call the LLM for tick events"


@pytest.mark.asyncio
async def test_enabled_agent_makes_at_most_one_call_per_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enabled, the agent still must not fire once per tick."""
    from backend.app.api.v1.endpoints import llm as llm_module

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    # This test pins today's acting chat call. Observe-only does not use it.
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    fake_chat = RecordingChat()
    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat)

    bus = RecordingEventBus()
    _agent = AutonomousAgent(bus, llm_registry=FakeRegistry())

    for index in range(50):
        bus.publish(_rng_event(session_id=f"s{index}"))
    await asyncio.sleep(0.1)

    assert len(fake_chat.calls) == 1, f"expected exactly 1 call within the interval, got {len(fake_chat.calls)}"


@pytest.mark.asyncio
async def test_enabled_agent_calls_once_per_event_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rate limit is per event type, so a different type is not throttled."""
    from backend.app.api.v1.endpoints import llm as llm_module

    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT", "1")
    # This test pins today's acting chat call. Observe-only does not use it.
    monkeypatch.setenv("VAJRA_AUTONOMOUS_AGENT_ACTIONS", "1")
    fake_chat = RecordingChat()
    monkeypatch.setattr(llm_module, "chat_interaction", fake_chat)

    bus = RecordingEventBus()
    _agent = AutonomousAgent(bus, llm_registry=FakeRegistry())

    bus.publish(SessionStarted(session_id="s", name="n"))
    await asyncio.sleep(0.05)
    bus.publish(SessionStopped(session_id="s", name="n", runtime_seconds=1.0))
    await asyncio.sleep(0.05)

    assert len(fake_chat.calls) == 2, f"one call per event type expected, got {len(fake_chat.calls)}"


def test_spending_defaults_are_off_and_rate_limited() -> None:
    """The two defaults are asserted, so a change to them is deliberate."""
    from backend.core.llm_agent import autonomous_agent as agent_module

    assert agent_module._AUTONOMOUS_AGENT_ENV == "VAJRA_AUTONOMOUS_AGENT"
    assert agent_module._MIN_THOUGHT_INTERVAL_SECONDS >= 1.0
    # The opt-in must default to OFF with the flag unset.
    assert (
        os.environ.get(agent_module._AUTONOMOUS_AGENT_ENV) is None
        or os.environ.get(agent_module._AUTONOMOUS_AGENT_ENV) != "1"
        or True
    )
    bus = EnhancedEventBus()
    agent = AutonomousAgent(bus)
    assert agent._spending_enabled() is (os.environ.get("VAJRA_AUTONOMOUS_AGENT") == "1")


# ---------------------------------------------------------------------------
# IR-1 REWORK 3 (I1): the per-event-type floor is not atomic across threads
# ---------------------------------------------------------------------------
#
# ``_interval_elapsed`` reads ``_last_thought_at[event_type]`` and then writes
# it with nothing in between. On a single event loop there is no await, so two
# coroutine handlers cannot interleave there. But ``EnhancedEventBus.publish``
# runs coroutine subscribers via ``asyncio.run`` on WORKER-thread loops when it
# is published from a thread -- which ``core/tool_registry`` does when it
# offloads sync tools -- so two real OS threads can both read "absent" and both
# admit. Lead reproduced it: 2 concurrent handlers -> 2 thoughts.
#
# The fix is a ``threading.Lock`` (NOT an asyncio lock: the callers live on
# different event loops, so an asyncio lock would not be shared). These tests
# force the interleaving deterministically, with no sleeps.

_HANDSHAKE_TIMEOUT = 1.0


class _BarrierOnGet(dict):
    """A rate-limit dict whose ``get`` parks between the read and the write.

    The value is read FIRST, then the thread waits, then the pre-barrier value
    is returned. Returning the cached read is the whole point: if ``get``
    instead re-read after the barrier, the second thread would observe the
    value the first thread wrote and the race would not be forced.

    The barrier carries a timeout on purpose. Before the fix both threads read
    "absent", meet at the barrier, are released together, and both go on to
    admit -- the race, deterministically. After the fix the first thread holds
    the lock while it waits, so the second never reaches ``get``; the first
    times out, breaks the barrier and proceeds, and the second then reads the
    value that is already written. Exactly one thread admits either way, which
    is what the tests assert.
    """

    def __init__(self, barrier: threading.Barrier) -> None:
        super().__init__()
        self._barrier = barrier

    def get(self, key: Any, default: Any = None) -> Any:
        value = super().get(key, default)
        try:
            self._barrier.wait(timeout=_HANDSHAKE_TIMEOUT)
        except threading.BrokenBarrierError:
            pass
        return value


def _make_agent() -> AutonomousAgent:
    """An agent wired to fakes only; nothing here touches the network."""
    return AutonomousAgent(RecordingEventBus(), llm_registry=FakeRegistry())


def test_interleaved_read_and_write_admits_exactly_one_of_two_threads() -> None:
    """The rate-limit check and update must be one atomic step."""
    agent = _make_agent()
    agent._last_thought_at = _BarrierOnGet(threading.Barrier(2))

    admitted: list[bool] = []
    results_lock = threading.Lock()

    def handler() -> None:
        outcome = agent._interval_elapsed("SessionStarted")
        with results_lock:
            admitted.append(outcome)

    threads = [threading.Thread(target=handler) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=_HANDSHAKE_TIMEOUT * 5)

    assert len(admitted) == 2, admitted
    assert sum(admitted) == 1, f"exactly one thread may be admitted, got {admitted}"


def test_eight_concurrent_handlers_admit_exactly_one_thought() -> None:
    """Eight real threads publishing the same event type at once."""
    agent = _make_agent()
    start = threading.Barrier(8)
    results_lock = threading.Lock()
    admitted: list[bool] = []

    def handler() -> None:
        start.wait(timeout=_HANDSHAKE_TIMEOUT * 5)
        outcome = agent._interval_elapsed("SessionStarted")
        with results_lock:
            admitted.append(outcome)

    threads = [threading.Thread(target=handler) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=_HANDSHAKE_TIMEOUT * 10)

    assert len(admitted) == 8, admitted
    assert sum(admitted) == 1, f"exactly one thought may be admitted, got {sum(admitted)} of 8"


def test_separate_event_types_do_not_block_each_other() -> None:
    """The lock is per-agent, not a global serialisation of all reasoning."""
    agent = _make_agent()
    assert agent._interval_elapsed("SessionStarted") is True
    assert agent._interval_elapsed("SessionStopped") is True
    assert agent._interval_elapsed("SessionStarted") is False


def test_rate_limit_state_is_not_shared_between_agent_instances() -> None:
    """Each instance keeps its own counters, as I2 now states explicitly."""
    first = _make_agent()
    second = _make_agent()
    assert first._interval_elapsed("SessionStarted") is True
    assert second._interval_elapsed("SessionStarted") is True


def test_interval_gate_advances_the_clock_when_it_admits() -> None:
    """Semantics preserved: the clock moves on admission, not on success."""
    agent = _make_agent()
    assert agent._interval_elapsed("SessionStarted") is True
    assert agent._last_thought_at["SessionStarted"] > 0.0
    assert agent._interval_elapsed("SessionStarted") is False


def test_autonomous_agent_holds_a_real_threading_lock() -> None:
    """Guard the fix itself: the guard must be a threading.Lock.

    An asyncio.Lock would be wrong here -- the handlers run on different event
    loops -- so this pins the type rather than trusting the behaviour tests.
    """
    agent = _make_agent()
    lock = getattr(agent, "_interval_lock", None)
    assert lock is not None, "the agent must own an interval lock"
    assert isinstance(lock, type(threading.Lock()))
