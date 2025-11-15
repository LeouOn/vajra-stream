#!/usr/bin/env python3
"""
Vajra.Stream Prayer Bowl Audio Test Script
Compare original sine waves vs enhanced prayer bowl synthesis
"""

import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_generator import ScalarWaveGenerator
from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3AmplifiedBroadcaster
import sounddevice as sd


def test_single_frequency_comparison():
    """Test single frequency with both modes"""
    print("\n" + "="*60)
    print("SINGLE FREQUENCY COMPARISON TEST")
    print("="*60)
    
    gen = ScalarWaveGenerator()
    test_freq = 528  # Love frequency
    duration = 8
    
    print(f"\nTesting {test_freq} Hz (Love frequency) for {duration} seconds each")
    print("\n1. Playing PRAYER BOWL synthesis (rich harmonics)...")
    print("   Listen for complex overtones and slow attack/decay")
    
    prayer_bowl_wave = gen.generate_prayer_bowl_tone(test_freq, duration, pure_sine=False)
    sd.play(prayer_bowl_wave, samplerate=gen.sample_rate)
    sd.wait()
    
    time.sleep(2)
    
    print("\n2. Playing PURE SINE wave (original)...")
    print("   Notice the simpler, cleaner tone")
    
    sine_wave = gen.generate_prayer_bowl_tone(test_freq, duration, pure_sine=True)
    sd.play(sine_wave, samplerate=gen.sample_rate)
    sd.wait()
    
    print("\nComparison complete! Notice the richer harmonic content in prayer bowl mode.")


def test_layered_frequencies():
    """Test multiple frequencies layered together"""
    print("\n" + "="*60)
    print("LAYERED FREQUENCIES TEST")
    print("="*60)
    
    gen = ScalarWaveGenerator()
    frequencies = [(528, 0.4), (639, 0.3), (7.83, 0.3)]  # Love, connection, earth
    duration = 10
    
    print(f"\nTesting layered frequencies: {frequencies}")
    print("\n1. Playing PRAYER BOWL synthesis...")
    print("   Listen for how multiple bowls interact harmonically")
    
    prayer_bowl_wave = gen.layer_frequencies(frequencies, duration, pure_sine=False)
    sd.play(prayer_bowl_wave, samplerate=gen.sample_rate)
    sd.wait()
    
    time.sleep(2)
    
    print("\n2. Playing PURE SINE waves...")
    print("   Notice the simpler interaction between tones")
    
    sine_wave = gen.layer_frequencies(frequencies, duration, pure_sine=True)
    sd.play(sine_wave, samplerate=gen.sample_rate)
    sd.wait()
    
    print("\nLayered comparison complete!")


def test_crystal_broadcaster_modes():
    """Test crystal broadcaster with both modes"""
    print("\n" + "="*60)
    print("CRYSTAL BROADCASTER MODE COMPARISON")
    print("="*60)
    
    intention = "Testing prayer bowl synthesis"
    duration = 12
    
    print(f"\nIntention: {intention}")
    print(f"Duration: {duration} seconds per mode")
    
    # Test Level 2 (passive)
    print("\n1. Level 2 - PRAYER BOWL synthesis...")
    broadcaster = Level2CrystalBroadcaster(pure_sine=False)
    
    # Create a shortened version for testing
    frequencies = {
        'schumann': 7.83,
        'om': 136.1,
        'love': 528,
    }
    
    t = np.linspace(0, duration, int(broadcaster.sample_rate * duration))
    wave = np.zeros_like(t)
    
    for freq in frequencies.values():
        bowl_tone = broadcaster.audio_gen.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
        wave += bowl_tone
    
    wave = wave / len(frequencies)
    stereo_wave = np.column_stack([wave, wave])
    
    print("   Broadcasting prayer bowl synthesis through crystal grid...")
    sd.play(stereo_wave, samplerate=broadcaster.sample_rate)
    sd.wait()
    
    time.sleep(2)
    
    print("\n2. Level 2 - PURE SINE waves...")
    broadcaster = Level2CrystalBroadcaster(pure_sine=True)
    
    wave = np.zeros_like(t)
    for freq in frequencies.values():
        wave += np.sin(2 * np.pi * freq * t)
    
    wave = wave / len(frequencies)
    
    # Add original breathing effect
    breath_freq = 0.1
    modulation = 0.85 + 0.15 * np.sin(2 * np.pi * breath_freq * t)
    wave = wave * modulation
    
    stereo_wave = np.column_stack([wave, wave])
    
    print("   Broadcasting pure sine waves through crystal grid...")
    sd.play(stereo_wave, samplerate=broadcaster.sample_rate)
    sd.wait()
    
    print("\nCrystal broadcaster comparison complete!")


def test_bass_shaker_optimization():
    """Test bass shaker optimization"""
    print("\n" + "="*60)
    print("BASS SHAKER OPTIMIZATION TEST")
    print("="*60)
    
    print("\n1. PRAYER BOWL synthesis optimized for bass shaker...")
    broadcaster = Level3AmplifiedBroadcaster(pure_sine=False)
    
    duration = 10
    frequencies = {
        'schumann': 7.83,
        'theta': 6.0,
        'om': 136.1,
    }
    
    t = np.linspace(0, duration, int(broadcaster.sample_rate * duration))
    wave = np.zeros_like(t)
    
    for name, freq in frequencies.items():
        bowl_tone = broadcaster.audio_gen.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
        weight = 2.0 if freq < 100 else 1.0
        wave += weight * bowl_tone
    
    wave = wave / np.max(np.abs(wave)) * 0.7
    
    # Gentle pulse
    pulse_freq = 0.8
    pulse = 0.95 + 0.05 * np.sin(2 * np.pi * pulse_freq * t)
    wave = wave * pulse
    
    stereo_wave = np.column_stack([wave, wave])
    
    print("   Notice the richer low-frequency content for tactile response")
    sd.play(stereo_wave, samplerate=broadcaster.sample_rate)
    sd.wait()
    
    time.sleep(2)
    
    print("\n2. PURE SINE waves for bass shaker...")
    broadcaster = Level3AmplifiedBroadcaster(pure_sine=True)
    
    wave = np.zeros_like(t)
    for name, freq in frequencies.items():
        weight = 2.0 if freq < 100 else 1.0
        wave += weight * np.sin(2 * np.pi * freq * t)
    
    wave = wave / np.max(np.abs(wave)) * 0.7
    
    # Original pulse
    pulse_freq = 1.2
    pulse = 0.9 + 0.1 * np.sin(2 * np.pi * pulse_freq * t)
    wave = wave * pulse
    
    stereo_wave = np.column_stack([wave, wave])
    
    print("   Notice the simpler low-frequency response")
    sd.play(stereo_wave, samplerate=broadcaster.sample_rate)
    sd.wait()
    
    print("\nBass shaker comparison complete!")


def interactive_frequency_test():
    """Interactive test for user-selected frequencies"""
    print("\n" + "="*60)
    print("INTERACTIVE FREQUENCY TEST")
    print("="*60)
    
    gen = ScalarWaveGenerator()
    
    while True:
        print("\nEnter a frequency to test (or 'quit' to exit):")
        print("Common frequencies: 528, 639, 741, 136.1, 7.83")
        
        user_input = input("Frequency Hz: ").strip().lower()
        
        if user_input in ['quit', 'exit', 'q']:
            break
        
        try:
            freq = float(user_input)
            duration = 6
            
            print(f"\nTesting {freq} Hz...")
            
            print("\n1. Prayer Bowl Synthesis:")
            prayer_wave = gen.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
            sd.play(prayer_wave, samplerate=gen.sample_rate)
            sd.wait()
            
            time.sleep(1)
            
            print("2. Pure Sine Wave:")
            sine_wave = gen.generate_prayer_bowl_tone(freq, duration, pure_sine=True)
            sd.play(sine_wave, samplerate=gen.sample_rate)
            sd.wait()
            
        except ValueError:
            print("Invalid frequency. Please enter a number.")
    
    print("\nInteractive test complete!")


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("VAJRA.STREAM PRAYER BOWL AUDIO TEST SUITE")
    print("="*60)
    print("\nThis test suite compares the original sine wave audio")
    print("with the new prayer bowl synthesis enhancements.")
    print("\nPlease ensure your speakers/headphones are connected.")
    print("Volume should be at a comfortable level.")
    
    while True:
        print("\n" + "="*40)
        print("TEST MENU")
        print("="*40)
        print("1. Single Frequency Comparison")
        print("2. Layered Frequencies Test")
        print("3. Crystal Broadcaster Modes")
        print("4. Bass Shaker Optimization")
        print("5. Interactive Frequency Test")
        print("6. Run All Tests")
        print("0. Exit")
        
        choice = input("\nSelect test (0-6): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            test_single_frequency_comparison()
        elif choice == '2':
            test_layered_frequencies()
        elif choice == '3':
            test_crystal_broadcaster_modes()
        elif choice == '4':
            test_bass_shaker_optimization()
        elif choice == '5':
            interactive_frequency_test()
        elif choice == '6':
            test_single_frequency_comparison()
            time.sleep(2)
            test_layered_frequencies()
            time.sleep(2)
            test_crystal_broadcaster_modes()
            time.sleep(2)
            test_bass_shaker_optimization()
        else:
            print("Invalid choice. Please select 0-6.")
    
    print("\n" + "="*60)
    print("PRAYER BOWL AUDIO TEST COMPLETE")
    print("="*60)
    print("\nKey differences to notice:")
    print("• Prayer Bowl mode: Rich harmonics, complex overtones")
    print("• Prayer Bowl mode: Slow attack/decay like struck bowl")
    print("• Prayer Bowl mode: Subtle modulation and beating effects")
    print("• Pure Sine mode: Clean, simple tones")
    print("• Pure Sine mode: Immediate attack, consistent sustain")
    print("\nPrayer bowl synthesis is now the DEFAULT mode.")
    print("Set pure_sine=True in code to use original sine waves.")
    print("\nMay all beings benefit from these enhanced frequencies! 🙏")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        print("May all beings benefit. 🙏")
    except Exception as e:
        print(f"\nError during testing: {e}")
        print("Please check your audio setup and try again.")