"""
Smoke + behaviour tests for ``core.protocol_selector``.

Covers the public surface:
- :class:`ConditionProtocol` — dataclass with list defaults.
- :class:`ProtocolSelector` — constructor populates the three healing systems
  (HAS_HEALING branch is exercised — healing_systems is a real module).
- ``select_protocol(condition)`` — known conditions map to chakras; unknown
  conditions return an empty protocol without raising.
- ``select_multi_condition`` — merges + dedupes frequencies and mantras.
- ``get_available_conditions`` — returns a sorted list of known conditions.

The module imports ``core.healing_systems`` at the top, which has no
external dependencies — no mocking is required.
"""
from __future__ import annotations

import pytest

from core.protocol_selector import (
    HAS_HEALING,
    ConditionProtocol,
    ProtocolSelector,
)


# ---------------------------------------------------------------------------
# 1. Import smoke + HAS_HEALING sanity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_healing_systems_available():
    """The module imports and the real ``core.healing_systems`` dependency is available."""
    assert HAS_HEALING is True
    import core.protocol_selector as mod

    for name in ("ProtocolSelector", "ConditionProtocol"):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. ConditionProtocol — list defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_condition_protocol_default_collections_are_empty_lists():
    """Every list field defaults to an empty list (not a shared mutable)."""
    a = ConditionProtocol(condition="x")
    b = ConditionProtocol(condition="y")

    # Mutating a's lists must not affect b's
    a.chakras.append("muladhara")
    a.frequencies.append(528.0)
    assert b.chakras == []
    assert b.frequencies == []


# ---------------------------------------------------------------------------
# 3. ProtocolSelector constructor populates all three systems
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_populates_healing_systems():
    """All three healing-system sub-objects are constructed."""
    sel = ProtocolSelector()

    assert sel.chakra_system is not None
    assert sel.meridian_system is not None
    assert sel.tibetan_system is not None
    # The chakra system has the canonical 7 chakras
    assert len(sel.chakra_system.chakras) == 7


# ---------------------------------------------------------------------------
# 4. select_protocol — known conditions map to chakras
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_select_protocol_known_condition_maps_to_chakras():
    """``select_protocol("anxiety")`` returns a protocol with the expected chakras."""
    sel = ProtocolSelector()
    proto = sel.select_protocol("anxiety")

    assert proto.condition == "anxiety"
    # Anxiety is documented to map to muladhara + anahata
    assert "muladhara" in proto.chakras
    assert "anahata" in proto.chakras
    # And therefore includes their Solfeggio frequencies
    assert 396.0 in proto.frequencies
    assert 639.0 in proto.frequencies


@pytest.mark.unit
def test_select_protocol_unknown_condition_returns_empty_lists():
    """An unknown condition returns an empty protocol without raising."""
    sel = ProtocolSelector()
    proto = sel.select_protocol("nonexistent_xyz_condition")

    assert proto.condition == "nonexistent_xyz_condition"
    assert proto.chakras == []
    assert proto.meridians == []
    assert proto.frequencies == []
    assert proto.mantras == []
    assert proto.colours == []
    assert proto.practices == []


# ---------------------------------------------------------------------------
# 5. select_multi_condition — merges and dedupes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_select_multi_condition_merges_and_dedupes():
    """``select_multi_condition`` joins the condition name and dedupes fields."""
    sel = ProtocolSelector()
    multi = sel.select_multi_condition(["anxiety", "headache"])

    # Condition field joins inputs
    assert "anxiety" in multi.condition
    assert "headache" in multi.condition
    # Merges chakras
    assert "muladhara" in multi.chakras
    assert "anahata" in multi.chakras
    # Frequencies are deduped
    assert len(multi.frequencies) == len(set(multi.frequencies))
    # Mantras are deduped
    assert len(multi.mantras) == len(set(multi.mantras))


@pytest.mark.unit
def test_select_multi_condition_empty_input_returns_none():
    """Empty input list returns a ConditionProtocol(condition='none')."""
    sel = ProtocolSelector()
    proto = sel.select_multi_condition([])

    assert proto.condition == "none"
    assert proto.chakras == []
    assert proto.frequencies == []


# ---------------------------------------------------------------------------
# 6. get_available_conditions — sorted list of known conditions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_available_conditions_returns_sorted_known_list():
    """Returns a sorted list including the documented conditions."""
    sel = ProtocolSelector()
    conds = sel.get_available_conditions()

    assert isinstance(conds, list)
    assert conds == sorted(conds)
    # A sample of well-known conditions
    for expected in ("anxiety", "headache", "grief"):
        assert expected in conds
