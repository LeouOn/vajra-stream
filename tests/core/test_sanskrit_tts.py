"""
Tests for ``core.sanskrit_tts`` — IAST → TTS-friendly phonetic converter.

Covers the public API:
- ``iast_to_tts`` — algorithmic IAST → English phonetics conversion
- ``preprocess_for_tts`` — mixed-text pipeline (Devanagari safety net + IAST)
- ``get_mantra_tts_preset`` — curated preset lookup
- ``mantra_to_tts`` — preset-first with algorithmic fallback

Tests focus on:
- Seed syllables (oṃ, hūṃ, hrīṃ) converted to pronounceable forms
- Common mantra vocabulary (vajrasattva, bhaiṣajye, tathāgata)
- Endings (svāhā, -āya) produce correct syllable boundaries
- Preset database returns hand-tuned phonetics for the 10 common mantras
- Edge cases: empty, English-only, numbers pass through unchanged
"""

from __future__ import annotations

import pytest

from core.sanskrit_tts import (
    get_mantra_tts_preset,
    iast_to_tts,
    mantra_to_tts,
    preprocess_for_tts,
)

# ---------------------------------------------------------------------------
# 1. iast_to_tts — seed syllables
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_om_seed_syllable():
    """Oṃ → Ohm (the primal sound)."""
    assert "Ohm" in iast_to_tts("Oṃ")


@pytest.mark.unit
def test_hum_seed_syllable():
    """Hūṃ → Hoom (Vajrayana purifying syllable)."""
    result = iast_to_tts("Hūṃ")
    assert "Hoom" in result


@pytest.mark.unit
def test_hrim_seed_syllable():
    """Hrīṃ → Hreem (heart seed of Tara/deities)."""
    result = iast_to_tts("Hrīṃ")
    assert "Hreem" in result


@pytest.mark.unit
def test_klim_seed_syllable():
    """Klīṃ → Kleem (Krishna/Guru seed)."""
    result = iast_to_tts("Klīṃ")
    assert "Kleem" in result


# ---------------------------------------------------------------------------
# 2. iast_to_tts — full mantras
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_om_mani_padme_hum():
    """The most universal Buddhist mantra converts to pronounceable English."""
    result = iast_to_tts("Oṃ Maṇi Padme Hūṃ")
    assert "Ohm" in result
    assert "Muh-nee" in result or "Muhnee" in result
    assert "Hoom" in result


@pytest.mark.unit
def test_green_tara_mantra():
    """Green Tara's 10-syllable mantra."""
    result = iast_to_tts("Oṃ Tāre Tuttāre Ture Svāhā")
    assert "Ohm" in result
    assert "Tah-reh" in result
    assert "Svah-hah" in result


@pytest.mark.unit
def test_heart_sutra_mantra():
    """The perfection of wisdom mantra."""
    result = iast_to_tts("Gate Gate Pāragate Pārasaṃgate Bodhi Svāhā")
    assert "Guh-tay" in result or "Guh-tay" in result
    assert "Svah-hah" in result


@pytest.mark.unit
def test_vajrasattva_mantra():
    """Vajrasattva short purification mantra."""
    result = iast_to_tts("Oṃ Vajrasattva Hūṃ")
    assert "Ohm" in result
    assert "Vahj-ruh-saht-vuh" in result
    assert "Hoom" in result


@pytest.mark.unit
def test_medicine_buddha_mantra():
    """Medicine Buddha mantra with the compound 'mahābhaiṣajye'."""
    result = iast_to_tts("Tadyathā Oṃ Bhaiṣajye Bhaiṣajye Mahābhaiṣajye Rāja Samudgate Svāhā")
    assert "By-shahj-yay" in result
    assert "Muh-hah-by-shahj-yay" in result  # compound doesn't merge
    assert "Svah-hah" in result


@pytest.mark.unit
def test_shiva_mantra_with_aya_ending():
    """-āya ending produces 'ah-yuh' syllable boundary."""
    result = iast_to_tts("Oṃ Namaḥ Śivāya")
    assert "Ohm" in result
    assert "ah-yuh" in result  # -āya → ah-yuh


# ---------------------------------------------------------------------------
# 3. iast_to_tts — vocabulary terms
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_tathagata():
    """Tathāgata → Tah-tah-gah-tuh."""
    result = iast_to_tts("tathāgata")
    assert "Tah-tah-gah-tuh" in result or "tah-tah-gah-tuh" in result


@pytest.mark.unit
def test_bodhisattva():
    """Bodhisattva → Boh-dee-saht-vuh."""
    result = iast_to_tts("bodhisattva")
    assert "Boh-dee-saht-vuh" in result or "boh-dee-saht-vuh" in result


@pytest.mark.unit
def test_svaha_ending():
    """Svāhā → Svah-hah (offerings made to the fire)."""
    result = iast_to_tts("Svāhā")
    assert "Svah-hah" in result


# ---------------------------------------------------------------------------
# 4. preprocess_for_tts — mixed text
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_preprocess_mixed_text_preserves_english():
    """English text in a mixed string passes through unchanged."""
    text = "Recite 108 times: Oṃ Tāre Tuttāre Ture Svāhā. Then dedicate the merit."
    result = preprocess_for_tts(text)
    assert "Recite 108 times:" in result
    assert "Then dedicate the merit." in result
    assert "Ohm" in result
    assert "Svah-hah" in result


@pytest.mark.unit
def test_preprocess_numbers_preserved():
    """Numbers are not affected by IAST conversion."""
    result = preprocess_for_tts("Repeat 108 times for 7 days")
    assert "108" in result
    assert "7" in result


# ---------------------------------------------------------------------------
# 5. get_mantra_tts_preset — curated database
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_preset_om_mani_padme_hum():
    """The preset for Om Mani Padme Hum returns the hand-tuned version."""
    result = get_mantra_tts_preset("om_mani_padme_hum")
    assert result is not None
    assert "Om Mani Padme Hung" in result


@pytest.mark.unit
def test_preset_om_tare():
    """The preset for Green Tara returns the hand-tuned version."""
    result = get_mantra_tts_preset("om_tare")
    assert result is not None
    assert "Tah-reh" in result


@pytest.mark.unit
def test_preset_heart_sutra_mantra():
    """The preset for the Heart Sutra mantra returns the hand-tuned version."""
    result = get_mantra_tts_preset("heart_sutra_mantra")
    assert result is not None
    assert "Gah-tay" in result


@pytest.mark.unit
def test_preset_nonexistent_returns_none():
    """Unknown preset keys return None (caller falls back to algorithmic)."""
    assert get_mantra_tts_preset("nonexistent_mantra") is None


# ---------------------------------------------------------------------------
# 6. mantra_to_tts — preset-first with fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mantra_to_tts_uses_preset_when_available():
    """When a preset key is provided AND exists, the preset is used."""
    result = mantra_to_tts("Oṃ Maṇi Padme Hūṃ", preset_key="om_mani_padme_hum")
    assert "Om Mani Padme Hung" in result  # preset version, not algorithmic


@pytest.mark.unit
def test_mantra_to_tts_falls_back_when_no_preset():
    """Without a preset key, the algorithmic conversion runs."""
    result = mantra_to_tts("Oṃ Vajrasattva Hūṃ")
    assert "Ohm" in result
    assert "Hoom" in result


@pytest.mark.unit
def test_mantra_to_tts_falls_back_when_preset_not_found():
    """When the preset key doesn't exist, falls back to algorithmic."""
    result = mantra_to_tts("Oṃ Maṇi Padme Hūṃ", preset_key="nonexistent")
    assert "Ohm" in result
    assert "Hoom" in result


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_empty_string():
    """Empty string returns empty."""
    assert iast_to_tts("") == ""
    assert preprocess_for_tts("") == ""


@pytest.mark.unit
def test_english_only_unchanged():
    """Pure English text passes through unchanged."""
    text = "Hello world, this is a test"
    assert iast_to_tts(text) == text


@pytest.mark.unit
def test_numbers_only_unchanged():
    """Pure numeric text passes through unchanged."""
    assert iast_to_tts("108 7 3") == "108 7 3"


@pytest.mark.unit
def test_capitalization_preserved():
    """Leading capital letters are preserved in the output."""
    result = iast_to_tts("Oṃ")
    assert result[0].isupper()  # "Ohm" not "ohm"
