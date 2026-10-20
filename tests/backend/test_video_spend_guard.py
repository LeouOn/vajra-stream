"""CD-2b: the paid-video spend guard must be check-and-reserve, not check-then-pay.

RED-first regression tests for a defect where ``submit_task`` checked the daily
cost cap and the hourly call limit, then AWAITED the paid POST to MiniMax, and
only recorded the spend afterwards. Nothing reserved the budget, so two
concurrent calls both passed the guard and both paid.

The learner pays per task, so the direction that matters is: never let two
concurrent submissions both pass the guard.

No network: ``httpx.AsyncClient`` is replaced by a recording fake.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.core.services import video_generation_service as vgs
from backend.core.services.video_generation_service import VideoGenerationError, VideoGenerationService

PROMPT = "a calm temple at dawn"


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {"task_id": "task-1"}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeHTTP:
    """Records every POST and answers with a scripted response."""

    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []
        self.clients_built = 0
        self.response = FakeResponse()
        self.raise_transport_error: Exception | None = None
        self.delay = 0.0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Patch httpx.AsyncClient where the service looks it up."""
        outer = self

        class _FakeAsyncClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                outer.clients_built += 1

            async def __aenter__(self) -> _FakeAsyncClient:
                return self

            async def __aexit__(self, *args: Any) -> bool:
                return False

            async def post(self, url: str, headers: Any = None, json: Any = None) -> FakeResponse:
                outer.posts.append({"url": url, "headers": headers, "body": json})
                if outer.delay:
                    await asyncio.sleep(outer.delay)
                if outer.raise_transport_error is not None:
                    raise outer.raise_transport_error
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


@pytest.mark.asyncio
async def test_two_concurrent_calls_only_one_pays(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two concurrent submissions must not both pass the guard."""
    http = FakeHTTP()
    http.install(monkeypatch)
    # The POST takes a moment, so both calls really do overlap.
    http.delay = 0.05
    service = _service(daily_cost_cap_usd=0.50, max_per_hour=1)

    results = await asyncio.gather(
        service.submit_task(PROMPT),
        service.submit_task(PROMPT),
        return_exceptions=True,
    )

    paid = [r for r in results if isinstance(r, str)]
    refused = [r for r in results if isinstance(r, RuntimeError)]
    assert len(http.posts) == 1, f"expected exactly one paid POST, got {len(http.posts)}"
    assert len(paid) == 1, f"expected one success, got {results}"
    assert len(refused) == 1, f"expected one refusal, got {results}"
    # The refusal must be the guard's own error, not something else.
    message = str(refused[0])
    assert "daily cost cap" in message or "max_per_hour" in message, message


@pytest.mark.asyncio
async def test_ten_concurrent_calls_with_room_for_three_post_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With budget for three calls, exactly three may be paid for."""
    http = FakeHTTP()
    http.install(monkeypatch)
    http.delay = 0.05
    service = _service(daily_cost_cap_usd=1.50, max_per_hour=3)

    results = await asyncio.gather(
        *(service.submit_task(PROMPT) for _ in range(10)),
        return_exceptions=True,
    )

    assert len(http.posts) == 3, f"expected exactly 3 paid POSTs, got {len(http.posts)}"
    assert sum(1 for r in results if isinstance(r, str)) == 3
    assert sum(1 for r in results if isinstance(r, RuntimeError)) == 7


@pytest.mark.asyncio
async def test_a_failed_post_releases_its_reservation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A submission that never produced a task id must not consume budget."""
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=0.50, max_per_hour=1)

    # First submission fails at the transport level.
    http.raise_transport_error = vgs.httpx.HTTPError("connection reset")
    with pytest.raises(VideoGenerationError):
        await service.submit_task(PROMPT)

    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.0, stats
    assert stats["hourly_calls"] == 0, stats

    # The budget is intact, so the next submission is allowed and pays.
    http.raise_transport_error = None
    task_id = await service.submit_task(PROMPT)
    assert task_id == "task-1"
    assert len(http.posts) == 2

    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.50, stats
    assert stats["hourly_calls"] == 1, stats


@pytest.mark.asyncio
async def test_a_response_without_a_task_id_releases_the_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 200 with no task id is a failed submission: the budget comes back."""
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=0.50, max_per_hour=1)

    http.response = FakeResponse(payload={"no_task_id_here": True})
    with pytest.raises(VideoGenerationError):
        await service.submit_task(PROMPT)

    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.0, stats
    assert stats["hourly_calls"] == 0, stats


@pytest.mark.asyncio
async def test_sequential_behaviour_and_recorded_numbers_are_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One normal call still costs one call and the same money."""
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=2.0, max_per_hour=2)

    task_id = await service.submit_task(PROMPT)
    assert task_id == "task-1"
    assert len(http.posts) == 1

    stats = service.get_cost_stats()
    assert stats["daily_spend_usd"] == 0.50, stats
    assert stats["hourly_calls"] == 1, stats
    assert stats["daily_cost_cap_usd"] == 2.0, stats
    assert stats["max_per_hour"] == 2, stats


@pytest.mark.asyncio
async def test_zero_cap_raises_before_any_client_is_built(monkeypatch: pytest.MonkeyPatch) -> None:
    """The zero-cap control must fail before an HTTP client exists."""
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=0.0, max_per_hour=1)

    with pytest.raises(RuntimeError) as excinfo:
        await service.submit_task(PROMPT)

    assert "daily cost cap" in str(excinfo.value)
    assert http.clients_built == 0, "the guard must run before the client is constructed"
    assert http.posts == []


@pytest.mark.asyncio
async def test_the_guard_refuses_a_sequential_over_cap_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sequential over-cap behaviour is unchanged: the second call is refused."""
    http = FakeHTTP()
    http.install(monkeypatch)
    service = _service(daily_cost_cap_usd=0.50, max_per_hour=5)

    await service.submit_task(PROMPT)
    with pytest.raises(RuntimeError) as excinfo:
        await service.submit_task(PROMPT)

    assert "daily cost cap" in str(excinfo.value)
    assert len(http.posts) == 1
