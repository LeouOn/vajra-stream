"""
Smoke + behaviour tests for ``core.outlook_generator``.

Covers the public surface of :class:`core.outlook_generator.OutlookGenerator`:

* import / construction
* ``generate_single_outlook`` happy path with no LLM (graceful fallback)
* ``generate_epic_outlook`` short-circuits when LLM is unavailable
* ``evaluate_ritual`` returns the documented fallback when ``llm`` is ``None``
* ``generate_single_outlook`` invokes the mocked LLM when one is injected
  and parses SCORE / FEEDBACK from ``evaluate_ritual``

Heavy infra (LLM network calls, full container init, astrology chart lookups,
file debug logging, random sacred-entity selection) is mocked so the tests
remain fast and deterministic.  No real database / network / audio device is
touched.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.outlook_generator import OutlookGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gen():
    """An OutlookGenerator with no LLM integration (uses fallback path)."""
    return OutlookGenerator(llm_integration=None)


@pytest.fixture
def mock_llm():
    """Mock object mimicking the LLMIntegration interface."""
    llm = MagicMock(name="MockLLMIntegration")
    llm.generate.return_value = (
        "SCORE: 8\nFEEDBACK: Lovely resonant blessing, vivid imagery."
    )
    return llm


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports():
    """The module imports without raising and exposes the public class."""
    from core import outlook_generator

    assert hasattr(outlook_generator, "OutlookGenerator")
    assert callable(outlook_generator.OutlookGenerator)


# ---------------------------------------------------------------------------
# 2. Construction — optional dependencies degrade gracefully
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_sets_defaults_and_genres():
    """Constructor populates genres/languages regardless of optional deps."""
    g = OutlookGenerator(llm_integration=None)

    assert g.llm is None
    assert isinstance(g.genres, list)
    assert "healing" in g.genres
    assert isinstance(g.supported_languages, list)
    assert "English" in g.supported_languages


# ---------------------------------------------------------------------------
# 3. generate_single_outlook — happy path without an LLM
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_single_outlook_falls_back_when_no_llm(gen):
    """With no LLM, the generator returns the documented fallback string and
    still produces a well-formed response dict."""
    # Force the astrology / divination lookups to deterministic stubs so we
    # never depend on real chart data.
    with patch.object(gen, "_gather_astrology_context", return_value="AstroCtx"), \
         patch.object(gen, "_gather_divination_data", return_value=("DivCtx", {"tarot": {"name": "The Fool"}})), \
         patch.object(gen, "_select_sacred_entities", return_value="EntityCtx"):
        result = gen.generate_single_outlook(
            lat=40.7128,
            lon=-74.0060,
            languages=["English"],
            genre="healing",
            include_astrology=True,
            include_tarot=False,
            include_iching=False,
            include_geomancy=False,
        )

    assert result["status"] == "success"
    assert result["type"] == "single"
    assert result["genre"] == "healing"
    # Languages should be echoed back unchanged
    assert result["languages"] == ["English"]
    # Fallback text contains the entity/astro/divination snippets we mocked
    assert "AstroCtx" in result["narrative"]
    assert "EntityCtx" in result["narrative"]
    assert "LLM unavailable" in result["narrative"]


# ---------------------------------------------------------------------------
# 4. generate_single_outlook — uses injected LLM and surfaces its output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_single_outlook_calls_llm_when_provided(mock_llm):
    """When an LLM is injected, ``generate_single_outlook`` delegates to it
    and the narrative field carries the LLM's response (not the fallback)."""
    g = OutlookGenerator(llm_integration=mock_llm)

    mock_llm.generate.return_value = "I. Invocatio — A bright star rises over the city."

    with patch.object(g, "_gather_astrology_context", return_value="AstroCtx"), \
         patch.object(g, "_gather_divination_data", return_value=("DivCtx", {})), \
         patch.object(g, "_select_sacred_entities", return_value="EntityCtx"):
        result = g.generate_single_outlook(
            lat=0.0,
            lon=0.0,
            languages=["English", "Sanskrit"],
            genre="victory",
            include_astrology=True,
            include_tarot=False,
            include_iching=False,
            include_geomancy=False,
        )

    # The LLM was actually invoked with the sutra prompt
    assert mock_llm.generate.called
    call_kwargs = mock_llm.generate.call_args.kwargs
    assert "prompt" in call_kwargs
    assert "Invocatio" in call_kwargs["prompt"]
    assert "Sanskrit" in call_kwargs["prompt"]

    # Narrative field contains the LLM's response verbatim
    assert result["narrative"] == mock_llm.generate.return_value
    assert "LLM unavailable" not in result["narrative"]


# ---------------------------------------------------------------------------
# 5. generate_epic_outlook — short-circuits when LLM is required but missing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_epic_outlook_errors_when_no_llm(gen):
    """Epic generation requires an LLM and returns an error status if absent."""
    result = gen.generate_epic_outlook(
        lat=0.0,
        lon=0.0,
        languages=["English"],
        genre="alchemist",
    )

    assert result["status"] == "error"
    assert "LLM" in result["message"]


# ---------------------------------------------------------------------------
# 6. evaluate_ritual — parses SCORE / FEEDBACK from LLM response
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_evaluate_ritual_parses_llm_response():
    """evaluate_ritual extracts SCORE and FEEDBACK from a well-formed reply."""
    llm = MagicMock(name="MockLLM")
    llm.generate.return_value = (
        "SCORE: 9\nFEEDBACK: Strong symbolic resonance."
    )
    g = OutlookGenerator(llm_integration=llm)

    parsed = g.evaluate_ritual("prompt", "outlook")

    assert parsed == {"score": 9, "feedback": "Strong symbolic resonance."}


@pytest.mark.unit
def test_evaluate_ritual_fallback_without_llm(gen):
    """Without an LLM, evaluate_ritual returns the documented default score
    and a feedback string mentioning the LLM."""
    result = gen.evaluate_ritual("prompt", "outlook")

    assert result["score"] == 5
    assert "LLM" in result["feedback"]
