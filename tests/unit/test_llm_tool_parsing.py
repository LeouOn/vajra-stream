"""Tests for text-mode tool-call parsing and alias resolution."""

from unittest.mock import patch

import pytest


class TestParseTextToolCalls:
    def _parse(self, content):
        from backend.app.api.v1.endpoints.llm import _parse_text_tool_calls

        return _parse_text_tool_calls(content)

    def test_inline_json_tool_format(self):
        content = 'Here is the result: {"tool": "list_targets", "arguments": {}}'
        result = self._parse(content)
        assert len(result) == 1
        assert result[0]["name"] == "list_targets"
        assert result[0]["arguments"] == {}

    def test_fenced_json_block(self):
        content = (
            'I will call the tool:\n```json\n{"tool": "start_automation", "arguments": {"population_id": "abc"}}\n```'
        )
        result = self._parse(content)
        assert len(result) == 1
        assert result[0]["name"] == "start_automation"
        assert result[0]["arguments"] == {"population_id": "abc"}

    def test_name_and_parameters_format(self):
        content = '{"name": "forge_sigil", "parameters": {"intention": "peace"}}'
        result = self._parse(content)
        assert len(result) == 1
        assert result[0]["name"] == "forge_sigil"
        assert result[0]["arguments"] == {"intention": "peace"}

    def test_no_tool_call_in_plain_text(self):
        content = "Hello! I can help you with radionics operations."
        result = self._parse(content)
        assert len(result) == 0

    def test_multiple_tool_calls(self):
        content = '{"tool": "list_populations", "arguments": {}} and {"tool": "get_rng_reading", "arguments": {"session_id": "s1"}}'
        result = self._parse(content)
        assert len(result) >= 1

    def test_malformed_json_ignored(self):
        content = '{"tool": "broken", "arguments":'
        result = self._parse(content)
        assert len(result) == 0

    def test_empty_arguments(self):
        content = '{"tool": "cast_i_ching", "arguments": {}}'
        result = self._parse(content)
        assert len(result) == 1
        assert result[0]["arguments"] == {}


class TestToolNameAliases:
    def test_list_targets_resolves_to_list_populations(self):
        from backend.app.api.v1.endpoints.llm import _resolve_tool_name

        assert _resolve_tool_name("list_targets") == "list_populations"

    def test_unknown_name_passes_through(self):
        from backend.app.api.v1.endpoints.llm import _resolve_tool_name

        assert _resolve_tool_name("forge_sigil") == "forge_sigil"

    def test_list_targets_in_registry(self):
        from backend.core.llm_agent.tools import TOOL_REGISTRY

        assert "list_targets" in TOOL_REGISTRY
        assert TOOL_REGISTRY["list_targets"] is TOOL_REGISTRY["list_populations"]


class TestExecuteToolAliasResolution:
    @pytest.mark.asyncio
    async def test_execute_list_targets_calls_list_populations(self):
        from backend.app.api.v1.endpoints.llm import execute_tool_locally

        with patch("backend.app.api.v1.endpoints.llm.get_population_manager") as mock_pm:
            mock_pm.return_value.get_all_populations.return_value = []
            result = await execute_tool_locally("list_targets", {})
            assert isinstance(result, list)
