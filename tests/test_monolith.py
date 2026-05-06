#!/usr/bin/env python3
"""
Test the modular monolith architecture
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from container import container


def test_scalar_waves():
    """Test scalar wave service"""
    print("🧪 Testing Scalar Waves Module...")

    scalar = container.scalar_waves

    # Generate waves
    result = scalar.generate("qrng", 1000, 1.0)  # Use full intensity
    assert result['count'] > 0  # May be throttled
    assert result['method'] == 'qrng'
    assert 'mops' in result

    print(f"   ✅ Generated {result['count']} values at {result['mops']:.2f} MMOPS")

    # Get thermal status
    thermal = scalar.get_thermal_status()
    assert 'temperature' in thermal
    assert 'status' in thermal
    print(f"   ✅ Thermal: {thermal['temperature']:.1f}°C ({thermal['status']})")


def test_radionics():
    """Test radionics service"""
    print("\n🧪 Testing Radionics Module...")

    radionics = container.radionics

    # Get intentions
    intentions = radionics.get_available_intentions()
    assert len(intentions) > 0
    print(f"   ✅ {len(intentions)} intentions available")

    # Broadcast healing
    result = radionics.broadcast_healing("Test Target", 1, 528)
    assert 'session_id' in result
    assert result['target'] == 'Test Target'
    print(f"   ✅ Healing broadcast configured (528 Hz)")


def test_anatomy():
    """Test anatomy service"""
    print("\n🧪 Testing Anatomy Module...")

    anatomy = container.anatomy

    # Get chakra info
    chakras = anatomy.get_chakra_info()
    assert len(chakras) == 7
    print(f"   ✅ {len(chakras)} chakras loaded")

    # Get meridian info
    meridians = anatomy.get_meridian_info()
    assert len(meridians) == 12
    print(f"   ✅ {len(meridians)} meridians loaded")

    # Generate visualization
    path = anatomy.visualize_chakras(width=800, height=1000)
    assert Path(path).exists()
    print(f"   ✅ Chakra diagram: {path}")


def test_blessings():
    """Test blessings service"""
    print("\n🧪 Testing Blessings Module...")

    blessings = container.blessings

    # Generate blessing
    blessing = blessings.generate_blessing(
        "All Beings",
        "peace and happiness",
        "universal"
    )
    assert 'blessing_text' in blessing
    assert len(blessing['blessing_text']) > 0
    print(f"   ✅ Blessing generated ({len(blessing['blessing_text'])} chars)")

    # Get traditions
    traditions = blessings.get_available_traditions()
    assert len(traditions) > 0
    print(f"   ✅ {len(traditions)} traditions available")


def test_event_bus():
    """Test event bus communication"""
    print("\n🧪 Testing Event Bus...")

    from modules.interfaces import ScalarWavesGenerated
    from datetime import datetime

    events_received = []

    def handler(event):
        events_received.append(event)

    # Subscribe
    container.event_bus.subscribe(ScalarWavesGenerated, handler)

    # Publish
    event = ScalarWavesGenerated(
        timestamp=datetime.now(),
        event_id="test-123",
        method="qrng",
        count=1000,
        mops=1.5
    )
    container.event_bus.publish(event)

    # Check
    assert len(events_received) == 1
    assert events_received[0].method == "qrng"
    print(f"   ✅ Event published and received")

    # Unsubscribe
    container.event_bus.unsubscribe(ScalarWavesGenerated, handler)


def test_full_integration():
    """Test complete healing session"""
    print("\n🧪 Testing Full Integration...")

    # Use VajraStream wrapper
    from vajra_stream import VajraStream
    vs = VajraStream()

    # Generate scalar waves
    scalar_result = vs.generate_scalar_waves("hybrid", 1000, 0.5)
    assert 'mops' in scalar_result
    print(f"   ✅ Scalar waves: {scalar_result['mops']:.2f} MMOPS")

    # Broadcast healing
    healing_result = vs.broadcast_healing("Integration Test", 1, 528)
    assert 'status' in healing_result
    print(f"   ✅ Healing broadcast configured")

    # Generate blessing
    blessing = vs.generate_blessing("Integration Test", "healing")
    assert len(blessing) > 0
    print(f"   ✅ Blessing generated")

    # Visualize chakras
    chakra_path = vs.visualize_chakras()
    assert Path(chakra_path).exists()
    print(f"   ✅ Visualization: {chakra_path}")


def main():
    """Run all tests"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║          Vajra Stream Modular Monolith Test Suite             ║
╚════════════════════════════════════════════════════════════════╝
""")

    try:
        test_scalar_waves()
        test_radionics()
        test_anatomy()
        test_blessings()
        test_event_bus()
        test_full_integration()

        print("""
╔════════════════════════════════════════════════════════════════╗
║                    ALL TESTS PASSED ✅                         ║
╚════════════════════════════════════════════════════════════════╝

The modular monolith is working correctly!

Key Benefits Demonstrated:
✅ Clear module boundaries (ports/adapters)
✅ Dependency injection container
✅ In-process event bus (no network calls)
✅ Simple integration
✅ Easy to test

May all beings benefit! 🙏
""")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
