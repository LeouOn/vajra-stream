# core/context/anatomy.py
"""Anatomy context module — chakras and meridians."""

from __future__ import annotations

import logging

from core.context.models import ContextData, ContextRequest

logger = logging.getLogger(__name__)


class AnatomyContextModule:
    """Gathers and renders subtle-body / energetic-anatomy context."""

    name = "anatomy"

    async def gather(self, request: ContextRequest) -> ContextData:
        """Collect chakra + meridian data, never raising."""
        if not request.include_anatomy:
            return ContextData(module_name=self.name)

        try:
            from modules.personal_healing import PersonalHealingModule

            phm = PersonalHealingModule()
        except Exception as exc:  # noqa: BLE001
            logger.debug("PersonalHealingModule import failed: %s", exc)
            return ContextData(
                module_name=self.name,
                error="PersonalHealingModule unavailable",
            )

        try:
            chakras = {}
            for chakra_name, info in phm.chakra_data.items():
                # Normalize the root-chakra " crystals" typo defensively.
                crystals = info.get("crystals") or info.get(" crystals") or []
                chakras[chakra_name] = {
                    "name": info.get("name", chakra_name),
                    "sanskrit": info.get("sanskrit", ""),
                    "governs": info.get("governs", ""),
                    "frequencies": info.get("frequencies", {}),
                    "crystals": crystals,
                    "affirmations": info.get("affirmations", []),
                }

            meridians = {}
            for m_name, info in phm.meridian_data.items():
                meridians[m_name] = {
                    "element": info.get("element", ""),
                    "emotion": info.get("emotion", ""),
                    "frequency": info.get("frequency", 0),
                    "color": info.get("color", ""),
                }

            return ContextData(
                module_name=self.name,
                data={"chakras": chakras, "meridians": meridians},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("anatomy gather failed: %s", exc)
            return ContextData(module_name=self.name, error=str(exc))

    def render(self, data: ContextData) -> str:
        """Render chakra and meridian Markdown."""
        d = data.data
        if not d:
            return ""
        lines: list[str] = ["### Subtle Body & Energetic Anatomy", ""]

        try:
            self._render_chakras(d, lines)
            self._render_meridians(d, lines)
        except Exception as exc:  # noqa: BLE001
            logger.warning("anatomy render failed: %s", exc)
            return ""

        if len(lines) <= 2:
            return ""
        return "\n".join(lines) + "\n"

    # -- render helpers -----------------------------------------------------

    @staticmethod
    def _render_chakras(d: dict, lines: list[str]) -> None:
        chakras = d.get("chakras")
        if not chakras:
            return
        lines.append("**Chakras:**")
        for chakra_name, info in chakras.items():
            name = info.get("name", chakra_name)
            sanskrit = info.get("sanskrit", "")
            governs = info.get("governs", "")
            label = f"{name} ({sanskrit})" if sanskrit else name
            lines.append(f"  - **{label}** — {governs}")
            freqs = info.get("frequencies", {})
            if freqs:
                freq_vals = list(freqs.values())[:3]
                lines.append(f"    Frequencies: {', '.join(str(f) for f in freq_vals)} Hz")
            crystals = info.get("crystals", [])
            if crystals:
                lines.append(f"    Crystals: {', '.join(crystals)}")
            affirmations = info.get("affirmations", [])
            if affirmations:
                lines.append(f'    Affirmation: "{affirmations[0]}"')
        lines.append("")

    @staticmethod
    def _render_meridians(d: dict, lines: list[str]) -> None:
        meridians = d.get("meridians")
        if not meridians:
            return
        lines.append("**Meridians (12):**")
        for m_name, info in meridians.items():
            element = info.get("element", "—")
            emotion = info.get("emotion", "—")
            freq = info.get("frequency", 0)
            label = m_name.replace("_", " ").title()
            lines.append(f"  - {label} ({element}) — {emotion}, {freq} Hz")
        lines.append("")
