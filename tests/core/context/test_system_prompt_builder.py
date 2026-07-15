# tests/core/context/test_base.py
"""Tests for ContextModule Protocol and SystemPromptBuilder."""

from __future__ import annotations

from core.context.base import SystemPromptBuilder
from core.context.models import ContextData, ContextRequest


class FakeModule:
    """Minimal ContextModule implementation for testing the builder."""

    def __init__(
        self,
        name: str = "fake",
        flag_key: str | None = None,
        fail_gather: bool = False,
        fail_render: bool = False,
    ) -> None:
        self.name = name
        self._flag_key = flag_key
        self._fail_gather = fail_gather
        self._fail_render = fail_render
        self.gather_called = False
        self.render_called = False

    async def gather(self, request: ContextRequest) -> ContextData:
        self.gather_called = True
        if self._fail_gather:
            raise RuntimeError(f"{self.name} gather boom")
        if self._flag_key is not None and not getattr(request, self._flag_key, True):
            return ContextData(module_name=self.name)
        return ContextData(module_name=self.name, data={"text": f"{self.name}-section"})

    def render(self, data: ContextData) -> str:
        self.render_called = True
        if self._fail_render:
            raise RuntimeError(f"{self.name} render boom")
        if not data.data:
            return ""
        return f"[{self.name}: {data.data['text']}]"


async def test_compose_no_modules_returns_empty_string():
    """A builder with no registered modules composes an empty prompt."""
    builder = SystemPromptBuilder()
    result = await builder.compose(ContextRequest())
    assert result == ""


async def test_compose_single_module_returns_rendered_section():
    """A single registered module appears in the composed prompt."""
    builder = SystemPromptBuilder()
    mod = FakeModule(name="solo")
    builder.register(mod)
    result = await builder.compose(ContextRequest())
    assert "[solo: solo-section]" in result


async def test_compose_only_runs_requested_modules():
    """Modules whose request flag is off produce no output."""
    builder = SystemPromptBuilder()
    astro = FakeModule(name="astrology", flag_key="include_astrology")
    anatomy = FakeModule(name="anatomy", flag_key="include_anatomy")
    builder.register(astro)
    builder.register(anatomy)

    request = ContextRequest(include_astrology=True, include_anatomy=False)
    result = await builder.compose(request)

    assert "astrology" in result
    assert "anatomy" not in result


async def test_compose_continues_past_module_error():
    """When one module raises, the rest still contribute to the prompt."""
    builder = SystemPromptBuilder()
    failing = FakeModule(name="broken", fail_gather=True)
    good = FakeModule(name="good")
    builder.register(failing)
    builder.register(good)

    result = await builder.compose(ContextRequest())

    assert "good" in result
    assert "broken" not in result
