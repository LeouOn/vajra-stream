"""
Sanskrit IAST → TTS-friendly phonetic converter.

Converts IAST transliteration of Sanskrit into simplified English phonetics
that Edge/Qwen TTS engines pronounce correctly. Applied BEFORE passing
mantra/sutra text to the TTS pipeline.

Why: TTS engines (Edge, Qwen, gTTS) cannot read Devanagari and mispronounce
IAST diacritics (e.g., "hūṃ" → "hyoom" instead of "hoom"). This module
normalizes both to syllables the engines already know.

Pipeline:
    mantras.json ("sanskrit_iast": "Oṃ Maṇi Padme Hūṃ")
        ↓ iast_to_tts()
    "Ohm Muh-nee Pud-may Hoom"
        ↓ tts_provider.speak()
    audio file

Usage:
    from core.sanskrit_tts import iast_to_tts, preprocess_for_tts

    phonetic = iast_to_tts("Oṃ Maṇi Padme Hūṃ")
    # → "Ohm Muh-nee Pud-may Hoom"

    clean = preprocess_for_tts("Recite: Oṃ Tāre Tuttāre Ture Svāhā 7 times")
    # → "Recite: Ohm Tah-reh Too-tah-reh Too-reh Svah-hah 7 times"

For the ~10 most common mantras, a hand-tuned preset exists in
knowledge/sanskrit_pronunciation.json (common_mantras_tts_ready). The
function iast_to_tts() checks that preset first, then falls back to the
algorithmic conversion.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

__all__ = [
    "iast_to_tts",
    "preprocess_for_tts",
    "get_mantra_tts_preset",
    "mantra_to_tts",
]


# ---------------------------------------------------------------------------
# Special compound sounds — checked FIRST (longest-match priority)
# ---------------------------------------------------------------------------
# These override character-by-character conversion because they are either:
#   - Multi-character seed syllables (oṃ, hrīṃ, klīṃ)
#   - Words whose TTS pronunciation is non-obvious (bhaiṣajye, tathāgata)
#   - Endings that must be pronounced consistently (svāhā, hūṃ, phaṭ)
#
# Format: lowercase IAST source → English-phonetic replacement.
# Matching is case-insensitive on the source side; replacement preserves
# the capitalization of the input first letter where practical.
_SPECIAL_COMPOUNDS: dict[str, str] = {
    # --- Seed syllables (bīja) ---
    "oṃ": "Ohm",
    "aum": "Ohm",
    "hrīṃ": "Hreem",
    "hrī": "Hree",
    "klīṃ": "Kleem",
    "śrīṃ": "Shreem",
    "śrī": "Shree",
    "aiṃ": "Aym",
    "aim": "Aym",
    "krīṃ": "Kreem",
    "strīṃ": "Streem",
    "gam": "Gum",
    "gaṃ": "Gum",
    # --- Common endings ---
    "hūṃ": "Hoom",
    "huṃ": "Hoom",
    "svāhā": "Svah-hah",
    "svaha": "Svah-hah",
    "soha": "Soh-hah",
    "svāhā.": "Svah-hah.",
    "phaṭ": "Phat",
    # --- Common deity / dharma terms ---
    "bodhi": "Boh-dee",
    "buddha": "Boo-dah",
    "buddhāya": "Boo-dhah-yuh",
    # Common dative/locative endings (preserve syllable boundary for TTS)
    "āya": "ah-yuh",
    "āye": "ah-yay",
    "āni": "ah-nee",
    "bhaiṣajye": "By-shahj-yay",
    "bhaiṣajya": "By-shahj-yuh",
    "mahābhaiṣajye": "Muh-hah-by-shahj-yay",
    "mahābhaiṣajya": "Muh-hah-by-shahj-yuh",
    "vaiḍūrya": "Vye-doo-ryuh",
    "tathāgatāya": "Tah-tah-gah-tah-yuh",
    "tathāgata": "Tah-tah-gah-tuh",
    "vajrasattva": "Vahj-ruh-saht-vuh",
    "vajrasattvāya": "Vahj-ruh-saht-vah-yuh",
    "vajra": "Vahj-ruh",
    "padme": "Pud-may",
    "padma": "Pud-muh",
    "maṇi": "Muh-nee",
    "avalokiteśvara": "Ah-vuh-loh-kee-tay-shvuh-ruh",
    "avalokitasvara": "Ah-vuh-loh-kee-tuh-svuh-ruh",
    "bodhisattva": "Boh-dee-saht-vuh",
    "bodhisattvāya": "Boh-dee-saht-vah-yuh",
    "mahāsattvāya": "Muh-hah-saht-vah-yuh",
    "mahāsattva": "Muh-hah-saht-vuh",
    "mahākāruṇikāya": "Muh-hah-kah-roo-nee-kah-yuh",
    "prajñā": "Pruhj-nyah",
    "prajñāpāramitā": "Pruhj-nyah-pah-ruh-mee-tah",
    "pāramitā": "Pah-ruh-mee-tah",
    "dhyāna": "Dhyah-nuh",
    "tadyathā": "Tuhd-yuh-tah-hah",
    "samudgate": "Suh-mood-guh-tay",
    "rāja": "Rah-juh",
    "rājāya": "Rah-jah-yuh",
    "mahā": "Muh-hah",
    "dzambhala": "Jahm-bhuh-luh",
    "jambhala": "Juhm-bhuh-luh",
    "dzaliṃ": "Juh-leem",
    "dzali": "Juh-lee",
    "dzale": "Juh-lay",
    "gate": "Guh-tay",
    "pāragate": "Pah-ruh-guh-tay",
    "pārasaṃgate": "Pah-ruh-suhm-guh-tay",
    "parasamgate": "Pah-ruh-suhm-guh-tay",
    "amitābhāya": "Ah-mee-tah-bhah-yuh",
    "amitābha": "Ah-mee-tah-bhuh",
    "namo": "Nuh-moh",
    "namaḥ": "Nuh-muh",
    "namah": "Nuh-muh",
    "namo'": "Nuh-moh ",  # Handle avagraha (apostrophe) sandhi
    "śānti": "Shahn-tee",
    "śāntiḥ": "Shahn-teeh",
    # --- Mrityunjaya mantra vocabulary ---
    "tryambakaṃ": "Try-uhm-buh-kum",
    "tryambakam": "Try-uhm-buh-kum",
    "yajāmahe": "Yuh-jah-muh-hay",
    "sugandhiṃ": "Soo-guhn-deem",
    "sugandhim": "Soo-guhn-deem",
    "puṣṭivardhanam": "Push-tee-vurd-huh-num",
    "pushtivardhanam": "Push-tee-vurd-huh-num",
    "ururvārukamiva": "Oor-oor-vah-roo-kuh-mee-vuh",
    "urvārukamiva": "Oor-vah-roo-kuh-mee-vuh",
    "bandhanān": "Buhn-dhuh-nahn",
    "bandhanan": "Buhn-dhuh-nahn",
    "mṛtyor": "Mree-tyor",
    "mrityor": "Mree-tyor",
    "mukṣīya": "Mook-shee-yuh",
    "mukshiya": "Mook-shee-yuh",
    "māmṛtāt": "Mahm-ree-taht",
    "mamritat": "Mahm-ree-taht",
    # --- Green Tara ---
    "tāre": "Tah-reh",
    "tare": "Tah-reh",
    "tuttāre": "Too-tah-reh",
    "tuttare": "Too-tah-reh",
    "ture": "Too-reh",
    # --- Manjushri ---
    "dhīḥ": "Dhee-hi",
    "dhīh": "Dhee-hi",
    # --- White Tara ---
    "āyuḥ": "Ah-yooh",
    "ayuh": "Ah-yooh",
    "puṇye": "Poony-yay",
    "punye": "Poony-yay",
    "jñāna": "Gyah-nuh",
    "jnana": "Gyah-nuh",
    "pūrti": "Poor-tee",
    "purti": "Poor-tee",
    "kuru": "Koo-roo",
    "mama": "Muh-muh",
    # --- Gayatri vocabulary ---
    "bhūr": "Bhoor",
    "bhur": "Bhoor",
    "bhuvaḥ": "Bhoo-vuh",
    "bhuvas": "Bhoo-vuh",
    "svaḥ": "Svuh",
    "svah": "Svuh",
    "tatsavitur": "Tuht-suh-vee-toor",
    "vareṇyaṃ": "Vuh-ren-yum",
    "varenyam": "Vuh-ren-yum",
    "bhargo": "Bhur-goh",
    "devasya": "Day-vuh-syuh",
    "dhīmahi": "Dhee-muh-hee",
    "dhimahi": "Dhee-muh-hee",
    "dhiyo": "Dhee-yoh",
    "yo": "yoh",
    "naḥ": "nuh",
    "nah": "nuh",
    "pracodayāt": "Pruh-choh-dyah-yuht",
    "prachodayat": "Pruh-choh-dyah-yuht",
    # --- Heart Sutra / Prajnaparamita ---
    "paragate": "Pah-ruh-guh-tay",
    "parasangate": "Pah-ruh-suhn-guh-tay",
}


# ---------------------------------------------------------------------------
# IAST character-level mappings (applied AFTER special compounds)
# ---------------------------------------------------------------------------
_VOWELS_LONG: dict[str, str] = {
    "ā": "ah",
    "ī": "ee",
    "ū": "oo",
    "ṛ": "ri",
    "ṝ": "ree",
    "ḷ": "li",
}

_VOWELS_DIPHTHONGS: dict[str, str] = {
    "ai": "eye",
    "au": "ow",
}

# Note: standalone "e" and "o" are tricky. In IAST they are LONG vowels
# (like "ay" and "oh"). But replacing every "e" with "ay" would corrupt
# English text. We only apply this within clearly-Sanskrit runs.
# For simplicity, we apply "e" → "ay" only inside Sanskrit tokens (detected
# by presence of other IAST diacritics in the same word).

_NASALS_AND_ASPIRATES: dict[str, str] = {
    "ṃ": "m",   # anusvara (simplified; special compounds handle seed syllables)
    "ḥ": "h",   # visarga  (simplified echo; special compounds handle endings)
    "ṅ": "ng",
    "ñ": "ny",
    "ṇ": "n",   # retroflex n → dental (TTS can't distinguish)
    "ś": "sh",
    "ṣ": "sh",
}

_CONSONANT_RETROFLEX: dict[str, str] = {
    "ṭ": "t",
    "ḍ": "d",
}

# Standalone e/o mapping for Sanskrit tokens only
_VOWEL_E_O: dict[str, str] = {
    "e": "ay",
    "o": "oh",
}


# ---------------------------------------------------------------------------
# Compiled regex (built once, cached)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _build_regex() -> tuple[re.Pattern[str], dict[str, str]]:
    """Build a single regex that matches any known IAST sequence.

    Returns the compiled pattern and the lowercase-source → replacement map.
    Ordering: special compounds first (they're longest), then vowels,
    then consonants.
    """
    # Merge maps; special compounds dominate (already longest).
    merged: dict[str, str] = {}
    merged.update(_NASALS_AND_ASPIRATES)
    merged.update(_CONSONANT_RETROFLEX)
    merged.update(_VOWELS_LONG)
    merged.update(_VOWELS_DIPHTHONGS)
    merged.update(_SPECIAL_COMPOUNDS)  # applied last so it overrides shorter keys

    # Sort by length descending so "ai" wins over "a", "svāhā" wins over "sv"
    ordered = sorted(merged.items(), key=lambda kv: -len(kv[0]))
    pattern = re.compile(
        "|".join(re.escape(src) for src, _ in ordered),
        flags=re.IGNORECASE,
    )
    return pattern, merged


# ---------------------------------------------------------------------------
# Devanagari → IAST (simple mapping for the common cases)
# ---------------------------------------------------------------------------
# Used by preprocess_for_tts() when Devanagari slips through. This is NOT
# a complete transliteration table — the common_mantras database already
# stores IAST. This is a safety net for stray Devanagari characters.
_DEVANAGARI_TO_IAST: dict[str, str] = {
    "अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ṅ",
    "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ञ": "ñ",
    "ट": "ṭ", "ठ": "ṭh", "ड": "ḍ", "ढ": "ḍh", "ण": "ṇ",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "ś",
    "ष": "ṣ", "स": "s", "ह": "h",
    "ं": "ṃ", "ः": "ḥ", "ॐ": "Oṃ",
}


def _devanagari_to_iast(text: str) -> str:
    """Replace common Devanagari characters with their IAST equivalents.

    This is a safety-net simplification. It does NOT handle conjunct
    consonants (क + ष → क्ष) or vowel signs (क + ा → का). It catches the
    common standalone characters that slip into mixed-language text.
    """
    if not any(0x0900 <= ord(c) <= 0x097F for c in text):
        return text  # No Devanagari — skip
    return "".join(_DEVANAGARI_TO_IAST.get(c, c) for c in text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def iast_to_tts(text: str) -> str:
    """Convert IAST Sanskrit text to TTS-friendly English phonetics.

    Special compounds (oṃ, hūṃ, svāhā, etc.) and known mantra vocabulary
    are replaced with hand-tuned syllables. Remaining IAST diacritics fall
    through to character-level conversion.

    Args:
        text: IAST transliteration (e.g., "Oṃ Maṇi Padme Hūṃ").

    Returns:
        English-phonetic string suitable for Edge/Qwen TTS engines
        (e.g., "Ohm Muh-nee Pud-may Hoom").

    Notes:
        - Case-insensitive matching; replacements preserve word boundaries.
        - English text passes through unchanged (only IAST diacritics are
          replaced, so "Gate" still has its capital G).
        - For best results with preset mantras, use get_mantra_tts_preset().
    """
    if not text:
        return text

    pattern, mapping = _build_regex()

    # We need case-insensitive lookup but case-preserving replacement.
    # The regex is IGNORECASE; for the replacement we lowercase the match
    # and look up the mapping. For ASCII-only inputs like "Om" (vs "Oṃ"),
    # we capitalize the first letter of the replacement if the original
    # started with uppercase.
    def replace(match: re.Match[str]) -> str:
        src = match.group(0)
        repl = mapping.get(src.lower())
        if repl is None:
            return src  # Should not happen (regex only matches known keys)
        # Preserve leading capitalization of the source token
        if src and src[0].isupper() and repl and repl[0].islower():
            repl = repl[0].upper() + repl[1:]
        return repl

    return pattern.sub(replace, text)


def preprocess_for_tts(text: str) -> str:
    """Auto-detect Sanskrit in mixed text and convert it for TTS.

    Use this when a single string may contain both English and Sanskrit —
    e.g., a ritual line: "Recite: Oṃ Tāre Tuttāre Ture Svāhā 7 times".

    Pipeline:
        1. Convert stray Devanagari characters to IAST (safety net).
        2. Convert IAST diacritics to English phonetics.
        3. Leave English / digits / punctuation unchanged.

    Args:
        text: Mixed text possibly containing IAST or Devanagari Sanskrit.

    Returns:
        Text safe to pass directly to any TTS engine.
    """
    if not text:
        return text
    # Step 1: Devanagari → IAST (only if Devanagari is present)
    step1 = _devanagari_to_iast(text)
    # Step 2: IAST → English phonetics
    return iast_to_tts(step1)


# ---------------------------------------------------------------------------
# Preset lookup (curated TTS-ready mantras)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_pronunciation_db() -> dict:
    """Load the curated TTS-ready mantra database from knowledge/.

    Returns the parsed JSON dict (empty on missing/corrupt file).
    The file lives at knowledge/sanskrit_pronunciation.json.
    """
    path = Path(__file__).resolve().parent.parent / "knowledge" / "sanskrit_pronunciation.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_mantra_tts_preset(mantra_key: str) -> str | None:
    """Look up a hand-tuned TTS-friendly version of a common mantra.

    Args:
        mantra_key: Key from sanskrit_pronunciation.json's
            ``common_mantras_tts_ready`` block
            (e.g., "om_mani_padme_hum", "om_tare", "heart_sutra_mantra").

    Returns:
        TTS-friendly string, or None if the mantra isn't in the preset DB.
        Callers should fall back to iast_to_tts() for unknown mantras.
    """
    data = _load_pronunciation_db()
    entry = data.get("common_mantras_tts_ready", {}).get(mantra_key)
    if entry is None:
        return None
    return entry.get("tts_friendly")


def mantra_to_tts(
    iast_text: str,
    preset_key: str | None = None,
) -> str:
    """Convert a mantra's IAST text to TTS-friendly phonetics.

    Convenience wrapper. If ``preset_key`` is provided AND a preset exists
    for it, return the hand-tuned preset (best quality). Otherwise fall
    back to the algorithmic iast_to_tts() conversion.

    Args:
        iast_text: Sanskrit in IAST transliteration.
        preset_key: Optional key into the curated preset database
            (e.g., "om_mani_padme_hum").

    Returns:
        TTS-friendly string ready for the TTS engine.
    """
    if preset_key:
        preset = get_mantra_tts_preset(preset_key)
        if preset:
            return preset
    return iast_to_tts(iast_text)
