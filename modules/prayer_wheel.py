"""
Prayer Wheel Module - Adapter Wrapper
Wraps core.prayer_wheel.PrayerWheel with EventBus integration
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class PrayerWheelService:
    """
    Digital prayer wheel service adapter.
    Wraps core.prayer_wheel.PrayerWheel with event bus integration.
    """

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._wheel = None

    @property
    def wheel(self):
        """Get prayer wheel instance (lazy loading)"""
        if self._wheel is None:
            try:
                from core.prayer_wheel import PrayerWheel
                self._wheel = PrayerWheel()
            except ImportError:
                self._wheel = None
        return self._wheel

    def spin_wheel(
        self,
        mantra: str = "Om Mani Padme Hum",
        rotations: int = 108,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """Spin the prayer wheel"""
        if self.wheel is None:
            return {'error': 'Prayer wheel not available'}

        try:
            result = self.wheel.spin(
                mantra=mantra,
                rotations=rotations,
                speed=speed
            )
            return {
                'status': 'success',
                'mantra': mantra,
                'rotations': rotations,
                'merit_generated': result.get('merit', rotations * len(mantra))
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_prayer(self, intention: str = "peace", use_llm: bool = True,
                        tradition: str = 'universal') -> str:
        """Generate a prayer based on intention"""
        if self.wheel is None:
            return "Prayer wheel not available"
        return self.wheel.generate_prayer(intention, use_llm, tradition)

    def continuous_spinning(
        self,
        mantras: List[str],
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """Start continuous prayer wheel spinning"""
        if self.wheel is None:
            return {'error': 'Prayer wheel not available'}

        try:
            session = self.wheel.continuous_spin(
                mantras=mantras,
                duration_minutes=duration_minutes
            )
            return {
                'status': 'success',
                'mantras': mantras,
                'duration_minutes': duration_minutes,
                'session_id': session.get('session_id', 'unknown')
            }
        except Exception as e:
            return {'error': str(e)}

    def get_traditional_mantras(self) -> List[Dict[str, str]]:
        """Get list of traditional mantras"""
        if self.wheel is None:
            return DEFAULT_MANTRAS
        return [
            {'mantra': m, 'tradition': 'tibetan', 'benefit': 'general'}
            for m in self.wheel.traditional_prayers.get('mantras', [])
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get prayer wheel status"""
        return {
            'prayer_wheel': self.wheel is not None,
            'available_mantras': len(self.get_traditional_mantras())
        }


DEFAULT_MANTRAS = [
    {'mantra': 'Om Mani Padme Hum', 'tradition': 'Tibetan Buddhist', 'deity': 'Chenrezig', 'benefit': 'Compassion'},
    {'mantra': 'Om Tare Tuttare Ture Soha', 'tradition': 'Tibetan Buddhist', 'deity': 'Green Tara', 'benefit': 'Protection'},
    {'mantra': 'Om Ah Ra Pa Tsa Na Dhih', 'tradition': 'Buddhist', 'deity': 'Manjushri', 'benefit': 'Wisdom'},
]
