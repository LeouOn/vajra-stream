"""
Visual Meditation Display System
Display Rothko-style images for contemplative practice
"""

import os
import time
from typing import Optional, List
from pathlib import Path

from PIL import Image


class MeditationDisplay:
    """
    Display meditation images with controllable presentation
    Supports multiple backends for cross-platform compatibility
    """

    def __init__(self, width: int = 1920, height: int = 1080, fullscreen: bool = True):
        """
        Initialize meditation display

        Args:
            width: Display width
            height: Display height
            fullscreen: Start in fullscreen mode
        """
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.backend = None
        self.window = None

        self._init_backend()

    def _init_backend(self):
        """Initialize the best available display backend"""
        try:
            import pygame
            pygame.init()
            pygame.display.set_caption("Vajra.Stream - Visual Meditation")
            self.backend = 'pygame'
            self.window = pygame.display.set_mode(
                (self.width, self.height),
                pygame.FULLSCREEN if self.fullscreen else 0
            )
        except ImportError:
            try:
                import tkinter as tk
                from tkinter import Canvas, Label, TclError
                self.backend = 'tkinter'
                self._setup_tkinter()
            except ImportError:
                self.backend = 'pillow'

    def _setup_tkinter(self):
        """Setup tkinter backend"""
        try:
            self.root = tk.Tk()
            self.root.title("Vajra.Stream - Visual Meditation")
            self.canvas = Canvas(self.root, width=self.width, height=self.height)
            self.canvas.pack()
            if self.fullscreen:
                self.root.attributes('-fullscreen', True)
        except Exception:
            self.backend = 'pillow'

    def display_image(self, image_path: str, duration: int = 0):
        """
        Display a single image

        Args:
            image_path: Path to image file
            duration: Display duration in seconds (0 = until closed)
        """
        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            return False

        img = Image.open(image_path)

        if self.backend == 'pygame':
            self._display_pygame(img)
        elif self.backend == 'tkinter':
            self._display_tkinter(img, duration)
        else:
            self._display_pillow(img, duration)

        return True

    def _display_pygame(self, img: Image):
        """Display using pygame"""
        try:
            import pygame

            surface = pygame.display.get_surface()
            pygame.pixelcopy.array_to_surface(surface, img.resize((self.width, self.height)).convert('RGB'))
            pygame.display.flip()

            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                        running = False

        except Exception as e:
            print(f"Pygame display error: {e}")
            self._display_pillow(img, 0)

    def _display_tkinter(self, img: Image, duration: int):
        """Display using tkinter"""
        try:
            img_display = img.resize((self.width, self.height))
            photo = Image.PhotoImage(img_display)

            self.canvas.create_image(self.width // 2, self.height // 2, image=photo)
            self.canvas.update()

            if duration > 0:
                self.root.after(int(duration * 1000), self.root.quit)
            else:
                self.root.mainloop()
        except Exception as e:
            print(f"Tkinter display error: {e}")
            self._display_pillow(img, duration)

    def _display_pillow(self, img: Image, duration: int):
        """Display using PIL/Pillow (fallback)"""
        try:
            img_resized = img.resize((min(img.width, 1920), min(img.height, 1080)))
            img_resized.show(title="Vajra.Stream - Visual Meditation")
            if duration > 0:
                time.sleep(duration)
        except Exception:
            print("Visual display not available in this environment")
            print(f"Saved image would be: {img.size}")

    def display_sequence(self, image_paths: List[str], duration_per: int = 5,
                         transition: str = 'fade', loop: bool = True):
        """
        Display a sequence of images with transitions

        Args:
            image_paths: List of image file paths
            duration_per: Seconds per image
            transition: 'none', 'fade', or 'instant'
            loop: Loop the sequence
        """
        if not image_paths:
            return

        loop_count = 0
        while loop or loop_count == 0:
            for i, path in enumerate(image_paths):
                if self.backend == 'pygame':
                    if not self._handle_events():
                        return
                elif self.backend == 'tkinter':
                    self.root.update()

                print(f"Displaying: {os.path.basename(path)}")
                self.display_image(path, duration_per)

                if transition == 'fade' and i < len(image_paths) - 1:
                    self._fade_transition(duration=1)

            loop_count += 1

        print(f"Displayed {len(image_paths)} images x {loop_count} iterations")

    def _handle_events(self) -> bool:
        """Handle pygame events, return False to quit"""
        try:
            import pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    return False
            return True
        except:
            return True

    def _fade_transition(self, duration: float = 1.0):
        """Fade transition (simplified)"""
        time.sleep(duration)

    def close(self):
        """Close the display"""
        if self.backend == 'pygame':
            import pygame
            pygame.quit()
        elif self.backend == 'tkinter':
            try:
                self.root.quit()
            except:
                pass

    def save_meditation_session(self, image_paths: List[str], output_dir: str = './generated/meditation_sessions'):
        """Save a meditation session configuration"""
        import json
        from datetime import datetime

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_file = os.path.join(output_dir, f'session_{timestamp}.json')

        session_data = {
            'created': datetime.now().isoformat(),
            'image_count': len(image_paths),
            'images': [os.path.abspath(p) for p in image_paths]
        }

        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        return session_file


def quick_display(theme: str = 'peace', count: int = 5, duration_per: int = 10):
    """
    Quick display of meditation images

    Args:
        theme: Meditation theme
        count: Number of images
        duration_per: Seconds per image
    """
    from core.rothko_generator import RothkoGenerator

    generator = RothkoGenerator()
    paths = generator.generate_meditation_sequence(theme, count)

    display = MeditationDisplay()
    display.display_sequence(paths, duration_per=duration_per, loop=False)
    display.close()


def display_chakra_series():
    """Display the chakra visualization series"""
    from core.rothko_generator import RothkoGenerator

    generator = RothkoGenerator()
    paths = generator.generate_chakra_series()

    display = MeditationDisplay()
    display.display_sequence(paths, duration_per=15, loop=False)
    display.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Vajra.Stream Visual Meditation Display')
    parser.add_argument('--theme', type=str, default='peace', help='Meditation theme')
    parser.add_argument('--count', type=int, default=5, help='Number of images')
    parser.add_argument('--duration', type=int, default=10, help='Seconds per image')
    parser.add_argument('--chakra', action='store_true', help='Display chakra series')
    parser.add_argument('--fullscreen', action='store_true', default=True, help='Fullscreen mode')

    args = parser.parse_args()

    if args.chakra:
        print("Displaying chakra series...")
        display_chakra_series()
    else:
        print(f"Displaying {args.count} {args.theme} meditation images...")
        quick_display(args.theme, args.count, args.duration)

    print("Display session complete.")