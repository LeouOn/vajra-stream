"""
Radionics Tool Schemas — OpenAI function-calling tool definitions for Vajra.Stream.

Defines a complete registry of typed tool schemas that enable LLMs to invoke
Vajra.Stream operations as structured function calls. Covers:
- Radionics broadcasting (healing, liberation, analysis, RNG interpretation)
- Affirmation and intention generation
- Context retrieval (knowledge index, internet news, session state)
- Outlook generation and astrological analysis

Each tool includes a JSON Schema ``parameters`` block compatible with OpenAI's
function-calling API, Anthropic's tool-use, and llama-cpp-python's grammar mode.

Exports:
    RADIONICS_TOOLS — the full list of tool definitions.
    get_tool_by_name — lookup utility.
"""

from typing import Any

# ============================================================================
# Tool Schema Registry
# ============================================================================

RADIONICS_TOOLS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # Radionics / Broadcasting
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "broadcast_healing",
            "description": "Broadcast healing scalar waves and radionics rates to a target. "
            "Use sacred frequencies (Solfeggio, planetary) and chakra-aligned rates.",
            "parameters": {
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
                    "intensity": {
                        "type": "number",
                        "description": "Broadcast intensity 0.0–1.0.",
                        "default": 0.8,
                    },
                },
                "required": ["target_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "broadcast_liberation",
            "description": "Broadcast liberation protocol — high-intensity scalar wave transmission "
            "for mass liberation, typically 108 minutes with 396 Hz carrier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_name": {
                        "type": "string",
                        "description": "Name of the event or population being liberated.",
                    },
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_intentions",
            "description": "List all available radionics intention types with their associated frequencies.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sacred_frequencies",
            "description": "Get the full library of sacred frequencies — Solfeggio tones, planetary frequencies, and their correspondences.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ------------------------------------------------------------------
    # Rate Selection & Analysis
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "text_to_rate",
            "description": "Convert a text intention/signature into a radionics rate (multi-dial values). "
            "Uses mixed algorithm (hash + gematria) for robust rate derivation. "
            "This is the core operation: intention → rate mapping.",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "measure_general_vitality",
            "description": "Measure General Vitality (GV) of a subject — the core energy/resonance metric in radionics. "
            "Scale: 0-1000. Returns mean, median, std, min, max over multiple samples. "
            "GV < 200 = very low, 200-400 = low, 400-600 = moderate, 600-800 = good, 800-1000 = excellent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "What/who is being measured (person name, intention, condition).",
                    },
                    "samples": {
                        "type": "integer",
                        "description": "Number of GV measurements to take. More samples = more stable reading.",
                        "default": 10,
                    },
                },
                "required": ["subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_balancing_rates",
            "description": "Find rates that balance/heal a subject. Generates complementary (inverse) rates "
            "based on the subject's signature rate. Returns top rates sorted by estimated potency.",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the entire Vajra.Stream knowledge base — frequencies, mantras, "
            "radionics rates, healing correspondences, and historical events. "
            "Use this to find relevant information when the rate database doesn't have "
            "a direct match. Returns ranked results with similarity scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about any radionics/spiritual topic.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 5,
                    },
                    "category": {
                        "type": "string",
                        "enum": ["frequency", "mantra", "rate", "healing", "history"],
                        "description": "Optional category to filter results.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_rate_database",
            "description": "Search the radionics rate database by name, category, or condition. "
            "The database contains pre-calibrated rates for organs, chakras, conditions, and healing remedies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term — rate name, condition, organ, or category.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter: organs_systems, conditions, chakra_rates, balancing_rates, healing_remedies.",
                        "enum": ["organs_systems", "conditions", "chakra_rates", "balancing_rates", "healing_remedies"],
                    },
                },
                "required": ["query"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Scalar Waves
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_scalar_waves",
            "description": "Generate scalar wave values using one of five methods: "
            "qrng (quantum-random), lorenz (chaotic attractor), rossler (chaotic attractor), "
            "ca (cellular automata), or hybrid (combined). Returns MOPS (million operations per second) metric.",
            "parameters": {
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
        },
    },
    # ------------------------------------------------------------------
    # RNG Attunement (E-meter style)
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_rng_session",
            "description": "Create an RNG attunement session for monitoring psychoenergetic activity "
            "(E-meter style needle visualization). Use before/during radionics sessions to track coherence and detect floating needle (release indicator).",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rng_reading",
            "description": "Get current RNG reading — tone arm, needle position, needle state, floating needle score, coherence, entropy. "
            "Needle states: still, rising, falling, floating (release indicator), stick (resistance), rock_slam (heavy charge).",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RNG session ID from create_rng_session.",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_rng_summary",
            "description": "Get RNG session summary — total readings, floating needle count, average tone arm, coherence/entropy averages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RNG session ID from create_rng_session.",
                    },
                },
                "required": ["session_id"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Energetic Anatomy
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_chakra_info",
            "description": "Get detailed information about the seven chakras — Sanskrit/English names, locations, elements, colors, and associated frequencies.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_meridian_info",
            "description": "Get detailed information about the twelve meridians — names, elements, yin/yang classification.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ------------------------------------------------------------------
    # Healing Protocols
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_healing_session",
            "description": "Create a comprehensive healing session combining multiple modalities "
            "(scalar waves, radionics, chakra balancing, meridian clearing, blessing, sound healing).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {
                        "type": "string",
                        "description": "Name of the healing target.",
                    },
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
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Session duration in minutes.",
                        "default": 60,
                    },
                    "intention": {
                        "type": "string",
                        "description": "Healing intention statement.",
                        "default": "complete healing",
                    },
                },
                "required": ["target_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "chakra_balancing_protocol",
            "description": "Run a chakra balancing protocol — scalar waves + chakra harmonization for all seven chakras.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {
                        "type": "string",
                        "description": "Name of the target for chakra balancing.",
                    },
                    "chakras": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "muladhara",
                                "svadhisthana",
                                "manipura",
                                "anahata",
                                "vishuddha",
                                "ajna",
                                "sahasrara",
                            ],
                        },
                        "description": "Specific chakras to balance (default: all seven).",
                    },
                },
                "required": ["target_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_healing_modalities",
            "description": "List all available healing modalities with descriptions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ------------------------------------------------------------------
    # Astrology
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_planetary_positions",
            "description": "Get current planetary positions for astrological context. "
            "Useful for timing radionics sessions, selecting auspicious frequencies, and understanding cosmic influences.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_natal_chart",
            "description": "Calculate a natal (birth) chart for a person. Required for personalized astrological radionics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Person's name.",
                    },
                    "birth_date": {
                        "type": "string",
                        "description": "Birth date and time in ISO format (YYYY-MM-DDTHH:MM:SS).",
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Birth latitude in decimal degrees.",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Birth longitude in decimal degrees.",
                    },
                },
                "required": ["birth_date", "latitude", "longitude"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Audio / Frequency
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_audio",
            "description": "Generate healing audio at a specific frequency. "
            "Can produce prayer bowl synthesis (rich harmonics with natural decay) or pure sine waves. "
            "Sacred frequencies: 136.1 Hz (Earth/OM), 528 Hz (DNA repair/love), 432 Hz (universal harmony).",
            "parameters": {
                "type": "object",
                "properties": {
                    "frequency_hz": {
                        "type": "number",
                        "description": "Base frequency in Hz. Use sacred values from get_sacred_frequencies.",
                        "default": 136.1,
                    },
                    "duration_seconds": {
                        "type": "number",
                        "description": "Duration in seconds.",
                        "default": 10,
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["prayer_bowl", "sine"],
                        "description": "Audio synthesis mode: prayer_bowl = rich harmonics with natural decay, sine = pure tone.",
                        "default": "prayer_bowl",
                    },
                },
                "required": [],
            },
        },
    },
    # ------------------------------------------------------------------
    # Blessings
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_blessing",
            "description": "Generate a sacred blessing or prayer for a target with a specific intention. "
            "Supports multiple traditions (universal, buddhist, tibetan, zen).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {
                        "type": "string",
                        "description": "Who/what the blessing is for.",
                    },
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_blessing_traditions",
            "description": "List available blessing traditions with descriptions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ------------------------------------------------------------------
    # Prayer / Dharma Content (existing LLM functionality)
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_prayer",
            "description": "Generate a beautiful prayer/aspiration using the LLM. "
            "For heartfelt, poetic prayer text rather than radionics operations.",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_teaching",
            "description": "Generate a dharma teaching on a topic using the LLM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Teaching topic (e.g., impermanence, compassion, emptiness).",
                    },
                    "length": {
                        "type": "string",
                        "enum": ["short", "medium", "long"],
                        "default": "short",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    # ------------------------------------------------------------------
    # Web Search & World Context
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information about events, conditions, "
            "or radionics knowledge beyond the local knowledge base. Use this to find "
            "real-time context about world events, disasters, or to research healing correspondences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — can be a world event, condition, or research topic.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the content of a specific web page. Use after web_search "
            "to get detailed information about a specific result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL of the page to fetch.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_world_context",
            "description": "Get a real-time snapshot of current world events — active disasters, "
            "humanitarian crises, astrological transits, and planetary timing. "
            "Use this to understand what's happening in the world and identify "
            "events that could benefit from radionics broadcasting.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ------------------------------------------------------------------
    # Prayer / Dharma Content
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_meditation_script",
            "description": "Generate a guided meditation script for a specific practice using the LLM.",
            "parameters": {
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
        },
    },
]

# ============================================================================
# Tool name → handler mapping (for dispatch)
# ============================================================================

TOOL_HANDLERS: dict[str, str] = {
    "broadcast_healing": "radionics.broadcast_healing",
    "broadcast_liberation": "radionics.broadcast_liberation",
    "get_available_intentions": "radionics.get_available_intentions",
    "get_sacred_frequencies": "radionics.get_sacred_frequencies",
    "text_to_rate": "radionics_engine.text_to_rate",
    "measure_general_vitality": "radionics_engine.measure_gv",
    "find_balancing_rates": "radionics_engine.find_balancing_rates",
    "search_knowledge": "knowledge.search",
    "search_rate_database": "radionics_engine.search_rates",
    "web_search": "web.search",
    "web_fetch": "web.fetch",
    "get_world_context": "world.context",
    "generate_scalar_waves": "scalar_waves.generate",
    "create_rng_session": "rng.create_session",
    "get_rng_reading": "rng.get_reading",
    "get_rng_summary": "rng.get_summary",
    "get_chakra_info": "anatomy.get_chakra_info",
    "get_meridian_info": "anatomy.get_meridian_info",
    "create_healing_session": "healing.create_healing_session",
    "chakra_balancing_protocol": "healing.chakra_balancing_protocol",
    "get_healing_modalities": "healing.get_available_modalities",
    "get_planetary_positions": "astrology.get_planetary_positions",
    "calculate_natal_chart": "astrology.calculate_natal_chart",
    "generate_audio": "audio.generate",
    "generate_blessing": "blessings.generate",
    "get_blessing_traditions": "blessings.get_traditions",
    "generate_prayer": "llm.generate_prayer",
    "generate_teaching": "llm.generate_teaching",
    "generate_meditation_script": "llm.generate_meditation_script",
}


def get_tools_for_provider(provider: str = "openai") -> list[dict[str, Any]]:
    """Get tool schemas formatted for a specific LLM provider."""
    if provider in ("openai", "local"):
        return RADIONICS_TOOLS
    if provider == "anthropic":
        # Anthropic uses the same function-calling format
        return RADIONICS_TOOLS
    return RADIONICS_TOOLS
