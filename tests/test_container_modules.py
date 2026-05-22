from pathlib import Path

import pytest


@pytest.mark.integration
class TestScalarWaves:
    def test_generate_qrng(self, fresh_container):
        scalar = fresh_container.scalar_waves
        result = scalar.generate("qrng", 1000, 1.0)
        assert result["count"] > 0
        assert result["method"] == "qrng"
        assert "mops" in result

    def test_thermal_status(self, fresh_container):
        scalar = fresh_container.scalar_waves
        thermal = scalar.get_thermal_status()
        assert "temperature" in thermal
        assert "status" in thermal


@pytest.mark.integration
class TestRadionics:
    def test_available_intentions(self, fresh_container):
        radionics = fresh_container.radionics
        intentions = radionics.get_available_intentions()
        assert len(intentions) > 0

    def test_broadcast_healing(self, fresh_container):
        radionics = fresh_container.radionics
        result = radionics.broadcast_healing("Test Target", 1, 528)
        assert "session_id" in result
        assert result["target"] == "Test Target"


@pytest.mark.integration
class TestAnatomy:
    def test_chakra_info(self, fresh_container):
        anatomy = fresh_container.anatomy
        chakras = anatomy.get_chakra_info()
        assert len(chakras) == 7

    def test_meridian_info(self, fresh_container):
        anatomy = fresh_container.anatomy
        meridians = anatomy.get_meridian_info()
        assert len(meridians) == 12

    def test_visualize_chakras(self, fresh_container, tmp_output_dir):
        anatomy = fresh_container.anatomy
        path = anatomy.visualize_chakras(width=800, height=1000, output_path=str(tmp_output_dir / "chakras.png"))
        assert Path(path).exists()


@pytest.mark.integration
class TestBlessings:
    def test_generate_blessing(self, fresh_container):
        blessings = fresh_container.blessings
        result = blessings.generate_blessing("All Beings", "peace and happiness", "universal")
        assert "blessing_text" in result
        assert len(result["blessing_text"]) > 0

    def test_available_traditions(self, fresh_container):
        blessings = fresh_container.blessings
        traditions = blessings.get_available_traditions()
        assert len(traditions) > 0


@pytest.mark.integration
class TestEventBus:
    def test_publish_and_receive(self, fresh_container):
        from modules.interfaces import ScalarWavesGenerated
        from datetime import datetime

        events = []
        fresh_container.event_bus.subscribe(ScalarWavesGenerated, lambda e: events.append(e))

        event = ScalarWavesGenerated(
            timestamp=datetime.now(),
            event_id="test-123",
            method="qrng",
            count=1000,
            mops=1.5,
        )
        fresh_container.event_bus.publish(event)

        assert len(events) == 1
        assert events[0].method == "qrng"

        fresh_container.event_bus.unsubscribe(ScalarWavesGenerated, events.append)
