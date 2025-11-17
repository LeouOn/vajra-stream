"""
Visualization Module
Wraps Rothko generator, energetic visualization, and visual renderer
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class VisualizationService:
    """Unified visualization service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._rothko = None
        self._energetic_viz = None
        self._visual_renderer = None

    @property
    def rothko(self):
        """Get Rothko generator"""
        if self._rothko is None:
            try:
                from core.rothko_generator import RothkoGenerator
                self._rothko = RothkoGenerator()
            except ImportError:
                self._rothko = None
        return self._rothko

    @property
    def energetic_viz(self):
        """Get energetic visualization"""
        if self._energetic_viz is None:
            try:
                from core.energetic_visualization import EnergeticVisualization
                self._energetic_viz = EnergeticVisualization()
            except ImportError:
                self._energetic_viz = None
        return self._energetic_viz

    @property
    def visual_renderer(self):
        """Get visual renderer"""
        if self._visual_renderer is None:
            try:
                from core.visual_renderer_simple import VisualRenderer
                self._visual_renderer = VisualRenderer()
            except ImportError:
                self._visual_renderer = None
        return self._visual_renderer

    def generate_rothko_art(
        self,
        width: int = 1920,
        height: int = 1080,
        colors: Optional[list] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Generate Rothko-style abstract art"""
        if self.rothko is None:
            raise RuntimeError(
                "Rothko generator not available - PIL/Pillow not installed.\n"
                "Install with: pip install pillow\n"
                "Or install all dependencies: pip install -r requirements.txt"
            )

        if output_path is None:
            output_path = "/tmp/vajra_rothko.png"

        try:
            image = self.rothko.generate(
                width=width,
                height=height,
                colors=colors
            )
            image.save(output_path)
            return output_path
        except Exception as e:
            raise ValueError(f"Error generating Rothko art: {e}")

    def generate_energy_field(
        self,
        width: int = 800,
        height: int = 800,
        field_type: str = "aura",
        colors: Optional[list] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Generate energetic field visualization"""
        if self.energetic_viz is None:
            raise ValueError("Energetic visualization not available")

        if output_path is None:
            output_path = "/tmp/vajra_energy_field.png"

        try:
            image = self.energetic_viz.create_field(
                width=width,
                height=height,
                field_type=field_type,
                colors=colors
            )
            image.save(output_path)
            return output_path
        except Exception as e:
            raise ValueError(f"Error generating energy field: {e}")

    def render_sacred_geometry(
        self,
        geometry_type: str = "flower_of_life",
        size: int = 800,
        color: Tuple[int, int, int] = (255, 215, 0),
        output_path: Optional[str] = None
    ) -> str:
        """Render sacred geometry"""
        if self.visual_renderer is None:
            raise ValueError("Visual renderer not available")

        if output_path is None:
            output_path = "/tmp/vajra_sacred_geometry.png"

        try:
            image = self.visual_renderer.render_geometry(
                geometry_type=geometry_type,
                size=size,
                color=color
            )
            image.save(output_path)
            return output_path
        except Exception as e:
            raise ValueError(f"Error rendering sacred geometry: {e}")

    def create_healing_mandala(
        self,
        intention: str = "healing",
        size: int = 1000,
        colors: Optional[list] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Create a healing mandala visualization"""
        if output_path is None:
            output_path = "/tmp/vajra_mandala.png"

        # Try energetic viz first, fall back to Rothko
        try:
            if self.energetic_viz:
                image = self.energetic_viz.create_mandala(
                    intention=intention,
                    size=size,
                    colors=colors
                )
            elif self.rothko:
                image = self.rothko.generate(
                    width=size,
                    height=size,
                    colors=colors or ['#FF6B6B', '#4ECDC4', '#45B7D1']
                )
            else:
                raise ValueError("No visualization engine available")

            image.save(output_path)
            return output_path
        except Exception as e:
            raise ValueError(f"Error creating mandala: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of all visualization subsystems"""
        return {
            'rothko_generator': self.rothko is not None,
            'energetic_visualization': self.energetic_viz is not None,
            'visual_renderer': self.visual_renderer is not None
        }

    def list_geometry_types(self) -> list:
        """List available sacred geometry types"""
        return [
            'flower_of_life',
            'seed_of_life',
            'metatrons_cube',
            'sri_yantra',
            'vesica_piscis',
            'torus',
            'golden_spiral'
        ]
