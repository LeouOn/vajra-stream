# Piper TTS Local Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Piper TTS as a third local, CPU-only, offline-capable TTS backend in the Vajra.Stream TTS provider, alongside the existing Edge (cloud) and Qwen (GPU) backends.

**Architecture:** A new `core/piper_tts.py` engine wraps the `piper-tts` PyPI package (v1.5.0, ONNX-runtime-based). It plugs into the existing `core/tts_provider.py:TTSProvider` via a new `TTSBackend.PIPER` enum value, following the exact same lazy-load + speak/speak_stream pattern as the Qwen path. The frontend `TTSSettingsPanel.tsx` gets a new "🔊 Piper" backend option.

**Tech Stack:** `piper-tts>=1.5.0` (GPL-3.0-or-later, ONNX runtime, bundles espeak-ng), `onnxruntime>=1.27.0` (already resolves on Python 3.14), `pathvalidate>=3.3.1`.

## Global Constraints

- **Python**: 3.14.0 in the active `.venv` — Piper's `cp39-abi3` wheel is forward-compatible.
- **CPU-only**: AMD Ryzen 7 PRO 7840U, 8 cores. No CUDA. Piper uses ONNX Runtime CPU.
- **License**: Piper is **GPL-3.0-or-later**. Vajra.Stream is MIT. This is acceptable for personal/open-source use. If the project ever goes closed-source, swap to Kokoro (Apache-2.0) — but Kokoro requires Python <3.14 and ~2.5 GB deps.
- **No new AudioService class** (per ADR 001): Piper slots into `TTSProvider`, NOT a separate service.
- **Voice model**: `en_US-lessac-medium` (~60 MB ONNX file) as default. Downloaded from HuggingFace on first use or manually via `python -m piper.download_voices`.
- **Audio format**: Piper outputs WAV (PCM 16-bit, 22050 Hz). Same MIME type as Qwen path (`audio/wav`).
- **Model storage**: Voice `.onnx` + `.onnx.json` files in `models/piper/voices/` directory (created if missing).

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `core/piper_tts.py` | `PiperTTSEngine` class: lazy-loads Piper voice models, provides `speak(text) → (wav_bytes, sample_rate)` API. Mirrors `core/qwen_tts.py:QwenTTSEngine` interface. |
| `tests/core/test_piper_tts.py` | Unit tests for `PiperTTSEngine` (mocked ONNX runtime — no model download needed). |
| `scripts/download_piper_voices.py` | CLI helper to download voice models from HuggingFace. |

### Modified files

| File | Change |
|---|---|
| `core/tts_provider.py` | Add `TTSBackend.PIPER`, `_get_piper()` lazy loader, `_speak_piper()`, branch in `speak()` / `speak_stream()` / `speak_batch()`, update `active_backend` / `capabilities` / `get_available_configs`. |
| `requirements.txt` | Add `piper-tts>=1.5.0`. |
| `backend/requirements.txt` | Add `piper-tts>=1.5.0`. |
| `pyproject.toml` | Add `piper-tts>=1.5.0` to `[project.optional-dependencies] audio`. |
| `frontend/src/components/UI/TTSSettingsPanel.tsx` | Add `'piper'` to `Backend` type, new Select option, voice list rendering. |

---

## Task 1: Install Piper and Download Default Voice

**Files:**
- Modify: `requirements.txt:12` (after `edge-tts>=6.1.9`)
- Modify: `backend/requirements.txt:41` (after `edge-tts>=6.1.0`)
- Modify: `pyproject.toml:42` (in `audio` extra list)
- Create: `models/piper/voices/.gitkeep`
- Create: `scripts/download_piper_voices.py`

**Interfaces:**
- Produces: `piper-tts` importable in the venv; voice model at `models/piper/voices/en_US-lessac-medium.onnx`

- [ ] **Step 1: Install piper-tts into the venv**

```bash
cd C:\Users\llama\OneDrive\proj\vajra-stream
.venv\Scripts\pip.exe install piper-tts>=1.5.0
```

Expected output: `Successfully installed onnxruntime-1.27.0 pathvalidate-3.3.1 piper-tts-1.5.0 protobuf-7.35.1`

- [ ] **Step 2: Add piper-tts to requirements files**

Add to `requirements.txt` after line 12 (`edge-tts>=6.1.9`):
```
piper-tts>=1.5.0  # Local CPU TTS — ONNX runtime, offline, no GPU
```

Add to `backend/requirements.txt` after line 41 (`edge-tts>=6.1.0`):
```
piper-tts>=1.5.0  # Local CPU TTS — offline neural synthesis
```

Add to `pyproject.toml` in the `audio` extra (after `pyttsx3>=2.90`):
```toml
    "piper-tts>=1.5.0",
```

- [ ] **Step 3: Create the voice models directory**

```bash
mkdir -p models\piper\voices
echo. > models\piper\voices\.gitkeep
```

- [ ] **Step 4: Create the voice download script**

Create `scripts/download_piper_voices.py`:
```python
#!/usr/bin/env python3
"""Download Piper voice models from HuggingFace.

Usage:
    python scripts/download_piper_voices.py
    python scripts/download_piper_voices.py --voice en_US-lessac-medium
    python scripts/download_piper_voices.py --voice zh_CN-huayan-medium
"""
import argparse
import sys
import urllib.request
from pathlib import Path

VOICE_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
DEFAULT_VOICES = [
    "en_US/en_US-lessac/medium/en_US-lessac-medium.onnx",
    "en_US/en_US-lessac/medium/en_US-lessac-medium.onnx.json",
]
VOICE_DIR = Path(__file__).parent.parent / "models" / "piper" / "voices"


def download_voice(voice_path: str) -> None:
    url = f"{VOICE_BASE_URL}/{voice_path}"
    dest = VOICE_DIR / Path(voice_path).name
    if dest.exists():
        print(f"  [SKIP] {dest.name} already exists ({dest.stat().st_size // 1024} KB)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [GET]  {dest.name} from {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"  [OK]   {dest.name} ({dest.stat().st_size // 1024} KB)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Piper voice models")
    parser.add_argument(
        "--voice", default=None,
        help="Specific voice to download (e.g. en_US-lessac-medium). Downloads defaults if omitted.",
    )
    args = parser.parse_args()

    if args.voice:
        voice_name = args.voice
        lang = voice_name.split("-")[0]  # e.g. "en_US"
        quality = voice_name.split("-")[-1]  # e.g. "medium"
        base = voice_name.rsplit("-", 1)[0]  # e.g. "en_US-lessac"
        paths = [
            f"{lang}/{base}/{quality}/{voice_name}.onnx",
            f"{lang}/{base}/{quality}/{voice_name}.onnx.json",
        ]
    else:
        paths = DEFAULT_VOICES

    print(f"Downloading to {VOICE_DIR}")
    for p in paths:
        download_voice(p)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Download the default voice model**

```bash
cd C:\Users\llama\OneDrive\proj\vajra-stream
.venv\Scripts\python.exe scripts\download_piper_voices.py
```

Expected: `en_US-lessac-medium.onnx` (~60 MB) and `en_US-lessac-medium.onnx.json` appear in `models/piper/voices/`.

- [ ] **Step 6: Verify the Piper Python API works**

```bash
.venv\Scripts\python.exe -c "from piper import PiperVoice; v = PiperVoice.load('models/piper/voices/en_US-lessac-medium.onnx'); import wave; v.synthesize_wav('Hello from Piper.', wave.open('test_piper.wav', 'wb')); print('OK')"
```

Expected: `OK` and a `test_piper.wav` file (~50-100 KB) appears.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt backend/requirements.txt pyproject.toml scripts/download_piper_voices.py models/piper/voices/.gitkeep
git commit -m "feat(tts): add piper-tts dependency and voice download script"
```

---

## Task 2: Create PiperTTSEngine (core/piper_tts.py)

**Files:**
- Create: `core/piper_tts.py`
- Test: `tests/core/test_piper_tts.py`

**Interfaces:**
- Produces: `PiperTTSEngine` class with:
  - `__init__(self, voice_path: str = "models/piper/voices/en_US-lessac-medium.onnx")`
  - `available: bool` property — True if Piper package installed and voice file exists
  - `speak(self, text: str) -> tuple[bytes, int] | None` — returns `(wav_pcm16_bytes, sample_rate)`, or None on failure
  - `PIPER_VOICES: dict[str, dict]` — catalog of known voice IDs for the frontend

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_piper_tts.py`:
```python
"""Tests for PiperTTSEngine — the local CPU-only TTS backend."""
import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PIPER_INSTALLED = importlib.util.find_spec("piper") is not None


@pytest.fixture
def mock_voice_file(tmp_path):
    """Create a fake .onnx file so the path-exists check passes."""
    voice = tmp_path / "test_voice.onnx"
    voice.write_bytes(b"fake onnx data")
    return str(voice)


@pytest.fixture
def engine(mock_voice_file):
    """Create a PiperTTSEngine with a mocked PiperVoice."""
    from core.piper_tts import PiperTTSEngine
    return PiperTTSEngine(voice_path=mock_voice_file)


class TestPiperTTSEngineAvailability:
    def test_available_returns_true_when_piper_importable_and_voice_exists(self, engine):
        assert engine.available is True

    def test_available_returns_false_when_voice_file_missing(self):
        from core.piper_tts import PiperTTSEngine
        eng = PiperTTSEngine(voice_path="/nonexistent/voice.onnx")
        assert eng.available is False


class TestPiperTTSEngineSpeak:
    def test_speak_returns_wav_bytes_and_sample_rate(self, engine):
        # The mocked PiperVoice.synthesize_wav writes to a wav file.
        # We mock it to produce a known 44-byte WAV header + 4 bytes of silence.
        import wave
        import struct

        def fake_synthesize(text, wav_file):
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(struct.pack("<h", 0))

        with patch.object(engine, "_voice") as mock_v:
            mock_v.synthesize_wav.side_effect = fake_synthesize
            result = engine.speak("hello")
        assert result is not None
        wav_bytes, sr = result
        assert isinstance(wav_bytes, bytes)
        assert len(wav_bytes) > 0
        assert sr == 22050

    def test_speak_returns_none_on_empty_text(self, engine):
        result = engine.speak("")
        assert result is None

    def test_speak_returns_none_on_failure(self, engine):
        with patch.object(engine, "_voice") as mock_v:
            mock_v.synthesize_wav.side_effect = RuntimeError("ONNX crashed")
            result = engine.speak("hello")
        assert result is None


class TestPiperVoiceCatalog:
    def test_PIPER_VOICES_dict_is_non_empty(self):
        from core.piper_tts import PIPER_VOICES
        assert len(PIPER_VOICES) >= 1

    def test_PIPER_VOICES_has_en_US_lessac_medium(self):
        from core.piper_tts import PIPER_VOICES
        assert "en_US-lessac-medium" in PIPER_VOICES
        info = PIPER_VOICES["en_US-lessac-medium"]
        assert "description" in info
        assert "language" in info
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:\Users\llama\OneDrive\proj\vajra-stream
.venv\Scripts\python.exe -m pytest tests/core/test_piper_tts.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.piper_tts'`

- [ ] **Step 3: Write minimal implementation**

Create `core/piper_tts.py`:
```python
"""
PiperTTSEngine — local CPU-only TTS using the piper-tts PyPI package.

Wraps the ONNX-runtime-based Piper neural TTS engine. No GPU required.
Downloads voice models from HuggingFace (rhasspy/piper-voices).

Usage:
    engine = PiperTTSEngine()
    if engine.available:
        wav_bytes, sample_rate = engine.speak("Hello world")
"""
import io
import logging
import os
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_VOICE_PATH = os.path.join("models", "piper", "voices", "en_US-lessac-medium.onnx")

PIPER_VOICES: dict[str, dict[str, str]] = {
    "en_US-lessac-medium": {
        "description": "English (US) female, clear and natural — good default",
        "language": "English",
        "gender": "female",
        "quality": "medium",
    },
    "en_US-amy-medium": {
        "description": "English (US) female, warm",
        "language": "English",
        "gender": "female",
        "quality": "medium",
    },
    "en_GB-alba-medium": {
        "description": "English (UK) female, gentle",
        "language": "English",
        "gender": "female",
        "quality": "medium",
    },
    "zh_CN-huayan-medium": {
        "description": "Mandarin Chinese, neutral — for sutra recitation",
        "language": "Chinese",
        "gender": "neutral",
        "quality": "medium",
    },
}


class PiperTTSEngine:
    """Local CPU TTS via the piper-tts ONNX runtime."""

    def __init__(self, voice_path: str = DEFAULT_VOICE_PATH):
        self.voice_path = voice_path
        self._voice = None
        self._loaded = False

    @property
    def available(self) -> bool:
        """True if piper-tts is installed AND the voice file exists."""
        try:
            import piper  # noqa: F401
        except ImportError:
            return False
        return os.path.isfile(self.voice_path)

    def _ensure_loaded(self) -> bool:
        """Lazy-load the ONNX voice model."""
        if self._loaded:
            return self._voice is not None
        self._loaded = True
        if not self.available:
            return False
        try:
            from piper import PiperVoice

            self._voice = PiperVoice.load(self.voice_path)
            logger.info(f"Piper voice loaded: {self.voice_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load Piper voice: {e}")
            self._voice = None
            return False

    def speak(self, text: str) -> tuple[bytes, int] | None:
        """Synthesize text to WAV bytes.

        Returns (wav_pcm16_bytes, sample_rate) or None on failure.
        """
        if not text.strip():
            return None
        if not self._ensure_loaded() or self._voice is None:
            return None
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                self._voice.synthesize_wav(text, wf)
            wav_bytes = buf.getvalue()
            return wav_bytes, 22050
        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv\Scripts\python.exe -m pytest tests/core/test_piper_tts.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/piper_tts.py tests/core/test_piper_tts.py
git commit -m "feat(tts): add PiperTTSEngine for local CPU-only TTS synthesis"
```

---

## Task 3: Wire Piper into TTSProvider

**Files:**
- Modify: `core/tts_provider.py` (lines 37-40 enum, 187-203 active_backend, 206-228 capabilities, 230-286 get_available_configs, 290-305 _get_qwen pattern, 326-357 speak, 359-443 speak_stream, 445-469 speak_batch)
- Test: `tests/core/test_tts_provider.py` (add Piper-specific tests)

**Interfaces:**
- Consumes: `core.piper_tts.PiperTTSEngine` with `available` property and `speak(text) -> (bytes, int) | None`
- Produces: `TTSBackend.PIPER` enum value; `TTSProvider.speak()` routes to Piper when `config.backend == "piper"` or when AUTO and neither Qwen nor Edge is desired

- [ ] **Step 1: Write failing test for PIPER backend routing**

Add to `tests/core/test_tts_provider.py`:
```python
class TestPiperBackend:
    """Tests for the Piper local TTS backend."""

    def test_piper_backend_enum_exists(self):
        from core.tts_provider import TTSBackend
        assert hasattr(TTSBackend, "PIPER")
        assert TTSBackend.PIPER.value == "piper"

    def test_piper_config_field_exists(self):
        from core.tts_provider import TTSConfig
        config = TTSConfig()
        assert hasattr(config, "piper_voice")
        assert config.piper_voice == "en_US-lessac-medium"

    def test_piper_in_get_available_configs(self):
        from core.tts_provider import TTSProvider
        provider = TTSProvider()
        configs = provider.get_available_configs()
        assert "piper" in configs["backends"]

    def test_piper_auto_fallback_when_no_gpu_and_piper_available(self):
        """AUTO should prefer Qwen (GPU) > Piper (local CPU) > Edge (cloud)."""
        from core.tts_provider import TTSBackend, TTSConfig, TTSProvider
        provider = TTSProvider()
        provider.config = TTSConfig(backend=TTSBackend.AUTO)
        # If Piper is available and Qwen is not, AUTO should resolve to PIPER
        with patch.object(provider, "_get_qwen", return_value=None):
            with patch.object(provider, "_get_piper") as mock_piper:
                mock_engine = MagicMock()
                mock_engine.available = True
                mock_piper.return_value = mock_engine
                assert provider.active_backend == TTSBackend.PIPER
```

Also add the import at the top of the test file:
```python
from unittest.mock import MagicMock, patch
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv\Scripts\python.exe -m pytest tests/core/test_tts_provider.py::TestPiperBackend -v
```

Expected: FAIL with `AttributeError: TTSBackend has no attribute 'PIPER'`

- [ ] **Step 3: Add PIPER to TTSBackend enum**

In `core/tts_provider.py` line 37-40, change:
```python
class TTSBackend(str, Enum):
    EDGE = "edge"
    QWEN = "qwen"
    AUTO = "auto"  # Qwen if GPU available, else Edge
```
to:
```python
class TTSBackend(str, Enum):
    EDGE = "edge"
    QWEN = "qwen"
    PIPER = "piper"
    AUTO = "auto"  # Qwen if GPU, else Piper if installed, else Edge
```

- [ ] **Step 4: Add piper_voice to TTSConfig**

In `core/tts_provider.py`, add after line 120 (`qwen_language: str = "Chinese"`):
```python
    piper_voice: str = "en_US-lessac-medium"
```

Update `to_dict()` (around line 127-137) to include:
```python
            "piper_voice": self.piper_voice,
```

- [ ] **Step 5: Add Piper to RITUAL_ROLE_SPEAKERS**

In `core/tts_provider.py`, after the `"edge": { ... }` block (line 55-63), add:
```python
    "piper": {
        "buddhist_chant": "zh_CN-huayan-medium",
        "compassionate": "en_US-lessac-medium",
        "meditation_guide": "en_US-lessac-medium",
        "dharma_teaching": "en_US-amy-medium",
        "english_blessing": "en_US-amy-medium",
        "outlook_narrative": "en_US-lessac-medium",
        "outlook_epic": "en_US-amy-medium",
    },
```

- [ ] **Step 6: Update active_backend property**

In `core/tts_provider.py` (around line 193-203), change:
```python
    @property
    def active_backend(self) -> TTSBackend:
        """Resolve 'auto' to actual available backend."""
        if self.config.backend != TTSBackend.AUTO:
            return self.config.backend

        # Auto: prefer Qwen if GPU available
        qwen = self._get_qwen()
        if qwen and qwen.available:
            return TTSBackend.QWEN
        return TTSBackend.EDGE
```
to:
```python
    @property
    def active_backend(self) -> TTSBackend:
        """Resolve 'auto' to actual available backend."""
        if self.config.backend != TTSBackend.AUTO:
            return self.config.backend

        # Auto: prefer Qwen (GPU) > Piper (local CPU) > Edge (cloud)
        qwen = self._get_qwen()
        if qwen and qwen.available:
            return TTSBackend.QWEN
        piper = self._get_piper()
        if piper and piper.available:
            return TTSBackend.PIPER
        return TTSBackend.EDGE
```

- [ ] **Step 7: Add _get_piper() lazy loader**

In `core/tts_provider.py`, after `_get_qwen()` (line 290-305), add:
```python
    def _get_piper(self):
        """Lazy-load Piper local TTS engine."""
        if self._piper_engine is None:
            try:
                from core.piper_tts import DEFAULT_VOICE_PATH, PiperTTSEngine

                voice_file = os.path.join(
                    os.path.dirname(DEFAULT_VOICE_PATH),
                    self.config.piper_voice + ".onnx",
                )
                self._piper_engine = PiperTTSEngine(voice_path=voice_file)
            except ImportError:
                self._piper_engine = False
        return self._piper_engine if self._piper_engine is not False else None
```

Also add `self._piper_engine = None` to `__init__` (line 189, after `self._qwen_engine = None`).

- [ ] **Step 8: Update resolve_speaker to handle Piper**

In `TTSConfig.resolve_speaker()` (around line 139-158), add a return for piper_voice. Change the return type from `tuple[str, str | None]` to `tuple[str, str | None, str | None]`:

Replace the method:
```python
    def resolve_speaker(self, role: str | None = None) -> tuple[str, str | None]:
        """Resolve (edge_voice, qwen_speaker) for the active role."""
        active_role = role or self.role
        edge_v = self.edge_voice
        qwen_s = self.qwen_speaker
        if active_role:
            edge_v = get_project_speaker(self.project_id, active_role, TTSBackend.EDGE) or edge_v
            qwen_s = get_project_speaker(self.project_id, active_role, TTSBackend.QWEN) or qwen_s
        return edge_v, qwen_s
```
with:
```python
    def resolve_speaker(self, role: str | None = None) -> tuple[str, str | None, str | None]:
        """Resolve (edge_voice, qwen_speaker, piper_voice) for the active role."""
        active_role = role or self.role
        edge_v = self.edge_voice
        qwen_s = self.qwen_speaker
        piper_v = self.piper_voice
        if active_role:
            edge_v = get_project_speaker(self.project_id, active_role, TTSBackend.EDGE) or edge_v
            qwen_s = get_project_speaker(self.project_id, active_role, TTSBackend.QWEN) or qwen_s
            piper_v = get_project_speaker(self.project_id, active_role, TTSBackend.PIPER) or piper_v
        return edge_v, qwen_s, piper_v
```

Also update `_resolve_voice` (around line 319-324):
```python
    def _resolve_voice(self, voice: str | None, role: str | None) -> tuple[str | None, str | None, str | None]:
        """Resolve (edge_voice, qwen_speaker, piper_voice) given an explicit voice or auto-role."""
        if voice:
            return voice, voice, voice
        return self.config.resolve_speaker(role=role)
```

- [ ] **Step 9: Add Piper branch to speak()**

In `speak()` (around line 326-357), after the Qwen branch, add Piper routing. Replace:
```python
        backend = self.active_backend
        edge_v, qwen_s = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            return await self._speak_qwen(text, qwen_s, language, output_file)
        else:
            return await self._speak_edge(text, edge_v, rate, output_file)
```
with:
```python
        backend = self.active_backend
        edge_v, qwen_s, piper_v = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            return await self._speak_qwen(text, qwen_s, language, output_file)
        elif backend == TTSBackend.PIPER:
            return await self._speak_piper(text, piper_v, output_file)
        else:
            return await self._speak_edge(text, edge_v, rate, output_file)
```

- [ ] **Step 10: Implement _speak_piper()**

After `_speak_edge()` (around line 471+), add:
```python
    async def _speak_piper(
        self,
        text: str,
        voice: str | None = None,
        output_file: str | None = None,
    ) -> str | None:
        """Piper local TTS backend — writes WAV file."""
        engine = self._get_piper()
        if not engine or not engine.available:
            logger.warning("Piper TTS not available, falling back to Edge")
            return await self._speak_edge(text, voice or self.config.edge_voice, None, output_file)

        result = engine.speak(text)
        if result is None:
            return None
        wav_bytes, _sr = result

        if output_file:
            path = output_file
        else:
            fd, path = tempfile.mkstemp(suffix=".wav", dir=self.config.output_dir or None)
            os.close(fd)
        with open(path, "wb") as f:
            f.write(wav_bytes)
        return path
```

- [ ] **Step 11: Add Piper branch to speak_stream()**

In `speak_stream()` (around line 384-443), after the Qwen branch and before the Edge fallback, add Piper. Replace:
```python
        backend = self.active_backend
        edge_v, qwen_s = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            ...
        # Edge TTS — stream into memory
```
with (inserting the Piper branch between Qwen and Edge):
```python
        backend = self.active_backend
        edge_v, qwen_s, piper_v = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            ...  # existing Qwen code unchanged

        if backend == TTSBackend.PIPER:
            engine = self._get_piper()
            if not engine or not engine.available:
                return None
            result = engine.speak(text)
            if result is None:
                return None
            wav_bytes, _sr = result
            return wav_bytes, "audio/wav", "piper"

        # Edge TTS — stream into memory
```

- [ ] **Step 12: Add Piper to get_available_configs()**

In `get_available_configs()` (around line 230-286), add Piper to the `backends` dict and a `piper` section. After the `"qwen": { ... }` block in the returned dict:
```python
            "piper": {
                "available": piper_available,
                "description": "Piper TTS — local CPU, offline neural, ONNX runtime",
            },
```

And after the `"qwen": { ... }` data block, add:
```python
            "piper": {
                "available": piper_available,
                "voices": [{"id": name, **info} for name, info in PIPER_VOICES.items()],
            },
```

Before the return, compute `piper_available`:
```python
        piper_available = False
        try:
            piper = self._get_piper()
            if piper:
                piper_available = piper.available
        except Exception:
            pass
```

Add the import at the top of the method or file:
```python
from core.piper_tts import PIPER_VOICES
```

- [ ] **Step 13: Update speak_batch() for Piper**

In `speak_batch()` (around line 445-469), add a Piper branch:
```python
        if backend == TTSBackend.QWEN:
            return await self._speak_batch_qwen(texts, qwen_s, language)
        elif backend == TTSBackend.PIPER:
            paths = []
            for text in texts:
                path = await self._speak_piper(text, piper_v)
                if path:
                    paths.append(path)
            return paths
        else:
            ...
```

Also update the destructuring at the top of `speak_batch` to use 3-tuple.

- [ ] **Step 14: Run tests to verify they pass**

```bash
.venv\Scripts\python.exe -m pytest tests/core/test_tts_provider.py tests/core/test_piper_tts.py -v
```

Expected: ALL PASS

- [ ] **Step 15: Commit**

```bash
git add core/tts_provider.py tests/core/test_tts_provider.py
git commit -m "feat(tts): wire Piper backend into TTSProvider with AUTO fallback"
```

---

## Task 4: Update Frontend TTSSettingsPanel

**Files:**
- Modify: `frontend/src/components/UI/TTSSettingsPanel.tsx:87` (Backend type), lines 249-254 (Select options), lines 265-293 (voice list)
- Test: `frontend/src/__tests__/components/TTSSettingsPanel.piper.test.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/tts/config` now returns `piper.voices[]` and `backends.piper.available`
- Produces: New Select option in the TTS backend dropdown

- [ ] **Step 1: Write failing test**

Create `frontend/src/__tests__/components/TTSSettingsPanel.piper.test.tsx`:
```typescript
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { ConfigProvider, theme } from 'antd';

vi.mock('../../utils/audioFeedback', () => ({
  audioFeedback: { playSuccess: vi.fn(), playError: vi.fn(), playClick: vi.fn() },
}));
vi.mock('../../stores/uiStore', () => ({
  useUIStore: (sel?: (s: unknown) => unknown) => sel ? sel({ addToast: vi.fn() }) : { addToast: vi.fn() },
}));
vi.mock('../../utils/logger', () => ({
  createLogger: () => ({ info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() }),
}));

const mockConfig = {
  active_backend: 'piper',
  backends: {
    edge: { available: true, description: 'Edge' },
    qwen: { available: false, description: 'Qwen' },
    piper: { available: true, description: 'Piper local' },
  },
  edge: { voices: [] },
  qwen: { available: false, models: {}, languages: [], speakers: [], ritual_speakers: {}, voice_design_presets: [] },
  piper: {
    available: true,
    voices: [
      { id: 'en_US-lessac-medium', description: 'English US female', language: 'English', gender: 'female', quality: 'medium' },
    ],
  },
  gpu: { gpu_available: false, backend: 'cpu', devices: [] },
  ritual_roles: {},
  current_config: { backend: 'piper', piper_voice: 'en_US-lessac-medium' },
};

describe('TTSSettingsPanel — Piper backend', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/tts/config')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => mockConfig,
        } as Response);
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response);
    });
  });

  it('renders Piper as a selectable backend option', async () => {
    const { default: TTSSettingsPanel } = await import('../../components/UI/TTSSettingsPanel');
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
          <TTSSettingsPanel />
        </ConfigProvider>,
      );
      await new Promise(r => setTimeout(r, 100));
    });
    const text = container.textContent || '';
    expect(text).toContain('Piper');
    root.unmount();
    container.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && node_modules\.bin\vitest.cmd run src\__tests__\components\TTSSettingsPanel.piper.test.tsx
```

Expected: FAIL — "Piper" not in the rendered text.

- [ ] **Step 3: Add Piper to the Backend type and Select options**

In `frontend/src/components/UI/TTSSettingsPanel.tsx`:

Line 87, change:
```typescript
type Backend = 'auto' | 'edge' | 'qwen';
```
to:
```typescript
type Backend = 'auto' | 'edge' | 'qwen' | 'piper';
```

In the interface (around line 53), add:
```typescript
  piper?: {
    available?: boolean;
    voices?: Array<{ id: string; description?: string; language?: string; gender?: string; quality?: string }>;
    [key: string]: unknown;
  };
```

In the full-panel backend Select options (around line 249-254), add after the Qwen option:
```typescript
              { value: 'piper', label: '🔊 Piper TTS — Local CPU, offline neural, no GPU required', disabled: !piperAvail },
```

Compute `piperAvail` near the top of the component (around line 165):
```typescript
  const piperAvail = config.piper?.available;
  const piperVoices = config.piper?.voices || [];
```

- [ ] **Step 4: Add Piper voice selection section**

After the Edge TTS settings block (around line 293) and before the Qwen settings, add:
```typescript
        {/* Piper TTS Settings */}
        {(backend === 'piper' || backend === 'auto') && piperAvail && (
          <>
            <Text strong style={{ fontSize: 12, color: '#22c55e' }}>🔊 Piper Local Voice</Text>
            <Select
              value={piperVoice}
              onChange={(v) => { const val = String(v); setPiperVoice(val); saveConfig({ piper_voice: val }); }}
              className="w-full"
              options={piperVoices.map(v => ({
                value: v.id,
                label: `${v.id} — ${v.description} (${v.language}, ${v.gender})`,
              }))}
            />
            <Text type="secondary" style={{ fontSize: 10 }}>
              Runs entirely offline on CPU. Download voices via <code>python scripts/download_piper_voices.py</code>.
            </Text>
          </>
        )}
```

Add the state and fetch logic. Near line 96-101 (state declarations), add:
```typescript
  const [piperVoice, setPiperVoice] = useState('en_US-lessac-medium');
```

In `fetchConfig` (around line 114-120), add after the Qwen settings:
```typescript
        setPiperVoice(cc.piper_voice || 'en_US-lessac-medium');
```

In `saveConfig` (around line 134-139), add:
```typescript
    if (!updates.piper_voice) body.piper_voice = piperVoice;
```

Also update the TtsConfig interface's `current_config` to include `piper_voice?`:
```typescript
    piper_voice?: string;
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd frontend && node_modules\.bin\vitest.cmd run src\__tests__\components\TTSSettingsPanel.piper.test.tsx
```

Expected: PASS

- [ ] **Step 6: Run full frontend test suite to check for regressions**

```bash
cd frontend && node_modules\.bin\vitest.cmd run --reporter=basic
```

Expected: No new failures beyond the 4 pre-existing ones.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/UI/TTSSettingsPanel.tsx frontend/src/__tests__/components/TTSSettingsPanel.piper.test.tsx
git commit -m "feat(tts): add Piper backend option to TTSSettingsPanel frontend"
```

---

## Task 5: Manual QA — End-to-End Piper Synthesis

**Files:** None (manual verification)

**Interfaces:** N/A — this is the surface check.

- [ ] **Step 1: Rebuild the frontend**

```bash
cd C:\Users\llama\OneDrive\proj\vajra-stream\frontend
node_modules\.bin\vite.cmd build
```

- [ ] **Step 2: Start the backend**

```bash
cd C:\Users\llama\OneDrive\proj\vajra-stream
.venv\Scripts\python.exe run.py serve
```

Wait for "Backend healthy" log line.

- [ ] **Step 3: Verify Piper appears in GET /api/v1/tts/config**

```bash
curl -s http://localhost:8008/api/v1/tts/config | python -m json.tool | findstr piper
```

Expected: `"piper": {"available": true, ...}` with voice catalog.

- [ ] **Step 4: Synthesize via Piper through the streaming endpoint**

```bash
curl -s -X POST http://localhost:8008/api/v1/tts/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"May all beings be happy and free from suffering.\", \"backend\": \"piper\"} ^
  -o test_piper_stream.wav
```

Expected: `test_piper_stream.wav` file created (~50-200 KB). Play it to confirm audible speech.

- [ ] **Step 5: Verify frontend Settings → TTS shows Piper**

Open `http://localhost:3009/settings/tts` in a browser. The backend dropdown should show "🔊 Piper TTS — Local CPU, offline neural, no GPU required". Select it, choose a voice, click Apply.

- [ ] **Step 6: Clean up test artifacts**

```bash
del test_piper.wav test_piper_stream.wav
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Piper installed via `piper-tts>=1.5.0` — Task 1
- ✅ Python 3.14 compatible — verified (cp39-abi3 wheel)
- ✅ CPU-only, no GPU — ONNX runtime CPU
- ✅ Voice model downloaded from HuggingFace — Task 1 Step 5
- ✅ `PiperTTSEngine` class created — Task 2
- ✅ Wired into `TTSProvider` with `PIPER` backend — Task 3
- ✅ Frontend `TTSSettingsPanel` shows Piper option — Task 4
- ✅ End-to-end streaming audio verification — Task 5
- ✅ No new `AudioService` class (ADR 001 respected) — Piper slots into `TTSProvider`
- ✅ No `as any` in new TypeScript — proper interfaces used
- ✅ Tests for engine + provider routing + frontend rendering — Tasks 2, 3, 4

**Placeholder scan:** No TBD, TODO, or "implement later" found.

**Type consistency:** `piper_voice: str` used consistently across TTSConfig, resolve_speaker, _speak_piper, TTSSettingsPanel state, and the TtsConfig TypeScript interface.
