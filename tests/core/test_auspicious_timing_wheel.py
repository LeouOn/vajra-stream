"""
Unit tests for the Auspicious Timing Wheel data engine.

Verifies:
1. 24 planetary hour slices (12 diurnal + 12 nocturnal) are generated with correct rulers.
2. Current active hour is correctly flagged based on local time.
3. Moon phase, glyph, tithi, and nakshatra are calculated.
4. Genre affinities (favorable/neutral/unfavorable) are populated for each genre.
5. Upcoming green windows per genre are resolved.
"""

from __future__ import annotations

from datetime import datetime

from core.auspicious_timing import (
    AuspiciousTiming,
    get_timing_wheel,
)


def test_get_timing_wheel_data_structure() -> None:
    timing = AuspiciousTiming()
    dt = datetime(2026, 8, 18, 14, 30)  # Tuesday afternoon
    wheel = timing.get_timing_wheel_data(lat=37.7749, lon=-122.4194, target_dt=dt)

    assert wheel["status"] == "success"
    assert "current_planetary_hour" in wheel
    assert "moon" in wheel
    assert "saka_dawa" in wheel
    assert "hourly_slices" in wheel
    assert "genre_windows" in wheel
    assert "next_optimal_windows" in wheel

    # Must contain exactly 24 hourly slices
    slices = wheel["hourly_slices"]
    assert len(slices) == 24

    day_slices = [s for s in slices if s["period"] == "day"]
    night_slices = [s for s in slices if s["period"] == "night"]
    assert len(day_slices) == 12
    assert len(night_slices) == 12

    # Exactly one slice should be flagged current
    current_slices = [s for s in slices if s["is_current"]]
    assert len(current_slices) == 1


def test_get_timing_wheel_genre_affinities() -> None:
    wheel = get_timing_wheel(lat=37.7749, lon=-122.4194)
    slices = wheel["hourly_slices"]

    # Each slice must have affinities for standard genres
    for s in slices:
        aff = s["affinities"]
        assert "healing" in aff
        assert "wisdom" in aff
        assert "purification" in aff
        assert "protection" in aff
        assert aff["healing"] in ("favorable", "neutral", "unfavorable")

    # Healing favorable hours (Jupiter, Venus, Moon, Sun)
    for s in slices:
        if s["ruler"] in ("Jupiter", "Venus", "Moon", "Sun"):
            assert s["affinities"]["healing"] == "favorable"
        elif s["ruler"] in ("Saturn", "Mars"):
            assert s["affinities"]["healing"] == "unfavorable"


def test_get_timing_wheel_moon_glyphs_and_tithi() -> None:
    wheel = get_timing_wheel()
    moon = wheel["moon"]

    assert "glyph" in moon
    assert moon["glyph"] in ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
    assert "phase_name" in moon
    assert "tithi" in moon
    assert "nakshatra" in moon
