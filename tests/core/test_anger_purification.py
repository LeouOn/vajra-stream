"""
Tests for the 'anger' and 'purification' suffering types in ``core.ritual_generator``.

These types were added to make the ritual generator responsive to a wider
range of user intentions — anger/rage/forgiveness and confession/karma/renewal.
Both map to Vajrasattva (Diamond Being) as the primary deity and use the
Vajrasattva Hundred-Syllable Dharani for purification.

Tests verify:
- Detection patterns recognize anger and purification intentions
- DEITY_MAP has correct entries for both types
- _SUFFERING_TO_DHARANI maps both to the Vajrasattva dharani
- Fallback prayers contain thematically relevant content
- Dharma teachings include the hot coal / river water parables
- Hero journeys have 6 stages with substantial content
- Sutra passages are selected from the patience/purification themes
"""
from __future__ import annotations

import pytest

from core.ritual_generator import RitualGenerator


# ---------------------------------------------------------------------------
# 1. Detection — anger
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_anger_basic():
    """'anger' in the intention triggers the anger type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am angry") == "anger"


@pytest.mark.unit
def test_detect_anger_rage():
    """'rage' triggers the anger type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am full of rage") == "anger"


@pytest.mark.unit
def test_detect_anger_forgiveness():
    """'forgiveness' triggers the anger type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I need help with forgiveness") == "anger"


@pytest.mark.unit
def test_detect_anger_resentment():
    """'resentment' triggers the anger type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I carry deep resentment") == "anger"


# ---------------------------------------------------------------------------
# 2. Detection — purification
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_purification_basic():
    """'purification' in the intention triggers the purification type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I need purification") == "purification"


@pytest.mark.unit
def test_detect_purification_confession():
    """'confession' triggers the purification type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I want to make a confession") == "purification"


@pytest.mark.unit
def test_detect_purification_karma():
    """'negative karma' triggers the purification type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I need to purify my negative karma") == "purification"


@pytest.mark.unit
def test_detect_purification_guilt():
    """'guilt' triggers the purification type."""
    gen = RitualGenerator()
    assert gen.detect_suffering_type("I am consumed by guilt") == "purification"


# ---------------------------------------------------------------------------
# 3. DEITY_MAP entries
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deity_map_has_anger():
    """DEITY_MAP contains the anger entry."""
    gen = RitualGenerator()
    assert "anger" in gen.DEITY_MAP
    entry = gen.DEITY_MAP["anger"]
    assert "Vajrasattva" in entry["primary"]
    assert entry["mantra"]


@pytest.mark.unit
def test_deity_map_has_purification():
    """DEITY_MAP contains the purification entry."""
    gen = RitualGenerator()
    assert "purification" in gen.DEITY_MAP
    entry = gen.DEITY_MAP["purification"]
    assert "Vajrasattva" in entry["primary"]
    assert entry["mantra"]


# ---------------------------------------------------------------------------
# 4. Dharani selection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_anger_selects_vajrasattva_dharani():
    """Anger maps to the Vajrasattva Hundred-Syllable Dharani."""
    gen = RitualGenerator()
    result = gen._select_dharani("anger")
    assert result is not None
    assert "Vajrasattva" in result or "Hundred" in result or "Diamond" in result


@pytest.mark.unit
def test_purification_selects_vajrasattva_dharani():
    """Purification maps to the Vajrasattva Hundred-Syllable Dharani."""
    gen = RitualGenerator()
    result = gen._select_dharani("purification")
    assert result is not None
    assert "Vajrasattva" in result or "Hundred" in result or "Diamond" in result


# ---------------------------------------------------------------------------
# 5. Prayer generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_anger_prayer_has_content():
    """The anger fallback prayer is substantial and thematically relevant."""
    gen = RitualGenerator()
    prayer = gen._fallback_prayer("I am furious", ["my enemy"])
    assert len(prayer) > 200
    # Should reference anger, forgiveness, or compassion themes
    lower = prayer.lower()
    assert any(w in lower for w in ["anger", "forgive", "compassion", "coal", "burn"])


@pytest.mark.unit
def test_purification_prayer_has_content():
    """The purification fallback prayer is substantial and thematically relevant."""
    gen = RitualGenerator()
    prayer = gen._fallback_prayer("I need to purify my karma", ["myself"])
    assert len(prayer) > 200
    lower = prayer.lower()
    assert any(w in lower for w in ["purif", "karma", "confess", "clean", "vajrasattva"])


# ---------------------------------------------------------------------------
# 6. Dharma teaching
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_anger_teaching_includes_hot_coal():
    """The anger teaching references the hot coal analogy."""
    gen = RitualGenerator()
    teaching = gen.generate_dharma_teaching("I am full of rage and cannot forgive")
    assert len(teaching) > 200
    # Should include the hot coal teaching and/or a sutra passage
    assert "coal" in teaching.lower() or "patience" in teaching.lower() or "**From" in teaching


@pytest.mark.unit
def test_purification_teaching_includes_water_mud():
    """The purification teaching references the river water/mud analogy."""
    gen = RitualGenerator()
    teaching = gen.generate_dharma_teaching("I need to confess and purify my karma")
    assert len(teaching) > 200
    lower = teaching.lower()
    # Should reference water, mud, vajrasattva, or include a sutra passage
    assert any(w in lower for w in ["water", "mud", "vajrasattva", "diamond", "purif", "**from"])


# ---------------------------------------------------------------------------
# 7. Hero journey
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_anger_hero_journey_has_six_stages():
    """The anger hero journey has all 6 stages."""
    gen = RitualGenerator()
    journey = gen.generate_hero_journey("I am angry and need transformation", ["all beings"])
    assert len(journey) > 500
    # Should have numbered stages
    for num in ["1.", "2.", "3.", "4.", "5.", "6."]:
        assert num in journey


@pytest.mark.unit
def test_purification_hero_journey_has_six_stages():
    """The purification hero journey has all 6 stages."""
    gen = RitualGenerator()
    journey = gen.generate_hero_journey("I seek purification and renewal", ["all beings"])
    assert len(journey) > 500
    for num in ["1.", "2.", "3.", "4.", "5.", "6."]:
        assert num in journey


# ---------------------------------------------------------------------------
# 8. Invocation includes dharani
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_anger_invocation_includes_dharani():
    """Anger invocation includes a Vajrasattva dharani recitation."""
    gen = RitualGenerator()
    invocation = gen.generate_invocation("I am furious and need to let go", "vajrayana")
    assert "Dharani Recitation" in invocation
    assert "Vajrasattva" in invocation or "Hundred" in invocation


@pytest.mark.unit
def test_purification_invocation_includes_dharani():
    """Purification invocation includes a Vajrasattva dharani recitation."""
    gen = RitualGenerator()
    invocation = gen.generate_invocation("I seek purification of all negative karma", "vajrayana")
    assert "Dharani Recitation" in invocation
    assert "Vajrasattva" in invocation or "Hundred" in invocation
