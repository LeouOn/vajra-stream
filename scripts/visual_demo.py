#!/usr/bin/env python3
"""
Vajra.Stream Visual Demo
Simple demonstration of visual system
"""

import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.visual_renderer_simple import SimpleVisualRenderer


def main():
    """
    Run visual demonstration
    """
    print("\n" + "="*60)
    print("VAJRA.STREAM VISUAL DEMONSTRATION")
    print("="*60)

    renderer = SimpleVisualRenderer()

    # Demo options
    print("\nSelect visualization type:")
    print("1. Rotating Mandala")
    print("2. Flower of Life Pattern")
    print("3. Concentric Circles")

    try:
        choice = int(input("\nEnter choice (1-3): "))
    except (ValueError, KeyboardInterrupt):
        print("\nExiting...")
        return

    print(f"\nStarting {choice} visualization...")
    print("Press Ctrl+C to stop\n")

    # Run selected visualization with duration option
    duration = 30  # Default 30 seconds
    try:
        duration_input = input("\nEnter duration in seconds (default 30): ")
        if duration_input.strip():
            duration = int(duration_input)
    except (ValueError, KeyboardInterrupt):
        print("Using default duration of 30 seconds")

    # Run selected visualization
    if choice == 1:
        renderer.animate_mandala(duration_seconds=duration, intention="peace and harmony")
    elif choice == 2:
        renderer.animate_flower_of_life(duration_seconds=duration, intention="growth and transformation")
    elif choice == 3:
        renderer.animate_concentric_circles(duration_seconds=duration, intention="unity and wholeness")
    else:
        print("\nInvalid choice. Running mandala by default...")
        renderer.animate_mandala(duration_seconds=duration, intention="peace and harmony")

    print("\nVisualization complete!")
    print("May this practice benefit all beings. 🙏")


if __name__ == "__main__":
    main()