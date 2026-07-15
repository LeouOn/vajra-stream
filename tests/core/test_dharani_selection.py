"""
Tests for dharani recitation selection in ``core.ritual_generator``.

Covers:
- ``_load_dharanis_db`` — module-level cached JSON list loader
- ``RitualGenerator._select_dharani`` — suffering-type → dharani mapping
- ``RitualGenerator.generate_invocation`` — dharani included in invocation output

Tests focus on:
- The dharanis DB loads from knowledge/dharanis.json with 12 entries
- Each suffering type maps to the correct protective/purifying dharani
  (earthquake→Great Compassion, illness→Medicine Buddha, death→Ushnisha Vijaya)
- The invocation includes a "Dharani Recitation" section with Sanskrit text
- _select_dharani returns None gracefully for unknown suffering types
"""

from __future__ import annotations

import pytest

from core.ritual_generator import RitualGenerator, _load_dharanis_db

# ---------------------------------------------------------------------------
# 1. _load_dharanis_db — module-level loader
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dharanis_db_loads():
    """The dharanis database loads from knowledge/dharanis.json."""
    entries = _load_dharanis_db()
    assert isinstance(entries, list)
    assert len(entries) >= 10  # we have 12 entries


@pytest.mark.unit
def test_dharanis_db_has_expected_entries():
    """Known dharani IDs are present in the database."""
    entries = _load_dharanis_db()
    ids = {e["id"] for e in entries}
    expected = {
        "great_compassion_dharani",
        "medicine_buddha_dharani",
        "ushnisha_vijaya_dharani",
        "vajrasattva_hundred_syllable",
        "cundi_dharani",
    }
    assert expected.issubset(ids)


@pytest.mark.unit
def test_dharanis_db_cached():
    """Repeated calls return the same cached list (lru_cache)."""
    db1 = _load_dharanis_db()
    db2 = _load_dharanis_db()
    assert db1 is db2


@pytest.mark.unit
def test_dharanis_have_sanskrit_text():
    """Every dharani entry has a non-empty text_sanskrit field."""
    entries = _load_dharanis_db()
    for entry in entries:
        assert entry.get("text_sanskrit"), f"Entry {entry.get('id')} missing Sanskrit text"


# ---------------------------------------------------------------------------
# 2. _select_dharani — suffering-type mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_earthquake_selects_great_compassion():
    """Earthquake suffering maps to the Great Compassion Dharani (Avalokiteshvara)."""
    gen = RitualGenerator()
    result = gen._select_dharani("earthquake")
    assert result is not None
    assert "Great Compassion" in result
    assert "Avalokiteshvara" in result or "Chenrezig" in result or "Guanyin" in result


@pytest.mark.unit
def test_illness_selects_medicine_buddha():
    """Illness suffering maps to the Medicine Buddha Dharani (healing)."""
    gen = RitualGenerator()
    result = gen._select_dharani("illness")
    assert result is not None
    assert "Medicine Buddha" in result
    assert "Bhai" in result or "Menla" in result or "Bhaisajyaguru" in result


@pytest.mark.unit
def test_death_selects_ushnisha_vijaya():
    """Death suffering maps to the Ushnisha Vijaya Dharani (liberation of deceased)."""
    gen = RitualGenerator()
    result = gen._select_dharani("death")
    assert result is not None
    assert "Ushnisha" in result or "Namgyalma" in result


@pytest.mark.unit
def test_dedication_selects_cundi():
    """Dedication of endeavors maps to the Cundi Dharani (wish-fulfilling/abundance)."""
    gen = RitualGenerator()
    result = gen._select_dharani("dedication_of_endeavors")
    assert result is not None
    assert "Cundi" in result


@pytest.mark.unit
def test_universal_selects_great_compassion():
    """Universal suffering maps to the Great Compassion Dharani."""
    gen = RitualGenerator()
    result = gen._select_dharani("universal")
    assert result is not None
    assert "Great Compassion" in result


@pytest.mark.unit
def test_unknown_suffering_returns_none():
    """An unrecognized suffering type returns None (no crash)."""
    gen = RitualGenerator()
    result = gen._select_dharani("nonexistent_suffering_type")
    assert result is None


@pytest.mark.unit
def test_dharani_includes_sanskrit_text():
    """Selected dharani includes the actual Sanskrit text for recitation."""
    gen = RitualGenerator()
    result = gen._select_dharani("universal")
    assert result is not None
    # Should contain Sanskrit text markers (IAST characters or known phrases)
    assert "O" in result or "Namo" in result or "Tadyath" in result
    assert len(result) > 50  # not just a header


@pytest.mark.unit
def test_dharani_includes_deity_header():
    """Selected dharani includes a '**Dharani of <deity>**' header."""
    gen = RitualGenerator()
    result = gen._select_dharani("illness")
    assert result is not None
    assert result.startswith("**Dharani of")


# ---------------------------------------------------------------------------
# 3. generate_invocation — dharani in invocation output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invocation_includes_dharani_section():
    """generate_invocation() includes a 'Dharani Recitation' subsection."""
    gen = RitualGenerator()
    invocation = gen.generate_invocation("earthquake relief", "vajrayana")
    assert "Dharani Recitation" in invocation
    assert "Recite with single-pointed concentration" in invocation


@pytest.mark.unit
def test_invocation_illness_includes_medicine_buddha_dharani():
    """Illness invocation includes the Medicine Buddha dharani."""
    gen = RitualGenerator()
    invocation = gen.generate_invocation("cancer healing", "vajrayana")
    assert "Medicine Buddha" in invocation


@pytest.mark.unit
def test_invocation_dharani_has_sanskrit_text():
    """The dharani in the invocation contains actual Sanskrit recitation text."""
    gen = RitualGenerator()
    invocation = gen.generate_invocation("universal compassion", "vajrayana")
    # The invocation should have substantial Sanskrit text (not just headers)
    assert len(invocation) > 500
    assert "Dharani" in invocation


# ---------------------------------------------------------------------------
# 4. Graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_select_dharani_with_empty_db(monkeypatch):
    """_select_dharani returns None when DB is empty."""
    import core.ritual_generator as rg

    monkeypatch.setattr(rg, "_load_dharanis_db", lambda: [])
    gen = RitualGenerator()
    result = gen._select_dharani("universal")
    assert result is None


@pytest.mark.unit
def test_invocation_works_without_dharani_db(monkeypatch):
    """generate_invocation still works when dharanis DB is unavailable."""
    import core.ritual_generator as rg

    monkeypatch.setattr(rg, "_load_dharanis_db", lambda: [])
    gen = RitualGenerator()
    invocation = gen.generate_invocation("universal compassion", "vajrayana")
    # Should still produce a valid invocation (without the dharani section)
    assert "OM AH HUM" in invocation
    assert len(invocation) > 100
