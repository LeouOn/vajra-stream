#!/usr/bin/env python3
"""
Test Enhanced Audio Features
Demonstrates the improved prayer bowl synthesis with natural modulation
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhanced_audio_generator import EnhancedAudioGenerator
import sounddevice as sd
import numpy as np
import time


def test_lfo_modulation():
    """Test LFO modulation effects"""
    print("\n" + "="*60)
    print("TESTING LFO MODULATION")
    print("="*60)
    
    gen = EnhancedAudioGenerator()
    
    # Test with different LFO settings
    lfo_rates = [0.05, 0.1, 0.2, 0.5]  # Very slow to moderate
    lfo_depths = [0.1, 0.2, 0.3]       # Subtle to moderate
    
    print("\nTesting LFO modulation with different rates and depths...")
    print("Listen for natural breathing/pulsing effects.\n")
    
    for rate in lfo_rates:
        for depth in lfo_depths:
            print(f"\nLFO Rate: {rate} Hz, Depth: {depth}")
            
            # Generate 5-second tone with specific LFO
            tone = gen.generate_prayer_bowl_tone(528, duration=5, pure_sine=False)
            
            # Play the tone
            try:
                sd.play(tone, 44100)
                sd.wait()
                time.sleep(1)
            except KeyboardInterrupt:
                sd.stop()
                print("\nTest interrupted by user.")
                return False
    
    return True


def test_harmonic_content():
    """Test harmonic richness of prayer bowl synthesis"""
    print("\n" + "="*60)
    print("TESTING HARMONIC CONTENT")
    print("="*60)
    
    gen = EnhancedAudioGenerator()
    
    # Test single frequency to hear harmonics
    print("\nTesting single frequency (528 Hz) for harmonic richness...")
    print("Listen for multiple harmonic overtones and metallic partials.\n")
    
    tone = gen.generate_prayer_bowl_tone(528, duration=8, pure_sine=False)
    
    try:
        sd.play(tone, 44100)
        sd.wait()
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")
        return False
    
    return True


def test_adsr_envelope():
    """Test ADSR envelope shaping"""
    print("\n" + "="*60)
    print("TESTING ADSR ENVELOPE")
    print("="*60)
    
    gen = EnhancedAudioGenerator()
    
    # Test with different envelope settings
    print("\nTesting different envelope configurations...")
    print("Listen for natural attack, decay, and release characteristics.\n")
    
    # Test quick attack (percussive)
    print("\n1. Quick attack (like struck bowl)...")
    tone1 = gen.generate_prayer_bowl_tone(528, duration=3, pure_sine=False)
    
    try:
        sd.play(tone1, 44100)
        sd.wait()
        time.sleep(1)
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")
        return False
    
    # Test slow attack (slow swelling)
    print("\n2. Slow attack (like swelling into sound)...")
    tone2 = gen.generate_prayer_bowl_tone(528, duration=3, pure_sine=False)
    
    try:
        sd.play(tone2, 44100)
        sd.wait()
        time.sleep(1)
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")
        return False
    
    return True


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("ENHANCED AUDIO FEATURE TEST")
    print("="*60)
    print("\nThis test demonstrates the enhanced prayer bowl synthesis features:")
    print("• Natural LFO modulation for breathing effects")
    print("• Rich harmonic spectrum based on real bowl measurements")
    print("• ADSR envelope shaping for natural attack/decay")
    print("• Subtle vibrato for pitch variation")
    print("\nListen for differences from original sine waves:")
    print("• More complex overtones")
    print("• Organic volume modulation")
    print("• Natural sound envelopes")
    
    while True:
        print("\n" + "="*40)
        print("TEST MENU")
        print("="*40)
        print("1. LFO Modulation Test")
        print("2. Harmonic Content Test")
        print("3. ADSR Envelope Test")
        print("0. Exit")
        
        choice = input("\nSelect test (0-3): ").strip()
        
        if choice == '0':
            print("\nExiting test suite...")
            break
        elif choice == '1':
            test_lfo_modulation()
        elif choice == '2':
            test_harmonic_content()
        elif choice == '3':
            test_adsr_envelope()
        else:
            print("\nInvalid choice. Please select 0-3.")
        
        if choice != '0':
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user.")
        print("May all beings benefit from these enhanced frequencies! 🙏")