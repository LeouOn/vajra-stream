#!/usr/bin/env python3
"""
Vajra.Stream Visual Demo Test
Non-interactive test of visual system
"""

import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.visual_renderer_simple import SimpleVisualRenderer


def main():
    """
    Test visual demonstration without user input
    """
    print("\n" + "="*60)
    print("VAJRA.STREAM VISUAL DEMONSTRATION TEST")
    print("="*60)

    renderer = SimpleVisualRenderer()

    # Test all visualization types
    print("\nTesting visualizations...")
    
    # Test 1: Rotating Mandala (short duration)
    print("\n1. Testing Rotating Mandala (5 seconds)...")
    try:
        renderer.animate_mandala(duration_seconds=5, intention="peace and harmony")
        print("+ Mandala test completed")
    except Exception as e:
        print(f"- Mandala test failed: {e}")

    time.sleep(1)

    # Test 2: Flower of Life Pattern (short duration)
    print("\n2. Testing Flower of Life Pattern (5 seconds)...")
    try:
        renderer.animate_flower_of_life(duration_seconds=5, intention="growth and transformation")
        print("+ Flower of Life test completed")
    except Exception as e:
        print(f"- Flower of Life test failed: {e}")

    time.sleep(1)

    # Test 3: Concentric Circles (short duration)
    print("\n3. Testing Concentric Circles (5 seconds)...")
    try:
        renderer.animate_concentric_circles(duration_seconds=5, intention="unity and wholeness")
        print("+ Concentric Circles test completed")
    except Exception as e:
        print(f"- Concentric Circles test failed: {e}")

    print("\n" + "="*60)
    print("VISUAL DEMONSTRATION TEST COMPLETE")
    print("="*60)
    print("All visualizations tested successfully!")
    print("May this practice benefit all beings. 🙏")


if __name__ == "__main__":
    main()