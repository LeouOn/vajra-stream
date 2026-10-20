"""IR-3: domain events are constructible and actually published.

RED-first regression tests for the defect where ``DomainEvent`` had two
REQUIRED fields (``timestamp``, ``event_id``), so every construction that
omitted them raised ``TypeError`` and the publish was swallowed by a bare
``except Exception: pass``. The events were therefore never delivered, and the
listeners that depend on them never fired.

No database, no network, no audio: the service is exercised with fakes and a
recording bus, and the only real event bus used is ``infrastructure.event_bus``
with a stand-in handler.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone

import pytest

from modules import interfaces
from modules.interfaces import (
    BlessingGenerated,
    BroadcastStarted,
    BroadcastStopped,
    DomainEvent,
    HealingBroadcastStarted,
    HealingSessionCompleted,
    HealingSessionStarted,
    RecitationCompleted,
    RecitationStarted,
    RNGReadingEvent,
    ScalarWavesGenerated,
    SessionCreated,
    SessionStarted,
    SessionStopped,
)

# Every concrete event in modules/interfaces.py, with the minimum own fields
# each one needs. Anything added to modules/interfaces.py later must be added
# here too, which is the point: a new event that cannot be built is a new bug.
EVENT_CASES: list[tuple[type, dict]] = [
    (HealingSessionStarted, {"target_name": "t", "intention": "i", "duration_minutes": 1}),
    (
        HealingBroadcastStarted,
        {"target_name": "t", "frequency_hz": 136.1, "frequencies": [136.1], "duration_minutes": 1},
    ),
    (HealingSessionCompleted, {"session_id": "s", "summary": "x", "key_insights": {}}),
    (RecitationStarted, {"intention": "i", "session_id": "s"}),
    (RecitationCompleted, {"session_id": "s", "cycles_completed": 1, "total_recited": 1, "dedication_text": "d"}),
    (ScalarWavesGenerated, {"method": "bagua", "count": 8, "generation_seconds": 1.0}),
    (BlessingGenerated, {"target_name": "t", "blessing_text": "b", "tradition": "vajra"}),
    (SessionCreated, {"session_id": "s", "name": "n", "intention": "i", "duration": 1, "audio_frequency": 136.1}),
    (SessionStarted, {"session_id": "s", "name": "n"}),
    (SessionStopped, {"session_id": "s", "name": "n", "runtime_seconds": 1.0}),
    (BroadcastStarted, {"session_id": "s", "hardware_level": 0, "frequencies": [136.1]}),
    (BroadcastStopped, {"session_id": "s", "actual_runtime": 1.0}),
    (RNGReadingEvent, {"session_id": "s", "coherence": 0.5, "entropy": 0.5, "floating_needle_score": 0.5}),
]


def _own_fields(event_cls: type) -> list[str]:
    """Field names a subclass adds itself (i.e. not the inherited base ones)."""
    base = {f.name for f in dataclasses.fields(DomainEvent)}
    return [f.name for f in dataclasses.fields(event_cls) if f.name not in base]


@pytest.mark.parametrize(("event_cls", "own"), EVENT_CASES, ids=[c.__name__ for c, _ in EVENT_CASES])
def test_every_event_is_constructible_from_its_own_fields(event_cls: type, own: dict) -> None:
    """An event must be buildable from only its own fields, and self-identify."""
    event = event_cls(**own)
    assert isinstance(event, DomainEvent)
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo is not None, "timestamps must be timezone-aware"
    assert isinstance(event.event_id, str) and event.event_id
    assert own  # sanity: the case really carries the subclass's own fields


def test_event_ids_are_unique_per_instance() -> None:
    """Two events built the same way must not share an id."""
    a = SessionStarted(session_id="s", name="n")
    b = SessionStarted(session_id="s", name="n")
    assert a.event_id != b.event_id
    assert uuid.UUID(a.event_id)  # a real uuid, not a placeholder


def test_explicit_timestamp_and_event_id_are_still_honoured() -> None:
    """Callers that pass the base fields explicitly keep full control."""
    stamp = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    event = SessionStarted(session_id="s", name="n", timestamp=stamp, event_id="fixed-id")
    assert event.timestamp == stamp
    assert event.event_id == "fixed-id"


def test_base_fields_are_keyword_only_so_subclass_order_is_free() -> None:
    """Subclass fields stay positional; the base's become keyword-only.

    This is what lets the base carry defaults without making every subclass
    'non-default argument follows default argument'.
    """
    event = SessionStarted("s", "n")  # subclass fields positional
    assert event.session_id == "s" and event.name == "n"
    with pytest.raises(TypeError):
        SessionStarted("s", "n", "positional-event-id")  # type: ignore[misc]


def test_domain_event_base_is_constructible_on_its_own() -> None:
    """The base class itself is usable, not just its subclasses."""
    event = DomainEvent()
    assert isinstance(event.timestamp, datetime)
    assert event.event_id


class RecordingBus:
    """Minimal event bus that records what it is asked to publish."""

    def __init__(self, *, fail: bool = False) -> None:
        self.published: list[object] = []
        self.fail = fail

    def publish(self, event: object) -> None:
        if self.fail:
            raise RuntimeError("bus is down")
        self.published.append(event)

    def types(self) -> list[type]:
        return [type(e) for e in self.published]


def _make_service(monkeypatch: pytest.MonkeyPatch, bus: object) -> object:
    """VajraStreamService with every heavy dependency faked out."""
    import backend.core.services.vajra_service as svc

    for symbol in (
        "Settings",
        "EnhancedAudioGenerator",
        "PrayerBowlGenerator",
        "Level2CrystalBroadcaster",
        "Level3CrystalBroadcaster",
        "PrayerWheel",
        "AstrologicalCalculator",
        "LLMIntegration",
        "TTSEngine",
        "RothkoGenerator",
        "VisualRenderer",
    ):
        monkeypatch.setattr(svc, symbol, None, raising=False)

    monkeypatch.setattr(svc.VajraStreamService, "_load_history", lambda self: None)
    monkeypatch.setattr(svc.VajraStreamService, "_save_history", lambda self: None)

    service = svc.VajraStreamService()
    service.event_bus = bus

    async def _fake_audio(self, audio_config):  # noqa: ANN001
        return [0.0, 0.0]

    async def _fake_broadcast(self, audio_data):  # noqa: ANN001
        return None

    async def _fake_visuals(self, audio_data):  # noqa: ANN001
        return None

    monkeypatch.setattr(svc.VajraStreamService, "generate_prayer_bowl_audio", _fake_audio)
    monkeypatch.setattr(svc.VajraStreamService, "broadcast_audio", _fake_broadcast)
    monkeypatch.setattr(svc.VajraStreamService, "_generate_visuals", _fake_visuals)
    monkeypatch.setattr(svc.VajraStreamService, "_start_broadcast_loop", lambda self: None)
    monkeypatch.setattr(svc.VajraStreamService, "_begin_session_operation", lambda self, *a, **k: None)
    monkeypatch.setattr(svc.VajraStreamService, "_end_session_operation", lambda self, *a, **k: None)
    return service


@pytest.mark.asyncio
async def test_service_publishes_the_session_lifecycle_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """create -> SessionCreated, start -> SessionStarted + BroadcastStarted, stop -> SessionStopped."""
    bus = RecordingBus()
    service = _make_service(monkeypatch, bus)

    session_id = await service.create_session(
        name="n", intention="i", duration=1, audio_frequency=136.1, astrology_enabled=False
    )
    assert bus.types() == [SessionCreated], "create_session must publish exactly SessionCreated"

    await service.start_session(session_id)
    assert bus.types() == [SessionCreated, SessionStarted, BroadcastStarted]

    await service.stop_session(session_id)
    assert bus.types() == [SessionCreated, SessionStarted, BroadcastStarted, SessionStopped]


@pytest.mark.asyncio
async def test_published_events_carry_an_id_and_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What reaches the bus is a fully formed event, not a half-built one."""
    bus = RecordingBus()
    service = _make_service(monkeypatch, bus)
    session_id = await service.create_session(
        name="n", intention="i", duration=1, audio_frequency=136.1, astrology_enabled=False
    )
    await service.start_session(session_id)
    for event in bus.published:
        assert isinstance(event, DomainEvent)
        assert event.event_id
        assert isinstance(event.timestamp, datetime) and event.timestamp.tzinfo is not None


def test_real_event_bus_delivers_a_domain_event_to_a_handler() -> None:
    """A REAL infrastructure.event_bus delivers BroadcastStarted to a subscriber.

    The MOPS engine is not run: this only proves the bus itself routes a
    modules.interfaces event to a subscribed handler.
    """
    from infrastructure.event_bus import EnhancedEventBus

    # No persistence_path: this must not write any file.
    bus = EnhancedEventBus()
    seen: list[object] = []

    def handler(event: object) -> None:
        seen.append(event)

    bus.subscribe(BroadcastStarted, handler)
    bus.publish(BroadcastStarted(session_id="s", hardware_level=0, frequencies=[136.1]))

    assert len(seen) == 1, "the subscriber must receive the event"
    assert isinstance(seen[0], BroadcastStarted)
    assert seen[0].session_id == "s"


@pytest.mark.asyncio
async def test_a_failing_publish_is_logged_not_swallowed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A broken bus must leave a trace instead of failing silently."""
    bus = RecordingBus(fail=True)
    service = _make_service(monkeypatch, bus)

    with caplog.at_level("WARNING"):
        await service.create_session(
            name="n", intention="i", duration=1, audio_frequency=136.1, astrology_enabled=False
        )

    assert caplog.records, "a failed publish must be logged as a warning"
    assert any(record.levelname == "WARNING" for record in caplog.records)
    assert any(
        "publish" in record.getMessage().lower() for record in caplog.records
    ), f"the warning should name the failed publish: {[r.getMessage() for r in caplog.records]}"


def test_every_event_class_in_interfaces_is_covered() -> None:
    """Guard the table above against new events appearing in modules/interfaces.py."""
    defined = {
        obj
        for obj in vars(interfaces).values()
        if isinstance(obj, type) and issubclass(obj, DomainEvent) and obj is not DomainEvent
    }
    covered = {cls for cls, _ in EVENT_CASES}
    assert defined == covered, f"events not covered by EVENT_CASES: {sorted(defined - covered)}"
