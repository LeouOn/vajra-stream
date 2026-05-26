"""
Internet Context Pipeline
Fetches real-world context for the RadionicsOperator — current events,
humanitarian crises, astrological transits, and global sentiment.

The compiled context is injected into the LLM's system prompt so the operator
can make radionics decisions informed by what's happening in the world.

Data sources (all free, no API keys required):
- GDACS RSS — global disaster alerts (earthquakes, floods, cyclones)
- ReliefWeb RSS — humanitarian crises
- Local astrology service — planetary transits and timing
- Optional: NewsAPI / RSS feeds for current events
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


@dataclass
class WorldEvent:
    """A significant world event that might warrant radionics attention."""

    title: str
    description: str
    location: str = ""
    event_type: str = "general"  # disaster, conflict, humanitarian, celestial
    severity: str = "medium"  # low, medium, high, critical
    source: str = ""
    date: str = ""
    url: str = ""

    def to_context_str(self) -> str:
        return f"[{self.event_type.upper()}|{self.severity}] {self.title} — {self.description[:120]} (Location: {self.location})"


@dataclass
class InternetContext:
    """Compiled world context for LLM injection."""

    events: list[WorldEvent] = field(default_factory=list)
    disasters: list[dict[str, Any]] = field(default_factory=list)
    astro_transits: dict[str, Any] = field(default_factory=dict)
    planetary_hour: str = ""
    day_ruler: str = ""
    fetched_at: str = ""
    summary: str = ""

    def to_prompt_context(self) -> str:
        """Format as a compact system prompt section."""
        if not self.events and not self.astro_transits:
            return ""

        lines = ["\n## Current World Context (auto-updated)\n"]

        if self.astro_transits:
            lines.append("### Celestial Timing")
            lines.append(f"- Planetary Hour: {self.planetary_hour}")
            lines.append(f"- Day Ruler: {self.day_ruler}")
            moon = self.astro_transits.get("moon_phase", {})
            if moon:
                lines.append(
                    f"- Moon: {moon.get('phase_name', 'unknown')} ({moon.get('illumination', '?')}% illuminated)"
                )
            lines.append("")

        if self.events:
            lines.append(f"### Active World Events ({len(self.events)} significant)")
            for evt in self.events[:10]:
                lines.append(f"- {evt.to_context_str()}")
            lines.append("")

        if self.disasters:
            lines.append(f"### Active Disasters ({len(self.disasters)})")
            for d in self.disasters[:8]:
                name = d.get("title", d.get("name", "Unknown"))
                loc = d.get("location", d.get("country", ""))
                sev = d.get("severity", "medium")
                lines.append(f"- [{sev.upper()}] {name} — {loc}")
            lines.append("")

        if self.summary:
            lines.append(f"### Summary\n{self.summary}\n")

        return "\n".join(lines)


# ============================================================================
# Fetchers
# ============================================================================


def _safe_http_get(url: str, timeout: float = 10.0) -> str | None:
    """Fetch a URL, returning None on any error."""
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "VajraStream/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug(f"HTTP fetch failed for {url}: {e}")
        return None


def fetch_gdacs_disasters() -> list[dict[str, Any]]:
    """
    Fetch active disaster alerts from GDACS (Global Disaster Alert and Coordination System).
    Free RSS feed, no API key required.
    """
    url = "https://www.gdacs.org/xml/rss.xml"
    xml_str = _safe_http_get(url, timeout=15.0)
    if not xml_str:
        return []

    disasters = []
    try:
        root = ElementTree.fromstring(xml_str)
        for item in root.iter("item"):
            title = ""
            description = ""
            for child in item:
                if child.tag == "title":
                    title = (child.text or "").strip()
                elif child.tag == "description":
                    description = (child.text or "").strip()

            if title:
                # Parse severity from title
                severity = "medium"
                title_lower = title.lower()
                if "red" in title_lower:
                    severity = "critical"
                elif "orange" in title_lower:
                    severity = "high"
                elif "green" in title_lower:
                    severity = "low"

                disasters.append(
                    {
                        "title": title,
                        "description": description[:200] if description else "",
                        "severity": severity,
                        "source": "GDACS",
                    }
                )
    except ElementTree.ParseError:
        pass

    return disasters[:15]


def fetch_reliefweb_headlines() -> list[dict[str, Any]]:
    """Fetch humanitarian headlines from ReliefWeb RSS."""
    url = "https://reliefweb.int/updates/rss"
    xml_str = _safe_http_get(url, timeout=15.0)
    if not xml_str:
        return []

    headlines = []
    try:
        root = ElementTree.fromstring(xml_str)
        for item in root.iter("item"):
            title = ""
            description = ""
            for child in item:
                if child.tag == "title":
                    title = (child.text or "").strip()
                elif child.tag == "description":
                    description = (child.text or "").strip()

            if title:
                headlines.append(
                    {
                        "title": title,
                        "description": description[:200] if description else "",
                        "source": "ReliefWeb",
                    }
                )
    except ElementTree.ParseError:
        pass

    return headlines[:10]


def fetch_astro_context() -> dict[str, Any]:
    """Get current astrological context from local astrology service."""
    try:
        from core.astrology import AstrologyEngine

        engine = AstrologyEngine()
        now = datetime.now()

        transits = engine.get_transits()
        moon = engine.get_moon_phase(now)
        positions = engine.get_planetary_positions(now)

        return {
            "moon_phase": moon,
            "transits": transits,
            "positions": positions,
        }
    except Exception as e:
        logger.debug(f"Astrology context fetch failed: {e}")
        return {}


def get_planetary_hour() -> tuple[str, str]:
    """Get current planetary hour and day ruler (simplified)."""
    now = datetime.now()
    weekday = now.weekday()  # 0=Mon, 6=Sun

    day_rulers = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
    day_ruler = day_rulers[weekday]

    # Simplified planetary hour — just the day ruler for now
    hour_names = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
    hour_index = (now.hour // 3) % 7  # Crude but functional
    planetary_hour = hour_names[hour_index]

    return planetary_hour, day_ruler


# ============================================================================
# Context Compiler
# ============================================================================


def compile_world_context(
    include_disasters: bool = True,
    include_headlines: bool = True,
    include_astrology: bool = True,
) -> InternetContext:
    """
    Compile a complete world context snapshot for LLM injection.

    Fetches disaster alerts, humanitarian headlines, and astrological transits.
    Each source fails gracefully — the context is built from whatever succeeds.
    """
    context = InternetContext()
    events: list[WorldEvent] = []

    # Disasters (GDACS)
    if include_disasters:
        try:
            disasters = fetch_gdacs_disasters()
            context.disasters = disasters
            for d in disasters:
                events.append(
                    WorldEvent(
                        title=d.get("title", ""),
                        description=d.get("description", ""),
                        event_type="disaster",
                        severity=d.get("severity", "medium"),
                        source=d.get("source", "GDACS"),
                    )
                )
        except Exception as e:
            logger.debug(f"GDACS fetch failed: {e}")

    # ReliefWeb headlines
    if include_headlines:
        try:
            headlines = fetch_reliefweb_headlines()
            for h in headlines:
                events.append(
                    WorldEvent(
                        title=h.get("title", ""),
                        description=h.get("description", ""),
                        event_type="humanitarian",
                        severity="medium",
                        source=h.get("source", "ReliefWeb"),
                    )
                )
        except Exception as e:
            logger.debug(f"ReliefWeb fetch failed: {e}")

    # Astrology
    if include_astrology:
        try:
            context.astro_transits = fetch_astro_context()
        except Exception as e:
            logger.debug(f"Astrology fetch failed: {e}")

    # Planetary hour
    try:
        hour, ruler = get_planetary_hour()
        context.planetary_hour = hour
        context.day_ruler = ruler
    except Exception:
        pass

    context.events = events
    context.fetched_at = datetime.now().isoformat()

    # Generate summary
    if events:
        disaster_count = sum(1 for e in events if e.event_type == "disaster")
        humanitarian_count = sum(1 for e in events if e.event_type == "humanitarian")
        critical = sum(1 for e in events if e.severity == "critical")
        context.summary = (
            f"{len(events)} significant world events detected: "
            f"{disaster_count} disasters, {humanitarian_count} humanitarian crises. "
            f"{critical} critical alerts. "
            f"Planetary hour: {context.planetary_hour}, Day ruler: {context.day_ruler}."
        )

    return context


def format_context_for_llm(context: InternetContext, max_events: int = 12) -> str:
    """Format context as a compact string for LLM system prompt injection."""
    return context.to_prompt_context()
