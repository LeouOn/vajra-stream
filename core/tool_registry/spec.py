"""Tool specification type and surface names for the LLM tool registry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Surfaces: the places a tool is offered to a model or a caller.
# ---------------------------------------------------------------------------

#: Advertised to the Command Center chat model (``/api/v1/llm/chat*``) and to
#: the event-driven autonomous agent, which talks through the same chat path.
#: Ordered by ``CHAT_ORDER`` in the catalog.
CHAT = "chat"

#: Executable through the chat dispatcher (``execute_tool_locally``). A model
#: may call these by name even when they are not advertised on ``CHAT``.
AGENT = "agent"

#: Advertised to and executable by ``RadionicsOperator.chat`` and the
#: ``POST /api/v1/operator/dispatch`` endpoint (both via ``ToolDispatcher``).
OPERATOR = "operator"

#: Actions the autonomous operator proposes as suggestions. Each one carries
#: ``requires_approval`` and runs only from ``approve_suggestion``.
AUTONOMOUS = "autonomous"

ALL_SURFACES: tuple[str, ...] = (CHAT, AGENT, OPERATOR, AUTONOMOUS)

#: Allowed values in ``ToolSpec.result_provenance`` (plain strings matching the
#: shared provenance vocabulary).
PROVENANCE_KINDS: frozenset[str] = frozenset({"record", "computed", "draw", "decorative"})


@dataclass(frozen=True)
class ToolSpec:
    """One tool, defined once.

    ``handler`` is a ``"module:function"`` reference resolved at call time, so
    importing the registry never imports the handler module (which pulls in
    backend services). Handlers take keyword arguments; a handler that
    declares a ``container`` parameter receives the caller's DI container.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: str
    surfaces: frozenset[str]
    #: On the ``AUTONOMOUS`` surface the call needs explicit user approval.
    requires_approval: bool = False
    #: Other names models use for this tool. Resolved before dispatch.
    aliases: tuple[str, ...] = ()
    #: Tool-specific argument synonyms (``{"lat": "latitude"}``). Applied only
    #: when the canonical argument is absent.
    arg_aliases: Mapping[str, str] = field(default_factory=dict)
    #: On async surfaces, run a sync handler in a worker thread. ``False``
    #: keeps it on the event loop (needed by handlers that schedule tasks on
    #: the running loop).
    offload: bool = True
    #: Per-call time budget on the async chat job, in seconds.
    timeout_s: float | None = None
    #: The chat loop runs a successful call of this tool at most once per
    #: sitting (it mints content: an outlook, a prayer, a working).
    once_per_sitting: bool = False
    #: How the tool's result fields were produced, in the shared provenance
    #: vocabulary's ``{field: kind}`` shape (kinds: "record", "computed",
    #: "draw", "decorative"). ``None`` until a tool is labelled.
    result_provenance: Mapping[str, str] | None = None

    def on(self, surface: str) -> bool:
        return surface in self.surfaces
