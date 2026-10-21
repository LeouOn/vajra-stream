"""SB-1: one shared spend budget for every paid image call.

RED-first tests for :mod:`backend.core.services.spend_budget`. The concurrency
test was written against a deliberately LOCKLESS stub of ``SpendBudget`` and
failed with two reservations admitted for room for one; it passes only once the
budget makes check + prune + reserve one critical section.

No network and no API key: nothing here talks to a provider.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from backend.core.services.spend_budget import (
    Reservation,
    SpendBudget,
    shared_image_budget,
)

BARRIER_TIMEOUT = 0.5
# One call at $0.034; a cap of $0.035 admits exactly one and refuses two.
ESTIMATE = 0.034
CAP_FOR_ONE = 0.035


class BarrierOnGet(dict):
    """A daily-spend dict whose ``get`` parks between the read and the write.

    ``get`` reads first, then waits, then returns the PRE-barrier value. That is
    what forces the race: without the lock both threads read "nothing spent",
    are released together, and both reserve. With the lock the first thread holds
    it while parked, so the second never gets in; the first times out, breaks the
    barrier and reserves, and the second then reads the reserved value and is
    refused.

    The timeout keeps the fixed version fast: once the lock works the barrier
    never completes, so the test must not wait on it.
    """

    def __init__(self, barrier: threading.Barrier) -> None:
        super().__init__()
        self._barrier = barrier

    def get(self, key: Any, default: Any = None) -> Any:
        value = super().get(key, default)
        try:
            self._barrier.wait(timeout=BARRIER_TIMEOUT)
        except threading.BrokenBarrierError:
            pass
        return value


@pytest.fixture
def budget() -> SpendBudget:
    """A FRESH budget per test -- never shared state across tests."""
    return SpendBudget(daily_cost_cap_usd=CAP_FOR_ONE, max_per_hour=10)


# ---------------------------------------------------------------------------
# the race: this fails against the lockless stub
# ---------------------------------------------------------------------------


def test_two_threads_forced_between_check_and_reserve_admit_exactly_one(budget: SpendBudget) -> None:
    """Deterministic, no sleeps: room for one call must mean one call."""
    budget._daily_spend = BarrierOnGet(threading.Barrier(2, timeout=BARRIER_TIMEOUT))

    results: list[str] = []
    guard = threading.Lock()

    def worker() -> None:
        try:
            budget.reserve(ESTIMATE)
            outcome = "reserved"
        except RuntimeError:
            outcome = "refused"
        with guard:
            results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=BARRIER_TIMEOUT * 6)

    assert results.count("reserved") == 1, f"exactly one reservation, got {results}"
    assert results.count("refused") == 1, f"the other must be refused, got {results}"
    assert budget.stats()["daily_spend_usd"] == pytest.approx(ESTIMATE)


def test_budget_owns_a_real_threading_lock(budget: SpendBudget) -> None:
    """Guard the guard: it must be a threading.Lock, not an asyncio one.

    The budget is used from worker threads (sigil runs its blocking requests in
    ``asyncio.to_thread``), so an asyncio lock would not be shared.
    """
    assert isinstance(budget._lock, type(threading.Lock()))


# ---------------------------------------------------------------------------
# reserve / reconcile / release
# ---------------------------------------------------------------------------


def test_reserve_charges_the_estimate(budget: SpendBudget) -> None:
    reservation = budget.reserve(ESTIMATE)
    assert isinstance(reservation, Reservation)
    assert budget.stats()["daily_spend_usd"] == pytest.approx(ESTIMATE)
    assert budget.stats()["hourly_calls"] == 1


def test_refusal_message_is_byte_identical_to_the_image_service(budget: SpendBudget) -> None:
    budget.reserve(ESTIMATE)
    with pytest.raises(RuntimeError) as excinfo:
        budget.reserve(ESTIMATE)
    assert str(excinfo.value) == f"Request would breach daily cost cap (${2 * ESTIMATE:.4f} > ${CAP_FOR_ONE:.4f})"


def test_hourly_limit_message_is_byte_identical(budget: SpendBudget) -> None:
    hourly = SpendBudget(daily_cost_cap_usd=100.0, max_per_hour=1)
    hourly.reserve(ESTIMATE)
    with pytest.raises(RuntimeError) as excinfo:
        hourly.reserve(ESTIMATE)
    assert str(excinfo.value) == "max_per_hour=1 reached; try again later"


def test_try_reserve_returns_none_instead_of_raising(budget: SpendBudget) -> None:
    """Sigil must be able to ask without an exception crossing the boundary."""
    assert budget.try_reserve(ESTIMATE) is not None
    assert budget.try_reserve(ESTIMATE) is None


def test_reconcile_settles_at_the_actual_cost(budget: SpendBudget) -> None:
    reservation = budget.reserve(ESTIMATE)
    budget.reconcile(reservation, 0.11)
    assert budget.stats()["daily_spend_usd"] == pytest.approx(0.11)
    assert budget.stats()["hourly_calls"] == 1, "the call happened; it keeps its slot"


def test_reconcile_when_the_provider_bills_less(budget: SpendBudget) -> None:
    reservation = budget.reserve(ESTIMATE)
    budget.reconcile(reservation, 0.001)
    assert budget.stats()["daily_spend_usd"] == pytest.approx(0.001)


def test_release_returns_the_whole_reservation(budget: SpendBudget) -> None:
    reservation = budget.reserve(ESTIMATE)
    budget.release(reservation)
    stats = budget.stats()
    assert stats["daily_spend_usd"] == pytest.approx(0.0)
    assert stats["hourly_calls"] == 0


def test_release_removes_only_its_own_stamp(budget: SpendBudget) -> None:
    first = budget.reserve(0.01)
    second = budget.reserve(0.01)
    budget.release(first)
    remaining = budget.stats()
    assert remaining["hourly_calls"] == 1
    assert remaining["daily_spend_usd"] == pytest.approx(0.01)
    assert second.stamp in budget._hourly_calls


def test_hourly_window_expires_old_stamps() -> None:
    stale = SpendBudget(daily_cost_cap_usd=100.0, max_per_hour=1)
    stale._hourly_calls = [0.0]  # epoch: ancient, must be pruned
    stale.reserve(ESTIMATE)
    assert stale.stats()["hourly_calls"] == 1


def test_daily_ledger_is_keyed_by_utc_day() -> None:
    b = SpendBudget(daily_cost_cap_usd=100.0, max_per_hour=10)
    b.reserve(0.01)
    today = b._today()
    assert b.stats()["daily_spend_usd"] == pytest.approx(0.01)
    assert list(b._daily_spend) == [today]


def test_configure_pushes_new_limits() -> None:
    b = SpendBudget(daily_cost_cap_usd=1.0, max_per_hour=1)
    b.reserve(0.5)
    b.configure(daily_cost_cap_usd=10.0, max_per_hour=10)
    stats = b.stats()
    assert stats["daily_cost_cap_usd"] == 10.0
    assert stats["max_per_hour"] == 10
    assert b.reserve(0.5) is not None, "the new room must be usable immediately"


# ---------------------------------------------------------------------------
# the shared instance
# ---------------------------------------------------------------------------


def test_shared_instance_is_genuinely_shared() -> None:
    assert shared_image_budget() is shared_image_budget()


def test_shared_instance_is_not_a_per_test_singleton() -> None:
    """Guard against a fixture accidentally rebinding the process-wide object."""
    first = shared_image_budget()
    assert isinstance(first, SpendBudget)
    assert shared_image_budget() is first


def test_shared_budget_two_threads_admit_exactly_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """The SHARED budget must be atomic too, not just a freshly built one.

    Without this, removing the lock left every other spend test green: the only
    detector in the suite was the private-budget test above. This one drives the
    process-wide instance through the same forced interleaving.
    """
    shared = SpendBudget(daily_cost_cap_usd=CAP_FOR_ONE, max_per_hour=10)
    monkeypatch.setattr("backend.core.services.spend_budget._shared_budget", shared)
    shared._daily_spend = BarrierOnGet(threading.Barrier(2, timeout=BARRIER_TIMEOUT))

    results: list[str] = []
    guard = threading.Lock()

    def worker() -> None:
        # try_reserve reports refusal as None rather than raising.
        outcome = "reserved" if shared.try_reserve(ESTIMATE) is not None else "refused"
        with guard:
            results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=BARRIER_TIMEOUT * 6)

    # try_reserve reports refusal as None rather than raising, so count both.
    assert results.count("reserved") == 1, f"exactly one reservation, got {results}"
    assert results.count("refused") == 1, f"the other must be refused, got {results}"
    assert shared.stats()["daily_spend_usd"] == pytest.approx(ESTIMATE)


# ---------------------------------------------------------------------------
# REWORK 2 (2): reconcile must not take NaN / inf / negative
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_reconcile_ignores_non_finite_costs_and_keeps_the_estimate(budget: SpendBudget, bad) -> None:
    """A NaN total would poison the ledger: ``nan > cap`` is False, so the cap
    would never trip again."""
    reservation = budget.reserve(ESTIMATE)
    budget.reconcile(reservation, bad)

    assert budget.stats()["daily_spend_usd"] == pytest.approx(ESTIMATE)
    # The cap must still bite.
    assert budget.try_reserve(ESTIMATE) is None, "the cap must still be enforced"


def test_reconcile_ignores_a_negative_cost(budget: SpendBudget) -> None:
    """A negative total would hand free budget back."""
    reservation = budget.reserve(ESTIMATE)
    budget.reconcile(reservation, -1.0)

    assert budget.stats()["daily_spend_usd"] == pytest.approx(ESTIMATE)
    assert budget.try_reserve(ESTIMATE) is None


def test_reconcile_floors_the_day_total_at_zero() -> None:
    """A rounding artefact must not leave the ledger negative.

    Constructed so the arithmetic genuinely goes negative: the day total is
    zeroed underneath the reservation, so ``total - estimate + actual`` is
    below zero and only the floor saves it.
    """
    budget = SpendBudget(daily_cost_cap_usd=1.0, max_per_hour=10)
    reservation = budget.reserve(0.05)
    budget._daily_spend[budget._today()] = 0.0
    budget.reconcile(reservation, 0.0)
    assert budget.stats()["daily_spend_usd"] == pytest.approx(0.0)
    assert budget.stats()["daily_spend_usd"] >= 0.0


def test_reconcile_honours_a_zero_actual_cost(budget: SpendBudget) -> None:
    """0.0 is a legitimate FREE call and must settle to zero.

    Sigil is unaffected: its own reader treats a reported zero as "not
    reported" and never passes 0.0 here.
    """
    reservation = budget.reserve(ESTIMATE)
    budget.reconcile(reservation, 0.0)

    assert budget.stats()["daily_spend_usd"] == pytest.approx(0.0)
    assert budget.stats()["hourly_calls"] == 1, "the call happened; it keeps its slot"


def test_reconcile_of_a_non_finite_cost_logs_one_warning(budget: SpendBudget, caplog) -> None:
    import logging

    reservation = budget.reserve(ESTIMATE)
    with caplog.at_level(logging.WARNING):
        budget.reconcile(reservation, float("nan"))
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1, f"expected exactly one warning, got {len(warnings)}"


def test_infinity_does_not_lock_the_cap() -> None:
    """An infinite actual cost must not make the cap unreachable.

    The budget has room for TWO calls, so if infinity were accepted the day
    total would become infinite and every later reserve would be refused --
    the cap would be locked permanently. Treating infinity as "not reported"
    keeps the estimate, so the second call still fits.
    """
    budget = SpendBudget(daily_cost_cap_usd=0.10, max_per_hour=10)
    reservation = budget.reserve(ESTIMATE)
    budget.reconcile(reservation, float("inf"))

    assert budget.stats()["daily_spend_usd"] == pytest.approx(ESTIMATE)
    assert budget.try_reserve(ESTIMATE) is not None, "the cap must not be locked by an infinity"
