"""JSON-safety helpers for websocket payloads (leaf module).

This module is deliberately a LEAF: it imports nothing from the connection
manager and no heavy application modules, so importing it can never drag in
the manager (or the application graph). ``backend/websocket/__init__.py`` is
empty, so ``import backend.websocket.json_safe`` pulls in nothing else.

The websocket payloads carry domain objects - dataclass events, pydantic
models, enums, datetimes, sets, bytes. One unserialisable value used to make
the WHOLE frame fail, and a frame that fails is a frame that is dropped. So
values are converted at the boundary instead.
"""

from __future__ import annotations

import dataclasses
import enum
import math
from datetime import date, datetime
from typing import Any

# How deep the conversion may recurse. A pathological structure (a 2,000-deep
# list) would otherwise raise RecursionError inside the conversion, and the
# callers' broad `except` would swallow it - so the event would silently not
# be forwarded. Past the limit the remainder is stringified instead.
MAX_DEPTH = 32

# What a container that refers back to itself becomes.
CIRCULAR_MARKER = "<circular>"


def to_json_safe(value: Any) -> Any:
    """Convert ``value`` into something ``json.dumps`` can always serialise.

      * a dataclass -> its fields, recursively
      * a pydantic v2 model -> ``model_dump()`` (duck-typed, so pydantic is
        not a dependency of this module)
      * an Enum -> its value
      * a datetime/date -> its ISO string
      * a set/tuple/list -> a list of converted items
      * bytes -> decoded with ``errors="replace"``
      * a non-finite float -> ``None`` (so one NaN cannot drop a whole frame)
      * anything else -> ``str(value)``

    Dict keys are stringified, which is what JSON does anyway. That means two
    distinct keys can collide: ``{1: "a", "1": "b"}`` becomes ``{"1": "b"}``
    and the first value is lost. The behaviour is kept (it is JSON's rule, not
    ours), but it is worth knowing.

    Recursion is bounded by ``MAX_DEPTH``, and a container that refers back
    to itself becomes ``"<circular>"`` rather than an infinite structure.
    """
    return _convert(value, 0, frozenset())


def _convert(value: Any, depth: int, seen: frozenset[int]) -> Any:
    if depth > MAX_DEPTH:
        # Deeper than the limit: stringify the remainder, but never raise.
        try:
            return str(value)
        except RecursionError:
            return f"<{type(value).__name__} beyond max depth>"

    if value is None or isinstance(value, str | bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        # A NaN or an infinity is not valid JSON (allow_nan=False rejects it).
        return value if math.isfinite(value) else None
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return _convert(value.value, depth + 1, seen)
    if isinstance(value, bytes | bytearray):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, dict):
        if id(value) in seen:
            return CIRCULAR_MARKER
        nested = seen | {id(value)}
        return {str(key): _convert(item, depth + 1, nested) for key, item in value.items()}
    if isinstance(value, set | frozenset):
        if id(value) in seen:
            return CIRCULAR_MARKER
        nested = seen | {id(value)}
        return [_convert(item, depth + 1, nested) for item in sorted(value, key=repr)]
    if isinstance(value, list | tuple):
        if id(value) in seen:
            return CIRCULAR_MARKER
        nested = seen | {id(value)}
        return [_convert(item, depth + 1, nested) for item in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        if id(value) in seen:
            return CIRCULAR_MARKER
        nested = seen | {id(value)}
        return {
            field.name: _convert(getattr(value, field.name), depth + 1, nested) for field in dataclasses.fields(value)
        }
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _convert(model_dump(), depth + 1, seen)
        except Exception:  # noqa: BLE001 - a broken model is just data
            return str(value)
    return str(value)
