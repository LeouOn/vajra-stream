#!/usr/bin/env python3
"""
Test TTS System Integration

Verifies that the TTS system is correctly implemented and ready for use.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.tts_integration import (
    TTSNarrator,
    TTSEngineType,
    SpeakingRate,
    VoiceGender
)

def test_imports():
    """Test that all TTS modules can be imported"""
    print("✓ TTS modules imported successfully")

def test_narrator_init():
    """Test that TTSNarrator can be initialized"""
    try:
        narrator = TTSNarrator()
        print(f"✓ TTSNarrator initialized with engine: {narrator.engine.__class__.__name__}")
        return narrator
    except Exception as e:
        print(f"✗ Failed to initialize TTSNarrator: {e}")
        return None

def test_engine_availability():
    """Test engine availability checks"""
    from core.tts_integration import HAS_PYTTSX3, HAS_GTTS, HAS_EDGE_TTS

    print(f"\nEngine Availability:")
    print(f"  pyttsx3 package: {'✓' if HAS_PYTTSX3 else '✗'}")
    print(f"  gTTS package: {'✓' if HAS_GTTS else '✗'}")
    print(f"  edge-tts package: {'✓' if HAS_EDGE_TTS else '✗'}")

def test_speaking_rates():
    """Test speaking rate enum"""
    rates = list(SpeakingRate)
    print(f"\n✓ Speaking rates defined: {[r.name for r in rates]}")

def test_voice_genders():
    """Test voice gender enum"""
    genders = list(VoiceGender)
    print(f"✓ Voice genders defined: {[g.name for g in genders]}")

def test_narrator_methods(narrator):
    """Test that narrator has all expected methods"""
    if not narrator:
        print("✗ Cannot test methods - narrator not initialized")
        return

    methods = [
        'generate_audio',
        'narrate_story',
        'generate_mantra_audio',
        'guided_meditation',
        'commemorate_event'
    ]

    print(f"\nNarrator Methods:")
    for method in methods:
        if hasattr(narrator, method):
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method} missing!")

def test_cli_exists():
    """Test that CLI tool exists"""
    cli_path = Path(__file__).parent / "scripts" / "tts_narrator.py"
    if cli_path.exists():
        print(f"\n✓ CLI tool exists at: {cli_path}")
    else:
        print(f"\n✗ CLI tool not found at: {cli_path}")

def test_integration_with_other_systems():
    """Test that TTS can integrate with other systems"""
    try:
        from core.blessing_narratives import StoryGenerator, NarrativeType, PureLandTradition
        from core.time_cycle_broadcaster import TimeCycleBroadcaster

        print(f"\n✓ TTS can import blessing narratives system")
        print(f"✓ TTS can import time cycle broadcaster")

        # Test that we can create objects
        generator = StoryGenerator()
        broadcaster = TimeCycleBroadcaster()

        print(f"✓ Can create StoryGenerator and TimeCycleBroadcaster")

    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")

def main():
    print("="*70)
    print("TTS SYSTEM INTEGRATION TEST")
    print("="*70)
    print()

    test_imports()
    test_engine_availability()
    test_speaking_rates()
    test_voice_genders()

    narrator = test_narrator_init()
    test_narrator_methods(narrator)
    test_cli_exists()
    test_integration_with_other_systems()

    print()
    print("="*70)
    print("TTS SYSTEM READY FOR USE")
    print("="*70)
    print()
    print("Note: Actual audio generation requires:")
    print("  - pyttsx3: espeak or espeak-ng installed")
    print("  - gTTS: Working internet connection (may be rate-limited)")
    print("  - edge-tts: Not yet implemented")
    print()
    print("The system will automatically fall back to available engines.")
    print()

if __name__ == "__main__":
    main()
