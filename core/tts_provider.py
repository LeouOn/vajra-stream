"""
TTS Provider — unified text-to-speech abstraction for Vajra.Stream.

Supports multiple backends with automatic fallback:
  - Edge TTS (fast, no GPU, Chinese-optimized, always available)
  - Qwen3-TTS (neural, GPU-accelerated, voice design/clone, 10 languages)

Usage:
    provider = get_tts_provider()
    provider.set_backend("edge")  # or "qwen"

    # Quick speak
    path = await provider.speak("南無普光佛")

    # Batch speak (much faster on Qwen3-TTS)
    paths = await provider.speak_batch(["name1", "name2", ...])

    # Check capabilities
    print(provider.capabilities)

Configuration via API:
    GET  /api/v1/tts/config     — list available backends, speakers, languages
    POST /api/v1/tts/config     — switch backend, voice, language
    POST /api/v1/tts/speak      — generate TTS audio
"""

import logging
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TTSBackend(str, Enum):
    EDGE = "edge"
    QWEN = "qwen"
    AUTO = "auto"  # Qwen if GPU available, else Edge


# Ritual-purpose → Qwen speaker ID (auto-mapped when caller specifies a "role")
# This is the default for new projects. Each project can override via ProjectTTSConfig.
RITUAL_ROLE_SPEAKERS: dict[str, dict[str, str]] = {
    "qwen": {
        "buddhist_chant": "Uncle_Fu",
        "compassionate": "Serena",
        "meditation_guide": "Vivian",
        "dharma_teaching": "Dylan",
        "english_blessing": "Ryan",
        "outlook_narrative": "Serena",  # Warm, gentle — for sutra-style blessings
        "outlook_epic": "Uncle_Fu",  # Deep, seasoned — for epic sealings
    },
    "edge": {
        "buddhist_chant": "zh-CN-YunxiNeural",
        "compassionate": "zh-CN-XiaoxiaoNeural",
        "meditation_guide": "zh-CN-XiaoxiaoNeural",
        "dharma_teaching": "zh-CN-YunxiNeural",
        "english_blessing": "en-US-AriaNeural",
        "outlook_narrative": "zh-CN-YunxiNeural",
        "outlook_epic": "zh-CN-YunxiNeural",
    },
}

# Per-project speaker overrides (project_id → role → speaker)
_project_speaker_overrides: dict[str, dict[str, str]] = {}


def set_project_speaker(project_id: str, role: str, speaker: str) -> None:
    """Override the speaker used for a role within a given project."""
    if not project_id or not role or not speaker:
        return
    _project_speaker_overrides.setdefault(project_id, {})[role] = speaker


def get_project_speaker(project_id: str | None, role: str, backend: "TTSBackend") -> str:
    """
    Resolve the speaker for a (project, role, backend) tuple.

    Resolution order:
      1. Per-project override (if project_id is set)
      2. Global default for the role
      3. Backend fallback default (Uncle_Fu / zh-CN-YunxiNeural)
    """
    backend_key = backend.value if backend != TTSBackend.AUTO else "qwen"
    if project_id and project_id in _project_speaker_overrides:
        override = _project_speaker_overrides[project_id].get(role)
        if override:
            return override
    role_map = RITUAL_ROLE_SPEAKERS.get(backend_key, {})
    if role in role_map:
        return role_map[role]
    return "Uncle_Fu" if backend_key == "qwen" else "zh-CN-YunxiNeural"


def clear_project_speakers(project_id: str) -> None:
    """Remove all speaker overrides for a project."""
    _project_speaker_overrides.pop(project_id, None)


def list_project_overrides(project_id: str | None = None) -> dict[str, dict[str, str]]:
    """Return all per-project speaker overrides (or one project's overrides)."""
    if project_id is None:
        return {k: dict(v) for k, v in _project_speaker_overrides.items()}
    return {project_id: dict(_project_speaker_overrides.get(project_id, {}))}


@dataclass
class TTSConfig:
    """Active TTS configuration."""

    backend: TTSBackend = TTSBackend.AUTO
    # Edge TTS settings
    edge_voice: str = "zh-CN-YunxiNeural"  # Male, warm — traditional sutra feel
    edge_rate: str = "-25%"
    # Qwen3-TTS settings
    qwen_model: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    qwen_speaker: str = "Uncle_Fu"
    qwen_language: str = "Chinese"
    # Ritual role for auto-speaker resolution (set per-call; None = use config defaults)
    role: str | None = None
    project_id: str | None = None
    # Output
    output_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend.value,
            "edge_voice": self.edge_voice,
            "edge_rate": self.edge_rate,
            "qwen_model": self.qwen_model,
            "qwen_speaker": self.qwen_speaker,
            "qwen_language": self.qwen_language,
            "role": self.role,
            "project_id": self.project_id,
        }

    def resolve_speaker(self, role: str | None = None) -> tuple[str, str | None]:
        """
        Resolve which (edge_voice, qwen_speaker) pair to use for the active role.

        Args:
            role: Optional role override (e.g. "buddhist_chant", "outlook_narrative").
                  Falls back to self.role.

        Returns:
            (edge_voice, qwen_speaker) tuple — either may be None if not relevant.
        """
        active_role = role or self.role
        # Edge auto-mode → resolve to Edge fallback
        # Qwen auto-mode → resolve to Qwen speaker
        edge_v = self.edge_voice
        qwen_s = self.qwen_speaker
        if active_role:
            edge_v = get_project_speaker(self.project_id, active_role, TTSBackend.EDGE) or edge_v
            qwen_s = get_project_speaker(self.project_id, active_role, TTSBackend.QWEN) or qwen_s
        return edge_v, qwen_s


class TTSProvider:
    """
    Unified TTS interface with multiple backends.

    Automatically routes to the best available backend:
    - Qwen3-TTS if GPU + qwen_tts package installed
    - Edge TTS as fallback (always available, no GPU needed)
    """

    # Edge TTS voice catalog
    EDGE_VOICES = {
        "zh-CN-YunxiNeural": {
            "description": "Male, warm — traditional sutra chanting feel",
            "gender": "male",
            "style": "sacred",
        },
        "zh-CN-XiaoxiaoNeural": {"description": "Female, clear, natural", "gender": "female", "style": "neutral"},
        "zh-CN-XiaoyiNeural": {"description": "Female, lively", "gender": "female", "style": "bright"},
        "zh-TW-HsiaoChenNeural": {"description": "Taiwanese female, gentle", "gender": "female", "style": "gentle"},
        "zh-HK-HiuGaaiNeural": {"description": "Cantonese female", "gender": "female", "style": "regional"},
        "en-US-AriaNeural": {"description": "American female, warm and engaging", "gender": "female", "style": "warm"},
        "en-US-GuyNeural": {"description": "American male, enthusiastic", "gender": "male", "style": "bright"},
        "ja-JP-NanamiNeural": {"description": "Japanese female, natural", "gender": "female", "style": "natural"},
        "ko-KR-SunHiNeural": {"description": "Korean female, natural", "gender": "female", "style": "natural"},
    }

    def __init__(self, config: TTSConfig | None = None):
        self.config = config or TTSConfig()
        self._qwen_engine = None

    # ─── Properties ─────────────────────────────────────────

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

    @property
    def capabilities(self) -> dict[str, Any]:
        """Return what the active backend can do."""
        backend = self.active_backend
        caps = {
            "backend": backend.value,
            "streaming": backend == TTSBackend.QWEN,
            "voice_design": backend == TTSBackend.QWEN,
            "voice_clone": backend == TTSBackend.QWEN,
            "batch_fast": backend == TTSBackend.QWEN,
            "languages": [],
            "speakers": [],
        }

        if backend == TTSBackend.QWEN:
            from core.qwen_tts import QWEN_LANGUAGES, QWEN_SPEAKERS

            caps["languages"] = QWEN_LANGUAGES
            caps["speakers"] = [{"id": name, **info} for name, info in QWEN_SPEAKERS.items()]
        else:
            caps["languages"] = ["Chinese", "English", "Japanese", "Korean"]
            caps["speakers"] = [{"id": name, **info} for name, info in self.EDGE_VOICES.items()]

        return caps

    def get_available_configs(self) -> dict[str, Any]:
        """Return full configuration catalog for the frontend."""
        qwen_available = False
        gpu_info = {"gpu_available": False, "backend": "cpu", "devices": []}
        try:
            qwen = self._get_qwen()
            if qwen:
                qwen_available = qwen.available
                if qwen_available:
                    gpu_info = qwen.get_device_info()
        except Exception:
            pass

        from core.qwen_tts import QWEN_SPEAKERS, RITUAL_SPEAKERS, VOICE_DESIGN_PRESETS

        return {
            "backends": {
                "edge": {"available": True, "description": "Microsoft Edge TTS — fast, no GPU, always available"},
                "qwen": {
                    "available": qwen_available,
                    "description": "Qwen3-TTS neural — GPU-accelerated, voice design/clone, 10 languages",
                },
            },
            "active_backend": self.active_backend.value,
            "gpu": gpu_info,
            "edge": {
                "voices": [{"id": name, **info} for name, info in self.EDGE_VOICES.items()],
            },
            "qwen": {
                "available": qwen_available,
                "models": {
                    "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                    "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                    "1.7B-Design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                    "1.7B-Clone": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                },
                "languages": [
                    "Chinese",
                    "English",
                    "Japanese",
                    "Korean",
                    "German",
                    "French",
                    "Russian",
                    "Portuguese",
                    "Spanish",
                    "Italian",
                ]
                if qwen_available
                else [],
                "speakers": [{"id": name, **info} for name, info in QWEN_SPEAKERS.items()] if qwen_available else [],
                "ritual_speakers": RITUAL_SPEAKERS if qwen_available else {},
                "voice_design_presets": list(VOICE_DESIGN_PRESETS.keys()) if qwen_available else [],
            },
            "ritual_roles": {backend: list(roles.keys()) for backend, roles in RITUAL_ROLE_SPEAKERS.items()},
            "current_config": self.config.to_dict(),
        }

    # ─── Internal ───────────────────────────────────────────

    def _get_qwen(self):
        """Lazy-load Qwen3-TTS engine."""
        if self._qwen_engine is None:
            try:
                from core.qwen_tts import QwenTTSConfig, QwenTTSEngine

                qwen_config = QwenTTSConfig(
                    model_name=self.config.qwen_model,
                    device="auto",
                    default_speaker=self.config.qwen_speaker,
                    default_language=self.config.qwen_language,
                )
                self._qwen_engine = QwenTTSEngine(qwen_config)
            except ImportError:
                self._qwen_engine = False  # Sentinel
        return self._qwen_engine if self._qwen_engine is not False else None

    def set_backend(self, backend: str):
        """Switch active backend."""
        self.config.backend = TTSBackend(backend)

    def set_config(self, **kwargs):
        """Update TTS config fields."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    # ─── Speak API ──────────────────────────────────────────

    def _resolve_voice(self, voice: str | None, role: str | None) -> tuple[str | None, str | None]:
        """Resolve (edge_voice, qwen_speaker) given an explicit voice or auto-role."""
        if voice:
            return voice, voice
        edge_v, qwen_s = self.config.resolve_speaker(role=role)
        return edge_v, qwen_s

    async def speak(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        language: str | None = None,
        output_file: str | None = None,
        role: str | None = None,
    ) -> str | None:
        """
        Generate speech and return path to audio file.

        Args:
            text: Text to speak
            voice: Override voice/speaker (bypasses role-based auto-mapping)
            rate: Override speech rate (Edge TTS only, e.g. "-25%")
            language: Override language (Qwen3-TTS only)
            output_file: Save to this path instead of temp file
            role: Ritual role (e.g. "buddhist_chant", "outlook_narrative") for
                  auto-speaker mapping. Falls back to self.config.role, then
                  explicit voice, then config defaults.

        Returns:
            Path to audio file, or None on failure
        """
        backend = self.active_backend
        edge_v, qwen_s = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            return await self._speak_qwen(text, qwen_s, language, output_file)
        else:
            return await self._speak_edge(text, edge_v, rate, output_file)

    async def speak_stream(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        language: str | None = None,
        role: str | None = None,
        instruct: str | None = None,
    ) -> tuple[bytes, str, str] | None:
        """
        Generate speech and return (audio_bytes, mime_type, backend_id).

        The bytes are ready to stream back to a browser <audio> element.
        Returns None on failure.

        - Edge TTS → audio/mpeg
        - Qwen3-TTS → audio/wav (raw PCM wrapped in a WAV header)

        ``instruct`` is forwarded to Qwen3-TTS's VoiceDesign model when
        present — this unlocks the 5 ritual voice presets defined in
        ``core/qwen_tts.py:VOICE_DESIGN_PRESETS`` (compassionate_bodhisattva,
        meditation_master, sutra_chanter, zen_teacher, english_sacred).
        Previously these presets existed but were unreachable from the
        ``/speak`` endpoint.
        """
        backend = self.active_backend
        edge_v, qwen_s = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            engine = self._get_qwen()
            if not engine or not engine.available:
                return None
            result = engine.speak(
                text=text,
                speaker=qwen_s,
                language=language or self.config.qwen_language,
                instruct=instruct or "",
            )
            if result is None:
                return None
            wav, sr = result
            try:
                import io

                import soundfile as sf

                buf = io.BytesIO()
                sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
                return buf.getvalue(), "audio/wav", "qwen"
            except ImportError:
                # No soundfile — write minimal WAV header around float32 PCM
                import io

                import numpy as np

                buf = io.BytesIO()
                pcm = np.clip(wav, -1.0, 1.0)
                pcm_i16 = (pcm * 32767.0).astype("<i2")
                data = pcm_i16.tobytes()
                with io.BytesIO() as wav_buf:
                    import wave

                    with wave.open(wav_buf, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(sr)
                        wf.writeframes(data)
                    return wav_buf.getvalue(), "audio/wav", "qwen"

        # Edge TTS — stream into memory
        try:
            import edge_tts
        except ImportError:
            return None

        edge_v_eff = edge_v or self.config.edge_voice
        rate_eff = rate or self.config.edge_rate
        communicate = edge_tts.Communicate(text, edge_v_eff, rate=rate_eff)
        chunks: list[bytes] = []
        async for ev in communicate.stream():
            if ev.get("type") == "audio":
                chunks.append(ev["data"])
        if not chunks:
            return None
        return b"".join(chunks), "audio/mpeg", "edge"

    async def speak_batch(
        self,
        texts: list[str],
        voice: str | None = None,
        language: str | None = None,
        role: str | None = None,
    ) -> list[str]:
        """
        Generate speech for multiple texts efficiently.

        On Qwen3-TTS: one GPU pass for all texts (fast).
        On Edge TTS: sequential (slower but reliable).
        """
        backend = self.active_backend
        edge_v, qwen_s = self._resolve_voice(voice, role)

        if backend == TTSBackend.QWEN:
            return await self._speak_batch_qwen(texts, qwen_s, language)
        else:
            paths = []
            for text in texts:
                path = await self._speak_edge(text, edge_v)
                if path:
                    paths.append(path)
            return paths

    async def _speak_edge(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        output_file: str | None = None,
    ) -> str | None:
        """Edge TTS backend."""
        try:
            import edge_tts
        except ImportError:
            logger.error("edge_tts not installed. Run: pip install edge-tts")
            return None

        voice = voice or self.config.edge_voice
        rate = rate or self.config.edge_rate
        output_path = output_file or os.path.join(tempfile.gettempdir(), f"vajra_tts_{hash(text) % 100000}.mp3")

        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return None

    async def _speak_qwen(
        self,
        text: str,
        speaker: str | None = None,
        language: str | None = None,
        output_file: str | None = None,
    ) -> str | None:
        """Qwen3-TTS backend."""
        engine = self._get_qwen()
        if not engine or not engine.available:
            return None

        result = engine.speak(
            text=text,
            speaker=speaker or self.config.qwen_speaker,
            language=language or self.config.qwen_language,
        )
        if result is None:
            return None

        wav, sr = result
        output_path = output_file or os.path.join(tempfile.gettempdir(), f"vajra_qwen_tts_{hash(text) % 100000}.wav")

        try:
            import soundfile as sf

            sf.write(output_path, wav, sr)
            return output_path
        except ImportError:
            # Fallback: save raw numpy
            import numpy as np

            np.save(output_path.replace(".wav", ".npy"), wav)
            return output_path.replace(".wav", ".npy")

    async def _speak_batch_qwen(
        self,
        texts: list[str],
        speaker: str | None = None,
        language: str | None = None,
    ) -> list[str]:
        """Qwen3-TTS batch generation."""
        engine = self._get_qwen()
        if not engine or not engine.available:
            return []

        results = engine.speak_batch(
            texts=texts,
            speaker=speaker or self.config.qwen_speaker,
            language=language or self.config.qwen_language,
        )
        if results is None:
            return []

        output_paths = []
        for i, (wav, sr) in enumerate(results):
            output_path = os.path.join(tempfile.gettempdir(), f"vajra_qwen_batch_{i}_{hash(texts[i]) % 100000}.wav")
            try:
                import soundfile as sf

                sf.write(output_path, wav, sr)
                output_paths.append(output_path)
            except ImportError:
                pass

        return output_paths


# ─── Global Singleton ──────────────────────────────────────

_tts_provider: TTSProvider | None = None


def get_tts_provider() -> TTSProvider:
    """Get or create the global TTS provider."""
    global _tts_provider
    if _tts_provider is None:
        _tts_provider = TTSProvider()
    return _tts_provider
