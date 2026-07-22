"""Tests for ``core.qwen_tts`` — Qwen3-TTS engine wrapper and catalogs.

Covers the public surface:
- Module-level catalogs: :data:`QWEN_SPEAKERS`, :data:`QWEN_LANGUAGES`,
  :data:`RITUAL_SPEAKERS`, :data:`VOICE_DESIGN_PRESETS`.
- :class:`QwenTTSConfig` — defaults + ``to_dict`` round-trip.
- :class:`QwenTTSEngine` — public lookup methods + graceful degradation
  when the qwen_tts package / GPU is unavailable.
- :func:`get_qwen_tts` — process-wide singleton.

Heavy ML deps (``qwen_tts``, ``torch``, GPU) are NOT required; tests
assert graceful degradation (``available=False`` → ``speak()`` returns
``None``) which is the contract for CPU-only / package-missing systems.
"""

from __future__ import annotations

import pytest

from core.qwen_tts import (
    QWEN_LANGUAGES,
    QWEN_SPEAKERS,
    RITUAL_SPEAKERS,
    VOICE_DESIGN_PRESETS,
    QwenTTSConfig,
    QwenTTSEngine,
    get_qwen_tts,
)

# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols."""
    import core.qwen_tts as mod

    for name in (
        "QWEN_SPEAKERS",
        "QWEN_LANGUAGES",
        "RITUAL_SPEAKERS",
        "VOICE_DESIGN_PRESETS",
        "QwenTTSConfig",
        "QwenTTSEngine",
        "get_qwen_tts",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Module-level catalogs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_qwen_speakers_catalog_has_nine_speakers_with_required_fields():
    """``QWEN_SPEAKERS`` is a 9-entry dict of speakers with description/gender/age/native."""
    assert len(QWEN_SPEAKERS) == 9

    required_fields = {"description", "native", "gender", "age"}
    for name, info in QWEN_SPEAKERS.items():
        assert isinstance(name, str) and name, f"Bad speaker name: {name!r}"
        assert required_fields.issubset(info.keys()), (
            f"Speaker {name!r} missing fields: {required_fields - info.keys()}"
        )
        assert info["gender"] in {"male", "female"}
        assert info["age"] in {"young", "adult", "senior"}

    # Spot-check the key ritual speaker used by the recitation loop
    assert "Uncle_Fu" in QWEN_SPEAKERS
    assert QWEN_SPEAKERS["Uncle_Fu"]["gender"] == "male"


@pytest.mark.unit
def test_qwen_languages_catalog_has_ten_languages():
    """``QWEN_LANGUAGES`` is a 10-entry list including the expected major languages."""
    assert len(QWEN_LANGUAGES) == 10
    for required in ("Chinese", "English", "Japanese", "Korean"):
        assert required in QWEN_LANGUAGES


@pytest.mark.unit
def test_ritual_speakers_and_voice_design_presets_have_expected_shapes():
    """``RITUAL_SPEAKERS`` maps role→speaker; ``VOICE_DESIGN_PRESETS`` is a dict of presets."""
    # Every ritual role points at a speaker that actually exists in QWEN_SPEAKERS
    for role, speaker in RITUAL_SPEAKERS.items():
        assert speaker in QWEN_SPEAKERS, f"Ritual role {role!r} → unknown speaker {speaker!r}"

    # Every voice-design preset has instruct + language
    for name, preset in VOICE_DESIGN_PRESETS.items():
        assert "instruct" in preset and preset["instruct"], f"Preset {name!r} missing 'instruct'"
        assert "language" in preset, f"Preset {name!r} missing 'language'"


# ---------------------------------------------------------------------------
# 3. QwenTTSConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_qwen_tts_config_defaults_and_to_dict():
    """``QwenTTSConfig`` defaults + ``to_dict`` round-trip."""
    cfg = QwenTTSConfig()

    assert cfg.model_name == "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    assert cfg.device == "cuda:0"
    assert cfg.dtype == "bfloat16"
    assert cfg.use_flash_attention is False
    assert cfg.default_speaker == "Uncle_Fu"
    assert cfg.default_language == "Chinese"

    # to_dict must include every field
    d = cfg.to_dict()
    assert d == {
        "model_name": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "device": "cuda:0",
        "dtype": "bfloat16",
        "default_speaker": "Uncle_Fu",
        "default_language": "Chinese",
    }

    # Round-trip with a custom value
    custom = QwenTTSConfig(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", dtype="float16")
    assert custom.to_dict()["model_name"].endswith("1.7B-CustomVoice")
    assert custom.to_dict()["dtype"] == "float16"


# ---------------------------------------------------------------------------
# 4. QwenTTSEngine public lookup methods
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_qwen_tts_engine_public_lookup_methods_return_catalog_data():
    """Engine exposes the catalogs via dedicated methods, returning copies of the data."""
    engine = QwenTTSEngine()

    speakers = engine.get_supported_speakers()
    assert len(speakers) == len(QWEN_SPEAKERS)
    # Each entry is a dict with the 'id' key added
    for entry in speakers:
        assert "id" in entry
        assert entry["id"] in QWEN_SPEAKERS

    assert engine.get_supported_languages() == QWEN_LANGUAGES
    assert engine.get_ritual_speakers() == RITUAL_SPEAKERS
    assert engine.get_voice_design_presets() == VOICE_DESIGN_PRESETS

    # ``available`` is a boolean (False on systems without qwen_tts/torch)
    assert isinstance(engine.available, bool)


@pytest.mark.unit
def test_qwen_tts_engine_speak_returns_none_when_unavailable(monkeypatch):
    """``speak`` / ``design_voice`` / ``clone_voice`` all return None when the engine is unavailable."""
    engine = QwenTTSEngine()
    # Force the engine into the "unavailable" state without hitting real torch
    engine._available = False

    assert engine.speak("南無普光佛") is None
    assert engine.speak(["a", "b"]) is None
    assert engine.speak_batch(["x", "y"]) is None
    assert engine.design_voice("text", "instruct") is None
    assert engine.clone_voice("text", ref_audio="/dev/null") is None


# ---------------------------------------------------------------------------
# 5. get_qwen_tts singleton
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_qwen_tts_returns_singleton_instance():
    """``get_qwen_tts`` returns the same instance across calls (process-wide cache)."""
    import core.qwen_tts as mod

    mod._qwen_tts = None  # reset for determinism

    a = get_qwen_tts()
    b = get_qwen_tts()

    assert a is b
    assert isinstance(a, QwenTTSEngine)


@pytest.mark.unit
def test_get_qwen_tts_applies_supplied_config_to_existing_singleton():
    """Passing a non-None config to ``get_qwen_tts`` updates the existing singleton's config."""
    import core.qwen_tts as mod

    mod._qwen_tts = None  # reset

    engine = get_qwen_tts()
    original_model = engine.config.model_name

    custom_cfg = QwenTTSConfig(model_name="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
    engine2 = get_qwen_tts(custom_cfg)

    assert engine2 is engine
    assert engine.config.model_name == "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    assert engine.config.model_name != original_model
