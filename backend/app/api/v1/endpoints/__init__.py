"""
API v1 endpoints package.

This file's __all__ is kept in sync with backend/app/api/v1/api.py
so `from backend.app.api.v1.endpoints import X` works for any endpoint.
The actual router registration in api.py imports modules directly.
"""
from . import agent_suggestions
from . import anatomy
from . import astrology
from . import audio
from . import automation
from . import blessing_slideshow
from . import blessings
from . import dharma_tales
from . import divination
from . import llm
from . import mops
from . import operator
from . import outlook
from . import personal_healing
from . import populations
from . import prayer_wheel
from . import radionics
from . import radionics_narratives
from . import ritual_engine
from . import rng_attunement
from . import scalar_waves
from . import sessions
from . import sigils
from . import time_cycles
from . import tts
from . import visualization

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
    "llm",
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
