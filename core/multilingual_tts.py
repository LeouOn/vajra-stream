"""
Multilingual TTS router — detects language per text segment and dispatches
to the best engine for each language.

Chinese text → SherpaTTSEngine (native G2P, best pronunciation)
English text → KokoroTTSEngine (natural neural voice, MIT+Apache)
Mixed text   → Split by language, synthesize each segment, concatenate audio

Usage:
    from core.multilingual_tts import MultilingualTTS
    mls = MultilingualTTS()
    if mls.available:
        wav_bytes, sr = mls.speak("May all beings be happy. 愿一切众生得安乐。")
"""

import io
import logging
import re
import wave

import numpy as np

logger = logging.getLogger(__name__)

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff]")
LATIN_RE = re.compile(r"[a-zA-Z]")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")
IAST_DIACRITIC_RE = re.compile(r"[āīūṃḥṅñṇṛṝḷḹśṣṭḍṅ]")
MANTRA_PHRASE_RE = re.compile(
    r"\b(?:"
    r"gate\s+gate|"  # Heart Sutra
    r"o[ṃm]\s+ma[ṇn]i\s+padme|"  # Om Mani Padme
    r"namo\s+(?:amit[aā]bh|śākyamuni)|"  # Namo
    r"tadyath[aā]|"  # Tadyatha
    r"sv[aā]h[aā]\s*\.?\s*$|"  # Svaha at end
    r"bhai[sṣ]ajya|"  # Medicine Buddha
    r"vajrasattva|"  # Vajrasattva
    r"tāre\s+tuttāre|"  # Green Tara
    r"tryambakam|"  # Mahamrityunjaya
    r"ga[yj]atr[iī]|"  # Gayatri
    r"o[ṃm]\s+(?:tāre|bhai[sṣ]ajy|vajra|ā[h]?)"  # Om + deity
    r")\b",
    re.IGNORECASE,
)
SENTENCE_SPLIT_RE = re.compile(r"([。！？；\.\!\?\n])")

SILENCE_GAP_SEC = 0.15
COMMON_SAMPLE_RATE = 24000


def _is_sanskrit(text: str) -> bool:
    """True if text contains IAST diacritics, Devanagari, or known mantra phrases."""
    if IAST_DIACRITIC_RE.search(text):
        return True
    if DEVANAGARI_RE.search(text):
        return True
    if MANTRA_PHRASE_RE.search(text):
        return True
    return False


def detect_language(text: str) -> str:
    """Return 'zh', 'en', 'sa' (Sanskrit), or 'mixed'."""
    has_cjk = bool(CJK_RE.search(text))
    has_latin = bool(LATIN_RE.search(text))
    if has_cjk and has_latin:
        return "mixed"
    if has_cjk:
        return "zh"
    if has_latin and _is_sanskrit(text):
        return "sa"
    return "en"


def split_by_language(text: str) -> list[tuple[str, str]]:
    """Split text into (language, segment) pairs at sentence boundaries.

    Languages: 'zh' (Chinese), 'en' (English), 'sa' (Sanskrit/Hindi).
    Adjacent segments of the same language are merged.
    """
    parts = SENTENCE_SPLIT_RE.split(text)
    chunks = []
    for i in range(0, len(parts) - 1, 2):
        chunk = parts[i] + parts[i + 1]
        if chunk.strip():
            chunks.append(chunk)
    if len(parts) % 2 == 1 and parts[-1].strip():
        chunks.append(parts[-1])

    if not chunks:
        return [("en", text)] if text.strip() else []

    segments: list[tuple[str, str]] = []
    for chunk in chunks:
        lang = detect_language(chunk)
        if lang == "mixed":
            lang = "zh" if CJK_RE.search(chunk[:10]) else ("sa" if _is_sanskrit(chunk) else "en")
        if segments and segments[-1][0] == lang:
            segments[-1] = (lang, segments[-1][1] + chunk)
        else:
            segments.append((lang, chunk))
    return segments


class MultilingualTTS:
    """Routes text segments to the best TTS engine per language."""

    def __init__(self):
        from core.kokoro_tts import KokoroTTSEngine
        from core.sherpa_tts import SherpaTTSEngine

        self.kokoro = KokoroTTSEngine()
        self.sherpa = SherpaTTSEngine()

    @property
    def available(self) -> bool:
        return self.kokoro.available or self.sherpa.available

    def speak(self, text: str) -> tuple[bytes, int] | None:
        """Synthesize multilingual text to a single WAV.

        Chinese segments → Sherpa (44.1 kHz, resampled to 24 kHz)
        English segments → Kokoro (24 kHz)
        Segments concatenated with 150ms silence gaps.
        """
        if not text.strip():
            return None

        segments = split_by_language(text)
        if not segments:
            return None

        audio_parts: list[np.ndarray] = []
        silence = np.zeros(int(COMMON_SAMPLE_RATE * SILENCE_GAP_SEC), dtype=np.float32)

        for lang, seg_text in segments:
            result = self._synthesize_segment(lang, seg_text)
            if result is None:
                logger.warning(f"TTS failed for {lang} segment: {seg_text[:30]}...")
                continue
            samples, sr = result
            if sr != COMMON_SAMPLE_RATE:
                samples = self._resample(samples, sr, COMMON_SAMPLE_RATE)
            audio_parts.append(samples)
            audio_parts.append(silence)

        if not audio_parts:
            return None

        full_audio = np.concatenate(audio_parts)
        pcm = np.clip(full_audio, -1.0, 1.0)
        pcm_i16 = (pcm * 32767.0).astype("<i2")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(COMMON_SAMPLE_RATE)
            wf.writeframes(pcm_i16.tobytes())
        return buf.getvalue(), COMMON_SAMPLE_RATE

    def _synthesize_segment(self, lang: str, text: str) -> tuple[np.ndarray, int] | None:
        """Route one segment to the appropriate engine."""
        if lang == "zh" and self.sherpa.available:
            result = self.sherpa.speak(text, speed=0.9, length_scale=1.1)
            if result:
                wav_bytes, sr = result
                return self._wav_to_samples(wav_bytes, sr)

        if lang == "sa":
            text = self._preprocess_sanskrit(text)

        if lang in ("en", "sa") and self.kokoro.available:
            result = self.kokoro.speak(text, voice="af_heart")
            if result:
                wav_bytes, sr = result
                return self._wav_to_samples(wav_bytes, sr)

        for engine, voice_kw in [(self.sherpa, {}), (self.kokoro, {"voice": "af_heart"})]:
            if engine.available:
                result = engine.speak(text, **voice_kw)
                if result:
                    wav_bytes, sr = result
                    return self._wav_to_samples(wav_bytes, sr)
        return None

    @staticmethod
    def _preprocess_sanskrit(text: str) -> str:
        """Convert IAST/Devanagari Sanskrit to TTS-friendly phonetics.

        Only fires on text already classified as Sanskrit (contains IAST
        diacritics, Devanagari, or known mantra phrases). Plain English
        words like 'gate' in non-Sanskrit segments are NOT affected.
        """
        try:
            from core.sanskrit_tts import preprocess_for_tts

            processed = preprocess_for_tts(text)
            if processed != text:
                logger.info(f"Sanskrit preprocessing: '{text[:40]}' -> '{processed[:40]}'")
            return processed
        except ImportError:
            logger.warning("core.sanskrit_tts not available, skipping Sanskrit preprocessing")
            return text

    @staticmethod
    def _wav_to_samples(wav_bytes: bytes, sr: int) -> tuple[np.ndarray, int]:
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
        return samples, sr

    @staticmethod
    def _resample(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple linear resampling — adequate for TTS audio."""
        if orig_sr == target_sr:
            return samples
        ratio = target_sr / orig_sr
        n_out = int(len(samples) * ratio)
        indices = np.linspace(0, len(samples) - 1, n_out)
        return np.interp(indices, np.arange(len(samples)), samples).astype(np.float32)
