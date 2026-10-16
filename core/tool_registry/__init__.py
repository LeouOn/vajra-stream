"""The single LLM tool registry.

Every tool the models can call is defined once in :mod:`core.tool_registry.catalog`
as a :class:`ToolSpec`: public name, JSON schema, handler, surfaces and flags.
Every consumer reads from here:

- the chat path (``backend/app/api/v1/endpoints/llm.py``) advertises
  ``schemas(CHAT)`` and executes through :func:`acall` on ``AGENT``;
- the radionics operator (``modules/radionics_operator.py``) advertises
  ``schemas(OPERATOR)`` and executes through :func:`call` on ``OPERATOR``;
- the autonomous operator executes an approved suggestion through
  :func:`call` on ``AUTONOMOUS`` with ``approved=True``.

Importing this package never imports a handler module. Handlers are resolved
by ``"module:function"`` reference when a tool runs, so ``core`` gains no
import-time dependency on ``backend``.
"""

from __future__ import annotations

import asyncio
import copy
import functools
import importlib
import inspect
from collections.abc import Callable, Mapping
from typing import Any

from .catalog import CHAT_ORDER, GLOBAL_ARG_ALIASES, TOOL_SPECS
from .spec import AGENT, ALL_SURFACES, AUTONOMOUS, CHAT, OPERATOR, PROVENANCE_KINDS, ToolSpec

__all__ = [
    "AGENT",
    "ALL_SURFACES",
    "AUTONOMOUS",
    "CHAT",
    "CHAT_ORDER",
    "OPERATOR",
    "PROVENANCE_KINDS",
    "ApprovalRequiredError",
    "ToolSpec",
    "UnknownToolError",
    "acall",
    "call",
    "chat_tool_schemas",
    "get_spec",
    "handler_accepts_container",
    "once_per_sitting_names",
    "prepare_arguments",
    "resolve_handler",
    "resolve_name",
    "schemas",
    "specs",
    "sync_callables",
    "timeout_for",
    "tool_names",
]

#: Argument names a model may never set: the DI container is the caller's.
_RESERVED_ARGS = frozenset({"container"})


class UnknownToolError(KeyError):
    """No tool by this name (or alias) on the requested surface."""


class ApprovalRequiredError(PermissionError):
    """An approval-gated tool was called on ``AUTONOMOUS`` without approval."""


_BY_NAME: dict[str, ToolSpec] = {spec.name: spec for spec in TOOL_SPECS}
_ALIASES: dict[str, str] = {alias: spec.name for spec in TOOL_SPECS for alias in spec.aliases}


def _validate() -> None:
    """Fail loudly at import if the catalog contradicts itself."""
    if len(_BY_NAME) != len(TOOL_SPECS):
        raise ValueError("core.tool_registry: duplicate tool names in the catalog")
    clashes = set(_ALIASES) & set(_BY_NAME)
    if clashes or len(_ALIASES) != sum(len(s.aliases) for s in TOOL_SPECS):
        raise ValueError(f"core.tool_registry: alias clash {sorted(clashes)}")
    chat = {s.name for s in TOOL_SPECS if s.on(CHAT)}
    if chat != set(CHAT_ORDER) or len(CHAT_ORDER) != len(chat):
        raise ValueError("core.tool_registry: CHAT_ORDER must list exactly the CHAT specs")
    for spec in TOOL_SPECS:
        unknown = spec.surfaces - set(ALL_SURFACES)
        if unknown or not spec.surfaces:
            raise ValueError(f"core.tool_registry: {spec.name} has bad surfaces {sorted(spec.surfaces)}")
        if spec.on(CHAT) and not spec.on(AGENT):
            raise ValueError(f"core.tool_registry: {spec.name} is advertised on chat but not executable")
        if spec.on(AUTONOMOUS) and not spec.requires_approval:
            raise ValueError(f"core.tool_registry: autonomous tool {spec.name} must require approval")
        if spec.result_provenance is not None and not set(spec.result_provenance.values()) <= PROVENANCE_KINDS:
            raise ValueError(f"core.tool_registry: {spec.name} has an unknown provenance kind")


_validate()


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def resolve_name(name: str) -> str:
    """Map an alias to its tool name; any other name passes through."""
    return _ALIASES.get(name, name)


def get_spec(name: str, surface: str | None = None) -> ToolSpec:
    """Return the spec for ``name`` (or an alias), optionally on ``surface``."""
    spec = _BY_NAME.get(resolve_name(name))
    if spec is None or (surface is not None and not spec.on(surface)):
        where = f" on surface {surface!r}" if surface else ""
        raise UnknownToolError(f"Tool {name} not found{where}")
    return spec


def specs(surface: str | None = None) -> list[ToolSpec]:
    """Specs on ``surface`` in their advertised order (``CHAT_ORDER`` for chat)."""
    if surface == CHAT:
        return [_BY_NAME[name] for name in CHAT_ORDER]
    return [spec for spec in TOOL_SPECS if surface is None or spec.on(surface)]


def tool_names(surface: str | None = None) -> list[str]:
    return [spec.name for spec in specs(surface)]


def schemas(surface: str, fmt: str = "plain") -> list[dict[str, Any]]:
    """Schemas for ``surface``.

    ``fmt``: ``"plain"`` (``name``/``description``/``parameters``),
    ``"openai"`` (``{"type": "function", "function": {...}}``) or
    ``"anthropic"`` (``name``/``description``/``input_schema``).
    """
    out: list[dict[str, Any]] = []
    for spec in specs(surface):
        params = copy.deepcopy(spec.parameters)
        if fmt == "plain":
            out.append({"name": spec.name, "description": spec.description, "parameters": params})
        elif fmt == "openai":
            out.append(
                {
                    "type": "function",
                    "function": {"name": spec.name, "description": spec.description, "parameters": params},
                }
            )
        elif fmt == "anthropic":
            out.append({"name": spec.name, "description": spec.description, "input_schema": params})
        else:
            raise ValueError(f"Unknown schema format: {fmt}")
    return out


def chat_tool_schemas() -> list[dict[str, Any]]:
    """The advertised chat allowlist, in ``CHAT_ORDER``."""
    return schemas(CHAT)


def once_per_sitting_names() -> frozenset[str]:
    return frozenset(spec.name for spec in TOOL_SPECS if spec.once_per_sitting)


def timeout_for(name: str, default: float) -> float:
    spec = _BY_NAME.get(resolve_name(name))
    if spec is None or spec.timeout_s is None:
        return default
    return spec.timeout_s


# ---------------------------------------------------------------------------
# Handlers and arguments
# ---------------------------------------------------------------------------


def resolve_handler(spec: ToolSpec) -> Callable[..., Any]:
    """Import and return the handler (looked up on every call, so patches apply)."""
    module_name, _, attr = spec.handler.partition(":")
    fn: Callable[..., Any] = getattr(importlib.import_module(module_name), attr)
    return fn


def _parameters(fn: Callable[..., Any]) -> tuple[set[str], bool]:
    sig = inspect.signature(fn)
    named = {
        n
        for n, p in sig.parameters.items()
        if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    return named, var_kw


def handler_accepts_container(spec: ToolSpec) -> bool:
    named, _ = _parameters(resolve_handler(spec))
    return "container" in named


def _coerce(value: Any, prop: Any) -> Any:
    """Coerce a string argument to its schema type (text-parsed tool calls send strings)."""
    if not isinstance(value, str) or not isinstance(prop, Mapping):
        return value
    kind = prop.get("type")
    text = value.strip()
    try:
        if kind == "integer":
            return int(float(text))
        if kind == "number":
            return float(text)
    except ValueError:
        return value
    if kind == "boolean":
        lowered = text.lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    return value


def prepare_arguments(
    spec: ToolSpec, args: Mapping[str, Any] | None, fn: Callable[..., Any] | None = None
) -> dict[str, Any]:
    """Turn model-emitted arguments into handler keyword arguments.

    1. Tool-specific synonyms (``spec.arg_aliases``) fill an absent argument.
    2. Global synonyms apply only when the tool does not accept the original
       name but does accept the target.
    3. ``None`` values and arguments the handler does not take are dropped;
       ``container`` is never taken from the model.
    4. Strings are coerced to the schema's integer/number/boolean type.
    """
    fn = fn or resolve_handler(spec)
    named, var_kw = _parameters(fn)
    named -= _RESERVED_ARGS
    props = spec.parameters.get("properties") or {}
    accepted = named | set(props)

    raw = dict(args or {})
    for alias, target in spec.arg_aliases.items():
        if alias in raw:
            value = raw.pop(alias)
            if raw.get(target) is None:
                raw[target] = value
    for key in list(raw):
        if key in accepted:
            continue
        mapped = GLOBAL_ARG_ALIASES.get(key)
        if mapped and mapped in accepted and raw.get(mapped) is None:
            raw[mapped] = raw.pop(key)

    out: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None or key in _RESERVED_ARGS:
            continue
        if key in named or var_kw:
            out[key] = _coerce(value, props.get(key))
    return out


def _check_approval(spec: ToolSpec, surface: str | None, approved: bool) -> None:
    if surface == AUTONOMOUS and spec.requires_approval and not approved:
        raise ApprovalRequiredError(f"Tool {spec.name} requires user approval on the autonomous surface")


def _bind(spec: ToolSpec, args: Mapping[str, Any] | None, container: Any) -> tuple[Callable[..., Any], dict[str, Any]]:
    fn = resolve_handler(spec)
    kwargs = prepare_arguments(spec, args, fn)
    if container is not None and "container" in _parameters(fn)[0]:
        kwargs["container"] = container
    return fn, kwargs


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def call(
    name: str,
    args: Mapping[str, Any] | None = None,
    *,
    surface: str | None = None,
    container: Any = None,
    approved: bool = False,
) -> Any:
    """Run a tool from synchronous code.

    An async handler runs on the persistent background loop
    (``core.llm.legacy_adapter.run_async``), which is safe inside a running
    event loop as well.
    """
    spec = get_spec(name, surface)
    _check_approval(spec, surface, approved)
    fn, kwargs = _bind(spec, args, container)
    if inspect.iscoroutinefunction(fn):
        from core.llm.legacy_adapter import run_async

        return run_async(fn(**kwargs))
    return fn(**kwargs)


async def acall(
    name: str,
    args: Mapping[str, Any] | None = None,
    *,
    surface: str | None = None,
    container: Any = None,
    approved: bool = False,
) -> Any:
    """Run a tool from async code.

    Async handlers are awaited on the current loop. Sync handlers run in a
    worker thread unless the spec sets ``offload=False``.
    """
    spec = get_spec(name, surface)
    _check_approval(spec, surface, approved)
    fn, kwargs = _bind(spec, args, container)
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    if spec.offload:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(fn, **kwargs))
    return fn(**kwargs)


def sync_callables(surface: str = AGENT) -> dict[str, Callable[..., Any]]:
    """``{name or alias: callable(**kwargs)}`` for ``surface`` (one callable per tool)."""
    table: dict[str, Callable[..., Any]] = {}
    for spec in specs(surface):

        def _run(_name: str = spec.name, **kwargs: Any) -> Any:
            return call(_name, kwargs, surface=surface)

        _run.__name__ = spec.name
        _run.__doc__ = spec.description
        table[spec.name] = _run
        for alias in spec.aliases:
            table[alias] = _run
    return table
