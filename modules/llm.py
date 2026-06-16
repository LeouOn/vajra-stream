"""
LLM Integration Module
Wraps :class:`LegacyLLMIntegration` and :class:`LegacyDharmaLLM` for
AI-powered content generation (prayers, teachings, meditations, etc.).
"""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus

# Depth → length mapping for ``generate_teaching``.
_DEPTH_TO_LENGTH: dict[str, str] = {
    "shallow": "short",
    "moderate": "medium",
    "deep": "long",
}


class LLMService:
    """LLM integration service for AI-powered content.

    The service lazily constructs two adapters from
    :mod:`core.llm.legacy_adapter`:

    - ``LegacyLLMIntegration`` — generic ``generate(prompt, ...)`` for
      free-form prompts (intention analysis, affirmations, custom
      meditation scripts).
    - ``LegacyDharmaLLM`` — curated dharma prompts for prayer,
      teaching, and meditation-instruction generation.
    """

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._llm: Any = None       # LegacyLLMIntegration for generate()
        self._dharma: Any = None    # LegacyDharmaLLM for prayer/teaching/meditation

    # ------------------------------------------------------------------
    # Lazy adapter construction
    # ------------------------------------------------------------------

    @property
    def llm(self) -> Any:
        """Lazily build and return the :class:`LegacyLLMIntegration`.

        As a side effect this also constructs the paired
        :class:`LegacyDharmaLLM` (sharing the same provider registry)
        and stores it on ``self._dharma``. Returns ``None`` if the
        adapters cannot be constructed (e.g. no providers configured).
        """
        if self._llm is None:
            try:
                from core.llm.legacy_adapter import (
                    LegacyDharmaLLM,
                    LegacyLLMIntegration,
                )

                self._llm = LegacyLLMIntegration()
                # Share the same registry so both adapters use the same
                # providers / connection pool.
                self._dharma = LegacyDharmaLLM(self._llm._registry)
            except Exception:
                # Any failure (import error, no providers, missing API
                # keys) leaves the service in an "unavailable" state;
                # callers get ``{"error": "LLM not available"}``.
                self._llm = None
                self._dharma = None
        return self._llm

    @property
    def dharma(self) -> Any:
        """Lazily ensure ``self._dharma`` is populated (tiggers ``llm``)."""
        if self._dharma is None and self.llm is None:
            return None
        return self._dharma

    # ------------------------------------------------------------------
    # Content generation methods
    # ------------------------------------------------------------------

    def generate_prayer(
        self,
        intention: str,
        tradition: str = "universal",
        length: str = "medium",
    ) -> dict[str, Any]:
        """Generate a prayer / aspiration.

        ``length`` is accepted for API compatibility but the underlying
        :meth:`LegacyDharmaLLM.generate_prayer` does not parameterise
        length, so it is intentionally ignored.
        """
        dharma = self.dharma
        if dharma is None:
            return {"error": "LLM not available"}

        try:
            prayer = dharma.generate_prayer(intention, tradition)
            return {
                "status": "success",
                "prayer": prayer,
                "intention": intention,
                "tradition": tradition,
            }
        except Exception as e:
            return {"error": str(e)}

    def generate_teaching(
        self,
        topic: str,
        tradition: str = "buddhist",
        depth: str = "moderate",
    ) -> dict[str, Any]:
        """Generate a dharma teaching.

        ``depth`` is mapped to a ``length`` for
        :meth:`LegacyDharmaLLM.generate_teaching`:

        - ``"shallow"``  → ``"short"``
        - ``"moderate"`` → ``"medium"``
        - ``"deep"``     → ``"long"``

        ``tradition`` is accepted for API compatibility but the
        underlying generator does not parameterise tradition, so it is
        intentionally ignored.
        """
        dharma = self.dharma
        if dharma is None:
            return {"error": "LLM not available"}

        try:
            length = _DEPTH_TO_LENGTH.get(depth, "medium")
            teaching = dharma.generate_teaching(topic, length)
            return {
                "status": "success",
                "teaching": teaching,
                "topic": topic,
                "tradition": tradition,
            }
        except Exception as e:
            return {"error": str(e)}

    def generate_meditation_script(
        self,
        meditation_type: str,
        duration_minutes: int = 20,
        experience_level: str = "beginner",
    ) -> dict[str, Any]:
        """Generate a guided meditation script.

        Builds a tailored system prompt from ``duration_minutes`` and
        ``experience_level`` and delegates the free-form generation to
        :meth:`LegacyLLMIntegration.generate`.
        """
        llm = self.llm
        if llm is None:
            return {"error": "LLM not available"}

        try:
            system_prompt = (
                "You are an experienced meditation guide. Tailor the "
                "script to the practitioner's experience level and the "
                f"requested duration. Experience level: {experience_level}. "
                f"Target duration: {duration_minutes} minutes. Pace the "
                "script — include pauses — so it can actually be read "
                "aloud within that duration."
            )
            prompt = (
                f"Write a guided meditation script for the practice: "
                f"{meditation_type}."
            )
            script = llm.generate(
                prompt,
                system_prompt=system_prompt,
                max_tokens=1200,
                temperature=0.7,
            )
            return {
                "status": "success",
                "script": script,
                "type": meditation_type,
                "duration_minutes": duration_minutes,
            }
        except Exception as e:
            return {"error": str(e)}

    def analyze_intention(self, text: str) -> dict[str, Any]:
        """Analyze the spiritual intention expressed in ``text``."""
        llm = self.llm
        if llm is None:
            return {"error": "LLM not available"}

        try:
            prompt = (
                "Analyze the spiritual intention in this text. Identify "
                "the core desire, the emotional tone, and any hidden "
                f"motivations. Text: {text}"
            )
            analysis = llm.generate(prompt, temperature=0.5)
            return {
                "status": "success",
                "analysis": analysis,
                "text_length": len(text),
            }
        except Exception as e:
            return {"error": str(e)}

    def generate_affirmations(
        self, intention: str, count: int = 7
    ) -> dict[str, Any]:
        """Generate ``count`` positive affirmations for ``intention``."""
        llm = self.llm
        if llm is None:
            return {"error": "LLM not available"}

        try:
            prompt = (
                f"Generate {count} positive affirmations for the "
                f"intention: {intention}. Format as a numbered list."
            )
            raw = llm.generate(prompt, temperature=0.8)
            affirmations = _parse_numbered_list(raw)
            return {
                "status": "success",
                "affirmations": affirmations,
                "intention": intention,
                "count": len(affirmations),
            }
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Get LLM service status."""
        available = self.llm is not None
        return {
            "llm_available": available,
            "capabilities": [
                "prayer_generation",
                "teaching_generation",
                "meditation_scripts",
                "intention_analysis",
                "affirmations",
            ]
            if available
            else [],
        }


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

# Matches a leading list marker: "1.", "1)", "-", "*", "•" plus space.
_LIST_MARKER_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s*")


def _parse_numbered_list(text: str) -> list[str]:
    """Parse a numbered/bulleted text block into a list of items.

    Tolerant of ``"1."``, ``"1)"``, ``"-"``, ``"*"``, ``"•"`` prefixes
    and surrounding blank lines. Non-blank lines without a marker are
    kept verbatim (so an unnumbered multi-line answer still yields
    useful output).
    """
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        items.append(_LIST_MARKER_RE.sub("", stripped, count=1))
    return items
