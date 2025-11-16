"""
Healing Systems Module
Wraps comprehensive healing systems functionality
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class HealingService:
    """Comprehensive healing systems service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._healing_systems = None

    @property
    def healing_systems(self):
        """Get healing systems"""
        if self._healing_systems is None:
            try:
                from core.healing_systems import HealingSystems
                self._healing_systems = HealingSystems()
            except ImportError:
                self._healing_systems = None
        return self._healing_systems

    def create_healing_session(
        self,
        target_name: str,
        modalities: Optional[List[str]] = None,
        duration_minutes: int = 60,
        intention: str = "complete healing"
    ) -> Dict[str, Any]:
        """Create a comprehensive healing session"""
        if self.healing_systems is None:
            return {'error': 'Healing systems not available'}

        if modalities is None:
            modalities = [
                'scalar_waves',
                'radionics',
                'chakra_balancing',
                'meridian_clearing',
                'blessing'
            ]

        try:
            session = self.healing_systems.create_session(
                target=target_name,
                modalities=modalities,
                duration=duration_minutes,
                intention=intention
            )
            return {
                'status': 'success',
                'target': target_name,
                'modalities': modalities,
                'duration_minutes': duration_minutes,
                'intention': intention,
                'session_id': session.get('session_id', 'unknown')
            }
        except Exception as e:
            return {'error': str(e)}

    def chakra_balancing_protocol(
        self,
        target_name: str,
        chakras: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run chakra balancing protocol"""
        if chakras is None:
            chakras = [
                'muladhara', 'svadhisthana', 'manipura', 'anahata',
                'vishuddha', 'ajna', 'sahasrara'
            ]

        return self.create_healing_session(
            target_name=target_name,
            modalities=['chakra_balancing', 'scalar_waves'],
            duration_minutes=45,
            intention=f"Balance and harmonize {', '.join(chakras)}"
        )

    def meridian_clearing_protocol(
        self,
        target_name: str,
        element: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run meridian clearing protocol"""
        modalities = ['meridian_clearing', 'scalar_waves']

        intention = "Clear and balance all meridians"
        if element:
            intention = f"Clear and balance {element} element meridians"

        return self.create_healing_session(
            target_name=target_name,
            modalities=modalities,
            duration_minutes=30,
            intention=intention
        )

    def trauma_release_protocol(
        self,
        target_name: str,
        trauma_type: str = "general",
        depth: str = "moderate"
    ) -> Dict[str, Any]:
        """Run trauma release protocol"""
        modalities = [
            'scalar_waves',
            'radionics',
            'time_cycle_healing',
            'blessing'
        ]

        duration_map = {
            'surface': 30,
            'moderate': 60,
            'deep': 108
        }

        return self.create_healing_session(
            target_name=target_name,
            modalities=modalities,
            duration_minutes=duration_map.get(depth, 60),
            intention=f"Release and heal {trauma_type} trauma"
        )

    def ancestral_healing_protocol(
        self,
        lineage_name: str,
        generations: int = 7
    ) -> Dict[str, Any]:
        """Run ancestral healing protocol"""
        return self.create_healing_session(
            target_name=f"{lineage_name} Lineage",
            modalities=[
                'time_cycle_healing',
                'radionics',
                'blessing',
                'scalar_waves'
            ],
            duration_minutes=108,  # Sacred number
            intention=f"Heal {generations} generations of {lineage_name} lineage"
        )

    def get_available_modalities(self) -> List[Dict[str, str]]:
        """Get list of available healing modalities"""
        return [
            {
                'id': 'scalar_waves',
                'name': 'Scalar Wave Generation',
                'description': 'Terra MOPS quantum healing waves'
            },
            {
                'id': 'radionics',
                'name': 'Radionics Broadcasting',
                'description': 'Intention-based energetic transmission'
            },
            {
                'id': 'chakra_balancing',
                'name': 'Chakra Balancing',
                'description': 'Seven chakra system harmonization'
            },
            {
                'id': 'meridian_clearing',
                'name': 'Meridian Clearing',
                'description': 'Twelve meridian system optimization'
            },
            {
                'id': 'time_cycle_healing',
                'name': 'Time Cycle Healing',
                'description': 'Healing across time dimensions'
            },
            {
                'id': 'blessing',
                'name': 'Sacred Blessings',
                'description': 'Spiritual blessing transmission'
            },
            {
                'id': 'sound_healing',
                'name': 'Sound Healing',
                'description': 'Healing through sacred frequencies'
            },
            {
                'id': 'visualization',
                'name': 'Healing Visualization',
                'description': 'Sacred geometry and energy field visualization'
            }
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get healing systems status"""
        return {
            'healing_systems': self.healing_systems is not None,
            'available_modalities': len(self.get_available_modalities())
        }
