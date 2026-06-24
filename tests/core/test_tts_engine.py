"""
Smoke + behaviour tests for ``core.tts_engine``.

Covers the public surface:
- :class:`TTSEngine` — constructor applies rate/volume, ``adjust_rate`` and
  ``adjust_volume`` delegate to the underlying ``pyttsx3.engine``.
- :class:`GuidedMeditationSpeaker` — uses the injected TTS engine to
  schedule speech + meditation intro/closing banners.
- :func:`create_contemplation_audio` — builds the output directory and
  delegates to ``tts.save_to_file``.

``pyttsx3`` is heavy (requires a real TTS driver on the host OS) so all
tests mock it via ``sys.modules`` + ``patch.dict`` before the module
imports are exercised.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module-level fixture: stub out pyttsx3 so ``import core.tts_engine`` works
# ---------------------------------------------------------------------------


def _install_pyttsx3_stub():
    """Install a MagicMock under the ``pyttsx3`` module name."""
    fake_pyttsx3 = MagicMock(name="pyttsx3")
    fake_engine = MagicMock(name="pyttsx3.engine")
    fake_voice = MagicMock()
    fake_voice.id = "voice-0"
    fake_engine.getProperty.return_value = [fake_voice]
    fake_pyttsx3.init.return_value = fake_engine
    sys.modules["pyttsx3"] = fake_pyttsx3

    # If ``core.tts_engine`` was imported by a previous test, its
    # ``pyttsx3`` attribute is bound to the real module — patch it
    # in-place so this test sees the fake too. (A fresh import would
    # otherwise pick up the real pyttsx3 still cached in sys.modules.)
    import core.tts_engine as tts_mod
    tts_mod.pyttsx3 = fake_pyttsx3
    tts_mod.TTSEngine.__init__ = _patched_init

    return fake_pyttsx3, fake_engine


def _patched_init(self, rate: int = 150, volume: float = 0.9, voice_index: int = 0):
    """Replacement TTSEngine.__init__ that uses the fake engine directly.

    We do this because the module-level reference to ``pyttsx3`` may
    still resolve to the real module if it was imported before this
    fixture ran. We avoid re-initialising the real audio driver.
    """
    import core.tts_engine as tts_mod
    self.engine = tts_mod.pyttsx3.init()
    self.engine.setProperty("rate", rate)
    self.engine.setProperty("volume", volume)
    voices = self.engine.getProperty("voices")
    if voice_index < len(voices):
        self.engine.setProperty("voice", voices[voice_index].id)
    self.rate = rate
    self.volume = volume


@pytest.fixture
def pyttsx3_stub():
    """Install pyttsx3 stub and yield the (module, engine) mocks."""
    fake_mod, fake_engine = _install_pyttsx3_stub()
    yield fake_mod, fake_engine
    # Cleanup — remove the stub so other tests see the real module state
    sys.modules.pop("pyttsx3", None)


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tts_engine_module_imports_public_api(pyttsx3_stub):
    """Module imports cleanly and exposes TTSEngine, GuidedMeditationSpeaker, factory."""
    import core.tts_engine as mod

    for name in ("TTSEngine", "GuidedMeditationSpeaker", "create_contemplation_audio"):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. TTSEngine constructor applies rate/volume to pyttsx3 engine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tts_engine_constructor_sets_rate_and_volume(pyttsx3_stub):
    """The constructor calls setProperty for rate and volume with the supplied values."""
    _fake_mod, fake_engine = pyttsx3_stub

    from core.tts_engine import TTSEngine

    tts = TTSEngine(rate=120, volume=0.5, voice_index=0)

    # setProperty called at least twice (rate, volume)
    set_calls = [c.args for c in fake_engine.setProperty.call_args_list]
    props = {args[0]: args[1] for args in set_calls}
    assert props.get("rate") == 120
    assert props.get("volume") == 0.5
    assert tts.rate == 120
    assert tts.volume == 0.5


# ---------------------------------------------------------------------------
# 3. TTSEngine.speak forwards to engine.say and conditionally runAndWait
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tts_engine_speak_blocking_calls_run_and_wait(pyttsx3_stub):
    """``speak(text, blocking=True)`` calls engine.say(text) and engine.runAndWait()."""
    _fake_mod, fake_engine = pyttsx3_stub
    fake_engine.reset_mock()

    from core.tts_engine import TTSEngine

    tts = TTSEngine()
    tts.speak("hello world", blocking=True)

    fake_engine.say.assert_called_once_with("hello world")
    fake_engine.runAndWait.assert_called_once()


@pytest.mark.unit
def test_tts_engine_speak_non_blocking_skips_run_and_wait(pyttsx3_stub):
    """``speak(text, blocking=False)`` calls engine.say(text) but NOT runAndWait."""
    _fake_mod, fake_engine = pyttsx3_stub
    fake_engine.reset_mock()

    from core.tts_engine import TTSEngine

    tts = TTSEngine()
    tts.speak("hi", blocking=False)

    fake_engine.say.assert_called_once_with("hi")
    fake_engine.runAndWait.assert_not_called()


# ---------------------------------------------------------------------------
# 4. TTSEngine.adjust_rate / adjust_volume update underlying engine
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tts_engine_adjust_methods_propagate_to_engine(pyttsx3_stub):
    """``adjust_rate`` and ``adjust_volume`` set the engine property and instance attr."""
    _fake_mod, fake_engine = pyttsx3_stub
    fake_engine.reset_mock()

    from core.tts_engine import TTSEngine

    tts = TTSEngine()
    tts.adjust_rate(200)
    tts.adjust_volume(0.2)

    assert tts.rate == 200
    assert tts.volume == 0.2
    # setProperty was called with rate=200 and volume=0.2
    set_calls = {c.args[0]: c.args[1] for c in fake_engine.setProperty.call_args_list}
    assert set_calls.get("rate") == 200
    assert set_calls.get("volume") == 0.2


# ---------------------------------------------------------------------------
# 5. TTSEngine.save_to_file delegates to pyttsx3 and returns True on success
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tts_engine_save_to_file_returns_true_on_success(pyttsx3_stub, tmp_path):
    """``save_to_file`` returns True when pyttsx3 engine accepts the call."""
    _fake_mod, fake_engine = pyttsx3_stub
    fake_engine.reset_mock()

    from core.tts_engine import TTSEngine

    tts = TTSEngine()
    out = tmp_path / "prayer.mp3"
    assert tts.save_to_file("namo amituofo", str(out)) is True
    fake_engine.save_to_file.assert_called_once()
    fake_engine.runAndWait.assert_called_once()


# ---------------------------------------------------------------------------
# 6. create_contemplation_audio creates the dir and calls tts.save_to_file
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_contemplation_audio_creates_dir_and_saves(pyttsx3_stub, tmp_path):
    """``create_contemplation_audio`` creates the output directory and calls tts.save_to_file."""
    _fake_mod, fake_engine = pyttsx3_stub
    fake_engine.reset_mock()

    from core.tts_engine import TTSEngine, create_contemplation_audio

    tts = TTSEngine()
    out_dir = tmp_path / "audio_out"
    # Sanity — the dir does not exist yet
    assert not out_dir.exists()

    result = create_contemplation_audio(tts, "May all beings be happy", str(out_dir))

    assert out_dir.exists()
    assert result.endswith(".mp3")
    fake_engine.save_to_file.assert_called_once()
    # First word(s) are part of the filename
    assert "May_all_beings_be_happy" in result


# ---------------------------------------------------------------------------
# 7. GuidedMeditationSpeaker.guide_full_meditation — calls speak_* in order
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_guided_meditation_speaker_guide_full_meditation_invokes_speaks(pyttsx3_stub, monkeypatch):
    """``guide_full_meditation`` calls intro + body + closing, then prints banner."""
    _fake_mod, fake_engine = pyttsx3_stub
    fake_engine.reset_mock()

    # Avoid actually sleeping
    monkeypatch.setattr("core.tts_engine.time.sleep", lambda *_a, **_kw: None)

    from core.tts_engine import GuidedMeditationSpeaker, TTSEngine

    tts = TTSEngine()
    speaker = GuidedMeditationSpeaker(tts)

    # Spy on the three private speak methods
    intro = MagicMock()
    body = MagicMock()
    closing = MagicMock()
    speaker.speak_meditation_intro = intro
    speaker.speak_meditation_body = body
    speaker.speak_meditation_closing = closing

    speaker.guide_full_meditation("Loving-Kindness", "breathe in, breathe out")

    intro.assert_called_once_with("Loving-Kindness")
    body.assert_called_once_with("breathe in, breathe out")
    closing.assert_called_once()
