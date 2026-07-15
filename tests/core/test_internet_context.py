"""
Smoke + behaviour tests for ``core.internet_context``.

Covers the public surface:
- :class:`WorldEvent` — dataclass + ``to_context_str`` formatting.
- :class:`InternetContext` — empty/populated ``to_prompt_context`` rendering.
- :func:`get_planetary_hour` — returns a tuple of two non-empty strings.
- :func:`fetch_gdacs_disasters` and :func:`fetch_reliefweb_headlines` —
  graceful failure on network errors (return ``[]``).
- :func:`compile_world_context` — builds an ``InternetContext`` with all
  fetches disabled, exercising the build-summary logic in isolation.

Heavy deps (``urllib``, ``core.astrology``) are mocked so tests are fast
and offline-safe.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.internet_context import (
    InternetContext,
    WorldEvent,
    compile_world_context,
    fetch_gdacs_disasters,
    fetch_reliefweb_headlines,
    format_context_for_llm,
    get_planetary_hour,
)

# ---------------------------------------------------------------------------
# 1. WorldEvent dataclass + to_context_str
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_world_event_to_context_str_formats_fields():
    """``to_context_str`` formats event_type, severity, title, description, location."""
    evt = WorldEvent(
        title="Earthquake 7.2",
        description="Major earthquake struck region, causing widespread damage and displacement",
        location="Japan",
        event_type="disaster",
        severity="critical",
    )

    line = evt.to_context_str()
    # event_type is upper-cased; severity is left as supplied
    assert "[DISASTER|critical]" in line
    assert "Earthquake 7.2" in line
    assert "Japan" in line
    # Description is truncated to 120 chars
    assert len(line) < 250


@pytest.mark.unit
def test_world_event_default_values():
    """Defaults: event_type 'general', severity 'medium', no source/date/url."""
    evt = WorldEvent(title="x", description="y")

    assert evt.event_type == "general"
    assert evt.severity == "medium"
    assert evt.location == ""
    assert evt.source == ""
    assert evt.date == ""
    assert evt.url == ""


# ---------------------------------------------------------------------------
# 2. InternetContext.to_prompt_context — empty + populated
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_internet_context_to_prompt_context_empty_returns_empty_string():
    """Empty context (no events, no transits) returns empty string."""
    ctx = InternetContext()
    assert ctx.to_prompt_context() == ""


@pytest.mark.unit
def test_internet_context_to_prompt_context_includes_transits_and_events():
    """Populated context includes celestial timing, events, disasters, summary."""
    ctx = InternetContext(
        events=[
            WorldEvent(
                title="Flood",
                description="Severe flooding in coastal areas",
                event_type="disaster",
                severity="high",
            )
        ],
        disasters=[{"title": "Quake", "location": "Chile", "severity": "critical"}],
        astro_transits={"moon_phase": {"phase_name": "full", "illumination": 100}},
        planetary_hour="Mars",
        day_ruler="Sun",
        summary="3 events detected",
    )

    text = ctx.to_prompt_context()
    assert "Current World Context" in text
    assert "Planetary Hour: Mars" in text
    assert "Day Ruler: Sun" in text
    assert "Moon: full" in text
    assert "Active World Events" in text
    assert "Flood" in text
    assert "Active Disasters" in text
    assert "Quake" in text
    assert "3 events detected" in text


# ---------------------------------------------------------------------------
# 3. get_planetary_hour returns a tuple of two non-empty strings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_planetary_hour_returns_tuple_of_strings():
    """Returns (planetary_hour, day_ruler), both non-empty."""
    hour, ruler = get_planetary_hour()

    assert isinstance(hour, str) and hour
    assert isinstance(ruler, str) and ruler
    # Day rulers come from a fixed list of 7
    assert ruler in {"Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"}
    # Planetary hours are one of the 7 classical planets
    assert hour in {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}


# ---------------------------------------------------------------------------
# 4. Network fetchers — graceful failure returns []
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetch_gdacs_disasters_returns_empty_on_http_failure():
    """``fetch_gdacs_disasters`` returns ``[]`` when the HTTP fetch fails."""
    with patch("core.internet_context._safe_http_get", return_value=None):
        assert fetch_gdacs_disasters() == []


@pytest.mark.unit
def test_fetch_reliefweb_headlines_returns_empty_on_http_failure():
    """``fetch_reliefweb_headlines`` returns ``[]`` when the HTTP fetch fails."""
    with patch("core.internet_context._safe_http_get", return_value=None):
        assert fetch_reliefweb_headlines() == []


# ---------------------------------------------------------------------------
# 5. compile_world_context — all-fetches-disabled produces a valid context
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compile_world_context_no_sources_builds_empty_context():
    """With all flags off, no fetches happen; context has empty events/disasters."""
    ctx = compile_world_context(
        include_disasters=False,
        include_headlines=False,
        include_astrology=False,
    )

    assert isinstance(ctx, InternetContext)
    assert ctx.events == []
    assert ctx.disasters == []
    assert ctx.astro_transits == {}
    # Planetary hour is still set
    assert ctx.planetary_hour != ""
    assert ctx.day_ruler != ""
    assert ctx.fetched_at != ""
    # No events → no summary text
    assert ctx.summary == ""


# ---------------------------------------------------------------------------
# 6. format_context_for_llm is a thin wrapper around to_prompt_context
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_context_for_llm_delegates_to_to_prompt_context():
    """``format_context_for_llm(ctx)`` returns the same string as ``ctx.to_prompt_context()``."""
    ctx = InternetContext(planetary_hour="Sun", day_ruler="Sun")
    assert format_context_for_llm(ctx) == ctx.to_prompt_context()
