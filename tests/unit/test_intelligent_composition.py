#!/usr/bin/env python3
"""
Test Intelligent Audio Composition
Demonstrates harmonic frequency selection and intelligent composition patterns
"""

import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.intelligent_composer import AudioOrchestrator, HARMONIC_BLESSING_SETS
import sounddevice as sd
import numpy as np


def test_harmonic_analysis():
    """Test harmonic relationship analysis"""
    print("\n" + "="*60)
    print("HARMONIC RELATIONSHIP ANALYSIS")
    print("="*60)
    
    orchestrator = AudioOrchestrator()
    
    # Test various frequency pairs
    test_pairs = [
        (528, 528),      # Unison
        (528, 264),      # Octave
        (528, 352),      # Perfect fifth (528 * 2/3)
        (528, 396),      # Perfect fourth (528 * 3/4)
        (528, 440),      # A4 - slightly dissonant
        (528, 600),      # Dissonant
    ]
    
    print("\nAnalyzing harmonic relationships:")
    for freq1, freq2 in test_pairs:
        relationship, score = orchestrator.composer.analyze_harmonic_relationship(freq1, freq2)
        print(f"  {freq1} Hz & {freq2} Hz: {relationship.name}, Consonance: {score:.2f}")


def test_frequency_selection():
    """Test intelligent frequency selection"""
    print("\n" + "="*60)
    print("INTELLIGENT FREQUENCY SELECTION")
    print("="*60)
    
    orchestrator = AudioOrchestrator()
    
    # Test with a set of frequencies
    test_frequencies = [7.83, 136.1, 528, 639, 741, 440, 600, 800, 1000]
    
    print(f"\nOriginal frequencies: {test_frequencies}")
    
    selected = orchestrator.composer.select_harmonic_frequencies(test_frequencies, min_consonance=0.6)
    
    print(f"Selected frequencies: {selected}")
    print(f"Selected {len(selected)} out of {len(test_frequencies)} frequencies")


def test_composition_patterns():
    """Test different composition patterns"""
    print("\n" + "="*60)
    print("COMPOSITION PATTERNS COMPARISON")
    print("="*60)
    
    orchestrator = AudioOrchestrator()
    
    # Use a consonant frequency set
    frequencies = [528, 264, 396, 792]  # Love frequency and harmonics
    
    duration = 10  # 10 seconds each
    
    patterns = ['alternating', 'layered', 'evolving', 'harmonic_chords']
    
    for pattern in patterns:
        print(f"\nTesting '{pattern}' pattern:")
        print(f"Frequencies: {frequencies}")
        
        composition = orchestrator.composer.compose_frequency_pattern(frequencies, duration, pattern)
        
        print(f"  Duration: {duration} seconds")
        print(f"  Max amplitude: {np.max(np.abs(composition)):.3f}")
        
        try:
            print(f"\n  Playing '{pattern}' pattern...")
            sd.play(composition, 44100)
            sd.wait()
            time.sleep(1)
        except KeyboardInterrupt:
            sd.stop()
            print("\nTest interrupted by user.")
            return


def test_spatial_panning():
    """Test spatial panning"""
    print("\n" + "="*60)
    print("SPATIAL PANNING TEST")
    print("="*60)
    
    orchestrator = AudioOrchestrator()
    
    for num_freqs in [1, 2, 3, 4, 5]:
        panning = orchestrator.composer.create_spatial_panning(num_freqs)
        print(f"  {num_freqs} frequencies: {panning}")


def test_complete_blessing():
    """Test complete blessing composition"""
    print("\n" + "="*60)
    print("COMPLETE BLESSING COMPOSITION")
    print("="*60)
    
    orchestrator = AudioOrchestrator()
    
    # Use predefined harmonic set
    frequencies = HARMONIC_BLESSING_SETS['earth_harmony']
    intention = "May all beings be happy and free from suffering"
    duration = 15
    
    print(f"\nIntention: {intention}")
    print(f"Frequencies: {frequencies}")
    print(f"Duration: {duration} seconds")
    
    composition = orchestrator.create_blessing_composition(frequencies, intention, duration, pattern_type='evolving')
    
    print(f"\nComposition created. Playing...")
    
    try:
        sd.play(composition, 44100)
        sd.wait()
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")


def test_chakra_healing():
    """Test chakra healing composition"""
    print("\n" + "="*60)
    print("CHAKRA HEALING COMPOSITION")
    print("="*60)
    
    orchestrator = AudioOrchestrator()
    
    chakra_freq = 639  # Heart chakra
    intention = "Healing for heart chakra - love and compassion"
    duration = 12
    
    print(f"\nChakra: Heart ({chakra_freq} Hz)")
    print(f"Intention: {intention}")
    print(f"Duration: {duration} seconds")
    
    composition = orchestrator.create_chakra_healing_composition(chakra_freq, duration, intention)
    
    print(f"\nHealing composition created. Playing...")
    
    try:
        sd.play(composition, 44100)
        sd.wait()
    except KeyboardInterrupt:
        sd.stop()
        print("\nTest interrupted by user.")


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("INTELLIGENT AUDIO COMPOSITION TEST SUITE")
    print("="*60)
    print("\nThis test suite demonstrates intelligent audio composition")
    print("that creates harmonic, beautiful soundscapes instead of cacophony.")
    
    while True:
        print("\n" + "="*40)
        print("TEST MENU")
        print("="*40)
        print("1. Harmonic Relationship Analysis")
        print("2. Frequency Selection Test")
        print("3. Composition Patterns Comparison")
        print("4. Spatial Panning Test")
        print("5. Complete Blessing Composition")
        print("6. Chakra Healing Composition")
        print("0. Exit")
        
        choice = input("\nSelect test (0-6): ").strip()
        
        if choice == '0':
            print("\nExiting test suite...")
            break
        elif choice == '1':
            test_harmonic_analysis()
        elif choice == '2':
            test_frequency_selection()
        elif choice == '3':
            test_composition_patterns()
        elif choice == '4':
            test_spatial_panning()
        elif choice == '5':
            test_complete_blessing()
        elif choice == '6':
            test_chakra_healing()
        else:
            print("\nInvalid choice. Please select 0-6.")
        
        if choice != '0':
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user.")
        print("May all beings benefit from these harmonic frequencies! 🙏")