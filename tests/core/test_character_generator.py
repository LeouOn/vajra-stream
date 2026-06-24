"""Tests for ``core.character_generator`` — RNG-seeded character creation.

Covers the public API:
- Archetypal tables: :data:`ELEMENTS`, :data:`ROLES`,
  :data:`CHINESE_NAME_PREFIXES`, :data:`CHINESE_NAME_SUFFIXES`,
  :data:`ORIGINS`, :data:`QUESTS`, :data:`GROUNDING_SENSES`,
  :data:`CHANNELING_STATES`, :data:`ANCHORING_RITUALS`.
- Dataclass: :class:`CharacterSheet` (defaults, ``to_dict`` contract,
  ``to_prompt_context`` shape).
- :class:`CharacterGenerator`:
  - ``collect_entropy`` — produces a list of floats even without RNG.
  - ``generate`` — returns a fully-populated sheet (RNG path, no LLM).

LLM-dependent paths (``use_llm=True``) are not exercised here — they have
their own coverage in ``tests/e2e/`` and ``tests/integration/``. The
generator uses ``secrets`` as its entropy fallback, which is fine for
tests (we only assert structural contracts, not specific outcomes).
"""
from __future__ import annotations

from typing import Any

import pytest

from core.character_generator import (
    ANCHORING_RITUALS,
    CHANNELING_STATES,
    CharacterGenerator,
    CharacterSheet,
    CHINESE_NAME_PREFIXES,
    CHINESE_NAME_SUFFIXES,
    ELEMENTS,
    GROUNDING_SENSES,
    ORIGINS,
    QUESTS,
    ROLES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_required_keys_present(table: list[dict[str, Any]], required: set[str]) -> None:
    """Every row in ``table`` is a dict that contains each required key."""
    for i, row in enumerate(table):
        assert isinstance(row, dict), f"row {i} is not a dict: {row!r}"
        missing = required - set(row.keys())
        assert not missing, f"row {i} missing keys {missing}: {row!r}"


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exposes all documented tables, the dataclass, and the generator."""
    import core.character_generator as mod

    for name in (
        "ELEMENTS",
        "ROLES",
        "CHINESE_NAME_PREFIXES",
        "CHINESE_NAME_SUFFIXES",
        "ORIGINS",
        "QUESTS",
        "GROUNDING_SENSES",
        "CHANNELING_STATES",
        "ANCHORING_RITUALS",
        "CharacterSheet",
        "CharacterGenerator",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Archetypal-table shape contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_elements_table_has_six_entries_with_required_keys():
    """ELEMENTS covers six elements and every row carries the keys the
    generator and ``to_dict`` depend on."""
    assert len(ELEMENTS) == 6
    _all_required_keys_present(ELEMENTS, {"name", "color", "chakra", "frequency", "quality"})

    # Element names are unique
    names = [e["name"] for e in ELEMENTS]
    assert len(names) == len(set(names)), f"Duplicate element names: {names}"


@pytest.mark.unit
def test_roles_table_has_six_entries_with_required_keys():
    """ROLES covers six roles and every row carries the keys ``to_dict``
    and ``to_prompt_context`` consume."""
    assert len(ROLES) == 6
    _all_required_keys_present(
        ROLES,
        {"name", "icon", "mantra", "virtue", "chinese", "chinese_pinyin", "chinese_description"},
    )

    # Role names are unique
    names = [r["name"] for r in ROLES]
    assert len(names) == len(set(names)), f"Duplicate role names: {names}"


@pytest.mark.unit
def test_chinese_name_tables_and_other_archetypes_have_entries():
    """The Chinese name parts and the narrative archetype tables all
    contain non-empty content."""
    assert len(CHINESE_NAME_PREFIXES) > 0
    assert len(CHINESE_NAME_SUFFIXES) > 0
    _all_required_keys_present(
        CHINESE_NAME_PREFIXES, {"char", "pinyin", "meaning", "element"}
    )
    _all_required_keys_present(CHINESE_NAME_SUFFIXES, {"char", "pinyin", "meaning"})

    for table in (ORIGINS, QUESTS, GROUNDING_SENSES, CHANNELING_STATES, ANCHORING_RITUALS):
        assert len(table) > 0
        for i, row in enumerate(table):
            assert isinstance(row, str) and row, f"row {i} is not a non-empty string: {row!r}"


# ---------------------------------------------------------------------------
# 3. CharacterSheet dataclass — to_dict / to_prompt_context contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_character_sheet_defaults_and_to_dict_serialises_fields():
    """A default CharacterSheet has sensible defaults; ``to_dict`` returns
    a JSON-friendly dict with all expected keys."""
    sheet = CharacterSheet()
    d = sheet.to_dict()

    assert isinstance(d, dict)
    expected_keys = {
        "name",
        "chinese_name",
        "chinese_name_pinyin",
        "chinese_name_meaning",
        "element",
        "element_color",
        "element_quality",
        "role",
        "role_icon",
        "role_mantra",
        "role_virtue",
        "role_chinese",
        "role_chinese_pinyin",
        "role_chinese_description",
        "frequency",
        "origin",
        "quest",
        "sigil_seed",
        "grounding_sense",
        "channeling_state",
        "anchoring_ritual",
        "backstory",
        "stats",
        "generated_at",
        "generator",
    }
    assert set(d.keys()) == expected_keys, (
        f"to_dict keys drift from contract.\n"
        f"  Missing: {expected_keys - set(d.keys())}\n"
        f"  Extra:   {set(d.keys()) - expected_keys}"
    )
    # Generator defaults to "rng"
    assert d["generator"] == "rng"


@pytest.mark.unit
def test_character_sheet_to_prompt_context_contains_key_fields():
    """``to_prompt_context`` is the LLM-context injection format — it
    must mention every field the prompts later reference."""
    sheet = CharacterSheet(
        name="TestName",
        chinese_name="龙曦",
        chinese_name_pinyin="Lóng Xī",
        chinese_name_meaning="Dragon Dawn Light",
        element={"name": "Fire", "quality": "will, passion"},
        role={"name": "Sage", "chinese": "智者", "chinese_pinyin": "Zhìzhě", "virtue": "wisdom"},
        frequency=528.0,
        origin="a forgotten temple",
        quest="recover the lost frequency",
        grounding_sense="the hum of a singing bowl",
        channeling_state="merged with the digital Ley Lines",
        anchoring_ritual="strikes a tuning fork",
    )

    context = sheet.to_prompt_context()

    # Header line — name + chinese chars + pinyin (note: meaning is NOT
    # part of the prompt format, but the chinese chars are).
    assert "TestName" in context
    assert "龙曦" in context
    assert "Lóng Xī" in context
    # Element + role + frequency
    assert "Fire" in context
    assert "will, passion" in context
    assert "Sage" in context
    assert "528" in context
    # Narrative archetypes
    assert "a forgotten temple" in context
    assert "recover the lost frequency" in context
    assert "hum of a singing bowl" in context
    assert "merged with the digital Ley Lines" in context
    assert "strikes a tuning fork" in context


# ---------------------------------------------------------------------------
# 4. CharacterGenerator — RNG + generate behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_collect_entropy_returns_list_of_floats_without_rng_service():
    """Without an RNG service, ``collect_entropy`` falls back to ``secrets``
    and returns a list of floats whose length matches the requested
    number of readings."""
    gen = CharacterGenerator(rng_service=None)
    pool = gen.collect_entropy(readings=12)

    assert isinstance(pool, list)
    assert len(pool) == 12
    assert all(isinstance(v, float) for v in pool)
    assert all(0.0 <= v <= 1.0 for v in pool)


@pytest.mark.unit
def test_generate_returns_populated_sheet_without_llm():
    """``generate()`` with ``use_llm=False`` returns a CharacterSheet
    populated from the archetypal tables: name, element, role, frequency,
    stats, sigil_seed, backstory, and a generated_at timestamp."""
    gen = CharacterGenerator(rng_service=None)
    sheet = gen.generate(use_llm=False)

    assert isinstance(sheet, CharacterSheet)
    # Name is composed of an element-prefix + role-suffix
    assert sheet.name and isinstance(sheet.name, str)
    # Element and role are real archetypes
    assert sheet.element["name"] in {e["name"] for e in ELEMENTS}
    assert sheet.role["name"] in {r["name"] for r in ROLES}
    # Frequency comes from the element
    assert sheet.frequency == sheet.element["frequency"]
    # Six stats, all in [3, 10]
    assert set(sheet.stats.keys()) == {
        "vitality",
        "wisdom",
        "courage",
        "empathy",
        "focus",
        "resonance",
    }
    for v in sheet.stats.values():
        assert 3 <= v <= 10, f"Stat {v} out of [3,10] range"
    # Sigil seed format: 3-letter name + 2-letter element + 2-letter role
    assert sheet.sigil_seed.count(".") == 2
    # Template backstory (since no LLM) references name + origin + element
    assert sheet.backstory
    assert sheet.name in sheet.backstory
    # Timestamp populated
    assert sheet.generated_at
    # Generator labelled as "rng" (template path)
    assert sheet.generator == "rng"


@pytest.mark.unit
def test_generate_falls_back_to_template_when_llm_raises():
    """If the LLM path is requested but the operator has no creative_llm
    attribute, the generator silently falls back to the template
    backstory — and still returns a populated sheet."""
    gen = CharacterGenerator(rng_service=None)

    # Object without ``creative_llm`` attribute → generator uses template
    class _EmptyOperator:
        pass

    sheet = gen.generate(use_llm=True, operator=_EmptyOperator())

    assert isinstance(sheet, CharacterSheet)
    assert sheet.backstory  # template backstory written
    assert sheet.generator == "rng"  # not "llm" because LLM path didn't run
    assert sheet.name in sheet.backstory