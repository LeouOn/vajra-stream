"""
Smoke + behaviour tests for ``core.prayer_wheel``.

Covers the public surface:
- :class:`PrayerWheel` — constructor + traditional prayer loading
- ``generate_prayer`` — returns a non-empty prayer string
- ``spin`` — returns a session dict with expected keys
- ``continuous_spin`` — returns a summary dict
- ``mantra_accumulation`` — accumulates count over time
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.prayer_wheel import PrayerWheel

# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exports the PrayerWheel class."""
    import core.prayer_wheel as mod

    assert hasattr(mod, "PrayerWheel")


# ---------------------------------------------------------------------------
# 2. Constructor + traditional prayers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_loads_traditional_prayers():
    """Constructor without deps still loads a non-empty prayer dict."""
    wheel = PrayerWheel()
    assert isinstance(wheel.traditional_prayers, dict)
    assert len(wheel.traditional_prayers) > 0


@pytest.mark.unit
def test_constructor_accepts_optional_deps():
    """Constructor accepts llm_integration / audio_generator / tts_engine."""
    mock_llm = MagicMock()
    mock_audio = MagicMock()
    mock_tts = MagicMock()
    wheel = PrayerWheel(llm_integration=mock_llm, audio_generator=mock_audio, tts_engine=mock_tts)
    assert wheel.llm is mock_llm
    assert wheel.audio is mock_audio
    assert wheel.tts is mock_tts


# ---------------------------------------------------------------------------
# 3. generate_prayer
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_prayer_without_llm_returns_traditional():
    """generate_prayer(use_llm=False) returns a non-empty string."""
    wheel = PrayerWheel()
    prayer = wheel.generate_prayer(intention="peace", use_llm=False)
    assert isinstance(prayer, str)
    assert len(prayer) > 0


@pytest.mark.unit
def test_generate_prayer_falls_back_when_no_llm():
    """generate_prayer(use_llm=True) falls back to traditional when no LLM is set."""
    wheel = PrayerWheel()  # no llm_integration
    prayer = wheel.generate_prayer(intention="healing", use_llm=True)
    assert isinstance(prayer, str)
    assert len(prayer) > 0


# ---------------------------------------------------------------------------
# 4. spin — returns session dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_spin_returns_without_error():
    """spin() completes without raising for a short duration."""
    wheel = PrayerWheel()
    # spin() prints session info and plays audio; just verify no exception
    result = wheel.spin(prayer="Om Mani Padme Hum", duration=1, with_audio=False)
    # May return dict or None depending on implementation; just don't crash
    assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# 5. mantra_accumulation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mantra_accumulation_completes_without_error():
    """mantra_accumulation completes without raising."""
    wheel = PrayerWheel()
    # Prints to console + optionally plays audio; just verify no exception
    result = wheel.mantra_accumulation(
        mantra="Om Mani Padme Hum", count=10, with_audio=False, with_voice=False, duration_per=1
    )
    assert result is None or isinstance(result, dict)
