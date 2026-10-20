"""CD-2c: the image service must reserve spend BEFORE it pays, not after.

RED-first regression tests for the same defect class as CD-2b (video, accepted).
``ImageGenerationService.generate`` checked the daily cap and the hourly limit,
then looked in the cache, then awaited the paid provider, and only recorded
``_daily_spend`` / ``_hourly_calls`` afterwards. Two concurrent callers (a double
click, two tabs, several Outlook illustrations at once) therefore both passed
both guards and both paid.

Verified at HEAD with a real service class and a fake provider:

    RACE_COST_CAP  2 concurrent, cap=$0.035 (one call costs $0.034)
                  -> provider_calls=2, refused=0, ledger=($0.04, 2)  # OVER BUDGET
    RACE_HOURLY    2 concurrent, max_per_hour=1
                  -> provider_calls=2, ledger=($0.04, 2)
    RACE_BULK      10 concurrent, room for 3
                  -> provider_calls=10, ledger=($0.20, 10)

No network and no API key: the provider seam (``_get_provider``) is replaced with
a fake, and the fake sleeps so the calls genuinely overlap.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest

from backend.core.services.image_generation_service import (
    ImageGenerationService,
    ProviderResult,
)

# google/gemini-3.1-flash-lite-image is the configured default model and costs
# $0.034 per image, so a cap of $0.035 admits exactly one call and refuses two.
DEFAULT_MODEL = "google/gemini-3.1-flash-lite-image"
ESTIMATE = 0.034
ONE_CALL_CAP = 0.035


class FakeProvider:
    """Scripted stand-in for a paid image provider.

    ``script(n)`` is called with the 1-based provider-call index and returns
    "ok", "fail" or "retryable". Every call awaits, so concurrent callers
    genuinely overlap rather than being serialised by the fake itself.
    """

    def __init__(self) -> None:
        self.calls = 0
        self.script: Any = lambda n: "ok"
        self.cost_usd = 0.034
        self.delay = 0.02

    async def generate(self, **kwargs: Any) -> ProviderResult:
        self.calls += 1
        mode = self.script(self.calls)
        await asyncio.sleep(self.delay)
        if mode == "fail":
            raise RuntimeError(f"scripted provider failure {self.calls}")
        if mode == "retryable":
            from backend.core.services.image_generation_service import RetryableProviderError

            raise RetryableProviderError(f"scripted retryable failure {self.calls}")
        return ProviderResult(
            image_data_url="not-a-data-url",
            model=kwargs.get("model", DEFAULT_MODEL),
            cost_usd=self.cost_usd,
            provider="fake",
        )


def make_service(tmp_path: Path, **overrides: Any) -> tuple[ImageGenerationService, FakeProvider]:
    config: dict[str, Any] = {
        "enabled": True,
        "openrouter_api_key": "fake-key",
        "minimax_api_key": "fake-key",
        "image_output_dir": str(tmp_path),
        "daily_cost_cap_usd": 100.0,
        "max_per_hour": 100,
    }
    config.update(overrides)
    service = ImageGenerationService(config)
    provider = FakeProvider()
    service._get_provider = lambda name: provider  # type: ignore[method-assign]
    return service, provider


def ledger(service: ImageGenerationService) -> tuple[float, int]:
    return round(sum(service._daily_spend.values()), 6), len(service._hourly_calls)


# ---------------------------------------------------------------------------
# (a) the daily cost cap is a budget, not a suggestion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_cap_admits_one_of_two_concurrent_calls(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path, daily_cost_cap_usd=ONE_CALL_CAP)

    results = await asyncio.gather(
        *[service.generate(f"a concurrent prompt {i}") for i in range(2)],
        return_exceptions=True,
    )

    ok = [r for r in results if isinstance(r, dict)]
    refused = [r for r in results if isinstance(r, RuntimeError)]

    assert provider.calls == 1, f"only one call may reach the paid provider, got {provider.calls}"
    assert len(ok) == 1
    assert len(refused) == 1
    assert "daily cost cap" in str(refused[0])
    assert ledger(service)[0] <= ONE_CALL_CAP


@pytest.mark.asyncio
async def test_daily_cap_refusal_uses_the_existing_message(tmp_path: Path) -> None:
    """Requirement 4: same exception type and message from the guard."""
    service, provider = make_service(tmp_path, daily_cost_cap_usd=ONE_CALL_CAP)
    await service.generate("first")
    with pytest.raises(RuntimeError) as excinfo:
        await service.generate("second")
    assert str(excinfo.value).startswith("Request would breach daily cost cap (")
    assert provider.calls == 1


# ---------------------------------------------------------------------------
# (b) the hourly limit is a limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hourly_limit_one_admits_one_of_two_concurrent_calls(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path, max_per_hour=1)

    results = await asyncio.gather(
        *[service.generate(f"b concurrent prompt {i}") for i in range(2)],
        return_exceptions=True,
    )

    refused = [r for r in results if isinstance(r, RuntimeError)]
    assert provider.calls == 1, f"got {provider.calls}"
    assert len(refused) == 1
    assert "max_per_hour=1 reached" in str(refused[0])


# ---------------------------------------------------------------------------
# (c) the bulk case
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ten_concurrent_calls_with_room_for_three_admit_exactly_three(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path, max_per_hour=3, daily_cost_cap_usd=100.0)

    results = await asyncio.gather(
        *[service.generate(f"c concurrent prompt {i}") for i in range(10)],
        return_exceptions=True,
    )

    ok = [r for r in results if isinstance(r, dict)]
    refused = [r for r in results if isinstance(r, RuntimeError)]

    assert provider.calls == 3, f"exactly three may be paid for, got {provider.calls}"
    assert len(ok) == 3
    assert len(refused) == 7
    assert ledger(service)[1] == 3


# ---------------------------------------------------------------------------
# (d) a failed call must not consume the budget
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_attempts_release_the_reservation_exactly(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path)
    provider.script = lambda n: "fail"

    with pytest.raises(RuntimeError):
        await service.generate("d failing prompt")

    assert ledger(service) == (0.0, 0), "a failed call must cost no budget"

    # The budget is genuinely available again: a later call is admitted.
    provider.script = lambda n: "ok"
    result = await service.generate("d later prompt")
    assert result["cached"] is False
    # A plain RuntimeError is NOT retryable, so the first attempt raises
    # immediately: 1 provider call for the failure + 1 for the success.
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_retryable_failure_that_exhausts_attempts_releases_the_reservation(
    tmp_path: Path,
) -> None:
    service, provider = make_service(tmp_path)
    provider.script = lambda n: "retryable"

    with pytest.raises(RuntimeError):
        await service.generate("d retryable prompt")

    assert ledger(service) == (0.0, 0)


@pytest.mark.asyncio
async def test_permanent_provider_error_releases_the_reservation(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path)

    async def always_permanent(**kwargs: Any) -> ProviderResult:
        provider.calls += 1
        from backend.core.services.image_generation_service import PermanentProviderError

        raise PermanentProviderError("scripted permanent failure")

    provider.generate = always_permanent  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await service.generate("d permanent prompt")

    assert ledger(service) == (0.0, 0)


# ---------------------------------------------------------------------------
# (e) both retry attempts are ONE reservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_success_on_attempt_two_is_a_single_reservation(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path)
    provider.script = lambda n: "retryable" if n == 1 else "ok"

    await service.generate("e retry prompt")

    assert provider.calls == 2, "one retry means two provider calls"
    spend, hourly = ledger(service)
    assert hourly == 1, f"both attempts share one reservation, got {hourly}"
    assert spend == pytest.approx(provider.cost_usd), "ledger must hold the ACTUAL cost once"


# ---------------------------------------------------------------------------
# (f) reconcile estimate -> actual
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ledger_reconciles_to_the_actual_cost_not_the_estimate(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path)
    provider.cost_usd = 0.11  # provider bills far more than the $0.034 estimate

    await service.generate("f over-estimate prompt")

    spend, hourly = ledger(service)
    assert spend == pytest.approx(0.11), "ledger must end at the ACTUAL cost"
    assert hourly == 1
    assert spend != pytest.approx(ESTIMATE)


@pytest.mark.asyncio
async def test_ledger_reconciles_when_the_provider_bills_less_than_the_estimate(
    tmp_path: Path,
) -> None:
    service, provider = make_service(tmp_path)
    provider.cost_usd = 0.001  # cheaper than the estimate

    await service.generate("f under-estimate prompt")

    spend, _ = ledger(service)
    assert spend == pytest.approx(0.001), "must subtract, not add on top of the estimate"


@pytest.mark.asyncio
async def test_three_sequential_calls_accumulate_the_actual_costs(tmp_path: Path) -> None:
    service, provider = make_service(tmp_path)
    provider.cost_usd = 0.05

    for i in range(3):
        await service.generate(f"f accumulate {i}")

    spend, hourly = ledger(service)
    assert spend == pytest.approx(0.15)
    assert hourly == 3


# ---------------------------------------------------------------------------
# (g) a cache hit costs nothing and must not reserve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_makes_no_provider_call_and_leaves_the_ledger_alone(
    tmp_path: Path,
) -> None:
    service, provider = make_service(tmp_path)

    first = await service.generate("g identical prompt")
    after_first = ledger(service)
    calls_after_first = provider.calls

    second = await service.generate("g identical prompt")

    assert second["cached"] is True
    assert first["cached"] is False
    assert provider.calls == calls_after_first, "a cache hit must not call the provider"
    assert ledger(service) == after_first, "a cache hit must not reserve or record"


# ---------------------------------------------------------------------------
# (h) requirement 4: public behaviour and numbers unchanged sequentially
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequential_stats_are_unchanged(tmp_path: Path) -> None:
    """One normal call: same numbers in get_cost_stats as before the fix."""
    service, provider = make_service(tmp_path, daily_cost_cap_usd=5.0, max_per_hour=10)

    result = await service.generate("h plain prompt")

    assert result["cached"] is False
    assert provider.calls == 1

    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == pytest.approx(provider.cost_usd)
    assert stats["hourly_calls"] == 1
    assert stats["daily_cost_cap_usd"] == 5.0
    assert stats["max_per_hour"] == 10
    assert stats["cache_entries"] == 1


@pytest.mark.asyncio
async def test_image_output_dir_is_respected(tmp_path: Path) -> None:
    """Sanity: the service still writes under the configured directory."""
    service, provider = make_service(tmp_path)
    import base64

    png = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
    provider.cost_usd = 0.02

    async def data_url(**kwargs: Any) -> ProviderResult:
        provider.calls += 1
        return ProviderResult(
            image_data_url=f"data:image/png;base64,{png}",
            model=kwargs.get("model", DEFAULT_MODEL),
            cost_usd=provider.cost_usd,
            provider="fake",
        )

    provider.generate = data_url  # type: ignore[method-assign]

    await service.generate("h write a png")
    assert list(Path(tmp_path).glob("*.png")), "image must land in image_output_dir"
    assert not list(Path.cwd().glob("img_*.png")), "nothing may be written into the repo"


def test_the_service_owns_a_threading_lock_not_an_asyncio_lock(tmp_path: Path) -> None:
    """Requirement: guard the choice.

    An ``asyncio.Lock`` would bind to whichever loop first awaited it, and this
    singleton is reachable from worker-thread event loops in this codebase, so
    the guard must be loop-agnostic.
    """
    import threading

    service, _provider = make_service(tmp_path)
    lock = getattr(service, "_spend_lock", None)
    assert lock is not None, "the service must own a spend lock"
    assert isinstance(lock, type(threading.Lock()))


# ---------------------------------------------------------------------------
# CD-2c REWORK 1: guard + prune + cache lookup + reserve must be ONE section
# ---------------------------------------------------------------------------
#
# The first version locked ONLY the reservation. The daily-cap guard, the hourly
# prune and the cache lookup ran outside it, so the lock did not deliver what
# its own comment claimed. Two OS threads could both pass the guard and then
# both reserve. Reproduced deterministically, no sleeps:
#
#   T two threads forced between guard and reserve, room for ONE
#     -> provider_calls=2 refused=0 ledger=(0.068, 2)
#
# The hourly prune made it worse in a second way: it REBINDS
# ``self._hourly_calls`` to a filtered list, so a thread appending its stamp to
# the old list loses that stamp when the rebind lands.

_BARRIER_TIMEOUT = 0.5


def _barrier_cache_key_hook(service: ImageGenerationService, barrier: threading.Barrier):
    """Wrap ``_cache_key`` so a caller parks between the guard and the reserve.

    ``_cache_key`` is called after the guard and before the reservation, so it
    is the seam that lets two real threads be inside the vulnerable window.

    The timeout is short and ``BrokenBarrierError`` is swallowed, because once
    the fix lands the second thread BLOCKS ON THE LOCK and never reaches this
    hook -- so the barrier never completes and the test must not hang waiting
    for it.
    """
    real_key = service._cache_key

    def hooked(*args: Any, **kwargs: Any):
        try:
            barrier.wait(timeout=_BARRIER_TIMEOUT)
        except threading.BrokenBarrierError:
            pass
        return real_key(*args, **kwargs)

    return hooked


def test_two_threads_forced_between_guard_and_reserve_admit_exactly_one(tmp_path: Path) -> None:
    """Two real threads, cap for one call: one pays, one is refused."""
    service, provider = make_service(tmp_path, daily_cost_cap_usd=ONE_CALL_CAP)
    service._cache_key = _barrier_cache_key_hook(service, threading.Barrier(2, timeout=_BARRIER_TIMEOUT))

    results: list[Any] = []
    results_lock = threading.Lock()

    def run(index: int) -> None:
        try:
            outcome: Any = asyncio.run(service.generate(f"threaded prompt {index}"))
        except BaseException as exc:  # noqa: BLE001 - recorded for assertions
            outcome = exc
        with results_lock:
            results.append(outcome)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(results) == 2, results
    refused = [r for r in results if isinstance(r, RuntimeError)]
    assert provider.calls == 1, f"exactly one call may be paid for, got {provider.calls}"
    assert len(refused) == 1, f"the other must be refused, got {results}"
    assert ledger(service) == (pytest.approx(0.034), 1), ledger(service)


def test_eight_threads_with_room_for_three_admit_exactly_three(tmp_path: Path) -> None:
    """Thread stress: 8 concurrent asyncio.run calls, repeated.

    The reservation must be exact under real thread contention, and the hourly
    prune must not lose a stamp by rebinding the list mid-flight.
    """
    provider_calls_per_trial: list[int] = []

    for trial in range(20):
        service, provider = make_service(tmp_path, daily_cost_cap_usd=10.0, max_per_hour=3)
        provider.delay = 0.004
        before = provider.calls

        def run(index: int) -> None:
            try:
                asyncio.run(service.generate(f"stress {trial} prompt {index}"))
            except BaseException:  # noqa: BLE001 - refusals are expected
                pass

        threads = [threading.Thread(target=run, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        provider_calls_per_trial.append(provider.calls - before)

    assert all(
        count == 3 for count in provider_calls_per_trial
    ), f"every trial must admit exactly 3, got {provider_calls_per_trial}"


def test_hourly_prune_does_not_lose_a_concurrent_reservation(tmp_path: Path) -> None:
    """The prune REBINDS ``_hourly_calls``; a concurrent stamp must survive.

    This is the second half of the same defect: the prune filtered the list into
    a NEW list, so a reservation appended to the old list between the filter and
    the rebind would be silently discarded -- an admitted call that then consumed
    no hourly slot.

    Counted rather than raced: after N admitted calls the list must hold exactly
    N stamps. Under the fix the prune and the reservation are in one critical
    section, so the count is exact.
    """
    for trial in range(20):
        service, provider = make_service(tmp_path, daily_cost_cap_usd=10.0, max_per_hour=3)
        provider.delay = 0.004

        def run(index: int) -> None:
            try:
                asyncio.run(service.generate(f"prune {trial} prompt {index}"))
            except BaseException:  # noqa: BLE001 - refusals are expected
                pass

        threads = [threading.Thread(target=run, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        admitted = provider.calls
        assert admitted == 3, f"trial {trial}: {admitted} admitted"
        assert len(service._hourly_calls) == admitted, (
            f"trial {trial}: {len(service._hourly_calls)} hourly stamps for "
            f"{admitted} admitted calls -- the prune dropped a reservation"
        )
