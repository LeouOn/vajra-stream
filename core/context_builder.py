"""
Context Builder
Constructs a rich system prompt for the RadionicsOperator LLM by loading
knowledge base files and injecting active session state.

The prompt gives the LLM everything it needs to act as a radionics practitioner:
- Sacred frequency correspondences
- Mantra library (summarized)
- Chakra/meridian anatomy
- Rate selection heuristics
- Active session context (rates, GV, RNG)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Path to knowledge base
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

# ============================================================================
# Core prompt template
# ============================================================================

RADIONICS_OPERATOR_SYSTEM_PROMPT = """You are a Vajra.Stream Radionics Operator — an AI radionics practitioner and sacred technology assistant.

## Your Role
You help users design and execute radionics sessions by:
1. **Analyzing intentions** — parse the user's intention into structured components (target, condition, system, chakra)
2. **Selecting rates** — recommend multi-dial radionics rates based on intention, knowledge base, and correspondences
3. **Choosing frequencies** — select optimal carrier frequencies (Solfeggio, planetary, Schumann) for the intention
4. **Recommending mantras** — suggest appropriate mantras from Buddhist, Hindu, and universal traditions
5. **Interpreting feedback** — analyze RNG readings, GV measurements, and coherence to assess session effectiveness
6. **Designing protocols** — combine modalities (scalar waves, radionics, chakra balancing, audio) into coherent sessions

## Radionics Fundamentals
- **Rates** are multi-dial numerical values (typically 2-3 dials, values 0-100) representing energy signatures
- **General Vitality (GV)** is measured 0-1000: <200 very low, 200-400 low, 400-600 moderate, 600-800 good, 800-1000 excellent
- **Broadcasting** transmits rates via scalar waves on a carrier frequency
- **Signature rates** are derived from intention text via hash+gematria algorithms
- **Balancing rates** are complementary/inverse rates that help restore equilibrium

## Operating Guidelines
- When a user describes an intention or condition, use tools to find appropriate rates rather than guessing
- Always consider chakra correspondences when selecting frequencies
- For physical conditions, search the rate database for organ/system-specific rates
- For emotional/spiritual intentions, use Solfeggio frequencies with the corresponding chakra
- 108 is a sacred number — use it for durations, repetitions, and counts when appropriate
- Always suggest a complete configuration: intention → rate → frequency → mantra → duration
- Explain your reasoning briefly — users want to understand WHY a rate was chosen

## Sacred Frequencies Quick Reference
{frequencies_reference}

## Mantra Quick Reference
{mantras_reference}

## Chakra Correspondences
{chakra_reference}
"""

# ============================================================================
# Knowledge loaders
# ============================================================================


def _load_json(path: Path) -> dict:
    """Load a JSON file, returning empty dict on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def build_frequencies_reference() -> str:
    """Build a compact frequencies reference table for the system prompt."""
    freq_data = _load_json(KNOWLEDGE_DIR / "frequencies.json")
    lines = []

    solfeggio = freq_data.get("solfeggio", {})
    if solfeggio:
        lines.append("### Solfeggio Frequencies")
        for hz, info in solfeggio.items():
            lines.append(
                f"- **{hz} Hz** — {info.get('name', '')} ({info.get('purpose', '')}) → {info.get('chakra', '')} chakra"
            )

    planetary = freq_data.get("planetary", {})
    if planetary:
        lines.append("\n### Planetary Frequencies")
        for hz, info in planetary.items():
            lines.append(
                f"- **{hz} Hz** — {info.get('name', '')} ({info.get('planet', '')}) — {info.get('purpose', '')}"
            )

    schumann = freq_data.get("schumann", {})
    if schumann:
        lines.append("\n### Schumann Resonances")
        for hz, info in schumann.items():
            lines.append(f"- **{hz} Hz** — {info.get('name', '')} — {info.get('purpose', '')}")

    brainwave = freq_data.get("brainwave", {})
    if brainwave:
        lines.append("\n### Brainwave States")
        for hz, info in brainwave.items():
            lines.append(
                f"- **{hz} Hz** — {info.get('name', '')} ({info.get('state', '')}) — {info.get('purpose', '')}"
            )

    return "\n".join(lines) if lines else "(frequency data unavailable)"


def build_mantras_reference() -> str:
    """Build a compact mantras reference for the system prompt."""
    mantra_data = _load_json(KNOWLEDGE_DIR / "mantras.json")
    lines = []

    for tradition, mantras in mantra_data.items():
        if tradition == "aspirations":
            continue
        if not isinstance(mantras, dict):
            continue
        lines.append(f"\n### {tradition.replace('_', ' ').title()}")
        for key, info in mantras.items():
            if isinstance(info, dict):
                name = info.get("name", key)
                purpose = info.get("purpose", "")
                chakra = info.get("chakra", "")
                chakra_str = f" → {chakra}" if chakra else ""
                lines.append(f"- **{name}** — {purpose}{chakra_str}")

    return "\n".join(lines[:80]) if lines else "(mantra data unavailable)"


def build_chakra_reference() -> str:
    """Build compact chakra reference."""
    return """| Chakra | Sanskrit | Location | Element | Color | Solfeggio Hz |
|--------|----------|----------|---------|-------|-------------|
| Root | Muladhara | Base of spine | Earth | Red | 396 |
| Sacral | Svadhisthana | Lower abdomen | Water | Orange | 417 |
| Solar Plexus | Manipura | Upper abdomen | Fire | Yellow | 528 |
| Heart | Anahata | Center of chest | Air | Green | 639 |
| Throat | Vishuddha | Throat | Ether | Blue | 741 |
| Third Eye | Ajna | Between eyebrows | Light | Indigo | 852 |
| Crown | Sahasrara | Top of head | Consciousness | Violet | 963 |"""


def load_rate_database() -> dict[str, list[dict]]:
    """Load all radionics rate databases."""
    rates_dir = KNOWLEDGE_DIR / "radionics_rates"
    databases = {}
    for rate_file in rates_dir.glob("*.json"):
        key = rate_file.stem
        data = _load_json(rate_file)
        if isinstance(data, dict):
            databases[key] = [{**v, "id": k} for k, v in data.items() if isinstance(v, dict)]
        elif isinstance(data, list):
            databases[key] = data
    return databases


def format_astrology_for_llm() -> str:
    """Build a concise current-astrology summary for LLM context injection.

    Auto-fetches comprehensive astrology for now at default SF location.
    Returns a compact 6-8 line summary suitable for appending to a system prompt.
    """
    try:
        from datetime import datetime

        import pytz

        from core.astrology import AstrologicalCalculator

        astro = AstrologicalCalculator()
        now = datetime.now(pytz.UTC)
        data = astro.get_comprehensive_astrology(now, (37.7749, -122.4194))

        western = data.get("western", {})
        indian = data.get("indian", {})
        chinese = data.get("chinese", {})
        hours = data.get("planetary_hours", {})
        moon = data.get("moon_phase", {})

        positions = western.get("positions", {})
        sun = positions.get("sun", {})
        moon_pos = positions.get("moon", {})
        asc = positions.get("ascendant", {})

        # Top 3 aspects
        aspects = western.get("aspects", [])[:3]
        aspect_lines = (
            ", ".join(f"{a['planet1']} {a['aspect'].lower()} {a['planet2']}" for a in aspects)
            if aspects
            else "no major aspects"
        )

        # Retrograde planets
        rx = [p for p, d in positions.items() if d.get("retrograde") and p not in ("ascendant", "midheaven")]
        rx_str = f"Retrograde: {', '.join(rx)}. " if rx else ""

        panchanga = indian.get("panchanga", {})

        lines = [
            "Current Astrology:",
            f"  Sun: {sun.get('sign', '?')} {sun.get('degree', 0):.1f}° (H{sun.get('house', '?')})",
            f"  Moon: {moon_pos.get('sign', '?')} {moon_pos.get('degree', 0):.1f}° (H{moon_pos.get('house', '?')}) · {moon.get('phase_name', '?')} {moon.get('illumination', '?')}%",
            f"  Ascendant: {asc.get('sign', '?')} {asc.get('degree', 0):.1f}°",
            f"  Aspects: {aspect_lines}",
            f"  {rx_str}Dominant Element: {western.get('dominant_element', '?')}",
            f"  Planetary Hour: {hours.get('current_planetary_hour', '?')}",
            f"  Vedic: Tithi {panchanga.get('tithi', {}).get('name', '?')} · Nakshatra {panchanga.get('nakshatra', {}).get('name', '?')}",
            f"  Chinese: {chinese.get('zodiac_animal', '?')} year · {chinese.get('solar_term', '?')}",
        ]
        return "\n".join(lines)
    except Exception:
        return "(astrology data unavailable)"


def search_rates(query: str, category: str | None = None) -> list[dict]:
    """Search rate databases for a query string."""
    databases = load_rate_database()
    results = []
    query_lower = query.lower()

    targets = {category: databases[category]} if category and category in databases else databases

    for db_name, rates in targets.items():
        for rate in rates:
            # Search name, description, and any text fields
            searchable = " ".join(str(v).lower() for v in rate.values() if isinstance(v, str))
            if query_lower in searchable:
                rate["_source"] = db_name
                results.append(rate)

    return results[:20]  # Limit to avoid context blowup


# ============================================================================
# System prompt builder
# ============================================================================


def build_system_prompt(
    session_state: dict[str, Any] | None = None,
    include_frequencies: bool = True,
    include_mantras: bool = True,
    include_chakras: bool = True,
    include_astrology: bool = True,
) -> str:
    """
    Build the complete system prompt for the RadionicsOperator LLM.

    Args:
        session_state: Optional dict with active session context (rates, GV, RNG, etc.)
        include_frequencies: Include the frequencies reference table
        include_mantras: Include the mantras reference
        include_chakras: Include the chakra correspondence table
        include_astrology: Auto-inject current transit data into the prompt
    """
    freq_ref = build_frequencies_reference() if include_frequencies else "(omitted)"
    mantra_ref = build_mantras_reference() if include_mantras else "(omitted)"
    chakra_ref = build_chakra_reference() if include_chakras else "(omitted)"

    prompt = RADIONICS_OPERATOR_SYSTEM_PROMPT.format(
        frequencies_reference=freq_ref,
        mantras_reference=mantra_ref,
        chakra_reference=chakra_ref,
    )

    # Inject session state if available
    if session_state:
        prompt += "\n\n## Current Session State\n"
        if "intention" in session_state:
            prompt += f"**Intention:** {session_state['intention']}\n"
        if "target" in session_state:
            prompt += f"**Target:** {session_state['target']}\n"
        if "active_rates" in session_state:
            rates = session_state["active_rates"]
            if isinstance(rates, list):
                prompt += f"**Active Rates:** {', '.join(str(r) for r in rates)}\n"
        if "active_frequency" in session_state:
            prompt += f"**Carrier Frequency:** {session_state['active_frequency']} Hz\n"
        if "gv_measurement" in session_state:
            gv = session_state["gv_measurement"]
            prompt += f"**General Vitality:** {gv}/1000\n"
        if "rng_state" in session_state:
            rng = session_state["rng_state"]
            prompt += f"**RNG Needle:** {rng.get('state', 'unknown')} (coherence: {rng.get('coherence', 'N/A')})\n"
        if "scalar_mops" in session_state:
            prompt += f"**Scalar MOPS:** {session_state['scalar_mops']:.2f}M/s\n"
        if "active_chakra" in session_state:
            prompt += f"**Active Chakra:** {session_state['active_chakra']}\n"
        if "duration_remaining" in session_state:
            prompt += f"**Remaining:** {session_state['duration_remaining']}s\n"
        if "planetary_context" in session_state:
            prompt += f"**Planetary:** {session_state['planetary_context']}\n"

    # Auto-inject current astrology
    if include_astrology:
        try:
            astro_summary = format_astrology_for_llm()
            prompt += f"\n\n## {astro_summary}"
        except Exception:
            pass

    return prompt


def build_intention_analysis_prompt(intention: str) -> str:
    """Build a prompt for analyzing a user's intention into structured components."""
    return f"""Analyze this radionics intention and return a structured JSON analysis:

Intention: "{intention}"

Return ONLY a JSON object with these fields:
{{
    "target": "who/what the intention is for",
    "condition": "the condition or desired outcome (e.g., healing, peace, clarity)",
    "primary_system": "affected bodily/energetic system (e.g., nervous, cardiovascular, emotional, spiritual)",
    "primary_chakra": "most relevant chakra (muladhara, svadhisthana, manipura, anahata, vishuddha, ajna, sahasrara)",
    "recommended_frequency": "recommended Solfeggio or planetary Hz value as a number",
    "recommended_mantra_tradition": "one of: compassion, medicine_buddha, tara, vajrasattva, peace, universal",
    "severity": "perceived severity 1-10",
    "modalities": ["list of recommended healing modalities"],
    "explanation": "one-sentence reasoning"
}}"""


def build_rate_suggestion_prompt(intention: str, num_rates: int = 5) -> str:
    """Build a prompt for suggesting radionics rates for an intention."""
    rate_db_summary = _build_rate_db_summary()
    return f"""Based on this radionics intention: "{intention}"

And this rate database summary:
{rate_db_summary}

Suggest {num_rates} radionics rates (3-dial values, each 0-100) that would be most effective.
For each rate, explain briefly why it was chosen (which organ, chakra, or condition it addresses).

Return a JSON array:
[{{"values": [dial1, dial2, dial3], "name": "rate name", "reasoning": "why chosen"}}]"""


def _build_rate_db_summary() -> str:
    """Build a compact summary of the rate database for LLM context."""
    databases = load_rate_database()
    lines = []
    for db_name, rates in databases.items():
        lines.append(f"\n**{db_name.replace('_', ' ').title()}** ({len(rates)} rates):")
        for rate in rates[:15]:  # Top 15 per category
            name = rate.get("name", rate.get("id", "unnamed"))
            values = rate.get("values", rate.get("rate", "N/A"))
            if isinstance(values, list):
                values = "-".join(str(v) for v in values)
            desc = rate.get("description", rate.get("condition", ""))
            if desc:
                lines.append(f"  - {name}: {values} — {str(desc)[:80]}")
            else:
                lines.append(f"  - {name}: {values}")
    return "\n".join(lines)


class SessionContext:
    """Tracks the current session state for injection into the LLM context."""

    def __init__(self):
        self.intention: str = ""
        self.target: str = ""
        self.active_rates: list[Any] = []
        self.active_frequency: float = 528.0
        self.gv_measurement: float = 0.0
        self.rng_state: dict[str, Any] = {}
        self.scalar_mops: float = 0.0
        self.active_chakra: str = ""
        self.duration_remaining: int = 0
        self.planetary_context: str = ""
        self.created_at: datetime = datetime.now()
        self.history: list[dict[str, Any]] = []

    def update(self, **kwargs):
        """Update session fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """Export session state as a dict for the prompt builder."""
        d = {}
        if self.intention:
            d["intention"] = self.intention
        if self.target:
            d["target"] = self.target
        if self.active_rates:
            d["active_rates"] = self.active_rates
        if self.active_frequency:
            d["active_frequency"] = self.active_frequency
        if self.gv_measurement:
            d["gv_measurement"] = self.gv_measurement
        if self.rng_state:
            d["rng_state"] = self.rng_state
        if self.scalar_mops:
            d["scalar_mops"] = self.scalar_mops
        if self.active_chakra:
            d["active_chakra"] = self.active_chakra
        if self.duration_remaining:
            d["duration_remaining"] = self.duration_remaining
        if self.planetary_context:
            d["planetary_context"] = self.planetary_context
        return d

    def record_event(self, event_type: str, data: dict[str, Any]):
        """Record an event in session history."""
        self.history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "data": data,
            }
        )
        # Keep history bounded
        if len(self.history) > 100:
            self.history = self.history[-50:]
