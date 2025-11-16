#!/usr/bin/env python3
"""
Energetic Visualization - Core Rendering Engine

Multi-modal visualization system supporting:
- Rothko-style abstract color fields
- Sacred geometry and fractals
- Energetic anatomy diagrams
- Meditation visuals
- Integration with all vajra-stream systems

Renders beautiful, meaningful visualizations for practice and contemplation.
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageColor
from PIL.ImageDraw import Draw
import math
import random
from typing import List, Tuple, Optional, Dict, Union
from dataclasses import dataclass, field
from enum import Enum
import colorsys

try:
    from core.energetic_anatomy import (
        EnergeticAnatomyDatabase,
        Chakra,
        Meridian,
        Element,
        get_chakra_by_name
    )
    HAS_ANATOMY = True
except ImportError:
    HAS_ANATOMY = False


# ============================================================================
# COLOR PALETTES
# ============================================================================

# Chakra colors (RGB)
CHAKRA_COLORS = {
    'muladhara': (196, 0, 0),        # Deep red
    'svadhisthana': (255, 127, 0),    # Orange
    'manipura': (255, 255, 0),        # Yellow/gold
    'anahata': (0, 255, 0),           # Green
    'anahata_alt': (255, 182, 193),   # Pink (alternative)
    'vishuddha': (0, 127, 255),       # Sky blue
    'ajna': (75, 0, 130),             # Indigo
    'sahasrara': (148, 0, 211)        # Violet
}

# Five Element colors
ELEMENT_COLORS = {
    'wood': (34, 139, 34),      # Forest green
    'fire': (220, 20, 60),      # Crimson
    'earth': (218, 165, 32),    # Goldenrod
    'metal': (192, 192, 192),   # Silver
    'water': (25, 25, 112)      # Midnight blue
}

# Rothko-inspired palettes
ROTHKO_PALETTES = {
    'classic': [(212, 69, 47), (255, 198, 93), (20, 20, 20)],
    'meditative': [(72, 61, 139), (147, 112, 219), (255, 250, 250)],
    'warm': [(255, 99, 71), (255, 140, 0), (255, 228, 181)],
    'cool': [(70, 130, 180), (176, 224, 230), (240, 248, 255)],
    'earth': [(139, 90, 43), (210, 180, 140), (245, 245, 220)],
    'sunset': [(255, 94, 77), (255, 155, 66), (254, 211, 48)],
    'ocean': [(13, 27, 42), (27, 38, 59), (65, 90, 119)],
    'forest': [(27, 54, 38), (76, 116, 73), (180, 204, 148)]
}

# Planetary colors
PLANET_COLORS = {
    'sun': (255, 215, 0),         # Gold
    'moon': (192, 192, 192),      # Silver
    'mercury': (128, 128, 128),   # Gray
    'venus': (50, 205, 50),       # Lime green
    'mars': (178, 34, 34),        # Firebrick
    'jupiter': (138, 43, 226),    # Blue violet
    'saturn': (25, 25, 112),      # Midnight blue
    'uranus': (64, 224, 208),     # Turquoise
    'neptune': (72, 61, 139),     # Dark slate blue
    'pluto': (139, 0, 0)          # Dark red
}


# ============================================================================
# ENUMS
# ============================================================================

class VisualizationStyle(Enum):
    """Visualization style"""
    ROTHKO = "rothko"
    MINIMAL = "minimal"
    DETAILED = "detailed"
    TRADITIONAL = "traditional"
    MODERN = "modern"
    FRACTAL = "fractal"
    SACRED_GEOMETRY = "sacred_geometry"


class RothkoLayout(Enum):
    """Layout for Rothko-style fields"""
    SINGLE = "single"          # One large field
    TWO_HORIZONTAL = "two_h"   # Two fields stacked
    THREE_HORIZONTAL = "three_h"  # Three fields stacked
    TWO_VERTICAL = "two_v"     # Two fields side by side
    FOUR_GRID = "four_grid"    # 2x2 grid


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ColorField:
    """A Rothko-style color field"""
    color: Tuple[int, int, int]
    position: Tuple[float, float]  # (x, y) as fraction of canvas (0-1)
    size: Tuple[float, float]      # (width, height) as fraction
    edge_blur: int = 30            # Blur radius for soft edges
    luminosity: float = 1.0        # Brightness multiplier
    texture_strength: float = 0.1  # Subtle texture variation
    name: str = ""                 # Optional name/label

    def add_color_variation(self, amount: float = 0.05) -> 'ColorField':
        """Create slight color variation"""
        r, g, b = self.color
        r = int(max(0, min(255, r + random.randint(-int(255*amount), int(255*amount)))))
        g = int(max(0, min(255, g + random.randint(-int(255*amount), int(255*amount)))))
        b = int(max(0, min(255, b + random.randint(-int(255*amount), int(255*amount)))))
        return ColorField(
            color=(r, g, b),
            position=self.position,
            size=self.size,
            edge_blur=self.edge_blur,
            luminosity=self.luminosity,
            texture_strength=self.texture_strength,
            name=self.name
        )


# ============================================================================
# BASE VISUALIZER
# ============================================================================

class BaseVisualizer:
    """Base class for all visualizers"""

    def __init__(self, width: int = 1920, height: int = 1080,
                 background: Tuple[int, int, int] = (255, 255, 255),
                 dpi: int = 150):
        """
        Initialize visualizer.

        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            background: Background RGB color
            dpi: Resolution for print quality
        """
        self.width = width
        self.height = height
        self.background = background
        self.dpi = dpi
        self.canvas = Image.new('RGB', (width, height), background)
        self.draw = ImageDraw.Draw(self.canvas)

    def clear(self):
        """Clear canvas to background color"""
        self.canvas = Image.new('RGB', (self.width, self.height), self.background)
        self.draw = ImageDraw.Draw(self.canvas)

    def save(self, filepath: str, format: Optional[str] = None):
        """Save image to file"""
        if format is None:
            # Detect from extension
            if filepath.endswith('.png'):
                format = 'PNG'
            elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                format = 'JPEG'
            elif filepath.endswith('.pdf'):
                format = 'PDF'

        self.canvas.save(filepath, format=format, dpi=(self.dpi, self.dpi))

    def show(self):
        """Display image"""
        self.canvas.show()

    def get_image(self) -> Image.Image:
        """Get PIL Image object"""
        return self.canvas.copy()

    def add_texture(self, strength: float = 0.1):
        """Add subtle texture to entire canvas"""
        pixels = self.canvas.load()
        for x in range(self.width):
            for y in range(self.height):
                r, g, b = pixels[x, y]
                variation = int(random.randint(-10, 10) * strength)
                r = max(0, min(255, r + variation))
                g = max(0, min(255, g + variation))
                b = max(0, min(255, b + variation))
                pixels[x, y] = (r, g, b)


# ============================================================================
# ROTHKO-STYLE VISUALIZER
# ============================================================================

class RothkoVisualizer(BaseVisualizer):
    """
    Create Rothko-style abstract color field paintings.

    Inspired by Mark Rothko's luminous, meditative works.
    Perfect for chakra meditations, emotional states, and contemplative art.
    """

    def __init__(self, width: int = 1920, height: int = 1080,
                 background: Tuple[int, int, int] = (245, 245, 240)):
        """Initialize with off-white background (Rothko's typical choice)"""
        super().__init__(width, height, background)
        self.fields: List[ColorField] = []

    def create_field(self, color: Tuple[int, int, int],
                     position: Tuple[float, float],
                     size: Tuple[float, float],
                     edge_blur: int = 40,
                     luminosity: float = 1.0,
                     name: str = "") -> ColorField:
        """
        Create a single color field.

        Args:
            color: RGB color tuple
            position: (x, y) as fractions of canvas (0-1)
            size: (width, height) as fractions of canvas
            edge_blur: Blur radius for soft edges
            luminosity: Brightness multiplier
            name: Optional label

        Returns:
            ColorField object
        """
        field = ColorField(
            color=color,
            position=position,
            size=size,
            edge_blur=edge_blur,
            luminosity=luminosity,
            name=name
        )
        self.fields.append(field)
        return field

    def render_field(self, field: ColorField, add_variation: bool = True):
        """
        Render a single color field onto canvas.

        Args:
            field: ColorField to render
            add_variation: Add subtle color variations
        """
        # Calculate pixel coordinates
        x = int(field.position[0] * self.width)
        y = int(field.position[1] * self.height)
        w = int(field.size[0] * self.width)
        h = int(field.size[1] * self.height)

        # Create field on separate layer for blending
        field_layer = Image.new('RGB', (self.width, self.height), self.background)
        field_draw = ImageDraw.Draw(field_layer)

        # Apply luminosity
        r, g, b = field.color
        r = int(min(255, r * field.luminosity))
        g = int(min(255, g * field.luminosity))
        b = int(min(255, b * field.luminosity))
        field_color = (r, g, b)

        # Draw rectangle
        field_draw.rectangle(
            [(x, y), (x + w, y + h)],
            fill=field_color
        )

        # Add subtle texture variations
        if add_variation:
            pixels = field_layer.load()
            for px in range(x, x + w):
                for py in range(y, y + h):
                    if 0 <= px < self.width and 0 <= py < self.height:
                        cr, cg, cb = pixels[px, py]
                        if cr == r and cg == g and cb == b:  # Only modify field pixels
                            variation = random.randint(-8, 8)
                            cr = max(0, min(255, cr + variation))
                            cg = max(0, min(255, cg + variation))
                            cb = max(0, min(255, cb + variation))
                            pixels[px, py] = (cr, cg, cb)

        # Apply edge blur for soft transitions
        if field.edge_blur > 0:
            field_layer = field_layer.filter(ImageFilter.GaussianBlur(radius=field.edge_blur))

        # Composite onto canvas
        self.canvas = Image.blend(self.canvas, field_layer, alpha=0.95)
        self.draw = ImageDraw.Draw(self.canvas)

    def render_all_fields(self):
        """Render all fields in order"""
        for field in self.fields:
            self.render_field(field)

    def create_from_palette(self, palette_name: str, layout: RothkoLayout = RothkoLayout.THREE_HORIZONTAL):
        """
        Create composition from predefined Rothko palette.

        Args:
            palette_name: Name from ROTHKO_PALETTES
            layout: How to arrange the color fields
        """
        if palette_name not in ROTHKO_PALETTES:
            raise ValueError(f"Unknown palette: {palette_name}")

        colors = ROTHKO_PALETTES[palette_name]
        self.fields = []

        if layout == RothkoLayout.SINGLE:
            self.create_field(colors[0], (0.1, 0.1), (0.8, 0.8))

        elif layout == RothkoLayout.TWO_HORIZONTAL:
            self.create_field(colors[0], (0.1, 0.1), (0.8, 0.35))
            self.create_field(colors[1], (0.1, 0.55), (0.8, 0.35))

        elif layout == RothkoLayout.THREE_HORIZONTAL:
            self.create_field(colors[0], (0.1, 0.08), (0.8, 0.25))
            self.create_field(colors[1], (0.1, 0.38), (0.8, 0.25))
            if len(colors) > 2:
                self.create_field(colors[2], (0.1, 0.68), (0.8, 0.25))

        elif layout == RothkoLayout.TWO_VERTICAL:
            self.create_field(colors[0], (0.1, 0.1), (0.35, 0.8))
            self.create_field(colors[1], (0.55, 0.1), (0.35, 0.8))

        elif layout == RothkoLayout.FOUR_GRID:
            self.create_field(colors[0], (0.1, 0.1), (0.35, 0.35))
            self.create_field(colors[1 % len(colors)], (0.55, 0.1), (0.35, 0.35))
            self.create_field(colors[2 % len(colors)], (0.1, 0.55), (0.35, 0.35))
            self.create_field(colors[0], (0.55, 0.55), (0.35, 0.35))

        self.render_all_fields()

    def create_chakra_field(self, chakra_name: str, include_label: bool = False):
        """
        Create Rothko-style field for a chakra.

        Args:
            chakra_name: Name of chakra (e.g., 'muladhara', 'anahata')
            include_label: Add chakra name as text
        """
        if chakra_name not in CHAKRA_COLORS:
            raise ValueError(f"Unknown chakra: {chakra_name}")

        color = CHAKRA_COLORS[chakra_name]
        self.fields = []

        # Single large field for meditation
        field = self.create_field(
            color=color,
            position=(0.1, 0.15),
            size=(0.8, 0.7),
            edge_blur=50,
            luminosity=1.1,  # Slightly brighter for glowing effect
            name=chakra_name
        )

        self.render_all_fields()

        # Optionally add label
        if include_label:
            # Try to load a font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
            except:
                font = ImageFont.load_default()

            # Add chakra name at bottom
            label = chakra_name.upper()
            bbox = self.draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (self.width - text_width) // 2
            text_y = int(self.height * 0.90)

            # Draw text with subtle shadow
            shadow_offset = 2
            self.draw.text((text_x + shadow_offset, text_y + shadow_offset),
                          label, fill=(0, 0, 0, 128), font=font)
            self.draw.text((text_x, text_y), label, fill=(50, 50, 50), font=font)

    def create_seven_chakras(self, vertical: bool = True):
        """
        Create composition showing all seven chakras.

        Args:
            vertical: If True, stack vertically (root to crown).
                     If False, arrange horizontally.
        """
        chakras = ['muladhara', 'svadhisthana', 'manipura', 'anahata',
                  'vishuddha', 'ajna', 'sahasrara']

        self.fields = []

        if vertical:
            # Stack from bottom (root) to top (crown)
            segment_height = 1.0 / len(chakras)
            for i, chakra_name in enumerate(reversed(chakras)):  # Reverse so root is at bottom
                color = CHAKRA_COLORS[chakra_name]
                y_pos = i * segment_height
                self.create_field(
                    color=color,
                    position=(0.0, y_pos),
                    size=(1.0, segment_height),
                    edge_blur=30,
                    name=chakra_name
                )
        else:
            # Arrange horizontally
            segment_width = 1.0 / len(chakras)
            for i, chakra_name in enumerate(chakras):
                color = CHAKRA_COLORS[chakra_name]
                x_pos = i * segment_width
                self.create_field(
                    color=color,
                    position=(x_pos, 0.0),
                    size=(segment_width, 1.0),
                    edge_blur=30,
                    name=chakra_name
                )

        self.render_all_fields()

    def create_element_field(self, element_name: str):
        """
        Create field for a Taoist element.

        Args:
            element_name: 'wood', 'fire', 'earth', 'metal', or 'water'
        """
        if element_name not in ELEMENT_COLORS:
            raise ValueError(f"Unknown element: {element_name}")

        color = ELEMENT_COLORS[element_name]
        self.fields = []

        # Create field with element-appropriate characteristics
        edge_blur = {
            'wood': 35,  # Slightly crisp (growing)
            'fire': 60,  # Very soft (flickering)
            'earth': 20, # Sharp (stable)
            'metal': 25, # Crisp (refined)
            'water': 50  # Soft (flowing)
        }.get(element_name, 40)

        self.create_field(
            color=color,
            position=(0.1, 0.15),
            size=(0.8, 0.7),
            edge_blur=edge_blur,
            name=element_name
        )

        self.render_all_fields()


# ============================================================================
# SACRED GEOMETRY VISUALIZER
# ============================================================================

class SacredGeometryVisualizer(BaseVisualizer):
    """
    Create sacred geometry patterns.

    Supports: Flower of Life, Seed of Life, Metatron's Cube, etc.
    """

    def __init__(self, width: int = 1920, height: int = 1080,
                 background: Tuple[int, int, int] = (20, 20, 30)):
        """Initialize with dark background for luminous effect"""
        super().__init__(width, height, background)
        self.center = (width // 2, height // 2)

    def draw_circle_outline(self, center: Tuple[int, int], radius: int,
                           color: Tuple[int, int, int] = (255, 255, 255),
                           width: int = 2, glow: bool = False):
        """Draw a circle outline, optionally with glow"""
        if glow:
            # Draw multiple circles with decreasing opacity for glow effect
            for i in range(10, 0, -1):
                alpha = int(255 * (i / 10) * 0.3)
                glow_color = (*color, alpha)
                self.draw.ellipse(
                    [center[0] - radius - i, center[1] - radius - i,
                     center[0] + radius + i, center[1] + radius + i],
                    outline=glow_color,
                    width=1
                )

        # Draw main circle
        self.draw.ellipse(
            [center[0] - radius, center[1] - radius,
             center[0] + radius, center[1] + radius],
            outline=color,
            width=width
        )

    def create_flower_of_life(self, radius: int = 200,
                             color: Tuple[int, int, int] = (255, 215, 0),
                             glow: bool = True):
        """
        Create Flower of Life pattern.

        19 overlapping circles in hexagonal pattern.
        """
        # Central circle
        self.draw_circle_outline(self.center, radius, color, width=3, glow=glow)

        # Six circles around center (first ring)
        for i in range(6):
            angle = i * 60  # 60 degrees apart
            rad = math.radians(angle)
            x = self.center[0] + int(radius * math.cos(rad))
            y = self.center[1] + int(radius * math.sin(rad))
            self.draw_circle_outline((x, y), radius, color, width=2, glow=glow)

        # Twelve circles in second ring
        for i in range(12):
            angle = i * 30  # 30 degrees apart
            rad = math.radians(angle)
            distance = radius * math.sqrt(3)  # Distance to second ring
            x = self.center[0] + int(distance * math.cos(rad))
            y = self.center[1] + int(distance * math.sin(rad))
            self.draw_circle_outline((x, y), radius, color, width=2, glow=glow)

    def create_seed_of_life(self, radius: int = 200,
                           color: Tuple[int, int, int] = (147, 112, 219),
                           glow: bool = True):
        """
        Create Seed of Life pattern.

        7 overlapping circles (central + 6 surrounding).
        """
        # Central circle
        self.draw_circle_outline(self.center, radius, color, width=3, glow=glow)

        # Six circles around center
        for i in range(6):
            angle = i * 60
            rad = math.radians(angle)
            x = self.center[0] + int(radius * math.cos(rad))
            y = self.center[1] + int(radius * math.sin(rad))
            self.draw_circle_outline((x, y), radius, color, width=3, glow=glow)

    def create_sri_yantra_simple(self, size: int = 400,
                                 color: Tuple[int, int, int] = (255, 100, 100)):
        """
        Create simplified Sri Yantra pattern.

        Nine interlocking triangles.
        """
        # This is a simplified version - full Sri Yantra is extremely complex
        half = size // 2

        # Upward pointing triangles (Shiva - masculine)
        for i in range(5):
            offset = i * 40
            points = [
                (self.center[0], self.center[1] - half + offset),           # Top
                (self.center[0] - half + offset, self.center[1] + half - offset),  # Bottom left
                (self.center[0] + half - offset, self.center[1] + half - offset)   # Bottom right
            ]
            self.draw.polygon(points, outline=color, width=2)

        # Downward pointing triangles (Shakti - feminine)
        for i in range(4):
            offset = i * 40 + 20
            points = [
                (self.center[0], self.center[1] + half - offset),           # Bottom
                (self.center[0] - half + offset, self.center[1] - half + offset),  # Top left
                (self.center[0] + half - offset, self.center[1] - half + offset)   # Top right
            ]
            self.draw.polygon(points, outline=color, width=2)

        # Central bindu (point)
        bindu_radius = 8
        self.draw.ellipse(
            [self.center[0] - bindu_radius, self.center[1] - bindu_radius,
             self.center[0] + bindu_radius, self.center[1] + bindu_radius],
            fill=color
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_chakra_meditation(chakra_name: str, width: int = 1920, height: int = 1080,
                             style: str = 'rothko', save_path: Optional[str] = None) -> Image.Image:
    """
    Quick function to create a chakra meditation visual.

    Args:
        chakra_name: Name of chakra
        width: Image width
        height: Image height
        style: 'rothko' or 'minimal'
        save_path: Optional path to save image

    Returns:
        PIL Image
    """
    if style == 'rothko':
        viz = RothkoVisualizer(width, height)
        viz.create_chakra_field(chakra_name, include_label=True)
    else:
        viz = BaseVisualizer(width, height, background=(0, 0, 0))
        color = CHAKRA_COLORS.get(chakra_name, (255, 255, 255))
        # Simple filled rectangle
        viz.draw.rectangle(
            [(width * 0.2, height * 0.2), (width * 0.8, height * 0.8)],
            fill=color
        )

    if save_path:
        viz.save(save_path)

    return viz.get_image()


def create_seven_chakras_composition(width: int = 1920, height: int = 1080,
                                    vertical: bool = True,
                                    save_path: Optional[str] = None) -> Image.Image:
    """Quick function to create seven chakras composition"""
    viz = RothkoVisualizer(width, height, background=(30, 30, 35))
    viz.create_seven_chakras(vertical=vertical)

    if save_path:
        viz.save(save_path)

    return viz.get_image()


def create_flower_of_life(width: int = 1920, height: int = 1080,
                         color: Tuple[int, int, int] = (255, 215, 0),
                         save_path: Optional[str] = None) -> Image.Image:
    """Quick function to create Flower of Life"""
    viz = SacredGeometryVisualizer(width, height)
    viz.create_flower_of_life(radius=min(width, height) // 4, color=color, glow=True)

    if save_path:
        viz.save(save_path)

    return viz.get_image()


# Example usage
if __name__ == "__main__":
    print("Energetic Visualization System - Core Engine\n")

    # Example 1: Rothko-style chakra field
    print("Creating heart chakra Rothko field...")
    viz1 = RothkoVisualizer(1920, 1080)
    viz1.create_chakra_field('anahata', include_label=True)
    viz1.save('/tmp/heart_chakra_rothko.png')
    print("  → Saved to /tmp/heart_chakra_rothko.png")

    # Example 2: Seven chakras composition
    print("\nCreating seven chakras vertical composition...")
    viz2 = RothkoVisualizer(1080, 1920)  # Portrait orientation
    viz2.create_seven_chakras(vertical=True)
    viz2.save('/tmp/seven_chakras.png')
    print("  → Saved to /tmp/seven_chakras.png")

    # Example 3: Rothko palette
    print("\nCreating Rothko 'meditative' palette...")
    viz3 = RothkoVisualizer(1920, 1080)
    viz3.create_from_palette('meditative', RothkoLayout.THREE_HORIZONTAL)
    viz3.save('/tmp/rothko_meditative.png')
    print("  → Saved to /tmp/rothko_meditative.png")

    # Example 4: Flower of Life
    print("\nCreating Flower of Life sacred geometry...")
    viz4 = SacredGeometryVisualizer(1920, 1920)  # Square
    viz4.create_flower_of_life(radius=400, color=(255, 215, 0), glow=True)
    viz4.save('/tmp/flower_of_life.png')
    print("  → Saved to /tmp/flower_of_life.png")

    # Example 5: Seed of Life
    print("\nCreating Seed of Life sacred geometry...")
    viz5 = SacredGeometryVisualizer(1920, 1920)
    viz5.create_seed_of_life(radius=350, color=(147, 112, 219), glow=True)
    viz5.save('/tmp/seed_of_life.png')
    print("  → Saved to /tmp/seed_of_life.png")

    # Example 6: Element field (Water)
    print("\nCreating Water element Rothko field...")
    viz6 = RothkoVisualizer(1920, 1080)
    viz6.create_element_field('water')
    viz6.save('/tmp/element_water.png')
    print("  → Saved to /tmp/element_water.png")

    print("\n✨ All visualizations created successfully! ✨")
    print("\nExamples demonstrate:")
    print("  - Rothko-style abstract color fields")
    print("  - Chakra meditation visuals")
    print("  - Sacred geometry patterns")
    print("  - Five element representations")
    print("\nUse these for meditation, contemplation, and energetic work!")
