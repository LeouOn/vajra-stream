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

    @patch("time.sleep")
    def test_continuous_spinning(self, mock_sleep):
        svc = PrayerWheelService()
        svc.wheel.audio = MagicMock()
        
        result = svc.continuous_spinning(mantras=["Om Mani Padme Hum"], duration_minutes=1)
        assert result["status"] == "success"
        assert "session_id" in result
        
        # Clean up threads
        if hasattr(svc.wheel, "_active_spins"):
            for s_id, info in list(svc.wheel._active_spins.items()):
                info["stop_event"].set()
