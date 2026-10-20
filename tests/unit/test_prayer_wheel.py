"""
Unit tests for the modular Prayer Wheel Service wrapper
"""

from unittest.mock import MagicMock, patch

import pytest

from modules.prayer_wheel import PrayerWheelService


@pytest.mark.unit
class TestPrayerWheelService:
    def test_service_initialization(self):
        svc = PrayerWheelService()
        assert svc.get_status()["prayer_wheel"] is True
        assert svc.get_status()["available_mantras"] > 0

    def test_get_traditional_mantras(self):
        svc = PrayerWheelService()
        mantras = svc.get_traditional_mantras()
        assert len(mantras) > 0
        assert "mantra" in mantras[0]

    def test_generate_prayer(self):
        svc = PrayerWheelService()
        # Mock LLM to test fallback
        svc.wheel.llm = None
        prayer = svc.generate_prayer("compassion", use_llm=False)
        assert prayer == "Om Mani Padme Hum"

        prayer_wisdom = svc.generate_prayer("wisdom", use_llm=False)
        assert prayer_wisdom == "Om Ah Ra Pa Tsa Na Dhih"

        prayer_general = svc.generate_prayer("general_intention_xyz", use_llm=False)
        assert len(prayer_general) > 0

    @patch("time.sleep")
    def test_spin_wheel(self, mock_sleep):
        svc = PrayerWheelService()
        # Mock audio play to avoid PortAudio issues
        svc.wheel.audio = MagicMock()

        result = svc.spin_wheel(mantra="Om Mani Padme Hum", rotations=10, speed=1.0)
        assert result["status"] == "success"
        assert result["mantra"] == "Om Mani Padme Hum"
        assert result["rotations"] == 10
        assert result["duration"] == 5

        # Join the background spin inside the patched clock, otherwise it is
        # still sleeping on the real one after this test returns.
        for spin_thread in list(svc._spin_threads):
            spin_thread.join(timeout=5)
            assert not spin_thread.is_alive()

    @patch("time.sleep")
    def test_spin_wheel_thread_does_not_block_shutdown(self, mock_sleep):
        """A spin outlives its request, but must never hold the process open."""
        svc = PrayerWheelService()
        svc.wheel.audio = MagicMock()

        result = svc.spin_wheel(mantra="Om Mani Padme Hum", rotations=10, speed=1.0)
        assert result["status"] == "success"

        assert len(svc._spin_threads) == 1
        spin_thread = svc._spin_threads[0]
        assert spin_thread.daemon is True

        spin_thread.join(timeout=5)
        assert not spin_thread.is_alive()

        # A finished spin is dropped, so repeated spins cannot pile up handles.
        svc.spin_wheel(mantra="Om Mani Padme Hum", rotations=10, speed=1.0)
        assert len(svc._spin_threads) == 1
        assert svc._spin_threads[0] is not spin_thread
        svc._spin_threads[0].join(timeout=5)

    @patch("time.sleep")
    def test_continuous_spinning(self, mock_sleep):
        svc = PrayerWheelService()
        svc.wheel.audio = MagicMock()

        result = svc.continuous_spinning(mantras=["Om Mani Padme Hum"], duration_minutes=1)
        assert result["status"] == "success"
        assert "session_id" in result

        # Stop the background loop *and wait for it*. Setting the stop event
        # alone leaves spin_loop calling spin() -- on the real time.sleep and
        # the real audio object -- after this test has returned.
        spins = list(getattr(svc.wheel, "_active_spins", {}).values())
        assert spins
        for info in spins:
            info["stop_event"].set()
            info["thread"].join(timeout=5)
            assert not info["thread"].is_alive()
