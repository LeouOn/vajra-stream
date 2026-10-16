"""VajraStreamService.generate_prayer_bowl_audio — enhanced path, no hardware.

Regression: the enhanced branch used to ``await`` the synchronous
``PrayerBowlGenerator.generate_prayer_bowl_tone`` and pass keyword arguments
it does not accept (``volume``, ``harmonic_strength``, ...). The resulting
TypeError was swallowed by the method's blanket ``except``, so every
prayer-bowl request silently returned the plain-sine fallback instead.

These tests install an explicit fake generator whose signature mirrors the
real one, and fail if the fallback path is taken.
"""

import numpy as np
import pytest

import backend.core.services.vajra_service as vajra_service_module
from backend.core.services.session_models import AudioConfig
from backend.core.services.vajra_service import VajraStreamService

SAMPLE_RATE = 44100


class FakePrayerBowlGenerator:
    """Same signature as core.enhanced_audio_generator.PrayerBowlGenerator.generate_prayer_bowl_tone."""

    def __init__(self):
        self.calls: list[dict] = []

    def generate_prayer_bowl_tone(self, frequency: float, duration: int = 60, pure_sine: bool = False) -> np.ndarray:
        self.calls.append({"frequency": frequency, "duration": duration, "pure_sine": pure_sine})
        return np.full(int(SAMPLE_RATE * duration), 0.5)


def make_service(generator) -> VajraStreamService:
    """A VajraStreamService with only the state generate_prayer_bowl_audio touches."""
    svc = VajraStreamService.__new__(VajraStreamService)
    svc.prayer_bowl_generator = generator
    svc.current_audio_data = None
    svc.audio_spectrum = []
    return svc


@pytest.fixture
def enhanced(monkeypatch):
    monkeypatch.setattr(vajra_service_module, "ENHANCED_MODE", True)
    gen = FakePrayerBowlGenerator()
    svc = make_service(gen)

    def _no_fallback(config):
        pytest.fail("generate_prayer_bowl_audio fell back to the plain-sine path")

    monkeypatch.setattr(svc, "_generate_fallback_audio", _no_fallback)
    return svc, gen


async def test_enhanced_path_calls_generator_with_its_real_signature(enhanced):
    svc, gen = enhanced

    audio = await svc.generate_prayer_bowl_audio(AudioConfig(frequency=528, duration=0.1, volume=1.0))

    assert gen.calls == [{"frequency": 528, "duration": 0.1, "pure_sine": False}]
    assert len(audio) == int(SAMPLE_RATE * 0.1)
    assert svc.current_audio_data is audio


async def test_prayer_bowl_mode_off_requests_pure_sine(enhanced):
    svc, gen = enhanced

    await svc.generate_prayer_bowl_audio(AudioConfig(frequency=432, duration=0.1, prayer_bowl_mode=False))

    assert gen.calls[0]["pure_sine"] is True


async def test_volume_scales_generator_output(enhanced):
    svc, _ = enhanced

    audio = await svc.generate_prayer_bowl_audio(AudioConfig(frequency=528, duration=0.1, volume=0.4))

    assert np.allclose(audio, 0.5 * 0.4)


async def test_zero_duration_is_clamped_not_empty(enhanced):
    svc, gen = enhanced

    audio = await svc.generate_prayer_bowl_audio(AudioConfig(frequency=528, duration=0.0))

    assert gen.calls[0]["duration"] > 0
    assert len(audio) > 0


async def test_fallback_still_records_current_audio(monkeypatch):
    """When the generator itself fails, the fallback must still become the playable buffer."""
    monkeypatch.setattr(vajra_service_module, "ENHANCED_MODE", True)

    class Exploding:
        def generate_prayer_bowl_tone(self, *args, **kwargs):
            raise RuntimeError("synth failure")

    svc = make_service(Exploding())

    audio = await svc.generate_prayer_bowl_audio(AudioConfig(frequency=528, duration=0.1, volume=0.5))

    assert len(audio) == int(SAMPLE_RATE * 0.1)
    assert svc.current_audio_data is audio
    assert svc.audio_spectrum, "fallback audio should also populate the spectrum"
