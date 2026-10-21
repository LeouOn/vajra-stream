"""The sharing layer for paid image spend.

``SpendBudget``, ``BudgetView`` and ``Reservation`` are DEFINED in
``image_generation_service`` and re-exported here, because that module has to
stay stdlib-only and independently extractable -- a guard test walks its whole
AST and rejects any project import. Putting the classes there lets the service
own its own ledger without importing this module, while this module owns the one
process-wide instance that lets two features share a single dollar cap.

See ``image_generation_service.SpendBudget`` for the class contract: a
threading.Lock, a daily USD cap plus a per-hour count, one critical section for
check + prune + reserve, reserve before the first await, reconcile to the actual
cost afterwards, release on failure.

LIMITS AND PRECEDENCE
---------------------
The LIMITS are owned by ``ImageGenerationService``: it builds the shared budget
with its own ``DEFAULT_CONFIG`` values and pushes the user's configured
``daily_cost_cap_usd`` / ``max_per_hour`` in through ``configure()``. Sigils and
generated images therefore draw on ONE cap.

The placeholders below are deliberately the SAME numbers as
``ImageGenerationService.DEFAULT_CONFIG`` (``daily_cost_cap_usd=0.50``,
``max_per_hour=10``), and that equality is asserted by a test. The reason it
matters: ``endpoints/image_generation.py`` constructs the service lazily, on the
first image request, but a sigil can be forged before that ever happens. Until
the endpoint's service is built, sigil spends against the placeholders. Matching
them to the shipped defaults means that window spends against exactly the limits
a fresh install would use, instead of against some third set of numbers.

They are IN-MEMORY and PER PROCESS: ``run.py`` starts one uvicorn process, so
there is one budget today; ``workers=N`` would give N independent budgets and
multiply every cap by N. Nothing here is persisted, so all state resets on
restart.
"""

from __future__ import annotations

import threading

from backend.core.services.image_generation_service import (
    BudgetView,
    Reservation,
    SpendBudget,
)

__all__ = [
    "BudgetView",
    "Reservation",
    "SpendBudget",
    "shared_image_budget",
]


_shared_budget: SpendBudget | None = None
_shared_lock = threading.Lock()


def shared_image_budget() -> SpendBudget:
    """The process-wide budget used by both paid image paths.

    Created lazily and exactly once, guarded by its own lock so two threads
    racing on first use cannot build two budgets -- which would silently split
    the cap in half.

    The limits here are PLACEHOLDERS equal to
    ``ImageGenerationService.DEFAULT_CONFIG``. The image service owns the real
    limits and pushes them in with ``configure()`` as soon as its config is
    loaded; sigil never sets them.
    """
    global _shared_budget
    if _shared_budget is None:
        with _shared_lock:
            if _shared_budget is None:
                _shared_budget = SpendBudget(daily_cost_cap_usd=0.50, max_per_hour=10)
    return _shared_budget
