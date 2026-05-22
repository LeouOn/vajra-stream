"""
Radionics Module
Adapter wrapping core.integrated_scalar_radionics
"""

import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.integrated_scalar_radionics import BroadcastConfiguration, IntegratedScalarRadionicsBroadcaster, IntentionType
from modules.interfaces import EventBus, RadionicsBroadcaster


class RadionicsService(RadionicsBroadcaster):
    """Radionics broadcasting service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self.broadcaster = IntegratedScalarRadionicsBroadcaster()

    def broadcast_healing(
        self, target_name: str, duration_minutes: int = 10, frequency_hz: float = 528.0, intensity: float = 0.8
    ) -> dict[str, Any]:
        """Broadcast healing to target"""

        BroadcastConfiguration(
            intention=IntentionType.HEALING,
            target_count=1,
            duration_seconds=duration_minutes * 60,
            scalar_intensity=intensity,
            frequency_hz=frequency_hz,
            mantra="Om Mani Padme Hum",
            use_chakras=True,
        )

        return {
            "session_id": str(uuid.uuid4()),
            "target": target_name,
            "frequency_hz": frequency_hz,
            "duration_minutes": duration_minutes,
            "status": "active",
        }

    def broadcast_liberation(
        self, event_name: str, souls_count: int = 1000, duration_minutes: int = 108
    ) -> dict[str, Any]:
        """Broadcast liberation protocol"""

        BroadcastConfiguration(
            intention=IntentionType.LIBERATION,
            target_count=souls_count,
            duration_seconds=duration_minutes * 60,
            scalar_intensity=1.0,
            frequency_hz=396,  # Liberation frequency
            mantra="Namo Amitabha Buddha",
            use_chakras=True,
            use_meridians=True,
        )

        return {
            "session_id": str(uuid.uuid4()),
            "event": event_name,
            "souls_count": souls_count,
            "frequency_hz": 396,
            "duration_minutes": duration_minutes,
            "status": "active",
        }

    def get_available_intentions(self) -> list[dict[str, Any]]:
        """Get list of available intention types"""
        return [
            {"id": "healing", "name": "Healing", "frequency": 528},
            {"id": "liberation", "name": "Liberation", "frequency": 396},
            {"id": "empowerment", "name": "Empowerment", "frequency": 528},
            {"id": "protection", "name": "Protection", "frequency": 741},
            {"id": "peace", "name": "Peace", "frequency": 852},
            {"id": "love", "name": "Love", "frequency": 528},
            {"id": "wisdom", "name": "Wisdom", "frequency": 963},
        ]

    def get_sacred_frequencies(self) -> dict[str, list[dict[str, Any]]]:
        """Get sacred frequency mappings"""
        return {
            "solfeggio": [
                {"hz": 396, "name": "Liberation from Guilt & Fear"},
                {"hz": 417, "name": "Undoing Situations"},
                {"hz": 528, "name": "DNA Repair, Love"},
                {"hz": 639, "name": "Connecting Relationships"},
                {"hz": 741, "name": "Awakening Intuition"},
                {"hz": 852, "name": "Spiritual Order"},
                {"hz": 963, "name": "Divine Consciousness"},
            ],
            "planetary": [
                {"hz": 136.10, "name": "Earth (OM)"},
                {"hz": 126.22, "name": "Sun"},
                {"hz": 210.42, "name": "Moon"},
            ],
        }
