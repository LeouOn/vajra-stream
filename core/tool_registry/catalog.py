"""The tool catalog: every LLM tool, defined once.

Each ``ToolSpec`` carries the tool's public name (stable: prompts and stored
conversations reference it), its JSON schema, its handler and the surfaces
that expose it. ``CHAT_ORDER`` is the advertised chat allowlist in priority
order.

Merged on 2026-10-16 from ``core/radionics_tools.py`` (operator schemas) and
``backend/core/llm_agent/tools.py`` (chat/agent schemas and ``TOOL_REGISTRY``).
Where both defined a schema, the radionics one is kept: it is the one both
surfaces already advertised.
"""

from .spec import AGENT, AUTONOMOUS, CHAT, OPERATOR, ToolSpec

#: Every handler lives in the in-process tool module.
_H = "backend.core.llm_agent.tools:"

#: Argument names models emit that map onto real parameters. Applied per tool,
#: and only when the tool does not accept the original name but does accept
#: the target (so ``intention`` reaches ``run_working`` intact and becomes
#: ``custom_context`` only for the outlook tools).
GLOBAL_ARG_ALIASES: dict[str, str] = {
    "intent": "custom_context",
    "intention": "custom_context",
    "focus": "custom_context",
    "context": "custom_context",
    "aspiration": "custom_context",
    "topic": "custom_context",
    "subject": "custom_context",
    "target": "population_ids",
    "targets": "population_ids",
    "duration": "duration_minutes",
    "minutes": "duration_minutes",
    "time": "duration_minutes",
    "voice": "edge_voice",
    "speed": "rate",
    "freq": "frequency",
    "hz": "frequency",
}

TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="broadcast_healing",
        description="Broadcast healing scalar waves and radionics rates to a target. Use sacred frequencies (Solfeggio, planetary) and chakra-aligned rates.",
        parameters={
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": "Name or identifier of the healing target (person, group, situation).",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Broadcast duration in minutes. Typical: 10-108.",
                    "default": 10,
                },
                "frequency_hz": {
                    "type": "number",
                    "description": "Base carrier frequency in Hz. Sacred values: 396 (liberation), 417 (undoing), 528 (DNA repair/love), 639 (relationships), 741 (intuition), 852 (spiritual order), 963 (divine consciousness), 136.1 (Earth/OM).",
                    "default": 528,
                },
                "intensity": {"type": "number", "description": "Broadcast intensity 0.0–1.0.", "default": 0.8},
            },
            "required": ["target_name"],
        },
        handler=_H + "broadcast_healing",
        surfaces=frozenset({AGENT, OPERATOR, AUTONOMOUS}),
        requires_approval=True,
        aliases=("broadcast_crystal", "set_crystal_intent"),
    ),
    ToolSpec(
        name="prepare_crystal_broadcast",
        description="Analyze an intention AND prepare the crystal bowl broadcast configuration in one call. Returns the derived Solfeggio carrier frequencies and prayer bowl parameters ready to feed into the crystal broadcaster. Use this when the user wants to start a broadcast from a free-text intention without specifying rates.",
        parameters={
            "type": "object",
            "properties": {
                "intention": {"type": "string", "description": "Free-text healing intention or goal."},
                "duration_minutes": {
                    "type": "integer",
                    "description": "Broadcast duration in minutes. Typical: 10-108.",
                    "default": 10,
                },
            },
            "required": ["intention"],
        },
        handler=_H + "prepare_crystal_broadcast",
        surfaces=frozenset({OPERATOR}),
    ),
    ToolSpec(
        name="broadcast_liberation",
        description="Broadcast liberation protocol — high-intensity scalar wave transmission for mass liberation, typically 108 minutes with 396 Hz carrier.",
        parameters={
            "type": "object",
            "properties": {
                "event_name": {"type": "string", "description": "Name of the event or population being liberated."},
                "souls_count": {
                    "type": "integer",
                    "description": "Estimated number of beings in the target population.",
                    "default": 1000,
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes. Traditional: 108.",
                    "default": 108,
                },
            },
            "required": ["event_name"],
        },
        handler=_H + "broadcast_liberation",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_available_intentions",
        description="List all available radionics intention types with their associated frequencies.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_available_intentions",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_sacred_frequencies",
        description="Get the full library of sacred frequencies — Solfeggio tones, planetary frequencies, and their correspondences.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_sacred_frequencies",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="text_to_rate",
        description="Convert a text intention/signature into a radionics rate (multi-dial values). Uses mixed algorithm (hash + gematria) for robust rate derivation. This is the core operation: intention → rate mapping.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The intention text, name, or signature to convert into a rate.",
                },
                "num_dials": {
                    "type": "integer",
                    "description": "Number of rate dials (2-5 typical). Traditional radionics uses 2 or 3.",
                    "default": 3,
                },
            },
            "required": ["text"],
        },
        handler=_H + "text_to_rate",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="measure_general_vitality",
        description="Draw General Vitality (GV) for a subject — the core resonance reading in radionics. GV is a DRAW: an RNG stands in for the stick pad or pendulum (a divinatory method). It is not a measurement and must never be reported as a diagnosis. Scale: 0-1000. Returns mean, median, std, min, max over several draws, plus a provenance map. Traditional reading bands: < 200 very low, 200-400 low, 400-600 balanced, 600-800 high, 800-1000 very high vitality. Phrase results as 'the draw reads as ...'.",
        parameters={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Who or what the draw is for (person name, intention, condition).",
                },
                "samples": {"type": "integer", "description": "Number of GV draws to average.", "default": 10},
            },
            "required": ["subject"],
        },
        handler=_H + "measure_general_vitality",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="find_balancing_rates",
        description="Find rates that balance/heal a subject. Inverts the subject's computed signature rate and offsets each dial by a draw; each rate's potency is drawn (stick-pad analog), not measured. Returns rates sorted by drawn potency, each with a provenance map.",
        parameters={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "The subject to find balancing rates for (condition, symptom, person).",
                },
                "num_rates": {
                    "type": "integer",
                    "description": "How many balancing rate candidates to generate.",
                    "default": 5,
                },
            },
            "required": ["subject"],
        },
        handler=_H + "find_balancing_rates",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="search_knowledge",
        description="Search the entire Vajra.Stream knowledge base — frequencies, mantras, radionics rates, healing correspondences, and historical events. Use this to find relevant information when the rate database doesn't have a direct match. Returns ranked results with similarity scores.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query about any radionics/spiritual topic.",
                },
                "top_k": {"type": "integer", "description": "Number of results to return.", "default": 5},
                "category": {
                    "type": "string",
                    "enum": ["frequency", "mantra", "rate", "healing", "history"],
                    "description": "Optional category to filter results.",
                },
            },
            "required": ["query"],
        },
        handler=_H + "search_knowledge",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="search_rate_database",
        description="Search the radionics rate database by name, category, or condition. The database contains pre-calibrated rates for organs, chakras, conditions, and healing remedies.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term — rate name, condition, organ, or category."},
                "category": {
                    "type": "string",
                    "description": "Optional category filter: organs_systems, conditions, chakra_rates, balancing_rates, healing_remedies.",
                    "enum": ["organs_systems", "conditions", "chakra_rates", "balancing_rates", "healing_remedies"],
                },
            },
            "required": ["query"],
        },
        handler=_H + "search_rate_database",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="generate_scalar_waves",
        description="Generate scalar wave values using one of five methods: qrng (quantum-random), lorenz (chaotic attractor), rossler (chaotic attractor), ca (cellular automata), or hybrid (combined). Returns the number of values generated and the measured generation time in seconds.",
        parameters={
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["qrng", "lorenz", "rossler", "ca", "hybrid"],
                    "description": "Generation method. hybrid blends all methods for maximum entropy.",
                    "default": "hybrid",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of scalar values to generate. Typical: 1000-100000.",
                    "default": 10000,
                },
                "intensity": {
                    "type": "number",
                    "description": "Generation intensity 0.0–1.0. Higher = more values, more CPU.",
                    "default": 1.0,
                },
            },
            "required": [],
        },
        handler=_H + "generate_scalar_waves",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="create_rng_session",
        description="Create an RNG attunement session for monitoring psychoenergetic activity (E-meter style needle visualization). Use before/during radionics sessions to track coherence and detect floating needle (release indicator).",
        parameters={
            "type": "object",
            "properties": {
                "baseline_tone_arm": {
                    "type": "number",
                    "description": "Baseline tone arm setting 0-10. Default: 5.0.",
                    "default": 5.0,
                },
                "sensitivity": {
                    "type": "number",
                    "description": "Sensitivity multiplier 0.1–5.0. Higher = more responsive needle.",
                    "default": 1.0,
                },
            },
            "required": [],
        },
        handler=_H + "create_rng_session",
        surfaces=frozenset({AGENT, OPERATOR}),
        aliases=("set_rng_bias", "calibrate_rng"),
        offload=False,
    ),
    ToolSpec(
        name="get_rng_reading",
        description="Get current RNG reading — tone arm, needle position, needle state, floating needle score, coherence, entropy. Needle states: still, rising, falling, floating (release indicator), stick (resistance), rock_slam (heavy charge).",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "RNG session ID from create_rng_session."}},
            "required": ["session_id"],
        },
        handler=_H + "get_rng_reading",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="get_rng_summary",
        description="Get RNG session summary — total readings, floating needle count, average tone arm, coherence/entropy averages.",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "RNG session ID from create_rng_session."}},
            "required": ["session_id"],
        },
        handler=_H + "get_rng_summary",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_chakra_info",
        description="Get detailed information about the seven chakras — Sanskrit/English names, locations, elements, colors, and associated frequencies.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_chakra_info",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_meridian_info",
        description="Get detailed information about the twelve meridians — names, elements, yin/yang classification.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_meridian_info",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="create_healing_session",
        description="Create a comprehensive healing session combining multiple modalities (scalar waves, radionics, chakra balancing, meridian clearing, blessing, sound healing).",
        parameters={
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "Name of the healing target."},
                "modalities": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "scalar_waves",
                            "radionics",
                            "chakra_balancing",
                            "meridian_clearing",
                            "blessing",
                            "sound_healing",
                            "visualization",
                            "time_cycle_healing",
                        ],
                    },
                    "description": "Healing modalities to combine.",
                },
                "duration_minutes": {"type": "integer", "description": "Session duration in minutes.", "default": 60},
                "intention": {
                    "type": "string",
                    "description": "Healing intention statement.",
                    "default": "complete healing",
                },
            },
            "required": ["target_name"],
        },
        handler=_H + "create_healing_session",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="chakra_balancing_protocol",
        description="Run a chakra balancing protocol — scalar waves + chakra harmonization for all seven chakras.",
        parameters={
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "Name of the target for chakra balancing."},
                "chakras": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["muladhara", "svadhisthana", "manipura", "anahata", "vishuddha", "ajna", "sahasrara"],
                    },
                    "description": "Specific chakras to balance (default: all seven).",
                },
            },
            "required": ["target_name"],
        },
        handler=_H + "chakra_balancing_protocol",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_healing_modalities",
        description="List all available healing modalities with descriptions.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_healing_modalities",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_planetary_positions",
        description="Get current planetary positions for astrological context. Useful for timing radionics sessions, selecting auspicious frequencies, and understanding cosmic influences.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_planetary_positions",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="calculate_natal_chart",
        description="Calculate a natal (birth) chart for a person. Required for personalized astrological radionics.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person's name."},
                "birth_date": {
                    "type": "string",
                    "description": "Birth date and time in ISO format (YYYY-MM-DDTHH:MM:SS).",
                },
                "latitude": {"type": "number", "description": "Birth latitude in decimal degrees."},
                "longitude": {"type": "number", "description": "Birth longitude in decimal degrees."},
            },
            "required": ["birth_date", "latitude", "longitude"],
        },
        handler=_H + "calculate_natal_chart",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="generate_audio",
        description="Generate healing audio at a specific frequency. Can produce prayer bowl synthesis (rich harmonics with natural decay) or pure sine waves. Sacred frequencies: 136.1 Hz (Earth/OM), 528 Hz (DNA repair/love), 432 Hz (universal harmony).",
        parameters={
            "type": "object",
            "properties": {
                "frequency_hz": {
                    "type": "number",
                    "description": "Base frequency in Hz. Use sacred values from get_sacred_frequencies.",
                    "default": 136.1,
                },
                "duration_seconds": {"type": "number", "description": "Duration in seconds.", "default": 10},
                "mode": {
                    "type": "string",
                    "enum": ["prayer_bowl", "sine"],
                    "description": "Audio synthesis mode: prayer_bowl = rich harmonics with natural decay, sine = pure tone.",
                    "default": "prayer_bowl",
                },
            },
            "required": [],
        },
        handler=_H + "generate_audio",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="generate_blessing",
        description="Generate a sacred blessing or prayer for a target with a specific intention. Supports multiple traditions (universal, buddhist, tibetan, zen).",
        parameters={
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "Who/what the blessing is for."},
                "intention": {
                    "type": "string",
                    "description": "The blessing intention (e.g., 'peace and happiness', 'healing', 'liberation').",
                    "default": "peace and happiness",
                },
                "tradition": {
                    "type": "string",
                    "enum": ["universal", "buddhist", "tibetan", "zen"],
                    "description": "Spiritual tradition for the blessing.",
                    "default": "universal",
                },
            },
            "required": ["target_name"],
        },
        handler=_H + "generate_blessing",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
        once_per_sitting=True,
    ),
    ToolSpec(
        name="get_blessing_traditions",
        description="List available blessing traditions with descriptions.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_blessing_traditions",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="generate_prayer",
        description="Generate a beautiful prayer/aspiration using the LLM. For heartfelt, poetic prayer text rather than radionics operations.",
        parameters={
            "type": "object",
            "properties": {
                "intention": {
                    "type": "string",
                    "description": "What the prayer is for (healing, peace, wisdom, etc.).",
                },
                "tradition": {
                    "type": "string",
                    "enum": ["universal", "buddhist", "tibetan", "zen"],
                    "default": "universal",
                },
            },
            "required": ["intention"],
        },
        handler=_H + "generate_prayer",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
        once_per_sitting=True,
    ),
    ToolSpec(
        name="generate_teaching",
        description="Generate a dharma teaching on a topic using the LLM.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Teaching topic (e.g., impermanence, compassion, emptiness).",
                },
                "length": {"type": "string", "enum": ["short", "medium", "long"], "default": "short"},
            },
            "required": ["topic"],
        },
        handler=_H + "generate_teaching",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="web_search",
        description="Search the web for current information about events, conditions, or radionics knowledge beyond the local knowledge base. Use this to find real-time context about world events, disasters, or to research healing correspondences.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — can be a world event, condition, or research topic.",
                },
                "top_k": {"type": "integer", "description": "Number of results to return.", "default": 5},
            },
            "required": ["query"],
        },
        handler=_H + "web_search",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="web_fetch",
        description="Fetch and read the content of a specific web page. Use after web_search to get detailed information about a specific result.",
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Full URL of the page to fetch."}},
            "required": ["url"],
        },
        handler=_H + "web_fetch",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_world_context",
        description="Get a real-time snapshot of current world events — active disasters, humanitarian crises, astrological transits, and planetary timing. Use this to understand what's happening in the world and identify events that could benefit from radionics broadcasting.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_world_context",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="check_auspicious_timing",
        description="Check if the current planetary hour, tithi, and nakshatra are favorable for a specific ritual genre. Returns go/no-go with quality rating and wait time if blocked. Genres: healing, victory, wisdom, purification, compassion, prosperity, protection, creativity.",
        parameters={
            "type": "object",
            "properties": {
                "genre": {
                    "type": "string",
                    "enum": [
                        "healing",
                        "victory",
                        "wisdom",
                        "purification",
                        "compassion",
                        "prosperity",
                        "protection",
                        "creativity",
                    ],
                    "description": "The ritual genre to check timing for.",
                }
            },
            "required": ["genre"],
        },
        handler=_H + "check_auspicious_timing",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="get_all_genre_windows",
        description="Get auspicious timing windows for all ritual genres at once. Use this to find which genre is most favorable right now.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_all_genre_windows",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_current_conditions",
        description="Get current planetary conditions — hour ruler, tithi, nakshatra, moon phase. Use before launching rituals to understand the energetic landscape.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_current_conditions",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="generate_character",
        description="Generate an RNG-seeded character for ritual work — element, role, frequency, stats, backstory. Each character is unique. Use when starting a new character journey arc.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "generate_character",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="start_character_journey",
        description="Begin a 6-stage character journey arc (Initiation→Training→Working→Overcoming→Utopia→Multiverse) for a generated or provided character.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "start_character_journey",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="advance_journey",
        description="Advance the active character journey by one complete stage. Each stage generates blessings, attunes rates, and applies stat growth.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "advance_journey",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="get_journey_status",
        description="Get current character journey status — stage, progress, stage results.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_journey_status",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="run_full_journey",
        description="Generate a character and run all 6 stages of the journey arc synchronously. Returns complete harvest results.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "run_full_journey",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="generate_meditation_script",
        description="Generate a guided meditation script for a specific practice using the LLM.",
        parameters={
            "type": "object",
            "properties": {
                "meditation_type": {
                    "type": "string",
                    "description": "Type of meditation (e.g., loving-kindness, shamatha, vipassana, body-scan).",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Target meditation duration in minutes.",
                    "default": 20,
                },
                "experience_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "default": "beginner",
                },
            },
            "required": ["meditation_type"],
        },
        handler=_H + "generate_meditation_script",
        surfaces=frozenset({AGENT, OPERATOR}),
    ),
    ToolSpec(
        name="get_random_buddha",
        description="Get a random Buddha from the 88-Buddha collection with name, meaning, and a contemplation narrative. Use for daily practice inspiration or when a user asks for a Buddha to contemplate.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["past", "confession"],
                    "description": "Optional: filter by 'past' (53 Past Buddhas) or 'confession' (35 Confession Buddhas).",
                }
            },
            "required": [],
        },
        handler=_H + "get_random_buddha",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="generate_buddha_narrative",
        description="Generate a sacred narrative or contemplation about a specific Buddha from the 88-Buddha collection. Search by Chinese or Sanskrit name.",
        parameters={
            "type": "object",
            "properties": {
                "buddha_name": {
                    "type": "string",
                    "description": "Chinese or Sanskrit name of the Buddha (e.g., 'Shakyamuni', '普光佛', 'Akshobhya').",
                },
                "depth": {
                    "type": "string",
                    "enum": ["brief", "contemplation", "narrative"],
                    "description": "Depth: 'brief' (2 lines), 'contemplation' (paragraph), 'narrative' (full story).",
                    "default": "contemplation",
                },
            },
            "required": ["buddha_name"],
        },
        handler=_H + "generate_buddha_narrative",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="get_88_buddhas_liturgy",
        description="Get the complete 88-Buddha Great Repentance liturgy (八十八佛大懺悔文) — opening verse, 53 Past Buddhas, 35 Confession Buddhas, and closing dedication. Use when the user wants the full confession sequence.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_88_buddhas_liturgy",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="recite_buddha_name",
        description="Recite a single Buddha's name using Chinese TTS (Edge TTS). Speaks the sacred name aloud for auditory contemplation.",
        parameters={
            "type": "object",
            "properties": {
                "buddha_name": {
                    "type": "string",
                    "description": "Chinese name of the Buddha to recite (e.g., '普光佛').",
                }
            },
            "required": ["buddha_name"],
        },
        handler=_H + "recite_buddha_name",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="start_buddha_recitation",
        description="Start a continuous 88-Buddha recitation loop with mala counting. Recites Buddha names at timed intervals with dedications every 21 names. Use for sustained practice sessions.",
        parameters={
            "type": "object",
            "properties": {
                "intention": {
                    "type": "string",
                    "description": "Dedication intention (e.g., 'world peace', 'all beings').",
                    "default": "愿一切众生离苦得乐",
                },
                "interval_seconds": {
                    "type": "number",
                    "description": "Seconds between each Buddha name recitation.",
                    "default": 3.0,
                },
                "mala_cycles": {
                    "type": "integer",
                    "description": "Number of full 88-name cycles before stopping (omit for infinite).",
                },
            },
            "required": [],
        },
        handler=_H + "start_buddha_recitation",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="stop_buddha_recitation",
        description="Stop the active 88-Buddha recitation loop. Returns final statistics.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "stop_buddha_recitation",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="get_buddha_recitation_status",
        description="Get current status of the 88-Buddha recitation loop — running state, current Buddha, cycle count, total recited, progress percentage.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "get_buddha_recitation_status",
        surfaces=frozenset({AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="check_saka_dawa",
        description="Check if we are currently in the Saka Dawa holy month (4th Tibetan month, typically May-June). Returns the Saka Dawa practice configuration with the epic three-part sutra blessing prompt and 100x merit multiplier. Use when the user asks about Saka Dawa or wants to perform a Saka Dawa blessing.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_H + "check_saka_dawa",
        surfaces=frozenset({CHAT, AGENT, OPERATOR}),
        offload=False,
    ),
    ToolSpec(
        name="create_blessing_slideshow",
        description="Create a blessing slideshow for a directory of photos with mantras and intentions",
        parameters={
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
                "rng_session_id": {"type": "string", "description": "Optional RNG session ID to link for monitoring"},
            },
            "required": ["directory_path"],
        },
        handler=_H + "create_blessing_slideshow",
        surfaces=frozenset({AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="create_population",
        description="Create a new target population for automated blessings",
        parameters={
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
                "directory_path": {"type": "string", "description": "Path to photos (required for local_directory)"},
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Priority level (1-10, higher = more important)",
                },
            },
            "required": ["name", "category", "source_type"],
        },
        handler=_H + "create_population",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="start_automation",
        description="Start automated 24/7 rotation through all populations with fair time distribution",
        parameters={
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
        handler=_H + "start_automation",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("start_blessing", "begin_session"),
        offload=False,
    ),
    ToolSpec(
        name="stop_automation",
        description="Stop the currently running automated blessing rotation and return final statistics",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Automation session ID from start_automation"}
            },
            "required": ["session_id"],
        },
        handler=_H + "stop_automation",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("stop_blessing",),
        offload=False,
    ),
    ToolSpec(
        name="pause_automation",
        description="Pause the automated blessing rotation (can be resumed later)",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Automation session ID from start_automation"}
            },
            "required": ["session_id"],
        },
        handler=_H + "pause_automation",
        surfaces=frozenset({AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="resume_automation",
        description="Resume a previously paused automated blessing rotation",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Automation session ID from start_automation"}
            },
            "required": ["session_id"],
        },
        handler=_H + "resume_automation",
        surfaces=frozenset({AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="get_automation_status",
        description="Get current automation status for monitoring. Call every 5-10 seconds for UI updates",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "Automation session ID"}},
            "required": ["session_id"],
        },
        handler=_H + "get_automation_status",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("get_session", "session_status"),
        offload=False,
    ),
    ToolSpec(
        name="stop_rng_session",
        description="Stop an active RNG attunement session and get final summary statistics",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "RNG session ID to stop"}},
            "required": ["session_id"],
        },
        handler=_H + "stop_rng_session",
        surfaces=frozenset({AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="set_audio_frequency",
        description="Directly tune the carrier frequency of the active audio broadcast. Use this to actively change frequencies based on RNG readings.",
        parameters={
            "type": "object",
            "properties": {
                "freq_hz": {"type": "number", "description": "The frequency in Hz to play (e.g. 432.0, 528.0)"},
                "duration_s": {"type": "number", "description": "Duration to play in seconds, default 30.0"},
            },
            "required": ["freq_hz"],
        },
        handler=_H + "set_audio_frequency",
        surfaces=frozenset({AGENT}),
        aliases=("set_scalar_frequency",),
    ),
    ToolSpec(
        name="set_audio_modulation",
        description="Change the timbre and modulation of the active broadcast. Use this to increase or decrease the intensity/richness of the sound.",
        parameters={
            "type": "object",
            "properties": {
                "harmonic_strength": {"type": "number", "description": "0.0 to 1.0, richness of overtones"},
                "modulation_depth": {"type": "number", "description": "0.0 to 1.0, depth of vibrato/tremolo"},
                "duration_s": {"type": "number", "description": "Duration to play in seconds, default 30.0"},
            },
            "required": ["harmonic_strength", "modulation_depth"],
        },
        handler=_H + "set_audio_modulation",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="play_audio_preset",
        description="Play a specific predefined audio preset. Available presets: 'om-frequency', 'heart-chakra', 'earth-resonance', 'pure-sine'.",
        parameters={
            "type": "object",
            "properties": {
                "preset_name": {"type": "string", "description": "Name of the preset to play"},
                "duration_s": {"type": "number", "description": "Duration in seconds, default 30.0"},
            },
            "required": ["preset_name"],
        },
        handler=_H + "play_audio_preset",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="play_chakra_healing_audio",
        description="Generate and play a Tibetan prayer bowl tone tuned to a specific chakra. Use this to calm the space.",
        parameters={
            "type": "object",
            "properties": {
                "chakra_name": {"type": "string", "description": "Name of the chakra (e.g. root, sacral, heart)"},
                "duration": {"type": "number", "description": "Duration to play in seconds, default 30.0"},
            },
            "required": ["chakra_name"],
        },
        handler=_H + "play_chakra_healing_audio",
        surfaces=frozenset({CHAT, AGENT}),
    ),
    ToolSpec(
        name="list_populations",
        description="Get list of all populations with optional filtering",
        parameters={
            "type": "object",
            "properties": {
                "active_only": {"type": "boolean", "description": "Only return active populations"},
                "category": {"type": "string", "description": "Filter by specific category"},
            },
        },
        handler=_H + "list_populations",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("list_targets", "show_targets", "show_populations", "get_targets", "list_population"),
        offload=False,
    ),
    ToolSpec(
        name="get_population_statistics",
        description="Get overall statistics across all populations including totals and categories",
        parameters={"type": "object", "properties": {}},
        handler=_H + "get_population_statistics",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="get_system_status",
        description="Complete system snapshot — populations, automation, RNG, rituals, practices. Use when user asks for 'statistics', 'status', 'dashboard', or 'system overview'. Returns everything in one call.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "get_system_status",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("get_statistics",),
    ),
    ToolSpec(
        name="forge_sigil",
        description="Create a graphical, neon-glowing vector sigil on a planetary magic square from an intention. An AI image comes inline as ai_image, or, on the local render engine, as ai_image_render {operation_id, status}: a queued render that finishes a few minutes later.",
        parameters={
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
        handler=_H + "forge_sigil",
        surfaces=frozenset({CHAT, AGENT}),
    ),
    ToolSpec(
        name="cast_tarot_spread",
        description="Draw Tarot cards with elemental, Hebrew, and planetary correspondences to answer a question.",
        parameters={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of cards to draw: 1 (single), 3 (past/present/future), or 10 (Celtic Cross)",
                },
                "question": {"type": "string", "description": "Focus question for oracle interpretation"},
            },
        },
        handler=_H + "cast_tarot_spread",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="cast_i_ching",
        description="Cast I Ching hexagrams using traditional yarrow-stalk probabilities, listing primary and relating hexagram meanings.",
        parameters={
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The situation or query to interpret"}},
        },
        handler=_H + "cast_i_ching",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="cast_geomancy",
        description="Cast a full 16-figure Geomantic shield chart projected into the 12 astrological houses.",
        parameters={
            "type": "object",
            "properties": {"question": {"type": "string", "description": "Query or context for the cast"}},
        },
        handler=_H + "cast_geomancy",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="search_grimoire_correspondences",
        description="Search the Grimoire database for herbs, minerals, metals, planets, chakras, and rates.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The herb, stone, planet, rate, or symptom to lookup"}
            },
            "required": ["query"],
        },
        handler=_H + "search_grimoire_correspondences",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="get_planetary_hours_and_transits",
        description="Fetch current planetary hours timeline, daily rulers, and planetary transit aspects.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "get_planetary_hours_and_transits",
        surfaces=frozenset({CHAT, AGENT}),
    ),
    ToolSpec(
        name="generate_single_outlook",
        description="Generate a single-pass sutra-style blessing and narrative outlook weaving astrology, divination, and realms. USE THIS TOOL when the user asks for: an outlook, a blessing, a sutra, a prayer, a healing story, a narrative blessing, or a generated prayer/affirmation for a group of people. The custom_context should reflect the user's stated intention. Do not call create_population repeatedly; if a population is needed, create it ONCE then call this tool.",
        parameters={
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
        handler=_H + "generate_single_outlook",
        surfaces=frozenset({CHAT, AGENT}),
        timeout_s=200.0,
        once_per_sitting=True,
    ),
    ToolSpec(
        name="generate_epic_outlook",
        description="Generate a multi-stage epic narrative blessing cycle over an extended arc.",
        parameters={
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
        handler=_H + "generate_epic_outlook",
        surfaces=frozenset({CHAT, AGENT}),
        timeout_s=300.0,
        once_per_sitting=True,
    ),
    ToolSpec(
        name="list_narrative_locations",
        description="List all active settings, earthly sacred sites, and metaphysical realms.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "list_narrative_locations",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="create_narrative_location",
        description="Define a new location or metaphysical realm setting for narrative blessings.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of location or realm"},
                "description": {"type": "string", "description": "Visionary description"},
                "location_type": {
                    "type": "string",
                    "enum": ["earthly_sacred", "metaphysical_realm", "cosmic_anchor", "historical_academy", "custom"],
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
        handler=_H + "create_narrative_location",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="list_narrative_characters",
        description="List all active narrative character personalities and spiritual archetypes.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "list_narrative_characters",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="create_narrative_character",
        description="Create a new character archetype to weave into dialogue parables.",
        parameters={
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
        handler=_H + "create_narrative_character",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="start_narrative_loop",
        description="Start continuous background narrative generation broadcasting on cycles.",
        parameters={
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
        handler=_H + "start_narrative_loop",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="stop_narrative_loop",
        description="Stop the continuous background narrative loop.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "stop_narrative_loop",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="get_narrative_loop_status",
        description="Check configuration and status of the continuous narrative broadcast loop.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "get_narrative_loop_status",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="get_current_slide",
        description="Get current slideshow photo details, progress, and overlay information.",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "Slideshow session ID"}},
            "required": ["session_id"],
        },
        handler=_H + "get_current_slide",
        surfaces=frozenset({AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="stop_slideshow",
        description="Stop an active blessing slideshow and get final statistics including photos blessed and mantras repeated.",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "Slideshow session ID"}},
            "required": ["session_id"],
        },
        handler=_H + "stop_slideshow",
        surfaces=frozenset({AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="update_population",
        description="Update a target population's settings — priority, active status, urgency, etc.",
        parameters={
            "type": "object",
            "properties": {
                "population_id": {"type": "string", "description": "Population ID to update"},
                "priority": {"type": "integer", "description": "Priority 1-10"},
                "is_urgent": {"type": "boolean", "description": "Whether urgent"},
                "is_active": {"type": "boolean", "description": "Whether active"},
            },
            "required": ["population_id"],
        },
        handler=_H + "update_population",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
    ),
    ToolSpec(
        name="get_automation_stats",
        description="Get complete automation statistics including history, totals, sessions completed, and populations processed.",
        parameters={
            "type": "object",
            "properties": {"session_id": {"type": "string", "description": "Automation session ID"}},
            "required": ["session_id"],
        },
        handler=_H + "get_automation_stats",
        surfaces=frozenset({AGENT}),
        aliases=("list_session",),
        offload=False,
    ),
    ToolSpec(
        name="add_agent_suggestion",
        description="Log an intentional path or suggestion for a task the agent wanted to do but couldn't because of missing capabilities or permissions.",
        parameters={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Identifier for the current agent"},
                "intention": {"type": "string", "description": "What you intended to do"},
                "missing_tools": {"type": "string", "description": "The specific tools or capabilities you needed"},
                "context": {"type": "string", "description": "Why you wanted to do it"},
            },
            "required": ["agent_id", "intention", "missing_tools", "context"],
        },
        handler=_H + "add_agent_suggestion",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="run_working",
        description="Begin a complete radionics working: derive a 5-dial rate from the intention, stamp Saka Dawa / Losar timing, map Solfeggio carriers, and optionally start a prayer-bowl broadcast. USE THIS when the user asks to begin a working, attune, broadcast a rate, charge an intention, or do radionics — not for casual chat.",
        parameters={
            "type": "object",
            "properties": {
                "intention": {"type": "string", "description": "The working's intention in the user's own words"},
                "target": {"type": "string", "description": "Who or what the working is for (default: all beings)"},
                "broadcast": {"type": "boolean", "description": "Start the prayer-bowl broadcast (default true)"},
                "duration_minutes": {
                    "type": "integer",
                    "description": "Broadcast duration in minutes, 1-30 (default 5)",
                },
                "deity": {
                    "type": "string",
                    "description": (
                        "Optional deity the working is offered through, painted in its witness with curated "
                        "iconography: green_tara, white_tara, avalokiteshvara (four-armed; or "
                        "'thousand-armed Avalokiteshvara'), medicine_buddha, amitabha, vajrasattva, cundi, "
                        "shakyamuni, manjushri, prajnaparamita, vairocana, akshobhya, ratnasambhava, amoghasiddhi, "
                        "or 88_buddhas. Leave out if none was named."
                    ),
                },
                "location": {
                    "type": "object",
                    "description": (
                        "Where the practitioner is sitting, ONLY if they explicitly said they are sealing it "
                        "somewhere other than home: {latitude, longitude, label}. Normally leave this out; the "
                        "user's saved home location is used. Not the place the working is for (that is target)."
                    ),
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "label": {"type": "string"},
                    },
                    "required": ["latitude", "longitude"],
                },
            },
            "required": ["intention"],
        },
        handler=_H + "run_working",
        surfaces=frozenset({CHAT, AGENT}),
        offload=False,
        once_per_sitting=True,
    ),
    ToolSpec(
        name="forge_witness",
        description="Generate a manifestation (witness) image for an already sealed working and attach it to the folio. Cheaper than video. Pass working_id. Uses the local render engine when it is up: that returns at once with status 'queued' and an operation_id, and the image lands on the folio a few minutes later. Otherwise a hosted image is attached immediately (witness_fallback explains why local was not used).",
        parameters={
            "type": "object",
            "properties": {"working_id": {"type": "string", "description": "Id returned by run_working (wrk_…)"}},
            "required": ["working_id"],
        },
        handler=_H + "forge_witness",
        surfaces=frozenset({CHAT, AGENT}),
    ),
    ToolSpec(
        name="speak_text",
        description="Speak text through the TTS engine. Use after generating a blessing, prayer, or teaching so it can be heard.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to speak"},
                "voice": {"type": "string", "description": "Optional voice override"},
                "role": {"type": "string", "description": "Ritual role for voice selection (default dharma_teaching)"},
            },
            "required": ["text"],
        },
        handler=_H + "speak_text",
        surfaces=frozenset({CHAT, AGENT}),
    ),
    ToolSpec(
        name="generate_image",
        description="Generate an image from a text prompt. The model and provider are configured in Settings — the LLM should NOT choose them. When model_lock is enabled (default), the configured default is always used. When disabled (discretionary mode), the LLM may suggest a model for the task, but the user's Settings still take precedence.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Image description. 30-60 words is ideal; max 1000 tokens. Be specific about subject, style, lighting, and mood. Imagery only: no numbers, degrees, percentages, dates, house numbers, headings, glyphs or words to be written in the picture (image models paint them as garbled text; they are stripped). Say 'a thin waning crescent moon', not 'Moon 12% illuminated'.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "description": "Override the configured default aspect ratio (e.g. '1:1', '16:9', '9:16'). Only set if the user explicitly asks for a specific shape.",
                },
                "subject_reference": {
                    "type": "string",
                    "description": "MiniMax only: URL of reference image for character consistency",
                },
            },
            "required": ["prompt"],
        },
        handler=_H + "generate_image_for_tool",
        surfaces=frozenset({CHAT, AGENT}),
    ),
    ToolSpec(
        name="get_celestial_night_sky",
        description="Calculate topocentric celestial dome Alt/Az coordinates for 10 planets and 10 Vedic nakshatra stars, with Moon phase, illumination, and LST.",
        parameters={
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Observer latitude in degrees (default: San Francisco 37.7749)",
                },
                "longitude": {
                    "type": "number",
                    "description": "Observer longitude in degrees (default: San Francisco -122.4194)",
                },
                "timestamp": {"type": "number", "description": "Unix timestamp in seconds (optional, defaults to now)"},
            },
        },
        handler=_H + "get_celestial_night_sky",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("get_night_sky", "night_sky", "celestial_sky"),
        arg_aliases={"lat": "latitude", "lon": "longitude", "lng": "longitude"},
        offload=False,
    ),
    ToolSpec(
        name="get_dharani_text",
        description="Retrieve complete unabbreviated sacred Dhāraṇī text (Sanskrit IAST, Chinese characters, English meaning, and recitation count). Supports Great Compassion (84 phrases), Śūraṅgama (5 assemblies), Sitātapatrā, Mahāpratisarā, Cundi, etc. Call with 'list' to browse directory.",
        parameters={
            "type": "object",
            "properties": {
                "dharani_id_or_name": {
                    "type": "string",
                    "description": "Identifier or name of dhāraṇī (e.g. 'great_compassion_dharani', 'shurangama_mantra_full', 'sitatapatra_dharani', 'cundi_dharani', or 'list')",
                }
            },
        },
        handler=_H + "get_dharani_text",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("get_dharani", "dharani_text", "dharani"),
        arg_aliases={"dharani_id": "dharani_id_or_name", "name": "dharani_id_or_name", "id": "dharani_id_or_name"},
        offload=False,
    ),
    ToolSpec(
        name="get_auspicious_timing_details",
        description="Retrieve full 24-hour Auspicious Timing Wheel data including planetary hours, current ruler, day/night status, tithi, nakshatra, Saka Dawa multiplier, and ritual genre green windows.",
        parameters={
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Observer latitude in degrees"},
                "longitude": {"type": "number", "description": "Observer longitude in degrees"},
            },
        },
        handler=_H + "get_auspicious_timing_details",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("timing_wheel", "get_timing_wheel"),
        arg_aliases={"lat": "latitude", "lon": "longitude", "lng": "longitude"},
        offload=False,
    ),
    ToolSpec(
        name="get_active_world_crises",
        description="Fetch real-time global crises and natural disaster alerts from GDACS and ReliefWeb, including geographic coordinates, magnitude/severity, and recommended compassionate healing intention focus.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "get_active_world_crises",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("world_crises", "get_world_crises", "active_crises"),
        offload=False,
    ),
    ToolSpec(
        name="trigger_living_ritual_broadcast",
        description="Trigger a living ritual broadcast combining 6-section generated ritual liturgy, crystal bowl Solfeggio carriers, dedication, and optional TTS recitation.",
        parameters={
            "type": "object",
            "properties": {
                "intention": {"type": "string", "description": "Sacred intention or dedication"},
                "target": {"type": "string", "description": "Target recipient or region (default 'all beings')"},
                "ritual_type": {
                    "type": "string",
                    "enum": [
                        "healing",
                        "victory",
                        "wisdom",
                        "purification",
                        "compassion",
                        "prosperity",
                        "protection",
                        "dedication_of_endeavors",
                    ],
                    "description": "Ritual genre or archetype",
                },
                "duration_minutes": {"type": "integer", "description": "Broadcast duration in minutes (default 5)"},
                "recite_with_tts": {"type": "boolean", "description": "Whether to recite the ritual aloud via TTS"},
            },
        },
        handler=_H + "trigger_living_ritual_broadcast",
        surfaces=frozenset({CHAT, AGENT}),
        aliases=("living_ritual", "living_ritual_broadcast"),
        offload=False,
    ),
    ToolSpec(
        name="get_ritual_status",
        description="Get the autonomous ritual engine's current state, recent ritual history and accumulated merit.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "get_ritual_status",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="start_ritual_engine",
        description="Start the autonomous ritual engine (a 60-second loop that selects and performs practices when the timing quality is at least the given minimum).",
        parameters={
            "type": "object",
            "properties": {
                "min_timing_quality": {
                    "type": "string",
                    "enum": ["excellent", "good", "challenging", "transmutative"],
                    "description": "Minimum timing quality to perform a ritual (default 'challenging').",
                }
            },
        },
        handler=_H + "start_ritual_engine",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="stop_ritual_engine",
        description="Stop the autonomous ritual engine. Safe to call when it is already stopped.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "stop_ritual_engine",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="trigger_ritual",
        description="Perform one ritual on the autonomous engine now, without starting its loop.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "trigger_ritual",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="list_practices",
        description="List the available ritual practices with their genre, merit multiplier and mantra.",
        parameters={"type": "object", "properties": {}},
        handler=_H + "list_practices",
        surfaces=frozenset({AGENT}),
    ),
    ToolSpec(
        name="get_ritual_schedule",
        description="Get the upcoming favorable ritual timing schedule from the ritual engine.",
        parameters={
            "type": "object",
            "properties": {"hours": {"type": "integer", "description": "Hours to look ahead (default 24)"}},
        },
        handler=_H + "get_ritual_schedule",
        surfaces=frozenset({AGENT}),
    ),
)

#: The chat allowlist, in priority order (the chat path caps the list, so
#: order decides what survives). Must equal the set of specs on ``CHAT``.
CHAT_ORDER: tuple[str, ...] = (
    "run_working",
    "forge_witness",
    "generate_single_outlook",
    "generate_prayer",
    "generate_image",
    "generate_epic_outlook",
    "generate_blessing",
    "generate_teaching",
    "forge_sigil",
    "speak_text",
    "cast_tarot_spread",
    "cast_i_ching",
    "cast_geomancy",
    "search_grimoire_correspondences",
    "search_knowledge",
    "web_search",
    "check_auspicious_timing",
    "get_auspicious_timing_details",
    "get_celestial_night_sky",
    "get_dharani_text",
    "get_active_world_crises",
    "trigger_living_ritual_broadcast",
    "check_saka_dawa",
    "get_planetary_hours_and_transits",
    "get_random_buddha",
    "create_population",
    "list_populations",
    "update_population",
    "get_population_statistics",
    "get_system_status",
    "start_automation",
    "stop_automation",
    "get_automation_status",
    "play_chakra_healing_audio",
)
