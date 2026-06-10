"""
API v1 endpoints package.

This file's __all__ is kept in sync with backend/app/api/v1/api.py
so `from backend.app.api.v1.endpoints import X` works for any endpoint.
The actual router registration in api.py imports modules directly.
"""

from . import (
    agent_suggestions,
    anatomy,
    astrology,
    audio,
    automation,
    blessing_slideshow,
    blessings,
    dharma_tales,
    divination,
    extraction,
    llm,
    locations,
    mops,
    operator,
    outlook,
    personal_healing,
    populations,
    prayer_wheel,
    radionics,
    radionics_narratives,
    ritual_engine,
    rng_attunement,
    scalar_waves,
    sessions,
    sigils,
    time_cycles,
    tts,
    visualization,
)

__all__ = [
    "agent_suggestions",
    "anatomy",
    "astrology",
    "audio",
    "automation",
    "blessing_slideshow",
    "blessings",
    "dharma_tales",
    "divination",
    "extraction",
    "llm",
    "locations",
    "mops",
    "operator",
    "outlook",
    "personal_healing",
    "populations",
    "prayer_wheel",
    "radionics",
    "radionics_narratives",
    "ritual_engine",
    "rng_attunement",
    "scalar_waves",
    "sessions",
    "sigils",
    "time_cycles",
    "tts",
    "visualization",
]
