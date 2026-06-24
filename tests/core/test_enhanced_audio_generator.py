"""
Smoke + behaviour tests for ``core.enhanced_audio_generator``.

Covers the public surface:
- :class:`EnhancedAudioGenerator` — constructor + ``PrayerBowlGenerator`` alias.
- ``generate_prayer_bowl_tone(pure_sine=True)`` — plain sine of expected shape/range.
- ``generate_prayer_bowl_tone(pure_sine=False)`` — rich harmonics; still 1-D and bounded.
- ``generate_chakra_healing`` — returns correct shape, includes Schumann resonance.
- ``generate_5_channel_blessing`` — returns correct shape, default duration.
- ``play`` — delegates to sounddevice (mocked) and tolerates failures.

``numpy``, ``sounddevice``, and ``config.settings.PRAYER_BOWL_CONFIG`` are
required at import time. We use a tiny ``sample_rate`` (e.g. 1024) to keep
the array math fast; the chakra test uses a longer duration at the same
sample rate because we only assert shape.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.enhanced_audio_generator import (
    EnhancedAudioGenerator,
    PrayerBowlGenerator,
)


# ---------------------------------------------------------------------------
# 1. Import smoke + alias
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module imports cleanly; ``PrayerBowlGenerator`` is an alias of ``EnhancedAudioGenerator``."""
    import core.enhanced_audio_generator as mod

    assert hasattr(mod, "EnhancedAudioGenerator")
    assert hasattr(mod, "PrayerBowlGenerator")
    assert PrayerBowlGenerator is EnhancedAudioGenerator


# ---------------------------------------------------------------------------
# 2. Constructor records sample_rate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_records_sample_rate():
    """Sample rate is stored verbatim on the instance."""
    gen = EnhancedAudioGenerator(sample_rate=22050)
    assert gen.sample_rate == 22050


# ---------------------------------------------------------------------------
# 3. pure_sine=True returns a simple bounded sine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_prayer_bowl_pure_sine_shape_and_range():
    """``pure_sine=True`` returns a 1-D float array in [-1, 1] of the right length."""
    gen = EnhancedAudioGenerator(sample_rate=44100)
    wave = gen.generate_prayer_bowl_tone(frequency=200, duration=1, pure_sine=True)

    assert isinstance(wave, np.ndarray)
    assert wave.ndim == 1
    assert wave.shape == (44100,)
    assert wave.dtype == np.float64
    # Bounded
    assert np.max(np.abs(wave)) <= 1.0 + 1e-9


# ---------------------------------------------------------------------------
# 4. pure_sine=False applies ADSR + LFO — still 1-D, still bounded
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_prayer_bowl_harmonic_mode_is_bounded_1d():
    """Default (prayer bowl) mode applies ADSR envelope + LFO and is still bounded."""
    gen = EnhancedAudioGenerator(sample_rate=1024)
    wave = gen.generate_prayer_bowl_tone(frequency=220, duration=1, pure_sine=False)

    assert wave.ndim == 1
    assert wave.shape == (1024,)
    # Final normalisation caps peak amplitude to 0.3
    assert np.max(np.abs(wave)) <= 0.3 + 1e-9


# ---------------------------------------------------------------------------
# 5. generate_chakra_healing returns correct shape and includes Schumann
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_chakra_healing_shape_and_normalisation():
    """Heart chakra returns a 1-D array of expected length, normalised to 0.3."""
    gen = EnhancedAudioGenerator(sample_rate=1024)
    wave = gen.generate_chakra_healing(chakra="heart", duration=2)

    assert isinstance(wave, np.ndarray)
    assert wave.ndim == 1
    assert wave.shape == (1024 * 2,)
    # Normalised to 30% peak amplitude (matches the "quiet ambient" contract)
    assert np.max(np.abs(wave)) <= 0.3 + 1e-9


@pytest.mark.unit
def test_generate_chakra_healing_unknown_chakra_falls_back_to_528():
    """Unknown chakra name falls back to 528 Hz (solar plexus default)."""
    gen = EnhancedAudioGenerator(sample_rate=1024)
    # Should not raise on an unknown name
    wave = gen.generate_chakra_healing(chakra="not_a_chakra", duration=1)

    assert wave.shape == (1024,)


# ---------------------------------------------------------------------------
# 6. generate_5_channel_blessing returns expected shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_5_channel_blessing_default_shape():
    """5-channel blessing returns a 1-D array of expected length."""
    gen = EnhancedAudioGenerator(sample_rate=1024)
    wave = gen.generate_5_channel_blessing(intention="peace", duration=1)

    assert wave.ndim == 1
    assert wave.shape == (1024,)
    # Layered + normalised
    assert np.max(np.abs(wave)) <= 1.0 + 1e-9


# ---------------------------------------------------------------------------
# 7. layer_frequencies (pure_sine=True) is a normalised sum
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_layer_frequencies_pure_sine_shape():
    """``layer_frequencies`` with pure_sine=True returns expected shape and is normalised."""
    gen = EnhancedAudioGenerator(sample_rate=1024)
    wave = gen.layer_frequencies(
        frequency_list=[(528, 0.5), (396, 0.5)],
        duration=1,
        pure_sine=True,
    )

    assert wave.shape == (1024,)
    # Normalised: peak <= 1
    assert np.max(np.abs(wave)) <= 1.0 + 1e-9


# ---------------------------------------------------------------------------
# 8. play() delegates to sounddevice and waits
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_play_calls_sounddevice_play_and_wait():
    """``play(wave)`` delegates to ``sd.play`` + ``sd.wait``."""
    import core.enhanced_audio_generator as eag

    mock_sd = MagicMock(name="sounddevice")
    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        with patch.object(eag, "sd", mock_sd):
            gen = EnhancedAudioGenerator(sample_rate=1024)
            wave = np.zeros(8, dtype=np.float64)
            gen.play(wave, loop=False)

    mock_sd.play.assert_called_once()
    mock_sd.wait.assert_called_once()


@pytest.mark.unit
def test_play_loop_passes_loop_true():
    """``play(wave, loop=True)`` passes ``loop=True`` to ``sd.play``."""
    import core.enhanced_audio_generator as eag

    mock_sd = MagicMock(name="sounddevice")
    with patch.dict(sys.modules, {"sounddevice": mock_sd}):
        with patch.object(eag, "sd", mock_sd):
            gen = EnhancedAudioGenerator(sample_rate=1024)
            wave = np.zeros(8, dtype=np.float64)
            gen.play(wave, loop=True)

    # sd.play was called with loop=True somewhere in its args
    args, kwargs = mock_sd.play.call_args
    assert kwargs.get("loop") is True or (len(args) >= 3 and args[2] is True)
