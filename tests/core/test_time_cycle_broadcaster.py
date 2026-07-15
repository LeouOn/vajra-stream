"""
Smoke + behaviour tests for ``core.time_cycle_broadcaster``.

Covers the public surface of :class:`TimeCycleBroadcaster`:

* Module import + top-level exports (``HAS_BLESSINGS``,
  ``HAS_ASTRO``, ``HAS_VIZ``)
* ``__init__`` with default and custom events files
* Event lookups: ``list_events``, ``get_event_by_id`` (hit + miss)
* Date helpers: ``parse_date`` and ``generate_date_range``
* ``create_blessing_targets_for_event`` (graceful no-op when the
  blessing subsystem is unavailable)
* ``broadcast_to_date`` end-to-end with blessing/astro/viz subsystems
  swapped for mocks
* ``run_daily_cycle`` with a single mocked day
* ``run_daily_cycle`` raises ``ValueError`` on an unknown event id

The real radionics broadcast is replaced with a no-op (no ``time.sleep``)
and astrocartography / visualization are stubbed out via monkeypatch.
"""

from __future__ import annotations

import datetime as _dt
import json
from unittest.mock import MagicMock

import pytest

from core import time_cycle_broadcaster as tcb
from core.time_cycle_broadcaster import TimeCycleBroadcaster

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_EVENTS = {
    "archetypal_healing_cycles": [
        {
            "id": "test-event",
            "name": "Test Healing Cycle",
            "description": "A test event.",
            "start_date": "2020-01-01",
            "end_date": "2020-01-03",
            "primary_locations": [
                {"name": "Test Place", "lat": 10.0, "lon": 20.0, "country": "Earth"},
            ],
            "estimated_deaths": 100,
            "population_affected": "Test beings",
            "blessing_focus": "May peace prevail.",
            "mantras": ["Om Mani Padme Hum"],
            "visualization_themes": ["healing light"],
        },
    ],
}


@pytest.fixture
def events_file(tmp_path):
    """Write a minimal events JSON to a tmp file and return its path."""
    p = tmp_path / "events.json"
    p.write_text(json.dumps(SAMPLE_EVENTS))
    return p


@pytest.fixture
def broadcaster(events_file, monkeypatch):
    """A TimeCycleBroadcaster pointing at the tmp events file with heavy
    subsystems (blessings, astro, viz) replaced with no-op mocks so the
    tests stay fast and isolated.
    """
    # Mock the heavy subsystems
    monkeypatch.setattr(tcb, "HAS_BLESSINGS", True)
    monkeypatch.setattr(tcb, "HAS_ASTRO", True)
    monkeypatch.setattr(tcb, "HAS_VIZ", True)

    fake_db = MagicMock(name="BlessingDatabase")
    fake_db.add_target = MagicMock()
    fake_db.record_session = MagicMock(return_value="session-1")
    fake_db.record_dedication = MagicMock()

    fake_astro = MagicMock(name="AstrocartographyCalculator")
    fake_chart = MagicMock(name="HistoricalChartCalculator")
    fake_chart.calculate_chart = MagicMock(return_value={"location_name": "Test Place"})

    monkeypatch.setattr(tcb, "BlessingDatabase", lambda: fake_db)
    monkeypatch.setattr(tcb, "AstrocartographyCalculator", lambda: fake_astro)
    monkeypatch.setattr(tcb, "HistoricalChartCalculator", lambda: fake_chart)

    bc = TimeCycleBroadcaster(events_file=str(events_file))
    # Replace blessing_db with the fake to ensure consistent behaviour
    bc.blessing_db = fake_db
    bc.chart_calc = fake_chart
    return bc


# ---------------------------------------------------------------------------
# 1. Import smoke + module-level flags
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_module_imports_and_exports():
    """Module imports cleanly and exposes its top-level names."""
    assert callable(TimeCycleBroadcaster)
    # Availability flags are booleans
    assert isinstance(tcb.HAS_BLESSINGS, bool)
    assert isinstance(tcb.HAS_ASTRO, bool)
    assert isinstance(tcb.HAS_VIZ, bool)
    # Convenience helpers are exposed
    assert callable(tcb.list_all_events)
    assert callable(tcb.run_quick_test)


# ---------------------------------------------------------------------------
# 2. Constructor — default vs custom events_file
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_constructor_loads_events(events_file):
    """``TimeCycleBroadcaster(events_file=...)`` loads that file's events."""
    bc = TimeCycleBroadcaster(events_file=str(events_file))
    assert bc.events_file == str(events_file)
    assert len(bc.list_events()) == 1
    assert bc.list_events()[0]["id"] == "test-event"


@pytest.mark.unit
def test_constructor_handles_missing_events_file(tmp_path):
    """Missing events file → empty events list, no exception."""
    bc = TimeCycleBroadcaster(events_file=str(tmp_path / "nope.json"))
    assert bc.list_events() == []


# ---------------------------------------------------------------------------
# 3. Event lookup
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_event_by_id_found_and_missing(broadcaster):
    """``get_event_by_id`` returns the matching event or None."""
    event = broadcaster.get_event_by_id("test-event")
    assert event is not None
    assert event["name"] == "Test Healing Cycle"

    missing = broadcaster.get_event_by_id("nope")
    assert missing is None


@pytest.mark.unit
def test_list_events_returns_all(broadcaster):
    """``list_events`` returns every event in the file."""
    events = broadcaster.list_events()
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0]["id"] == "test-event"


# ---------------------------------------------------------------------------
# 4. Date helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_date_returns_datetime(broadcaster):
    """``parse_date`` returns a ``datetime`` for a YYYY-MM-DD string."""
    result = broadcaster.parse_date("2020-06-15")
    assert isinstance(result, _dt.datetime)
    assert result.year == 2020
    assert result.month == 6
    assert result.day == 15


@pytest.mark.unit
def test_generate_date_range_inclusive_with_step(broadcaster):
    """``generate_date_range`` produces every step_days-th date, inclusive."""
    dates = broadcaster.generate_date_range("2020-01-01", "2020-01-05", step_days=1)
    assert len(dates) == 5
    assert dates[0] == _dt.datetime(2020, 1, 1)
    assert dates[-1] == _dt.datetime(2020, 1, 5)

    # step_days=2 → every other day, still inclusive
    dates2 = broadcaster.generate_date_range("2020-01-01", "2020-01-05", step_days=2)
    assert [d.day for d in dates2] == [1, 3, 5]


# ---------------------------------------------------------------------------
# 5. create_blessing_targets_for_event — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_blessing_targets_when_subsystem_unavailable(events_file, monkeypatch):
    """When ``HAS_BLESSINGS`` is False, the helper returns an empty list
    without raising."""
    monkeypatch.setattr(tcb, "HAS_BLESSINGS", False)
    bc = TimeCycleBroadcaster(events_file=str(events_file))
    bc.blessing_db = None

    result = bc.create_blessing_targets_for_event(SAMPLE_EVENTS["archetypal_healing_cycles"][0])
    assert result == []


@pytest.mark.unit
def test_create_blessing_targets_creates_main_and_location_targets(broadcaster):
    """With the blessing subsystem available, main + per-location targets are added."""
    event = SAMPLE_EVENTS["archetypal_healing_cycles"][0]
    target_ids = broadcaster.create_blessing_targets_for_event(event)
    # Main target + 1 location target
    assert len(target_ids) == 2
    broadcaster.blessing_db.add_target.assert_called()


# ---------------------------------------------------------------------------
# 6. broadcast_to_date — end-to-end with mocked subsystems
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_broadcast_to_date_records_session_and_dedication(broadcaster, monkeypatch):
    """``broadcast_to_date`` calls the blessing DB, records a session,
    and dedicates mantras for every target."""
    # Disable the real radionics sleep + the visualization (we want a fast test)
    monkeypatch.setattr(tcb.time, "sleep", lambda s: None)
    broadcaster._create_daily_visualization = MagicMock(return_value="/tmp/viz.png")

    event = SAMPLE_EVENTS["archetypal_healing_cycles"][0]
    result = broadcaster.broadcast_to_date(
        event=event,
        date=_dt.datetime(2020, 1, 2),
        duration_seconds=0,  # avoids the time.sleep(min(duration, 3)) call entirely
        create_visualization=True,
    )

    # Result shape
    assert result["event_id"] == "test-event"
    assert result["date"] == "2020-01-02"
    assert isinstance(result["actions"], list)
    assert len(result["actions"]) >= 3  # astro, blessing, viz, radionics

    # Astrocartography was called
    broadcaster.chart_calc.calculate_chart.assert_called_once()
    # Blessing session + dedication recorded
    broadcaster.blessing_db.record_session.assert_called_once()
    broadcaster.blessing_db.record_dedication.assert_called()
    # Visualization created
    broadcaster._create_daily_visualization.assert_called_once()


@pytest.mark.unit
def test_broadcast_to_date_handles_astro_failure(broadcaster, monkeypatch):
    """If astrocartography raises, the failure is captured, broadcast still proceeds."""
    monkeypatch.setattr(tcb.time, "sleep", lambda s: None)
    broadcaster._create_daily_visualization = MagicMock(return_value="/tmp/viz.png")
    broadcaster.chart_calc.calculate_chart.side_effect = RuntimeError("boom")

    event = SAMPLE_EVENTS["archetypal_healing_cycles"][0]
    result = broadcaster.broadcast_to_date(
        event=event,
        date=_dt.datetime(2020, 1, 2),
        duration_seconds=0,
        create_visualization=False,
    )

    # The astro action was recorded as failed
    astro_actions = [a for a in result["actions"] if a["type"] == "astrocartography"]
    assert len(astro_actions) == 1
    assert astro_actions[0]["status"] == "failed"
    assert "boom" in astro_actions[0]["error"]


# ---------------------------------------------------------------------------
# 7. run_daily_cycle — single day, mocked broadcast
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_daily_cycle_processes_each_date(broadcaster, monkeypatch):
    """``run_daily_cycle`` iterates through every date and returns a result per day."""
    # Avoid the real radionics sleep
    monkeypatch.setattr(tcb.time, "sleep", lambda s: None)
    # Skip the visualization creation (we're not testing the file path here)
    broadcaster._create_daily_visualization = MagicMock(return_value="/tmp/viz.png")

    results = broadcaster.run_daily_cycle(
        event_id="test-event",
        start_date="2020-01-01",
        end_date="2020-01-03",
        step_days=1,
        duration_per_day=0,
        create_visualizations=False,
    )

    assert len(results) == 3
    # Every result has the expected shape
    for r in results:
        assert r["event_id"] == "test-event"
        assert "actions" in r


# ---------------------------------------------------------------------------
# 8. run_daily_cycle — unknown event raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_daily_cycle_unknown_event_raises(events_file):
    """Calling ``run_daily_cycle`` with an unknown id raises ``ValueError``."""
    bc = TimeCycleBroadcaster(events_file=str(events_file))
    with pytest.raises(ValueError) as excinfo:
        bc.run_daily_cycle(event_id="does-not-exist")
    assert "does-not-exist" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 9. run_sample_cycle — uses num_days and overrides duration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_sample_cycle_limits_to_num_days(broadcaster, monkeypatch):
    """``run_sample_cycle`` honours ``num_days`` and overrides ``duration_per_day``."""
    monkeypatch.setattr(tcb.time, "sleep", lambda s: None)
    broadcaster._create_daily_visualization = MagicMock(return_value="/tmp/viz.png")
    # Capture the duration_per_day forwarded to broadcast_to_date
    captured = {}

    real_broadcast = broadcaster.broadcast_to_date

    def spy_broadcast(*args, **kwargs):
        captured["duration_seconds"] = kwargs.get("duration_seconds")
        return real_broadcast(*args, **kwargs)

    broadcaster.broadcast_to_date = spy_broadcast

    results = broadcaster.run_sample_cycle(event_id="test-event", num_days=2, create_visualizations=False)

    # num_days=2 over a 3-day range → 2 results
    assert len(results) == 2
    # The helper hardcodes duration_per_day=10 for fast testing
    assert captured["duration_seconds"] == 10
