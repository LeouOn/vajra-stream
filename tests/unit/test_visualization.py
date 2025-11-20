#!/usr/bin/env python3
"""
Test script for visualization system
Generates sample visualizations to verify system works correctly
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.energetic_visualization import (
    RothkoVisualizer,
    SacredGeometryVisualizer,
    create_chakra_meditation,
    create_seven_chakras_composition
)

def test_rothko_visualizations():
    """Test Rothko-style visualizations"""
    print("🎨 Testing Rothko Visualizations...")

    viz = RothkoVisualizer(width=1920, height=1080)
    output_dir = Path("/tmp/vajra_viz_test")
    output_dir.mkdir(exist_ok=True)

    # Test 1: Single chakra field
    print("  Creating crown chakra field (sahasrara)...")
    viz.create_chakra_field("sahasrara", include_label=True)
    viz.get_image().save(output_dir / "rothko_sahasrara_chakra.png")

    # Test 2: Seven chakras vertical
    print("  Creating seven chakras (vertical)...")
    viz.create_seven_chakras(vertical=True)
    viz.get_image().save(output_dir / "rothko_seven_chakras_vertical.png")

    # Test 3: Seven chakras horizontal
    print("  Creating seven chakras (horizontal)...")
    viz.create_seven_chakras(vertical=False)
    viz.get_image().save(output_dir / "rothko_seven_chakras_horizontal.png")

    # Test 4: Classic Rothko palette
    print("  Creating classic Rothko palette...")
    from core.energetic_visualization import RothkoLayout
    viz.create_from_palette("classic", RothkoLayout.THREE_HORIZONTAL)
    viz.get_image().save(output_dir / "rothko_classic.png")

    # Test 5: Meditative palette
    print("  Creating meditative palette...")
    viz.create_from_palette("meditative", RothkoLayout.TWO_HORIZONTAL)
    viz.get_image().save(output_dir / "rothko_meditative.png")

    print(f"  ✅ Rothko visualizations saved to {output_dir}/")

def test_sacred_geometry():
    """Test sacred geometry visualizations"""
    print("\n🔯 Testing Sacred Geometry...")

    viz = SacredGeometryVisualizer(width=1920, height=1080)
    output_dir = Path("/tmp/vajra_viz_test")
    output_dir.mkdir(exist_ok=True)

    # Test 1: Flower of Life
    print("  Creating Flower of Life...")
    viz.create_flower_of_life(
        radius=150,
        color=(138, 43, 226),  # Violet
        glow=True
    )
    viz.get_image().save(output_dir / "sacred_flower_of_life.png")

    # Test 2: Seed of Life
    print("  Creating Seed of Life...")
    viz2 = SacredGeometryVisualizer(width=1920, height=1080)
    viz2.create_seed_of_life(
        radius=200,
        color=(255, 215, 0),  # Gold
        glow=True
    )
    viz2.get_image().save(output_dir / "sacred_seed_of_life.png")

    # Test 3: Sri Yantra
    print("  Creating Sri Yantra...")
    viz3 = SacredGeometryVisualizer(width=1920, height=1080)
    viz3.create_sri_yantra_simple(
        size=800,
        color=(220, 20, 60)  # Crimson
    )
    viz3.get_image().save(output_dir / "sacred_sri_yantra.png")

    # Test 4: Combined - Seed of Life with chakra colors
    print("  Creating chakra-colored Seed of Life...")
    viz4 = SacredGeometryVisualizer(width=1920, height=1080)
    viz4.create_seed_of_life(
        radius=200,
        color=(138, 43, 226),  # Crown chakra color
        glow=True
    )
    viz4.get_image().save(output_dir / "sacred_seed_chakra.png")

    print(f"  ✅ Sacred geometry saved to {output_dir}/")

def test_meditation_sequence():
    """Test creating a meditation sequence"""
    print("\n🧘 Testing Meditation Sequence...")

    output_dir = Path("/tmp/vajra_viz_test/meditation_sequence")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Create 7-image chakra meditation sequence
    chakras = [
        ("muladhara", "Root"),
        ("svadhisthana", "Sacral"),
        ("manipura", "Solar Plexus"),
        ("anahata", "Heart"),
        ("vishuddha", "Throat"),
        ("ajna", "Third Eye"),
        ("sahasrara", "Crown")
    ]
    images = []

    for i, (chakra_sanskrit, chakra_english) in enumerate(chakras, 1):
        print(f"  Creating {chakra_english} ({chakra_sanskrit}) meditation image...")
        img = create_chakra_meditation(chakra_sanskrit, width=1920, height=1080)
        output_file = output_dir / f"{i:02d}_{chakra_sanskrit}_meditation.png"
        img.save(output_file)
        images.append(output_file)

    print(f"  ✅ Created {len(images)} meditation images in {output_dir}/")

def main():
    """Run all visualization tests"""
    print("="*70)
    print("VAJRA STREAM VISUALIZATION SYSTEM TEST")
    print("="*70)
    print()

    try:
        test_rothko_visualizations()
        test_sacred_geometry()
        test_meditation_sequence()

        print()
        print("="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print()
        print("Output directory: /tmp/vajra_viz_test/")
        print()
        print("Generated visualizations:")

        output_dir = Path("/tmp/vajra_viz_test")
        for img_file in sorted(output_dir.glob("*.png")):
            print(f"  • {img_file.name}")

        # List meditation sequence
        med_dir = output_dir / "meditation_sequence"
        if med_dir.exists():
            print("\nMeditation sequence:")
            for img_file in sorted(med_dir.glob("*.png")):
                print(f"  • meditation_sequence/{img_file.name}")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
