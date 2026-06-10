"""
Tests for RitualScheduler pure methods and state transitions.

Covers:
- update_config (dict merge)
- _get_upcoming_schedule (24 entries, Chaldean cycle, favorable genres)
- status property (shape, in-memory state reflected)
- start/stop state transitions (no actual loop run)
- _is_timing_good_enough (currently always True - documents behavior)
"""

import asyncio

import pytest

from core.ritual_engine import (
    EngineState,
    RitualScheduler,
)


@pytest.fixture
def scheduler() -> RitualScheduler:
    """Fresh scheduler. No DB or async loop side effects."""
    return RitualScheduler()


# --- update_config ---


def test_update_config_merges_new_keys(scheduler: RitualScheduler):
    scheduler.update_config(tts_enabled=False, max_per_hour=5)
    assert scheduler._config["tts_enabled"] is False
    assert scheduler._config["max_per_hour"] == 5


def test_update_config_preserves_unspecified_keys(scheduler: RitualScheduler):
    original_min_quality = scheduler._config["min_timing_quality"]
    scheduler.update_config(tts_enabled=False)
    assert scheduler._config["min_timing_quality"] == original_min_quality


def test_update_config_with_no_args_is_noop(scheduler: RitualScheduler):
    original = dict(scheduler._config)
    scheduler.update_config()
    assert scheduler._config == original


def test_update_config_can_add_arbitrary_keys(scheduler: RitualScheduler):
    scheduler.update_config(custom_key="custom_value")
    assert scheduler._config["custom_key"] == "custom_value"


# --- _is_timing_good_enough ---


def test_is_timing_good_enough_currently_always_true(scheduler: RitualScheduler):
    """Documents current behavior: this method is a placeholder that
    always allows execution. The PracticeSelector handles scoring.
    The quality_rank dict is defined but never used."""
    for hour in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", ""]:
        for quality in ["excellent", "good", "challenging", "transmutative", "unknown"]:
            assert scheduler._is_timing_good_enough(hour, quality) is True, (
                f"unexpected false for hour={hour!r} quality={quality!r}"
            )


# --- _get_upcoming_schedule ---


def test_get_upcoming_schedule_returns_24_hours(scheduler: RitualScheduler):
    schedule = scheduler._get_upcoming_schedule()
    assert len(schedule) == 24


def test_get_upcoming_schedule_offsets_increment_by_1(scheduler: RitualScheduler):
    schedule = scheduler._get_upcoming_schedule()
    offsets = [h["hour_offset"] for h in schedule]
    assert offsets == list(range(24))


def test_get_upcoming_schedule_planets_from_chaldean_order(scheduler: RitualScheduler):
    chaldean = {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}
    schedule = scheduler._get_upcoming_schedule()
    for h in schedule:
        assert h["planet"] in chaldean, f"unexpected planet: {h['planet']!r}"


def test_get_upcoming_schedule_planet_cycles_correctly(scheduler: RitualScheduler):
    """Each hour shifts by one Chaldean position. After 7 hours we
    should be back at the same planet (mod 7 cycle)."""
    schedule = scheduler._get_upcoming_schedule()
    planets = [h["planet"] for h in schedule]
    # The 0th and 7th planet must match (Chaldean cycle = 7)
    assert planets[0] == planets[7]
    assert planets[0] == planets[14]
    assert planets[0] == planets[21]


def test_get_upcoming_schedule_favorable_genres_is_list(scheduler: RitualScheduler):
    schedule = scheduler._get_upcoming_schedule()
    for h in schedule:
        assert isinstance(h["favorable_genres"], list)
        # At most 3 genres per entry (truncated in source)
        assert len(h["favorable_genres"]) <= 3
        # All entries must be strings
        for g in h["favorable_genres"]:
            assert isinstance(g, str)
            assert g  # non-empty


# --- status property ---


def test_status_shape_keys(scheduler: RitualScheduler):
    s = scheduler.status
    expected_keys = {
        "state",
        "current_ritual",
        "rituals_today",
        "total_merit_today",
        "current_hour",
        "rituals_this_hour",
        "config",
        "history",
        "schedule",
    }
    assert set(s.keys()) == expected_keys


def test_status_initial_values(scheduler: RitualScheduler):
    s = scheduler.status
    assert s["state"] == EngineState.STOPPED.value
    assert s["current_ritual"] is None
    assert s["rituals_today"] == 0
    assert s["total_merit_today"] == 0
    assert s["current_hour"] == ""
    assert s["rituals_this_hour"] == 0
    assert s["history"] == []  # empty in-memory
    assert len(s["schedule"]) == 24  # from _get_upcoming_schedule
    assert s["config"]["enabled"] is True
    assert s["config"]["tts_enabled"] is True
    assert s["config"]["max_per_hour"] == 2


def test_status_reflects_in_memory_counter_changes(scheduler: RitualScheduler):
    scheduler._rituals_today = 7
    scheduler._total_merit_today = 42
    s = scheduler.status
    assert s["rituals_today"] == 7
    assert s["total_merit_today"] == 42


# --- start/stop state transitions ---


def test_initial_state_is_stopped(scheduler: RitualScheduler):
    assert scheduler.state == EngineState.STOPPED
    assert scheduler._task is None


def test_start_transitions_to_running(scheduler: RitualScheduler):
    """start() should flip state and create a task. We cancel the
    task immediately so no actual loop runs."""
    asyncio.run(_start_then_stop(scheduler))
    assert scheduler._task is None or scheduler._task.cancelled() or scheduler._task.done()


async def _start_then_stop(scheduler: RitualScheduler):
    await scheduler.start()
    assert scheduler.state == EngineState.RUNNING
    assert scheduler._task is not None
    # Stop cancels the task; we tolerate a brief window where it's still alive
    await scheduler.stop()
    assert scheduler.state == EngineState.STOPPED


def test_start_is_idempotent_when_already_running(scheduler: RitualScheduler):
    async def runner():
        await scheduler.start()
        first_task = scheduler._task
        await scheduler.start()  # second call
        assert scheduler._task is first_task, "second start() should not create a new task"
        await scheduler.stop()

    asyncio.run(runner())


def test_stop_when_not_running_is_safe(scheduler: RitualScheduler):
    async def runner():
        # No prior start
        await scheduler.stop()
        assert scheduler.state == EngineState.STOPPED

    asyncio.run(runner())
