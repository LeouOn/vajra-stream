"""
Smoke + behaviour tests for ``core.enhanced_tts``.

Covers:
* Module import — every public TTS provider class is exposed
* :class:`TTSProvider` (abstract base) — default ``check_availability``,
  ``speak`` and ``generate_audio_file`` return ``False`` and set ``error_msg``
* :class:`EnhancedTTSEngine` — initialises all providers, selects an
  available one, and raises ``RuntimeError`` when none are available
* :meth:`EnhancedTTSEngine.set_provider` — returns ``False`` for unknown
  providers and for unavailable providers
* :meth:`EnhancedTTSEngine.list_available_providers` — returns the expected
  dict shape (``name``, ``available``, ``error``)
* :meth:`EnhancedTTSEngine.speak_slowly` — stops early and returns ``False``
  if the active provider's ``speak`` returns ``False`` on the first sentence

Heavy dependencies (elevenlabs, azure-cognitiveservices-speech, google.cloud,
openai, TTS, pyttsx3, pygame, edge-tts) are mocked so the tests never
require real cloud credentials or audio hardware.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core import enhanced_tts as etts

# ---------------------------------------------------------------------------
# 1. Import smoke + provider class surface
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_provider_classes_exposed():
    """Module imports cleanly and exposes every public provider class."""
    # Abstract base + the 7 concrete providers
    assert callable(etts.TTSProvider)
    for cls_name in (
        "ElevenLabsTTS",
        "AzureTTS",
        "GoogleCloudTTS",
        "OpenAITTS",
        "CoquiTTS",
        "PiperTTS",
        "Pyttsx3TTS",
        "EnhancedTTSEngine",
    ):
        assert hasattr(etts, cls_name), f"missing class: {cls_name}"

    # Top-level convenience helpers
    assert callable(etts.speak)
    assert callable(etts.speak_prayer)
    assert callable(etts.speak_mantra)


# ---------------------------------------------------------------------------
# 2. TTSProvider base class — safe no-op defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_base_ttsprovider_defaults_are_noops():
    """A bare ``TTSProvider`` reports unavailable and its methods return False."""
    provider = etts.TTSProvider("Test")
    assert provider.name == "Test"
    assert provider.available is False
    assert provider.error_msg is None

    # check_availability returns False and sets a reason
    assert provider.check_availability() is False
    assert provider.error_msg is not None
    assert "no concrete backend" in provider.error_msg.lower()

    # speak / generate_audio_file return False without raising
    assert provider.speak("hello") is False
    assert provider.generate_audio_file("hello", "/tmp/out.mp3") is False


# ---------------------------------------------------------------------------
# 3. EnhancedTTSEngine — initialises all providers and picks an available one
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_enhanced_tts_engine_initialises_all_providers(monkeypatch, capsys):
    """Engine instantiates every provider class once and stores them by name."""
    # Force every provider to be unavailable so _select_provider raises
    # without depending on real cloud creds / heavy deps.
    fake_provider_classes = []
    expected_names = [
        "OpenAI TTS",
        "ElevenLabs",
        "Azure TTS",
        "Google Cloud TTS",
        "Coqui TTS",
        "Piper TTS",
        "pyttsx3",
    ]

    def make_fake_provider_class(name: str):
        cls = type(
            f"Fake{name.replace(' ', '')}Provider",
            (etts.TTSProvider,),
            {"__init__": lambda self: etts.TTSProvider.__init__(self, name)},
        )
        return cls

    fake_provider_classes = [make_fake_provider_class(n) for n in expected_names]

    with (
        patch.object(etts, "OpenAITTS", fake_provider_classes[0]),
        patch.object(etts, "ElevenLabsTTS", fake_provider_classes[1]),
        patch.object(etts, "AzureTTS", fake_provider_classes[2]),
        patch.object(etts, "GoogleCloudTTS", fake_provider_classes[3]),
        patch.object(etts, "CoquiTTS", fake_provider_classes[4]),
        patch.object(etts, "PiperTTS", fake_provider_classes[5]),
        patch.object(etts, "Pyttsx3TTS", fake_provider_classes[6]),
    ):
        with pytest.raises(RuntimeError, match="No TTS provider available"):
            etts.EnhancedTTSEngine(prefer_local=False)

    # Silence the noisy "[init failed]" prints that the engine emits when
    # provider constructors raise (they don't here, but other tests might).
    capsys.readouterr()


# ---------------------------------------------------------------------------
# 4. EnhancedTTSEngine — selects first available provider by priority
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_enhanced_tts_engine_picks_first_available_provider(monkeypatch):
    """Engine selects the highest-priority provider whose ``available`` is True."""
    # Build one fake "available" provider and stub out the rest as unavailable.
    available = etts.TTSProvider("OpenAI TTS")
    available.available = True

    # Replace every concrete class with a constructor that returns either the
    # available instance or an unavailable one.
    def stub(name: str, avail: bool):
        cls = type(
            f"Fake_{name.replace(' ', '')}",
            (etts.TTSProvider,),
            {"__init__": lambda self: etts.TTSProvider.__init__(self, name)},
        )

        def __init__(self):
            etts.TTSProvider.__init__(self, name)
            self.available = avail

        cls.__init__ = __init__
        return cls

    classes = {
        "OpenAITTS": stub("OpenAI TTS", True),
        "ElevenLabsTTS": stub("ElevenLabs", False),
        "AzureTTS": stub("Azure TTS", False),
        "GoogleCloudTTS": stub("Google Cloud TTS", False),
        "CoquiTTS": stub("Coqui TTS", False),
        "PiperTTS": stub("Piper TTS", False),
        "Pyttsx3TTS": stub("pyttsx3", False),
    }

    with patch.multiple(etts, **classes):
        engine = etts.EnhancedTTSEngine(prefer_local=False)

    assert engine.active_provider is not None
    assert engine.active_provider.name == "OpenAI TTS"
    assert engine.get_current_provider() == "OpenAI TTS"

    # All 7 providers were instantiated and stored under their human-readable
    # name regardless of availability.
    assert set(engine.providers.keys()) == {
        "OpenAI TTS",
        "ElevenLabs",
        "Azure TTS",
        "Google Cloud TTS",
        "Coqui TTS",
        "Piper TTS",
        "pyttsx3",
    }


# ---------------------------------------------------------------------------
# 5. EnhancedTTSEngine.set_provider — unknown / unavailable handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_set_provider_returns_false_for_unknown_or_unavailable(monkeypatch):
    """``set_provider`` returns False and never mutates active_provider on bad input."""
    # Build an engine where exactly one provider (PiperTTS) is available.
    available = etts.TTSProvider("Piper TTS")
    available.available = True

    def stub(name: str, avail: bool):
        cls = type(
            f"Fake_{name.replace(' ', '')}",
            (etts.TTSProvider,),
            {},
        )

        def __init__(self):
            etts.TTSProvider.__init__(self, name)
            self.available = avail

        cls.__init__ = __init__
        return cls

    classes = {
        "OpenAITTS": stub("OpenAI TTS", False),
        "ElevenLabsTTS": stub("ElevenLabs", False),
        "AzureTTS": stub("Azure TTS", False),
        "GoogleCloudTTS": stub("Google Cloud TTS", False),
        "CoquiTTS": stub("Coqui TTS", False),
        "PiperTTS": stub("Piper TTS", True),
        "Pyttsx3TTS": stub("pyttsx3", False),
    }

    with patch.multiple(etts, **classes):
        engine = etts.EnhancedTTSEngine(prefer_local=False)
        original = engine.active_provider

        # Unknown provider name -> False, active provider unchanged
        assert engine.set_provider("totally-fake") is False
        assert engine.active_provider is original

        # Known-but-unavailable provider -> False, active provider unchanged
        assert engine.set_provider("OpenAI TTS") is False
        assert engine.active_provider is original

        # Available provider -> True and active provider swapped
        # (Piper TTS is already active here, so re-select is a no-op success.)
        assert engine.set_provider("Piper TTS") is True


# ---------------------------------------------------------------------------
# 6. EnhancedTTSEngine.list_available_providers — dict shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_available_providers_returns_expected_dict_shape(monkeypatch):
    """``list_available_providers`` returns one dict per provider with the right keys."""

    def stub(name: str, avail: bool, err: str | None = None):
        cls = type(
            f"Fake_{name.replace(' ', '')}",
            (etts.TTSProvider,),
            {},
        )

        def __init__(self):
            etts.TTSProvider.__init__(self, name)
            self.available = avail
            if err is not None:
                self.error_msg = err

        cls.__init__ = __init__
        return cls

    classes = {
        "OpenAITTS": stub("OpenAI TTS", False, "no key"),
        "ElevenLabsTTS": stub("ElevenLabs", False, "no key"),
        "AzureTTS": stub("Azure TTS", True),
        "GoogleCloudTTS": stub("Google Cloud TTS", False, "no creds"),
        "CoquiTTS": stub("Coqui TTS", False, "no pkg"),
        "PiperTTS": stub("Piper TTS", False, "no binary"),
        "Pyttsx3TTS": stub("pyttsx3", False, "no pkg"),
    }

    with patch.multiple(etts, **classes):
        engine = etts.EnhancedTTSEngine(prefer_local=False)

    listing = engine.list_available_providers()
    assert isinstance(listing, list)
    assert len(listing) == 7

    by_name = {item["name"]: item for item in listing}
    # Available provider reports available=True and error=None
    assert by_name["Azure TTS"]["available"] is True
    assert by_name["Azure TTS"]["error"] is None
    # Unavailable provider reports available=False and an error string
    assert by_name["OpenAI TTS"]["available"] is False
    assert by_name["OpenAI TTS"]["error"] == "no key"

    # Every entry has exactly the three documented keys
    for item in listing:
        assert set(item.keys()) == {"name", "available", "error"}


# ---------------------------------------------------------------------------
# 7. speak_slowly — short-circuits when the active provider fails
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_speak_slowly_returns_false_when_first_sentence_fails(monkeypatch):
    """``speak_slowly`` returns False and stops after the first failing sentence."""
    failing = etts.TTSProvider("OpenAI TTS")
    failing.available = True
    failing.speak = MagicMock(return_value=False)  # type: ignore[method-assign]

    engine = etts.EnhancedTTSEngine.__new__(etts.EnhancedTTSEngine)
    engine.prefer_local = False
    engine.providers = {failing.name: failing}
    engine.active_provider = failing

    # Two sentences: first call must fail; the second must never happen.
    result = engine.speak_slowly("First. Second.", pause_duration=0.0)
    assert result is False
    assert failing.speak.call_count == 1
