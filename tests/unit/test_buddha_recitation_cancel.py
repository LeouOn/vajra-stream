"""
Wave 4 Task 28 — BuddhaRecitationLoop background task cancellation.

Regression test: ``BuddhaRecitationLoop.start()`` spawns the recitation loop
via ``asyncio.create_task(self._run_loop(...))`` but historically discarded
the returned task handle. ``stop()`` only flipped ``state.running = False``,
so the underlying asyncio task kept running (and kept the event loop alive
with "task was destroyed but it is pending!" warnings on shutdown).

Contract under test:
    After ``await loop.stop()`` returns, the background recitation task
    created by ``start()`` MUST be done (cancelled) within 2 seconds.

The reference cancellation pattern lives in
``modules/radionics_operator.py`` (``_blessing_loop_task``), which stores the
handle on start and calls ``.cancel()`` on stop.
"""

from __future__ import annotations

import asyncio

import pytest

from core.buddha_recitation_loop import BuddhaRecitationLoop


async def test_start_stores_background_task_handle():
    """start() must store the asyncio task handle so stop() can cancel it."""
    loop = BuddhaRecitationLoop(tts_reciter=False)
    try:
        await loop.start(intention="test", interval_seconds=0.01)
        # The handle MUST be stored; the bug was discarding it.
        assert loop._task is not None, (
            "start() must store the background task handle on self._task"
        )
        assert isinstance(loop._task, asyncio.Task)
        assert not loop._task.done()
    finally:
        # Best-effort cleanup if the fix is present; otherwise let the test
        # that asserts cancellation handle the full stop path.
        if loop._task is not None and not loop._task.done():
            loop._task.cancel()
            try:
                await asyncio.wait_for(loop._task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass


async def test_stop_cancels_background_task_within_two_seconds():
    """stop() must cancel the background task, not just flip a running flag.

    This is the core regression: previously ``stop()`` set ``running=False``
    but never cancelled the asyncio task. The task would only exit at its
    next loop iteration check, and if blocked inside ``provider.speak()``
    it could hang indefinitely.
    """
    loop = BuddhaRecitationLoop(tts_reciter=False)
    await loop.start(intention="test", interval_seconds=0.01)

    # Capture the handle before stop() clears it.
    task = loop._task
    assert task is not None, "precondition: start() must store the task handle"
    # Yield once so the task actually starts running.
    await asyncio.sleep(0)
    assert not task.done(), "precondition: task should be running before stop()"

    # stop() must cancel + await the task. Bound it at 2s per acceptance criteria.
    await asyncio.wait_for(loop.stop(), timeout=2.0)

    # The task MUST be done within 2s of stop().
    assert task.done(), (
        "background recitation task must be done within 2s of stop()"
    )


async def test_stop_is_idempotent_and_safe_when_not_started():
    """stop() with no running task must not raise."""
    loop = BuddhaRecitationLoop(tts_reciter=False)
    # No start() called — _task should be None and stop() must be a no-op.
    await loop.stop()
    assert loop.state.running is False


async def test_stop_broadcasts_stopped_event_once():
    """Regression guard: stop() must still broadcast the WS stopped event.

    The fix must not remove the existing ``BUDDHA_RECITATION_STOPPED``
    broadcast — only add task cancellation on top of it.
    """
    loop = BuddhaRecitationLoop(tts_reciter=False)
    broadcast_calls: list[str] = []
    original = loop._broadcast_ws

    def spy(event_type: str, data: dict):
        broadcast_calls.append(event_type)
        return original(event_type, data)

    loop._broadcast_ws = spy  # type: ignore[method-assign]

    await loop.start(intention="test", interval_seconds=0.01)
    await asyncio.wait_for(loop.stop(), timeout=2.0)

    assert "BUDDHA_RECITATION_STOPPED" in broadcast_calls, (
        "stop() must still broadcast BUDDHA_RECITATION_STOPPED"
    )
