"""
Vajra.Stream Audio Generator
Scalar wave and frequency generation for blessing/healing broadcasts
"""

import numpy as np
import sounddevice as sd
from scipy import signal
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import PRAYER_BOWL_CONFIG


class ScalarWaveGenerator:
    """
    Generate biologically-active frequency patterns
    Supports Schumann resonance, Solfeggio tones, planetary frequencies
    """
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        
    def generate_schumann_resonance(self, duration=60):
        """
        Earth's fundamental frequency: 7.83 Hz with harmonics
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Fundamental and harmonics
        fundamental = 7.83
        harmonics = [14.3, 20.8, 27.3, 33.8]
        
        wave = np.zeros_like(t)
        
        # Combine fundamental + harmonics with natural amplitude decay
        wave += np.sin(2 * np.pi * fundamental * t)
        for i, harmonic in enumerate(harmonics):
            amplitude = 1.0 / (i + 2)
            wave += amplitude * np.sin(2 * np.pi * harmonic * t)
        
        # Normalize
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def generate_solfeggio_tone(self, frequency, duration=60):
        """
        Solfeggio frequencies: 396, 417, 528, 639, 741, 852 Hz
        528 Hz is "DNA repair" / "love frequency"
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Pure tone
        wave = np.sin(2 * np.pi * frequency * t)
        
        # Add subtle amplitude modulation for "alive" quality
        mod_freq = 0.1  # Very slow modulation
        modulation = 0.9 + 0.1 * np.sin(2 * np.pi * mod_freq * t)
        
        wave = wave * modulation
        
        return wave
    
    def generate_binaural_beat(self, base_freq, beat_freq, duration=60):
        """
        Binaural beats for brainwave entrainment
        beat_freq: 4-8 Hz (theta), 8-12 Hz (alpha), etc.
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Left ear: base frequency
        left = np.sin(2 * np.pi * base_freq * t)
        
        # Right ear: base + beat frequency
        right = np.sin(2 * np.pi * (base_freq + beat_freq) * t)
        
        # Stereo output
        stereo = np.column_stack((left, right))
        
        return stereo
    
    def generate_om_frequency(self, duration=60):
        """
        136.1 Hz - "OM" frequency (C# based on Earth year)
        """
        return self.generate_solfeggio_tone(136.1, duration)
    
    def generate_intention_carrier(self, intention_text, base_freq=432, duration=60):
        """
        Create a carrier wave modulated by intention
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Convert intention to seed for modulation
        intention_seed = sum(ord(c) for c in intention_text)
        np.random.seed(intention_seed % 2**32)
        
        # Base carrier at 432 Hz (some say "natural tuning")
        carrier = np.sin(2 * np.pi * base_freq * t)
        
        # Intention modulation (subtle)
        mod_pattern = np.random.randn(len(t)) * 0.05
        
        # Apply low-pass filter to make it smooth
        mod_pattern = signal.filtfilt(*signal.butter(3, 0.01), mod_pattern)
        
        wave = carrier * (1 + mod_pattern)
        
        return wave
    
    def layer_frequencies(self, frequency_list, duration=60, pure_sine=False):
        """
        Layer multiple frequencies together
        frequency_list: [(freq, amplitude), ...]
        pure_sine: If True, use simple sine waves instead of prayer bowl synthesis
        """
        if pure_sine:
            # Original implementation for backward compatibility
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            wave = np.zeros_like(t)
            
            for freq, amplitude in frequency_list:
                wave += amplitude * np.sin(2 * np.pi * freq * t)
            
            # Normalize
            wave = wave / np.max(np.abs(wave))
            
            return wave
        else:
            # Prayer bowl synthesis for each frequency
            wave = np.zeros(int(self.sample_rate * duration))
            
            for freq, amplitude in frequency_list:
                tone = self.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
                wave += amplitude * tone
            
            # Normalize
            wave = wave / np.max(np.abs(wave))
            
            return wave
    
    def generate_prayer_bowl_tone(self, frequency, duration=60, pure_sine=False):
        """
        Generate prayer bowl synthesis with rich harmonics or pure sine wave
        
        Args:
            frequency: Base frequency in Hz
            duration: Duration in seconds
            pure_sine: If True, generate simple sine wave instead of prayer bowl
            
        Returns:
            numpy array: Generated audio waveform
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
        attack_time = 1.5  # seconds
        decay_time = 0.8
        sustain_level = 0.6
        release_time = 2.0
        
        attack_samples = int(attack_time * self.sample_rate)
        decay_samples = int(decay_time * self.sample_rate)
        release_samples = int(release_time * self.sample_rate)
        
        envelope = np.ones_like(t)
        
        # Attack - exponential rise
        attack_indices = np.arange(min(attack_samples, len(t)))
        envelope[attack_indices] = 1 - np.exp(-3 * attack_indices / attack_samples)
        
        # Decay - exponential fall to sustain level
        decay_start = attack_samples
        decay_end = min(decay_start + decay_samples, len(t))
        if decay_end > decay_start:
            decay_indices = np.arange(decay_end - decay_start)
            envelope[decay_start:decay_end] = 1 - (1 - sustain_level) * (1 - np.exp(-3 * decay_indices / decay_samples))
        
        # Release - exponential fade at end
        release_start = max(len(t) - release_samples, decay_end)
        if release_start < len(t):
            release_indices = np.arange(len(t) - release_start)
            envelope[release_start:] = sustain_level * np.exp(-3 * release_indices / release_samples)
        
        # Apply envelope
        wave = wave * envelope
        
        # Add subtle tremolo (amplitude modulation)
        tremolo_rate = PRAYER_BOWL_CONFIG['tremolo_rate']
        tremolo_depth = PRAYER_BOWL_CONFIG['tremolo_depth']
        tremolo = 1 - tremolo_depth/2 + tremolo_depth/2 * np.sin(2 * np.pi * tremolo_rate * t)
        wave = wave * tremolo
        
        # Add subtle vibrato (pitch modulation)
        vibrato_rate = PRAYER_BOWL_CONFIG['vibrato_rate']
        vibrato_depth = PRAYER_BOWL_CONFIG['vibrato_depth']
        vibrato_phase = 2 * np.pi * vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)
        
        # Apply vibrato by phase modulation
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
    
    def play(self, wave, loop=False, blocking=True):
        """
        Play generated wave
        """
        if loop:
            sd.play(wave, samplerate=self.sample_rate, loop=True)
        else:
            sd.play(wave, samplerate=self.sample_rate)
        
        if blocking:
            sd.wait()
    
    def stop(self):
        """
        Stop playback
        """
        sd.stop()


# Frequency library
BLESSING_FREQUENCIES = {
    # Planetary frequencies (calculated from orbital periods)
    'earth_year': 136.1,  # OM frequency
    'earth_day': 194.18,
    'platonic_year': 172.06,
    
    # Solfeggio frequencies (ancient sacred tones)
    'liberation_from_fear': 396,
    'undoing_situations': 417,
    'transformation_miracles': 528,  # "Love frequency"
    'connecting_relationships': 639,
    'awakening_intuition': 741,
    'returning_to_spirit': 852,
    
    # Schumann resonances (Earth's frequencies)
    'schumann_fundamental': 7.83,
    'schumann_2nd': 14.3,
    'schumann_3rd': 20.8,
    
    # Brainwave entrainment
    'delta_sleep': 2.5,
    'theta_meditation': 6.0,
    'alpha_relaxation': 10.0,
    'beta_alertness': 20.0,
    'gamma_insight': 40.0,
}

INTENTION_TO_FREQUENCY = {
    'peace': [528, 639, 7.83],  # Love + connection + Earth
    'healing': [528, 417, 174],
    'wisdom': [852, 963, 40],  # Spirit + awakening + gamma
    'compassion': [639, 528, 10],  # Connection + love + alpha
    'protection': [396, 7.83, 285],
    'prosperity': [417, 10, 194.18],
}


if __name__ == "__main__":
    # Test the generator
    gen = ScalarWaveGenerator()
    
    print("Testing Schumann Resonance (10 seconds)...")
    wave = gen.generate_schumann_resonance(duration=10)
    gen.play(wave)
    
    print("Testing OM Frequency (5 seconds)...")
    wave = gen.generate_om_frequency(duration=5)
    gen.play(wave)
    
    print("Testing layered frequencies (10 seconds)...")
    freqs = [(7.83, 0.3), (136.1, 0.3), (528, 0.4)]
    wave = gen.layer_frequencies(freqs, duration=10)
    gen.play(wave)
    
    print("Complete!")
