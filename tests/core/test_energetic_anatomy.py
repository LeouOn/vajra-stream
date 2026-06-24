"""
Tests for core/energetic_anatomy.py — multi-traditional subtle body system
(Taoist meridians, Tibetan channels, Hindu chakras).

Covers the EnergeticAnatomyDatabase public API, the dataclass contracts
(Chakra, Meridian), and the convenience functions. No IO: tests use the
in-memory default database.
"""
from __future__ import annotations

import json

import pytest

from core.energetic_anatomy import (
    Chakra,
    Element,
    EnergeticAnatomyDatabase,
    Tradition,
    get_chakra_by_name,
    get_meridian_by_element,
)

# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def db() -> EnergeticAnatomyDatabase:
    """Fresh in-memory database with default initialization."""
    return EnergeticAnatomyDatabase()


# ─── Smoke ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_module_imports():
    """Smoke test: the module imports and exposes expected public symbols."""
    # Enums
    assert Element.WOOD.value == "wood"
    assert Tradition.HINDU.value == "hindu"
    # Dataclasses
    assert Chakra is not None
    # Public functions
    assert callable(get_chakra_by_name)
    assert callable(get_meridian_by_element)
    # Database class
    assert callable(EnergeticAnatomyDatabase)


# ─── Behavior: database initialization ──────────────────────────────────────


@pytest.mark.unit
def test_default_database_populates_all_three_systems(db: EnergeticAnatomyDatabase):
    """Default ctor populates Taoist, Tibetan, and Hindu dictionaries."""
    # Taoist
    assert len(db.meridians) > 0
    assert len(db.dantians) > 0

    # Tibetan
    assert len(db.tibetan_channels) > 0
    assert len(db.tibetan_chakras) > 0
    assert len(db.winds) > 0

    # Hindu
    assert len(db.chakras) == 7  # the classical 7 chakras
    assert len(db.nadis) > 0
    assert len(db.granthis) > 0
    assert db.kundalini is not None  # kundalini shakti initialized

    # Cross-system
    assert len(db.correspondences) > 0


# ─── Behavior: lookup helpers ──────────────────────────────────────────────


@pytest.mark.unit
def test_get_chakra_by_name_finds_heart_chakra(db: EnergeticAnatomyDatabase):
    """get_chakra_by_name resolves heart chakra by English or Sanskrit name."""
    heart = get_chakra_by_name(db, "heart")
    assert heart is not None
    assert heart.sanskrit_name.lower() == "anahata"

    # Sanskrit name lookup works too
    anahata = get_chakra_by_name(db, "anahata")
    assert anahata is heart  # same object

    # Unknown name returns None
    assert get_chakra_by_name(db, "not-a-real-chakra") is None


@pytest.mark.unit
def test_get_meridian_by_element_filters_correctly(db: EnergeticAnatomyDatabase):
    """get_meridian_by_element returns meridians matching element (+ optional yin/yang)."""
    # Wood meridians (Liver) — at least 1 (the database has 1 of each classical element).
    wood_meridians = get_meridian_by_element(db, Element.WOOD)
    assert len(wood_meridians) >= 1
    assert all(m.element == Element.WOOD for m in wood_meridians)

    # Fire meridian (Heart) exists.
    fire_meridians = get_meridian_by_element(db, Element.FIRE)
    assert len(fire_meridians) >= 1
    assert all(m.element == Element.FIRE for m in fire_meridians)

    # Space element has no meridians (chakras only).
    space_meridians = get_meridian_by_element(db, Element.SPACE)
    assert space_meridians == []


# ─── Behavior: dataclass contract ──────────────────────────────────────────


@pytest.mark.unit
def test_chakra_to_dict_includes_sanskrit_fields(db: EnergeticAnatomyDatabase):
    """Chakra.to_dict() exposes both base EnergeticCenter fields and Hindu-specific ones."""
    heart = get_chakra_by_name(db, "heart")
    assert heart is not None
    d = heart.to_dict()

    # Base EnergeticCenter fields
    assert d["name"] == heart.name
    assert d["tradition"] == Tradition.HINDU.value
    assert d["element"] == Element.SPACE.value  # heart chakra = space element
    assert "frequency" in d
    assert "bija_mantra" in d

    # Hindu-specific fields
    assert d["sanskrit_name"].lower() == "anahata"
    assert d["petals"] == 12  # heart chakra has 12 petals
    assert d["deity"] != ""
    assert isinstance(d["blocked_issues"], list)
    assert isinstance(d["open_qualities"], list)


# ─── Behavior: search and export ───────────────────────────────────────────


@pytest.mark.unit
def test_search_by_keyword_returns_expected_categories(db: EnergeticAnatomyDatabase):
    """search_by_keyword returns a dict with the documented category buckets."""
    results = db.search_by_keyword("fire")

    # The function returns the documented keys (even if some are empty for
    # this particular query).
    assert "meridians" in results
    assert "chakras" in results
    assert "tibetan_chakras" in results
    assert "winds" in results
    assert "dantians" in results

    # "Fire" matches on name/description; the Fire-Accompanying Wind is one
    # such hit (the Tibetan Navel chakra also references fire in its text).
    fire_winds = results["winds"]
    assert any("fire" in w.name.lower() for w in fire_winds)


@pytest.mark.unit
def test_export_to_json_writes_valid_file(db: EnergeticAnatomyDatabase, tmp_path):
    """export_to_json() writes a parseable JSON file with all three systems."""
    out = tmp_path / "anatomy.json"
    db.export_to_json(str(out))

    assert out.exists()
    data = json.loads(out.read_text())

    assert "taoist" in data
    assert "tibetan" in data
    assert "hindu" in data
    assert "correspondences" in data

    # Hindu section includes kundalini
    assert data["hindu"]["kundalini"] is not None
    assert data["hindu"]["kundalini"]["id"] == "kundalini"
