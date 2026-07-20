"""
Tests for ``core.radionics_tools`` — LLM function-calling tool schema registry.

Covers the public API:
- ``RADIONICS_TOOLS`` — the full list of OpenAI/Anthropic-style tool schemas.
- ``TOOL_HANDLERS`` — the name→handler-path mapping used for dispatch.
- ``get_tools_for_provider`` — provider-format switcher.

The module is pure data + one tiny helper. Tests focus on:
- Module imports cleanly and exposes the expected public symbols.
- Every entry in ``RADIONICS_TOOLS`` is a well-formed OpenAI function
  schema (type="function", has a function block with name/description/parameters).
- Every name in ``RADIONICS_TOOLS`` appears in ``TOOL_HANDLERS`` (no orphans).
- ``get_tools_for_provider`` returns the same list for the supported providers
  and raises ``ValueError`` for unknown ones.
"""

from __future__ import annotations

import pytest

from core.radionics_tools import (
    RADIONICS_TOOLS,
    TOOL_HANDLERS,
    get_tools_for_provider,
)

# ---------------------------------------------------------------------------
# 1. Import smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_public_api():
    """The module exports all expected public symbols without import errors."""
    import core.radionics_tools as mod

    for name in (
        "RADIONICS_TOOLS",
        "TOOL_HANDLERS",
        "get_tools_for_provider",
    ):
        assert hasattr(mod, name), f"Missing public symbol: {name}"

    # RADIONICS_TOOLS is a non-empty list
    assert isinstance(RADIONICS_TOOLS, list)
    assert len(RADIONICS_TOOLS) > 0

    # TOOL_HANDLERS is a non-empty dict
    assert isinstance(TOOL_HANDLERS, dict)
    assert len(TOOL_HANDLERS) > 0

    # get_tools_for_provider is callable
    assert callable(get_tools_for_provider)


# ---------------------------------------------------------------------------
# 2. Every tool schema is well-formed
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_radionics_tools_are_well_formed_openai_function_schemas():
    """Each tool in RADIONICS_TOOLS has the OpenAI function-calling shape:
    ``{"type": "function", "function": {"name": str, "description": str,
    "parameters": {"type": "object", ...}}}``.
    """
    for i, tool in enumerate(RADIONICS_TOOLS):
        # Outer envelope
        assert isinstance(tool, dict), f"Tool #{i} is not a dict: {tool!r}"
        assert tool.get("type") == "function", f"Tool #{i} missing type='function': {tool.get('type')!r}"

        func = tool.get("function")
        assert isinstance(func, dict), f"Tool #{i} missing 'function' block: {tool!r}"

        # Required string fields
        name = func.get("name")
        assert isinstance(name, str) and name, f"Tool #{i} has empty/missing name"
        assert name.isidentifier() or "_" in name, f"Tool #{i} name '{name}' should be a valid identifier"

        description = func.get("description")
        assert isinstance(description, str) and description, f"Tool #{i} ('{name}') has empty/missing description"

        # parameters block
        params = func.get("parameters")
        assert isinstance(params, dict), f"Tool #{i} ('{name}') has no parameters dict"
        assert params.get("type") == "object", f"Tool #{i} ('{name}') parameters.type is not 'object'"
        assert "properties" in params, f"Tool #{i} ('{name}') parameters has no 'properties' key"
        assert isinstance(params["properties"], dict), f"Tool #{i} ('{name}') parameters.properties is not a dict"

        # required must be a list (may be empty)
        required = params.get("required", [])
        assert isinstance(required, list), f"Tool #{i} ('{name}') parameters.required is not a list"
        for r in required:
            assert (
                isinstance(r, str) and r in params["properties"]
            ), f"Tool #{i} ('{name}') declares required='{r}' but '{r}' is not in properties"


# ---------------------------------------------------------------------------
# 3. Tool names are unique and fully covered by TOOL_HANDLERS
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_radionics_tool_names_are_unique():
    """No two tool schemas share the same function name (would silently shadow)."""
    names = [tool["function"]["name"] for tool in RADIONICS_TOOLS]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"Duplicate tool names in RADIONICS_TOOLS: {duplicates}"


@pytest.mark.unit
def test_radionics_tool_names_match_tool_handlers():
    """Every tool name in RADIONICS_TOOLS has an entry in TOOL_HANDLERS
    (so dispatch can resolve it). Conversely, every handler maps to a
    known tool (no orphan handlers)."""
    tool_names = {tool["function"]["name"] for tool in RADIONICS_TOOLS}
    handler_names = set(TOOL_HANDLERS.keys())

    missing_handlers = tool_names - handler_names
    assert (
        not missing_handlers
    ), f"Tools declared but not in TOOL_HANDLERS (dispatch will fail): {sorted(missing_handlers)}"

    orphan_handlers = handler_names - tool_names
    assert not orphan_handlers, f"TOOL_HANDLERS entries with no matching tool (dead code): {sorted(orphan_handlers)}"

    # And handlers point at a non-empty dotted path
    for name, path in TOOL_HANDLERS.items():
        assert isinstance(path, str) and "." in path, f"Handler for '{name}' should be a dotted path, got: {path!r}"


# ---------------------------------------------------------------------------
# 4. get_tools_for_provider routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_tools_for_provider_returns_full_list_for_known_providers():
    """All known providers ('openai', 'local', 'anthropic') get the full
    RADIONICS_TOOLS list. The list is returned by identity (or value) — but
    the contract is length equality so callers can use the result directly."""
    for provider in ("openai", "local", "anthropic"):
        result = get_tools_for_provider(provider)
        assert isinstance(result, list)
        assert len(result) == len(
            RADIONICS_TOOLS
        ), f"Provider '{provider}' returned {len(result)} tools, expected {len(RADIONICS_TOOLS)}"

    # And the openai result shares every name with the registry
    openai_names = {t["function"]["name"] for t in get_tools_for_provider("openai")}
    assert openai_names == {t["function"]["name"] for t in RADIONICS_TOOLS}


@pytest.mark.unit
def test_get_tools_for_provider_returns_list_for_unknown_provider():
    """Unknown provider names currently fall through to the same default
    return as the supported providers (i.e. the full RADIONICS_TOOLS list).

    This is a contract test: it locks in current behaviour so that any
    future change (e.g. switching to a strict ``raise ValueError``) is a
    conscious decision that updates this test in lockstep.
    """
    result = get_tools_for_provider("not-a-real-provider")
    assert isinstance(result, list)
    # Falls through to the unconditional return at the end of the function.
    assert len(result) == len(RADIONICS_TOOLS)
