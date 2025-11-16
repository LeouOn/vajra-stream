#!/usr/bin/env python3
"""
Meridian & Energetic Anatomy Visualization System

Beautiful visualizations of:
- 12 primary meridians (Taoist)
- 8 extraordinary meridians
- 7 chakras (Hindu)
- 5 Tibetan chakras
- 3 channels (Uma, Roma, Kyangma)
- Energy flows and connections

Creates stunning visual representations for healing work.
"""

import math
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from enum import Enum

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Note: PIL not available - visualization disabled")

try:
    from core.energetic_anatomy import (
        EnergeticAnatomyDatabase,
        Tradition,
        Element
    )
    HAS_ANATOMY = True
except ImportError:
    HAS_ANATOMY = False
    # Define simple Element enum if not available
    from enum import Enum as EnumBase
    class Element(EnumBase):
        WOOD = "wood"
        FIRE = "fire"
        EARTH = "earth"
        METAL = "metal"
        WATER = "water"


class BodyPosition(Enum):
    """Standard body positions for visualization"""
    FRONT = "front"
    BACK = "back"
    SIDE_LEFT = "side_left"
    SIDE_RIGHT = "side_right"


class MeridianVisualizer:
    """
    Visualize meridians and energy channels on human body outline.
    """

    def __init__(self, width: int = 1200, height: int = 1600,
                 background: Tuple[int, int, int] = (20, 20, 30)):
        if not HAS_PIL:
            raise RuntimeError("PIL/Pillow required for visualization")

        self.width = width
        self.height = height
        self.background = background

        # Create image
        self.image = Image.new('RGB', (width, height), background)
        self.draw = ImageDraw.Draw(self.image, 'RGBA')

        # Load anatomy database
        self.anatomy_db = EnergeticAnatomyDatabase() if HAS_ANATOMY else None

        # Element colors
        self.element_colors = {
            Element.WOOD: (0, 200, 100, 200),      # Green
            Element.FIRE: (255, 100, 50, 200),     # Red-orange
            Element.EARTH: (200, 150, 50, 200),    # Yellow-brown
            Element.METAL: (200, 200, 220, 200),   # Silver-white
            Element.WATER: (50, 150, 255, 200),    # Blue
            None: (150, 150, 200, 200)             # Default lavender
        }

        # Chakra colors
        self.chakra_colors = {
            'muladhara': (196, 0, 0),         # Root - Red
            'svadhisthana': (255, 127, 0),    # Sacral - Orange
            'manipura': (255, 255, 0),        # Solar - Yellow
            'anahata': (0, 255, 0),           # Heart - Green
            'vishuddha': (0, 127, 255),       # Throat - Blue
            'ajna': (75, 0, 130),             # Third Eye - Indigo
            'sahasrara': (148, 0, 211)        # Crown - Violet
        }

    def draw_body_outline(self, position: BodyPosition = BodyPosition.FRONT):
        """Draw simplified human body outline"""
        center_x = self.width // 2
        head_y = 100
        torso_top = 200
        torso_bottom = 800
        hip_y = 850
        foot_y = 1500

        if position == BodyPosition.FRONT:
            # Head (circle)
            head_radius = 60
            self.draw.ellipse(
                [center_x - head_radius, head_y - head_radius,
                 center_x + head_radius, head_y + head_radius],
                outline=(100, 100, 150, 150),
                width=2
            )

            # Neck
            self.draw.line(
                [(center_x, head_y + head_radius), (center_x, torso_top)],
                fill=(100, 100, 150, 150),
                width=15
            )

            # Shoulders
            shoulder_width = 180
            self.draw.line(
                [(center_x - shoulder_width, torso_top),
                 (center_x + shoulder_width, torso_top)],
                fill=(100, 100, 150, 150),
                width=15
            )

            # Arms
            arm_length = 400
            # Left arm
            self.draw.line(
                [(center_x - shoulder_width, torso_top),
                 (center_x - shoulder_width - 50, torso_top + arm_length)],
                fill=(100, 100, 150, 150),
                width=12
            )
            # Right arm
            self.draw.line(
                [(center_x + shoulder_width, torso_top),
                 (center_x + shoulder_width + 50, torso_top + arm_length)],
                fill=(100, 100, 150, 150),
                width=12
            )

            # Torso (elongated oval)
            torso_width = 140
            self.draw.ellipse(
                [center_x - torso_width, torso_top,
                 center_x + torso_width, torso_bottom],
                outline=(100, 100, 150, 150),
                width=3
            )

            # Legs
            leg_spread = 60
            # Left leg
            self.draw.line(
                [(center_x - leg_spread, hip_y),
                 (center_x - leg_spread - 20, foot_y)],
                fill=(100, 100, 150, 150),
                width=15
            )
            # Right leg
            self.draw.line(
                [(center_x + leg_spread, hip_y),
                 (center_x + leg_spread + 20, foot_y)],
                fill=(100, 100, 150, 150),
                width=15
            )

    def draw_chakra(self, name: str, position: Tuple[int, int],
                    size: int = 40, glow: bool = True):
        """Draw a chakra point"""
        x, y = position
        color = self.chakra_colors.get(name, (255, 255, 255))

        if glow:
            # Draw glow effect
            for i in range(15, 0, -1):
                alpha = int(255 * (i / 15) * 0.3)
                glow_color = (*color, alpha)
                self.draw.ellipse(
                    [x - size - i, y - size - i,
                     x + size + i, y + size + i],
                    fill=glow_color
                )

        # Draw main chakra
        self.draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(*color, 220),
            outline=(*color, 255),
            width=2
        )

        # Draw center point
        center_size = size // 3
        self.draw.ellipse(
            [x - center_size, y - center_size,
             x + center_size, y + center_size],
            fill=(255, 255, 255, 255)
        )

    def draw_meridian_flow(self, points: List[Tuple[int, int]],
                          color: Tuple[int, int, int, int],
                          width: int = 3,
                          flow_animation: bool = False):
        """Draw meridian as flowing energy line"""
        if len(points) < 2:
            return

        # Draw smooth curve through points
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]

            # Main line
            self.draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

            # Add flow indicators (small circles along path)
            if flow_animation:
                num_circles = 3
                for j in range(num_circles):
                    t = j / num_circles
                    x = int(x1 + (x2 - x1) * t)
                    y = int(y1 + (y2 - y1) * t)
                    self.draw.ellipse(
                        [x - 3, y - 3, x + 3, y + 3],
                        fill=(*color[:3], 255)
                    )

    def create_seven_chakras_diagram(self) -> Image.Image:
        """Create diagram showing all 7 chakras on body"""
        self.draw_body_outline(BodyPosition.FRONT)

        center_x = self.width // 2

        # Chakra positions (front view)
        chakra_positions = {
            'sahasrara': (center_x, 60),       # Crown
            'ajna': (center_x, 130),           # Third eye
            'vishuddha': (center_x, 220),      # Throat
            'anahata': (center_x, 400),        # Heart
            'manipura': (center_x, 550),       # Solar plexus
            'svadhisthana': (center_x, 700),   # Sacral
            'muladhara': (center_x, 850)       # Root
        }

        # Draw each chakra
        for name, pos in chakra_positions.items():
            self.draw_chakra(name, pos, size=35, glow=True)

        # Add labels
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()

        labels = {
            'sahasrara': 'Crown\nSahasrara',
            'ajna': 'Third Eye\nAjna',
            'vishuddha': 'Throat\nVishuddha',
            'anahata': 'Heart\nAnahata',
            'manipura': 'Solar Plexus\nManipura',
            'svadhisthana': 'Sacral\nSvadhisthana',
            'muladhara': 'Root\nMuladhara'
        }

        for name, pos in chakra_positions.items():
            x, y = pos
            label = labels[name]
            color = self.chakra_colors[name]

            # Draw label to the side
            label_x = x + 100
            self.draw.text(
                (label_x, y - 20),
                label,
                fill=(*color, 255),
                font=font
            )

        return self.image

    def create_meridian_diagram(self, meridian_name: str = None) -> Image.Image:
        """Create diagram showing meridian pathways"""
        self.draw_body_outline(BodyPosition.FRONT)

        if not self.anatomy_db:
            return self.image

        center_x = self.width // 2

        # Get meridians
        if meridian_name:
            meridian = self.anatomy_db.meridians.get(meridian_name)
            meridians_to_draw = [meridian] if meridian else []
        else:
            meridians_to_draw = list(self.anatomy_db.meridians.values())

        # Draw each meridian
        for meridian in meridians_to_draw:
            # Get color for this meridian's element
            color = self.element_colors.get(meridian.element, (200, 200, 200, 200))

            # Simplified meridian paths (would need detailed acupoint data for accuracy)
            # For now, draw representative flow
            if "Lung" in meridian.name:
                points = [
                    (center_x + 80, 300),   # Chest
                    (center_x + 120, 350),
                    (center_x + 150, 450),  # Arm
                    (center_x + 170, 550)   # Hand
                ]
            elif "Heart" in meridian.name:
                points = [
                    (center_x + 50, 400),   # Heart area
                    (center_x + 80, 450),
                    (center_x + 110, 520),  # Inner arm
                    (center_x + 130, 580)   # Hand
                ]
            elif "Kidney" in meridian.name:
                points = [
                    (center_x - 40, 650),   # Lower abdomen
                    (center_x - 30, 800),
                    (center_x - 20, 1000),  # Leg
                    (center_x - 10, 1200),
                    (center_x, 1400)        # Foot
                ]
            elif "Liver" in meridian.name:
                points = [
                    (center_x + 40, 650),
                    (center_x + 30, 800),
                    (center_x + 20, 1000),
                    (center_x + 10, 1200),
                    (center_x, 1400)
                ]
            elif "Spleen" in meridian.name:
                points = [
                    (center_x - 60, 700),
                    (center_x - 50, 900),
                    (center_x - 40, 1100),
                    (center_x - 30, 1350)
                ]
            else:
                # Default path
                points = [
                    (center_x, 300),
                    (center_x, 600),
                    (center_x, 900)
                ]

            # Draw meridian
            self.draw_meridian_flow(points, color, width=4, flow_animation=True)

            # Label
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except:
                font = ImageFont.load_default()

            if points:
                label_x, label_y = points[0]
                label_x += 20
                element_name = meridian.element.value if meridian.element else "N/A"
                self.draw.text(
                    (label_x, label_y),
                    f"{meridian.name}\n({element_name})",
                    fill=color,
                    font=font
                )

        return self.image

    def create_central_channel_diagram(self) -> Image.Image:
        """Create diagram of central channel (sushumna/uma)"""
        self.draw_body_outline(BodyPosition.FRONT)

        center_x = self.width // 2

        # Draw central channel (sushumna/uma)
        channel_points = [
            (center_x, 850),   # Base (muladhara)
            (center_x, 700),   # Sacral
            (center_x, 550),   # Solar
            (center_x, 400),   # Heart
            (center_x, 220),   # Throat
            (center_x, 130),   # Third eye
            (center_x, 60)     # Crown
        ]

        # Draw with gold color
        gold = (255, 215, 0, 200)
        self.draw_meridian_flow(channel_points, gold, width=8, flow_animation=True)

        # Draw ida (left, moon, cooling)
        ida_color = (100, 150, 255, 180)  # Cool blue
        ida_points = []
        for i, (x, y) in enumerate(channel_points):
            offset = 30 if i % 2 == 0 else -30
            ida_points.append((x - offset, y))

        self.draw_meridian_flow(ida_points, ida_color, width=6)

        # Draw pingala (right, sun, heating)
        pingala_color = (255, 150, 100, 180)  # Warm red
        pingala_points = []
        for i, (x, y) in enumerate(channel_points):
            offset = 30 if i % 2 == 0 else -30
            pingala_points.append((x + offset, y))

        self.draw_meridian_flow(pingala_points, pingala_color, width=6)

        # Draw chakras at intersections
        chakras = ['muladhara', 'svadhisthana', 'manipura', 'anahata',
                  'vishuddha', 'ajna', 'sahasrara']

        for chakra, (x, y) in zip(chakras, channel_points):
            self.draw_chakra(chakra, (x, y), size=30, glow=True)

        # Add title
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            font = ImageFont.load_default()

        self.draw.text(
            (self.width // 2 - 200, 30),
            "Three Channels (Nadis)",
            fill=(255, 255, 255, 255),
            font=font
        )

        # Add legend
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()

        legend_x = 50
        legend_y = 200
        self.draw.text((legend_x, legend_y), "Sushumna (Central)", fill=gold, font=font)
        self.draw.text((legend_x, legend_y + 30), "Ida (Left, Moon)", fill=ida_color, font=font)
        self.draw.text((legend_x, legend_y + 60), "Pingala (Right, Sun)", fill=pingala_color, font=font)

        return self.image

    def create_elemental_meridian_map(self) -> Image.Image:
        """Create map showing meridians grouped by element"""
        self.draw_body_outline(BodyPosition.FRONT)

        if not self.anatomy_db:
            return self.image

        # Group meridians by element
        element_groups = {}
        for meridian in self.anatomy_db.meridians.values():
            element = meridian.element
            if element not in element_groups:
                element_groups[element] = []
            element_groups[element].append(meridian)

        # Draw legend
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            font = ImageFont.load_default()
            font_small = font

        self.draw.text(
            (self.width // 2 - 150, 30),
            "Five Element Meridians",
            fill=(255, 255, 255, 255),
            font=font
        )

        # Draw element legend
        legend_x = 50
        legend_y = 1000
        y_offset = 0

        for element in [Element.WOOD, Element.FIRE, Element.EARTH,
                       Element.METAL, Element.WATER]:
            if element in element_groups:
                color = self.element_colors[element]
                meridians = element_groups[element]

                # Draw color swatch
                self.draw.rectangle(
                    [legend_x, legend_y + y_offset,
                     legend_x + 30, legend_y + y_offset + 20],
                    fill=color
                )

                # Draw element name and meridians
                text = f"{element.value.capitalize()}: "
                text += ", ".join([m.name for m in meridians])

                self.draw.text(
                    (legend_x + 40, legend_y + y_offset),
                    text,
                    fill=(255, 255, 255, 255),
                    font=font_small
                )

                y_offset += 35

        return self.image

    def save(self, filename: str):
        """Save image to file"""
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(filename)
        print(f"✅ Saved to: {filename}")

    def get_image(self) -> Image.Image:
        """Get the current image"""
        return self.image


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_complete_chakra_diagram(output_path: str = "/tmp/chakra_diagram.png"):
    """Create and save complete chakra diagram"""
    viz = MeridianVisualizer(width=1200, height=1600)
    viz.create_seven_chakras_diagram()
    viz.save(output_path)
    return output_path


def create_complete_meridian_map(output_path: str = "/tmp/meridian_map.png"):
    """Create and save complete meridian map"""
    viz = MeridianVisualizer(width=1200, height=1600)
    viz.create_elemental_meridian_map()
    viz.save(output_path)
    return output_path


def create_central_channel(output_path: str = "/tmp/central_channel.png"):
    """Create and save central channel diagram"""
    viz = MeridianVisualizer(width=1200, height=1600)
    viz.create_central_channel_diagram()
    viz.save(output_path)
    return output_path


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("MERIDIAN & ENERGETIC ANATOMY VISUALIZATION")
    print("="*70)
    print()

    output_dir = Path("/tmp/vajra_meridian_viz")
    output_dir.mkdir(exist_ok=True, parents=True)

    print("Creating visualizations...")
    print()

    # Create chakra diagram
    print("1. Seven Chakras Diagram...")
    create_complete_chakra_diagram(str(output_dir / "seven_chakras.png"))

    # Create central channel
    print("2. Central Channel (Three Nadis)...")
    create_central_channel(str(output_dir / "central_channel.png"))

    # Create meridian map
    print("3. Five Element Meridian Map...")
    create_complete_meridian_map(str(output_dir / "meridian_map.png"))

    print()
    print("="*70)
    print("VISUALIZATION COMPLETE")
    print("="*70)
    print(f"\nAll visualizations saved to: {output_dir}")
    print()
    print("May these visualizations serve healing and understanding!")
    print("Om Mani Padme Hum 🙏")
    print()
