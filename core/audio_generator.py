"""
Vajra.Stream Audio Generator — scalar wave and frequency synthesis for blessing/healing broadcasts.

Provides the foundational audio synthesis engine for the entire Vajra.Stream system.
Generates Schumann resonances, Solfeggio tones, binaural beats, OM frequency (136.1 Hz),
intention-modulated carrier waves, and multi-frequency layered prayer bowl tones
with natural ADSR envelopes, tremolo, and vibrato.

Dependencies:
    numpy, scipy — required at import time.
    sounddevice  — required only for actual playback (play() method). The import
                   is wrapped in try/except so the module loads cleanly on systems
                   without PortAudio (e.g. CI without libportaudio2 installed).
                   `ScalarWaveGenerator.play()` will raise a clear RuntimeError
                   if called without sounddevice available.
    config.settings.PRAYER_BOWL_CONFIG — optional; falls back gracefully if config
        module is not on sys.path.

Exports:
    ScalarWaveGenerator — main synthesis class.
    BLESSING_FREQUENCIES — dictionary of named frequency constants.
    INTENTION_TO_FREQUENCY — mapping of intention keywords to frequency lists.

Typical usage:
    >>> gen = ScalarWaveGenerator()
    >>> wave = gen.generate_prayer_bowl_tone(528, duration=60)
    >>> gen.play(wave)  # requires sounddevice + PortAudio
"""

import logging
import sys
from pathlib import Path

import numpy as np
from scipy import signal

# sounddevice is only required for actual audio playback. Allow the module
# to load on systems without PortAudio so the synthesis/analysis classes
# can be imported and unit-tested headlessly.
try:
    import sounddevice as sd

    _SOUNDDEVICE_AVAILABLE = True
except (ImportError, OSError) as _sd_err:
    sd = None  # type: ignore[assignment]
    _SOUNDDEVICE_AVAILABLE = False
    _SOUNDDEVICE_IMPORT_ERROR = _sd_err

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


class ScalarWaveGenerator:
    """Primary audio synthesis engine for Vajra.Stream.

    Generates biologically-active frequency patterns used throughout the system:
    Schumann resonances (Earth's electromagnetic heartbeat), Solfeggio sacred tones,
    binaural beats for brainwave entrainment, planetary frequencies, and rich
    prayer-bowl synthesis with harmonic overtones, ADSR envelopes, tremolo, and vibrato.

    All generation methods return numpy float64 arrays at ``self.sample_rate`` (default 44100 Hz).
    Use :meth:`play` to send audio to the default sound device, or pass the arrays
    to hardware broadcasters (e.g. :class:`~hardware.crystal_broadcaster.Level2CrystalBroadcaster`).

    Attributes:
        sample_rate: Audio sample rate in Hz (default 44100).
    """

    def __init__(self, sample_rate: int = 44100) -> None:
        self.sample_rate: int = sample_rate

    def generate_schumann_resonance(self, duration: int = 60) -> "np.ndarray":
        """Generate Earth's Schumann resonance at 7.83 Hz with natural harmonics.

        The fundamental (7.83 Hz) is combined with its first four harmonics
        (14.3, 20.8, 27.3, 33.8 Hz) at decreasing amplitudes to mimic the
        naturally-occurring atmospheric resonance.

        Args:
            duration: Length of the generated waveform in seconds (default 60).

        Returns:
            numpy.ndarray: Normalised mono waveform (float64, shape ``(n_samples,)``).
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

    def generate_solfeggio_tone(self, frequency: float, duration: int = 60) -> "np.ndarray":
        """Generate a pure Solfeggio sacred tone with subtle amplitude modulation.

        Common Solfeggio frequencies:
        - 396 Hz — liberating guilt and fear
        - 417 Hz — undoing situations and facilitating change
        - 528 Hz — transformation, miracles, "DNA repair / love frequency"
        - 639 Hz — connecting relationships
        - 741 Hz — awakening intuition
        - 852 Hz — returning to spiritual order

        A slow 0.1 Hz amplitude modulation (10% depth) is applied to give the
        tone a living, breathing quality.

        Args:
            frequency: Base frequency in Hz (e.g. 528).
            duration: Length in seconds (default 60).

        Returns:
            numpy.ndarray: Normalised mono waveform.
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))

        # Pure tone
        wave = np.sin(2 * np.pi * frequency * t)

        # Add subtle amplitude modulation for "alive" quality
        mod_freq = 0.1  # Very slow modulation
        modulation = 0.9 + 0.1 * np.sin(2 * np.pi * mod_freq * t)

        wave = wave * modulation

        return wave

    def generate_binaural_beat(self, base_freq: float, beat_freq: float, duration: int = 60) -> "np.ndarray":
        """Generate binaural beats for brainwave entrainment.

        Produces a stereo signal where the left channel carries ``base_freq``
        and the right channel carries ``base_freq + beat_freq``. When listened
        to with headphones the brain perceives the difference frequency as a
        pulse that can guide brainwave states.

        Common beat-frequency ranges:
        - 0.5–4 Hz — delta (deep sleep)
        - 4–8 Hz — theta (meditation, creativity)
        - 8–12 Hz — alpha (relaxed alertness)
        - 12–30 Hz — beta (active thinking)
        - 30+ Hz — gamma (insight, integration)

        Args:
            base_freq: Carrier frequency in Hz (e.g. 200).
            beat_freq: Difference frequency in Hz (e.g. 6 for theta).
            duration: Length in seconds (default 60).

        Returns:
            numpy.ndarray: Stereo waveform (float64, shape ``(n_samples, 2)``).
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration))

        # Left ear: base frequency
        left = np.sin(2 * np.pi * base_freq * t)

        # Right ear: base + beat frequency
        right = np.sin(2 * np.pi * (base_freq + beat_freq) * t)

        # Stereo output
        stereo = np.column_stack((left, right))

        return stereo

    def generate_om_frequency(self, duration: int = 60) -> "np.ndarray":
        """Generate the OM frequency (136.1 Hz).

        136.1 Hz corresponds to the orbital period of Earth around the Sun
        (calculated as an audible octave) and is traditionally associated with
        the primordial sound "OM". This is a convenience wrapper around
        :meth:`generate_solfeggio_tone`.

        Args:
            duration: Length in seconds (default 60).

        Returns:
            numpy.ndarray: Normalised mono waveform.
        """
        return self.generate_solfeggio_tone(136.1, duration)

    def generate_intention_carrier(
        self, intention_text: str, base_freq: float = 432, duration: int = 60
    ) -> "np.ndarray":
        """Create a carrier wave uniquely modulated by the user's intention text.

        Hashes ``intention_text`` into a deterministic but unique random seed,
        then generates a smooth low-frequency modulation pattern (3rd-order
        Butterworth low-pass at 0.01 × Nyquist) applied to a 432 Hz carrier.

        Args:
            intention_text: Free-form intention string (e.g. "May all beings be happy").
            base_freq: Carrier frequency in Hz (default 432, "natural tuning").
            duration: Length in seconds (default 60).

        Returns:
            numpy.ndarray: Normalised mono waveform with intention modulation.
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

    def layer_frequencies(
        self, frequency_list: list[tuple[float, float]], duration: int = 60, pure_sine: bool = False
    ) -> "np.ndarray":
        """Layer multiple frequencies together into a single waveform.

        Each frequency is generated independently (as a prayer bowl tone or
        pure sine, depending on ``pure_sine``), scaled by its amplitude, and
        summed. The result is normalised to avoid clipping.

        Args:
            frequency_list: List of ``(freq_hz, amplitude)`` tuples.
            duration: Length in seconds (default 60).
            pure_sine: If True, use simple sine waves; if False (default),
                use prayer bowl synthesis for each tone.

        Returns:
            numpy.ndarray: Normalised mono layered waveform.
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

    def generate_prayer_bowl_tone(self, frequency: float, duration: int = 60, pure_sine: bool = False) -> "np.ndarray":
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
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["harmonic_ratios"]):
            harmonic_freq = frequency * ratio
            # Decrease amplitude for higher harmonics
            amplitude = 1.0 / (i + 1)
            wave += amplitude * np.sin(2 * np.pi * harmonic_freq * t)

        # Add inharmonic metallic partials
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["inharmonic_partials"]):
            inharmonic_freq = frequency * ratio
            # Lower amplitude for metallic character
            amplitude = 0.08 / (i + 1)  # Made significantly quieter for a softer ambient sound
            wave += amplitude * np.sin(2 * np.pi * inharmonic_freq * t)

        # Apply ADSR envelope for natural bowl sound
        attack_time = getattr(sys.modules.get("config.settings"), "PRAYER_BOWL_ATTACK", 4.0)  # seconds
        decay_time = getattr(sys.modules.get("config.settings"), "PRAYER_BOWL_DECAY", 2.0)
        sustain_level = getattr(sys.modules.get("config.settings"), "PRAYER_BOWL_SUSTAIN", 0.4)
        release_time = getattr(sys.modules.get("config.settings"), "PRAYER_BOWL_RELEASE", 5.0)

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
        tremolo_rate = PRAYER_BOWL_CONFIG["tremolo_rate"]
        tremolo_depth = PRAYER_BOWL_CONFIG["tremolo_depth"]
        tremolo = 1 - tremolo_depth / 2 + tremolo_depth / 2 * np.sin(2 * np.pi * tremolo_rate * t)
        wave = wave * tremolo

        # Add subtle vibrato (pitch modulation)
        vibrato_rate = PRAYER_BOWL_CONFIG["vibrato_rate"]
        vibrato_depth = PRAYER_BOWL_CONFIG["vibrato_depth"]
        vibrato_phase = 2 * np.pi * vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)

        # Apply vibrato by phase modulation
        wave_with_vibrato = np.zeros_like(wave)
        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["harmonic_ratios"]):
            harmonic_freq = frequency * ratio
            amplitude = 1.0 / (i + 1)
            wave_with_vibrato += amplitude * np.sin(2 * np.pi * harmonic_freq * t + vibrato_phase)

        for i, ratio in enumerate(PRAYER_BOWL_CONFIG["inharmonic_partials"]):
            inharmonic_freq = frequency * ratio
            amplitude = 0.08 / (i + 1)
            wave_with_vibrato += amplitude * np.sin(2 * np.pi * inharmonic_freq * t + vibrato_phase)

        # Mix vibrato signal with original
        wave = 0.7 * wave + 0.3 * wave_with_vibrato

        # Normalize
        wave = wave / np.max(np.abs(wave))

        return wave

    def play(self, wave: "np.ndarray", loop: bool = False, blocking: bool = True) -> None:
        """Play a generated waveform through the default audio device.

        Args:
            wave: numpy array from any generation method.
            loop: If True, loop playback indefinitely.
            blocking: If True (default), block until playback finishes;
                if False, return immediately (background playback).
        """
        if not _SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice is not available — cannot play audio. "
                f"Original import error: {_SOUNDDEVICE_IMPORT_ERROR}. "
                "Install PortAudio (e.g. `apt-get install libportaudio2`) and "
                "sounddevice (`pip install sounddevice`) to enable playback."
            )
        if loop:
            sd.play(wave, samplerate=self.sample_rate, loop=True)
        else:
            sd.play(wave, samplerate=self.sample_rate)

        if blocking:
            sd.wait()

    def stop(self) -> None:
        """Stop any currently-playing audio on the default device."""
        if not _SOUNDDEVICE_AVAILABLE:
            return  # nothing playing, nothing to stop
        sd.stop()


# Frequency library
BLESSING_FREQUENCIES = {
    # Planetary frequencies (calculated from orbital periods)
    "earth_year": 136.1,  # OM frequency
    "earth_day": 194.18,
    "platonic_year": 172.06,
    # Solfeggio frequencies (ancient sacred tones)
    "liberation_from_fear": 396,
    "undoing_situations": 417,
    "transformation_miracles": 528,  # "Love frequency"
    "connecting_relationships": 639,
    "awakening_intuition": 741,
    "returning_to_spirit": 852,
    # Schumann resonances (Earth's frequencies)
    "schumann_fundamental": 7.83,
    "schumann_2nd": 14.3,
    "schumann_3rd": 20.8,
    # Brainwave entrainment
    "delta_sleep": 2.5,
    "theta_meditation": 6.0,
    "alpha_relaxation": 10.0,
    "beta_alertness": 20.0,
    "gamma_insight": 40.0,
}

INTENTION_TO_FREQUENCY = {
    "peace": [528, 639, 7.83],  # Love + connection + Earth
    "healing": [528, 417, 174],
    "wisdom": [852, 963, 40],  # Spirit + awakening + gamma
    "compassion": [639, 528, 10],  # Connection + love + alpha
    "protection": [396, 7.83, 285],
    "prosperity": [417, 10, 194.18],
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
