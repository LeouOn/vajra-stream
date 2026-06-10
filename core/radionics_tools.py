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
    # Agentic Journey & Timing
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "check_auspicious_timing",
            "description": "Check if the current planetary hour, tithi, and nakshatra are favorable for a specific ritual genre. Returns go/no-go with quality rating and wait time if blocked. Genres: healing, victory, wisdom, purification, compassion, prosperity, protection, creativity.",
            "parameters": {
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
                    },
                },
                "required": ["genre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_genre_windows",
            "description": "Get auspicious timing windows for all ritual genres at once. Use this to find which genre is most favorable right now.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_conditions",
            "description": "Get current planetary conditions — hour ruler, tithi, nakshatra, moon phase. Use before launching rituals to understand the energetic landscape.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_character",
            "description": "Generate an RNG-seeded character for ritual work — element, role, frequency, stats, backstory. Each character is unique. Use when starting a new character journey arc.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_character_journey",
            "description": "Begin a 6-stage character journey arc (Initiation→Training→Working→Overcoming→Utopia→Multiverse) for a generated or provided character.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "advance_journey",
            "description": "Advance the active character journey by one complete stage. Each stage generates blessings, attunes rates, and applies stat growth.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_journey_status",
            "description": "Get current character journey status — stage, progress, stage results.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_full_journey",
            "description": "Generate a character and run all 6 stages of the journey arc synchronously. Returns complete harvest results.",
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
    # ------------------------------------------------------------------
    # 88 Buddhas & Saka Dawa
    # ------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_random_buddha",
            "description": "Get a random Buddha from the 88-Buddha collection with name, meaning, and a contemplation narrative. Use for daily practice inspiration or when a user asks for a Buddha to contemplate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["past", "confession"],
                        "description": "Optional: filter by 'past' (53 Past Buddhas) or 'confession' (35 Confession Buddhas).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_buddha_narrative",
            "description": "Generate a sacred narrative or contemplation about a specific Buddha from the 88-Buddha collection. Search by Chinese or Sanskrit name.",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_88_buddhas_liturgy",
            "description": "Get the complete 88-Buddha Great Repentance liturgy (八十八佛大懺悔文) — opening verse, 53 Past Buddhas, 35 Confession Buddhas, and closing dedication. Use when the user wants the full confession sequence.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recite_buddha_name",
            "description": "Recite a single Buddha's name using Chinese TTS (Edge TTS). Speaks the sacred name aloud for auditory contemplation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buddha_name": {
                        "type": "string",
                        "description": "Chinese name of the Buddha to recite (e.g., '普光佛').",
                    },
                },
                "required": ["buddha_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_buddha_recitation",
            "description": "Start a continuous 88-Buddha recitation loop with mala counting. Recites Buddha names at timed intervals with dedications every 21 names. Use for sustained practice sessions.",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_buddha_recitation",
            "description": "Stop the active 88-Buddha recitation loop. Returns final statistics.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_buddha_recitation_status",
            "description": "Get current status of the 88-Buddha recitation loop — running state, current Buddha, cycle count, total recited, progress percentage.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_saka_dawa",
            "description": "Check if we are currently in the Saka Dawa holy month (4th Tibetan month, typically May-June). Returns the Saka Dawa practice configuration with the epic three-part sutra blessing prompt and 100x merit multiplier. Use when the user asks about Saka Dawa or wants to perform a Saka Dawa blessing.",
            "parameters": {"type": "object", "properties": {}, "required": []},
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
    # Agentic journey tools
    "check_auspicious_timing": "timing.check",
    "get_all_genre_windows": "timing.all_windows",
    "get_current_conditions": "timing.conditions",
    "generate_character": "journey.generate_character",
    "start_character_journey": "journey.start",
    "advance_journey": "journey.advance",
    "get_journey_status": "journey.status",
    "run_full_journey": "journey.run_full",
    # 88 Buddhas & Saka Dawa tools
    "get_random_buddha": "buddhas.random",
    "generate_buddha_narrative": "buddhas.narrative",
    "get_88_buddhas_liturgy": "buddhas.liturgy",
    "recite_buddha_name": "buddhas.recite",
    "start_buddha_recitation": "buddhas.start_loop",
    "stop_buddha_recitation": "buddhas.stop_loop",
    "get_buddha_recitation_status": "buddhas.loop_status",
    "check_saka_dawa": "saka_dawa.check",
}


def get_tools_for_provider(provider: str = "openai") -> list[dict[str, Any]]:
    """Get tool schemas formatted for a specific LLM provider."""
    if provider in ("openai", "local"):
        return RADIONICS_TOOLS
    if provider == "anthropic":
        # Anthropic uses the same function-calling format
        return RADIONICS_TOOLS
    return RADIONICS_TOOLS
