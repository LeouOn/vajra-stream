"""Smoke + behaviour tests for ``core.eighty_eight_buddhas``.

Covers :class:`core.eighty_eight_buddhas.EightyEightBuddhas` and its public
helpers (:func:`get_eighty_eight_buddhas`). Exercises the loader, random
selection, name lookup, the confession-sequence shape, and the template
narrative path (no LLM available in tests).

The module loads from ``knowledge/eighty_eight_buddhas.json`` which is
shipped with the repository; we exercise the real loader.
"""

from __future__ import annotations

import pytest

from core.eighty_eight_buddhas import (
    BuddhaEntry,
    EightyEightBuddhas,
    get_eighty_eight_buddhas,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service():
    """A freshly-constructed EightyEightBuddhas service."""
    return EightyEightBuddhas()


# ---------------------------------------------------------------------------
# 1. Import smoke + public API
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exposes_public_api():
    """The module imports cleanly and exposes its public symbols."""
    import core.eighty_eight_buddhas as mod

    assert hasattr(mod, "BuddhaEntry")
    assert hasattr(mod, "EightyEightBuddhas")
    assert callable(mod.get_eighty_eight_buddhas)
    # BuddhaEntry must be a dataclass with the expected fields
    fields = {f for f in BuddhaEntry.__dataclass_fields__}
    for expected in (
        "index",
        "name_chinese",
        "name_pinyin",
        "name_sanskrit",
        "category",
        "meaning",
        "realm",
        "light",
        "epithet",
    ):
        assert expected in fields, f"BuddhaEntry missing field: {expected}"


# ---------------------------------------------------------------------------
# 2. Loader: 88 Buddhas are loaded into both categories
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_loader_populates_both_categories(service):
    """The loader should populate 88 entries split between past/confession."""
    assert service.buddha_count == 88, f"Expected 88, got {service.buddha_count}"

    past = [b for b in service._buddhas if b.category == "past"]
    confession = [b for b in service._buddhas if b.category == "confession"]
    assert len(past) == 53, f"Expected 53 past Buddhas, got {len(past)}"
    assert len(confession) == 35, f"Expected 35 confession Buddhas, got {len(confession)}"


# ---------------------------------------------------------------------------
# 3. random_buddha honours category filter
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_random_buddha_category_filter(service):
    """When a category is given, only Buddhas of that category are returned."""
    for _ in range(10):
        b = service.random_buddha(category="past")
        assert b.category == "past"
    for _ in range(10):
        b = service.random_buddha(category="confession")
        assert b.category == "confession"


# ---------------------------------------------------------------------------
# 4. get_buddha_by_name supports partial Chinese / Sanskrit match
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_buddha_by_name_returns_match(service):
    """Partial name lookup finds a Buddha by Chinese substring."""
    # 釋迦牟尼佛 (Shakyamuni) should be in the confession group
    buddha = service.get_buddha_by_name("釋迦牟尼")
    assert buddha is not None
    assert buddha.category == "confession"

    # Sanskrit field uses IAST diacritics; a substring that appears in the
    # Sanskrit field of many Buddhas (e.g. "Tathāgatāya") must match.
    sanskrit_hit = service.get_buddha_by_name("tathāgatāya")
    assert sanskrit_hit is not None
    assert sanskrit_hit.category in ("past", "confession")

    # Unknown name returns None
    assert service.get_buddha_by_name("xyzzy_no_such_buddha") is None


# ---------------------------------------------------------------------------
# 5. get_confession_sequence returns the full liturgical structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_confession_sequence_shape(service):
    """The confession sequence includes titles, 53 past Buddhas, and 35 confession Buddhas."""
    seq = service.get_confession_sequence()

    assert seq["title"] == "八十八佛大懺悔文"
    assert "Great Repentance" in seq["title_english"]
    assert isinstance(seq["opening_verse"], dict)
    assert isinstance(seq["closing_dedication"], dict)
    assert len(seq["fifty_three_past_buddhas"]) == 53
    assert len(seq["thirty_five_confession_buddhas"]) == 35

    # Each confession entry must include the 南無 (Namo) prefix
    sample = seq["thirty_five_confession_buddhas"][0]
    assert sample["confession_line"].startswith("南無")


# ---------------------------------------------------------------------------
# 6. generate_buddha_narrative: brief / contemplation / unknown-name error
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_buddha_narrative_paths(service):
    """Brief depth is deterministic; unknown name returns an error payload."""
    # Brief depth is fully template-driven and works without an LLM
    result = service.generate_buddha_narrative("釋迦牟尼", depth="brief")
    assert "buddha" in result
    assert "narrative" in result
    assert result["depth"] == "brief"
    assert isinstance(result["narrative"], str)
    assert len(result["narrative"]) > 0
    assert "generated_at" in result

    # Unknown Buddha → error dict, not an exception
    err = service.generate_buddha_narrative("nonexistent_buddha_xyz", depth="brief")
    assert "error" in err
    assert "nonexistent_buddha_xyz" in err["error"]


# ---------------------------------------------------------------------------
# 7. Singleton accessor returns the same instance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_eighty_eight_buddhas_singleton():
    """The module-level accessor returns a cached singleton instance."""
    import core.eighty_eight_buddhas as mod

    # Reset module-level cache to guarantee a clean test
    mod._eighty_eight_buddhas_instance = None
    a = get_eighty_eight_buddhas()
    b = get_eighty_eight_buddhas()
    assert a is b, "Accessor should return the same singleton instance"
