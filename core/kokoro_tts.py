"""
KokoroTTSEngine — local CPU TTS via kokoro-onnx (ONNX runtime).

82M-param neural TTS, 54 voices across 8 languages, MIT+Apache-2.0 licensed.
Near real-time on CPU (~2x real-time on AMD Ryzen 7840U).

Usage:
    engine = KokoroTTSEngine()
    if engine.available:
        samples, sample_rate = engine.speak("Hello world", voice="af_heart")
"""

import io
import logging
import os
import wave

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = os.path.join("models", "kokoro", "kokoro-v1.0.onnx")
DEFAULT_VOICES_PATH = os.path.join("models", "kokoro", "voices-v1.0.bin")

KOKORO_VOICES: dict[str, dict[str, str]] = {
    "af_heart": {"description": "American female, warm heart-centered", "language": "English", "gender": "female"},
    "af_bella": {"description": "American female, soft and gentle", "language": "English", "gender": "female"},
    "am_michael": {"description": "American male, steady and clear", "language": "English", "gender": "male"},
    "am_adam": {"description": "American male, deep and resonant", "language": "English", "gender": "male"},
    "zf_xiaobei": {
        "description": "Mandarin Chinese female, clear — sutra recitation",
        "language": "Chinese",
        "gender": "female",
    },
    "zf_xiaoxiao": {"description": "Mandarin Chinese female, warm", "language": "Chinese", "gender": "female"},
    "zm_yunxi": {
        "description": "Mandarin Chinese male, warm — traditional chanting feel",
        "language": "Chinese",
        "gender": "male",
    },
    "zm_yunyang": {"description": "Mandarin Chinese male, resonant", "language": "Chinese", "gender": "male"},
    "bf_emma": {"description": "British female, refined", "language": "English", "gender": "female"},
    "bm_george": {"description": "British male, authoritative", "language": "English", "gender": "male"},
}

DEFAULT_VOICE = "af_heart"

VOICE_PREFIX_LANG: dict[str, str] = {
    "a": "en-us",
    "b": "en-gb",
    "z": "cmn",
    "j": "ja",
    "p": "pt-br",
    "e": "es",
    "f": "fr-fr",
    "h": "hi",
    "i": "it",
}


def _lang_for_voice(voice: str) -> str:
    prefix = voice[0].lower() if voice else "a"
    return VOICE_PREFIX_LANG.get(prefix, "en-us")


class KokoroTTSEngine:
    """Local CPU TTS via kokoro-onnx."""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        voices_path: str = DEFAULT_VOICES_PATH,
    ):
        self.model_path = model_path
        self.voices_path = voices_path
        self._model = None
        self._loaded = False

    @property
    def available(self) -> bool:
        try:
            import kokoro_onnx  # noqa: F401
        except ImportError:
            return False
        return os.path.isfile(self.model_path) and os.path.isfile(self.voices_path)

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._model is not None
        self._loaded = True
        if not self.available:
            return False
        try:
            from kokoro_onnx import Kokoro

            self._model = Kokoro(self.model_path, self.voices_path)
            logger.info(f"Kokoro model loaded: {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load Kokoro model: {e}")
            self._model = None
            return False

    def speak(self, text: str, voice: str = DEFAULT_VOICE) -> tuple[bytes, int] | None:
        """Synthesize text to WAV bytes (PCM 16-bit, 24kHz).

        Returns (wav_bytes, sample_rate) or None on failure.
        """
        if not text.strip():
            return None
        if not self._ensure_loaded() or self._model is None:
            return None
        try:
            lang = _lang_for_voice(voice)
            if lang == "cmn":
                return self._speak_cmn(text, voice)
            samples, sample_rate = self._model.create(text, voice=voice, lang=lang)
            return self._wav_bytes(samples, sample_rate)
        except Exception as e:
            logger.error(f"Kokoro synthesis failed: {e}")
            return None

    def _speak_cmn(self, text: str, voice: str) -> tuple[bytes, int] | None:
        """Chinese synthesis with espeak-ng χ→h phoneme correction.

        espeak-ng maps Mandarin "h" initial to χ (voiceless uvular fricative),
        but Kokoro's model produces natural Mandarin only with h (glottal).
        Verified via A/B comparison against Edge TTS neural voices.
        """
        phonemes = self._model.tokenizer.phonemize(text, "cmn")
        phonemes = phonemes.replace("χ", "h")
        samples, sample_rate = self._model.create(
            phonemes,
            voice=voice,
            lang="cmn",
            is_phonemes=True,
        )
        return self._wav_bytes(samples, sample_rate)

    def _wav_bytes(self, samples: np.ndarray, sample_rate: int) -> tuple[bytes, int]:
        pcm = np.clip(samples, -1.0, 1.0)
        pcm_i16 = (pcm * 32767.0).astype("<i2")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_i16.tobytes())
        return buf.getvalue(), sample_rate

    def get_voices(self) -> list[str]:
        if not self._ensure_loaded() or self._model is None:
            return []
        try:
            return self._model.get_voices()
        except Exception:
            return []
