#!/usr/bin/env python3
"""
Quick test of all Vajra.Stream modules
Tests functionality without requiring audio output or LLM
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_astrology():
    """Test astrology module"""
    print("\n" + "="*60)
    print("Testing Astrology Module")
    print("="*60)

    try:
        from core.astrology import AstrologicalCalculator
        from datetime import datetime

        astro = AstrologicalCalculator()

        # Get current data
        now = datetime.now()
        data = astro.get_current_energetics(now)

        print(f"✓ Moon Phase: {data['moon_phase']['phase_name']}")
        print(f"✓ Lunar Mansion: {data['lunar_mansion']['name']}")
        print(f"✓ Sun Position: {data['planetary_positions']['sun']['formatted']}")

        # Get recommended frequencies
        freqs = astro.recommend_frequencies_for_time(now)
        print(f"✓ Recommended {len(freqs)} frequencies")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_rothko():
    """Test Rothko visual generator"""
    print("\n" + "="*60)
    print("Testing Rothko Visual Generator")
    print("="*60)

    try:
        from core.rothko_generator import RothkoGenerator

        gen = RothkoGenerator(width=800, height=600)

        # Generate a test image
        img = gen.generate_rothko('compassion', num_bands=3)

        print(f"✓ Generated image: {img.size[0]}x{img.size[1]}")
        print(f"✓ Image mode: {img.mode}")

        # Save test image
        output_dir = './generated/rothko/test'
        os.makedirs(output_dir, exist_ok=True)
        filepath = f"{output_dir}/test_compassion.png"
        img.save(filepath)

        print(f"✓ Saved to: {filepath}")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm():
    """Test LLM integration"""
    print("\n" + "="*60)
    print("Testing LLM Integration")
    print("="*60)

    try:
        from core.llm_integration import LLMIntegration

        llm = LLMIntegration(model_type='auto')

        # List available models
        available = llm.list_available_models()

        print(f"Local models: {len(available['local'])} found")
        if available['local']:
            for model in available['local']:
                print(f"  - {model}")

        print(f"API models: {len(available['api'])} configured")
        if available['api']:
            for api in available['api']:
                print(f"  - {api}")

        if llm.client or llm.local_model:
            print(f"✓ LLM initialized: {llm.model_type}")
        else:
            print("ℹ No LLM available (this is optional)")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_prayer_wheel():
    """Test prayer wheel"""
    print("\n" + "="*60)
    print("Testing Prayer Wheel")
    print("="*60)

    try:
        from core.prayer_wheel import PrayerWheel

        wheel = PrayerWheel()

        # Generate traditional prayers
        intentions = ['healing', 'wisdom', 'compassion', 'peace']

        for intention in intentions:
            prayer = wheel.generate_prayer(intention, use_llm=False)
            print(f"✓ {intention}: {prayer[:50]}...")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_audio_generator():
    """Test audio generator (without playback)"""
    print("\n" + "="*60)
    print("Testing Audio Generator")
    print("="*60)

    try:
        from core.audio_generator import ScalarWaveGenerator
        import numpy as np

        gen = ScalarWaveGenerator()

        # Generate waves (without playing)
        wave1 = gen.generate_schumann_resonance(duration=1)
        print(f"✓ Generated Schumann resonance: {len(wave1)} samples")

        wave2 = gen.generate_solfeggio_tone(528, duration=1)
        print(f"✓ Generated 528 Hz tone: {len(wave2)} samples")

        wave3 = gen.layer_frequencies([(7.83, 0.5), (136.1, 0.5)], duration=1)
        print(f"✓ Generated layered frequencies: {len(wave3)} samples")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_tts():
    """Test TTS (without speaking)"""
    print("\n" + "="*60)
    print("Testing TTS Engine")
    print("="*60)

    try:
        from core.tts_engine import TTSEngine

        tts = TTSEngine()

        # List voices
        voices = tts.list_available_voices()
        print(f"✓ Found {len(voices)} voices")

        if voices:
            print(f"  Default: {voices[0]['name']}")

        return True
    except Exception as e:
        print(f"ℹ TTS not available (may not work in headless environment)")
        return True  # Don't fail on TTS


def main():
    print("\n" + "="*60)
    print("VAJRA.STREAM - SYSTEM TEST")
    print("="*60)

    results = {}

    # Run all tests
    results['Astrology'] = test_astrology()
    results['Rothko Visuals'] = test_rothko()
    results['Audio Generator'] = test_audio_generator()
    results['LLM Integration'] = test_llm()
    results['Prayer Wheel'] = test_prayer_wheel()
    results['TTS Engine'] = test_tts()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n🙏 All core systems operational")
        print("\nNext steps:")
        print("  - Add GGUF models to ./models/ for local LLM")
        print("  - Set ANTHROPIC_API_KEY or OPENAI_API_KEY for cloud LLM")
        print("  - Run: python scripts/vajra_orchestrator.py test")
        print("\nMay all beings benefit! 🙏\n")
        return 0
    else:
        print("\n⚠ Some tests failed. See errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
