# core/context/base.py
"""ContextModule Protocol and SystemPromptBuilder."""
from __future__ import annotations

import asyncio
import logging

from core.context.models import ContextData, ContextRequest

logger = logging.getLogger(__name__)


class ContextModule:
    """Protocol that all context modules must satisfy.

    Implementations gather structured data asynchronously (``gather``) and
    format it into a Markdown section synchronously (``render``).  Both
    methods must be defensive: ``gather`` returns a :class:`ContextData`
    with ``error`` set instead of raising; ``render`` returns ``""`` on
    bad or empty data instead of raising.
    """

    name: str

    async def gather(self, request: ContextRequest) -> ContextData:  # pragma: no cover - protocol
        ...

    def render(self, data: ContextData) -> str:  # pragma: no cover - protocol
        ...


class SystemPromptBuilder:
    """Composes a system prompt from registered :class:`ContextModule` instances.

    ``compose`` gathers every module's data concurrently via
    :func:`asyncio.gather` then renders each result sequentially.  Modules
    whose ``gather`` or ``render`` raises are logged and skipped so a single
    broken module never prevents the rest from contributing.
    """

    def __init__(self) -> None:
        self._modules: list[ContextModule] = []

    @property
    def modules(self) -> list[ContextModule]:
        """Return a shallow copy of the registered modules."""
        return list(self._modules)

    def register(self, module: ContextModule) -> None:
        """Append *module* to the composition pipeline."""
        self._modules.append(module)

    async def compose(
        self, request: ContextRequest, base_prompt: str = ""
    ) -> str:
        """Gather all modules in parallel, render sequentially, skip failures.

        The optional ``base_prompt`` is prepended so callers don't need to
        concatenate strings themselves. If provided, the returned string is
        ``base_prompt + "\n\n" + <rendered sections>``. If no modules
        contribute anything, ``base_prompt`` is returned verbatim.
        """
        if not self._modules:
            return base_prompt

        results = await asyncio.gather(
            *(self._safe_gather(m, request) for m in self._modules),
        )

        sections: list[str] = []
        for module, data in zip(self._modules, results, strict=False):
            if data.error is not None:
                logger.debug("Skipping render for '%s': gather reported error", module.name)
                continue
            rendered = self._safe_render(module, data)
            if rendered:
                sections.append(rendered)

        body = "\n\n".join(sections)
        if base_prompt and body:
            return f"{base_prompt}\n\n{body}"
        return body or base_prompt

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    async def _safe_gather(
        module: ContextModule, request: ContextRequest
    ) -> ContextData:
        """Call ``module.gather`` defensively, returning error ContextData on failure."""
        try:
            return await module.gather(request)
        except Exception as exc:  # noqa: BLE001 — builder must survive any module
            logger.warning("ContextModule '%s' gather() raised: %s", module.name, exc)
            return ContextData(module_name=getattr(module, "name", "unknown"), error=str(exc))

    @staticmethod
    def _safe_render(module: ContextModule, data: ContextData) -> str:
        """Call ``module.render`` defensively, returning "" on failure."""
        try:
            return module.render(data)
        except Exception as exc:  # noqa: BLE001 — builder must survive any module
            logger.warning("ContextModule '%s' render() raised: %s", module.name, exc)
            return ""
