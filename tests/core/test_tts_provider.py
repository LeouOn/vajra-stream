"""
Smoke + behaviour tests for ``core.tts_provider``.

Covers:

* Module import + top-level exports
* Module-level :data:`RITUAL_ROLE_SPEAKERS` (shape + content)
* :func:`set_project_speaker`, :func:`get_project_speaker`,
  :func:`clear_project_speakers`, :func:`list_project_overrides`
* :class:`TTSConfig` — defaults, ``to_dict()``, ``resolve_speaker()``
* :class:`TTSProvider` — ``active_backend``, ``capabilities``,
  ``set_backend``, ``set_config``
* :meth:`TTSProvider.speak` (async, mocked edge_tts)
* :meth:`TTSProvider.speak_batch` (async, mocked edge_tts)
* :func:`get_tts_provider` — singleton behaviour
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core import tts_provider as tp
from core.tts_provider import (
    RITUAL_ROLE_SPEAKERS,
    TTSBackend,
    TTSConfig,
    TTSProvider,
    clear_project_speakers,
    get_project_speaker,
    get_tts_provider,
    list_project_overrides,
    set_project_speaker,
)

# ---------------------------------------------------------------------------
# 1. Import smoke + module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """Module imports cleanly; enum + role table + helpers are exposed."""
    # TTSBackend enum
    assert TTSBackend.EDGE.value == "edge"
    assert TTSBackend.QWEN.value == "qwen"
    assert TTSBackend.AUTO.value == "auto"

    # RITUAL_ROLE_SPEAKERS contains both backends
    assert "qwen" in RITUAL_ROLE_SPEAKERS
    assert "edge" in RITUAL_ROLE_SPEAKERS
    # A few well-known roles
    for backend in ("qwen", "edge"):
        assert "buddhist_chant" in RITUAL_ROLE_SPEAKERS[backend]
        assert "compassionate" in RITUAL_ROLE_SPEAKERS[backend]

    # Module-level helpers
    assert callable(set_project_speaker)
    assert callable(get_project_speaker)
    assert callable(clear_project_speakers)
    assert callable(list_project_overrides)
    assert callable(get_tts_provider)


# ---------------------------------------------------------------------------
# 2. Project speaker overrides
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_set_and_get_project_speaker():
    """``set_project_speaker`` overrides the global default for one project."""
    set_project_speaker("proj-x", "compassionate", "CustomVoice")
    try:
        speaker = get_project_speaker("proj-x", "compassionate", TTSBackend.QWEN)
        assert speaker == "CustomVoice"
        # A different project still gets the global default
        other = get_project_speaker("proj-y", "compassionate", TTSBackend.QWEN)
        assert other != "CustomVoice"
        # A different role in the same project keeps the global default
        other_role = get_project_speaker("proj-x", "dharma_teaching", TTSBackend.QWEN)
        assert other_role != "CustomVoice"
    finally:
        clear_project_speakers("proj-x")


@pytest.mark.unit
def test_get_project_speaker_ignores_empty_inputs():
    """Empty strings are ignored by ``set_project_speaker`` (no override created)."""
    clear_project_speakers("empty-proj")
    set_project_speaker("", "compassionate", "x")
    set_project_speaker("empty-proj", "", "x")
    set_project_speaker("empty-proj", "compassionate", "")
    # The inner dict is empty (no roles were actually set for this project)
    assert list_project_overrides("empty-proj") == {"empty-proj": {}}


@pytest.mark.unit
def test_get_project_speaker_backend_fallback():
    """Unknown backend roles fall back to the canonical default per backend."""
    qwen_default = get_project_speaker(None, "no-such-role", TTSBackend.QWEN)
    assert qwen_default == "Uncle_Fu"
    edge_default = get_project_speaker(None, "no-such-role", TTSBackend.EDGE)
    assert edge_default == "zh-CN-YunxiNeural"


@pytest.mark.unit
def test_clear_project_speakers_removes_all():
    """``clear_project_speakers`` removes all roles for a given project."""
    set_project_speaker("clear-me", "r1", "v1")
    set_project_speaker("clear-me", "r2", "v2")
    assert "r1" in list_project_overrides("clear-me")["clear-me"]
    assert "r2" in list_project_overrides("clear-me")["clear-me"]
    clear_project_speakers("clear-me")
    # After clearing, the project has no role overrides
    assert list_project_overrides("clear-me") == {"clear-me": {}}


# ---------------------------------------------------------------------------
# 3. TTSConfig — defaults, to_dict, resolve_speaker
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ttsconfig_defaults_and_to_dict():
    """``TTSConfig`` has sensible defaults and ``to_dict`` is JSON-safe."""
    cfg = TTSConfig()
    assert cfg.backend == TTSBackend.AUTO
    assert cfg.edge_voice == "zh-CN-YunxiNeural"
    assert cfg.qwen_speaker == "Uncle_Fu"
    assert cfg.qwen_language == "Chinese"
    assert cfg.role is None
    assert cfg.project_id is None

    d = cfg.to_dict()
    assert d["backend"] == "auto"
    assert d["edge_voice"] == "zh-CN-YunxiNeural"
    assert d["qwen_speaker"] == "Uncle_Fu"
    assert d["qwen_language"] == "Chinese"
    # to_dict output contains only JSON-safe types
    for value in d.values():
        assert isinstance(value, str | type(None))


@pytest.mark.unit
def test_ttsconfig_resolve_speaker_with_and_without_role():
    """``resolve_speaker`` returns the role-mapped voices when a role is given."""
    cfg = TTSConfig(role="compassionate")
    edge_v, qwen_s = cfg.resolve_speaker()
    assert edge_v == RITUAL_ROLE_SPEAKERS["edge"]["compassionate"]
    assert qwen_s == RITUAL_ROLE_SPEAKERS["qwen"]["compassionate"]

    # Without role → config defaults are returned
    cfg2 = TTSConfig()
    edge_v, qwen_s = cfg2.resolve_speaker()
    assert edge_v == cfg2.edge_voice
    assert qwen_s == cfg2.qwen_speaker

    # Argument role overrides config role
    edge_v, qwen_s = cfg.resolve_speaker(role="buddhist_chant")
    assert edge_v == RITUAL_ROLE_SPEAKERS["edge"]["buddhist_chant"]


# ---------------------------------------------------------------------------
# 4. TTSProvider — active_backend + capabilities
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ttsprovider_active_backend_explicit():
    """Explicit backend (not AUTO) is returned as-is."""
    p_edge = TTSProvider(config=TTSConfig(backend=TTSBackend.EDGE))
    assert p_edge.active_backend == TTSBackend.EDGE

    p_qwen = TTSProvider(config=TTSConfig(backend=TTSBackend.QWEN))
    assert p_qwen.active_backend == TTSBackend.QWEN


@pytest.mark.unit
def test_ttsprovider_active_backend_auto_falls_back_to_edge():
    """AUTO without a working Qwen engine resolves to EDGE."""
    p = TTSProvider(config=TTSConfig(backend=TTSBackend.AUTO))
    # Force _get_qwen to return None (simulates "no Qwen")
    p._qwen_engine = False  # The module's sentinel for "not available"
    assert p.active_backend == TTSBackend.EDGE


@pytest.mark.unit
def test_ttsprovider_capabilities_edge():
    """Capabilities for EDGE backend lists the EDGE voice catalog and no streaming."""
    p = TTSProvider(config=TTSConfig(backend=TTSBackend.EDGE))
    caps = p.capabilities
    assert caps["backend"] == "edge"
    assert caps["streaming"] is False
    assert caps["voice_design"] is False
    assert caps["voice_clone"] is False
    assert "Chinese" in caps["languages"]
    # EDGE_VOICES is exposed
    assert any(s["id"] == "zh-CN-YunxiNeural" for s in caps["speakers"])


@pytest.mark.unit
def test_ttsprovider_set_backend_and_config():
    """``set_backend`` and ``set_config`` mutate the live config."""
    p = TTSProvider()
    p.set_backend("qwen")
    assert p.config.backend == TTSBackend.QWEN

    p.set_config(edge_voice="en-US-AriaNeural", edge_rate="+10%")
    assert p.config.edge_voice == "en-US-AriaNeural"
    assert p.config.edge_rate == "+10%"

    # Unknown attribute is silently ignored (no exception)
    p.set_config(this_does_not_exist="x")
    assert not hasattr(p.config, "this_does_not_exist")


# ---------------------------------------------------------------------------
# 5. TTSProvider.speak — async, mocked edge_tts
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ttsprovider_speak_edge_returns_output_path(tmp_path, monkeypatch):
    """``speak`` on the EDGE backend delegates to ``edge_tts.Communicate``."""
    # Force the EDGE backend
    p = TTSProvider(config=TTSConfig(backend=TTSBackend.EDGE))
    out_file = str(tmp_path / "speech.mp3")

    fake_communicate = MagicMock()
    fake_communicate.save = AsyncMock(return_value=None)
    fake_module = MagicMock()
    fake_module.Communicate = MagicMock(return_value=fake_communicate)

    with patch.dict("sys.modules", {"edge_tts": fake_module}):
        result = await p.speak(text="南無阿彌陀佛", output_file=out_file)

    assert result == out_file
    fake_module.Communicate.assert_called_once()
    # The voice and rate were passed from config
    call_kwargs = fake_module.Communicate.call_args.kwargs
    assert call_kwargs["rate"] == p.config.edge_rate
    assert call_kwargs["rate"] == "-25%"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ttsprovider_speak_returns_none_when_edge_tts_missing():
    """``speak`` returns ``None`` when edge_tts is not importable."""
    p = TTSProvider(config=TTSConfig(backend=TTSBackend.EDGE))

    # Force the inner import to fail by hiding edge_tts
    with patch.dict("sys.modules", {"edge_tts": None}):
        result = await p.speak(text="hello")

    assert result is None


# ---------------------------------------------------------------------------
# 6. TTSProvider.speak_batch — async
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ttsprovider_speak_batch_edge_calls_per_text(tmp_path, monkeypatch):
    """``speak_batch`` on EDGE sequentially calls speak for each text."""
    p = TTSProvider(config=TTSConfig(backend=TTSBackend.EDGE))

    fake_communicate = MagicMock()
    fake_communicate.save = AsyncMock(return_value=None)
    fake_module = MagicMock()
    fake_module.Communicate = MagicMock(return_value=fake_communicate)

    with patch.dict("sys.modules", {"edge_tts": fake_module}):
        paths = await p.speak_batch(texts=["a", "b", "c"])

    # 3 distinct outputs (1 per text)
    assert isinstance(paths, list)
    assert len(paths) == 3
    # edge_tts.Communicate called once per text
    assert fake_module.Communicate.call_count == 3
    # Each path is a string
    for path in paths:
        assert isinstance(path, str)


# ---------------------------------------------------------------------------
# 7. TTSProvider.speak — explicit voice overrides role-based resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ttsprovider_speak_explicit_voice_bypasses_role(monkeypatch):
    """An explicit ``voice=`` argument bypasses the role-based speaker map."""
    p = TTSProvider(config=TTSConfig(backend=TTSBackend.EDGE, role="compassionate"))

    fake_communicate = MagicMock()
    fake_communicate.save = AsyncMock(return_value=None)
    fake_module = MagicMock()
    fake_module.Communicate = MagicMock(return_value=fake_communicate)

    with patch.dict("sys.modules", {"edge_tts": fake_module}):
        await p.speak(text="hi", voice="en-US-GuyNeural")

    # The voice was forwarded verbatim, not the role's mapped voice
    args, kwargs = fake_module.Communicate.call_args
    assert args[1] == "en-US-GuyNeural"  # voice positional arg


# ---------------------------------------------------------------------------
# 8. get_tts_provider — singleton
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_tts_provider_returns_singleton():
    """``get_tts_provider`` returns the same instance on repeated calls."""
    # Reset the module-level singleton to exercise the lazy-init path
    tp._tts_provider = None
    a = get_tts_provider()
    b = get_tts_provider()
    assert a is b
    assert isinstance(a, TTSProvider)
    # Cleanup
    tp._tts_provider = None
