"""
LLM tool handlers for Vajra Stream.

This module holds the one implementation of every LLM tool. The tools
themselves (name, schema, surfaces, flags) are defined in
:mod:`core.tool_registry`, whose specs point here by ``"module:function"``;
call a tool through ``core.tool_registry.call``/``acall`` so argument
normalization and surface checks apply.

Handlers take keyword arguments. A handler that needs the DI container takes
``container=None`` and falls back to the global container.

Every tool runs IN-PROCESS against the backing service or endpoint function.
Tools must not HTTP back into this same FastAPI process — the socket hop can
deadlock a saturated worker, couples tools to port 8008, and lets endpoint
paths silently drift into 404 ghosts.
"""

import asyncio
import os
import time
from typing import Any

from core import tool_registry
from core.situation_geometry import DEFAULT_LAT, DEFAULT_LNG

# ============================================================================
# IN-PROCESS BRIDGE
# ----------------------------------------------------------------------------
# ``_run_async`` bridges sync tool bodies to async services on the persistent
# background loop (safe from inside a running event loop); ``_spawn`` is the
# fire-and-forget twin for background work like audio playback.
# ============================================================================


def _run_async(coro: Any) -> Any:
    """Run an async service call from a sync tool body and return its result."""
    from core.llm.legacy_adapter import run_async

    return run_async(coro)


def _spawn(coro: Any) -> None:
    """Schedule an async side-effect (e.g. audio playback) without waiting."""
    from core.llm.legacy_adapter import spawn_async

    spawn_async(coro)


def _dump(result: Any) -> Any:
    """Normalize a Pydantic model returned by an endpoint function to a dict."""
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


def _resolve_container(container: Any = None) -> Any:
    """The caller's DI container, else the global one."""
    if container is not None:
        return container
    from container import container as global_container

    return global_container


def _operator_call(container: Any, method: str, **kwargs: Any) -> Any:
    """Delegate to the container's RadionicsOperator (agentic journey operations)."""
    op = getattr(_resolve_container(container), "operator", None)
    if op is not None and hasattr(op, method):
        return getattr(op, method)(**kwargs)
    return {"error": f"Operator method {method} unavailable"}


# ============================================================================
# RNG ATTUNEMENT TOOLS
# ============================================================================


def create_rng_session(
    baseline_tone_arm: float = 5.0, sensitivity: float = 1.0, session_id: str | None = None
) -> dict[str, Any]:
    """
    Create a new RNG attunement session for monitoring psychoenergetic activity.

    Use this when:
    - User wants to monitor RNG during practice
    - Starting manual radionics session
    - Need floating needle detection

    Args:
        baseline_tone_arm: Baseline setting (0-10), default 5.0
        sensitivity: Sensitivity multiplier (0.1-5.0), default 1.0
        session_id: Optional session identifier

    Returns:
        {"session_id": "rng_1234567890_abcdef12", "status": "active"}
    """
    from backend.core.services.rng_attunement_service import get_rng_service

    service = get_rng_service()
    session_id = service.create_session(
        session_id=session_id, baseline_tone_arm=baseline_tone_arm, sensitivity=sensitivity
    )
    return {"session_id": session_id, "status": "active"}


def get_rng_reading(session_id: str) -> dict[str, Any]:
    """
    Get current RNG reading including needle state and floating needle score.

    Every value is a draw (the RNG as stick pad), not a measurement; the
    output says so in ``note`` and ``provenance``.

    Args:
        session_id: RNG session ID from create_rng_session
    """
    from backend.core.services.rng_attunement_service import (
        ATTUNEMENT_DRAW_NOTE,
        get_rng_service,
        reading_provenance,
    )

    service = get_rng_service()
    reading = service.get_reading(session_id)
    if reading is None:
        return {"error": "Session not found or inactive"}
    return {
        "timestamp": reading.timestamp,
        "raw_value": reading.raw_value,
        "tone_arm": reading.tone_arm,
        "needle_position": reading.needle_position,
        "needle_state": reading.needle_state.value if hasattr(reading.needle_state, "value") else reading.needle_state,
        "quality": reading.quality.value if hasattr(reading.quality, "value") else reading.quality,
        "entropy": reading.entropy,
        "coherence": reading.coherence,
        "trend": reading.trend,
        "floating_needle_score": reading.floating_needle_score,
        "note": ATTUNEMENT_DRAW_NOTE,
        "provenance": reading_provenance(),
    }


def stop_rng_session(session_id: str) -> dict[str, Any]:
    """Stop active RNG session"""
    from backend.core.services.rng_attunement_service import get_rng_service

    service = get_rng_service()
    summary = service.get_session_summary(session_id) or {}
    service.stop_session(session_id)
    return summary


# ============================================================================
# AUDIO TOOLS
# ----------------------------------------------------------------------------
# ADR 001: the user-facing audio subsystem is the ``vajra_service``
# singleton — these tools call it in-process instead of POSTing to
# ``/api/v1/audio/*``.
# ============================================================================


def _audio_generate(config: dict[str, Any]) -> dict[str, Any]:
    """Generate prayer-bowl audio on the canonical vajra_service (in-process)."""
    from backend.core.services.vajra_service import AudioConfig as ServiceAudioConfig
    from backend.core.services.vajra_service import vajra_service

    service_config = ServiceAudioConfig(
        frequency=config["frequency"],
        duration=config["duration"],
        volume=config["volume"],
        prayer_bowl_mode=config["prayer_bowl_mode"],
        harmonic_strength=config["harmonic_strength"],
        modulation_depth=config["modulation_depth"],
    )
    _run_async(vajra_service.generate_prayer_bowl_audio(service_config))
    return {
        "status": "success",
        "message": "Audio generation completed",
        "config": dict(config),
        "audio_generated": True,
        "samples": len(vajra_service.current_audio_data) if vajra_service.current_audio_data is not None else 0,
    }


def _audio_play(hardware_level: int = 2) -> dict[str, Any]:
    """Play the generated audio in the background (mirrors the /play endpoint)."""
    from backend.core.services.vajra_service import vajra_service

    if vajra_service.current_audio_data is None:
        return {"status": "error", "message": "No audio data available. Please generate audio first."}
    audio_length = len(vajra_service.current_audio_data)
    stop_epoch_floor = vajra_service.current_playback_epoch()
    _spawn(
        vajra_service.broadcast_audio(
            vajra_service.current_audio_data,
            hardware_level,
            stop_epoch_floor=stop_epoch_floor,
        )
    )
    return {
        "status": "success",
        "message": "Audio playback started",
        "hardware_level": hardware_level,
        "audio_duration": audio_length / 44100,
        "audio_samples": audio_length,
    }


def _audio_presets() -> dict[str, Any]:
    from backend.app.api.v1.endpoints.audio import get_audio_presets

    return _dump(_run_async(get_audio_presets()))


def play_chakra_healing_audio(chakra_name: str, duration: float = 30.0) -> dict[str, Any]:
    """
    Generate and play a Tibetan prayer bowl tone tuned to a specific chakra.

    Use this when:
    - You detect negative RNG spikes and want to calm the space
    - The user requests a healing tone
    - You are leading a meditation session

    Args:
        chakra_name: Name of the chakra (e.g. "root", "sacral", "solar_plexus", "heart", "throat", "third_eye", "crown")
        duration: Duration of the audio in seconds, default 30.0

    Returns:
        {"status": "success", "message": "..."}
    """
    from backend.core.services.vajra_service import vajra_service

    _run_async(vajra_service.generate_chakra_audio(chakra_name, duration))
    gen_res = {
        "status": "success",
        "message": f"Chakra audio generation completed for {chakra_name}",
        "config": {"chakra_name": chakra_name, "duration": duration},
        "audio_generated": True,
        "samples": len(vajra_service.current_audio_data) if vajra_service.current_audio_data is not None else 0,
    }

    play_res = _audio_play()
    return {
        "status": "success",
        "message": f"Successfully playing {chakra_name} chakra healing audio.",
        "generation_details": gen_res,
        "playback_details": play_res,
    }


def set_audio_frequency(freq_hz: float, duration_s: float = 30.0) -> dict[str, Any]:
    """
    Directly tune the carrier frequency of the audio broadcast.

    Use this when:
    - You want to actively change the frequency based on RNG readings
    - Need specific Rife or Solfeggio frequencies

    Args:
        freq_hz: The frequency in Hz to play
        duration_s: Duration to play in seconds, default 30.0
    """
    config = {
        "frequency": freq_hz,
        "duration": duration_s,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": 0.3,
        "modulation_depth": 0.05,
    }
    gen_res = _audio_generate(config)
    if gen_res.get("status") == "success":
        play_res = _audio_play()
        return {"status": "success", "message": f"Successfully tuned frequency to {freq_hz} Hz.", "playback": play_res}
    return gen_res


def set_audio_modulation(harmonic_strength: float, modulation_depth: float, duration_s: float = 30.0) -> dict[str, Any]:
    """
    Change the timbre and modulation of the active broadcast.

    Use this when:
    - You want to increase or decrease the intensity/richness of the sound
    - Reacting to coherence changes

    Args:
        harmonic_strength: 0.0 to 1.0, richness of overtones
        modulation_depth: 0.0 to 1.0, depth of vibrato/tremolo
        duration_s: Duration in seconds, default 30.0
    """
    config = {
        "frequency": 432.0,  # Defaulting to a safe base frequency
        "duration": duration_s,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": harmonic_strength,
        "modulation_depth": modulation_depth,
    }
    gen_res = _audio_generate(config)
    if gen_res.get("status") == "success":
        play_res = _audio_play()
        return {
            "status": "success",
            "message": f"Successfully modulated audio (harmonics: {harmonic_strength}, depth: {modulation_depth}).",
            "playback": play_res,
        }
    return gen_res


def play_audio_preset(preset_name: str, duration_s: float = 30.0) -> dict[str, Any]:
    """
    Play a specific predefined audio preset.

    Use this when:
    - You want guaranteed safe configurations
    - You want to quickly shift states

    Available presets: 'om-frequency', 'heart-chakra', 'earth-resonance', 'pure-sine'

    Args:
        preset_name: Name of the preset to play
        duration_s: Duration in seconds, default 30.0
    """
    presets_res = _audio_presets()
    presets = presets_res.get("presets", {})
    if preset_name not in presets:
        return {"status": "error", "message": f"Preset '{preset_name}' not found."}

    config = dict(presets[preset_name])
    config["duration"] = duration_s

    gen_res = _audio_generate(config)
    if gen_res.get("status") == "success":
        play_res = _audio_play()
        return {"status": "success", "message": f"Successfully playing preset '{preset_name}'.", "playback": play_res}
    return gen_res


# ============================================================================
# BLESSING SLIDESHOW TOOLS
# ============================================================================


def create_blessing_slideshow(
    directory_path: str,
    mantra: str = "chenrezig",
    intentions: list[str] = None,
    repetitions_per_photo: int = 108,
    display_duration_ms: int = 2000,
    loop_mode: bool = True,
    rng_session_id: str | None = None,
    dedication: str = "May all beings benefit",
) -> dict[str, Any]:
    """
    Create a blessing slideshow session for a directory of photos.

    Use this when:
    - User wants to bless photos
    - Manual compassion practice
    - Need visual witness for radionics

    Args:
        directory_path: Absolute path to directory with photos
        mantra: Mantra to use (chenrezig, tara, medicine_buddha, etc.)
        intentions: List of intentions (love, healing, peace, etc.)
        repetitions_per_photo: Number of mantra repetitions per photo
        display_duration_ms: How long to display each photo (ms)
        loop_mode: Whether to loop back to start
        rng_session_id: Optional RNG session to link

    Returns:
        {"session_id": "blessing_slideshow_...", "total_photos": 50}
    """
    if intentions is None:
        intentions = ["love", "healing", "peace"]

    from backend.core.services.blessing_slideshow_service import (
        IntentionSet,
        IntentionType,
        MantraType,
        get_blessing_slideshow_service,
    )

    service = get_blessing_slideshow_service()
    intention_set = IntentionSet(
        primary_mantra=MantraType(mantra),
        intentions=[IntentionType(i) for i in intentions],
        repetitions_per_photo=repetitions_per_photo,
        dedication=dedication,
    )
    session_id = service.create_session(
        directory_path=directory_path,
        intention_set=intention_set,
        loop_mode=loop_mode,
        display_duration_ms=display_duration_ms,
        rng_session_id=rng_session_id,
    )
    session = service.sessions.get(session_id)
    total_photos = len(session.photos) if session else 0
    return {"session_id": session_id, "total_photos": total_photos}


def get_current_slide(session_id: str) -> dict[str, Any]:
    """
    Get current slide information including photo details and progress.

    Args:
        session_id: Slideshow session ID

    Returns:
        Complete current slide info including photo, session, overlay, progress
    """
    from backend.core.services.blessing_slideshow_service import get_blessing_slideshow_service

    service = get_blessing_slideshow_service()
    slide_info = service.get_current_slide(session_id)
    return slide_info if slide_info is not None else {}


def stop_slideshow(session_id: str) -> dict[str, Any]:
    """
    Stop slideshow and get final statistics.

    Args:
        session_id: Slideshow session ID

    Returns:
        Final statistics including photos blessed, mantras repeated
    """
    from backend.core.services.blessing_slideshow_service import get_blessing_slideshow_service

    service = get_blessing_slideshow_service()
    return service.stop_session(session_id)


# ============================================================================
# POPULATION MANAGEMENT TOOLS
# ============================================================================


def create_population(
    name: str = "Untitled Population",
    category: str = "custom",
    source_type: str = "manual",
    description: str = "",
    directory_path: str | None = None,
    mantra_preference: str = "chenrezig",
    intentions: list[str] = None,
    priority: int = 5,
    is_urgent: bool = False,
) -> dict[str, Any]:
    """
    Create a new target population for automated blessings.

    Use this when:
    - User wants to add a new population
    - Setting up automated rotation
    - Organizing blessing targets

    Args:
        name: Clear, descriptive name
        category: missing_persons, refugees, disaster_victims, etc.
        source_type: local_directory, manual, etc.
        description: Optional description
        directory_path: Required for local_directory source
        mantra_preference: Preferred mantra
        intentions: List of intentions
        priority: Priority 1-10 (higher = more important)
        is_urgent: Whether urgent

    Returns:
        Complete population object with ID
    """
    if intentions is None:
        intentions = ["love", "healing", "peace"]

    from backend.core.services.population_manager import PopulationCategory, SourceType, get_population_manager

    try:
        category = PopulationCategory(category) if isinstance(category, str) else category
    except ValueError:
        category = PopulationCategory.CUSTOM
    try:
        source = SourceType(source_type) if isinstance(source_type, str) else source_type
    except ValueError:
        source = SourceType.MANUAL

    pm = get_population_manager()
    pop = pm.create_population(
        name=name,
        description=description,
        category=category,
        source_type=source,
        directory_path=directory_path,
        mantra_preference=mantra_preference,
        intentions=intentions,
        priority=priority,
        is_urgent=is_urgent,
    )
    return pop.to_dict() if pop else {"status": "error", "message": f"Could not create population '{name}'."}


def list_populations(
    active_only: bool = False, category: str | None = None, urgent_only: bool = False
) -> list[dict[str, Any]]:
    """
    Get list of all populations with optional filtering.

    Args:
        active_only: Only return active populations
        category: Filter by specific category
        urgent_only: Only return urgent populations

    Returns:
        List of population objects
    """
    from backend.core.services.population_manager import get_population_manager

    pm = get_population_manager()
    pops = [p.to_dict() for p in pm.get_all_populations()]
    if active_only:
        pops = [p for p in pops if p.get("is_active")]
    if category:
        pops = [p for p in pops if p.get("category") == category]
    if urgent_only:
        pops = [p for p in pops if p.get("is_urgent")]
    # Dedup by name so a seeded "California" × N ledger cannot flood the
    # follow-up prompt (repetition makes free models stutter the name).
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pop in pops:
        name = str(pop.get("name") or pop.get("id") or "").strip()
        key = name.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "id": pop.get("id"),
                "name": name,
                "category": pop.get("category"),
                "is_active": pop.get("is_active"),
                "is_urgent": pop.get("is_urgent"),
                "mantra_preference": pop.get("mantra_preference"),
                "intentions": (pop.get("intentions") or [])[:4],
            }
        )
        if len(unique) >= 30:
            break
    return unique


def get_population_statistics() -> dict[str, Any]:
    """
    Get overall statistics across all populations.

    Returns:
        Statistics including totals, categories, blessings sent
    """
    from backend.core.services.population_manager import get_population_manager

    pm = get_population_manager()
    stats = pm.get_statistics()
    return {
        "total_populations": stats.get("total_populations", 0),
        "active_populations": stats.get("active_populations", 0),
        "total_blessings_sent": stats.get("total_blessings_sent", 0),
        "total_mantras_repeated": stats.get("total_mantras_repeated", 0),
    }


def get_system_status() -> dict[str, Any]:
    """
    Get a complete system status snapshot — populations, automation, RNG, world context.
    Use this when the user asks for 'statistics', 'status', 'system overview', or 'dashboard'.

    Returns all data in a single call so the LLM doesn't need multiple follow-up turns.
    """
    from backend.app.api.v1.endpoints.automation import get_automation_overview
    from backend.app.api.v1.endpoints.practices import all_practice_status
    from backend.app.api.v1.endpoints.ritual_engine import get_status as get_ritual_status_fn
    from backend.core.services.population_manager import get_population_manager
    from backend.core.services.rng_attunement_service import get_rng_service

    result: dict[str, Any] = {}

    try:
        stats = get_population_manager().get_statistics()
        result["population_stats"] = {
            "total_populations": stats.get("total_populations", 0),
            "active_populations": stats.get("active_populations", 0),
            "total_blessings_sent": stats.get("total_blessings_sent", 0),
            "total_mantras_repeated": stats.get("total_mantras_repeated", 0),
        }
    except Exception:
        result["population_stats"] = {"error": "unavailable"}

    try:
        rng_sessions = get_rng_service().get_all_sessions()
        result["rng_attunement"] = {"active": bool(rng_sessions), "sessions": len(rng_sessions)}
    except Exception:
        result["rng_attunement"] = {"error": "unavailable"}

    for name, call in [
        ("automation_status", get_automation_overview),
        ("ritual_status", get_ritual_status_fn),
        ("practice_status", all_practice_status),
    ]:
        try:
            result[name] = _dump(_run_async(call()))
        except Exception:
            result[name] = {"error": "unavailable"}

    pop_count = result.get("population_stats", {}).get("total_populations", len(result.get("population_stats", {})))
    result["summary"] = {
        "populations": pop_count,
        "automation": "active" if result.get("automation_status", {}).get("active") else "idle",
        "rng": "online" if result.get("rng_attunement", {}).get("active") else "offline",
        "rituals": result.get("ritual_status", {}).get("active_count", 0),
    }
    return result


def update_population(population_id: str, **updates) -> dict[str, Any]:
    """
    Update a population's settings.

    Args:
        population_id: Population ID
        **updates: Fields to update (priority, is_urgent, etc.)

    Returns:
        Updated population object
    """
    from backend.core.services.population_manager import get_population_manager

    pm = get_population_manager()
    pop = pm.update_population(population_id, **updates)
    if pop is None:
        return {"status": "error", "message": f"Population not found: {population_id}"}
    return pop.to_dict()


# ============================================================================
# AUTOMATION/SCHEDULER TOOLS
# ============================================================================


def start_automation(
    duration_per_population: int = 1800,
    transition_pause: int = 30,
    link_rng: bool = True,
    continuous_mode: bool = True,
    only_active: bool = True,
    min_priority: int = 1,
    mode: str = "round_robin",
    auto_dedicate: bool = True,
) -> dict[str, Any]:
    """
    Start automated 24/7 rotation through populations.

    Use this when:
    - User wants hands-off automatic operation
    - Setting up continuous compassion practice
    - Need fair distribution of blessing time

    Args:
        duration_per_population: Seconds to spend on each population
        transition_pause: Seconds between populations
        link_rng: Whether to create RNG session per population
        continuous_mode: Loop indefinitely if True
        only_active: Only include active populations
        min_priority: Minimum priority to include (1-10)

    Returns:
        {"session_id": "scheduler_...", "populations_in_queue": 15}
    """
    from backend.core.services.blessing_scheduler import SchedulerConfig, SchedulerMode, get_scheduler

    scheduler = get_scheduler()
    config = SchedulerConfig(
        mode=SchedulerMode(mode),
        duration_per_population=duration_per_population,
        transition_pause=transition_pause,
        link_rng=link_rng,
        auto_dedicate=auto_dedicate,
        continuous_mode=continuous_mode,
        only_active=only_active,
        min_priority=min_priority,
    )
    session_id = scheduler.start_automation(config=config)
    session = scheduler.sessions.get(session_id)
    queue_len = len(session.populations_queue) if session else 0
    return {"session_id": session_id, "populations_in_queue": queue_len}


def get_automation_status(session_id: str) -> dict[str, Any]:
    """
    Get current automation status (lightweight, for frequent polling).

    Use this for:
    - Real-time monitoring
    - UI updates every 5-10 seconds
    - Progress tracking

    Args:
        session_id: Automation session ID

    Returns:
        Current status including population, progress, elapsed time
    """
    from backend.core.services.blessing_scheduler import get_scheduler

    scheduler = get_scheduler()
    status_info = scheduler.get_current_status(session_id)
    return status_info if status_info is not None else {}


def get_automation_stats(session_id: str) -> dict[str, Any]:
    """
    Get complete automation statistics.

    Args:
        session_id: Automation session ID

    Returns:
        Complete statistics including history, totals, sessions completed
    """
    from backend.core.services.blessing_scheduler import get_scheduler

    return get_scheduler().get_session_stats(session_id)


def stop_automation(session_id: str) -> dict[str, Any]:
    """
    Stop automated rotation and get final statistics.

    Args:
        session_id: Automation session ID

    Returns:
        Final statistics for entire automation session
    """
    from backend.core.services.blessing_scheduler import get_scheduler

    return get_scheduler().stop_automation(session_id)


def pause_automation(session_id: str) -> dict[str, Any]:
    """
    Pause automated rotation (can be resumed later).

    Args:
        session_id: Automation session ID

    Returns:
        Confirmation message
    """
    from backend.core.services.blessing_scheduler import get_scheduler

    scheduler = get_scheduler()
    success = scheduler.pause_automation(session_id)
    return {
        "success": success,
        "message": "Automation paused successfully" if success else "Failed to pause automation",
    }


def resume_automation(session_id: str) -> dict[str, Any]:
    """
    Resume paused automation.

    Args:
        session_id: Automation session ID

    Returns:
        Confirmation message
    """
    from backend.core.services.blessing_scheduler import get_scheduler

    scheduler = get_scheduler()
    success = scheduler.resume_automation(session_id)
    return {
        "success": success,
        "message": "Automation resumed successfully" if success else "Failed to resume automation",
    }


# ============================================================================
# MAGICAL & ESOTERIC OPERATIONS TOOLS
# ============================================================================


async def forge_sigil(intention: str, kamea: str = "saturn") -> dict[str, Any]:
    """
    Forge a magical visual sigil from an intention statement.
    Generates the planetary Kamea SVG plus an optional AI image: inline
    (``ai_image``) for hosted providers, or a queued local render
    (``ai_image_render`` = ``{"operation_id", "status"}``) with ``IMAGE_PROVIDER=comfyui``.

    Args:
        intention: What the sigil is designed to manifest or bless
        kamea: Planetary Kamea grid to draw on (saturn, jupiter, mars)
    """
    from backend.core.services.sigil_service import sigil_service

    return _dump(await sigil_service.forge_sigil(intention, kamea))


# The divination tools return the raw cast: the Command Center widgets
# (RenderMessageWidgets.tsx) read ``cards`` / the hexagram / the shield chart
# straight off the tool result. ``question`` frames the draw for the model,
# which interprets it in its reply.


def cast_tarot_spread(count: int = 3, question: str = "") -> dict[str, Any]:
    """
    Draw Tarot cards from a 78-card deck with full elemental, Hebrew, and planetary correspondences.

    Args:
        count: Number of cards to draw (1, 3, or 10 for Celtic Cross)
        question: Question in focus for the Tarot oracle
    """
    from backend.core.services.divination_service import divination_service

    return {"cards": divination_service.draw_tarot(count)}


def cast_i_ching(question: str = "") -> dict[str, Any]:
    """
    Cast an I Ching hexagram using traditional yarrow-stalk probability weights.
    Returns primary/relating hexagrams, changing lines, and meaning interpretation.

    Args:
        question: The situation or focus query for the hexagram
    """
    from backend.core.services.divination_service import divination_service

    return divination_service.cast_i_ching()


def cast_geomancy(question: str = "") -> dict[str, Any]:
    """
    Cast a Geomantic Shield Chart containing 4 Mothers, 4 Daughters, Nieces, Witnesses, and the Judge.
    Projects figures into the 12 astrological houses.

    Args:
        question: Query/trend-check focus
    """
    from backend.core.services.divination_service import divination_service

    return divination_service.cast_geomancy()


def search_grimoire_correspondences(query: str = "") -> list[dict[str, Any]]:
    """
    Search the Grimoire library for herbs, stones, metals, planets, and rates that match.

    Args:
        query: Name of herb, crystal, element, or symptom/intention
    """
    # Import locally to avoid circular dependency
    from backend.core.services.grimoire_service import grimoire_service

    return grimoire_service.search(query)


async def get_planetary_hours_and_transits() -> dict[str, Any]:
    """
    Retrieve current planetary hour, day ruler, auspicious timing guidelines, and transits.
    """
    import datetime

    from backend.core.services.grimoire_service import grimoire_service
    from backend.core.services.vajra_service import vajra_service

    now = datetime.datetime.now()
    astro_data = await vajra_service._get_astrology_data()
    hour_data = grimoire_service.get_planetary_hours(now.hour, now.weekday())
    return {"astrology": astro_data, "planetary_hour": hour_data, "timestamp": time.time()}


# ============================================================================
# NARRATIVE GENERATION AND OUTLOOK TOOLS
# ============================================================================


def generate_single_outlook(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LNG,
    languages: list[str] = None,
    genre: str = "healing",
    custom_context: str | None = None,
    realm_id: str | None = None,
    population_ids: list[str] | None = None,
    character_ids: list[str] | None = None,
    excluded_forces: list[str] | None = None,
    include_dialogue: bool = False,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Generate a single-pass sutra-style blessing and narrative outlook.

    Args:
        lat: Target latitude
        lon: Target longitude
        languages: List of languages to weave (English, Sanskrit, Tibetan, etc.)
        genre: Genre of blessing (healing, victory, alchemist, fun_parable, dharani)
        custom_context: Optional user aspiration text
        realm_id: Setting or realm ID
        population_ids: Target populations receiving the blessing
        character_ids: Narrative characters present in the scene
        excluded_forces: Negative forces to exclude or pacify
        include_dialogue: Weave spoken dialogue between characters if True
    """
    if languages is None:
        languages = ["English"]
    from container import container
    from core.llm.defaults import NEMOTRON_FREE_MODEL_ID

    return container.outlook.generate_single(
        lat=lat,
        lon=lon,
        languages=languages,
        genre=genre,
        custom_context=custom_context,
        realm_id=realm_id,
        population_ids=population_ids,
        character_ids=character_ids,
        excluded_forces=excluded_forces,
        include_dialogue=include_dialogue,
        model=model or NEMOTRON_FREE_MODEL_ID,
    )


def generate_epic_outlook(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LNG,
    languages: list[str] = None,
    genre: str = "alchemist",
    stages: int = 9,
    custom_context: str | None = None,
    realm_id: str | None = None,
    population_ids: list[str] | None = None,
    character_ids: list[str] | None = None,
    excluded_forces: list[str] | None = None,
    include_dialogue: bool = False,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Generate a multi-stage epic narrative blessing cycle.

    Args:
        lat: Target latitude
        lon: Target longitude
        languages: Languages to weave
        genre: Genre of blessing
        stages: Number of stages to generate (default 9)
        custom_context: Optional custom context
        realm_id: Setting or realm ID
        population_ids: Beneficiary populations
        character_ids: Present characters
        excluded_forces: Excluded forces list
        include_dialogue: Include direct dialogue if True
    """
    if languages is None:
        languages = ["English"]
    from container import container
    from core.llm.defaults import NEMOTRON_FREE_MODEL_ID

    return container.outlook.generate_epic(
        lat=lat,
        lon=lon,
        languages=languages,
        genre=genre,
        stages=stages,
        custom_context=custom_context,
        realm_id=realm_id,
        population_ids=population_ids,
        character_ids=character_ids,
        excluded_forces=excluded_forces,
        include_dialogue=include_dialogue,
        model=model or NEMOTRON_FREE_MODEL_ID,
    )


def list_narrative_locations() -> list[dict[str, Any]]:
    """
    List all active locations and metaphysical realms.
    """
    from backend.app.api.v1.endpoints.outlook import list_locations

    return _dump(_run_async(list_locations()))


def create_narrative_location(
    name: str,
    description: str,
    location_type: str,
    source_type: str = "manual",
    is_metaphysical: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
    celestial_coordinates: str | None = None,
    dimension_frequency: float | None = None,
    realm_governor: str | None = None,
    astrological_anchor: str | None = None,
    elemental_affinity: str | None = None,
    priority: int = 5,
) -> dict[str, Any]:
    """
    Create a new location or metaphysical realm setting.

    Args:
        name: Name of location or realm
        description: Visionary description of setting
        location_type: earthly_sacred, metaphysical_realm, cosmic_anchor, historical_academy, custom
        source_type: manual, generated, mythology, geographic
        is_metaphysical: Set True for metaphysical dimensions with frequencies
        latitude: Latitude for earthly sacred sites
        longitude: Longitude for earthly sacred sites
        celestial_coordinates: Celestial/star coords (metaphysical only)
        dimension_frequency: Vibrational frequency in Hz (metaphysical only)
        realm_governor: Ruler or deity of the setting
        astrological_anchor: Astrological anchor lines
        elemental_affinity: Primary element (Fire, Water, etc.)
        priority: Priority weighting (1-10)
    """
    from backend.app.api.v1.endpoints.outlook import LocationCreate, create_location

    loc = _dump(
        _run_async(
            create_location(
                LocationCreate(
                    **{
                        "name": name,
                        "description": description,
                        "location_type": location_type,
                        "source_type": source_type,
                        "is_metaphysical": is_metaphysical,
                        "latitude": latitude,
                        "longitude": longitude,
                        "celestial_coordinates": celestial_coordinates,
                        "dimension_frequency": dimension_frequency,
                        "realm_governor": realm_governor,
                        "astrological_anchor": astrological_anchor,
                        "elemental_affinity": elemental_affinity,
                        "priority": priority,
                    }
                )
            )
        )
    )
    return loc


def list_narrative_characters() -> list[dict[str, Any]]:
    """
    List all active narrative characters and archetypes.
    """
    from backend.app.api.v1.endpoints.outlook import list_characters

    return _dump(_run_async(list_characters()))


def create_narrative_character(
    name: str,
    role: str,
    description: str,
    source_type: str = "manual",
    dialogue_style: str = "cryptic and profound",
    associated_realms: list[str] = None,
    mantra_preference: str | None = None,
    elemental_anchor: str = "space",
    priority: int = 5,
) -> dict[str, Any]:
    """
    Create a new narrative character archetype.

    Args:
        name: Character name
        role: master, student, alchemist, hero, deity, guardian, custom
        description: Archetypal description
        source_type: manual, generated, mythology, historical
        dialogue_style: Description of dialogue pattern
        associated_realms: Realm IDs frequented
        mantra_preference: Prefered mantra key
        elemental_anchor: earth, water, fire, air, space, aether
        priority: Priority weighting (1-10)
    """
    from backend.app.api.v1.endpoints.outlook import CharacterCreate, create_character

    return _dump(
        _run_async(
            create_character(
                CharacterCreate(
                    **{
                        "name": name,
                        "role": role,
                        "description": description,
                        "source_type": source_type,
                        "dialogue_style": dialogue_style,
                        "associated_realms": associated_realms or [],
                        "mantra_preference": mantra_preference,
                        "elemental_anchor": elemental_anchor,
                        "priority": priority,
                    }
                )
            )
        )
    )


def start_narrative_loop(
    interval_minutes: int = 15,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LNG,
    languages: list[str] = None,
    genre: str = "healing",
    custom_context: str | None = None,
    realm_id: str | None = None,
    population_ids: list[str] | None = None,
    character_ids: list[str] | None = None,
    excluded_forces: list[str] | None = None,
    include_dialogue: bool = False,
) -> dict[str, Any]:
    """
    Start the continuous background narrative transmission loop.

    Args:
        interval_minutes: Minutes between generation cycles (1-1440)
        lat: Target latitude
        lon: Target longitude
        languages: Languages to weave
        genre: Genre of narrative
        custom_context: User custom aspiration notes
        realm_id: Setting or realm ID
        population_ids: List of target population IDs
        character_ids: List of character IDs present
        excluded_forces: Negative forces to exclude
        include_dialogue: Include spoken dialogue between characters if True
    """
    if languages is None:
        languages = ["English"]
    from backend.app.api.v1.endpoints.outlook import BackgroundGenerationConfig, start_background_generation

    config = BackgroundGenerationConfig(
        interval_minutes=interval_minutes,
        loop_mode="sequential_delay",
        cycle_genres=False,
        cycle_intentions=False,
        lat=lat,
        lon=lon,
        languages=languages,
        genre=genre,
        custom_context=custom_context,
    )
    result = _dump(_run_async(start_background_generation(config)))
    if result.get("status") == "already_running":
        return {"status": "already_running", "stats": result.get("stats", {})}
    return {
        "status": "success",
        "message": f"Background generation started. Mode: sequential_delay. Every {interval_minutes} min.",
        "stats": result.get("stats", {}),
    }


def stop_narrative_loop() -> dict[str, Any]:
    """
    Stop the active background narrative transmission loop.
    """
    from backend.app.api.v1.endpoints.outlook import stop_background_generation

    return _dump(_run_async(stop_background_generation()))


def get_narrative_loop_status() -> dict[str, Any]:
    """
    Check active background narrative loop state, configuration, and last generated draft.
    """
    from backend.app.api.v1.endpoints.outlook import background_status

    status = _dump(_run_async(background_status()))
    return {
        "active": status["active"],
        "interval_minutes": status["config"].get("interval_minutes", 5),
        "config": {"loop_mode": status["config"].get("loop_mode", "sequential_delay")},
        "stats": status.get("stats", {}),
        "last_generated": status.get("stats", {}).get("last_generated_at"),
    }


# ============================================================================
# 88 BUDDHAS & SAKA DAWA TOOLS
# ============================================================================


def get_random_buddha(category: str | None = None) -> dict[str, Any]:
    """Get a random Buddha from the 88-Buddha collection with contemplation narrative."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    svc = get_eighty_eight_buddhas()
    b = svc.random_buddha(category=category)
    narrative = svc.generate_buddha_narrative(b.name_chinese, depth="contemplation")
    return {
        "buddha": {
            "name_chinese": b.name_chinese,
            "name_pinyin": b.name_pinyin,
            "name_sanskrit": b.name_sanskrit,
            "category": b.category,
            "meaning": b.meaning,
            "realm": b.realm,
            "light": b.light,
        },
        "narrative": narrative.get("narrative", ""),
    }


def generate_buddha_narrative(buddha_name: str = "", depth: str = "contemplation") -> dict[str, Any]:
    """Generate a sacred narrative about a specific Buddha."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    return get_eighty_eight_buddhas().generate_buddha_narrative(buddha_name, depth=depth)


def get_88_buddhas_liturgy() -> dict[str, Any]:
    """Get the full 88-Buddha confession liturgy."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    return get_eighty_eight_buddhas().get_confession_sequence()


def recite_buddha_name(
    buddha_name: str = "",
    voice: str | None = None,
    role: str = "buddhist_chant",
    project_id: str | None = None,
) -> dict[str, Any]:
    """Recite a single Buddha name through the unified TTS provider.

    On a running event loop the audio renders in the background and
    ``audio_path`` is ``None``; otherwise the call waits for the file.
    """
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    svc = get_eighty_eight_buddhas()
    b = svc.get_buddha_by_name(buddha_name)
    if not b:
        return {"error": f"Buddha not found: {buddha_name}"}
    text = f"南無{b.name_chinese}" if not b.name_chinese.startswith("南無") else b.name_chinese
    try:
        from core.tts_provider import get_tts_provider

        provider = get_tts_provider()
        if project_id is not None:
            provider.config.project_id = project_id
        edge_v, qwen_s = provider._resolve_voice(voice, role)
        backend_id = provider.active_backend.value

        async def _do_speak() -> str | None:
            return await provider.speak(text=text, voice=voice, rate="-30%", role=role)

        try:
            running = asyncio.get_event_loop()
            if running.is_running():
                # Schedule the coroutine and return the metadata now; the
                # audio renders in the background.
                asyncio.ensure_future(_do_speak())
                path = None
            else:
                path = asyncio.run(_do_speak())
        except RuntimeError:
            path = asyncio.run(_do_speak())

        return {
            "buddha": b.name_chinese,
            "pinyin": b.name_pinyin,
            "text": text,
            "audio_path": path,
            "backend": backend_id,
            "speaker": qwen_s if backend_id == "qwen" else edge_v,
            "role": role,
            "message": f"Recited {b.name_chinese} ({b.name_pinyin}) via {backend_id}.",
        }
    except Exception as e:
        return {
            "buddha": b.name_chinese,
            "pinyin": b.name_pinyin,
            "text": text,
            "error": str(e),
            "message": f"Could not play recitation of {b.name_chinese}: {e}",
        }


def start_buddha_recitation(
    intention: str = "愿一切众生离苦得乐",
    interval_seconds: float = 3.0,
    mala_cycles: int | None = None,
    voice: str = "zh-CN-YunxiNeural",
    role: str = "buddhist_chant",
    project_id: str | None = None,
) -> dict[str, Any]:
    """Start the continuous 88-Buddha recitation loop (on the running loop when there is one)."""
    from core.buddha_recitation_loop import get_recitation_loop

    loop = get_recitation_loop()
    if loop.state.running:
        return {"status": "already_running", "message": "Recitation loop already active."}

    def _start() -> Any:
        return loop.start(
            intention=intention,
            interval_seconds=interval_seconds,
            mala_cycles=mala_cycles,
            voice=voice,
            role=role,
            project_id=project_id,
        )

    try:
        running_loop = asyncio.get_event_loop()
        if running_loop.is_running():
            running_loop.create_task(_start())
        else:
            asyncio.run(_start())
    except RuntimeError:
        asyncio.run(_start())
    return loop.get_status()


def stop_buddha_recitation() -> dict[str, Any]:
    """Stop the active Buddha recitation loop.

    The loop's task lives on the event loop that started it, so on a running
    loop the stop is scheduled there (the returned status already reads
    stopped); without one it completes before returning.
    """
    from core.buddha_recitation_loop import get_recitation_loop

    loop = get_recitation_loop()
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(loop.stop())
        return loop.get_status()
    loop.state.running = False
    running_loop.create_task(loop.stop())
    return loop.get_status()


def get_buddha_recitation_status() -> dict[str, Any]:
    """Get current recitation loop status."""
    from core.buddha_recitation_loop import get_recitation_loop

    return get_recitation_loop().get_status()


def check_saka_dawa() -> dict[str, Any]:
    """Check Saka Dawa holy month status (Losar-anchored 4th Tibetan month) with a suggested action."""
    from core.auspicious_timing import check_saka_dawa as _check_saka_dawa

    status = _check_saka_dawa()
    if status.get("is_duchen"):
        suggested = (
            "Perform the Saka Dawa Blessing now — Duchen, the full moon "
            "of the 4th Tibetan month, multiplies merit 100,000×."
        )
    elif status.get("is_saka_dawa"):
        suggested = (
            f"Perform the Saka Dawa Blessing — the 4th Tibetan month (from Losar {status.get('losar')}) is active."
        )
    else:
        suggested = (
            "Prepare for Saka Dawa. Next Duchen is "
            f"{status.get('saka_dawa_duchen')} "
            f"({status.get('days_until_duchen')} days)."
        )
    return {**status, "suggested_action": suggested}


def run_working(
    intention: str = "",
    target: str = "all beings",
    broadcast: bool = True,
    duration_minutes: int = 5,
    deity: str | None = None,
    location: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Seal one working: rates, Saka Dawa stamp, optional broadcast, optional deity.

    A deity the iconography data does not know is dropped (and said so in
    ``deity_note``) rather than failing the whole working. ``location`` is
    normally omitted so the user's home location applies; one that is not a
    valid ``{latitude, longitude}`` is dropped the same way (``location_note``).
    """
    from core import iconography
    from core.working import run_working as _run_working

    note = None
    if deity and deity.strip() and iconography.resolve(deity) is None:
        note = f"unknown deity {deity!r} was not applied; known: {', '.join(d['id'] for d in iconography.deities())}"
        deity = None
    location_note = None
    if location is not None:
        from core.home_location import normalize_location

        try:
            if not isinstance(location, dict):
                raise ValueError("location must be an object with latitude and longitude")
            location = normalize_location(location)
        except ValueError as exc:
            location_note = f"location was not applied ({exc}); the home location is used instead"
            location = None
    folio = _run_working(
        intention=intention,
        target=target,
        broadcast=broadcast,
        duration_minutes=duration_minutes,
        deity=deity,
        location=location,
    )
    if note:
        folio["deity_note"] = note
    if location_note:
        folio["location_note"] = location_note
    return folio


async def forge_witness(working_id: str = "") -> dict[str, Any]:
    """Witness image for an existing working folio, preferring the local render engine.

    Same policy as ``POST /operator/workings/{id}/witness``
    (:func:`core.working.forge_witness`): a queued local render returns its
    ``operation_id``; with the engine unreachable the hosted image is attached
    and ``witness_fallback`` says so.
    """
    from core.working import forge_witness_for_tool

    return await forge_witness_for_tool(str(working_id))


def check_auspicious_timing(genre: str = "healing") -> dict[str, Any]:
    """Check auspicious timing for a ritual genre."""
    from core.auspicious_timing import check_auspicious_window

    return check_auspicious_window(genre).to_dict()


# ============================================================================
# RITUAL ENGINE TOOLS — autonomous LLM agent control over the ritual engine
# ============================================================================


def get_ritual_status() -> dict[str, Any]:
    """Get the current state, history, and merit of the autonomous ritual engine.

    Use this when:
    - The user asks about recent rituals or accumulated merit
    - You need to decide whether to start/stop the engine
    - You want to know what the engine has been doing

    Returns:
        {
            "state": "running" | "stopped" | "executing" | "paused",
            "is_running": bool,
            "rituals_today": int,
            "rituals_this_hour": int,
            "total_merit_today": float,
            "recent_history": [{"id", "practice_name", "genre", "merit_multiplier", "narrative_length", "completed_at"}, ...],
            "current_ritual": {...} | None,
        }
    """
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    return {
        "status": engine.status,
        "history": engine.get_history(20),
        "merit": engine.get_merit_stats(),
    }


def start_ritual_engine(min_timing_quality: str = "challenging") -> dict[str, Any]:
    """Start the autonomous ritual engine.

    The engine runs on a 60-second loop, selecting and executing rituals
    based on the configured minimum timing quality and current auspicious
    windows. Practice selection uses the PracticeSelector to score by
    genre, timing, merit, and recency diversity.

    Use this when:
    - The user asks to start a continuous blessing practice
    - You detect favorable Saka Dawa or other high-merit windows
    - You want to maintain ongoing intentional practice

    Args:
        min_timing_quality: Minimum timing quality to execute — one of
            "excellent" (4), "good" (3), "challenging" (2), "transmutative" (1).
            Default "challenging" — execute unless the hour is fully blocked.

    Returns:
        {"status": "started" | "already_running", "state": "running"}
    """
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    engine.update_config(min_timing_quality=min_timing_quality)
    _run_async(engine.start())
    return {"status": "started", "state": engine.state.value}


def stop_ritual_engine() -> dict[str, Any]:
    """Stop the autonomous ritual engine.

    Idempotent — safe to call when the engine is already stopped.

    Use this when:
    - The user asks to pause or stop automatic practice
    - You're transitioning to a manual ritual mode
    - The engine has accumulated enough merit and the user wants a break
    """
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    _run_async(engine.stop())
    return {"status": "stopped", "state": engine.state.value}


def trigger_ritual() -> dict[str, Any]:
    """Manually trigger one ritual execution on the autonomous engine.

    Use this when:
    - The user asks for an immediate blessing
    - You want to fire a one-off practice without starting the full loop
    - You're testing or demonstrating the engine

    Returns:
        {"status": "executed" | "no_practice_selected",
         "ritual": {RitualRecord fields} | None}
    """
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    record = _run_async(engine.trigger_now())
    if record is None:
        return {"status": "no_suitable_practice", "message": "No practice scored above threshold"}
    return {"status": "executed", "ritual": record.to_dict()}


def list_practices() -> dict[str, Any]:
    """List all available ritual practices with their genre, merit, and mantras.

    Use this when:
    - The user asks what practices are available
    - You need to recommend a specific practice for a situation
    - You want to see the merit multipliers for scoring decisions

    Returns:
        {"practices": [{"id", "name", "genre", "merit_multiplier",
                        "preferred_planetary_hours", "duration_sec", "mantra"}, ...]}
    """
    from core.practices.practice import Practice

    return {"practices": [p.__dict__ for p in Practice.get_default_practices()]}


def get_ritual_schedule(hours: int = 24) -> dict[str, Any]:
    """Get the next N hours of predicted favorable ritual timing.

    Use this when:
    - You want to schedule a specific ritual for an upcoming favorable hour
    - The user asks "when's the next good time for X?"
    - You're planning a sequence of practices

    Args:
        hours: How many hours to look ahead (default 24)

    Returns:
        {"schedule": [{"datetime", "planetary_hour", "favorable_genres", "quality"}, ...]}
    """
    from core.ritual_engine import get_ritual_engine

    engine = get_ritual_engine()
    return {"schedule": engine.status.get("schedule", [])}


def generate_character() -> dict[str, Any]:
    """Generate an RNG-seeded character (no LLM call)."""
    from core.character_generator import CharacterGenerator

    return CharacterGenerator().generate(use_llm=False).to_dict()


def start_character_journey(*, container: Any = None) -> dict[str, Any]:
    """Start a character journey arc on the container's operator."""
    return _operator_call(container, "start_character_journey")


def advance_journey(*, container: Any = None) -> dict[str, Any]:
    """Advance character journey by one stage."""
    return _operator_call(container, "advance_journey")


def get_journey_status(*, container: Any = None) -> dict[str, Any]:
    """Get current journey status."""
    return _operator_call(container, "get_journey_status")


def run_full_journey(*, container: Any = None) -> dict[str, Any]:
    """Run full 6-stage journey."""
    return _operator_call(container, "run_full_journey")


# ============================================================================
# SACRED ASTRONOMY, DHARANI, CRISIS & LIVING RITUAL EXPANSION
# ============================================================================


def get_celestial_night_sky(
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LNG,
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Get celestial night sky coordinates for observer.

    Computes Altitude/Azimuth for 10 solar system bodies (Sun, Moon,
    Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto) and 10 Vedic
    nakshatra fixed stars (Sirius/Mrigashirsha, Vega/Abhijit, Arcturus/Swati,
    Spica/Chitra, Aldebaran/Rohini, Antares/Jyeshtha, Betelgeuse/Ardra,
    Polaris/Dhruva, Regulus/Magha, Pleiades/Krittika), along with Moon phase,
    illumination percentage, and Local Sidereal Time (LST).

    The bodies' Altitude/Azimuth are topocentric: corrected for the diurnal parallax
    of an observer at sea level (the Moon sits up to ~1 degree lower than its
    geocentric place); altitudes are geometric, with no refraction. The result's
    ``position_frame`` names that frame; right_ascension/declination stay geocentric.
    """
    from datetime import datetime, timezone

    from core.celestial_sky import calculate_night_sky

    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp is not None else None
    return calculate_night_sky(latitude=latitude, longitude=longitude, dt=dt)


def get_dharani_text(dharani_id_or_name: str = "") -> dict[str, Any]:
    """Retrieve unabbreviated sacred Dhāraṇī or mantra text from the canonical library.

    Loads complete canonical text (Sanskrit IAST, Chinese characters, English meaning,
    historical context, and recitation instructions) from the sacred dhāraṇī library.
    Supports Great Compassion Mantra (84 phrases), Śūraṅgama Mantra (all 5 assemblies),
    Sitātapatrā (White Umbrella), Mahāpratisarā, Cundi (with full 4-line praise), etc.
    If 'list' or empty query is supplied, returns a directory of available dhāraṇīs.
    """
    import json
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    dharani_path = base_dir / "knowledge" / "dharanis.json"
    if not dharani_path.exists():
        return {"status": "error", "message": "knowledge/dharanis.json not found"}

    try:
        data = json.loads(dharani_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse dharanis.json: {e}"}

    query = (dharani_id_or_name or "").strip().lower()

    if not query or query in ("list", "all", "help", "dir"):
        summary_list = [
            {
                "id": d.get("id"),
                "name": d.get("name"),
                "name_chinese": d.get("name_chinese", ""),
                "deity": d.get("deity", ""),
                "purpose": d.get("purpose", ""),
                "frequency_hz": d.get("frequency_hz", 528),
            }
            for d in data
        ]
        return {
            "status": "list",
            "total": len(data),
            "available_dharanis": summary_list,
            "message": "Specify a dhāraṇī id or name to retrieve the full unabbreviated text.",
        }

    # Match exact ID first
    match = next((d for d in data if d.get("id", "").lower() == query), None)

    # Match substring on id, name, name_chinese, deity, purpose
    if not match:
        for d in data:
            if (
                query in d.get("id", "").lower()
                or query in d.get("name", "").lower()
                or query in d.get("name_chinese", "").lower()
                or query in d.get("deity", "").lower()
                or query in d.get("purpose", "").lower()
            ):
                match = d
                break

    if not match:
        return {
            "status": "not_found",
            "query": dharani_id_or_name,
            "message": f"Dhāraṇī '{dharani_id_or_name}' not found. Available IDs: {[d.get('id') for d in data]}",
        }

    return {
        "status": "found",
        "dharani": match,
    }


def get_auspicious_timing_details(
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LNG,
) -> dict[str, Any]:
    """Get full 24-hour Auspicious Timing Wheel details for ritual scheduling.

    Includes 24 planetary hour slices, current planetary ruler, daytime/nighttime state,
    lunar phase and tithi, nakshatra, Saka Dawa multiplier and status, and green windows
    for ritual genres (healing, victory, wisdom, purification, compassion, prosperity, protection).
    """
    from core.auspicious_timing import AuspiciousTiming

    engine = AuspiciousTiming()
    return engine.get_timing_wheel_data(lat=latitude, lon=longitude)


def get_active_world_crises() -> dict[str, Any]:
    """Retrieve active global crises, natural disasters, and humanitarian events.

    Fetches real-time alert data from GDACS (earthquakes, floods, cyclones, tsunamis)
    and humanitarian situations from ReliefWeb. Provides geographic coordinates,
    severity ratings, and recommended compassionate healing intention focal points.
    """
    from core.internet_context import compile_world_context

    ctx = compile_world_context(include_disasters=True, include_headlines=True, include_astrology=False)
    crises = []
    for ev in ctx.events:
        crises.append(
            {
                "title": ev.title,
                "description": ev.description,
                "location": ev.location or ev.country or "Global",
                "country": ev.country,
                "latitude": ev.lat,
                "longitude": ev.lon,
                "event_type": ev.event_type,
                "severity": ev.severity,
                "source": ev.source,
                "date": ev.date,
                "url": ev.url,
            }
        )
    return {
        "status": "success",
        "total_crises": len(crises),
        "disaster_count": sum(1 for c in crises if c["event_type"] == "disaster"),
        "humanitarian_count": sum(1 for c in crises if c["event_type"] == "humanitarian"),
        "crises": crises,
        "summary": ctx.summary,
    }


def trigger_living_ritual_broadcast(
    intention: str = "May all beings be free from suffering",
    target: str = "all beings",
    ritual_type: str = "healing",
    duration_minutes: int = 5,
    recite_with_tts: bool = False,
) -> dict[str, Any]:
    """Trigger a living ritual broadcast combining sacred text, Solfeggio tones, and dedication.

    Generates a full 6-section sacred ritual (Invocation, Sacred Prayer, Dharma Teaching,
    Divination/Correspondence, Hero Journey Narrative, and Dedication of Merit),
    initiates crystal bowl Solfeggio carrier broadcast, optionally cues TTS recitation,
    and archives the ritual to outlook_narratives.
    """
    from backend.app.api.v1.endpoints.radionics import RitualBroadcastRequest, ritual_broadcast

    req = RitualBroadcastRequest(
        intention=intention,
        target=target,
        ritual_type=ritual_type,
        duration_minutes=duration_minutes,
        recite_with_tts=recite_with_tts,
    )
    res = _run_async(ritual_broadcast(req))
    return _dump(res)


# ============================================================================
# IMAGE GENERATION (modular service — see backend/core/services/image_generation_service.py)
# ============================================================================


def generate_image(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    size: str = "1024x1024",
    quality: str = "standard",
    aspect_ratio: str | None = None,
    subject_reference: str | None = None,
) -> dict[str, Any]:
    """
    Generate an image from a text prompt via OpenRouter or MiniMax.

    Cost-controlled (default daily cap $0.50), cached (1 hour), and rate-limited
    (max 10/hour). Returns a base64 data URL the chat UI can render inline.

    Use this when:
    - The user asks for a sacred illustration, mandala, deity portrait, or visual
    - You want to depict a generated blessing narrative
    - The user invokes "draw", "paint", "show me", or "create an image of"

    Args:
        prompt: Image description (max 1000 tokens; 30-60 words is ideal).
        provider: "openrouter" (default) or "minimax". None uses config default.
        model: Model slug. None uses config default
            (e.g. "google/gemini-3.1-flash-lite-image", "image-01").
        size: OpenRouter size: "1024x1024" (default), "1792x1024", "1024x1792".
        quality: OpenRouter "standard" or "hd". Ignored by MiniMax.
        aspect_ratio: MiniMax-only override (e.g. "1:1", "16:9", "4:3").
        subject_reference: MiniMax-only image URL for image-to-image consistency.

    Returns:
        {
            "image_data_url": "data:image/png;base64,...",
            "model": "google/gemini-3.1-flash-lite-image",
            "cost_usd": 0.008,
            "provider_used": "openrouter",
            "cached": false,
            "revised_prompt": "...",
            "prompt_tokens": 42
        }

    Raises:
        RuntimeError: If image generation is disabled, daily cap reached,
            rate-limited, or the provider call fails.
        ValueError: If prompt exceeds the configured token budget.

    The prompt is passed through ``core.image_prompts.finalize_image_prompt``:
    degrees, percentages, dates, house numbers and other digits are stripped
    and a "no lettering, no numerals" suffix is added, because image models
    paint such values as garbled text. Real values belong in the UI caption.
    """
    from backend.app.api.v1.endpoints.image_generation import get_service
    from backend.core.services.image_generation_service import ImageGenerationService
    from core.image_prompts import finalize_image_prompt

    prompt = finalize_image_prompt(prompt)
    service: ImageGenerationService = get_service()

    try:
        asyncio.get_running_loop()
        in_loop = True
    except RuntimeError:
        in_loop = False

    async def _call() -> dict[str, Any]:
        return await service.generate(
            prompt=prompt,
            provider=provider,
            model=model,
            size=size,
            quality=quality,
            n=1,
            aspect_ratio=aspect_ratio,
            subject_reference=subject_reference,
        )

    if in_loop:
        return generate_image_for_tool(
            prompt=prompt,
            provider=provider,
            model=model,
            size=size,
            quality=quality,
            aspect_ratio=aspect_ratio,
            subject_reference=subject_reference,
        )

    return asyncio.run(_call())


async def generate_image_for_tool(
    prompt: str = "",
    provider: str | None = None,
    model: str | None = None,
    size: str = "1024x1024",
    quality: str = "standard",
    aspect_ratio: str | None = None,
    subject_reference: str | None = None,
) -> dict[str, Any]:
    """The ``generate_image`` tool handler: honors the service's ``model_lock``."""
    from backend.app.api.v1.endpoints.image_generation import get_service
    from core.image_prompts import finalize_image_prompt

    # Backstop for LLM-written prompts: no numerals, degrees, dates or lettering reach the model.
    prompt = finalize_image_prompt(prompt)
    service = get_service()
    cfg = service.config

    model_lock = cfg.get("model_lock", True)
    if model_lock:
        return await service.generate(
            prompt=prompt,
            provider=None,
            model=None,
            size=size,
            quality=quality,
            n=1,
            aspect_ratio=None,
            subject_reference=subject_reference,
        )

    return await service.generate(
        prompt=prompt,
        provider=provider,
        model=model,
        size=size,
        quality=quality,
        n=1,
        aspect_ratio=aspect_ratio,
        subject_reference=subject_reference,
    )


# ============================================================================
# RADIONICS / BROADCASTING / RATE ENGINE
# ----------------------------------------------------------------------------
# Container-backed tools take ``container`` (the operator passes its own; the
# chat path uses the global one).
# ============================================================================


def broadcast_healing(
    target_name: str = "",
    duration_minutes: int = 10,
    frequency_hz: float = 528.0,
    intensity: float = 0.8,
    *,
    container: Any = None,
) -> dict[str, Any]:
    """Broadcast healing scalar waves and radionics rates to a target."""
    return _resolve_container(container).radionics.broadcast_healing(
        target_name=target_name,
        duration_minutes=duration_minutes,
        frequency_hz=frequency_hz,
        intensity=intensity,
    )


def broadcast_liberation(
    event_name: str = "", souls_count: int = 1000, duration_minutes: int = 108, *, container: Any = None
) -> dict[str, Any]:
    """Broadcast the liberation protocol for an event or population."""
    return _resolve_container(container).radionics.broadcast_liberation(
        event_name=event_name,
        souls_count=souls_count,
        duration_minutes=duration_minutes,
    )


def prepare_crystal_broadcast(intention: str = "", duration_minutes: int = 10, *, container: Any = None) -> Any:
    """Analyze an intention and prepare the crystal bowl broadcast configuration."""
    return _operator_call(
        container, "prepare_crystal_broadcast", intention=intention, duration_minutes=duration_minutes
    )


def get_available_intentions(*, container: Any = None) -> dict[str, Any]:
    """List the radionics intention types."""
    return {"intentions": _resolve_container(container).radionics.get_available_intentions()}


def get_sacred_frequencies(*, container: Any = None) -> dict[str, Any]:
    """List the sacred frequencies (Solfeggio, planetary, ...)."""
    return _resolve_container(container).radionics.get_sacred_frequencies()


def text_to_rate(text: str = "", num_dials: int = 3) -> dict[str, Any]:
    """Derive a radionics rate from text (deterministic signature)."""
    from core.radionics_engine import SignatureCalculator

    rate = SignatureCalculator().text_to_rate(text=text, num_dials=num_dials, algorithm="mixed")
    return rate.to_dict()


def measure_general_vitality(subject: str = "", samples: int = 10) -> dict[str, Any]:
    """A general-vitality DRAW for a subject.

    The tool name is kept for registry stability; this is a GV *draw* (RNG as
    stick pad), so the output says so field by field.
    """
    from core.radionics_engine import GV_DRAW_NOTE, GeneralVitalityMeter

    meter = GeneralVitalityMeter()
    stats = meter.measure_multiple(count=samples, subject=subject)
    return {
        "subject": subject,
        "method": "draw",
        "gv_mean": stats["mean"],
        "gv_median": stats["median"],
        "gv_std": stats["std"],
        "gv_min": stats["min"],
        "gv_max": stats["max"],
        "interpretation": meter.interpret_gv(stats["mean"]),
        "samples": samples,
        "note": GV_DRAW_NOTE,
        "provenance": {
            "gv_mean": "draw",
            "gv_median": "draw",
            "gv_std": "draw",
            "gv_min": "draw",
            "gv_max": "draw",
            "interpretation": "draw",
        },
    }


def find_balancing_rates(subject: str = "", num_rates: int = 5) -> dict[str, Any]:
    """Balancing rates for a subject: its signature inverted and offset by a draw."""
    from core.radionics_engine import RadionicsAnalyzer

    rates = RadionicsAnalyzer().find_balancing_rates(subject=subject, num_rates=num_rates)
    return {
        "subject": subject,
        "method": "draw",
        "balancing_rates": [r.to_dict() for r in rates],
        "note": (
            "Dial values are the subject's signature inverted and offset by a draw; "
            "each potency is drawn (stick-pad analog), not measured."
        ),
        "provenance": {"balancing_rates": "draw"},
    }


def search_knowledge(query: str = "", top_k: int = 5, category: str | None = None) -> dict[str, Any]:
    """Search the local knowledge index."""
    from core.knowledge_index import search_knowledge as kb_search

    results = kb_search(query=query, top_k=top_k, category=category)
    return {"query": query, "results": results, "count": len(results)}


def search_rate_database(query: str = "", category: str | None = None) -> dict[str, Any]:
    """Search the radionics rate database."""
    from core.context_builder import search_rates

    results = search_rates(query=query, category=category)
    return {"query": query, "results": results, "count": len(results)}


def generate_scalar_waves(
    method: str = "hybrid", count: int = 10000, intensity: float = 1.0, *, container: Any = None
) -> dict[str, Any]:
    """Generate scalar waves via the container's scalar-wave service."""
    return _resolve_container(container).scalar_waves.generate(method=method, count=count, intensity=intensity)


def get_rng_summary(session_id: str) -> dict[str, Any]:
    """Summary of an RNG attunement session."""
    from backend.core.services.rng_attunement_service import get_rng_service

    return get_rng_service().get_session_summary(session_id)


# ============================================================================
# ANATOMY / HEALING / ASTROLOGY / AUDIO / BLESSINGS / LLM CONTENT
# ============================================================================


def get_chakra_info(*, container: Any = None) -> dict[str, Any]:
    return {"chakras": _resolve_container(container).anatomy.get_chakra_info()}


def get_meridian_info(*, container: Any = None) -> dict[str, Any]:
    return {"meridians": _resolve_container(container).anatomy.get_meridian_info()}


def create_healing_session(
    target_name: str = "",
    modalities: list[str] | None = None,
    duration_minutes: int = 60,
    intention: str = "complete healing",
    *,
    container: Any = None,
) -> dict[str, Any]:
    return _resolve_container(container).healing.create_healing_session(
        target_name=target_name,
        modalities=modalities,
        duration_minutes=duration_minutes,
        intention=intention,
    )


def chakra_balancing_protocol(
    target_name: str = "", chakras: list[str] | None = None, *, container: Any = None
) -> dict[str, Any]:
    return _resolve_container(container).healing.chakra_balancing_protocol(target_name=target_name, chakras=chakras)


def get_healing_modalities(*, container: Any = None) -> dict[str, Any]:
    return {"modalities": _resolve_container(container).healing.get_available_modalities()}


def get_planetary_positions(*, container: Any = None) -> dict[str, Any]:
    svc = _resolve_container(container).astrology
    if svc is None:
        return {"error": "Astrology service not available"}
    return svc.get_planetary_positions()


def calculate_natal_chart(
    birth_date: str,
    latitude: float,
    longitude: float,
    name: str | None = None,
    *,
    container: Any = None,
) -> dict[str, Any]:
    from datetime import datetime

    svc = _resolve_container(container).astrology
    if svc is None:
        return {"error": "Astrology service not available"}
    return svc.calculate_natal_chart(
        name=name,
        birth_date=datetime.fromisoformat(birth_date),
        latitude=latitude,
        longitude=longitude,
    )


def generate_audio(
    frequency_hz: float = 136.1,
    duration_seconds: float = 10,
    mode: str = "prayer_bowl",
    *,
    container: Any = None,
) -> dict[str, Any]:
    """Generate a tone on the LLM-tool audio path (``modules/audio.py``, ADR 001)."""
    return _resolve_container(container).audio.generate_tone(
        frequency=frequency_hz, duration=duration_seconds, mode=mode
    )


def generate_blessing(
    target_name: str = "",
    intention: str = "peace and happiness",
    tradition: str = "universal",
    *,
    container: Any = None,
) -> dict[str, Any]:
    return _resolve_container(container).blessings.generate_blessing(
        target_name=target_name, intention=intention, tradition=tradition
    )


def get_blessing_traditions(*, container: Any = None) -> dict[str, Any]:
    return {"traditions": _resolve_container(container).blessings.get_available_traditions()}


def generate_prayer(intention: str = "healing", tradition: str = "universal", *, container: Any = None) -> Any:
    return _resolve_container(container).llm.generate_prayer(intention=intention, tradition=tradition)


def generate_teaching(
    topic: str = "compassion",
    length: str = "short",
    tradition: str = "buddhist",
    *,
    container: Any = None,
) -> Any:
    return _resolve_container(container).llm.generate_teaching(topic=topic, tradition=tradition, depth=length)


def generate_meditation_script(
    meditation_type: str = "loving-kindness",
    duration_minutes: int = 20,
    experience_level: str = "beginner",
    *,
    container: Any = None,
) -> Any:
    return _resolve_container(container).llm.generate_meditation_script(
        meditation_type=meditation_type,
        duration_minutes=duration_minutes,
        experience_level=experience_level,
    )


def speak_text(text: str, voice: str | None = None, role: str = "dharma_teaching") -> dict[str, Any]:
    """
    Speak text through the TTS engine (Kokoro/Sherpa/Edge multilingual router).

    Use this AFTER generating a blessing, prayer, or teaching to give it voice.
    Generates audio and returns a path that can be played back.

    Args:
        text: The text to speak (will be spoken as-is)
        voice: Optional voice override
        role: Ritual role for voice selection

    Returns:
        Dict with status, audio_path, and text_length
    """
    import tempfile

    from core.tts_provider import get_tts_provider

    try:
        provider = get_tts_provider()
        result = _run_async(provider.speak_stream(text=text[:5000], voice=voice, role=role))
        if result is None:
            return {"status": "error", "error": "TTS generation failed — check backend availability"}
        audio_bytes, mime_type, backend = result
        audio_dir = os.path.join(tempfile.gettempdir(), "vajra_tts")
        os.makedirs(audio_dir, exist_ok=True)
        filename = f"tts_{int(time.time())}.{'mp3' if 'mpeg' in mime_type else 'wav'}"
        filepath = os.path.join(audio_dir, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        return {
            "status": "success",
            "audio_path": filepath,
            "backend_used": backend,
            "text_length": len(text),
            "size_bytes": len(audio_bytes),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================================================
# WEB / WORLD CONTEXT / TIMING
# ============================================================================


def web_search(query: str = "", top_k: int = 5) -> dict[str, Any]:
    """Search the web via DuckDuckGo (no API key needed)."""
    try:
        import re
        import urllib.parse
        import urllib.request

        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "VajraStream/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results = []
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        for s in snippets[:top_k]:
            clean = re.sub(r"<[^>]+>", "", s).strip()
            if clean:
                results.append({"snippet": clean[:300]})

        if not results:
            results = [
                {
                    "snippet": f"Web search for '{query}' — results unavailable (network issue or no results). Try using the local knowledge base via search_knowledge."
                }
            ]

        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        return {"query": query, "results": [], "error": str(e)}


def web_fetch(url: str = "") -> dict[str, Any]:
    """Fetch a web page and return its text (first 3000 characters)."""
    if not url:
        return {"error": "No URL provided"}
    try:
        import re
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "VajraStream/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return {"url": url, "content": text[:3000], "length": len(text)}
    except Exception as e:
        return {"url": url, "error": str(e)}


def get_world_context() -> dict[str, Any]:
    """Current world events, disasters and planetary hour, compiled for the model."""
    from core.internet_context import compile_world_context, format_context_for_llm

    ctx = compile_world_context()
    return {
        "events_count": len(ctx.events),
        "disasters_count": len(ctx.disasters),
        "summary": ctx.summary,
        "planetary_hour": ctx.planetary_hour,
        "day_ruler": ctx.day_ruler,
        "context_text": format_context_for_llm(ctx),
    }


def get_all_genre_windows() -> dict[str, Any]:
    from core.auspicious_timing import get_all_windows

    return {"windows": get_all_windows()}


def get_current_conditions() -> dict[str, Any]:
    from core.auspicious_timing import AuspiciousTiming

    return AuspiciousTiming().get_current_conditions()


# ============================================================================
# AGENT SUGGESTIONS
# ============================================================================


def add_agent_suggestion(agent_id: str, intention: str, missing_tools: str, context: str) -> dict[str, Any]:
    """
    Log an intentional path or suggestion for a task the agent wanted to do but couldn't.
    Use this when you lack the tools, permissions, or system capabilities to complete a requested or inferred task.

    Args:
        agent_id: Identifier for the current agent (e.g. 'llm_agent_1')
        intention: What you intended to do
        missing_tools: The specific tools or capabilities you needed
        context: Why you wanted to do it
    """
    from backend.app.api.v1.endpoints.agent_suggestions import IntentionalPathSchema, log_intentional_path

    return _dump(
        log_intentional_path(
            IntentionalPathSchema(agent_id=agent_id, intention=intention, missing_tools=missing_tools, context=context)
        )
    )


# ============================================================================
# REGISTRY VIEWS
# ----------------------------------------------------------------------------
# Read-only views of ``core.tool_registry`` kept for existing importers. The
# registry is the source; do not add tools here.
# ============================================================================

#: ``{name or alias: callable(**kwargs)}`` for every tool the chat dispatcher
#: can execute. Calls go through ``core.tool_registry.call``.
TOOL_REGISTRY = tool_registry.sync_callables(tool_registry.AGENT)

#: The advertised chat allowlist, in priority order.
ESSENTIAL_TOOL_ORDER: list[str] = list(tool_registry.CHAT_ORDER)
ESSENTIAL_TOOL_NAMES: set[str] = set(ESSENTIAL_TOOL_ORDER)


def get_tool_schemas(essential_only: bool = True) -> list[dict[str, Any]]:
    """Tool schemas (``name``/``description``/``parameters``).

    ``essential_only=True``: the advertised chat allowlist, in priority order.
    ``essential_only=False``: every tool the chat dispatcher can execute.
    """
    surface = tool_registry.CHAT if essential_only else tool_registry.AGENT
    return tool_registry.schemas(surface)
