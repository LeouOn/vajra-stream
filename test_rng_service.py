#!/usr/bin/env python3
"""
Test script for RNG Attunement Service
Tests the service in isolation to verify functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.core.services.rng_attunement_service import (
    RNGAttunementService,
    NeedleState,
    ReadingQuality
)


def test_rng_service():
    """Test RNG Attunement service functionality"""

    print("=" * 60)
    print("RNG Attunement Service Test")
    print("=" * 60)
    print()

    # Create service instance
    print("1. Creating RNG service instance...")
    service = RNGAttunementService()
    print("✅ Service created successfully")
    print()

    # Create session
    print("2. Creating attunement session...")
    session_id = service.create_session(
        baseline_tone_arm=5.0,
        sensitivity=1.0
    )
    print(f"✅ Session created: {session_id}")
    print()

    # Generate 10 readings
    print("3. Generating 10 readings...")
    print("-" * 60)
    readings = []
    for i in range(10):
        reading = service.get_reading(session_id)
        if reading is None:
            print(f"❌ Failed to get reading {i+1}")
            return False

        readings.append(reading)

        # Print reading details
        print(f"\nReading {i+1}:")
        print(f"  Timestamp:    {reading.timestamp:.2f}")
        print(f"  Raw Value:    {reading.raw_value:.4f}")
        print(f"  Tone Arm:     {reading.tone_arm:.2f} (0-10)")
        print(f"  Needle Pos:   {reading.needle_position:+6.1f} (-100 to +100)")
        print(f"  Needle State: {reading.needle_state.value.upper()}")
        print(f"  Quality:      {reading.quality.value.upper()}")
        print(f"  Entropy:      {reading.entropy:.3f}")
        print(f"  Coherence:    {reading.coherence:.3f}")
        print(f"  Trend:        {reading.trend:+.2f}")
        print(f"  FN Score:     {reading.floating_needle_score:.3f}")

        # Special indicators
        if reading.needle_state == NeedleState.FLOATING:
            print(f"  🎯 FLOATING NEEDLE DETECTED!")
        if reading.floating_needle_score > 0.8:
            print(f"  ⭐ HIGH FN SCORE!")
        if reading.needle_state == NeedleState.ROCKSLAM:
            print(f"  ⚡ ROCKSLAM - Heavy charge!")

    print("\n" + "-" * 60)
    print("✅ All 10 readings generated successfully")
    print()

    # Get session summary
    print("4. Getting session summary...")
    summary = service.get_session_summary(session_id)

    if summary is None:
        print("❌ Failed to get session summary")
        return False

    print(f"✅ Session Summary:")
    print(f"  Total Readings:       {summary['total_readings']}")
    print(f"  Floating Needles:     {summary['floating_needle_count']}")
    print(f"  Duration:             {summary['duration_seconds']:.1f}s")
    print(f"  Avg Tone Arm:         {summary['avg_tone_arm']:.2f}")
    print(f"  Avg Coherence:        {summary['avg_coherence']:.3f}")
    print(f"  Avg Entropy:          {summary['avg_entropy']:.3f}")
    print(f"  Session Active:       {summary['is_active']}")
    print()

    print("  Needle State Distribution:")
    for state, count in summary['needle_state_distribution'].items():
        if count > 0:
            print(f"    {state:12s}: {count}")
    print()

    print("  Quality Distribution:")
    for quality, count in summary['quality_distribution'].items():
        if count > 0:
            print(f"    {quality:12s}: {count}")
    print()

    # Stop session
    print("5. Stopping session...")
    success = service.stop_session(session_id)
    if success:
        print("✅ Session stopped successfully")
    else:
        print("❌ Failed to stop session")
        return False
    print()

    # Verify session is stopped
    print("6. Verifying session is inactive...")
    reading_after_stop = service.get_reading(session_id)
    if reading_after_stop is None:
        print("✅ Correctly returns None for stopped session")
    else:
        print("❌ Session still generating readings after stop!")
        return False
    print()

    # Validation checks
    print("7. Running validation checks...")
    all_valid = True

    # Check all readings have valid ranges
    for i, reading in enumerate(readings):
        if not (0.0 <= reading.raw_value <= 1.0):
            print(f"❌ Reading {i+1}: raw_value out of range: {reading.raw_value}")
            all_valid = False

        if not (0.0 <= reading.tone_arm <= 10.0):
            print(f"❌ Reading {i+1}: tone_arm out of range: {reading.tone_arm}")
            all_valid = False

        if not (-100 <= reading.needle_position <= 100):
            print(f"❌ Reading {i+1}: needle_position out of range: {reading.needle_position}")
            all_valid = False

        if not isinstance(reading.needle_state, NeedleState):
            print(f"❌ Reading {i+1}: invalid needle_state type")
            all_valid = False

        if not isinstance(reading.quality, ReadingQuality):
            print(f"❌ Reading {i+1}: invalid quality type")
            all_valid = False

        if not (0.0 <= reading.coherence <= 1.0):
            print(f"❌ Reading {i+1}: coherence out of range: {reading.coherence}")
            all_valid = False

        if not (0.0 <= reading.entropy <= 1.0):
            print(f"❌ Reading {i+1}: entropy out of range: {reading.entropy}")
            all_valid = False

        if not (0.0 <= reading.floating_needle_score <= 1.0):
            print(f"❌ Reading {i+1}: FN score out of range: {reading.floating_needle_score}")
            all_valid = False

    if all_valid:
        print("✅ All readings have valid values")
    print()

    print("=" * 60)
    print("TEST RESULT: " + ("✅ ALL TESTS PASSED" if all_valid else "❌ SOME TESTS FAILED"))
    print("=" * 60)
    print()

    return all_valid


if __name__ == "__main__":
    try:
        success = test_rng_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
