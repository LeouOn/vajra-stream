# tests/core/context/test_hardware.py
"""Tests for HardwareContextModule."""
from __future__ import annotations

from core.context.hardware import HardwareContextModule
from core.context.models import ContextData, ContextRequest


async def test_hardware_not_requested_returns_empty():
    """When include_hardware is False, gather returns empty ContextData."""
    mod = HardwareContextModule()
    result = await mod.gather(ContextRequest())
    assert result.data == {}
    assert result.error is None


def test_hardware_render_sample_data():
    """render() produces Markdown from system-status / session data."""
    mod = HardwareContextModule()
    data = ContextData(
        module_name="hardware",
        data={
            "system_status": {
                "enhanced_mode": True,
                "active_sessions": 2,
                "current_audio": True,
                "spectrum_available": True,
                "modules_loaded": {"audio_generator": True, "astrology": True},
            },
            "sessions": [
                {"name": "blessing-1", "type": "blessing", "status": "running"},
                {"name": "healing-2", "type": "healing", "status": "idle"},
            ],
        },
    )
    rendered = mod.render(data)
    assert "Enhanced mode" in rendered
    assert "ON" in rendered
    assert "blessing-1" in rendered
    assert "running" in rendered


def test_hardware_render_empty_data_returns_empty():
    """render() returns '' for empty data."""
    mod = HardwareContextModule()
    assert mod.render(ContextData(module_name="hardware")) == ""


def test_hardware_render_bad_data_returns_empty():
    """render() never raises on malformed data."""
    mod = HardwareContextModule()
    bad = ContextData(module_name="hardware", data={"system_status": 42})
    result = mod.render(bad)
    assert isinstance(result, str)
