"""
Vajra.Stream - Mark Rothko Style Visual Generator
Creates contemplative color field images for meditation and visual dharma practice
Inspired by Rothko's approach to color, light, and spiritual experience
"""

from PIL import Image, ImageDraw, ImageFilter
import random
import colorsys
from typing import Tuple, List, Optional
import os


class RothkoGenerator:
    """
    Generate Rothko-style color field paintings
    Soft edges, luminous colors, contemplative compositions
    """

    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

        # Color palettes inspired by spiritual themes
        self.PALETTES = {
            'compassion': [
                # Pinks, soft reds, warm whites
                (255, 182, 193),  # Light pink
                (255, 105, 180),  # Hot pink
                (255, 228, 225),  # Misty rose
                (220, 20, 60),    # Crimson
            ],
            'wisdom': [
                # Deep blues, purples, indigos
                (25, 25, 112),    # Midnight blue
                (75, 0, 130),     # Indigo
                (138, 43, 226),   # Blue violet
                (230, 230, 250),  # Lavender
            ],
            'peace': [
                # Blues, soft greens, white
                (135, 206, 235),  # Sky blue
                (176, 224, 230),  # Powder blue
                (152, 251, 152),  # Pale green
                (245, 245, 220),  # Beige
            ],
            'awakening': [
                # Golds, oranges, warm yellows
                (255, 215, 0),    # Gold
                (255, 140, 0),    # Dark orange
                (255, 228, 181),  # Moccasin
                (255, 250, 205),  # Lemon chiffon
            ],
            'emptiness': [
                # Grays, blacks, whites - void nature
                (47, 79, 79),     # Dark slate gray
                (112, 128, 144),  # Slate gray
                (211, 211, 211),  # Light gray
                (245, 245, 245),  # White smoke
            ],
            'earth': [
                # Browns, ochres, earth tones
                (139, 69, 19),    # Saddle brown
                (205, 133, 63),   # Peru
                (222, 184, 135),  # Burlywood
                (245, 222, 179),  # Wheat
            ],
            'transcendence': [
                # Deep reds, blacks, golds - Tibetan thangka colors
                (139, 0, 0),      # Dark red
                (220, 20, 60),    # Crimson
                (255, 215, 0),    # Gold
                (25, 25, 25),     # Near black
            ],
            'rainbow_body': [
                # Spectrum colors for rainbow body meditation
                (255, 0, 0),      # Red
                (255, 127, 0),    # Orange
                (255, 255, 0),    # Yellow
                (0, 255, 0),      # Green
                (0, 0, 255),      # Blue
                (75, 0, 130),     # Indigo
                (148, 0, 211),    # Violet
            ]
        }

    def create_soft_rectangle(self, draw, bbox: Tuple[int, int, int, int],
                             color: Tuple[int, int, int], alpha: int = 230) -> Image:
        """
        Create a soft-edged rectangle with gradual alpha blend
        """
        x1, y1, x2, y2 = bbox

        # Create a temporary image for this rectangle
        temp = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp)

        # Draw the base rectangle
        temp_draw.rectangle(bbox, fill=color + (alpha,))

        # Apply Gaussian blur for soft edges
        temp = temp.filter(ImageFilter.GaussianBlur(radius=30))

        return temp

    def add_texture(self, img: Image, intensity: float = 0.1) -> Image:
        """
        Add subtle texture variation (like canvas texture)
        """
        pixels = img.load()

        for i in range(0, self.width, 3):
            for j in range(0, self.height, 3):
                if random.random() < intensity:
                    # Get current pixel
                    r, g, b, a = pixels[i, j]

                    # Add slight variation
                    variation = random.randint(-10, 10)
                    r = max(0, min(255, r + variation))
                    g = max(0, min(255, g + variation))
                    b = max(0, min(255, b + variation))

                    pixels[i, j] = (r, g, b, a)

        return img

    def adjust_luminosity(self, color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
        """
        Adjust color luminosity while preserving hue
        factor > 1 makes it lighter, < 1 makes it darker
        """
        r, g, b = [x / 255.0 for x in color]
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        # Adjust lightness
        l = max(0, min(1, l * factor))

        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return tuple(int(x * 255) for x in (r, g, b))

    def generate_rothko(self, theme: str = 'compassion',
                       num_bands: int = 3,
                       variation: bool = True,
                       seed: Optional[int] = None) -> Image:
        """
        Generate a Rothko-style composition

        Args:
            theme: Color palette theme
            num_bands: Number of horizontal color bands (2-5)
            variation: Add subtle variations
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)

        # Get palette
        palette = self.PALETTES.get(theme, self.PALETTES['compassion'])

        # Create base image
        img = Image.new('RGBA', (self.width, self.height), (255, 255, 255, 255))

        # Choose background color (usually darkest or lightest)
        bg_color = random.choice(palette)
        img_bg = Image.new('RGBA', (self.width, self.height), bg_color + (255,))

        # Calculate band heights
        margin_top = int(self.height * 0.05)
        margin_bottom = int(self.height * 0.05)
        margin_side = int(self.width * 0.05)

        available_height = self.height - margin_top - margin_bottom
        band_height = available_height // num_bands

        # Randomly select colors from palette
        band_colors = random.sample(palette, min(num_bands, len(palette)))

        # Add variation to colors
        if variation:
            band_colors = [
                self.adjust_luminosity(c, random.uniform(0.8, 1.2))
                for c in band_colors
            ]

        # Create bands
        layers = [img_bg]
        current_y = margin_top

        for i, color in enumerate(band_colors):
            # Add some randomness to band positioning
            if variation and i > 0:
                offset = random.randint(-20, 20)
                current_y += offset

            # Random height variation
            if variation:
                height_var = int(band_height * random.uniform(0.9, 1.1))
            else:
                height_var = band_height

            # Create band
            x1 = margin_side + random.randint(-10, 10) if variation else margin_side
            y1 = current_y
            x2 = self.width - margin_side + random.randint(-10, 10) if variation else self.width - margin_side
            y2 = current_y + height_var

            # Create soft rectangle
            band = self.create_soft_rectangle(
                None,
                (x1, y1, x2, y2),
                color,
                alpha=random.randint(200, 240) if variation else 230
            )

            layers.append(band)
            current_y = y2

        # Composite all layers
        result = layers[0]
        for layer in layers[1:]:
            result = Image.alpha_composite(result, layer)

        # Add subtle texture
        if variation:
            result = self.add_texture(result, intensity=0.05)

        # Convert to RGB
        final = Image.new('RGB', (self.width, self.height), (255, 255, 255))
        final.paste(result, (0, 0), result)

        return final

    def generate_meditation_sequence(self, theme: str, count: int = 5,
                                    output_dir: str = './generated/rothko') -> List[str]:
        """
        Generate a sequence of related images for meditation progression
        """
        os.makedirs(output_dir, exist_ok=True)

        paths = []
        for i in range(count):
            img = self.generate_rothko(theme, num_bands=random.randint(2, 4))
            filename = f"{theme}_{i+1:02d}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath, quality=95)
            paths.append(filepath)
            print(f"Generated: {filepath}")

        return paths

    def generate_chakra_series(self, output_dir: str = './generated/rothko/chakras') -> List[str]:
        """
        Generate one image for each chakra
        """
        os.makedirs(output_dir, exist_ok=True)

        chakra_colors = {
            'root': [(255, 0, 0), (139, 0, 0), (205, 92, 92)],
            'sacral': [(255, 140, 0), (255, 165, 0), (255, 200, 124)],
            'solar_plexus': [(255, 255, 0), (255, 215, 0), (255, 250, 205)],
            'heart': [(0, 255, 0), (152, 251, 152), (144, 238, 144)],
            'throat': [(0, 191, 255), (135, 206, 250), (176, 224, 230)],
            'third_eye': [(75, 0, 130), (138, 43, 226), (216, 191, 216)],
            'crown': [(148, 0, 211), (218, 112, 214), (255, 250, 250)]
        }

        paths = []
        for chakra_name, colors in chakra_colors.items():
            # Temporarily add to palettes
            self.PALETTES[chakra_name] = colors

            img = self.generate_rothko(chakra_name, num_bands=3, variation=True)
            filename = f"chakra_{chakra_name}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath, quality=95)
            paths.append(filepath)
            print(f"Generated chakra: {filepath}")

        return paths

    def generate_for_mood(self, intention: str) -> Image:
        """
        Generate image based on intention/mood keywords
        """
        intention_lower = intention.lower()

        # Map keywords to themes
        theme_mapping = {
            'love': 'compassion',
            'compassion': 'compassion',
            'peace': 'peace',
            'calm': 'peace',
            'wisdom': 'wisdom',
            'insight': 'wisdom',
            'awakening': 'awakening',
            'enlightenment': 'awakening',
            'ground': 'earth',
            'stability': 'earth',
            'void': 'emptiness',
            'emptiness': 'emptiness',
            'transcend': 'transcendence',
            'rainbow': 'rainbow_body'
        }

        # Find matching theme
        theme = 'compassion'  # default
        for keyword, theme_name in theme_mapping.items():
            if keyword in intention_lower:
                theme = theme_name
                break

        return self.generate_rothko(theme, num_bands=random.randint(2, 4))


def create_display_window(img: Image, title: str = "Vajra.Stream - Visual Meditation"):
    """
    Display image in a window for contemplation
    (Requires display - for local use)
    """
    try:
        img.show(title=title)
    except:
        print("Display not available (running headless)")


if __name__ == "__main__":
    print("Testing Rothko Generator")
    print("=" * 60)

    generator = RothkoGenerator(width=1920, height=1080)

    # Test each theme
    themes = ['compassion', 'wisdom', 'peace', 'awakening', 'emptiness', 'transcendence']

    output_dir = './generated/rothko/test'
    os.makedirs(output_dir, exist_ok=True)

    for theme in themes:
        print(f"Generating {theme}...")
        img = generator.generate_rothko(theme, num_bands=3)
        filepath = os.path.join(output_dir, f"{theme}.png")
        img.save(filepath, quality=95)
        print(f"  Saved: {filepath}")

    # Generate chakra series
    print("\nGenerating chakra series...")
    generator.generate_chakra_series()

    print("\n✓ Rothko generator test complete")
    print(f"  Images saved to: {output_dir}")
