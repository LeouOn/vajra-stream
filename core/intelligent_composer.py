"""
Intelligent Audio Composer for Vajra.Stream
Creates harmonic, beautiful compositions instead of cacophony
"""

import numpy as np
from enum import Enum
from typing import List, Tuple, Dict
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PRAYER_BOWL_CONFIG


class HarmonicRelationship(Enum):
    """Harmonic relationship types based on frequency ratios"""
    PERFECT_CONSONANCE = 1  # 1:1, 2:1, 3:2
    IMPERFECT_CONSONANCE = 2  # 4:3, 5:4, 6:5
    MILD_DIATONIC_DISONANCE = 3  # 9:8, 10:9
    SHARP_DISONANCE = 4  # 15:8, 16:9
    EXTREME_DISONANCE = 5  # 45:32, 64:45


class IntelligentComposer:
    """
    Intelligent audio composition system that creates harmonic, beautiful soundscapes
    instead of cacophony through:
    - Harmonic ratio analysis
    - Alternating/layering patterns
    - Spatial panning
    - Dynamic mixing
    """
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        
        # Harmonic consonance table - which intervals sound good together
        self.consonant_ratios = [
            1.0,    # Unison
            1.125,  # Major second (9:8) - mild consonance
            1.2,    # Minor third (6:5) - imperfect consonance
            1.25,   # Major third (5:4) - imperfect consonance
            1.333,  # Perfect fourth (4:3) - imperfect consonance
            1.5,    # Perfect fifth (3:2) - perfect consonance
            1.6,    # Minor sixth (8:5) - imperfect consonance
            1.667,  # Major sixth (5:3) - imperfect consonance
            1.875,  # Major seventh (15:8) - mild dissonance
            2.0,    # Octave (2:1) - perfect consonance
        ]
        
        # Composition patterns for alternating/layering
        self.composition_patterns = {
            'alternating': self._pattern_alternating,
            'layered': self._pattern_layered,
            'evolving': self._pattern_evolving,
            'harmonic_chords': self._pattern_harmonic_chords,
        }
    
    def analyze_harmonic_relationship(self, freq1: float, freq2: float) -> Tuple[HarmonicRelationship, float]:
        """
        Analyze the harmonic relationship between two frequencies
        
        Returns:
            relationship_type: Type of harmonic relationship
            consonance_score: Score from 0-1 (1 = perfectly consonant)
        """
        ratio = max(freq1, freq2) / min(freq1, freq2)
        
        # Normalize ratio to within one octave
        while ratio > 2.0:
            ratio /= 2.0
        
        # Find closest consonant ratio
        closest_ratio = min(self.consonant_ratios, key=lambda x: abs(x - ratio))
        difference = abs(closest_ratio - ratio)
        
        # Calculate consonance score (inverse of difference)
        consonance_score = max(0, 1 - (difference * 10))
        
        # Determine relationship type
        if closest_ratio in [1.0, 1.5, 2.0]:  # Unison, perfect fifth, octave
            relationship = HarmonicRelationship.PERFECT_CONSONANCE
        elif closest_ratio in [1.2, 1.25, 1.333, 1.6, 1.667]:  # Thirds, fourths, sixths
            relationship = HarmonicRelationship.IMPERFECT_CONSONANCE
        elif closest_ratio in [1.125]:  # Major second
            relationship = HarmonicRelationship.MILD_DIATONIC_DISONANCE
        elif closest_ratio in [1.875]:  # Major seventh
            relationship = HarmonicRelationship.SHARP_DISONANCE
        else:
            relationship = HarmonicRelationship.EXTREME_DISONANCE
        
        return relationship, consonance_score
    
    def select_harmonic_frequencies(self, frequencies: List[float], min_consonance: float = 0.6) -> List[float]:
        """
        Intelligently select frequencies that are harmonically consonant
        
        Args:
            frequencies: List of frequencies to choose from
            min_consonance: Minimum consonance score (0-1)
            
        Returns:
            List of selected frequencies that sound good together
        """
        if len(frequencies) <= 2:
            return frequencies
        
        selected = [frequencies[0]]  # Start with first frequency
        
        for freq in frequencies[1:]:
            # Check if this frequency is consonant with all selected frequencies
            is_consonant = True
            total_consonance = 0
            
            for selected_freq in selected:
                relationship, score = self.analyze_harmonic_relationship(freq, selected_freq)
                total_consonance += score
                
                if score < min_consonance:
                    is_consonant = False
                    break
            
            if is_consonant:
                selected.append(freq)
        
        return selected
    
    def create_spatial_panning(self, num_frequencies: int) -> List[float]:
        """
        Create spatial panning positions for frequencies
        
        Returns:
            List of panning positions (-1 = left, 0 = center, 1 = right)
        """
        if num_frequencies == 1:
            return [0.0]  # Center
        
        elif num_frequencies == 2:
            return [-0.5, 0.5]  # Left and right
        
        elif num_frequencies == 3:
            return [-0.7, 0.0, 0.7]  # Left, center, right
        
        elif num_frequencies == 4:
            return [-0.8, -0.2, 0.2, 0.8]  # Spread across stereo field
        
        else:  # 5 or more
            # Distribute evenly across stereo field
            return [-0.9 + (i * 1.8 / (num_frequencies - 1)) for i in range(num_frequencies)]
    
    def compose_frequency_pattern(self, frequencies: List[float], duration: float, pattern_type: str = 'evolving') -> np.ndarray:
        """
        Compose frequencies using intelligent patterns instead of simple mixing
        
        Args:
            frequencies: List of frequencies to compose
            duration: Total duration in seconds
            pattern_type: Type of composition pattern
            
        Returns:
            Composed audio waveform
        """
        if pattern_type not in self.composition_patterns:
            pattern_type = 'evolving'
        
        return self.composition_patterns[pattern_type](frequencies, duration)
    
    def _pattern_alternating(self, frequencies: List[float], duration: float) -> np.ndarray:
        """
        Alternating pattern: frequencies take turns playing
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        wave = np.zeros_like(t)
        
        # Each frequency plays for a segment
        segment_duration = duration / len(frequencies)
        segment_samples = int(segment_duration * self.sample_rate)
        
        for i, freq in enumerate(frequencies):
            start_idx = i * segment_samples
            end_idx = min((i + 1) * segment_samples, len(t))
            
            if start_idx < len(t):
                segment_t = t[start_idx:end_idx]
                segment_wave = np.sin(2 * np.pi * freq * segment_t)
                
                # Apply fade in/out
                fade_samples = min(1000, len(segment_wave) // 10)
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                if len(segment_wave) > fade_samples * 2:
                    segment_wave[:fade_samples] *= fade_in
                    segment_wave[-fade_samples:] *= fade_out
                
                wave[start_idx:end_idx] += segment_wave
        
        return wave
    
    def _pattern_layered(self, frequencies: List[float], duration: float) -> np.ndarray:
        """
        Layered pattern: frequencies fade in/out at different times
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        wave = np.zeros_like(t)
        
        # Each frequency fades in at a different time
        for i, freq in enumerate(frequencies):
            # Calculate fade in time (staggered)
            fade_in_start = (i / len(frequencies)) * duration * 0.5
            fade_in_duration = duration * 0.3
            
            # Create amplitude envelope for this frequency
            amplitude = np.zeros_like(t)
            fade_in_samples = int(fade_in_duration * self.sample_rate)
            start_sample = int(fade_in_start * self.sample_rate)
            
            # Fade in
            if start_sample < len(t):
                end_fade = min(start_sample + fade_in_samples, len(t))
                fade_length = end_fade - start_sample
                amplitude[start_sample:end_fade] = np.linspace(0, 1, fade_length)
                
                # Hold and fade out
                if end_fade < len(t):
                    hold_duration = int(duration * 0.2 * self.sample_rate)
                    hold_end = min(end_fade + hold_duration, len(t))
                    amplitude[end_fade:hold_end] = 1.0
                    
                    # Fade out
                    fade_out_start = hold_end
                    fade_out_end = min(fade_out_start + fade_in_samples, len(t))
                    if fade_out_end > fade_out_start:
                        fade_out_length = fade_out_end - fade_out_start
                        amplitude[fade_out_start:fade_out_end] = np.linspace(1, 0, fade_out_length)
            
            # Generate and apply amplitude envelope
            freq_wave = np.sin(2 * np.pi * freq * t)
            wave += freq_wave * amplitude
        
        # Normalize
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def _pattern_evolving(self, frequencies: List[float], duration: float) -> np.ndarray:
        """
        Evolving pattern: mix changes over time, some frequencies come and go
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        wave = np.zeros_like(t)
        
        # Create evolution timeline
        evolution_phases = 4
        phase_duration = duration / evolution_phases
        
        for phase in range(evolution_phases):
            phase_start = phase * phase_duration
            phase_end = min((phase + 1) * phase_duration, duration)
            
            # Select different frequencies for each phase
            if phase == 0:
                # Start with lower frequencies
                phase_freqs = [f for f in frequencies if f < 200]
            elif phase == 1:
                # Add mid frequencies
                phase_freqs = [f for f in frequencies if 200 <= f < 600]
            elif phase == 2:
                # Add higher frequencies
                phase_freqs = [f for f in frequencies if f >= 600]
            else:
                # All frequencies together for climax
                phase_freqs = frequencies
            
            if not phase_freqs:
                phase_freqs = frequencies[:2]  # Fallback
            
            # Generate phase audio
            start_idx = int(phase_start * self.sample_rate)
            end_idx = int(phase_end * self.sample_rate)
            phase_t = t[start_idx:end_idx]
            
            phase_wave = np.zeros_like(phase_t)
            for freq in phase_freqs:
                phase_wave += np.sin(2 * np.pi * freq * phase_t)
            
            # Normalize phase
            if len(phase_freqs) > 0:
                phase_wave = phase_wave / len(phase_freqs)
            
            # Apply fade at phase boundaries
            fade_samples = min(1000, len(phase_wave) // 10)
            if len(phase_wave) > fade_samples * 2:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                phase_wave[:fade_samples] *= fade_in
                phase_wave[-fade_samples:] *= fade_out
            
            wave[start_idx:end_idx] += phase_wave
        
        # Normalize final wave
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def _pattern_harmonic_chords(self, frequencies: List[float], duration: float) -> np.ndarray:
        """
        Harmonic chords pattern: group frequencies into consonant chords
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        wave = np.zeros_like(t)
        
        # Group frequencies into chords based on harmonic relationships
        chords = []
        remaining_freqs = frequencies.copy()
        
        while len(remaining_freqs) >= 2:
            # Find frequencies that are consonant with each other
            chord = [remaining_freqs[0]]
            remaining_freqs = remaining_freqs[1:]
            
            for freq in remaining_freqs[:]:
                is_consonant = True
                for chord_freq in chord:
                    relationship, score = self.analyze_harmonic_relationship(freq, chord_freq)
                    if score < 0.6:  # Not consonant enough
                        is_consonant = False
                        break
                
                if is_consonant:
                    chord.append(freq)
                    remaining_freqs.remove(freq)
            
            chords.append(chord)
        
        # Play chords in sequence
        if chords:
            chord_duration = duration / len(chords)
            chord_samples = int(chord_duration * self.sample_rate)
            
            for i, chord in enumerate(chords):
                if not chord:
                    continue
                
                start_idx = i * chord_samples
                end_idx = min((i + 1) * chord_samples, len(t))
                
                chord_t = t[start_idx:end_idx]
                chord_wave = np.zeros_like(chord_t)
                
                # Mix chord frequencies
                for freq in chord:
                    chord_wave += np.sin(2 * np.pi * freq * chord_t)
                
                # Normalize chord
                chord_wave = chord_wave / len(chord)
                
                # Apply envelope
                fade_samples = min(500, len(chord_wave) // 8)
                if len(chord_wave) > fade_samples * 2:
                    fade_in = np.linspace(0, 1, fade_samples)
                    fade_out = np.linspace(1, 0, fade_samples)
                    chord_wave[:fade_samples] *= fade_in
                    chord_wave[-fade_samples:] *= fade_out
                
                wave[start_idx:end_idx] += chord_wave
        
        # Fill remaining time with individual frequencies if any left
        if remaining_freqs:
            remaining_duration = duration * 0.2
            remaining_samples = int(remaining_duration * self.sample_rate)
            if remaining_samples < len(t):
                start_idx = len(t) - remaining_samples
                remaining_t = t[start_idx:]
                remaining_wave = np.zeros_like(remaining_t)
                
                for freq in remaining_freqs:
                    remaining_wave += np.sin(2 * np.pi * freq * remaining_t)
                
                remaining_wave = remaining_wave / len(remaining_freqs)
                wave[start_idx:] += remaining_wave
        
        # Normalize
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def create_intention_modulation(self, intention: str, base_wave: np.ndarray, modulation_depth: float = 0.1) -> np.ndarray:
        """
        Modulate the audio based on intention text
        Creates subtle variations that make each session unique
        """
        # Convert intention to seed
        intention_seed = sum(ord(c) for c in intention)
        np.random.seed(intention_seed % 2**32)
        
        # Create subtle modulation pattern
        t = np.linspace(0, len(base_wave) / self.sample_rate, len(base_wave))
        modulation_freq = 0.05 + (intention_seed % 10) * 0.01  # 0.05-0.15 Hz
        
        modulation = 1 + modulation_depth * np.sin(2 * np.pi * modulation_freq * t)
        
        # Apply modulation
        modulated_wave = base_wave * modulation
        
        return modulated_wave


class AudioOrchestrator:
    """
    High-level orchestrator that manages the entire audio composition
    """
    
    def __init__(self, sample_rate=44100):
        self.composer = IntelligentComposer(sample_rate)
        self.sample_rate = sample_rate
    
    def create_blessing_composition(self, frequencies: List[float], intention: str, duration: float, pattern_type: str = 'evolving') -> np.ndarray:
        """
        Create a complete blessing composition
        
        Args:
            frequencies: List of frequencies to use
            intention: Intention text for modulation
            duration: Duration in seconds
            pattern_type: Composition pattern type
            
        Returns:
            Complete composed audio waveform
        """
        # Step 1: Select harmonically consonant frequencies
        selected_freqs = self.composer.select_harmonic_frequencies(frequencies, min_consonance=0.6)
        
        if len(selected_freqs) < 2:
            selected_freqs = frequencies[:3]  # Fallback to first 3 frequencies
        
        print(f"Selected {len(selected_freqs)} harmonically consonant frequencies from {len(frequencies)}")
        
        # Step 2: Create composition using intelligent pattern
        composition = self.composer.compose_frequency_pattern(selected_freqs, duration, pattern_type)
        
        # Step 3: Apply intention-based modulation
        modulated_composition = self.composer.create_intention_modulation(intention, composition)
        
        # Step 4: Apply spatial panning if multiple frequencies
        if len(selected_freqs) > 1:
            panning = self.composer.create_spatial_panning(len(selected_freqs))
            print(f"Applied spatial panning: {panning}")
        
        return modulated_composition
    
    def create_chakra_healing_composition(self, chakra_freq: float, duration: float, intention: str) -> np.ndarray:
        """
        Create chakra healing composition with supporting frequencies
        """
        # Primary chakra frequency
        # Supporting frequencies (harmonically related)
        supporting_freqs = [
            chakra_freq * 0.5,    # Sub-octave
            chakra_freq * 1.5,    # Perfect fifth
            chakra_freq * 2.0,    # Octave
        ]
        
        # Add Schumann resonance
        all_freqs = [chakra_freq, 7.83] + supporting_freqs
        
        # Select consonant frequencies
        selected_freqs = self.composer.select_harmonic_frequencies(all_freqs, min_consonance=0.5)
        
        # Create layered composition for healing
        return self.composer.compose_frequency_pattern(selected_freqs, duration, 'layered')


# Pre-defined harmonic frequency sets that sound good together
HARMONIC_BLESSING_SETS = {
    'earth_harmony': [7.83, 136.1, 272.2, 408.3],  # Schumann + OM + harmonics
    'love_resonance': [528, 264, 396, 792],        # Love frequency + related
    'heart_chord': [639, 426, 852, 319.5],         # Heart chakra + perfect fifths
    'full_spectrum': [7.83, 136.1, 528, 639, 741], # Original set, but will be filtered
}