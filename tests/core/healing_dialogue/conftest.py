# tests/core/healing_dialogue/conftest.py
"""Shared test doubles for healing-dialogue tests.

These were previously duplicated verbatim in:

* ``tests/core/healing_dialogue/test_service.py``
* ``tests/backend/test_healing_endpoints.py``

Importing tests in the same directory can do ``from conftest import ...``;
cross-directory tests (e.g. ``tests/backend/``) must add this directory to
``sys.path`` before importing, see ``test_healing_endpoints.py`` for the
one-line shim.
"""

from __future__ import annotations

from typing import Any


class StubDialogue:
    """Stand-in for AsyncHealingDialogue whose respond() returns a canned dict.

    Tests can mutate ``next_response`` between calls to simulate different LLM
    turns. ``calls`` records every invocation for assertions.
    """

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.next_response: dict[str, Any] = response or {
            "content": "I am here with you.",
            "phase_hint": None,
            "insights_update": {},
        }
        self.calls: list[dict[str, Any]] = []

    async def respond(self, **kwargs: Any) -> dict[str, Any]:
        # Record a shallow copy so later mutations don't rewrite history.
        self.calls.append({"kwargs": dict(kwargs), "result": dict(self.next_response)})
        return dict(self.next_response)


class FakeEmptyRegistry:
    """Registry stub whose pick_best() always returns None.

    Used so the summary path takes the deterministic fallback (no LLM call).
    """

    async def pick_best(self):
        return None
