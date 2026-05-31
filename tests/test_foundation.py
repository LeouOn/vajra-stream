import pytest

import config.settings as settings
from infrastructure.event_bus import DomainEvent, EnhancedEventBus
from modules.blessing_router import BlessingRouted, BlessingRouter, DeliveryMethod, TargetSpecification, TargetType
from modules.crystal import CrystalBroadcastCompleted, CrystalBroadcastStarted, CrystalService
from modules.enhanced_scalar_waves import EnhancedScalarWaveService, WaveSessionStarted


@pytest.mark.unit
class TestEventBusPersistence:
    def test_publish_and_subscribe(self, event_bus, tmp_path):
        path = tmp_path / "test_events.jsonl"
        bus = EnhancedEventBus(persistence_path=str(path))

        class TestEvent(DomainEvent):
            def __init__(self, message: str):
                super().__init__()
                self.message = message

        received = []
        bus.subscribe(TestEvent, lambda e: received.append(e))
        bus.publish(TestEvent("Hello World"))

        assert len(received) == 1
        assert received[0].message == "Hello World"
        assert path.exists()

        content = path.read_text()
        assert "Hello World" in content


@pytest.mark.unit
class TestCrystalService:
    def test_broadcast_intention(self, event_bus):
        service = CrystalService(event_bus)

        events = []
        event_bus.subscribe(CrystalBroadcastStarted, lambda e: events.append(e))
        event_bus.subscribe(CrystalBroadcastCompleted, lambda e: events.append(e))

        result = service.broadcast_intention("Healing Light", duration=1)

        assert result["status"] == "completed"
        assert len(events) == 2
        assert isinstance(events[0], CrystalBroadcastStarted)
        assert isinstance(events[1], CrystalBroadcastCompleted)
        assert events[0].intention == "Healing Light"


@pytest.mark.unit
class TestBlessingRouter:
    def test_route_blessing(self, event_bus):
        router = BlessingRouter(event_bus)

        events = []
        event_bus.subscribe(BlessingRouted, lambda e: events.append(e))

        target = TargetSpecification(TargetType.INDIVIDUAL, "John Doe")
        router.route_blessing("Peace", target, DeliveryMethod.DIRECT)

        assert len(events) == 1
        assert isinstance(events[0], BlessingRouted)
        assert events[0].intention == "Peace"
        assert events[0].target_spec.identifier == "John Doe"


@pytest.mark.unit
class TestEnhancedScalarWaves:
    def test_create_wave_session(self, event_bus):
        service = EnhancedScalarWaveService(event_bus)

        events = []
        event_bus.subscribe(WaveSessionStarted, lambda e: events.append(e))

        session_id = service.create_wave_session("lorenz", count=100)

        assert session_id is not None
        assert len(events) == 1
        assert isinstance(events[0], WaveSessionStarted)
        assert events[0].session_id == session_id


@pytest.mark.unit
class TestConfiguration:
    def test_default_config(self):
        assert settings.SAMPLE_RATE == 44100
        assert settings.HARDWARE_LEVEL in [2, 3]
