"""
LLM Agent Interface for Vajra Stream

Provides tool-calling interface for LLM agents to interact with the
radionics and blessing system.
"""

from .tools import (
    # RNG Tools
    create_rng_session,
    get_rng_reading,
    stop_rng_session,

    # Slideshow Tools
    create_blessing_slideshow,
    get_current_slide,
    stop_slideshow,

    # Population Tools
    create_population,
    list_populations,
    get_population_statistics,
    update_population,

    # Automation Tools
    start_automation,
    get_automation_status,
    get_automation_stats,
    stop_automation,
    pause_automation,
    resume_automation,

    # Registry
    TOOL_REGISTRY,
    get_tool_schemas
)

__all__ = [
    # RNG
    "create_rng_session",
    "get_rng_reading",
    "stop_rng_session",

    # Slideshow
    "create_blessing_slideshow",
    "get_current_slide",
    "stop_slideshow",

    # Population
    "create_population",
    "list_populations",
    "get_population_statistics",
    "update_population",

    # Automation
    "start_automation",
    "get_automation_status",
    "get_automation_stats",
    "stop_automation",
    "pause_automation",
    "resume_automation",

    # Utility
    "TOOL_REGISTRY",
    "get_tool_schemas"
]
