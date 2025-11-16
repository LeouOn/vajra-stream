"""
Anatomy Module
Adapter wrapping core.meridian_visualization and core.energetic_anatomy
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import io
import base64

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.meridian_visualization import MeridianVisualizer, BodyPosition
from core.energetic_anatomy import EnergeticAnatomyDatabase, Tradition
from modules.interfaces import AnatomyVisualizer, EventBus


class AnatomyService(AnatomyVisualizer):
    """Energetic anatomy service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self.visualizer = MeridianVisualizer()
        self.database = EnergeticAnatomyDatabase()

    def visualize_chakras(
        self,
        width: int = 1200,
        height: int = 1600,
        output_path: Optional[str] = None
    ) -> str:
        """Generate chakra diagram"""

        if output_path is None:
            output_path = "/tmp/vajra_chakras.png"

        viz = MeridianVisualizer(width=width, height=height)
        image = viz.create_seven_chakras_diagram()
        image.save(output_path)

        return output_path

    def visualize_meridians(
        self,
        width: int = 1200,
        height: int = 1600,
        output_path: Optional[str] = None
    ) -> str:
        """Generate meridian map"""

        if output_path is None:
            output_path = "/tmp/vajra_meridians.png"

        viz = MeridianVisualizer(width=width, height=height)
        image = viz.create_elemental_meridian_map()
        image.save(output_path)

        return output_path

    def visualize_central_channel(
        self,
        width: int = 1200,
        height: int = 1800,
        output_path: Optional[str] = None
    ) -> str:
        """Generate central channel diagram"""

        if output_path is None:
            output_path = "/tmp/vajra_central_channel.png"

        viz = MeridianVisualizer(width=width, height=height)
        image = viz.create_central_channel_diagram()
        image.save(output_path)

        return output_path

    def get_chakra_info(self) -> List[Dict[str, Any]]:
        """Get chakra information"""
        return [
            {
                'sanskrit': 'Muladhara', 'english': 'Root',
                'location': 'Base of spine', 'element': 'Earth',
                'color': 'Red', 'frequency': 396
            },
            {
                'sanskrit': 'Svadhisthana', 'english': 'Sacral',
                'location': 'Lower abdomen', 'element': 'Water',
                'color': 'Orange', 'frequency': 417
            },
            {
                'sanskrit': 'Manipura', 'english': 'Solar Plexus',
                'location': 'Upper abdomen', 'element': 'Fire',
                'color': 'Yellow', 'frequency': 528
            },
            {
                'sanskrit': 'Anahata', 'english': 'Heart',
                'location': 'Center of chest', 'element': 'Air',
                'color': 'Green', 'frequency': 639
            },
            {
                'sanskrit': 'Vishuddha', 'english': 'Throat',
                'location': 'Throat', 'element': 'Ether',
                'color': 'Blue', 'frequency': 741
            },
            {
                'sanskrit': 'Ajna', 'english': 'Third Eye',
                'location': 'Between eyebrows', 'element': 'Light',
                'color': 'Indigo', 'frequency': 852
            },
            {
                'sanskrit': 'Sahasrara', 'english': 'Crown',
                'location': 'Top of head', 'element': 'Consciousness',
                'color': 'Violet', 'frequency': 963
            }
        ]

    def get_meridian_info(self) -> List[Dict[str, Any]]:
        """Get meridian information"""
        return [
            {'name': 'Lung', 'element': 'Metal', 'yin_yang': 'Yin'},
            {'name': 'Large Intestine', 'element': 'Metal', 'yin_yang': 'Yang'},
            {'name': 'Stomach', 'element': 'Earth', 'yin_yang': 'Yang'},
            {'name': 'Spleen', 'element': 'Earth', 'yin_yang': 'Yin'},
            {'name': 'Heart', 'element': 'Fire', 'yin_yang': 'Yin'},
            {'name': 'Small Intestine', 'element': 'Fire', 'yin_yang': 'Yang'},
            {'name': 'Bladder', 'element': 'Water', 'yin_yang': 'Yang'},
            {'name': 'Kidney', 'element': 'Water', 'yin_yang': 'Yin'},
            {'name': 'Pericardium', 'element': 'Fire', 'yin_yang': 'Yin'},
            {'name': 'Triple Warmer', 'element': 'Fire', 'yin_yang': 'Yang'},
            {'name': 'Gallbladder', 'element': 'Wood', 'yin_yang': 'Yang'},
            {'name': 'Liver', 'element': 'Wood', 'yin_yang': 'Yin'}
        ]
