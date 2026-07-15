# tests/core/context/test_anatomy.py
"""Tests for AnatomyContextModule."""

from __future__ import annotations

from core.context.anatomy import AnatomyContextModule
from core.context.models import ContextData, ContextRequest


async def test_anatomy_not_requested_returns_empty():
    """When include_anatomy is False, gather returns empty ContextData."""
    mod = AnatomyContextModule()
    result = await mod.gather(ContextRequest())
    assert result.data == {}
    assert result.error is None


def test_anatomy_render_sample_data():
    """render() produces Markdown from chakra/meridian data."""
    mod = AnatomyContextModule()
    data = ContextData(
        module_name="anatomy",
        data={
            "chakras": {
                "heart": {
                    "name": "Heart",
                    "sanskrit": "Anahata",
                    "governs": "love, compassion",
                    "frequencies": {"heart": 639, "balancing": 639},
                    "crystals": ["Rose Quartz", "Emerald"],
                    "affirmations": ["I am love"],
                },
            },
            "meridians": {
                "heart": {"element": "Fire", "emotion": "joy", "frequency": 639, "color": "red"},
            },
        },
    )
    rendered = mod.render(data)
    assert "Heart" in rendered
    assert "Anahata" in rendered
    assert "Rose Quartz" in rendered
    assert "Meridians" in rendered


def test_anatomy_render_empty_data_returns_empty():
    """render() returns '' for empty data."""
    mod = AnatomyContextModule()
    assert mod.render(ContextData(module_name="anatomy")) == ""


def test_anatomy_render_bad_data_returns_empty():
    """render() never raises on malformed data."""
    mod = AnatomyContextModule()
    bad = ContextData(module_name="anatomy", data={"chakras": "not-a-dict"})
    result = mod.render(bad)
    assert isinstance(result, str)
