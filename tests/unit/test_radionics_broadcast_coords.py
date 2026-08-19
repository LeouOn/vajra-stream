"""
Unit tests for Radionics broadcast target resolution and coordinate emission.

Verifies:
1. situation_geometry.resolve_target_coordinates pipeline (known locations, compound phrases, honesty rules).
2. RadionicsService.broadcast_healing coordinate resolution and WebSocket broadcast payload.
3. Event bus publication of HealingBroadcastStarted with lat/lon telemetry.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.situation_geometry import (
    KNOWN_LOCATION_COORDS,
    resolve_target_coordinates,
)
from modules.interfaces import HealingBroadcastStarted
from modules.radionics import RadionicsService


def test_resolve_target_coordinates_direct_matches() -> None:
    assert resolve_target_coordinates("Japan") == KNOWN_LOCATION_COORDS["japan"]
    assert resolve_target_coordinates("tokyo") == KNOWN_LOCATION_COORDS["tokyo"]
    assert resolve_target_coordinates("Brazil") == KNOWN_LOCATION_COORDS["brazil"]
    assert resolve_target_coordinates("Nepal") == KNOWN_LOCATION_COORDS["nepal"]


def test_resolve_target_coordinates_compound_and_substring() -> None:
    # "East Java, Indonesia" should prioritize the island segment "East Java" -> java
    assert resolve_target_coordinates("East Java, Indonesia") == KNOWN_LOCATION_COORDS["java"]
    # City in phrase
    assert resolve_target_coordinates("Prayers for Kathmandu") == KNOWN_LOCATION_COORDS["kathmandu"]
    # Regional crisis zones
    assert resolve_target_coordinates("Relief in Gaza") == KNOWN_LOCATION_COORDS["gaza"]
    assert resolve_target_coordinates("Kigali, Rwanda") == KNOWN_LOCATION_COORDS["kigali"]


def test_resolve_target_coordinates_honesty_rules() -> None:
    # Universal / abstract targets must return None (no fake pins)
    assert resolve_target_coordinates("all beings") is None
    assert resolve_target_coordinates("all sentient beings") is None
    assert resolve_target_coordinates("the field") is None
    assert resolve_target_coordinates("world peace") is None
    assert resolve_target_coordinates("") is None
    assert resolve_target_coordinates(None) is None


def test_broadcast_healing_emits_resolved_coordinates() -> None:
    event_bus = MagicMock()
    service = RadionicsService(event_bus=event_bus)
    service.broadcaster.broadcast_to_targets = MagicMock(return_value={"status": "completed", "mops": 15.0})

    # Broadcast to a known location
    result = service.broadcast_healing(
        target_name="Tokyo Hospital",
        duration_minutes=5,
        frequency_hz=528.0,
        intensity=0.8,
    )

    assert result["status"] == "active"
    assert result["lat"] == pytest.approx(35.6762, abs=0.01)
    assert result["lon"] == pytest.approx(139.6503, abs=0.01)
    assert result["target"] == "Tokyo Hospital"

    # Verify event bus publication
    assert event_bus.publish.called
    published_event = event_bus.publish.call_args[0][0]
    assert isinstance(published_event, HealingBroadcastStarted)
    assert published_event.target_name == "Tokyo Hospital"
    assert published_event.lat == pytest.approx(35.6762, abs=0.01)
    assert published_event.lon == pytest.approx(139.6503, abs=0.01)
    assert published_event.duration_minutes == 5


def test_broadcast_healing_explicit_coordinates_override() -> None:
    event_bus = MagicMock()
    service = RadionicsService(event_bus=event_bus)
    service.broadcaster.broadcast_to_targets = MagicMock(return_value={"status": "completed", "mops": 15.0})

    # Pass explicit custom coordinates
    result = service.broadcast_healing(
        target_name="Custom Sacred Site",
        duration_minutes=10,
        frequency_hz=432.0,
        location="Mount Shasta",
        lat=41.4092,
        lon=-122.1949,
    )

    assert result["lat"] == 41.4092
    assert result["lon"] == -122.1949
    assert result["location"] == "Mount Shasta"

    published_event = event_bus.publish.call_args[0][0]
    assert published_event.lat == 41.4092
    assert published_event.lon == -122.1949
