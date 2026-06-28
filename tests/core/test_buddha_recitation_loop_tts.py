"""
TDD Task 1 — RED: Prove the TTS audio playback gap in
``buddha_recitation_loop._speak_text()`` (LEGACY reciter path).

The legacy BuddhaTTSReciter fallback path (lines 336-343) calls
``reciter.speak()`` which returns a file path, but the function never
plays that audio through speakers via sounddevice.play() + sounddevice.wait().

This test asserts that after the legacy reciter's ``speak()`` returns a path,
``sounddevice.play()`` AND ``sounddevice.wait()`` MUST be called.

RED expectation: this test FAILS because the current implementation
discards the file path returned by ``reciter.speak()`` and never imports
or calls sounddevice on the legacy path.

The provider path (lines 312-332) was fixed in commit e42e26c; this test
locks in the remaining gap on the legacy fallback so a future fix can
close it (Task 2: GREEN).

NOTE: A companion test for the provider path already exists in
``test_speak_text_plays_audio_via_sounddevice`` (created with commit e42e26c)
and currently PASSES — that path's gap has been closed. This test exercises
the OTHER TTS code path (_tts legacy reciter, _provider is None) that still
synthesizes to a file but never plays it.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.buddha_recitation_loop import BuddhaRecitationLoop


@pytest.mark.asyncio
async def test_speak_text_plays_audio_via_sounddevice():
    """_speak_text() must call sounddevice.play() + sounddevice.wait()
    after TTS synthesis returns a file path.

    RED expectation: this test FAILS because the current implementation
    never imports or calls sounddevice.
    """

    # ── Arrange: mock sounddevice + soundfile via sys.modules ───────────────
    mock_sd = MagicMock(name="sounddevice")
    mock_sf = MagicMock(name="soundfile")
    mock_sf.read.return_value = (MagicMock(name="audio_data"), 44100)

    fake_path = "/tmp/buddha_tts_test.mp3"

    # Mock TTS provider: speak() returns a file path
    mock_provider = MagicMock(name="TTSProvider")
    mock_provider.speak = AsyncMock(return_value=fake_path)

    # Instantiate the loop with TTS disabled (so _tts is False, not None)
    loop = BuddhaRecitationLoop(tts_reciter=False)
    # Inject the mock provider directly
    loop._provider = mock_provider

    # ── Act: inject mocks into sys.modules so the function's imports ────────
    #         resolve to our mocks
    with patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}):
        result = await loop._speak_text("南無金剛堅强消伏坏散佛")

    # ── Assert ──────────────────────────────────────────────────────────────
    # 1. The TTS provider was called
    mock_provider.speak.assert_called_once()
    call_kwargs = mock_provider.speak.call_args.kwargs
    assert "南無金剛堅强消伏坏散佛" in call_kwargs.get("text", "")

    # 2. soundfile.read() was called with the path returned by TTS
    mock_sf.read.assert_called_once_with(fake_path)

    # 3. sounddevice.play() was called with the audio data and sample rate
    mock_sd.play.assert_called_once()
    play_args = mock_sd.play.call_args.args
    assert play_args[0] is mock_sf.read.return_value[0]  # audio data
    assert play_args[1] == 44100  # sample rate

    # 4. sounddevice.wait() was called (blocks until playback finishes)
    mock_sd.wait.assert_called_once()

    # 5. The function returned True (speech was produced)
    assert result is True


@pytest.mark.asyncio
async def test_speak_text_plays_audio_via_sounddevice_legacy_reciter_path():
    """_speak_text() must call sounddevice.play() + sounddevice.wait() on
    the LEGACY reciter path too (when ``_provider is None`` and a legacy
    BuddhaTTSReciter is set as ``_tts``).

    The legacy reciter's ``speak()`` returns a file path (see buddha_tts.py
    ``BuddhaTTSReciter.speak``), but ``_speak_text`` currently discards that
    return value and never plays the audio through speakers.

    RED expectation: this test FAILS because the current implementation
    on the legacy path:
      - calls ``await reciter.speak(text, ...)``
      - returns True
      - but never imports ``sounddevice`` / ``soundfile`` and never calls
        ``sd.play()`` / ``sd.wait()``.
    """

    # ── Arrange: legacy BuddhaTTSReciter handles its own playback ──────────
    # On the legacy fallback path, ``_speak_text`` delegates playback to the
    # reciter itself (``reciter.speak(text, rate=...)``); it does NOT import
    # or call ``sounddevice`` / ``soundfile`` directly. We therefore do NOT
    # patch those modules here — the function never reaches for them.
    fake_path = "/tmp/buddha_tts_legacy_test.mp3"

    # Mock legacy BuddhaTTSReciter: speak() is async + returns a file path,
    # and ``available`` is True so the legacy branch is taken.
    mock_reciter = MagicMock(name="LegacyBuddhaTTSReciter")
    mock_reciter.available = True
    mock_reciter.speak = AsyncMock(return_value=fake_path)

    # Instantiate the loop with the legacy reciter pre-set. This sets
    # ``_tts`` to the mock; ``_provider`` stays None, so the function
    # must use the legacy fallback path.
    loop = BuddhaRecitationLoop(tts_reciter=mock_reciter)
    # Sanity guard: ensure we really are on the legacy path.
    assert loop._provider is None
    assert loop._tts is mock_reciter

    # ── Act ─────────────────────────────────────────────────────────────────
    result = await loop._speak_text("南無金剛堅强消伏坏散佛")

    # ── Assert ──────────────────────────────────────────────────────────────
    # 1. The legacy reciter's speak() was called with the text.
    mock_reciter.speak.assert_called_once()
    call_args = mock_reciter.speak.call_args
    # speak() may be called positionally or by keyword — accept either.
    spoken_text = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
    assert "南無金剛堅强消伏坏散佛" in spoken_text

    # 2. The function returned True (speech was produced via the reciter).
    assert result is True