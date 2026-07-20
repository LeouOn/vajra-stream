"""
SherpaTTSEngine — local CPU TTS via sherpa-onnx (VITS MeloTTS zh_en).

Native Chinese G2P with proper lexicon — no espeak-ng phoneme quirks.
44.1 kHz output. Apache-2.0 licensed.

Usage:
    engine = SherpaTTSEngine()
    if engine.available:
        wav_bytes, sample_rate = engine.speak("愿一切众生得安乐")
"""

import io
import logging
import os
import wave

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = os.path.join("models", "sherpa", "vits-melo-tts-zh_en")


class SherpaTTSEngine:
    """Local CPU TTS via sherpa-onnx VITS MeloTTS."""

    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR):
        self.model_dir = model_dir
        self._tts = None
        self._loaded = False

    @property
    def available(self) -> bool:
        try:
            import sherpa_onnx  # noqa: F401
        except ImportError:
            return False
        return os.path.isfile(os.path.join(self.model_dir, "model.onnx"))

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._tts is not None
        self._loaded = True
        if not self.available:
            return False
        try:
            import sherpa_onnx

            base = self.model_dir
            config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=os.path.join(base, "model.onnx"),
                        lexicon=os.path.join(base, "lexicon.txt"),
                        tokens=os.path.join(base, "tokens.txt"),
                        dict_dir=os.path.join(base, "dict"),
                    ),
                    num_threads=4,
                    provider="cpu",
                ),
                rule_fsts=",".join(
                    os.path.join(base, f)
                    for f in ("date.fst", "number.fst", "phone.fst")
                    if os.path.isfile(os.path.join(base, f))
                ),
                max_num_sentences=1,
            )
            self._tts = sherpa_onnx.OfflineTts(config)
            logger.info(f"Sherpa TTS loaded: {base}")
            return True
        except Exception as e:
            logger.error(f"Failed to load Sherpa TTS: {e}")
            self._tts = None
            return False

    def speak(self, text: str, speed: float = 1.0, length_scale: float = 1.0) -> tuple[bytes, int] | None:
        """Synthesize text to WAV bytes (PCM 16-bit, 44.1 kHz).

        Returns (wav_bytes, sample_rate) or None on failure.
        """
        if not text.strip():
            return None
        if not self._ensure_loaded() or self._tts is None:
            return None
        try:
            audio_obj = self._tts.generate(text, sid=0, speed=speed)
            samples = np.array(audio_obj.samples, dtype=np.float32)
            sr = audio_obj.sample_rate
            pcm = np.clip(samples, -1.0, 1.0)
            pcm_i16 = (pcm * 32767.0).astype("<i2")
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm_i16.tobytes())
            return buf.getvalue(), sr
        except Exception as e:
            logger.error(f"Sherpa synthesis failed: {e}")
            return None
