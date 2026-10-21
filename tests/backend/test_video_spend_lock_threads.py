"""VL-1: the video spend guard must be safe across THREADS.

The guard's check-and-reserve was protected by an ``asyncio.Lock``. That is
per-loop and not thread-safe, so two worker threads - each running its own
event loop - could both pass the guard and both pay.

The image generation service already does this correctly with a
``threading.Lock``; these tests are the same idea for the video service, and
the two-thread case is DETERMINISTIC: a barrier parks a caller in the window
between the guard and the reservation, so the vulnerable interleaving is forced
rather than hoped for.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from backend.core.services import video_generation_service as vgs
from backend.core.services.video_generation_service import VideoGenerationError, VideoGenerationService

PROMPT = "a calm temple at dawn"

# Short, so the test never hangs: once the fix lands the second thread blocks
# on the lock and never reaches the barrier, so the barrier times out.
_BARRIER_TIMEOUT = 0.5

ONE_CALL_CAP = 0.50
THREE_CALL_CAP = 1.50


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"task_id": "task-1"}
        self.text = ""

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeHTTP:
    """Records every POST. No network, no delay: the point is the count."""

    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []
        self.response = FakeResponse()

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        outer = self

        class _FakeAsyncClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def __aenter__(self) -> _FakeAsyncClient:
                return self

            async def __aexit__(self, *args: Any) -> bool:
                return False

            async def post(self, url: str, headers: Any = None, json: Any = None) -> FakeResponse:
                outer.posts.append({"url": url, "body": json})
                return outer.response

        monkeypatch.setattr(vgs.httpx, "AsyncClient", _FakeAsyncClient)


def _service(**config: Any) -> VideoGenerationService:
    base: dict[str, Any] = {
        "minimax_api_key": "test-key",
        "default_model": "T2V-01",  # $0.50 per call
        "daily_cost_cap_usd": 2.0,
        "max_per_hour": 2,
    }
    base.update(config)
    return VideoGenerationService(base)


def _barrier_guard_hook(service: VideoGenerationService, barrier: threading.Barrier):
    """Park a caller between the guard and the reservation.

    ``_check_cost_guard`` runs immediately before the reservation is recorded,
    so wrapping it parks the caller in exactly the vulnerable window: the
    budget has been checked but not yet spent.

    The barrier's timeout is short and ``BrokenBarrierError`` is swallowed,
    because once the fix lands the second thread BLOCKS ON THE LOCK and never
    reaches this hook - the barrier never completes, and the test must not hang
    waiting for it.
    """
    real_check = service._check_cost_guard

    def hooked(model: str) -> None:
        real_check(model)
        try:
            barrier.wait(timeout=_BARRIER_TIMEOUT)
        except threading.BrokenBarrierError:
            pass

    return hooked


def _run_in_threads(service: VideoGenerationService, count: int) -> tuple[list[Any], int]:
    """Run ``count`` real threads, each on its own event loop.

    Returns the outcomes and the number of threads that never finished.
    """
    results: list[Any] = []
    results_lock = threading.Lock()

    def run(index: int) -> None:
        try:
            outcome: Any = asyncio.run(service.submit_task(f"threaded prompt {index}"))
        except BaseException as exc:  # noqa: BLE001 - recorded for the assertions
            outcome = exc
        with results_lock:
            results.append(outcome)

    threads = [threading.Thread(target=run, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    unfinished = sum(1 for thread in threads if thread.is_alive())
    return results, unfinished


def test_two_threads_forced_between_guard_and_reserve_admit_exactly_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two real threads, budget for one call: one pays, one is refused.

    Deterministic: the barrier forces both threads into the window between the
    guard and the reserve, which is exactly where the unguarded implementation
    lets both through.
    """
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=ONE_CALL_CAP, max_per_hour=1)
    service._check_cost_guard = _barrier_guard_hook(  # type: ignore[method-assign]
        service, threading.Barrier(2, timeout=_BARRIER_TIMEOUT)
    )

    results, unfinished = _run_in_threads(service, 2)

    assert unfinished == 0, (
        f"{unfinished} worker thread(s) never finished: an asyncio.Lock is bound to the "
        f"loop that first awaited it, so a thread on another loop waits on a lock that "
        f"will never be released for it (results so far: {results})"
    )
    assert len(results) == 2, results
    paid = [r for r in results if isinstance(r, str)]
    refused = [r for r in results if isinstance(r, RuntimeError)]
    assert len(http.posts) == 1, f"expected exactly one paid POST, got {len(http.posts)}"
    assert len(paid) == 1, results
    assert len(refused) == 1, results
    assert "daily cost cap" in str(refused[0]) or "max_per_hour" in str(refused[0])


def test_eight_threads_with_room_for_three_admit_exactly_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Eight real threads, budget for three calls: three pay, five are refused.

    HONESTY NOTE: unlike the two-thread test above, this one is NOT
    deterministic. With the old per-loop lock the eight threads happened to
    serialise on the fake HTTP client often enough to pass, so it may pass
    without the fix; it is here as a stress check, not as the proof.
    """
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=THREE_CALL_CAP, max_per_hour=3)

    results, unfinished = _run_in_threads(service, 8)

    assert unfinished == 0, f"{unfinished} worker thread(s) never finished (results: {results})"
    paid = [r for r in results if isinstance(r, str)]
    refused = [r for r in results if isinstance(r, RuntimeError)]
    assert len(results) == 8, results
    assert len(http.posts) == 3, f"expected exactly 3 paid POSTs, got {len(http.posts)}"
    assert len(paid) == 3, results
    assert len(refused) == 5, results


def test_the_service_owns_a_threading_lock_not_an_asyncio_lock() -> None:
    """The lock must be a threading.Lock: an asyncio.Lock is per-loop."""
    service = _service()
    assert isinstance(service._spend_lock, threading.Lock)
    assert not isinstance(service._spend_lock, asyncio.Lock)


def test_a_failed_post_in_a_thread_releases_its_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rollback path still works, and still releases the reservation."""
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=ONE_CALL_CAP, max_per_hour=1)

    original_post = http.response

    # Make the POST fail with an HTTP error.
    http.response = FakeResponse(status_code=500, payload={})
    with pytest.raises(VideoGenerationError):
        asyncio.run(service.submit_task(PROMPT))

    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.0, stats
    assert stats["hourly_calls"] == 0, stats

    # And the budget is intact for the next call.
    http.response = original_post
    assert asyncio.run(service.submit_task(PROMPT)) == "task-1"
    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.50, stats
    assert stats["hourly_calls"] == 1, stats
