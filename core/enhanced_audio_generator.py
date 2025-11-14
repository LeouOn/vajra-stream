"""
Enhanced Audio Generator for Vajra.Stream
Creates beautiful, natural prayer bowl sounds with LFO modulation
"""

import numpy as np
import sounddevice as sd
from scipy import signal
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PRAYER_BOWL_CONFIG


class EnhancedAudioGenerator:
    """
    Enhanced audio generator with natural LFO modulation and beautiful prayer bowl synthesis
    """
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        
    def generate_prayer_bowl_tone(self, frequency, duration=60, pure_sine=False):
        """
        Generate prayer bowl synthesis with rich harmonics and natural modulation
        
        Args:
            frequency: Base frequency in Hz
            duration: Duration in seconds
            pure_sine: If True, generate simple sine wave
            
        Returns:
            numpy array: Generated audio
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        if pure_sine:
            # Simple sine wave for backward compatibility
            return np.sin(2 * np.pi * frequency * t)
        
        # Prayer bowl synthesis with harmonics
        wave = np.zeros_like(t)
        
        # Add harmonic overtones based on real bowl measurements
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG['harmonic_ratios']):
            harmonic_freq = frequency * ratio
            # Decrease amplitude for higher harmonics
            amplitude = 1.0 / (i + 1)
            wave += amplitude * np.sin(2 * np.pi * harmonic_freq * t)
        
        # Add inharmonic metallic partials
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG['inharmonic_partials']):
            inharmonic_freq = frequency * ratio
            # Lower amplitude for metallic character
            amplitude = 0.3 / (i + 1)
            wave += amplitude * np.sin(2 * np.pi * inharmonic_freq * t)
        
        # Apply ADSR envelope for natural bowl sound
        attack_time = PRAYER_BOWL_CONFIG.get('attack', 1.5)
        decay_time = PRAYER_BOWL_CONFIG.get('decay', 0.8)
        sustain_level = PRAYER_BOWL_CONFIG.get('sustain', 0.6)
        release_time = PRAYER_BOWL_CONFIG.get('release', 2.0)
        
        # Create envelope
        attack_samples = int(attack_time * self.sample_rate)
        decay_samples = int(decay_time * self.sample_rate)
        release_samples = int(release_time * self.sample_rate)
        total_samples = len(t)
        
        envelope = np.ones_like(t)
        
        # Attack - exponential rise
        attack_indices = np.arange(min(attack_samples, total_samples))
        envelope[attack_indices] = 1 - np.exp(-3 * attack_indices / attack_samples)
        
        # Decay - exponential fall to sustain level
        decay_start = attack_samples
        decay_end = min(decay_start + decay_samples, total_samples)
        decay_indices = np.arange(decay_start, decay_end)
        envelope[decay_indices] = 1 - (1 - sustain_level) * (1 - np.exp(-3 * (decay_indices - decay_start) / decay_samples))
        
        # Release - exponential fade at end
        release_start = max(total_samples - release_samples, 0)
        release_indices = np.arange(release_start, total_samples)
        envelope[release_indices] = sustain_level * np.exp(-3 * (release_indices - release_start) / release_samples)
        
        # Apply envelope
        wave = wave * envelope
        
        # Add subtle LFO modulation for natural breathing effect
        lfo_rate = PRAYER_BOWL_CONFIG.get('tremolo_rate', 0.15)  # Very slow breathing
        lfo_depth = PRAYER_BOWL_CONFIG.get('tremolo_depth', 0.15)
        
        # Create LFO modulation
        lfo = lfo_depth * np.sin(2 * np.pi * lfo_rate * t)
        
        # Apply LFO to create natural volume pulsing
        wave = wave * (1 + lfo)
        
        # Add subtle vibrato (pitch modulation)
        vibrato_rate = PRAYER_BOWL_CONFIG.get('vibrato_rate', 0.05)
        vibrato_depth = PRAYER_BOWL_CONFIG.get('vibrato_depth', 0.02)
        
        # Apply vibrato by phase modulation
        vibrato_phase = 2 * np.pi * vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)
        wave_with_vibrato = np.zeros_like(wave)
        
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG['harmonic_ratios']):
            harmonic_freq = frequency * ratio
            amplitude = 1.0 / (i + 1)
            wave_with_vibrato += amplitude * np.sin(2 * np.pi * harmonic_freq * t + vibrato_phase)
        
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG['inharmonic_partials']):
            inharmonic_freq = frequency * ratio
            amplitude = 0.3 / (i + 1)
            wave_with_vibrato += amplitude * np.sin(2 * np.pi * inharmonic_freq * t + vibrato_phase)
        
        # Mix vibrato signal with original
        wave = 0.7 * wave + 0.3 * wave_with_vibrato
        
        # Normalize
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def layer_frequencies(self, frequency_list, duration=60, pure_sine=False):
        """
        Layer multiple frequencies together
        
        Args:
            frequency_list: [(freq, amplitude), ...]
            duration: Duration in seconds
            pure_sine: If True, use simple sine waves
            
        Returns:
            numpy array: Layered audio
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        wave = np.zeros_like(t)
        
        if pure_sine:
            # Original implementation for backward compatibility
            for freq, amplitude in frequency_list:
                wave += amplitude * np.sin(2 * np.pi * freq * t)
        else:
            # Prayer bowl synthesis for each frequency
            for freq, amplitude in frequency_list:
                tone = self.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
                wave += amplitude * tone
        
        # Normalize
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def generate_chakra_healing(self, chakra='heart', duration=300):
        """
        Generate focused healing for specific chakra with prayer bowl synthesis
        
        Args:
            chakra: Chakra name
            duration: Duration in seconds
            
        Returns:
            numpy array: Healing audio
        """
        chakra_frequencies = {
            'root': 396,
            'sacral': 417,
            'solar_plexus': 528,
            'heart': 639,
            'throat': 741,
            'third_eye': 852,
            'crown': 963
        }
        
        base_freq = chakra_frequencies.get(chakra, 528)
        
        # Generate prayer bowl tone for primary frequency
        primary = self.generate_prayer_bowl_tone(base_freq, duration, pure_sine=False)
        
        # Add Schumann resonance as supporting frequency
        schumann = self.generate_prayer_bowl_tone(7.83, duration, pure_sine=False)
        
        # Combine and normalize
        healing = primary + 0.3 * schumann
        healing = healing / np.max(np.abs(healing))
        
        return healing
    
    def generate_5_channel_blessing(self, intention, duration=300):
        """
        Generate 5 simultaneous frequencies for blessing
        
        Args:
            intention: Intention text (affects frequency modulation)
            duration: Duration in seconds
            
        Returns:
            numpy array: Blessing audio
        """
        # 5 frequencies - each chosen for specific purpose
        frequencies = [
            (7.83, 0.3),      # Earth resonance
            (136.1, 0.3),     # Year of Earth frequency
            (528, 0.4),        # DNA healing/love
            (639, 0.3),        # Relationships/connection
            (741, 0.3)         # Intuition/awakening
        ]
        
        return self.layer_frequencies(frequencies, duration, pure_sine=False)
    
    def play(self, wave, loop=False):
        """
        Play generated audio using sounddevice
        
        Args:
            wave: numpy array audio data
            loop: If True, loop the audio
        """
        try:
            if loop:
                sd.play(wave, self.sample_rate, loop=True)
            else:
                sd.play(wave, self.sample_rate)
            sd.wait()
        except Exception as e:
            print(f"Error playing audio: {e}")