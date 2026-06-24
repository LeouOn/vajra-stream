"""Tests for ``core.blessing_narratives`` — template + LLM narrative engine.

Covers the public API:
- Enums: :class:`NarrativeType`, :class:`PureLandTradition`
- Dataclasses: :class:`NarrativeTemplate`, :class:`GeneratedStory`
- Static content providers: :class:`PureLandDescriptions`,
  :class:`NarrativeTemplateLibrary`
- :class:`StoryGenerator` (template path; LLM path is exercised via attribute
  contract only to avoid heavy infra)
- :class:`StoryExporter` (markdown / JSON / collection)

Heavy LLM I/O is **not** exercised — those code paths are guarded by
``use_llm=False`` and the optional ``LLMIntegration`` import.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.blessing_narratives import (
    GeneratedStory,
    NarrativeTemplate,
    NarrativeTemplateLibrary,
    NarrativeType,
    PureLandDescriptions,
    PureLandTradition,
    StoryExporter,
    StoryGenerator,
)


# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.blessing_narratives as mod

    for name in (
        "NarrativeType",
        "PureLandTradition",
        "NarrativeTemplate",
        "GeneratedStory",
        "PureLandDescriptions",
        "NarrativeTemplateLibrary",
        "StoryGenerator",
        "StoryExporter",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"


# ---------------------------------------------------------------------------
# 2. Enum contracts
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_narrative_type_enum_has_expected_members():
    """NarrativeType covers all 10 narrative kinds promised by the docstring."""
    expected = {
        "pure_land_arrival",
        "hell_liberation",
        "hungry_ghost_nourishment",
        "empowerment",
        "reconciliation",
        "healing_journey",
        "alternate_timeline",
        "divine_intervention",
        "self_realization",
        "collective_awakening",
    }
    actual = {nt.value for nt in NarrativeType}
    assert actual == expected


@pytest.mark.unit
def test_pure_land_tradition_enum_has_expected_members():
    """PureLandTradition covers the 10 traditions documented in the module."""
    expected = {
        "sukhavati",
        "abhirati",
        "shambhala",
        "tushita",
        "potala",
        "vimalakirti",
        "universal_light",
        "nature_paradise",
        "ancestral_peace",
        "quantum_healing",
    }
    actual = {pl.value for pl in PureLandTradition}
    assert actual == expected


# ---------------------------------------------------------------------------
# 3. PureLandDescriptions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pure_land_descriptions_returns_known_tradition():
    """get_description for a known tradition returns a populated dict."""
    desc = PureLandDescriptions.get_description(PureLandTradition.SUKHAVATI)
    assert isinstance(desc, dict)
    assert "name" in desc and "description" in desc and "activities" in desc
    assert "Sukhavati" in desc["name"]
    assert isinstance(desc["activities"], list) and len(desc["activities"]) >= 1
    assert isinstance(desc.get("sensory"), dict)


@pytest.mark.unit
def test_pure_land_descriptions_falls_back_to_universal_light():
    """Unknown / non-overridden tradition falls back to UNIVERSAL_LIGHT.

    Only 4 of the 10 traditions have full descriptions in DESCRIPTIONS;
    the others are expected to fall through to the universal default.
    """
    desc = PureLandDescriptions.get_description(PureLandTradition.QUANTUM_HEALING)
    fallback = PureLandDescriptions.get_description(PureLandTradition.UNIVERSAL_LIGHT)
    assert desc == fallback
    assert "Universal Light" in desc["name"]


# ---------------------------------------------------------------------------
# 4. NarrativeTemplateLibrary
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_narrative_template_library_pure_land_arrival_template():
    """The pure land arrival template is well-formed and references the right enum."""
    tpl = NarrativeTemplateLibrary.get_pure_land_arrival_template()
    assert isinstance(tpl, NarrativeTemplate)
    assert tpl.narrative_type == NarrativeType.PURE_LAND_ARRIVAL
    assert isinstance(tpl.title, str) and tpl.title
    # All list fields should be non-empty so story generation always has material
    for field_name in ("opening", "journey", "transformation", "resolution", "dedication"):
        value = getattr(tpl, field_name)
        assert isinstance(value, list) and value, f"Template field {field_name!r} is empty"
    assert "liberation" in tpl.tags


# ---------------------------------------------------------------------------
# 5. StoryGenerator (template path)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_story_generator_template_path_returns_generated_story():
    """StoryGenerator(use_llm=False) generates a populated GeneratedStory."""
    gen = StoryGenerator(use_llm=False)
    story = gen.generate_story(
        target_name="Test Being",
        narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
        pure_land=PureLandTradition.SUKHAVATI,
    )

    assert isinstance(story, GeneratedStory)
    assert story.target_name == "Test Being"
    assert story.narrative_type == NarrativeType.PURE_LAND_ARRIVAL
    assert story.pure_land == PureLandTradition.SUKHAVATI
    assert story.generation_method == "template"
    # Story body should mention the target and contain markdown
    assert "Test Being" in story.story_text
    assert "#" in story.story_text  # markdown header
    # Dedication joined as multi-line string
    assert isinstance(story.dedication, str) and story.dedication
    # Metadata carries template tags
    assert "template_tags" in story.metadata


@pytest.mark.unit
def test_story_generator_unknown_narrative_type_falls_back_to_pure_land_arrival():
    """Narrative types without a dedicated template fall back to pure land arrival."""
    gen = StoryGenerator(use_llm=False)
    story = gen.generate_story(
        target_name="Edge Case",
        narrative_type=NarrativeType.DIVINE_INTERVENTION,  # No dedicated template
    )
    # Should still succeed and tag the run as the *original* requested type
    assert story.narrative_type == NarrativeType.DIVINE_INTERVENTION
    # …but use the pure-land arrival template body (which has the only fallback)
    assert "Journey" in story.story_text  # section header from arrival template


# ---------------------------------------------------------------------------
# 6. StoryExporter
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_story_exporter_export_as_markdown_writes_file(tmp_path: Path):
    """export_as_markdown writes the story body verbatim to disk."""
    gen = StoryGenerator(use_llm=False)
    story = gen.generate_story(target_name="Markdown Tester")

    out = tmp_path / "story.md"
    StoryExporter.export_as_markdown(story, str(out))

    assert out.exists()
    assert out.read_text(encoding="utf-8") == story.story_text


@pytest.mark.unit
def test_story_exporter_export_as_json_round_trip(tmp_path: Path):
    """export_as_json produces a JSON file with all the dataclass fields."""
    gen = StoryGenerator(use_llm=False)
    story = gen.generate_story(
        target_name="JSON Tester",
        narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
        pure_land=PureLandTradition.SUKHAVATI,
    )

    out = tmp_path / "story.json"
    StoryExporter.export_as_json(story, str(out))

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["target_name"] == "JSON Tester"
    assert data["narrative_type"] == "pure_land_arrival"
    assert data["pure_land"] == "sukhavati"
    assert data["generation_method"] == "template"
    assert data["story_text"] == story.story_text
    assert isinstance(data["metadata"], dict)


@pytest.mark.unit
def test_story_exporter_export_collection_creates_index_and_files(tmp_path: Path):
    """export_collection writes a per-story file plus an INDEX.md manifest."""
    gen = StoryGenerator(use_llm=False)
    stories = [
        gen.generate_story(target_name="Being A"),
        gen.generate_story(target_name="Being B"),
    ]

    out_dir = tmp_path / "stories"
    StoryExporter.export_collection(stories, str(out_dir))

    index = out_dir / "INDEX.md"
    assert index.exists()
    content = index.read_text(encoding="utf-8")
    assert "Liberation Stories Collection" in content
    assert "Total Stories: 2" in content
    assert "Being A" in content and "Being B" in content

    # One markdown file per story
    md_files = [p for p in out_dir.glob("story_*.md")]
    assert len(md_files) == 2


# ---------------------------------------------------------------------------
# 7. Error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_story_exporter_export_as_markdown_propagates_oserror(tmp_path: Path):
    """export_as_markdown should propagate OSError when the path is invalid."""
    gen = StoryGenerator(use_llm=False)
    story = gen.generate_story(target_name="Doomed")

    # Point at a path inside a *file* (not a directory) so the open-for-write fails.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir")
    bad = blocker / "nested" / "story.md"

    with pytest.raises(OSError):
        StoryExporter.export_as_markdown(story, str(bad))


# ---------------------------------------------------------------------------
# 8. Internal LLM guard: use_llm=True without a working client downgrades
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_story_generator_use_llm_true_falls_back_when_llm_init_fails():
    """When use_llm=True but the LLM client constructor raises, the generator
    silently downgrades to template mode rather than crashing on construction.

    This is a contract test: the public ``generate_story`` must always return
    a valid :class:`GeneratedStory`, regardless of LLM availability.
    """
    # Patch the LLMIntegration class to blow up on construction. The generator
    # catches the exception, logs a warning, and falls back to template mode.
    with patch("core.blessing_narratives.LLMIntegration", side_effect=RuntimeError("boom")):
        gen = StoryGenerator(use_llm=True, llm_provider="ollama")
        # If init failed cleanly, llm_client should be None and use_llm downgraded
        assert gen.llm_client is None
        assert gen.use_llm is False
        story = gen.generate_story(target_name="Fallback Test")
        assert isinstance(story, GeneratedStory)
        assert story.generation_method == "template"
