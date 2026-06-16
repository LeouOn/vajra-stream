# tests/core/context/test_astrology.py
"""Tests for AstrologyContextModule."""
from __future__ import annotations

from core.context.astrology import AstrologyContextModule
from core.context.models import ContextData, ContextRequest


async def test_astrology_not_requested_returns_empty():
    """When include_astrology is False, gather returns empty ContextData."""
    mod = AstrologyContextModule()
    result = await mod.gather(ContextRequest())
    assert result.data == {}
    assert result.error is None



async def test_astrology_uses_precomputed_data():
    """When astrology_data is supplied, gather uses it directly."""
    sample = {
        "western": {
            "positions": {"sun": {"sign": "Aries", "degree": 15.3}},
            "dominant_element": "Fire",
        },
        "indian": {
            "panchanga": {"tithi": {"name": "Shukla Paksha"}},
            "ayanamsa": 24.2,
        },
        "chinese": {"zodiac_animal": "Dragon"},
        "planetary_hours": {"current_planetary_hour": "Mars", "day_planet": "Sun"},
    }
    mod = AstrologyContextModule()
    request = ContextRequest(include_astrology=True, astrology_data=sample)
    result = await mod.gather(request)
    assert result.data == sample
    assert result.error is None


def test_astrology_render_sample_data():
    """render() produces Markdown sections from sample data."""
    mod = AstrologyContextModule()
    data = ContextData(
        module_name="astrology",
        data={
            "planetary_hours": {"current_planetary_hour": "Mars", "day_planet": "Sun"},
            "western": {
                "positions": {
                    "sun": {"sign": "Aries", "degree": 15.3},
                    "moon": {"sign": "Pisces", "degree": 28.1},
                },
                "dominant_element": "Fire",
            },
            "indian": {
                "panchanga": {"tithi": {"name": "Shukla"}, "nakshatra": {"name": "Rohini"}},
                "ayanamsa": 24.2,
            },
            "chinese": {
                "zodiac_animal": "Dragon",
                "lunar_date": {"formatted": "Year of Dragon"},
                "bazi": {"year": "Yang Wood Dragon"},
            },
        },
    )
    rendered = mod.render(data)
    assert "Mars" in rendered
    assert "Aries" in rendered
    assert "Fire" in rendered
    assert "Shukla" in rendered
    assert "Dragon" in rendered


def test_astrology_render_empty_data_returns_empty():
    """render() returns '' for empty data."""
    mod = AstrologyContextModule()
    assert mod.render(ContextData(module_name="astrology")) == ""


def test_astrology_render_bad_data_returns_empty():
    """render() never raises on malformed data."""
    mod = AstrologyContextModule()
    # Pass data that would trigger KeyError without defensive rendering.
    bad = ContextData(module_name="astrology", data={"western": "not-a-dict"})
    # Should not raise.
    result = mod.render(bad)
    assert isinstance(result, str)
