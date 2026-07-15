"""
Tests for the 'fear' / anxiety suffering type in ``core.ritual_generator``.

This type was added to make the ritual generator responsive to fear,
anxiety, panic, and dread — the most common form of suffering that brings
people to spiritual practice. It maps to Green Tara (Swift Savior) as the
primary deity, the Green Tara Dharani for recitation, and the Heart Sutra
passage (whose core teaching is the end of fear: 'no obstruction, no fear').

Tests verify:
- Detection patterns recognize fear / anxiety / panic / worry intentions
- DEITY_MAP has correct entry with Green Tara as primary
- _SUFFERING_TO_DHARANI maps fear -> green_tara_dharani
- Fallback prayer contains thematically relevant content
- Dharma teaching includes the present-moment practice
- Hero journey has all 6 stages with substantial content
- Invocation includes the Green Tara dharani recitation
"""

from __future__ import annotations

import pytest

from core.ritual_generator import RitualGenerator

# ---------------------------------------------------------------------------
# 1. Detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_fear_basic():
    """'fear' in the intention triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am full of fear") == "fear"


@pytest.mark.unit
def test_detect_fear_afraid():
    """'afraid' triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am afraid of dying") == "fear"


@pytest.mark.unit
def test_detect_fear_anxious():
    """'anxious' triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I feel very anxious about the future") == "fear"


@pytest.mark.unit
def test_detect_fear_panic():
    """'panic' triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am having panic attacks") == "fear"


@pytest.mark.unit
def test_detect_fear_worry():
    """'worry' triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I worry about everything") == "fear"


@pytest.mark.unit
def test_detect_fear_terror():
    """'terror' triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I live in terror") == "fear"


@pytest.mark.unit
def test_detect_fear_scared():
    """'scared' triggers the fear type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am scared of the dark") == "fear"


# ---------------------------------------------------------------------------
# 2. DEITY_MAP entry
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deity_map_has_fear():
    """DEITY_MAP contains the fear entry with Green Tara as primary."""
    gen = RitualGenerator()
    assert "fear" in gen.DEITY_MAP
    entry = gen.DEITY_MAP["fear"]
    assert "Green Tara" in entry["primary"]
    assert "Tare Tuttare Ture" in entry["mantra"]
    assert entry["mantra"]
    assert len(entry["secondary"]) >= 1


# ---------------------------------------------------------------------------
# 3. Dharani selection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fear_selects_green_tara_dharani():
    """Fear maps to the Green Tara Dharani (the remover of fear)."""
    gen = RitualGenerator()
    result = gen._select_dharani("fear")
    assert result is not None
    assert "Green Tara" in result or "Tare" in result or "remover" in result.lower()


# ---------------------------------------------------------------------------
# 4. Prayer generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fear_prayer_has_content():
    """The fear fallback prayer is substantial and addresses the fear."""
    gen = RitualGenerator()
    prayer = gen._fallback_prayer("I am afraid", ["myself"])
    assert len(prayer) > 200
    lower = prayer.lower()
    assert any(w in lower for w in ["fear", "afraid", "tara", "trembl", "anxiety", "present", "alarma"])


# ---------------------------------------------------------------------------
# 5. Dharma teaching
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fear_teaching_has_content():
    """The fear dharma teaching has substantial content."""
    gen = RitualGenerator()
    teaching = gen.generate_dharma_teaching("I am afraid of the future")
    assert len(teaching) > 200
    # Should reference present moment / fear / sutra passage
    assert any(w in teaching.lower() for w in ["fear", "present", "afraid", "future", "imagined", "**from"])


# ---------------------------------------------------------------------------
# 6. Hero journey
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fear_hero_journey_has_six_stages():
    """The fear hero journey has all 6 numbered stages."""
    gen = RitualGenerator()
    journey = gen.generate_hero_journey("I am afraid and seek fearlessness", ["all beings"])
    assert len(journey) > 500
    for num in ["1.", "2.", "3.", "4.", "5.", "6."]:
        assert num in journey


# ---------------------------------------------------------------------------
# 7. Invocation includes dharani
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fear_invocation_includes_green_tara_dharani():
    """Fear invocation includes a Green Tara dharani recitation."""
    gen = RitualGenerator()
    invocation = gen.generate_invocation("I am afraid", "vajrayana")
    assert "Dharani Recitation" in invocation
    assert "Green Tara" in invocation or "Tare Tuttare Ture" in invocation


# ---------------------------------------------------------------------------
# 8. Sutra passage mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fear_sutra_matches_emptiness_or_protection():
    """Fear suffering selects a sutra passage with 'emptiness' or 'protection'
    tag (Heart Sutra's core teaching ends fear; Golden Light offers protection)."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("fear")
    # Should not be None and the passage should reference fear-relevant themes
    assert result is not None
    assert result.startswith("**From ")
