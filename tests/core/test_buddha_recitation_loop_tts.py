"""
TDD Task 1 — RED: Prove the TTS audio playback gap in
``buddha_recitation_loop._speak_text()``.

The function currently synthesises audio via the TTS provider (saving a file)
but never plays it back. This test asserts that after synthesis,
``sounddevice.play()`` and ``sounddevice.wait()`` are called — which they
are NOT in the current code, so the test MUST fail (RED).

After Task 2 adds the playback block, this same test MUST pass (GREEN).
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
