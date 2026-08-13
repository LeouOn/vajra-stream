"""Tests for essential tool schemas in backend/core/llm_agent/tools.py:
generate_image, generate_prayer, update_population.

Note: get_current_slide / stop_slideshow were removed from the LLM tool
exposure by the "reduce tools to 28 essentials" trim (they remain in the
TOOL_REGISTRY for direct dispatch but are no longer exposed to the LLM).
"""

import pytest

from backend.app.api.v1.endpoints.llm import _prioritize_tool_schemas
from backend.core.llm_agent.tools import ESSENTIAL_TOOL_ORDER, get_tool_schemas

NEW_TOOL_NAMES = ["generate_image", "generate_prayer", "update_population"]


@pytest.fixture
def all_schemas():
    return get_tool_schemas()


@pytest.fixture
def new_schemas(all_schemas):
    by_name = {s["name"]: s for s in all_schemas}
    return {name: by_name[name] for name in NEW_TOOL_NAMES if name in by_name}


def test_all_three_new_tools_are_registered(new_schemas):
    assert set(new_schemas.keys()) == set(NEW_TOOL_NAMES), f"expected {NEW_TOOL_NAMES}, got {list(new_schemas.keys())}"


def test_generate_image_has_prompt_required(new_schemas):
    schema = new_schemas["generate_image"]
    assert "prompt" in schema["parameters"]["required"]
    assert "prompt" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["prompt"]["type"] == "string"


def test_generate_prayer_has_intention_parameter(new_schemas):
    schema = new_schemas["generate_prayer"]
    props = schema["parameters"]["properties"]
    assert "intention" in props
    assert props["intention"]["type"] == "string"


def test_update_population_accepts_priority_and_flags(new_schemas):
    schema = new_schemas["update_population"]
    props = schema["parameters"]["properties"]
    assert "population_id" in props
    assert props["population_id"]["type"] == "string"
    assert "priority" in props
    assert props["priority"]["type"] == "integer"
    assert "is_urgent" in props
    assert props["is_urgent"]["type"] == "boolean"
    assert "is_active" in props
    assert props["is_active"]["type"] == "boolean"
    assert "population_id" in schema["parameters"]["required"]


def test_each_new_tool_has_a_meaningful_description(new_schemas):
    for name, schema in new_schemas.items():
        desc = schema.get("description", "")
        assert len(desc) > 20, f"{name}: description too short: {desc!r}"


def test_speak_text_has_a_schema():
    by_name = {s["name"]: s for s in get_tool_schemas()}
    assert "speak_text" in by_name
    assert "text" in by_name["speak_text"]["parameters"]["required"]


def test_prioritize_matches_essential_order():
    schemas = get_tool_schemas()
    prioritized = _prioritize_tool_schemas(schemas, 50)
    names = [s["name"] for s in prioritized]
    expected = [n for n in ESSENTIAL_TOOL_ORDER if n in {s["name"] for s in schemas}]
    assert names == expected
    assert "speak_text" in names


def test_new_tool_names_are_unique_among_themselves(new_schemas):
    names = [schema["name"] for schema in new_schemas.values()]
    assert len(names) == 3
    assert len(set(names)) == 3, f"the 3 new tools share names: {names}"
