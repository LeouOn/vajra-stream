#!/usr/bin/env python3
"""
Audio Comparison Test Script
Compare original sine waves vs enhanced prayer bowl synthesis
"""

import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.crystal_broadcaster import Level2CrystalBroadcaster
from core.audio_generator import ScalarWaveGenerator
from core.enhanced_audio_generator import EnhancedAudioGenerator
import sounddevice as sd
import numpy as np


def test_single_frequency_comparison():
    """Test single frequency with both implementations"""
    print("\n" + "="*60)
    print("SINGLE FREQUENCY COMPARISON TEST")
    print("="*60)
    
    test_freq = 528  # Love frequency
    duration = 8  # 8 seconds each
    
    print(f"\nTesting {test_freq} Hz ({duration} seconds each)")
    print("\n1. Original sine wave implementation:")
    print("   Simple, clean tone")
    
    # Test original implementation
    original_gen = ScalarWaveGenerator()
    original_wave = original_gen.generate_prayer_bowl_tone(test_freq, duration, pure_sine=True)
    
    print("\n2. Enhanced prayer bowl synthesis:")
    print("   Rich harmonics with natural modulation")
    
    # Test enhanced implementation
    enhanced_gen = EnhancedAudioGenerator()
    enhanced_wave = enhanced_gen.generate_prayer_bowl_tone(test_freq, duration, pure_sine=False)
    
    # Play both for comparison
    try:
        print("\nPlaying original sine wave...")
        sd.play(original_wave, 44100)
        sd.wait()
        
        time.sleep(1)
        
        print("Playing enhanced prayer bowl synthesis...")
        sd.play(enhanced_wave, 44100)
        sd.wait()
        
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")


def test_layered_frequencies():
    """Test multiple frequencies layered together"""
    print("\n" + "="*60)
    print("LAYERED FREQUENCIES COMPARISON TEST")
    print("="*60)
    
    frequencies = [
        (7.83, 0.3),      # Earth resonance
        (136.1, 0.3),     # Year of Earth frequency
        (528, 0.4),        # DNA healing/love
    ]
    
    duration = 10  # 10 seconds each
    
    print(f"\nTesting layered frequencies: {frequencies}")
    print(f"Duration: {duration} seconds each")
    
    # Test original implementation
    print("\n1. Original sine wave implementation:")
    original_gen = ScalarWaveGenerator()
    original_wave = original_gen.layer_frequencies(frequencies, duration, pure_sine=True)
    
    # Test enhanced implementation
    print("\n2. Enhanced prayer bowl synthesis:")
    enhanced_gen = EnhancedAudioGenerator()
    enhanced_wave = enhanced_gen.layer_frequencies(frequencies, duration, pure_sine=False)
    
    # Play both for comparison
    try:
        print("\nPlaying original layered sine waves...")
        sd.play(original_wave, 44100)
        sd.wait()
        
        time.sleep(1)
        
        print("Playing enhanced layered prayer bowl synthesis...")
        sd.play(enhanced_wave, 44100)
        sd.wait()
        
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")


def test_chakra_healing():
    """Test chakra healing with both implementations"""
    print("\n" + "="*60)
    print("CHAKRA HEALING COMPARISON TEST")
    print("="*60)
    
    chakra = 'heart'
    duration = 10  # 10 seconds each
    
    print(f"\nTesting {chakra} chakra healing")
    print(f"Duration: {duration} seconds each")
    
    # Test original implementation
    print("\n1. Original sine wave implementation:")
    original_broadcaster = Level2CrystalBroadcaster(pure_sine=True)
    
    # Test enhanced implementation
    print("\n2. Enhanced prayer bowl synthesis:")
    enhanced_broadcaster = Level2CrystalBroadcaster(pure_sine=False)
    
    # Play both for comparison
    try:
        print("\nPlaying original chakra healing (sine waves)...")
        original_broadcaster.generate_chakra_healing(chakra, duration)
        
        time.sleep(1)
        
        print("Playing enhanced chakra healing (prayer bowl synthesis)...")
        enhanced_broadcaster.generate_chakra_healing(chakra, duration)
        
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("VAJRA.STREAM AUDIO COMPARISON TEST SUITE")
    print("="*60)
    print("\nThis test compares the original sine wave implementation")
    print("with the enhanced prayer bowl synthesis.")
    print("\nListen for differences in:")
    print("• Harmonic richness")
    print("• Natural volume modulation (LFO)")
    print("• Subtle vibrato effects")
    print("• ADSR envelope shaping")
    
    while True:
        print("\n" + "="*40)
        print("TEST MENU")
        print("="*40)
        print("1. Single Frequency Comparison")
        print("2. Layered Frequencies Test")
        print("3. Chakra Healing Comparison")
        print("0. Exit")
        
        choice = input("\nSelect test (0-3): ").strip()
        
        if choice == '0':
            print("\nExiting test suite...")
            break
        elif choice == '1':
            test_single_frequency_comparison()
        elif choice == '2':
            test_layered_frequencies()
        elif choice == '3':
            test_chakra_healing()
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