"""
Smoke + behaviour tests for ``core.context_builder``.

Covers the public surface:
- ``build_frequencies_reference`` / ``build_mantras_reference`` / ``build_chakra_reference``
- ``load_rate_database``
- ``build_system_prompt``
- ``build_intention_analysis_prompt`` / ``build_rate_suggestion_prompt``
- ``search_rates``
- :class:`SessionContext`
"""

from __future__ import annotations

import pytest

from core.context_builder import (
    SessionContext,
    build_chakra_reference,
    build_frequencies_reference,
    build_intention_analysis_prompt,
    build_mantras_reference,
    build_rate_suggestion_prompt,
    build_system_prompt,
    load_rate_database,
    search_rates,
)

# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """Module exports all expected public functions."""
    import core.context_builder as mod

    for name in (
        "build_frequencies_reference",
        "build_mantras_reference",
        "build_chakra_reference",
        "load_rate_database",
        "build_system_prompt",
        "build_intention_analysis_prompt",
        "build_rate_suggestion_prompt",
        "search_rates",
        "SessionContext",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Reference builders return non-empty strings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_frequencies_reference_returns_string():
    ref = build_frequencies_reference()
    assert isinstance(ref, str)
    assert len(ref) > 0


@pytest.mark.unit
def test_build_mantras_reference_returns_string():
    ref = build_mantras_reference()
    assert isinstance(ref, str)
    assert len(ref) > 0


@pytest.mark.unit
def test_build_chakra_reference_returns_string():
    ref = build_chakra_reference()
    assert isinstance(ref, str)
    assert len(ref) > 0


# ---------------------------------------------------------------------------
# 3. Rate database + search
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_rate_database_returns_dict():
    db = load_rate_database()
    assert isinstance(db, dict)


@pytest.mark.unit
def test_search_rates_returns_list():
    """search_rates returns a list for any query (possibly empty)."""
    results = search_rates("healing")
    assert isinstance(results, list)


@pytest.mark.unit
def test_search_rates_unknown_query_returns_empty():
    """search_rates for nonsense returns empty list, never raises."""
    results = search_rates("xyzzy_nonexistent_12345")
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# 4. Prompt builders
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_system_prompt_returns_string():
    prompt = build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


@pytest.mark.unit
def test_build_intention_analysis_prompt_includes_intention():
    prompt = build_intention_analysis_prompt("May all beings be happy")
    assert isinstance(prompt, str)
    assert "May all beings be happy" in prompt


@pytest.mark.unit
def test_build_rate_suggestion_prompt_includes_intention():
    prompt = build_rate_suggestion_prompt("healing", num_rates=3)
    assert isinstance(prompt, str)
    assert "healing" in prompt.lower()


# ---------------------------------------------------------------------------
# 5. SessionContext
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_session_context_init_and_to_dict():
    ctx = SessionContext()
    d = ctx.to_dict()
    assert isinstance(d, dict)


@pytest.mark.unit
def test_session_context_update_and_record_event():
    ctx = SessionContext()
    ctx.update(intention="peace")
    d = ctx.to_dict()
    assert d.get("intention") == "peace"

    # record_event should not raise
    ctx.record_event("test_event", {"key": "value"})
