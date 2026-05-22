"""
LLM Agent Interface for Vajra Stream

Provides tool-calling interface for LLM agents to interact with the
radionics and blessing system.
"""

from .tools import (
    # Registry
    TOOL_REGISTRY,
    # Slideshow Tools
    create_blessing_slideshow,
    # Population Tools
    create_population,
    # RNG Tools
    create_rng_session,
    get_automation_stats,
    get_automation_status,
    get_current_slide,
    get_population_statistics,
    get_rng_reading,
    get_tool_schemas,
    list_populations,
    pause_automation,
    resume_automation,
    # Automation Tools
    start_automation,
    stop_automation,
    stop_rng_session,
    stop_slideshow,
    update_population,
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
    "get_tool_schemas",
]
