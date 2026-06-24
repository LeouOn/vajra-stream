"""
Smoke + behaviour tests for ``core.chinese_invocations``.

The module is a pure-data lookup with two public surfaces:
- ``CHINESE_INVOCATIONS`` — a dict keyed by category, each value a list of
  invocation dicts with ``chinese`` / ``pinyin`` / ``translation`` / ``source``.
- ``get_chinese_invocation(category, index)`` — a safe lookup with a
  fallback for unknown categories.
- ``CHINESE_DHARANI_PINYIN`` — a separate dict of dharani metadata.

This module has no imports beyond the standard library — no mocking needed.
"""
from __future__ import annotations

import pytest

from core.chinese_invocations import (
    CHINESE_DHARANI_PINYIN,
    CHINESE_INVOCATIONS,
    get_chinese_invocation,
)


# ---------------------------------------------------------------------------
# 1. Module imports + structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exports CHINESE_INVOCATIONS, get_chinese_invocation, and CHINESE_DHARANI_PINYIN."""
    import core.chinese_invocations as mod

    for name in ("CHINESE_INVOCATIONS", "get_chinese_invocation", "CHINESE_DHARANI_PINYIN"):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


@pytest.mark.unit
def test_chinese_invocations_has_all_expected_categories():
    """``CHINESE_INVOCATIONS`` contains the five ritual categories."""
    expected = {"opening", "purification", "dedication", "blessing", "sealing"}
    assert expected <= set(CHINESE_INVOCATIONS.keys())

    # Each category has at least one invocation
    for cat, items in CHINESE_INVOCATIONS.items():
        assert isinstance(items, list) and len(items) > 0, f"Empty category: {cat}"


@pytest.mark.unit
def test_invocations_have_required_fields():
    """Every invocation dict has chinese, pinyin, translation, and source fields."""
    for category, items in CHINESE_INVOCATIONS.items():
        for inv in items:
            for field in ("chinese", "pinyin", "translation", "source"):
                assert field in inv, f"Missing '{field}' in {category} invocation"
                assert isinstance(inv[field], str) and inv[field], (
                    f"Empty '{field}' in {category} invocation"
                )


# ---------------------------------------------------------------------------
# 2. get_chinese_invocation — happy path + fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_chinese_invocation_returns_indexed_entry():
    """Known category + index returns the matching invocation."""
    inv = get_chinese_invocation("opening", index=0)

    assert "chinese" in inv
    assert "pinyin" in inv
    assert "translation" in inv
    # Matches the first opening invocation
    assert inv == CHINESE_INVOCATIONS["opening"][0]


@pytest.mark.unit
def test_get_chinese_invocation_wraps_index_out_of_range():
    """Index beyond list length wraps around via modulo."""
    items = CHINESE_INVOCATIONS["opening"]
    inv = get_chinese_invocation("opening", index=len(items) + 5)

    # Modulo brings it back into range
    assert inv == items[(len(items) + 5) % len(items)]


@pytest.mark.unit
def test_get_chinese_invocation_unknown_category_falls_back_to_namo_amituofo():
    """Unknown category returns the fallback Namo Amitabha invocation."""
    inv = get_chinese_invocation("nonexistent_category_xyz", index=0)

    assert inv["chinese"] == "南无阿弥陀佛"
    assert inv["pinyin"] == "Námó Āmítuófó"
    assert "Amitabha" in inv["translation"]


# ---------------------------------------------------------------------------
# 3. CHINESE_DHARANI_PINYIN — well-known dharanis
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dharani_dict_contains_known_dharanis():
    """``CHINESE_DHARANI_PINYIN`` has the well-known dharanis with title + pinyin."""
    expected_keys = {
        "great_compassion",
        "heart_sutra",
        "medicine_buddha",
        "cundi",
        "amitabha",
        "shurangama",
    }
    assert expected_keys <= set(CHINESE_DHARANI_PINYIN.keys())

    for key, entry in CHINESE_DHARANI_PINYIN.items():
        assert "title" in entry, f"Missing title in {key}"
        assert "pinyin_title" in entry, f"Missing pinyin_title in {key}"
        assert isinstance(entry["title"], str) and entry["title"]
        assert isinstance(entry["pinyin_title"], str) and entry["pinyin_title"]
