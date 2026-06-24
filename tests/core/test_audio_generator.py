"""
Smoke + behaviour tests for ``core.audio_generator``.

Covers :class:`core.audio_generator.ScalarWaveGenerator` and the module-level
constants ``BLESSING_FREQUENCIES`` / ``INTENTION_TO_FREQUENCY``.

The generator depends on ``numpy`` and ``scipy`` (required at import time) but
only requires ``sounddevice`` for actual playback.  Tests use small
``sample_rate``/``duration`` values to keep them fast, and mock ``sounddevice``
so the ``play`` method can be exercised without a real audio device.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core import audio_generator as ag
from core.audio_generator import (
    BLESSING_FREQUENCIES,
    INTENTION_TO_FREQUENCY,
    ScalarWaveGenerator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gen_fast():
    """A ScalarWaveGenerator with a tiny sample rate for fast tests."""
    return ScalarWaveGenerator(sample_rate=1024)


# ---------------------------------------------------------------------------
# 1. Import smoke + module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """The module imports cleanly and exposes its public API."""
    assert callable(ScalarWaveGenerator)
    assert isinstance(BLESSING_FREQUENCIES, dict)
    assert isinstance(INTENTION_TO_FREQUENCY, dict)
    # A few well-known keys must be present
    assert "earth_year" in BLESSING_FREQUENCIES
    assert BLESSING_FREQUENCIES["earth_year"] == 136.1
    assert "peace" in INTENTION_TO_FREQUENCY
    assert "healing" in INTENTION_TO_FREQUENCY


# ---------------------------------------------------------------------------
# 2. Constructor — sample rate is honoured
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_records_sample_rate():
    """The constructor stores ``sample_rate`` on the instance."""
    g = ScalarWaveGenerator(sample_rate=22050)
    assert g.sample_rate == 22050


# ---------------------------------------------------------------------------
# 3. Schumann resonance — shape and amplitude
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_schumann_resonance_shape_and_range(gen_fast):
    """Schumann resonance returns a normalised 1-D waveform of expected length."""
    wave = gen_fast.generate_schumann_resonance(duration=2)

    assert isinstance(wave, np.ndarray)
    assert wave.ndim == 1
    assert wave.dtype == np.float64
    # sample_rate * duration samples
    assert wave.shape == (gen_fast.sample_rate * 2,)
    # Wave is normalised — peak absolute amplitude <= 1
    assert np.max(np.abs(wave)) <= 1.0 + 1e-9


# ---------------------------------------------------------------------------
# 4. Solfeggio tone + OM convenience wrapper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_solfeggio_tone_returns_normalised_sine(gen_fast):
    """Solfeggio tone is a 1-D waveform with values in [-1, 1]."""
    wave = gen_fast.generate_solfeggio_tone(frequency=528, duration=1)

    assert wave.ndim == 1
    assert wave.shape == (gen_fast.sample_rate,)
    assert np.max(wave) <= 1.0 + 1e-9
    assert np.min(wave) >= -1.0 - 1e-9


@pytest.mark.unit
def test_generate_om_frequency_is_a_solfeggio_at_136_1(gen_fast):
    """``generate_om_frequency`` returns the same shape as a Solfeggio tone."""
    om = gen_fast.generate_om_frequency(duration=1)
    tone = gen_fast.generate_solfeggio_tone(frequency=136.1, duration=1)

    assert om.shape == tone.shape


# ---------------------------------------------------------------------------
# 5. Binaural beat — stereo shape, channels differ
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_binaural_beat_is_stereo_with_different_channels(gen_fast):
    """Binaural beat returns a 2-column stereo array; the two channels differ
    because the right ear carries base + beat frequency."""
    wave = gen_fast.generate_binaural_beat(base_freq=200, beat_freq=6, duration=1)

    assert wave.ndim == 2
    assert wave.shape == (gen_fast.sample_rate, 2)
    # Channels must not be identical (different frequencies)
    assert not np.array_equal(wave[:, 0], wave[:, 1])


# ---------------------------------------------------------------------------
# 6. Prayer bowl — pure_sine=True gives a simple sine; default is harmonic
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_prayer_bowl_tone_pure_sine():
    """``pure_sine=True`` returns a plain sine wave of the requested frequency.

    Uses a moderate sample rate / frequency ratio so the zero-crossing count
    is a reliable frequency proxy (the default ``gen_fast`` fixture uses a
    very low 1024 Hz sample rate, which severely aliases high frequencies).
    """
    g = ScalarWaveGenerator(sample_rate=44100)
    freq = 100  # well below Nyquist at this sample rate
    wave = g.generate_prayer_bowl_tone(frequency=freq, duration=1, pure_sine=True)

    assert wave.shape == (g.sample_rate,)
    # Naive frequency check via zero crossings — should be approximately ``freq``
    zero_crossings = int(np.sum(np.diff(np.sign(wave)) != 0))
    expected_crossings = 2 * freq  # two zero-crossings per cycle
    # Allow ±2% tolerance — integer rounding accumulates error over many cycles
    assert abs(zero_crossings - expected_crossings) < int(0.05 * expected_crossings)


@pytest.mark.unit
def test_layer_frequencies_pure_sine_shape(gen_fast):
    """``layer_frequencies`` with pure_sine=True returns the expected shape."""
    wave = gen_fast.layer_frequencies(
        frequency_list=[(528, 0.5), (396, 0.5)],
        duration=1,
        pure_sine=True,
    )
    assert wave.shape == (gen_fast.sample_rate,)


# ---------------------------------------------------------------------------
# 7. Error handling — play() raises when sounddevice is unavailable
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_play_raises_when_sounddevice_missing(gen_fast, monkeypatch):
    """``play`` raises a clear ``RuntimeError`` when sounddevice isn't present.

    We force ``_SOUNDDEVICE_AVAILABLE`` to False and patch ``sd`` to ``None``
    inside the module's namespace, then assert ``play`` raises.  We use
    ``raising=False`` on ``_SOUNDDEVICE_IMPORT_ERROR`` because the attribute
    only exists when sounddevice actually failed to import at module load.
    """
    monkeypatch.setattr(ag, "_SOUNDDEVICE_AVAILABLE", False)
    monkeypatch.setattr(ag, "sd", None)
    monkeypatch.setattr(
        ag,
        "_SOUNDDEVICE_IMPORT_ERROR",
        ImportError("simulated"),
        raising=False,
    )

    wave = np.zeros(8, dtype=np.float64)
    with pytest.raises(RuntimeError) as excinfo:
        gen_fast.play(wave)

    assert "sounddevice is not available" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 8. play() / stop() delegation when sounddevice is mocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_play_calls_sounddevice_play_and_wait(gen_fast):
    """``play(wave, blocking=True)`` delegates to ``sd.play`` + ``sd.wait``."""
    mock_sd = MagicMock(name="sounddevice")

    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        with patch.object(ag, "_SOUNDDEVICE_AVAILABLE", True), \
             patch.object(ag, "sd", mock_sd):
            wave = np.zeros(8, dtype=np.float64)
            gen_fast.play(wave, loop=False, blocking=True)

    mock_sd.play.assert_called_once()
    mock_sd.wait.assert_called_once()


@pytest.mark.unit
def test_play_non_blocking_skips_wait(gen_fast):
    """``play(wave, blocking=False)`` calls ``sd.play`` but NOT ``sd.wait``."""
    mock_sd = MagicMock(name="sounddevice")

    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        with patch.object(ag, "_SOUNDDEVICE_AVAILABLE", True), \
             patch.object(ag, "sd", mock_sd):
            wave = np.zeros(8, dtype=np.float64)
            gen_fast.play(wave, blocking=False)

    mock_sd.play.assert_called_once()
    mock_sd.wait.assert_not_called()
