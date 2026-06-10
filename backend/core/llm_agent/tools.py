"""
LLM Agent Tool Calling Interface for Vajra Stream

Provides a standardized interface for LLM agents to interact with the Vajra Stream
radionics system via tool calling (function calling).

Each function is designed to be called by an LLM agent and returns structured data
that can be used in the agent's responses.
"""

from typing import Any

import requests


class APIClient:
    """Client for making requests to Vajra Stream API"""

    def __init__(self, base_url: str | None = None):
        import os

        if base_url is None:
            port = os.environ.get("PORT", "8008")
            base_url = f"http://localhost:{port}"
        self.base_url = base_url

    def _get(self, endpoint: str) -> dict[str, Any]:
        """Make GET request"""
        response = requests.get(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make POST request"""
        response = requests.post(f"{self.base_url}{endpoint}", json=data or {})
        response.raise_for_status()
        return response.json()

    def _put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make PUT request"""
        response = requests.put(f"{self.base_url}{endpoint}", json=data)
        response.raise_for_status()
        return response.json()

    def _delete(self, endpoint: str) -> dict[str, Any]:
        """Make DELETE request"""
        response = requests.delete(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()


# Global API client instance
_client = None


def get_client() -> APIClient:
    """Get or create API client"""
    global _client
    if _client is None:
        _client = APIClient()
    return _client


# ============================================================================
# RNG ATTUNEMENT TOOLS
# ============================================================================


def create_rng_session(baseline_tone_arm: float = 5.0, sensitivity: float = 1.0) -> dict[str, Any]:
    """
    Create a new RNG attunement session for monitoring psychoenergetic activity.

    Use this when:
    - User wants to monitor RNG during practice
    - Starting manual radionics session
    - Need floating needle detection

    Args:
        baseline_tone_arm: Baseline setting (0-10), default 5.0
        sensitivity: Sensitivity multiplier (0.1-5.0), default 1.0

    Returns:
        {"session_id": "rng_1234567890_abcdef12"}
    """
    client = get_client()
    return client._post(
        "/api/v1/rng/session/create", {"baseline_tone_arm": baseline_tone_arm, "sensitivity": sensitivity}
    )


def get_rng_reading(session_id: str) -> dict[str, Any]:
    """
    Get current RNG reading including needle state and floating needle score.

    Use this for:
    - Monitoring psychoenergetic activity
    - Checking for floating needle (score > 0.6)
    - Real-time feedback during practice

    Args:
        session_id: RNG session ID from create_rng_session

    Returns:
        {
            "tone_arm": 5.2,
            "needle_position": 15.3,
            "needle_state": "rising",
            "floating_needle_score": 0.73,
            "coherence_index": 0.65,
            "entropy": 0.82
        }
    """
    client = get_client()
    return client._get(f"/api/v1/rng/session/{session_id}/reading")


def stop_rng_session(session_id: str) -> dict[str, Any]:
    """Stop active RNG session"""
    client = get_client()
    return client._post(f"/api/v1/rng/session/{session_id}/stop")


# ============================================================================
# AUDIO TOOLS
# ============================================================================


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
    client = get_client()

    # Generate the audio in memory
    gen_res = client._post("/api/v1/audio/generate_chakra", {"chakra_name": chakra_name, "duration": duration})

    if gen_res.get("status") == "success":
        # Play the audio on local hardware
        play_res = client._post("/api/v1/audio/play", {"hardware_level": 2})
        return {
            "status": "success",
            "message": f"Successfully playing {chakra_name} chakra healing audio.",
            "generation_details": gen_res,
            "playback_details": play_res,
        }
    return gen_res


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
    client = get_client()
    config = {
        "frequency": freq_hz,
        "duration": duration_s,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": 0.3,
        "modulation_depth": 0.05,
    }
    gen_res = client._post("/api/v1/audio/generate", config)
    if gen_res.get("status") == "success":
        play_res = client._post("/api/v1/audio/play", {"hardware_level": 2})
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
    client = get_client()
    config = {
        "frequency": 432.0,  # Defaulting to a safe base frequency
        "duration": duration_s,
        "volume": 0.8,
        "prayer_bowl_mode": True,
        "harmonic_strength": harmonic_strength,
        "modulation_depth": modulation_depth,
    }
    gen_res = client._post("/api/v1/audio/generate", config)
    if gen_res.get("status") == "success":
        play_res = client._post("/api/v1/audio/play", {"hardware_level": 2})
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
    client = get_client()
    presets_res = client._get("/api/v1/audio/presets")
    presets = presets_res.get("presets", {})
    if preset_name not in presets:
        return {"status": "error", "message": f"Preset '{preset_name}' not found."}

    config = presets[preset_name]
    config["duration"] = duration_s

    gen_res = client._post("/api/v1/audio/generate", config)
    if gen_res.get("status") == "success":
        play_res = client._post("/api/v1/audio/play", {"hardware_level": 2})
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

    client = get_client()
    return client._post(
        "/api/v1/slideshow/session/create",
        {
            "directory_path": directory_path,
            "intention_set": {
                "primary_mantra": mantra,
                "intentions": intentions,
                "repetitions_per_photo": repetitions_per_photo,
                "dedication": "May all beings benefit",
            },
            "loop_mode": loop_mode,
            "display_duration_ms": display_duration_ms,
            "rng_session_id": rng_session_id,
        },
    )


def get_current_slide(session_id: str) -> dict[str, Any]:
    """
    Get current slide information including photo details and progress.

    Args:
        session_id: Slideshow session ID

    Returns:
        Complete current slide info including photo, session, overlay, progress
    """
    client = get_client()
    return client._get(f"/api/v1/slideshow/session/{session_id}/current")


def stop_slideshow(session_id: str) -> dict[str, Any]:
    """
    Stop slideshow and get final statistics.

    Args:
        session_id: Slideshow session ID

    Returns:
        Final statistics including photos blessed, mantras repeated
    """
    client = get_client()
    return client._post(f"/api/v1/slideshow/session/{session_id}/stop")


# ============================================================================
# POPULATION MANAGEMENT TOOLS
# ============================================================================


def create_population(
    name: str,
    category: str,
    source_type: str,
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

    client = get_client()
    return client._post(
        "/api/v1/populations/create",
        {
            "name": name,
            "description": description,
            "category": category,
            "source_type": source_type,
            "directory_path": directory_path,
            "mantra_preference": mantra_preference,
            "intentions": intentions,
            "repetitions_per_photo": 108,
            "display_duration_ms": 2000,
            "priority": priority,
            "is_urgent": is_urgent,
            "tags": [],
            "notes": "",
        },
    )


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
    client = get_client()
    params = []
    if active_only:
        params.append("active_only=true")
    if category:
        params.append(f"category={category}")
    if urgent_only:
        params.append("urgent_only=true")

    query = "?" + "&".join(params) if params else ""
    return client._get(f"/api/v1/populations/{query}")


def get_population_statistics() -> dict[str, Any]:
    """
    Get overall statistics across all populations.

    Returns:
        Statistics including totals, categories, blessings sent
    """
    client = get_client()
    return client._get("/api/v1/populations/statistics/overall")


def update_population(population_id: str, **updates) -> dict[str, Any]:
    """
    Update a population's settings.

    Args:
        population_id: Population ID
        **updates: Fields to update (priority, is_urgent, etc.)

    Returns:
        Updated population object
    """
    client = get_client()
    return client._put(f"/api/v1/populations/{population_id}", updates)


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
    client = get_client()
    return client._post(
        "/api/v1/automation/start",
        {
            "mode": "round_robin",
            "duration_per_population": duration_per_population,
            "transition_pause": transition_pause,
            "link_rng": link_rng,
            "auto_dedicate": True,
            "continuous_mode": continuous_mode,
            "only_active": only_active,
            "min_priority": min_priority,
        },
    )


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
    client = get_client()
    return client._get(f"/api/v1/automation/{session_id}/status")


def get_automation_stats(session_id: str) -> dict[str, Any]:
    """
    Get complete automation statistics.

    Args:
        session_id: Automation session ID

    Returns:
        Complete statistics including history, totals, sessions completed
    """
    client = get_client()
    return client._get(f"/api/v1/automation/{session_id}/stats")


def stop_automation(session_id: str) -> dict[str, Any]:
    """
    Stop automated rotation and get final statistics.

    Args:
        session_id: Automation session ID

    Returns:
        Final statistics for entire automation session
    """
    client = get_client()
    return client._post(f"/api/v1/automation/{session_id}/stop")


def pause_automation(session_id: str) -> dict[str, Any]:
    """
    Pause automated rotation (can be resumed later).

    Args:
        session_id: Automation session ID

    Returns:
        Confirmation message
    """
    client = get_client()
    return client._post(f"/api/v1/automation/{session_id}/pause")


def resume_automation(session_id: str) -> dict[str, Any]:
    """
    Resume paused automation.

    Args:
        session_id: Automation session ID

    Returns:
        Confirmation message
    """
    client = get_client()
    return client._post(f"/api/v1/automation/{session_id}/resume")


# ============================================================================
# MAGICAL & ESOTERIC OPERATIONS TOOLS
# ============================================================================


def forge_sigil(intention: str, kamea: str = "saturn") -> dict[str, Any]:
    """
    Forge a magical visual sigil from an intention statement.
    Generates both planetary Kamea SVGs and schedules Stable Diffusion generation.

    Args:
        intention: What the sigil is designed to manifest or bless
        kamea: Planetary Kamea grid to draw on (saturn, jupiter, mars)
    """
    client = get_client()
    return client._post("/api/v1/sigils/forge", {"intention": intention, "kamea": kamea})


def cast_tarot_spread(count: int = 3, question: str = "") -> dict[str, Any]:
    """
    Draw Tarot cards from a 78-card deck with full elemental, Hebrew, and planetary correspondences.

    Args:
        count: Number of cards to draw (1, 3, or 10 for Celtic Cross)
        question: Question in focus for the Tarot oracle
    """
    client = get_client()
    res = client._post("/api/v1/divination/tarot/draw", {"count": count})
    if question and "cards" in res:
        # Request esoteric interpretation
        interpretation = client._post(
            "/api/v1/divination/interpret", {"system": "Tarot", "question": question, "details": res}
        )
        res["interpretation"] = interpretation.get("interpretation")
    return res


def cast_i_ching(question: str = "") -> dict[str, Any]:
    """
    Cast an I Ching hexagram using traditional yarrow-stalk probability weights.
    Returns primary/relating hexagrams, changing lines, and meaning interpretation.

    Args:
        question: The situation or focus query for the hexagram
    """
    client = get_client()
    res = client._post("/api/v1/divination/iching/cast")
    if question and "cast" in res:
        interpretation = client._post(
            "/api/v1/divination/interpret", {"system": "I Ching", "question": question, "details": res}
        )
        res["interpretation"] = interpretation.get("interpretation")
    return res


def cast_geomancy(question: str = "") -> dict[str, Any]:
    """
    Cast a Geomantic Shield Chart containing 4 Mothers, 4 Daughters, Nieces, Witnesses, and the Judge.
    Projects figures into the 12 astrological houses.

    Args:
        question: Query/trend-check focus
    """
    client = get_client()
    res = client._post("/api/v1/divination/geomancy/shield")
    if question and "chart" in res:
        interpretation = client._post(
            "/api/v1/divination/interpret", {"system": "Geomancy", "question": question, "details": res}
        )
        res["interpretation"] = interpretation.get("interpretation")
    return res


def search_grimoire_correspondences(query: str) -> list[dict[str, Any]]:
    """
    Search the Grimoire library for herbs, stones, metals, planets, and rates that match.

    Args:
        query: Name of herb, crystal, element, or symptom/intention
    """
    # Import locally to avoid circular dependency
    from backend.core.services.grimoire_service import grimoire_service

    return grimoire_service.search(query)


def get_planetary_hours_and_transits() -> dict[str, Any]:
    """
    Retrieve current planetary hour, day ruler, auspicious timing guidelines, and transits.
    """
    client = get_client()
    astrology_data = client._get("/api/v1/current")
    planetary_hours = client._get("/api/v1/planetary-hours")
    transits = client._get("/api/v1/transits")
    return {
        "astrology": astrology_data.get("astrology", {}),
        "planetary_hours": planetary_hours,
        "transits": transits.get("transits", []),
    }


# ============================================================================
# NARRATIVE GENERATION AND OUTLOOK TOOLS
# ============================================================================


def generate_single_outlook(
    lat: float = 34.0522,
    lon: float = -118.2437,
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
    client = get_client()
    return client._post(
        "/api/v1/outlook/generate_single",
        {
            "lat": lat,
            "lon": lon,
            "languages": languages,
            "genre": genre,
            "custom_context": custom_context,
            "realm_id": realm_id,
            "population_ids": population_ids,
            "character_ids": character_ids,
            "excluded_forces": excluded_forces,
            "include_dialogue": include_dialogue,
        },
    )


def generate_epic_outlook(
    lat: float = 34.0522,
    lon: float = -118.2437,
    languages: list[str] = None,
    genre: str = "alchemist",
    stages: int = 9,
    custom_context: str | None = None,
    realm_id: str | None = None,
    population_ids: list[str] | None = None,
    character_ids: list[str] | None = None,
    excluded_forces: list[str] | None = None,
    include_dialogue: bool = False,
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
    client = get_client()
    return client._post(
        "/api/v1/outlook/generate_epic",
        {
            "lat": lat,
            "lon": lon,
            "languages": languages,
            "genre": genre,
            "stages": stages,
            "custom_context": custom_context,
            "realm_id": realm_id,
            "population_ids": population_ids,
            "character_ids": character_ids,
            "excluded_forces": excluded_forces,
            "include_dialogue": include_dialogue,
        },
    )


def list_narrative_locations() -> list[dict[str, Any]]:
    """
    List all active locations and metaphysical realms.
    """
    client = get_client()
    return client._get("/api/v1/outlook/locations")


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
    client = get_client()
    return client._post(
        "/api/v1/outlook/locations",
        {
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
        },
    )


def list_narrative_characters() -> list[dict[str, Any]]:
    """
    List all active narrative characters and archetypes.
    """
    client = get_client()
    return client._get("/api/v1/outlook/characters")


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
    client = get_client()
    return client._post(
        "/api/v1/outlook/characters",
        {
            "name": name,
            "role": role,
            "description": description,
            "source_type": source_type,
            "dialogue_style": dialogue_style,
            "associated_realms": associated_realms or [],
            "mantra_preference": mantra_preference,
            "elemental_anchor": elemental_anchor,
            "priority": priority,
        },
    )


def start_narrative_loop(
    interval_minutes: int = 15,
    lat: float = 34.0522,
    lon: float = -118.2437,
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
    client = get_client()
    return client._post(
        "/api/v1/outlook/loop/start",
        {
            "interval_minutes": interval_minutes,
            "lat": lat,
            "lon": lon,
            "languages": languages,
            "genre": genre,
            "custom_context": custom_context,
            "realm_id": realm_id,
            "population_ids": population_ids,
            "character_ids": character_ids,
            "excluded_forces": excluded_forces,
            "include_dialogue": include_dialogue,
        },
    )


def stop_narrative_loop() -> dict[str, Any]:
    """
    Stop the active background narrative transmission loop.
    """
    client = get_client()
    return client._post("/api/v1/outlook/loop/stop")


def get_narrative_loop_status() -> dict[str, Any]:
    """
    Check active background narrative loop state, configuration, and last generated draft.
    """
    client = get_client()
    return client._get("/api/v1/outlook/loop/status")


# ============================================================================
# 88 BUDDHAS & SAKA DAWA TOOLS (stubs — executed by llm.py's execute_tool_locally)
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


def generate_buddha_narrative(buddha_name: str, depth: str = "contemplation") -> dict[str, Any]:
    """Generate a sacred narrative about a specific Buddha."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    return get_eighty_eight_buddhas().generate_buddha_narrative(buddha_name, depth=depth)


def get_88_buddhas_liturgy() -> dict[str, Any]:
    """Get the full 88-Buddha confession liturgy."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    return get_eighty_eight_buddhas().get_confession_sequence()


def recite_buddha_name(buddha_name: str) -> dict[str, Any]:
    """Recite a single Buddha name via TTS."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    svc = get_eighty_eight_buddhas()
    b = svc.get_buddha_by_name(buddha_name)
    if not b:
        return {"error": f"Buddha not found: {buddha_name}"}
    return {
        "buddha": b.name_chinese,
        "pinyin": b.name_pinyin,
        "message": f"Recitation of {b.name_chinese} would play via TTS.",
    }


def start_buddha_recitation(
    intention: str = "愿一切众生离苦得乐", interval_seconds: float = 3.0, mala_cycles: int | None = None
) -> dict[str, Any]:
    """Start continuous 88-Buddha recitation loop."""
    import asyncio

    from core.buddha_recitation_loop import get_recitation_loop

    loop = get_recitation_loop()
    if loop.state.running:
        return {"status": "already_running"}
    try:
        running_loop = asyncio.get_event_loop()
        if running_loop.is_running():
            running_loop.create_task(
                loop.start(intention=intention, interval_seconds=interval_seconds, mala_cycles=mala_cycles)
            )
        else:
            asyncio.run(loop.start(intention=intention, interval_seconds=interval_seconds, mala_cycles=mala_cycles))
    except RuntimeError:
        asyncio.run(loop.start(intention=intention, interval_seconds=interval_seconds, mala_cycles=mala_cycles))
    return loop.get_status()


def stop_buddha_recitation() -> dict[str, Any]:
    """Stop active Buddha recitation loop."""
    from core.buddha_recitation_loop import get_recitation_loop

    loop = get_recitation_loop()
    loop.stop()
    return loop.get_status()


def get_buddha_recitation_status() -> dict[str, Any]:
    """Get current recitation loop status."""
    from core.buddha_recitation_loop import get_recitation_loop

    return get_recitation_loop().get_status()


def check_saka_dawa() -> dict[str, Any]:
    """Check Saka Dawa holy month status."""
    from datetime import datetime

    from core.models.practice import Practice

    practices = Practice.get_default_practices()
    saka = next((p for p in practices if "saka" in p.name.lower()), None)
    if not saka:
        return {"error": "Saka Dawa practice not found"}
    now = datetime.now()
    in_window = now.month in (5, 6)
    return {
        "in_saka_dawa_window": in_window,
        "practice": {
            "name": saka.name,
            "genre": saka.genre,
            "merit_multiplier": saka.merit_multiplier,
            "blessing_prompt": saka.base_prompt_template,
        },
        "message": "ACTIVE — 100,000x merit!" if in_window else "Not in Saka Dawa window.",
    }


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
    client = get_client()
    return client._get("/api/v1/ritual/status")


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
    client = get_client()
    return client._post("/api/v1/ritual/start", {"min_timing_quality": min_timing_quality})


def stop_ritual_engine() -> dict[str, Any]:
    """Stop the autonomous ritual engine.

    Idempotent — safe to call when the engine is already stopped.

    Use this when:
    - The user asks to pause or stop automatic practice
    - You're transitioning to a manual ritual mode
    - The engine has accumulated enough merit and the user wants a break
    """
    client = get_client()
    return client._post("/api/v1/ritual/stop", {})


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
    client = get_client()
    return client._post("/api/v1/ritual/trigger", {})


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
    client = get_client()
    return client._get(f"/api/v1/ritual/schedule?hours={hours}")


def generate_character() -> dict[str, Any]:
    """Generate an RNG-seeded character."""
    from core.character_generator import CharacterGenerator

    return CharacterGenerator().generate(use_llm=False).to_dict()


def start_character_journey() -> dict[str, Any]:
    """Start a character journey arc."""
    from container import container
    from modules.radionics_operator import ToolDispatcher

    return ToolDispatcher(container).dispatch("start_character_journey", {})


def advance_journey() -> dict[str, Any]:
    """Advance character journey by one stage."""
    from container import container
    from modules.radionics_operator import ToolDispatcher

    return ToolDispatcher(container).dispatch("advance_journey", {})


def get_journey_status() -> dict[str, Any]:
    """Get current journey status."""
    from container import container
    from modules.radionics_operator import ToolDispatcher

    return ToolDispatcher(container).dispatch("get_journey_status", {})


def run_full_journey() -> dict[str, Any]:
    """Run full 6-stage journey."""
    from container import container
    from modules.radionics_operator import ToolDispatcher

    return ToolDispatcher(container).dispatch("run_full_journey", {})


# ============================================================================
# RADIONICS / BROADCASTING / ASTROLOGY / AUDIO STUBS
# (delegate to ToolDispatcher for unified dispatch)
# ============================================================================


def _dispatch_via_container(tool_name: str, **args) -> dict[str, Any]:
    """Helper: dispatch any tool through the container's ToolDispatcher."""
    from container import container
    from modules.radionics_operator import ToolDispatcher

    return ToolDispatcher(container).dispatch(tool_name, args)


def broadcast_healing(
    target_name: str, duration_minutes: int = 10, frequency_hz: float = 528.0, intensity: float = 0.8
) -> dict[str, Any]:
    return _dispatch_via_container(
        "broadcast_healing",
        target_name=target_name,
        duration_minutes=duration_minutes,
        frequency_hz=frequency_hz,
        intensity=intensity,
    )


def broadcast_liberation(event_name: str, souls_count: int = 1000, duration_minutes: int = 108) -> dict[str, Any]:
    return _dispatch_via_container(
        "broadcast_liberation", event_name=event_name, souls_count=souls_count, duration_minutes=duration_minutes
    )


def get_available_intentions() -> dict[str, Any]:
    return _dispatch_via_container("get_available_intentions")


def get_sacred_frequencies() -> dict[str, Any]:
    return _dispatch_via_container("get_sacred_frequencies")


def text_to_rate(text: str, num_dials: int = 3) -> dict[str, Any]:
    return _dispatch_via_container("text_to_rate", text=text, num_dials=num_dials)


def measure_general_vitality(subject: str, samples: int = 10) -> dict[str, Any]:
    return _dispatch_via_container("measure_general_vitality", subject=subject, samples=samples)


def find_balancing_rates(subject: str, num_rates: int = 5) -> dict[str, Any]:
    return _dispatch_via_container("find_balancing_rates", subject=subject, num_rates=num_rates)


def search_knowledge(query: str, top_k: int = 5, category: str | None = None) -> dict[str, Any]:
    return _dispatch_via_container("search_knowledge", query=query, top_k=top_k, category=category)


def search_rate_database(query: str, category: str | None = None) -> dict[str, Any]:
    return _dispatch_via_container("search_rate_database", query=query, category=category)


def generate_scalar_waves(method: str = "hybrid", count: int = 10000, intensity: float = 1.0) -> dict[str, Any]:
    return _dispatch_via_container("generate_scalar_waves", method=method, count=count, intensity=intensity)


def get_rng_summary(session_id: str) -> dict[str, Any]:
    return _dispatch_via_container("get_rng_summary", session_id=session_id)


def get_chakra_info() -> dict[str, Any]:
    return _dispatch_via_container("get_chakra_info")


def get_meridian_info() -> dict[str, Any]:
    return _dispatch_via_container("get_meridian_info")


def create_healing_session(
    target_name: str,
    modalities: list[str] | None = None,
    duration_minutes: int = 60,
    intention: str = "complete healing",
) -> dict[str, Any]:
    return _dispatch_via_container(
        "create_healing_session",
        target_name=target_name,
        modalities=modalities,
        duration_minutes=duration_minutes,
        intention=intention,
    )


def chakra_balancing_protocol(target_name: str, chakras: list[str] | None = None) -> dict[str, Any]:
    return _dispatch_via_container("chakra_balancing_protocol", target_name=target_name, chakras=chakras)


def get_healing_modalities() -> dict[str, Any]:
    return _dispatch_via_container("get_healing_modalities")


def get_planetary_positions() -> dict[str, Any]:
    return _dispatch_via_container("get_planetary_positions")


def calculate_natal_chart(
    name: str = "", birth_date: str = "", latitude: float = 0, longitude: float = 0
) -> dict[str, Any]:
    return _dispatch_via_container(
        "calculate_natal_chart", name=name, birth_date=birth_date, latitude=latitude, longitude=longitude
    )


def generate_audio(
    frequency_hz: float = 136.1, duration_seconds: float = 10, mode: str = "prayer_bowl"
) -> dict[str, Any]:
    return _dispatch_via_container("generate_audio", frequency_hz=frequency_hz, duration_seconds=duration_seconds)


def generate_blessing(
    target_name: str, intention: str = "peace and happiness", tradition: str = "universal"
) -> dict[str, Any]:
    return _dispatch_via_container(
        "generate_blessing", target_name=target_name, intention=intention, tradition=tradition
    )


def get_blessing_traditions() -> dict[str, Any]:
    return _dispatch_via_container("get_blessing_traditions")


def generate_prayer(intention: str, tradition: str = "universal") -> dict[str, Any]:
    return _dispatch_via_container("generate_prayer", intention=intention, tradition=tradition)


def generate_teaching(topic: str, length: str = "short") -> dict[str, Any]:
    return _dispatch_via_container("generate_teaching", topic=topic, length=length)


def generate_meditation_script(
    meditation_type: str, duration_minutes: int = 20, experience_level: str = "beginner"
) -> dict[str, Any]:
    return _dispatch_via_container(
        "generate_meditation_script",
        meditation_type=meditation_type,
        duration_minutes=duration_minutes,
        experience_level=experience_level,
    )


def web_search(query: str, top_k: int = 5) -> dict[str, Any]:
    return _dispatch_via_container("web_search", query=query, top_k=top_k)


def web_fetch(url: str) -> dict[str, Any]:
    return _dispatch_via_container("web_fetch", url=url)


def get_world_context() -> dict[str, Any]:
    return _dispatch_via_container("get_world_context")


def get_all_genre_windows() -> dict[str, Any]:
    return _dispatch_via_container("get_all_genre_windows")


def get_current_conditions() -> dict[str, Any]:
    return _dispatch_via_container("get_current_conditions")


# ============================================================================
# TOOL REGISTRY (for LLM agents)
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
    client = get_client()
    return client._post(
        "/api/v1/agent_suggestions/intentional_paths",
        {"agent_id": agent_id, "intention": intention, "missing_tools": missing_tools, "context": context},
    )


# Registry of all available tools
TOOL_REGISTRY = {
    "create_rng_session": create_rng_session,
    "get_rng_reading": get_rng_reading,
    "stop_rng_session": stop_rng_session,
    "play_chakra_healing_audio": play_chakra_healing_audio,
    "set_audio_frequency": set_audio_frequency,
    "set_audio_modulation": set_audio_modulation,
    "play_audio_preset": play_audio_preset,
    "create_blessing_slideshow": create_blessing_slideshow,
    "get_current_slide": get_current_slide,
    "stop_slideshow": stop_slideshow,
    "create_population": create_population,
    "list_populations": list_populations,
    "get_population_statistics": get_population_statistics,
    "update_population": update_population,
    "start_automation": start_automation,
    "get_automation_status": get_automation_status,
    "get_automation_stats": get_automation_stats,
    "stop_automation": stop_automation,
    "pause_automation": pause_automation,
    "resume_automation": resume_automation,
    "forge_sigil": forge_sigil,
    "cast_tarot_spread": cast_tarot_spread,
    "cast_i_ching": cast_i_ching,
    "cast_geomancy": cast_geomancy,
    "search_grimoire_correspondences": search_grimoire_correspondences,
    "get_planetary_hours_and_transits": get_planetary_hours_and_transits,
    "generate_single_outlook": generate_single_outlook,
    "generate_epic_outlook": generate_epic_outlook,
    "list_narrative_locations": list_narrative_locations,
    "create_narrative_location": create_narrative_location,
    "list_narrative_characters": list_narrative_characters,
    "create_narrative_character": create_narrative_character,
    "start_narrative_loop": start_narrative_loop,
    "stop_narrative_loop": stop_narrative_loop,
    "get_narrative_loop_status": get_narrative_loop_status,
    "add_agent_suggestion": add_agent_suggestion,
    # 88 Buddhas & Saka Dawa
    "get_random_buddha": get_random_buddha,
    "generate_buddha_narrative": generate_buddha_narrative,
    "get_88_buddhas_liturgy": get_88_buddhas_liturgy,
    "recite_buddha_name": recite_buddha_name,
    "start_buddha_recitation": start_buddha_recitation,
    "stop_buddha_recitation": stop_buddha_recitation,
    "get_buddha_recitation_status": get_buddha_recitation_status,
    "check_saka_dawa": check_saka_dawa,
    "check_auspicious_timing": check_auspicious_timing,
    "generate_character": generate_character,
    "start_character_journey": start_character_journey,
    "advance_journey": advance_journey,
    "get_journey_status": get_journey_status,
    "run_full_journey": run_full_journey,
    # Radionics / Broadcasting / Astrology / Audio (via ToolDispatcher)
    "broadcast_healing": broadcast_healing,
    "broadcast_liberation": broadcast_liberation,
    "get_available_intentions": get_available_intentions,
    "get_sacred_frequencies": get_sacred_frequencies,
    "text_to_rate": text_to_rate,
    "measure_general_vitality": measure_general_vitality,
    "find_balancing_rates": find_balancing_rates,
    "search_knowledge": search_knowledge,
    "search_rate_database": search_rate_database,
    "generate_scalar_waves": generate_scalar_waves,
    "get_rng_summary": get_rng_summary,
    "get_chakra_info": get_chakra_info,
    "get_meridian_info": get_meridian_info,
    "create_healing_session": create_healing_session,
    "chakra_balancing_protocol": chakra_balancing_protocol,
    "get_healing_modalities": get_healing_modalities,
    "get_planetary_positions": get_planetary_positions,
    "calculate_natal_chart": calculate_natal_chart,
    "generate_audio": generate_audio,
    "generate_blessing": generate_blessing,
    "get_blessing_traditions": get_blessing_traditions,
    "generate_prayer": generate_prayer,
    "generate_teaching": generate_teaching,
    "generate_meditation_script": generate_meditation_script,
    "web_search": web_search,
    "web_fetch": web_fetch,
    "get_world_context": get_world_context,
    "get_all_genre_windows": get_all_genre_windows,
    "get_current_conditions": get_current_conditions,
    # Ritual engine
    "get_ritual_status": get_ritual_status,
    "start_ritual_engine": start_ritual_engine,
    "stop_ritual_engine": stop_ritual_engine,
    "trigger_ritual": trigger_ritual,
    "list_practices": list_practices,
    "get_ritual_schedule": get_ritual_schedule,
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """
    Get JSON schemas for all available tools.

    Merges RADIONICS_TOOLS (core radionics/broadcasting/astrology schemas)
    with the llm_agent-specific tool schemas (slideshows, populations, narratives).

    Returns schemas in OpenAI function calling format.
    Can be used with Claude, GPT-4, or other LLMs that support tool calling.

    Returns:
        List of tool schemas
    """
    # Import RADIONICS_TOOLS for the full radionics/broadcasting/astrology domain
    try:
        from core.radionics_tools import RADIONICS_TOOLS as raw_schemas

        _radionics_schemas = []
        for s in raw_schemas:
            if "type" in s and s["type"] == "function" and "function" in s:
                _radionics_schemas.append(s["function"])
            else:
                _radionics_schemas.append(s)
    except ImportError:
        _radionics_schemas = []

    # llm_agent-specific schemas (slideshows, populations, narratives, divination, etc.)
    _agent_schemas = [
        {
            "name": "create_rng_session",
            "description": "Create a new RNG attunement session for monitoring psychoenergetic activity during radionics practice",
            "parameters": {
                "type": "object",
                "properties": {
                    "baseline_tone_arm": {
                        "type": "number",
                        "description": "Baseline tone arm setting (0-10), default 5.0",
                    },
                    "sensitivity": {"type": "number", "description": "Sensitivity multiplier (0.1-5.0), default 1.0"},
                },
            },
        },
        {
            "name": "get_rng_reading",
            "description": "Get current RNG reading to check for psychoenergetic activity. floating_needle_score > 0.6 indicates release/completion",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "RNG session ID from create_rng_session"}
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "create_blessing_slideshow",
            "description": "Create a blessing slideshow for a directory of photos with mantras and intentions",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Absolute path to directory containing photos"},
                    "mantra": {
                        "type": "string",
                        "enum": [
                            "chenrezig",
                            "tara",
                            "medicine_buddha",
                            "vajrasattva",
                            "manjushri",
                            "amitabha",
                            "universal",
                        ],
                        "description": "Mantra to use (default: chenrezig)",
                    },
                    "intentions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "love",
                                "healing",
                                "peace",
                                "protection",
                                "prosperity",
                                "wisdom",
                                "reunion",
                                "safety",
                                "liberation",
                                "compassion",
                                "clarity",
                                "strength",
                            ],
                        },
                        "description": "List of intentions to transmit",
                    },
                    "rng_session_id": {
                        "type": "string",
                        "description": "Optional RNG session ID to link for monitoring",
                    },
                },
                "required": ["directory_path"],
            },
        },
        {
            "name": "create_population",
            "description": "Create a new target population for automated blessings",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Clear, descriptive name for the population"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "missing_persons",
                            "refugees",
                            "disaster_victims",
                            "conflict_zones",
                            "hospital_patients",
                            "humanitarian_crisis",
                            "memorial",
                            "custom",
                        ],
                        "description": "Category of population",
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["local_directory", "manual"],
                        "description": "Where photos come from",
                    },
                    "directory_path": {
                        "type": "string",
                        "description": "Path to photos (required for local_directory)",
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Priority level (1-10, higher = more important)",
                    },
                },
                "required": ["name", "category", "source_type"],
            },
        },
        {
            "name": "start_automation",
            "description": "Start automated 24/7 rotation through all populations with fair time distribution",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_per_population": {
                        "type": "integer",
                        "description": "Seconds to spend on each population (default 1800 = 30 min)",
                    },
                    "continuous_mode": {"type": "boolean", "description": "Loop indefinitely if true (default true)"},
                    "link_rng": {"type": "boolean", "description": "Monitor RNG for each population (default true)"},
                },
            },
        },
        {
            "name": "stop_automation",
            "description": "Stop the currently running automated blessing rotation and return final statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Automation session ID from start_automation"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "pause_automation",
            "description": "Pause the automated blessing rotation (can be resumed later)",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Automation session ID from start_automation"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "resume_automation",
            "description": "Resume a previously paused automated blessing rotation",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Automation session ID from start_automation"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "get_automation_status",
            "description": "Get current automation status for monitoring. Call every 5-10 seconds for UI updates",
            "parameters": {
                "type": "object",
                "properties": {"session_id": {"type": "string", "description": "Automation session ID"}},
                "required": ["session_id"],
            },
        },
        {
            "name": "stop_rng_session",
            "description": "Stop an active RNG attunement session and get final summary statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "RNG session ID to stop"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "set_audio_frequency",
            "description": "Directly tune the carrier frequency of the active audio broadcast. Use this to actively change frequencies based on RNG readings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "freq_hz": {"type": "number", "description": "The frequency in Hz to play (e.g. 432.0, 528.0)"},
                    "duration_s": {"type": "number", "description": "Duration to play in seconds, default 30.0"},
                },
                "required": ["freq_hz"],
            },
        },
        {
            "name": "set_audio_modulation",
            "description": "Change the timbre and modulation of the active broadcast. Use this to increase or decrease the intensity/richness of the sound.",
            "parameters": {
                "type": "object",
                "properties": {
                    "harmonic_strength": {"type": "number", "description": "0.0 to 1.0, richness of overtones"},
                    "modulation_depth": {"type": "number", "description": "0.0 to 1.0, depth of vibrato/tremolo"},
                    "duration_s": {"type": "number", "description": "Duration to play in seconds, default 30.0"},
                },
                "required": ["harmonic_strength", "modulation_depth"],
            },
        },
        {
            "name": "play_audio_preset",
            "description": "Play a specific predefined audio preset. Available presets: 'om-frequency', 'heart-chakra', 'earth-resonance', 'pure-sine'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preset_name": {"type": "string", "description": "Name of the preset to play"},
                    "duration_s": {"type": "number", "description": "Duration in seconds, default 30.0"},
                },
                "required": ["preset_name"],
            },
        },
        {
            "name": "play_chakra_healing_audio",
            "description": "Generate and play a Tibetan prayer bowl tone tuned to a specific chakra. Use this to calm the space.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chakra_name": {"type": "string", "description": "Name of the chakra (e.g. root, sacral, heart)"},
                    "duration": {"type": "number", "description": "Duration to play in seconds, default 30.0"},
                },
                "required": ["chakra_name"],
            },
        },
        {
            "name": "list_populations",
            "description": "Get list of all populations with optional filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "active_only": {"type": "boolean", "description": "Only return active populations"},
                    "category": {"type": "string", "description": "Filter by specific category"},
                },
            },
        },
        {
            "name": "get_population_statistics",
            "description": "Get overall statistics across all populations including totals and categories",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "forge_sigil",
            "description": "Create a graphical, neon-glowing vector sigil on a planetary magic square from an intention.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intention": {
                        "type": "string",
                        "description": "Clear intention statement (e.g. 'protection and clarity')",
                    },
                    "kamea": {
                        "type": "string",
                        "enum": ["saturn", "jupiter", "mars"],
                        "description": "Planetary grid context (default saturn)",
                    },
                },
                "required": ["intention"],
            },
        },
        {
            "name": "cast_tarot_spread",
            "description": "Draw Tarot cards with elemental, Hebrew, and planetary correspondences to answer a question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of cards to draw: 1 (single), 3 (past/present/future), or 10 (Celtic Cross)",
                    },
                    "question": {"type": "string", "description": "Focus question for oracle interpretation"},
                },
            },
        },
        {
            "name": "cast_i_ching",
            "description": "Cast I Ching hexagrams using traditional yarrow-stalk probabilities, listing primary and relating hexagram meanings.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string", "description": "The situation or query to interpret"}},
            },
        },
        {
            "name": "cast_geomancy",
            "description": "Cast a full 16-figure Geomantic shield chart projected into the 12 astrological houses.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string", "description": "Query or context for the cast"}},
            },
        },
        {
            "name": "search_grimoire_correspondences",
            "description": "Search the Grimoire database for herbs, minerals, metals, planets, chakras, and rates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The herb, stone, planet, rate, or symptom to lookup"}
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_planetary_hours_and_transits",
            "description": "Fetch current planetary hours timeline, daily rulers, and planetary transit aspects.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "generate_single_outlook",
            "description": "Generate a single-pass sutra-style blessing and narrative outlook weaving astrology, divination, and realms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Target latitude"},
                    "lon": {"type": "number", "description": "Target longitude"},
                    "languages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Languages to weave (English, Sanskrit, Tibetan, Chinese, Latin, Greek, Hebrew)",
                    },
                    "genre": {
                        "type": "string",
                        "enum": ["healing", "victory", "alchemist", "fun_parable", "dharani"],
                        "description": "Blessing genre",
                    },
                    "custom_context": {"type": "string", "description": "Custom aspirations or intention text"},
                    "realm_id": {"type": "string", "description": "Location or realm ID from list_narrative_locations"},
                    "population_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Target population IDs",
                    },
                    "character_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Characters present in narrative",
                    },
                    "excluded_forces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Negative forces to pacify",
                    },
                    "include_dialogue": {
                        "type": "boolean",
                        "description": "Whether to include active dialogue between characters",
                    },
                },
            },
        },
        {
            "name": "generate_epic_outlook",
            "description": "Generate a multi-stage epic narrative blessing cycle over an extended arc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Target latitude"},
                    "lon": {"type": "number", "description": "Target longitude"},
                    "languages": {"type": "array", "items": {"type": "string"}, "description": "Languages to weave"},
                    "genre": {
                        "type": "string",
                        "enum": ["healing", "victory", "alchemist", "fun_parable", "dharani"],
                        "description": "Blessing genre",
                    },
                    "stages": {"type": "integer", "description": "Number of stages to generate (default 9)"},
                    "custom_context": {"type": "string", "description": "Custom aspirations or intention text"},
                    "realm_id": {"type": "string", "description": "Location or realm ID"},
                    "population_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Target population IDs",
                    },
                    "character_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Characters present in narrative",
                    },
                    "excluded_forces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Negative forces to pacify",
                    },
                    "include_dialogue": {
                        "type": "boolean",
                        "description": "Whether to include active dialogue between characters",
                    },
                },
            },
        },
        {
            "name": "list_narrative_locations",
            "description": "List all active settings, earthly sacred sites, and metaphysical realms.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "create_narrative_location",
            "description": "Define a new location or metaphysical realm setting for narrative blessings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of location or realm"},
                    "description": {"type": "string", "description": "Visionary description"},
                    "location_type": {
                        "type": "string",
                        "enum": [
                            "earthly_sacred",
                            "metaphysical_realm",
                            "cosmic_anchor",
                            "historical_academy",
                            "custom",
                        ],
                    },
                    "source_type": {"type": "string", "enum": ["manual", "generated", "mythology", "geographic"]},
                    "is_metaphysical": {"type": "boolean", "description": "Set True for metaphysical realms"},
                    "latitude": {"type": "number", "description": "Latitude (for earthly location)"},
                    "longitude": {"type": "number", "description": "Longitude (for earthly location)"},
                    "celestial_coordinates": {"type": "string", "description": "Star coordinates (metaphysical only)"},
                    "dimension_frequency": {
                        "type": "number",
                        "description": "Vibrational frequency in Hz (metaphysical only)",
                    },
                    "realm_governor": {"type": "string", "description": "Deity/guardian ruler"},
                    "astrological_anchor": {"type": "string", "description": "Planetary line anchor"},
                    "elemental_affinity": {"type": "string", "description": "Element (Fire, Water, etc.)"},
                },
                "required": ["name", "description", "location_type"],
            },
        },
        {
            "name": "list_narrative_characters",
            "description": "List all active narrative character personalities and spiritual archetypes.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "create_narrative_character",
            "description": "Create a new character archetype to weave into dialogue parables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Character name"},
                    "role": {
                        "type": "string",
                        "enum": ["master", "student", "alchemist", "hero", "deity", "guardian", "custom"],
                    },
                    "description": {"type": "string", "description": "Biography description"},
                    "dialogue_style": {"type": "string", "description": "Description of speaking style (e.g. koans)"},
                    "associated_realms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Realm IDs frequented",
                    },
                    "mantra_preference": {"type": "string", "description": "Preferred mantra key"},
                    "elemental_anchor": {"type": "string", "description": "Element key (space, fire, earth, etc.)"},
                },
                "required": ["name", "role", "description"],
            },
        },
        {
            "name": "start_narrative_loop",
            "description": "Start continuous background narrative generation broadcasting on cycles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interval_minutes": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1440,
                        "description": "Minutes per cycle",
                    },
                    "lat": {"type": "number", "description": "Target latitude"},
                    "lon": {"type": "number", "description": "Target longitude"},
                    "languages": {"type": "array", "items": {"type": "string"}, "description": "Languages to weave"},
                    "genre": {
                        "type": "string",
                        "enum": ["healing", "victory", "alchemist", "fun_parable", "dharani"],
                        "description": "Blessing genre",
                    },
                    "custom_context": {"type": "string", "description": "Custom intentions"},
                    "realm_id": {"type": "string", "description": "Realm ID"},
                    "population_ids": {"type": "array", "items": {"type": "string"}, "description": "Population IDs"},
                    "character_ids": {"type": "array", "items": {"type": "string"}, "description": "Character IDs"},
                    "excluded_forces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Negative forces to pacify",
                    },
                    "include_dialogue": {"type": "boolean", "description": "Include dialogue if True"},
                },
            },
        },
        {
            "name": "stop_narrative_loop",
            "description": "Stop the continuous background narrative loop.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_narrative_loop_status",
            "description": "Check configuration and status of the continuous narrative broadcast loop.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_current_slide",
            "description": "Get current slideshow photo details, progress, and overlay information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Slideshow session ID"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "stop_slideshow",
            "description": "Stop an active blessing slideshow and get final statistics including photos blessed and mantras repeated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Slideshow session ID"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "update_population",
            "description": "Update a target population's settings — priority, active status, urgency, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "population_id": {"type": "string", "description": "Population ID to update"},
                    "priority": {"type": "integer", "description": "Priority 1-10"},
                    "is_urgent": {"type": "boolean", "description": "Whether urgent"},
                    "is_active": {"type": "boolean", "description": "Whether active"},
                },
                "required": ["population_id"],
            },
        },
        {
            "name": "get_automation_stats",
            "description": "Get complete automation statistics including history, totals, sessions completed, and populations processed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Automation session ID"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "add_agent_suggestion",
            "description": "Log an intentional path or suggestion for a task the agent wanted to do but couldn't because of missing capabilities or permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Identifier for the current agent"},
                    "intention": {"type": "string", "description": "What you intended to do"},
                    "missing_tools": {"type": "string", "description": "The specific tools or capabilities you needed"},
                    "context": {"type": "string", "description": "Why you wanted to do it"},
                },
                "required": ["agent_id", "intention", "missing_tools", "context"],
            },
        },
    ]

    # Merge: return RADIONICS_TOOLS (45 schemas) + agent-specific schemas
    # This gives the LLM visibility into ALL 80+ tools
    return _radionics_schemas + _agent_schemas


# Example usage for LLM agents
if __name__ == "__main__":
    # Example: Complete automated workflow
    print("Creating population...")
    pop = create_population(
        name="Test Population", category="custom", source_type="manual", description="Test population for demonstration"
    )
    print(f"Created: {pop['id']}")

    print("\nListing all populations...")
    pops = list_populations()
    print(f"Total populations: {len(pops)}")

    print("\nGetting statistics...")
    stats = get_population_statistics()
    print(f"Total blessings sent: {stats['total_blessings_sent']}")

    # More examples would follow...
