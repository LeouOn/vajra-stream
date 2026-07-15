# core/context/models.py
"""Pydantic models for the context module layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContextRequest(BaseModel):
    """Parameters controlling which context modules gather data.

    Each ``include_*`` flag gates the corresponding built-in module.  When a
    caller has *pre-computed* data (for example astrology data resolved
    earlier in the request lifecycle) it can be supplied via ``astrology_data``
    so the module skips the expensive recalculation.
    """

    include_astrology: bool = False
    include_anatomy: bool = False
    include_hardware: bool = False
    astrology_data: dict[str, Any] | None = None

    #: Free-form bag for module-specific configuration.
    extra: dict[str, Any] = Field(default_factory=dict)


class ContextData(BaseModel):
    """Payload returned by a single :class:`ContextModule.gather` call.

    ``data`` holds whatever structured information the module collected.
    When ``error`` is set the module should be skipped during rendering.
    """

    module_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
