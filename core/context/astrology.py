# core/context/astrology.py
"""Astrology context module — Western / Vedic / Chinese sections."""
from __future__ import annotations

import logging

from core.context.models import ContextData, ContextRequest

logger = logging.getLogger(__name__)


class AstrologyContextModule:
    """Gathers and renders astrological context (Western, Vedic, BaZi)."""

    name = "astrology"

    async def gather(self, request: ContextRequest) -> ContextData:
        """Collect astrology data, never raising."""
        if not request.include_astrology:
            return ContextData(module_name=self.name)

        # Pre-computed data wins.
        if request.astrology_data:
            return ContextData(module_name=self.name, data=request.astrology_data)

        data: dict | None = None

        # Path 1: vajra_service singleton (async, enriched dict).
        try:
            from backend.core.services.vajra_service import vajra_service

            data = await vajra_service._get_astrology_data()
        except Exception as exc:  # noqa: BLE001
            logger.debug("vajra_service astrology path failed: %s", exc)

        # Path 2: AstrologicalCalculator directly (sync).
        if not data:
            try:
                from core.astrology import AstrologicalCalculator

                calc = AstrologicalCalculator()
                data = calc.get_comprehensive_astrology()
            except Exception as exc:  # noqa: BLE001
                logger.debug("AstrologicalCalculator path failed: %s", exc)

        if not data:
            return ContextData(
                module_name=self.name,
                error="Astrology data unavailable (swisseph/deps missing or calculation failed)",
            )
        return ContextData(module_name=self.name, data=data)

    def render(self, data: ContextData) -> str:
        """Render the three-section astrology Markdown."""
        d = data.data
        if not d:
            return ""
        lines: list[str] = ["### Astrological Context", ""]

        try:
            self._render_planetary_hour(d, lines)
            self._render_western(d, lines)
            self._render_vedic(d, lines)
            self._render_chinese(d, lines)
        except Exception as exc:  # noqa: BLE001
            logger.warning("astrology render failed: %s", exc)
            return ""

        if len(lines) <= 2:
            return ""
        return "\n".join(lines) + "\n"

    # -- render helpers -----------------------------------------------------

    @staticmethod
    def _render_planetary_hour(d: dict, lines: list[str]) -> None:
        ph = d.get("planetary_hours") or {}
        if not ph and (d.get("planetary_hour") or d.get("day_planet")):
            ph = {
                "current_planetary_hour": d.get("planetary_hour"),
                "day_planet": d.get("day_planet"),
                "day_of_week": d.get("day_of_week"),
            }
        if ph:
            hour = ph.get("current_planetary_hour", "—")
            day_planet = ph.get("day_planet", "—")
            lines.append(f"**Planetary Hour:** {hour} (Day Ruler: {day_planet})")
            lines.append("")

    @staticmethod
    def _render_western(d: dict, lines: list[str]) -> None:
        western = d.get("western")
        if not western:
            return
        lines.append("**Western Tropical Astrology:**")
        positions = western.get("positions", {})
        for planet in ("sun", "moon", "ascendant", "mercury", "venus", "mars"):
            info = positions.get(planet)
            if not info:
                continue
            sign = info.get("sign", "—")
            degree = info.get("degree", "—")
            lines.append(f"  - {planet.title()} in {sign} ({degree}°)")
        dom_el = western.get("dominant_element")
        if dom_el:
            lines.append(f"  - Dominant element: **{dom_el}**")
        lines.append("")

    @staticmethod
    def _render_vedic(d: dict, lines: list[str]) -> None:
        indian = d.get("indian")
        if not indian:
            return
        lines.append("**Vedic / Panchanga:**")
        panchanga = indian.get("panchanga", {})
        for key in ("tithi", "nakshatra", "yoga", "vara"):
            info = panchanga.get(key, {})
            if isinstance(info, dict) and info.get("name"):
                lines.append(f"  - {key.title()}: {info['name']}")
        ayanamsa = indian.get("ayanamsa")
        if ayanamsa is not None:
            lines.append(f"  - Ayanamsa: {ayanamsa:.4f}°")
        lines.append("")

    @staticmethod
    def _render_chinese(d: dict, lines: list[str]) -> None:
        chinese = d.get("chinese")
        if not chinese:
            return
        lines.append("**Chinese / BaZi:**")
        animal = chinese.get("zodiac_animal")
        if animal:
            lines.append(f"  - Zodiac: {animal}")
        lunar = chinese.get("lunar_date", {})
        formatted = lunar.get("formatted") if isinstance(lunar, dict) else None
        if formatted:
            lines.append(f"  - Lunar date: {formatted}")
        bazi = chinese.get("bazi", {})
        for pillar in ("year", "month", "day", "hour"):
            val = bazi.get(pillar)
            if val:
                lines.append(f"  - {pillar.title()} pillar: {val}")
        lines.append("")
