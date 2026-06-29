"""
Tests for sutra passage selection in ``core.ritual_generator``.

Covers:
- ``_load_sutra_db`` — module-level cached JSON loader
- ``RitualGenerator._select_sutra_passage`` — theme-based passage selection
- ``RitualGenerator._with_sutra`` — helper that appends a passage to a teaching
- ``RitualGenerator.generate_dharma_teaching`` — sutra passage included in output

Tests focus on:
- The sutra DB loads from knowledge/sutra_passages.json with expected passages
- Each suffering type maps to a thematically relevant sutra (earthquake→protection,
  illness→healing, dedication_of_endeavors→loss/dedication, death→impermanence)
- The _with_sutra helper appends when a match exists and is a no-op when it doesn't
- generate_dharma_teaching includes a "**From ... Sutra" header in its output
"""
from __future__ import annotations

import pytest

from core.ritual_generator import RitualGenerator, _load_sutra_db


# ---------------------------------------------------------------------------
# 1. _load_sutra_db — module-level loader
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sutra_db_loads():
    """The sutra database loads from knowledge/sutra_passages.json."""
    db = _load_sutra_db()
    assert isinstance(db, dict)
    assert "sutra_passages" in db
    passages = db["sutra_passages"]
    assert len(passages) >= 8  # we have 10 passages


@pytest.mark.unit
def test_sutra_db_has_expected_passages():
    """Known passage IDs are present in the database."""
    db = _load_sutra_db()
    passages = db["sutra_passages"]
    ids = {p["id"] for p in passages}
    expected_ids = {
        "heart_sutra_essence",
        "diamond_impermanence",
        "sanghata_loss_transformation",
        "golden_light_protection",
        "vimalakirti_sickness",
    }
    assert expected_ids.issubset(ids)


@pytest.mark.unit
def test_sutra_db_cached():
    """Repeated calls return the same cached object (lru_cache)."""
    db1 = _load_sutra_db()
    db2 = _load_sutra_db()
    assert db1 is db2  # same object reference (cached)


# ---------------------------------------------------------------------------
# 2. _select_sutra_passage — theme-based selection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_earthquake_selects_protection_passage():
    """Earthquake suffering maps to the Golden Light Sutra (protection)."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("earthquake")
    assert result is not None
    assert "Golden Light" in result or "protection" in result.lower()


@pytest.mark.unit
def test_illness_selects_healing_passage():
    """Illness suffering maps to the Vimalakirti Sutra (healing)."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("illness")
    assert result is not None
    assert "Vimalakirti" in result or "healing" in result.lower() or "sick" in result.lower()


@pytest.mark.unit
def test_dedication_selects_loss_or_dedication_passage():
    """Dedication of endeavors maps to Sanghata (loss/dedication/wealth)."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("dedication_of_endeavors")
    assert result is not None
    assert "Sanghata" in result or "Diamond" in result


@pytest.mark.unit
def test_death_selects_impermanence_passage():
    """Death suffering maps to Diamond Sutra (impermanence/emptiness)."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("death")
    assert result is not None
    assert "Diamond" in result or "Heart" in result  # impermanence or emptiness


@pytest.mark.unit
def test_universal_selects_dedication_or_emptiness():
    """Universal suffering maps to dedication/emptiness/generosity themes."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("universal")
    assert result is not None
    # Should pull from Heart Sutra, Sanghata, or Diamond
    assert any(s in result for s in ["Heart", "Sanghata", "Diamond", "Golden"])


@pytest.mark.unit
def test_passage_has_formatted_header():
    """Selected passage includes a '**From <Sutra>**' header."""
    gen = RitualGenerator()
    result = gen._select_sutra_passage("universal")
    assert result is not None
    assert result.startswith("**From ")


# ---------------------------------------------------------------------------
# 3. _with_sutra — helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_with_sutra_appends_passage():
    """_with_sutra appends a sutra passage when a match exists."""
    gen = RitualGenerator()
    teaching = "Original teaching text."
    result = gen._with_sutra(teaching, "universal")
    assert "Original teaching text." in result
    assert "**From " in result  # sutra header appended
    assert len(result) > len(teaching)  # grew


@pytest.mark.unit
def test_with_sutra_noop_for_empty_db(monkeypatch):
    """_with_sutra returns teaching unchanged when DB returns nothing."""
    # Simulate empty DB by patching _load_sutra_db
    import core.ritual_generator as rg

    monkeypatch.setattr(rg, "_load_sutra_db", lambda: {})
    gen = RitualGenerator()
    teaching = "Just a teaching."
    result = gen._with_sutra(teaching, "universal")
    assert result == teaching  # unchanged


# ---------------------------------------------------------------------------
# 4. generate_dharma_teaching — full integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dharma_teaching_includes_sutra():
    """generate_dharma_teaching appends a sutra passage (fallback path)."""
    gen = RitualGenerator()
    result = gen.generate_dharma_teaching("financial loss and investment failure")
    assert "**From " in result  # sutra header present
    assert len(result) > 500  # substantial output (parable + sutra)


@pytest.mark.unit
def test_dharma_teaching_earthquake_includes_sutra():
    """Earthquake teaching includes a protection-themed sutra."""
    gen = RitualGenerator()
    result = gen.generate_dharma_teaching("earthquake disaster relief")
    assert "**From " in result
    assert "Golden Light" in result or "Vimalakirti" in result


@pytest.mark.unit
def test_dharma_teaching_returns_string():
    """generate_dharma_teaching always returns a non-empty string."""
    gen = RitualGenerator()
    result = gen.generate_dharma_teaching("universal suffering")
    assert isinstance(result, str)
    assert len(result) > 100
