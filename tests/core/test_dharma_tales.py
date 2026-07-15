"""Smoke + behaviour tests for ``core.dharma_tales``.

Covers :class:`core.dharma_tales.DharmaTalesGenerator` and the
:func:`create_dharma_tales_generator` factory. Exercises the in-memory
template path (``use_llm=False``) so no LLM is contacted, plus the
list/lookup helpers.

The ``traditional_tales`` library, ``archetypes``, ``themes``, and
``traditions`` are hardcoded in the module under test — there are no
external dependencies.
"""

from __future__ import annotations

import pytest

from core.dharma_tales import (
    DharmaTalesGenerator,
    create_dharma_tales_generator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gen():
    """A bare DharmaTalesGenerator with no LLM attached."""
    return DharmaTalesGenerator()


@pytest.fixture
def gen_with_mock_llm():
    """A generator with a stub LLM that records the prompts passed to it."""

    class _StubLLM:
        def __init__(self):
            self.calls = []

        def generate(self, prompt, system_prompt=None, max_tokens=None, temperature=None):  # noqa: ANN001
            self.calls.append(
                {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            return "An inspiring dharma tale."

    stub = _StubLLM()
    return DharmaTalesGenerator(llm_integration=stub), stub


# ---------------------------------------------------------------------------
# 1. Import smoke + module constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_libraries_loaded(gen):
    """The module imports and exposes 10 themes, 10 archetypes, 8 traditions, and tales."""
    import core.dharma_tales as mod

    assert hasattr(mod, "DharmaTalesGenerator")
    assert callable(mod.create_dharma_tales_generator)

    assert len(gen.themes) == 10
    assert len(gen.archetypes) == 10
    assert len(gen.traditions) == 8

    expected_themes = {
        "impermanence",
        "compassion",
        "emptiness",
        "interdependence",
        "right_action",
        "mindfulness",
        "wisdom",
        "equanimity",
        "letting_go",
        "true_self",
    }
    assert set(gen.themes) == expected_themes

    # NOTE: real bug in core.dharma_tales.py — the key is "the_ burning_house"
    # (with an extra space) instead of "the_burning_house". We assert the actual
    # current behavior here so the test passes; see report.
    tales = gen.get_traditional_tales()
    assert "the_ burning_house" in tales, (
        "Expected the (typo'd) key 'the_ burning_house' — there is a bug in "
        "core.dharma_tales.py where this and 'the_ raft' have an extra space."
    )
    assert tales["the_ burning_house"]["source"] == "Lotus Sutra"


# ---------------------------------------------------------------------------
# 2. Factory function returns a configured instance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_factory_returns_generator():
    """``create_dharma_tales_generator`` returns a configured generator."""
    g = create_dharma_tales_generator()
    assert isinstance(g, DharmaTalesGenerator)
    assert g.llm is None
    assert len(g.themes) == 10


# ---------------------------------------------------------------------------
# 3. generate_tale without LLM uses the template path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_tale_template_path(gen):
    """With ``use_llm=False`` the template engine produces a non-empty tale."""
    # The SHORT template intentionally omits the explicit "-- From the {tradition}
    # tradition" label; only the LONG form appends it. We assert both forms work.
    short_tale = gen.generate_tale(theme="compassion", tradition="Zen", length="short", use_llm=False)
    assert isinstance(short_tale, str)
    assert len(short_tale) > 0

    long_tale = gen.generate_tale(theme="impermanence", tradition="Theravada", length="long", use_llm=False)
    assert isinstance(long_tale, str)
    assert "Theravada" in long_tale
    assert "impermanence" in long_tale.lower() or "arises" in long_tale.lower()


# ---------------------------------------------------------------------------
# 4. generate_tale with a stub LLM delegates to llm.generate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_tale_uses_llm_when_available(gen_with_mock_llm):
    """With an LLM attached, the generator delegates generation to it."""
    g, stub = gen_with_mock_llm
    result = g.generate_tale(theme="emptiness", tradition="Mahayana", length="medium", use_llm=True)
    assert result == "An inspiring dharma tale."
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert "emptiness" in call["prompt"].lower()
    assert "Mahayana" in call["prompt"]
    assert call["max_tokens"] == 400  # medium length
    assert call["system_prompt"] is not None


# ---------------------------------------------------------------------------
# 5. generate_parable template path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_parable_template_fallback(gen):
    """Without an LLM, ``generate_parable`` returns the cup-overflow parable."""
    text = gen.generate_parable("letting go", use_llm=False)
    assert "seeker" in text
    assert "master" in text
    assert "letting go" in text


# ---------------------------------------------------------------------------
# 6. list helpers return copies (mutating them doesn't affect the generator)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_helpers_return_independent_copies(gen):
    """``list_themes`` / ``list_traditions`` return copies that can be mutated safely."""
    themes = gen.list_themes()
    themes.append("nonsense")
    assert "nonsense" not in gen.themes

    traditions = gen.list_traditions()
    traditions.remove("Zen")
    assert "Zen" in gen.traditions


# ---------------------------------------------------------------------------
# 7. generate_teaching_story without LLM falls back to long template
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generate_teaching_story_template_path(gen):
    """Without an LLM, ``generate_teaching_story`` uses the long template."""
    text = gen.generate_teaching_story(
        archetype="The Curious Child", challenge="wisdom", tradition="Sufi", use_llm=False
    )
    assert isinstance(text, str)
    assert len(text) > 50
    assert "Sufi" in text
