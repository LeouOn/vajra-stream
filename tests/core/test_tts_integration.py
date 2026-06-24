"""
Smoke + behaviour tests for ``core.tts_integration``.

Covers the high-level TTS abstraction:

* Module-level enums / dataclasses (``TTSEngineType``, ``VoiceGender``,
  ``SpeakingRate``, ``Voice``, ``TTSConfig``)
* The base :class:`TTSEngine` and its ``preprocess_text`` helper
* The three concrete engines: :class:`Pyttsx3Engine`,
  :class:`GTTSEngine`, and the :class:`EdgeTTSEngine` stub
* The :class:`TTSNarrator` high-level wrapper (engine fallback, voice
  listing, ``generate_audio`` delegation, ``narrate_story``,
  ``generate_mantra_audio``, ``guided_meditation``, ``commemorate_event``)
* The module-level ``quick_narrate`` / ``narrate_mantra`` helpers

External TTS engines (``pyttsx3``, ``gTTS``, ``edge_tts``) are treated
as optional: tests pass whether or not they're installed, by exercising
the engines via mocks and by going through paths that the engines'
``is_available()`` flag controls.  No real audio device or network
access is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core import tts_integration as ti
from core.tts_integration import (
    GTTSEngine,
    Pyttsx3Engine,
    EdgeTTSEngine,
    SpeakingRate,
    TTSConfig,
    TTSEngine,
    TTSEngineType,
    TTSNarrator,
    Voice,
    VoiceGender,
    narrate_mantra,
    quick_narrate,
)


# ---------------------------------------------------------------------------
# 1. Import smoke + module-level constants / availability flags
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """Module imports cleanly and exposes its public API + availability flags."""
    # Enums
    assert TTSEngineType.PYTTSX3.value == "pyttsx3"
    assert TTSEngineType.GTTS.value == "gtts"
    assert TTSEngineType.EDGE_TTS.value == "edge_tts"
    assert TTSEngineType.AUTO.value == "auto"

    # VoiceGender has three members
    assert {g.value for g in VoiceGender} == {"male", "female", "neutral"}

    # SpeakingRate has four members
    assert {r.value for r in SpeakingRate} == {
        "very_slow",
        "slow",
        "normal",
        "fast",
    }

    # The "HAS_*" flags are always booleans (some engines may be missing)
    assert isinstance(ti.HAS_PYTTSX3, bool)
    assert isinstance(ti.HAS_GTTS, bool)
    assert isinstance(ti.HAS_EDGE_TTS, bool)
    assert isinstance(ti.HAS_NARRATIVES, bool)


# ---------------------------------------------------------------------------
# 2. Voice + TTSConfig dataclasses — defaults and equality
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_voice_and_ttsconfig_defaults():
    """``Voice`` and ``TTSConfig`` construct with sensible defaults."""
    voice = Voice(id="v1", name="Test", gender=VoiceGender.FEMALE)
    assert voice.language == "en"
    assert voice.engine == ""
    assert voice.quality == "standard"

    cfg = TTSConfig()
    assert cfg.engine == TTSEngineType.AUTO
    assert cfg.voice_id is None
    assert cfg.rate == SpeakingRate.NORMAL
    assert cfg.volume == 1.0
    assert cfg.pitch is None
    assert cfg.add_pauses is True
    assert cfg.pause_duration == 1.0


# ---------------------------------------------------------------------------
# 3. TTSEngine.preprocess_text — strips markdown headers and emphasis
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_preprocess_text_strips_markdown():
    """``TTSEngine.preprocess_text`` removes headers, bold, italic."""
    # Use a tiny concrete subclass so we can call the helper.
    class _Stub(TTSEngine):
        def synthesize(self, text, output_file, **kwargs):  # pragma: no cover
            return output_file

        def get_voices(self):  # pragma: no cover
            return []

        def is_available(self):  # pragma: no cover
            return False

    raw = "# Title\n**bold** and *italic* and _under_"
    cleaned = _Stub().preprocess_text(raw)
    assert "# Title" not in cleaned
    assert "**" not in cleaned
    assert "Title" in cleaned
    assert "bold" in cleaned
    assert "italic" in cleaned
    assert "under" in cleaned


# ---------------------------------------------------------------------------
# 4. EdgeTTSEngine stub — synthesize() raises a clear error
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_edge_tts_engine_synthesize_raises_stub_error():
    """The Edge TTS stub raises ``RuntimeError`` (full impl deferred)."""
    engine = EdgeTTSEngine()
    # The stub always reports unavailable and has no voices.
    assert engine.is_available() is False
    assert engine.get_voices() == []

    with pytest.raises(RuntimeError) as excinfo:
        engine.synthesize("hello", "/tmp/x.mp3")
    assert "edge-tts" in str(excinfo.value).lower()
    assert "not yet implemented" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. Pyttsx3Engine / GTTSEngine — graceful degradation when unavailable
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pyttsx3_engine_unavailable_returns_empty_voices():
    """Pyttsx3Engine returns no voices and reports unavailable when missing."""
    engine = Pyttsx3Engine()
    if not ti.HAS_PYTTSX3:
        # Engine is None and is_available is False
        assert engine.is_available() is False
    # Either way, get_voices() must not raise and must return a list
    voices = engine.get_voices()
    assert isinstance(voices, list)


@pytest.mark.unit
def test_gtts_engine_synthesize_raises_when_missing():
    """GTTSEngine.synthesize raises a clear ``RuntimeError`` when not installed."""
    if ti.HAS_GTTS:
        pytest.skip("gTTS is installed; cannot test the missing-engine path")
    engine = GTTSEngine()
    assert engine.is_available() is False
    assert engine.get_voices() == []
    with pytest.raises(RuntimeError) as excinfo:
        engine.synthesize("hello", "/tmp/x.mp3")
    assert "gtts" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# 6. TTSNarrator — engine fallback, voice listing, generate_audio delegation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ttsnarrator_selects_engine_or_falls_back_to_stub(capsys):
    """``TTSNarrator`` picks the first available engine and never raises for missing deps.

    When the requested backend is missing, the constructor either
    falls back to AUTO selection or falls back to the EdgeTTSEngine
    stub.  We assert that ``list_voices()`` does not raise.
    """
    # Use AUTO so the constructor picks whatever's available.
    narrator = TTSNarrator(engine=TTSEngineType.AUTO)
    voices = narrator.list_voices()
    assert isinstance(voices, list)
    # The engine is one of the three concrete classes
    assert isinstance(
        narrator.engine, (Pyttsx3Engine, GTTSEngine, EdgeTTSEngine)
    )


@pytest.mark.unit
def test_ttsnarrator_generate_audio_delegates_to_engine():
    """``generate_audio`` forwards text + rate + volume to the underlying engine.

    We swap the engine for a mock so no real TTS library is invoked.
    """
    mock_engine = MagicMock()
    mock_engine.synthesize.return_value = "/tmp/out.mp3"
    narrator = TTSNarrator()
    narrator.engine = mock_engine
    narrator.voice = "fake-voice"

    out = narrator.generate_audio(
        text="hello world",
        output_file="/tmp/out.mp3",
        rate=SpeakingRate.SLOW,
        volume=0.5,
    )
    assert out == "/tmp/out.mp3"
    mock_engine.synthesize.assert_called_once()
    call_kwargs = mock_engine.synthesize.call_args.kwargs
    # rate / volume / voice_id forwarded
    assert call_kwargs["rate"] == SpeakingRate.SLOW
    assert call_kwargs["volume"] == 0.5
    assert call_kwargs["voice_id"] == "fake-voice"
    # Positional args are text + output_file
    args = mock_engine.synthesize.call_args.args
    assert args[0] == "hello world"
    assert args[1] == "/tmp/out.mp3"


# ---------------------------------------------------------------------------
# 7. TTSNarrator.generate_mantra_audio — repetition count
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_mantra_audio_includes_repetitions():
    """``generate_mantra_audio`` joins the mantra ``repetitions`` times
    and delegates to the engine.  We assert on the *joined text* via a
    mock engine.
    """
    mock_engine = MagicMock()
    mock_engine.synthesize.return_value = "/tmp/mantra.mp3"
    narrator = TTSNarrator()
    narrator.engine = mock_engine

    narrator.generate_mantra_audio(
        mantra="Om Mani Padme Hum",
        repetitions=3,
        output_file="/tmp/mantra.mp3",
    )

    mock_engine.synthesize.assert_called_once()
    text_arg = mock_engine.synthesize.call_args.args[0]
    # All 3 mantra occurrences plus the 2 pause markers ("...")
    assert text_arg.count("Om Mani Padme Hum") == 3
    assert text_arg.count("...") == 2


# ---------------------------------------------------------------------------
# 8. TTSNarrator.guided_meditation — pause marker substitution
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_guided_meditation_substitutes_pause_markers():
    """``guided_meditation`` replaces [PAUSE:N] and [BREATHE] markers."""
    mock_engine = MagicMock()
    mock_engine.synthesize.return_value = "/tmp/meditation.mp3"
    narrator = TTSNarrator()
    narrator.engine = mock_engine

    script = "Begin. [PAUSE:5] Continue. [BREATHE] End."
    narrator.guided_meditation(script=script, output_file="/tmp/meditation.mp3")

    text_arg = mock_engine.synthesize.call_args.args[0]
    # [PAUSE:5] replaced with "..." (the simple-pause marker)
    assert "[PAUSE:5]" not in text_arg
    # [BREATHE] replaced with "... breathe ..."
    assert "[BREATHE]" not in text_arg
    assert "breathe" in text_arg
    # Original words preserved
    assert "Begin." in text_arg
    assert "Continue." in text_arg
    assert "End." in text_arg


# ---------------------------------------------------------------------------
# 9. TTSNarrator.commmemorate_event — text composition
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_commemorate_event_composes_text(tmp_path):
    """``commemorate_event`` produces text containing the event name, date, and deaths."""
    import datetime as _dt

    mock_engine = MagicMock()
    mock_engine.synthesize.return_value = "/tmp/event.mp3"
    narrator = TTSNarrator()
    narrator.engine = mock_engine

    event = {
        "name": "Test Tragedy",
        "estimated_deaths": 1000,
        "blessing_focus": "May peace prevail.",
        "mantras": ["Om Ah Hum", "Gate Gate"],
    }
    date = _dt.datetime(1945, 8, 6)

    narrator.commemorate_event(event=event, date=date, output_file="/tmp/event.mp3")

    text_arg = mock_engine.synthesize.call_args.args[0]
    assert "Test Tragedy" in text_arg
    assert "August 06, 1945" in text_arg
    assert "1,000" in text_arg  # formatted with thousands separator
    # First two mantras included
    assert "Om Ah Hum" in text_arg
    assert "Gate Gate" in text_arg


# ---------------------------------------------------------------------------
# 10. Module-level convenience functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quick_narrate_with_slow_flag(monkeypatch):
    """``quick_narrate`` uses ``SpeakingRate.SLOW`` when slow=True, else NORMAL."""
    captured_rates = []

    class _FakeNarrator:
        def __init__(self, engine):
            pass

        def generate_audio(self, text, output_file, rate, **kwargs):
            captured_rates.append(rate)
            return output_file

    # Force TTSNarrator to be our fake so we can observe the rate
    monkeypatch.setattr(ti, "TTSNarrator", _FakeNarrator)

    quick_narrate("hi", output_file="/tmp/q.mp3", slow=True)
    quick_narrate("hi", output_file="/tmp/q.mp3", slow=False)
    assert captured_rates == [SpeakingRate.SLOW, SpeakingRate.NORMAL]


@pytest.mark.unit
def test_narrate_mantra_defaults(monkeypatch):
    """``narrate_mantra`` defaults to Om Mani Padme Hum, 108 repetitions."""
    captured_kwargs = {}

    class _FakeNarrator:
        def __init__(self):
            pass

        def generate_mantra_audio(self, **kwargs):
            captured_kwargs.update(kwargs)
            return kwargs["output_file"]

    monkeypatch.setattr(ti, "TTSNarrator", _FakeNarrator)

    out = narrate_mantra()
    assert out == "mantra.mp3"
    assert captured_kwargs["mantra"] == "Om Mani Padme Hum"
    assert captured_kwargs["repetitions"] == 108
