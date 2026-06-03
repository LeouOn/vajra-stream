"""
Qwen3-TTS Integration — neural text-to-speech via Qwen3-TTS models.

Supports:
  - CustomVoice: 9 preset speakers across 10 languages, instruction-based emotion control
  - VoiceDesign: describe any voice in natural language → generate that voice
  - VoiceClone: 3-second audio reference → clone and speak as that voice
  - Streaming: 97ms latency for real-time scenarios
  - Batch generation: multiple texts in one GPU pass for speed

Models (auto-downloaded from HuggingFace/ModelScope on first use):
  - Qwen3-TTS-12Hz-0.6B-CustomVoice  (~3 GB) — lightweight, 9 speakers
  - Qwen3-TTS-12Hz-1.7B-CustomVoice  (~7 GB) — highest quality, 9 speakers
  - Qwen3-TTS-12Hz-1.7B-VoiceDesign   (~7 GB) — free-form voice description
  - Qwen3-TTS-12Hz-1.7B-Base          (~7 GB) — 3-second voice clone

Gracefully degrades: returns None if qwen_tts not installed or GPU unavailable.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ─── Speaker Catalog ───────────────────────────────────────

QWEN_SPEAKERS = {
    "Vivian":    {"description": "Bright, slightly edgy young female voice",        "native": "Chinese", "gender": "female", "age": "young"},
    "Serena":    {"description": "Warm, gentle young female voice",                 "native": "Chinese", "gender": "female", "age": "young"},
    "Uncle_Fu":  {"description": "Seasoned male voice with a low, mellow timbre",   "native": "Chinese", "gender": "male",   "age": "senior"},
    "Dylan":     {"description": "Youthful Beijing male voice, clear and natural",  "native": "Chinese (Beijing)", "gender": "male", "age": "young"},
    "Eric":      {"description": "Lively Chengdu male voice, slightly husky",       "native": "Chinese (Sichuan)", "gender": "male", "age": "young"},
    "Ryan":      {"description": "Dynamic male voice with strong rhythmic drive",   "native": "English", "gender": "male",   "age": "adult"},
    "Aiden":     {"description": "Sunny American male voice with a clear midrange", "native": "English", "gender": "male",   "age": "young"},
    "Ono_Anna":  {"description": "Playful Japanese female voice, light and nimble", "native": "Japanese","gender": "female", "age": "young"},
    "Sohee":     {"description": "Warm Korean female voice with rich emotion",      "native": "Korean",  "gender": "female", "age": "young"},
}

QWEN_LANGUAGES = [
    "Chinese", "English", "Japanese", "Korean",
    "German", "French", "Russian", "Portuguese", "Spanish", "Italian",
]

# Recommend speakers for ritual/spiritual content
RITUAL_SPEAKERS = {
    "buddhist_chant":    "Uncle_Fu",   # Deep, seasoned — sutra recitation
    "compassionate":     "Serena",     # Warm, gentle — blessings
    "meditation_guide":  "Vivian",     # Clear, bright — guided meditation
    "dharma_teaching":   "Dylan",      # Natural Beijing — dharma talks
    "english_blessing":  "Ryan",       # Dynamic English — universal blessings
}

# Voice design presets for Vajra.Stream use cases
VOICE_DESIGN_PRESETS = {
    "meditation_master": {
        "instruct": "A deep, resonant male voice in his 60s, speaking slowly with the gravity of decades of meditation practice. Each word carries weight and stillness.",
        "language": "Chinese",
    },
    "compassionate_bodhisattva": {
        "instruct": "A warm, luminous voice that seems to emanate unconditional love. Neither fully male nor female, with a slight ethereal quality. Speaks as if each syllable is a blessing.",
        "language": "Chinese",
    },
    "zen_teacher": {
        "instruct": "A crisp, precise voice with a hint of a smile. Speaks in short, deliberate phrases with long pauses. Slightly gruff but deeply kind.",
        "language": "Chinese",
    },
    "sutra_chanter": {
        "instruct": "A sonorous monastic voice trained in traditional sutra chanting. Rhythmic, even-paced, with natural vibrato on sustained vowels. The voice of a temple hall at dawn.",
        "language": "Chinese",
    },
    "english_sacred": {
        "instruct": "A calm, measured voice with perfect clarity. Speaks sacred texts with reverence but without theatricality. Warm baritone, BBC documentary style.",
        "language": "English",
    },
}


# ─── Qwen3-TTS Wrapper ─────────────────────────────────────

@dataclass
class QwenTTSConfig:
    """Configuration for Qwen3-TTS model."""
    model_name: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    device: str = "cuda:0"  # "cuda:0", "cpu", "auto"
    dtype: str = "bfloat16"  # "bfloat16", "float16", "float32"
    use_flash_attention: bool = False
    default_speaker: str = "Uncle_Fu"
    default_language: str = "Chinese"

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "dtype": self.dtype,
            "default_speaker": self.default_speaker,
            "default_language": self.default_language,
        }


class QwenTTSEngine:
    """
    Wraps Qwen3-TTS models behind a uniform interface.

    Usage:
        engine = QwenTTSEngine()
        if engine.available:
            audio, sr = engine.speak("南無普光佛", speaker="Uncle_Fu")
            sf.write("output.wav", audio, sr)
    """

    def __init__(self, config: QwenTTSConfig | None = None):
        self.config = config or QwenTTSConfig()
        self._model = None
        self._available: bool | None = None  # None = not yet checked

    @property
    def available(self) -> bool:
        """Check if Qwen3-TTS is usable (GPU + package installed)."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """Probe for qwen_tts package and GPU (CUDA/ROCm) availability."""
        try:
            import torch
            has_gpu = torch.cuda.is_available()
            if has_gpu:
                device_name = torch.cuda.get_device_name(0) or "Unknown GPU"
                # Detect ROCm vs CUDA
                if hasattr(torch.version, 'hip') and torch.version.hip is not None:
                    logger.info(f"AMD ROCm detected: {device_name} (HIP {torch.version.hip})")
                else:
                    logger.info(f"NVIDIA CUDA detected: {device_name}")
            else:
                logger.info("No GPU detected — Qwen3-TTS will run on CPU (slow)")
        except ImportError:
            has_gpu = False
            logger.info("PyTorch not installed")

        try:
            import qwen_tts  # noqa: F401
            return True  # Package available — can run on CPU or GPU
        except ImportError:
            logger.info("qwen_tts not installed. Install with: pip install qwen-tts")
            return False

    def get_device_info(self) -> dict[str, Any]:
        """Return GPU/ROCm device information for display."""
        info = {"gpu_available": False, "backend": "cpu", "devices": []}
        try:
            import torch
            if torch.cuda.is_available():
                info["gpu_available"] = True
                # Detect ROCm vs CUDA
                if hasattr(torch.version, 'hip') and torch.version.hip is not None:
                    info["backend"] = "ROCm"
                    info["hip_version"] = torch.version.hip
                else:
                    info["backend"] = "CUDA"
                    info["cuda_version"] = torch.version.cuda
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    info["devices"].append({
                        "id": i,
                        "name": torch.cuda.get_device_name(i),
                        "vram_gb": round(props.total_mem / 1e9, 1),
                        "compute": f"{props.major}.{props.minor}",
                    })
        except ImportError:
            pass
        return info

    def _load_model(self):
        """Lazy-load the Qwen3-TTS model with CUDA/ROCm/CPU auto-detection."""
        if self._model is not None:
            return

        import torch
        from qwen_tts import Qwen3TTSModel

        device = self.config.device
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda:0"  # Works for both CUDA (NVIDIA) and ROCm (AMD)
                backend = "ROCm" if (hasattr(torch.version, 'hip') and torch.version.hip) else "CUDA"
                logger.info(f"Auto-selected GPU: {torch.cuda.get_device_name(0)} ({backend})")
            else:
                device = "cpu"
                logger.warning("No GPU detected — falling back to CPU (Qwen3-TTS will be slow on CPU)")

        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        dtype = dtype_map.get(self.config.dtype, torch.float32)

        # ROCm may not support bfloat16 on some GPUs — fall back to float16
        if dtype == torch.bfloat16:
            try:
                torch.zeros(1, dtype=torch.bfloat16, device=device)
            except (RuntimeError, TypeError):
                logger.info("bfloat16 not supported on this device — falling back to float16")
                dtype = torch.float16

        load_kwargs = {
            "device_map": device,
            "dtype": dtype,
        }
        # Flash Attention 2 works on both CUDA (Ampere+) and ROCm (CDNA2/RDNA3+)
        if self.config.use_flash_attention and device != "cpu":
            try:
                load_kwargs["attn_implementation"] = "flash_attention_2"
            except Exception:
                logger.info("Flash Attention 2 not available — using default attention")

        logger.info(f"Loading Qwen3-TTS model: {self.config.model_name} on {device} ({dtype})")
        self._model = Qwen3TTSModel.from_pretrained(
            self.config.model_name,
            **load_kwargs,
        )
        logger.info("Qwen3-TTS model loaded successfully.")

    def get_supported_speakers(self) -> list[dict[str, Any]]:
        """Return available speakers with descriptions."""
        return [
            {"id": name, **info}
            for name, info in QWEN_SPEAKERS.items()
        ]

    def get_supported_languages(self) -> list[str]:
        """Return supported languages."""
        return QWEN_LANGUAGES

    def get_ritual_speakers(self) -> dict[str, str]:
        """Return recommended speaker→role mapping for ritual use."""
        return RITUAL_SPEAKERS

    def get_voice_design_presets(self) -> dict[str, dict]:
        """Return voice design presets for Vajra.Stream contexts."""
        return VOICE_DESIGN_PRESETS

    def speak(
        self,
        text: str | list[str],
        speaker: str | None = None,
        language: str | None = None,
        instruct: str | None = None,
    ) -> tuple[np.ndarray, int] | list[tuple[np.ndarray, int]] | None:
        """
        Generate speech from text using Qwen3-TTS CustomVoice model.

        Args:
            text: Chinese/English/etc text or list of texts for batch
            speaker: One of the 9 preset speakers (default: config.default_speaker)
            language: Target language (default: config.default_language)
            instruct: Optional emotion/prosody instruction (e.g., "用特别愤怒的语气说")

        Returns:
            (waveform_numpy, sample_rate) or list of tuples for batch,
            or None if unavailable.
        """
        if not self.available:
            return None

        self._load_model()

        speaker = speaker or self.config.default_speaker
        language = language or self.config.default_language
        is_batch = isinstance(text, list)

        try:
            wavs, sr = self._model.generate_custom_voice(
                text=text,
                language=language if not is_batch else [language] * len(text),
                speaker=speaker if not is_batch else [speaker] * len(text),
                instruct=instruct if instruct else ("" if not is_batch else [""] * len(text)),
            )

            if is_batch:
                return [(wavs[i], sr) for i in range(len(wavs))]
            return wavs[0], sr
        except Exception as e:
            logger.error(f"Qwen3-TTS speak error: {e}")
            return None

    def speak_batch(
        self,
        texts: list[str],
        speaker: str | None = None,
        language: str | None = None,
    ) -> list[tuple[np.ndarray, int]] | None:
        """
        Generate speech for multiple texts in one GPU pass (much faster than sequential).

        Use for reciting Buddha name lists, narrative paragraphs, etc.
        """
        return self.speak(texts, speaker=speaker, language=language)

    def design_voice(
        self,
        text: str,
        instruct: str,
        language: str = "Chinese",
    ) -> tuple[np.ndarray, int] | None:
        """
        Generate speech using voice design — describe the voice in natural language.

        Requires Qwen3-TTS-12Hz-1.7B-VoiceDesign model.

        Args:
            text: Text to speak
            instruct: Natural language voice description
            language: Target language

        Returns:
            (waveform, sample_rate) or None
        """
        if not self.available:
            return None

        self._load_model()

        try:
            wavs, sr = self._model.generate_voice_design(
                text=text,
                language=language,
                instruct=instruct,
            )
            return wavs[0], sr
        except AttributeError:
            logger.error("VoiceDesign requires Qwen3-TTS-12Hz-1.7B-VoiceDesign model")
            return None
        except Exception as e:
            logger.error(f"Qwen3-TTS voice design error: {e}")
            return None

    def clone_voice(
        self,
        text: str,
        ref_audio: str | np.ndarray,
        ref_text: str = "",
        language: str = "Chinese",
    ) -> tuple[np.ndarray, int] | None:
        """
        Clone a voice from a reference audio sample and speak new text.

        Requires Qwen3-TTS-12Hz-1.7B-Base model.

        Args:
            text: New text to speak
            ref_audio: Path to reference audio file or numpy array
            ref_text: Transcript of the reference audio
            language: Target language

        Returns:
            (waveform, sample_rate) or None
        """
        if not self.available:
            return None

        self._load_model()

        try:
            wavs, sr = self._model.generate_voice_clone(
                text=text,
                language=language,
                ref_audio=ref_audio,
                ref_text=ref_text,
            )
            return wavs[0], sr
        except Exception as e:
            logger.error(f"Qwen3-TTS voice clone error: {e}")
            return None


# ─── Global Singleton ──────────────────────────────────────

_qwen_tts: QwenTTSEngine | None = None


def get_qwen_tts(config: QwenTTSConfig | None = None) -> QwenTTSEngine:
    """Get or create the global Qwen3-TTS engine instance."""
    global _qwen_tts
    if _qwen_tts is None:
        _qwen_tts = QwenTTSEngine(config)
    elif config is not None:
        _qwen_tts.config = config
    return _qwen_tts
