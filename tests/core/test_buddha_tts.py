"""
Smoke + behaviour tests for ``core.buddha_tts``.

Covers the public surface:
- :class:`BuddhaTTSReciter` — constructor + ``available`` property + voice handling.
- ``recite_buddha_name`` — strips existing 南無 and re-prefixes it; returns path
  on success, ``None`` on failure / unavailable.
- ``recite_full_liturgy`` — filters structural lines, returns path on success.
- ``recite_with_timing`` — produces a summary dict with audio_files, total_recited,
  dedications, and total_buddhas_in_collection.

``edge_tts`` is the only heavy dependency and is not installed in the
test environment — so ``BuddhaTTSReciter.available`` is ``False`` in CI.
We assert that contract directly. The test that requires TTS success
forces ``_available=True`` and patches ``edge_tts`` in ``sys.modules``.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.buddha_tts import (
    ALT_VOICES,
    DEFAULT_VOICE,
    PREFERRED_VOICE,
    BuddhaTTSReciter,
)

# ---------------------------------------------------------------------------
# 1. Import smoke + module-level constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exports the reciter class and the voice constants."""
    import core.buddha_tts as mod

    for name in (
        "BuddhaTTSReciter",
        "DEFAULT_VOICE",
        "PREFERRED_VOICE",
        "ALT_VOICES",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"

    # Voice constants are non-empty strings
    assert isinstance(DEFAULT_VOICE, str) and DEFAULT_VOICE
    assert isinstance(PREFERRED_VOICE, str) and PREFERRED_VOICE
    assert isinstance(ALT_VOICES, list) and len(ALT_VOICES) > 0
    # All alt voices are Chinese / Taiwanese / Cantonese locales
    for v in ALT_VOICES:
        assert v.startswith(("zh-",))


# ---------------------------------------------------------------------------
# 2. BuddhaTTSReciter constructor — voice + availability probe
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reciter_constructor_uses_supplied_voice():
    """Voice is stored verbatim on the instance."""
    rec = BuddhaTTSReciter(voice="zh-CN-XiaoxiaoNeural")
    assert rec.voice == "zh-CN-XiaoxiaoNeural"


@pytest.mark.unit
def test_reciter_available_false_when_edge_tts_missing():
    """If edge_tts is not importable, ``available`` is False."""
    # Ensure edge_tts is not installed
    with patch.dict(sys.modules, {"edge_tts": None}):
        rec = BuddhaTTSReciter()
        assert rec.available is False


# ---------------------------------------------------------------------------
# 3. recite_buddha_name — strips existing 南無 and re-prefixes
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_recite_buddha_name_strips_and_reprefixes():
    """``recite_buddha_name`` removes any existing 南無 and re-adds it before TTS.

    The method does not accept an ``output_file`` kwarg — it returns the
    temp file path created by ``speak()`` instead. We assert against the
    path that was actually forwarded to ``Communicate.save``.
    """
    rec = BuddhaTTSReciter()
    rec._available = True  # force "available" without installing edge_tts

    # Patch edge_tts into sys.modules so the import inside ``speak`` works
    fake_edge = MagicMock(name="edge_tts")
    fake_communicate = MagicMock()
    fake_communicate.save = AsyncMock(return_value=None)
    fake_edge.Communicate = MagicMock(return_value=fake_communicate)

    captured = {}

    def capture(text, voice, rate=None, volume=None):
        captured["text"] = text
        captured["voice"] = voice
        captured["rate"] = rate
        return fake_communicate

    fake_edge.Communicate.side_effect = capture

    with patch.dict(sys.modules, {"edge_tts": fake_edge}):
        # Buddha name already starts with 南無
        result = await rec.recite_buddha_name("南無阿彌陀佛", "ámítuófó", rate="-30%")

    # The text sent to Communicate is "南無阿彌陀佛" (南無 preserved once, not doubled)
    assert captured["text"] == "南無阿彌陀佛"
    assert captured["voice"] == rec.voice
    # The returned path is the temp file that was forwarded to save
    assert result is not None
    assert result.endswith(".mp3")
    fake_communicate.save.assert_awaited_once()


@pytest.mark.unit
async def test_recite_buddha_name_returns_none_when_unavailable():
    """``recite_buddha_name`` returns None when the reciter is not available."""
    rec = BuddhaTTSReciter()
    rec._available = False
    assert await rec.recite_buddha_name("阿彌陀佛") is None


# ---------------------------------------------------------------------------
# 4. recite_full_liturgy — filters structural lines, returns path on success
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_recite_full_liturgy_filters_structural_lines():
    """Structural lines (Roman numerals, dashes) are stripped before TTS.

    ``recite_full_liturgy`` does not accept an ``output_file`` kwarg —
    it returns the temp-file path created by ``speak()``.
    """
    rec = BuddhaTTSReciter()
    rec._available = True

    fake_edge = MagicMock(name="edge_tts")
    fake_communicate = MagicMock()
    fake_communicate.save = AsyncMock(return_value=None)
    fake_edge.Communicate = MagicMock(return_value=fake_communicate)

    captured = {}

    def capture(text, voice, rate=None, volume=None):
        captured["text"] = text
        return fake_communicate

    fake_edge.Communicate.side_effect = capture

    liturgy = (
        "I. Opening\n"  # skipped: starts with "I."
        "─── header ───\n"  # skipped: starts with "─"
        "南無釋迦牟尼佛\n"  # kept
        "南無阿彌陀佛\n"  # kept
        "... and all\n"  # skipped: starts with "..."
        "V. Closing\n"  # skipped: starts with "V."
    )

    with patch.dict(sys.modules, {"edge_tts": fake_edge}):
        result = await rec.recite_full_liturgy(liturgy)

    # Returns a path to an mp3 file
    assert result is not None
    assert result.endswith(".mp3")
    # The text joined for TTS contains only the kept lines, joined with "。"
    assert "南無釋迦牟尼佛" in captured["text"]
    assert "南無阿彌陀佛" in captured["text"]
    # Structural markers are not present
    assert "I. Opening" not in captured["text"]
    assert "───" not in captured["text"]
    assert "V. Closing" not in captured["text"]


# ---------------------------------------------------------------------------
# 5. recite_with_timing — returns summary dict with expected keys
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_recite_with_timing_returns_summary_dict():
    """``recite_with_timing`` returns a dict with audio_files, total_recited, etc."""
    rec = BuddhaTTSReciter()
    rec._available = True

    fake_edge = MagicMock(name="edge_tts")
    fake_communicate = MagicMock()
    fake_communicate.save = AsyncMock(return_value=None)
    fake_edge.Communicate = MagicMock(return_value=fake_communicate)

    with patch.dict(sys.modules, {"edge_tts": fake_edge}):
        # 3 buddhas, mala_count=5 (less than 21 so no dedication fires)
        buddhas = [
            {"name_chinese": "南無佛一", "name_pinyin": "yī"},
            {"name_chinese": "南無佛二", "name_pinyin": "èr"},
            {"name_chinese": "南無佛三", "name_pinyin": "sān"},
        ]
        result = await rec.recite_with_timing(buddhas, mala_count=5)

    assert set(result.keys()) == {
        "audio_files",
        "total_recited",
        "dedications",
        "total_buddhas_in_collection",
    }
    assert result["total_buddhas_in_collection"] == 3
    assert result["total_recited"] == 5
    assert result["dedications"] == 0  # 5 < 21, no dedication triggered
    assert len(result["audio_files"]) == 5
    for entry in result["audio_files"]:
        assert entry["type"] == "buddha"
        assert "path" in entry
