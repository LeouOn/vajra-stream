"""
Enhanced Audio Generator — rich prayer bowl synthesis with LFO modulation.

Extends the audio synthesis capabilities of :mod:`core.audio_generator` with
additional features: natural LFO breathing modulation, chakra-specific healing
tones, and a dedicated 5-channel blessing generator that layers Earth resonance,
OM frequency, and Solfeggio tones with prayer bowl synthesis.

Dependencies:
    numpy, scipy, sounddevice — required at import time.
    config.settings.PRAYER_BOWL_CONFIG — ADSR, harmonic, and modulation parameters.

Exports:
    EnhancedAudioGenerator — main synthesis class (aliased as ``PrayerBowlGenerator``).

Typical usage:
    >>> gen = EnhancedAudioGenerator()
    >>> wave = gen.generate_chakra_healing("heart", duration=300)
    >>> gen.play(wave)
"""

import logging
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

try:
    from config.settings import PRAYER_BOWL_CONFIG
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).parent.parent))
    try:
        from config.settings import PRAYER_BOWL_CONFIG
    except ImportError:
        # Fallback if config package is not found directly
        import sys

        sys.path.append(str(Path(__file__).parent.parent / "config"))
        from settings import PRAYER_BOWL_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedAudioGenerator:
    """Enhanced audio synthesis with prayer bowl tones and LFO modulation.

    Builds on :class:`~core.audio_generator.ScalarWaveGenerator` concepts but is a
    standalone implementation with richer ADSR envelope handling (reading config
    for attack/decay/sustain/release), breathing LFO, dedicated chakra healing
    tones, and a 5-channel blessing preset.

    Attributes:
        sample_rate: Audio sample rate in Hz (default 44100).
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate: int = sample_rate

    def generate_prayer_bowl_tone(self, frequency: float, duration: int = 60, pure_sine: bool = False) -> "np.ndarray":
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
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["harmonic_ratios"]):
            harmonic_freq = frequency * ratio
            # Decrease amplitude for higher harmonics
            amplitude = 1.0 / (i + 1)
            wave += amplitude * np.sin(2 * np.pi * harmonic_freq * t)

        # Add inharmonic metallic partials
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["inharmonic_partials"]):
            inharmonic_freq = frequency * ratio
            # Lower amplitude for metallic character
            amplitude = 0.3 / (i + 1)
            wave += amplitude * np.sin(2 * np.pi * inharmonic_freq * t)

        # Apply ADSR envelope for natural bowl sound
        attack_time = PRAYER_BOWL_CONFIG.get("attack", 1.5)
        decay_time = PRAYER_BOWL_CONFIG.get("decay", 0.8)
        sustain_level = PRAYER_BOWL_CONFIG.get("sustain", 0.6)
        release_time = PRAYER_BOWL_CONFIG.get("release", 2.0)

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
        envelope[decay_indices] = 1 - (1 - sustain_level) * (
            1 - np.exp(-3 * (decay_indices - decay_start) / decay_samples)
        )

        # Release - exponential fade at end
        release_start = max(total_samples - release_samples, 0)
        release_indices = np.arange(release_start, total_samples)
        envelope[release_indices] = sustain_level * np.exp(-3 * (release_indices - release_start) / release_samples)

        # Apply envelope
        wave = wave * envelope

        # Add subtle LFO modulation for natural breathing effect
        lfo_rate = PRAYER_BOWL_CONFIG.get("tremolo_rate", 0.15)  # Very slow breathing
        lfo_depth = PRAYER_BOWL_CONFIG.get("tremolo_depth", 0.15)

        # Create LFO modulation
        lfo = lfo_depth * np.sin(2 * np.pi * lfo_rate * t)

        # Apply LFO to create natural volume pulsing
        wave = wave * (1 + lfo)

        # Add subtle vibrato (pitch modulation)
        vibrato_rate = PRAYER_BOWL_CONFIG.get("vibrato_rate", 0.05)
        vibrato_depth = PRAYER_BOWL_CONFIG.get("vibrato_depth", 0.02)

        # Apply vibrato by phase modulation
        vibrato_phase = 2 * np.pi * vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)
        wave_with_vibrato = np.zeros_like(wave)

        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["harmonic_ratios"]):
            harmonic_freq = frequency * ratio
            amplitude = 1.0 / (i + 1)
            wave_with_vibrato += amplitude * np.sin(2 * np.pi * harmonic_freq * t + vibrato_phase)

        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["inharmonic_partials"]):
            inharmonic_freq = frequency * ratio
            amplitude = 0.3 / (i + 1)
            wave_with_vibrato += amplitude * np.sin(2 * np.pi * inharmonic_freq * t + vibrato_phase)

        # Mix vibrato signal with original
        wave = 0.7 * wave + 0.3 * wave_with_vibrato

        # Normalize but significantly reduce overall volume for a quiet, ambient drone
        max_val = np.max(np.abs(wave))
        if max_val > 0:
            wave = (wave / max_val) * 0.3  # Reduced to 30% peak amplitude

        return wave

    def layer_frequencies(self, frequency_list: list[tuple[float, float]], duration: int = 60, pure_sine: bool = False) -> "np.ndarray":
        """Layer multiple frequencies together into a single waveform.

        Each frequency in the list is generated as a prayer bowl tone (or pure
        sine if ``pure_sine=True``), scaled by its amplitude, and summed.
        The result is normalised.

        Args:
            frequency_list: List of ``(freq_hz, amplitude)`` tuples.
            duration: Length in seconds (default 60).
            pure_sine: If True, use simple sine waves; otherwise use
                prayer bowl synthesis (default False).

        Returns:
            numpy.ndarray: Normalised mono layered waveform.
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

    def generate_chakra_healing(self, chakra: str = "heart", duration: int = 300) -> "np.ndarray":
        """Generate a focused healing tone for a specific chakra.

        Combines the chakra's associated Solfeggio frequency as a prayer bowl
        tone with the Schumann resonance (7.83 Hz) at 30% amplitude as a
        supporting grounding frequency.

        Chakra–frequency mapping:
            root (396), sacral (417), solar_plexus (528), heart (639),
            throat (741), third_eye (852), crown (963).

        Args:
            chakra: Chakra name (``"root"``, ``"heart"``, ``"crown"``, etc.).
                Defaults to ``"heart"``.
            duration: Length in seconds (default 300).

        Returns:
            numpy.ndarray: Normalised mono healing waveform.
        """
        chakra_frequencies = {
            "root": 396,
            "sacral": 417,
            "solar_plexus": 528,
            "heart": 639,
            "throat": 741,
            "third_eye": 852,
            "crown": 963,
        }

        base_freq = chakra_frequencies.get(chakra, 528)

        # Generate prayer bowl tone for primary frequency
        primary = self.generate_prayer_bowl_tone(base_freq, duration, pure_sine=False)

        # Add Schumann resonance as supporting frequency
        schumann = self.generate_prayer_bowl_tone(7.83, duration, pure_sine=False)

        # Combine and normalize, keeping amplitude quiet
        healing = primary + 0.3 * schumann
        max_val = np.max(np.abs(healing))
        if max_val > 0:
            healing = (healing / max_val) * 0.3

        return healing

    def generate_5_channel_blessing(self, intention: str, duration: int = 300) -> "np.ndarray":
        """Generate a 5-frequency blessing broadcast.

        Layers five frequencies chosen for holistic effect:
        - 7.83 Hz (Schumann / Earth resonance, amplitude 0.3)
        - 136.1 Hz (OM / Earth year, amplitude 0.3)
        - 528 Hz (DNA healing / love, amplitude 0.4)
        - 639 Hz (relationships / connection, amplitude 0.3)
        - 741 Hz (intuition / awakening, amplitude 0.3)

        Each tone uses prayer bowl synthesis for rich harmonic texture.

        Args:
            intention: Free-form intention string (currently informational;
                frequency selection is fixed in this version).
            duration: Length in seconds (default 300).

        Returns:
            numpy.ndarray: Normalised mono blessing waveform.
        """
        # 5 frequencies - each chosen for specific purpose
        frequencies = [
            (7.83, 0.3),  # Earth resonance
            (136.1, 0.3),  # Year of Earth frequency
            (528, 0.4),  # DNA healing/love
            (639, 0.3),  # Relationships/connection
            (741, 0.3),  # Intuition/awakening
        ]

        return self.layer_frequencies(frequencies, duration, pure_sine=False)

    def play(self, wave: "np.ndarray", loop: bool = False) -> None:
        """Play a generated waveform through the default audio device.

        Blocks until playback completes (calls ``sd.wait()`` internally).

        Args:
            wave: numpy array from any generation method.
            loop: If True, loop playback indefinitely.

        Raises:
            Prints error message to stdout on playback failure (does not raise).
        """
        try:
            if loop:
                sd.play(wave, self.sample_rate, loop=True)
            else:
                sd.play(wave, self.sample_rate)
            sd.wait()
        except Exception as e:
            print(f"Error playing audio: {e}")


# Add alias for backward compatibility
PrayerBowlGenerator = EnhancedAudioGenerator
