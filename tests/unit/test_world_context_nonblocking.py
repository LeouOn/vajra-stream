"""W5-S3: ``GET /api/v1/operator/world-context`` must not park the API's event loop.

The route used to be ``async def`` and call the synchronous ``compile_world_context()`` (two RSS downloads with
15 s timeouts, ``core/internet_context.py``) directly on the loop, so while one request was downloading, EVERY other
request - ``/health``, ``/api/v1/astrology/night-sky`` - waited behind it. Measured on the running API in W5-S1b/S2:
1-4 s stalls, 23 s when a page mount fired a dozen calls at once; the Earth & Sky dome showed "Night sky unavailable".

The route is now a plain ``def``, which FastAPI runs in its threadpool. The tests patch ``compile_world_context`` (no
network, ``urllib.request.urlopen`` is replaced by something that fails the test if it is touched) with a function that
sleeps 0.5 s and run the real app (no lifespan: ``httpx.ASGITransport`` does not start the warm-up tasks).
"""

from __future__ import annotations

import asyncio
import inspect
import time
import traceback
from unittest.mock import patch

import httpx
import pytest

from core.internet_context import InternetContext, WorldEvent

BUSY_SECONDS = 0.5
HEALTH_DELAY_SECONDS = 0.05
HEALTH_LIMIT_SECONDS = 0.2  # generous: a free loop answers /health in a few milliseconds
LOOP_GAP_LIMIT_SECONDS = 0.2


def _fake_context(n_events: int = 3, n_disasters: int = 2) -> InternetContext:
    return InternetContext(
        events=[
            WorldEvent(
                title=f"Event {i}",
                description="d",
                location=f"Place {i}",
                country="Chile",
                lat=-33.4 + i,
                lon=-70.6 - i,
                event_type="disaster" if i % 2 == 0 else "humanitarian",
                severity="critical" if i == 0 else "medium",
                source="GDACS",
                url="https://example.invalid/e",
                date="2026-10-24",
            )
            for i in range(n_events)
        ],
        disasters=[{"title": f"Disaster {i}", "country": "Chile"} for i in range(n_disasters)],
        planetary_hour="Mars",
        day_ruler="Saturn",
        fetched_at="2026-10-24T22:00:00",
        summary="3 significant world events detected.",
    )


@pytest.fixture()
async def app():
    """The real app, warmed: the first request through a fresh app pays ~0.2 s of one-off setup (lazy imports, the
    thread pool, the middleware stack), which has nothing to do with the question and would blur the 200 ms limit."""
    from backend.app.main import app as real_app

    transport = httpx.ASGITransport(app=real_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("core.internet_context.compile_world_context", return_value=_fake_context()):
            assert (await client.get("/health")).status_code == 200
            assert (await client.get("/api/v1/operator/world-context")).status_code == 200
    return real_app


@pytest.fixture(autouse=True)
def no_network():
    """No test here reaches the network, and nothing in the world-context path even tries.

    ``urllib.request.urlopen`` is replaced by a function that refuses (``OSError``) and remembers who called it.
    Importing the app starts an unrelated entropy worker thread that tries one fetch of its own
    (``backend/core/services/true_rng_provider.py``); it is refused too, but it is not what is under test, so the
    assertion is that no call came from ``core/internet_context.py`` or the operator route.
    """
    callers: list[list[str]] = []

    def refuse(*_args, **_kwargs):
        callers.append([frame.filename for frame in traceback.extract_stack()])
        raise OSError("network disabled in tests")

    with patch("urllib.request.urlopen", side_effect=refuse):
        yield
    offenders = [
        c for c in callers if any(f.endswith(("core/internet_context.py", "endpoints/operator.py")) for f in c)
    ]
    assert not offenders, "the world-context path called urllib.request.urlopen"


def _slow_compile(*_args, **_kwargs) -> InternetContext:
    time.sleep(BUSY_SECONDS)  # stands for the two blocking RSS downloads
    return _fake_context()


async def test_health_stays_responsive_while_world_context_is_busy(app, capsys):
    """Fire world-context, then /health 50 ms later: /health must answer within 200 ms, not after the 0.5 s call."""
    gaps: list[float] = []
    stop = asyncio.Event()

    async def loop_lag_gauge() -> None:
        previous = time.perf_counter()
        while not stop.is_set():
            await asyncio.sleep(0.01)
            now = time.perf_counter()
            gaps.append(now - previous)
            previous = now

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("core.internet_context.compile_world_context", side_effect=_slow_compile):
            gauge = asyncio.create_task(loop_lag_gauge())
            t0 = time.perf_counter()

            async def world_context():
                response = await client.get("/api/v1/operator/world-context")
                return response, time.perf_counter() - t0

            async def health():
                # Latency is measured from the moment the request was MEANT to be sent, so a loop that was blocked
                # and only resumed this coroutine late is charged for the wait instead of hiding it.
                intended = t0 + HEALTH_DELAY_SECONDS
                await asyncio.sleep(HEALTH_DELAY_SECONDS)
                response = await client.get("/health")
                return response, time.perf_counter() - intended

            (wc_response, wc_elapsed), (health_response, health_elapsed) = await asyncio.gather(
                world_context(), health()
            )
            stop.set()
            await gauge

    worst_gap = max(gaps)
    with capsys.disabled():
        print(
            f"\n[W5-S3] world-context {wc_elapsed * 1000:.0f} ms | /health {health_elapsed * 1000:.0f} ms "
            f"(fired {HEALTH_DELAY_SECONDS * 1000:.0f} ms after) | worst event-loop gap {worst_gap * 1000:.0f} ms"
        )
    assert wc_response.status_code == 200
    assert wc_elapsed >= BUSY_SECONDS, "the patched call really did take 0.5 s"
    assert health_response.status_code == 200
    assert (
        health_elapsed < HEALTH_LIMIT_SECONDS
    ), f"/health took {health_elapsed:.3f} s: the event loop was blocked by world-context"
    assert worst_gap < LOOP_GAP_LIMIT_SECONDS, f"the event loop stalled for {worst_gap:.3f} s"


async def test_a_burst_of_world_context_calls_does_not_stall_health(app):
    """A page mount fires several calls at once (the 18:58 burst): /health still answers while all of them run."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("core.internet_context.compile_world_context", side_effect=_slow_compile):
            t0 = time.perf_counter()

            async def health():
                intended = t0 + HEALTH_DELAY_SECONDS
                await asyncio.sleep(HEALTH_DELAY_SECONDS)
                response = await client.get("/health")
                return response.status_code, time.perf_counter() - intended

            results = await asyncio.gather(
                *(client.get("/api/v1/operator/world-context") for _ in range(4)),
                health(),
            )
    assert [r.status_code for r in results[:4]] == [200, 200, 200, 200]
    status, elapsed = results[4]
    assert status == 200
    assert elapsed < HEALTH_LIMIT_SECONDS, f"/health took {elapsed:.3f} s behind four concurrent world-context calls"


def test_the_route_is_a_plain_def_so_fastapi_runs_it_off_the_loop():
    from backend.app.api.v1.endpoints.operator import get_world_context

    assert not inspect.iscoroutinefunction(get_world_context)


def test_the_response_for_a_faked_context_is_unchanged(app):
    from fastapi.testclient import TestClient

    with patch("core.internet_context.compile_world_context", return_value=_fake_context(n_events=20, n_disasters=12)):
        response = TestClient(app).get("/api/v1/operator/world-context")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "events_count",
        "disasters",
        "events",
        "planetary_hour",
        "day_ruler",
        "summary",
        "fetched_at",
    }
    assert body["events_count"] == 20  # the count of ALL events ...
    assert len(body["events"]) == 15  # ... while the list is capped at 15
    assert len(body["disasters"]) == 10  # and disasters at 10
    assert body["events"][0] == {
        "title": "Event 0",
        "type": "disaster",
        "severity": "critical",
        "location": "Place 0",
        "country": "Chile",
        "lat": -33.4,
        "lon": -70.6,
        "source": "GDACS",
    }
    assert body["disasters"][0] == {"title": "Disaster 0", "country": "Chile"}
    assert (body["planetary_hour"], body["day_ruler"], body["fetched_at"]) == ("Mars", "Saturn", "2026-10-24T22:00:00")
    assert body["summary"] == "3 significant world events detected."


def test_a_failing_fetch_is_still_a_500_with_the_message(app):
    from fastapi.testclient import TestClient

    with patch("core.internet_context.compile_world_context", side_effect=RuntimeError("feed exploded")):
        response = TestClient(app).get("/api/v1/operator/world-context")
    assert response.status_code == 500
    assert response.json()["detail"] == "feed exploded"
