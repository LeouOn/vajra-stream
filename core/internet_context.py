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

from core.situation_geometry import DEFAULT_COORDS

logger = logging.getLogger(__name__)


@dataclass
class WorldEvent:
    """A significant world event that might warrant radionics attention."""

    title: str
    description: str
    location: str = ""
    country: str = ""
    lat: float | None = None
    lon: float | None = None
    event_type: str = "general"  # disaster, conflict, humanitarian, celestial
    severity: str = "medium"  # low, medium, high, critical
    source: str = ""
    date: str = ""
    url: str = ""

    def to_context_str(self) -> str:
        loc_str = self.location or self.country or "Global"
        coord_str = f" ({self.lat:.2f}, {self.lon:.2f})" if self.lat is not None and self.lon is not None else ""
        return f"[{self.event_type.upper()}|{self.severity}] {self.title} — {self.description[:120]} (Location: {loc_str}{coord_str})"


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
                coord_str = (
                    f" [{d['lat']:.2f}, {d['lon']:.2f}]"
                    if d.get("lat") is not None and d.get("lon") is not None
                    else ""
                )
                lines.append(f"- [{sev.upper()}] {name} — {loc}{coord_str}")
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


def _find_element_text(item: ElementTree.Element, *tag_names: str) -> str:
    """Find text of a child element matching any tag name, ignoring XML namespaces."""
    target_names = {t.lower() for t in tag_names}
    for child in item:
        local_name = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()
        if local_name in target_names and child.text:
            return child.text.strip()
        for sub in child:
            sub_local = sub.tag.split("}")[-1].lower() if "}" in sub.tag else sub.tag.lower()
            if sub_local in target_names and sub.text:
                return sub.text.strip()
    return ""


def fetch_gdacs_disasters() -> list[dict[str, Any]]:
    """
    Fetch active disaster alerts from GDACS (Global Disaster Alert and Coordination System).
    Free RSS feed, no API key required. Parses coordinates, country, and severity.
    """
    url = "https://www.gdacs.org/xml/rss.xml"
    xml_str = _safe_http_get(url, timeout=15.0)
    if not xml_str:
        return []

    disasters = []
    try:
        root = ElementTree.fromstring(xml_str)
        for item in root.iter("item"):
            title = _find_element_text(item, "title")
            description = _find_element_text(item, "description")
            country = _find_element_text(item, "country")
            event_name = _find_element_text(item, "eventname")
            event_type = _find_element_text(item, "eventtype")
            severity_tag = _find_element_text(item, "severity", "alertlevel")
            lat_str = _find_element_text(item, "lat", "latitude", "point_lat")
            lon_str = _find_element_text(item, "long", "lon", "longitude", "point_long")
            link = _find_element_text(item, "link")
            pub_date = _find_element_text(item, "pubdate")

            if title:
                # Parse severity
                severity = "medium"
                title_lower = title.lower()
                sev_lower = severity_tag.lower()
                if "red" in title_lower or "red" in sev_lower or "critical" in sev_lower:
                    severity = "critical"
                elif "orange" in title_lower or "orange" in sev_lower or "high" in sev_lower:
                    severity = "high"
                elif "green" in title_lower or "green" in sev_lower or "low" in sev_lower:
                    severity = "low"

                # Parse coordinates
                lat: float | None = None
                lon: float | None = None
                if lat_str and lon_str:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                    except ValueError:
                        pass

                location = country or event_name or ""

                disasters.append(
                    {
                        "title": title,
                        "description": description[:200] if description else "",
                        "location": location,
                        "country": country,
                        "event_name": event_name,
                        "event_type": event_type or "disaster",
                        "severity": severity,
                        "lat": lat,
                        "lon": lon,
                        "url": link,
                        "date": pub_date,
                        "source": "GDACS",
                    }
                )
    except ElementTree.ParseError:
        pass

    return disasters[:15]


def fetch_reliefweb_headlines() -> list[dict[str, Any]]:
    """Fetch humanitarian headlines from ReliefWeb RSS with location/country metadata."""
    url = "https://reliefweb.int/updates/rss"
    xml_str = _safe_http_get(url, timeout=15.0)
    if not xml_str:
        return []

    headlines = []
    try:
        root = ElementTree.fromstring(xml_str)
        for item in root.iter("item"):
            title = _find_element_text(item, "title")
            description = _find_element_text(item, "description")
            category = _find_element_text(item, "category")
            link = _find_element_text(item, "link")
            pub_date = _find_element_text(item, "pubdate")

            if title:
                headlines.append(
                    {
                        "title": title,
                        "description": description[:200] if description else "",
                        "location": category,
                        "country": category,
                        "url": link,
                        "date": pub_date,
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


def get_planetary_hour(
    dt: datetime | None = None,
    coords: tuple[float, float] | None = None,
) -> tuple[str, str]:
    """
    Get current planetary hour and day ruler using exact Swiss Ephemeris or Chaldean rotation.
    """
    now = dt or datetime.now()
    location = coords or DEFAULT_COORDS

    try:
        from core.astrology import AstrologyEngine

        engine = AstrologyEngine()
        res = engine.calculate_exact_planetary_hours(now, location)
        current_hour = res.get("current_planetary_hour")
        if current_hour:
            weekday = now.weekday()
            day_rulers = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
            day_ruler = day_rulers[weekday]
            return current_hour, day_ruler
    except Exception as e:
        logger.debug(f"Exact planetary hour calculation fallback to Chaldean rotation: {e}")

    # Standard Chaldean planetary hour rotation fallback
    # Weekday rulers: Monday(0)=Moon, Tuesday(1)=Mars, Wednesday(2)=Mercury,
    # Thursday(3)=Jupiter, Friday(4)=Venus, Saturday(5)=Saturn, Sunday(6)=Sun
    weekday_rulers = {
        0: "Moon",
        1: "Mars",
        2: "Mercury",
        3: "Jupiter",
        4: "Venus",
        5: "Saturn",
        6: "Sun",
    }
    day_ruler = weekday_rulers.get(now.weekday(), "Sun")

    # Chaldean order from slowest to fastest celestial sphere:
    chaldean_order = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
    day_ruler_idx = chaldean_order.index(day_ruler)
    # Hour 1 begins around sunrise (~6:00 AM)
    sunrise_offset_hour = (now.hour - 6) % 24
    hour_planet_idx = (day_ruler_idx + sunrise_offset_hour) % 7
    planetary_hour = chaldean_order[hour_planet_idx]

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
                        location=d.get("location", d.get("country", "")),
                        country=d.get("country", ""),
                        lat=d.get("lat"),
                        lon=d.get("lon"),
                        event_type="disaster",
                        severity=d.get("severity", "medium"),
                        source=d.get("source", "GDACS"),
                        url=d.get("url", ""),
                        date=d.get("date", ""),
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
                        location=h.get("location", h.get("country", "")),
                        country=h.get("country", ""),
                        event_type="humanitarian",
                        severity="medium",
                        source=h.get("source", "ReliefWeb"),
                        url=h.get("url", ""),
                        date=h.get("date", ""),
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
