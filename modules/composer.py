"""
Intelligent Composer Module
Wraps intelligent music composition functionality
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class ComposerService:
    """Intelligent music composition service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._composer = None

    @property
    def composer(self):
        """Get intelligent composer"""
        if self._composer is None:
            try:
                from core.intelligent_composer import IntelligentComposer
                self._composer = IntelligentComposer()
            except ImportError:
                self._composer = None
        return self._composer

    def compose_healing_music(
        self,
        intention: str = "healing",
        duration_seconds: int = 300,
        base_frequency: float = 528.0,
        style: str = "ambient"
    ) -> Dict[str, Any]:
        """Compose healing music"""
        if self.composer is None:
            return {'error': 'Composer not available'}

        try:
            composition = self.composer.compose(
                intention=intention,
                duration=duration_seconds,
                base_freq=base_frequency,
                style=style
            )
            return {
                'status': 'success',
                'intention': intention,
                'duration_seconds': duration_seconds,
                'base_frequency': base_frequency,
                'composition': composition
            }
        except Exception as e:
            return {'error': str(e)}

    def generate_frequency_sequence(
        self,
        frequencies: List[float],
        duration_per_frequency: float = 60.0
    ) -> Dict[str, Any]:
        """Generate a sequence of healing frequencies"""
        if self.composer is None:
            return {'error': 'Composer not available'}

        try:
            sequence = self.composer.create_sequence(
                frequencies=frequencies,
                duration_each=duration_per_frequency
            )
            return {
                'status': 'success',
                'frequencies': frequencies,
                'total_duration': len(frequencies) * duration_per_frequency,
                'sequence': sequence
            }
        except Exception as e:
            return {'error': str(e)}

    def create_solfeggio_progression(
        self,
        include_frequencies: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Create a Solfeggio frequency progression"""
        all_solfeggio = [396, 417, 528, 639, 741, 852, 963]
        frequencies = include_frequencies or all_solfeggio

        return self.generate_frequency_sequence(
            frequencies=[float(f) for f in frequencies],
            duration_per_frequency=90.0  # 1.5 minutes each
        )

    def compose_meditation_soundscape(
        self,
        meditation_type: str = "mindfulness",
        duration_minutes: int = 20
    ) -> Dict[str, Any]:
        """Create a meditation soundscape"""
        if self.composer is None:
            return {'error': 'Composer not available'}

        # Map meditation types to frequencies
        frequency_map = {
            'mindfulness': 432.0,      # Natural tuning
            'loving-kindness': 528.0,  # Love frequency
            'transcendental': 963.0,   # Divine consciousness
            'deep_relaxation': 7.83,   # Schumann resonance
            'focus': 40.0              # Gamma waves
        }

        base_freq = frequency_map.get(meditation_type, 432.0)

        return self.compose_healing_music(
            intention=f"{meditation_type} meditation",
            duration_seconds=duration_minutes * 60,
            base_frequency=base_freq,
            style="ambient"
        )

    def get_available_styles(self) -> List[str]:
        """Get available composition styles"""
        return [
            'ambient',
            'drone',
            'rhythmic',
            'melodic',
            'binaural',
            'isochronic',
            'nature_sounds'
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get composer status"""
        return {
            'composer': self.composer is not None,
            'available_styles': self.get_available_styles()
        }
