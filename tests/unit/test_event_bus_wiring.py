#!/usr/bin/env python3
"""
Wave 4 Task 23 — Shared event bus wiring (ADR 003).

Behaviour-lock + RED tests for the canonical event-bus injection contract.
The pre-fix defect lives at ``modules/radionics_operator.py:684``::

    self.event_bus = event_bus or EnhancedEventBus()

The ``or EnhancedEventBus()`` branch silently mints a SECOND bus instance any
time the ``event_bus`` argument is omitted — fracturing pub/sub. Today
``container.py:198`` always supplies ``self.event_bus``, so production has
been spared; but any future caller (test fixture, refactor, ad-hoc
instantiation) that forgets the argument silently gets a private bus:
publishes invisible, subscriptions orphaned.

This file locks in TWO things:

1. **Behaviour-lock (ADR 003 EC1 mitigation)** — the *correct* production
   wiring must keep working after the fix. ``container.operator`` must share
   the canonical bus identity with ``container.event_bus``, and a publish on
   one side must be observed by a subscriber on the other. These tests PASS
   today and must PASS after the fix — they are regression guards.

2. **RED (strict TDD)** — the latent bug must be eliminated. Direct
   instantiation of ``RadionicsOperator`` without a bus must NOT silently
   mint a private ``EnhancedEventBus``, and the ``EnhancedEventBus(``
   constructor call must be ABSENT from all production code. These tests
   FAIL today (fallback fires) and PASS after the fix.

Reference: ``docs/decisions/003-orchestrator-canonical.md``
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

# Repository root = parents[2] up from this test file
# (tests/unit/test_event_bus_wiring.py -> tests/unit -> tests -> root)
REPO_ROOT = Path(__file__).resolve().parents[2]


# ============================================================================
# Behaviour-lock (ADR 003 EC1) — regression guards for the CORRECT wiring.
# These PASS before the fix and must PASS after the fix.
# ============================================================================


def test_container_operator_shares_canonical_event_bus_identity(fresh_container):
    """``container.operator.event_bus`` MUST be the very same instance as
    ``container.event_bus``.

    This is the single-bus invariant: the canonical bus created at
    ``container.py:43`` (``self.event_bus = SimpleEventBus()``) is the ONE
    bus the operator subscribes/publishes on. If identity ever breaks, every
    cross-service event (blessing → audio → radionics) silently fractures.
    """
    operator = fresh_container.operator
    assert operator.event_bus is fresh_container.event_bus, (
        "RadionicsOperator.event_bus is NOT the canonical container.event_bus "
        "instance. Pub/sub is fractured. See ADR 003 §'Event Bus Injection Plan'."
    )


@pytest.mark.asyncio
async def test_publish_on_container_bus_reaches_operator_subscriber(fresh_container):
    """An ``OperatorInsightGenerated`` event published on ``container.event_bus``
    MUST be observed by a handler subscribed through ``container.operator``
    within 2 seconds.

    This is the cross-bus delivery guarantee. The handler is registered on the
    operator's bus (``operator.event_bus.subscribe(...)``); the publish happens
    on the container's bus. If the two buses are the same instance (the
    contract), delivery is immediate. If they are split (the latent bug),
    the handler never fires and this test times out.
    """
    from modules.radionics_operator import OperatorInsightGenerated

    operator = fresh_container.operator

    # Identity precondition — if this fails, the delivery assertion below is
    # testing the wrong thing.
    assert operator.event_bus is fresh_container.event_bus

    received: list = []
    seen = asyncio.Event()

    def handler(event):
        received.append(event)
        seen.set()

    # Subscribe through the OPERATOR's bus — the production path for any
    # component that wants operator insights.
    operator.event_bus.subscribe(OperatorInsightGenerated, handler)

    # Publish on the CONTAINER's bus — the canonical bus other services use.
    fresh_container.event_bus.publish(
        OperatorInsightGenerated(
            insight_type="wiring_probe",
            content={"message": "cross-bus delivery check"},
        )
    )

    # Must arrive within 2s. Sync handlers fire inside publish(), so this
    # resolves immediately when the bus is shared; it times out when split.
    await asyncio.wait_for(seen.wait(), timeout=2.0)
    assert len(received) == 1
    assert received[0].insight_type == "wiring_probe"
    assert received[0].content["message"] == "cross-bus delivery check"


# ============================================================================
# RED (strict TDD) — the latent bug. These FAIL before the fix, PASS after.
# ============================================================================


def test_no_silent_private_bus_when_event_bus_not_injected():
    """RED: ``RadionicsOperator()`` with no ``event_bus`` MUST NOT silently
    mint a private ``EnhancedEventBus``.

    Before fix (``radionics_operator.py:684`` —
    ``self.event_bus = event_bus or EnhancedEventBus()``): calling the
    constructor with no bus silently creates a SECOND bus, fracturing
    pub/sub. This assertion FAILS because ``operator.event_bus`` is a
    privately-minted ``EnhancedEventBus`` instance.

    After fix (``self.event_bus = event_bus`` — fallback removed):
    ``operator.event_bus`` is ``None``. The first attempt to publish or
    subscribe then fails loudly with ``AttributeError``, making the missed
    injection visible at the call site instead of silently dropping events.
    """
    from modules.radionics_operator import RadionicsOperator

    # Bypass the container — simulates a missed arg in a future refactor or
    # an ad-hoc instantiation. This is exactly the scenario the fallback masks.
    operator = RadionicsOperator()

    assert operator.event_bus is None, (
        f"RadionicsOperator silently minted a private bus "
        f"({type(operator.event_bus).__name__}) when event_bus was not injected. "
        f"The `or EnhancedEventBus()` fallback at radionics_operator.py:684 "
        f"must be removed — it fractures pub/sub. See ADR 003."
    )


def test_no_enhancedeventbus_instantiation_in_production_code():
    """RED (Wave 4 Task 23 acceptance criterion): ZERO ``EnhancedEventBus(``
    instantiations in production code.

    Per ADR 003 acceptance::

        grep -rn "EnhancedEventBus(" backend/ modules/

    must return ZERO hits. This test scans the full production tree
    (``backend/``, ``modules/``, ``core/``, ``infrastructure/``) for the
    constructor pattern.

    Permitted sites (NOT scanned here): ``tests/`` (fixtures) and
    ``scripts/unified_orchestrator.py:69`` (Guardrail G1 — CLI isolation,
    intentionally out of remediation scope).

    Before fix: finds ``modules/radionics_operator.py:684`` → FAILS.
    After fix: clean → PASSES.
    """
    pattern = re.compile(r"\bEnhancedEventBus\s*\(")
    production_dirs = ["backend", "modules", "core", "infrastructure"]

    offenders: list[str] = []
    for subdir in production_dirs:
        directory = REPO_ROOT / subdir
        if not directory.exists():
            continue
        for py_file in directory.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    rel = py_file.relative_to(REPO_ROOT).as_posix()
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Wave 4 Task 23 acceptance FAILED: EnhancedEventBus( instantiations "
        "found in production code:\n"
        + "\n".join(f"  - {o}" for o in offenders)
        + "\nOnly tests/ and scripts/unified_orchestrator.py:69 (G1) are permitted."
    )
