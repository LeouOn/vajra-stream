"""Tests for the 3 new tool schemas added to backend/core/llm_agent/tools.py:
get_current_slide, stop_slideshow, update_population."""
import pytest

from backend.core.llm_agent.tools import get_tool_schemas


NEW_TOOL_NAMES = ["get_current_slide", "stop_slideshow", "update_population"]


@pytest.fixture
def all_schemas():
    return get_tool_schemas()


@pytest.fixture
def new_schemas(all_schemas):
    by_name = {s["name"]: s for s in all_schemas}
    return {name: by_name[name] for name in NEW_TOOL_NAMES if name in by_name}


def test_all_three_new_tools_are_registered(new_schemas):
    assert set(new_schemas.keys()) == set(NEW_TOOL_NAMES), (
        f"expected {NEW_TOOL_NAMES}, got {list(new_schemas.keys())}"
    )


def test_get_current_slide_requires_session_id(new_schemas):
    schema = new_schemas["get_current_slide"]
    assert "session_id" in schema["parameters"]["required"]
    assert "session_id" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["session_id"]["type"] == "string"


def test_stop_slideshow_requires_session_id(new_schemas):
    schema = new_schemas["stop_slideshow"]
    assert "session_id" in schema["parameters"]["required"]
    assert "session_id" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["session_id"]["type"] == "string"


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


def test_new_tool_names_are_unique_among_themselves(new_schemas):
    names = [schema["name"] for schema in new_schemas.values()]
    assert len(names) == 3
    assert len(set(names)) == 3, f"the 3 new tools share names: {names}"
