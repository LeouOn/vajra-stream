# core/llm/healing.py
"""Async multi-turn LLM service for the healing dialogue.

:class:`AsyncHealingDialogue` wraps a :class:`~core.llm.registry.ProviderRegistry`
and exposes :meth:`respond` for advancing a multi-turn healing dialogue one
turn at a time.

Unlike :class:`~core.llm.dharma.AsyncDharmaLLM` (which takes a single prompt
string per call), this service accepts the **full conversation history** as a
``list[dict]`` of ``{"role", "content"}`` messages, builds the phase-aware
system prompt via :func:`~core.healing_dialogue.build_system_prompt`, asks the
registry for the best healthy provider, calls ``provider.generate(...)``, and
returns a structured dict with the response text plus a phase-transition hint
and any extracted insight updates.

Usage::

    from core.llm.bootstrap import build_default_registry
    from core.llm.healing import AsyncHealingDialogue
    from core.healing_dialogue import DialoguePhase

    registry = build_default_registry()
    dialogue = AsyncHealingDialogue(registry)
    result = await dialogue.respond(
        messages=[{"role": "user", "content": "I lost everything in the market today."}],
        phase=DialoguePhase.ARRIVAL,
        insights={},
    )
    print(result["content"])
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.healing_dialogue.phases import DialoguePhase
from core.healing_dialogue.prompts import build_system_prompt
from core.llm.models import ChatMessage, ChatRequest
from core.llm.registry import ProviderRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase-transition cue detection.
# ---------------------------------------------------------------------------
# Phrases the LLM might use when offering to move to the next phase. Matched
# case-insensitively against the assistant response. Each list is tied to the
# phase the cue would *leave* (i.e. the phase the session is currently in).
# The hint is the NEXT phase, per the arc ARRIVAL → SEEING → MEETING →
# RELEASE → DEDICATION → COMPLETED.
_TRANSITION_CUES: dict[DialoguePhase, tuple[tuple[str, DialoguePhase], ...]] = {
    DialoguePhase.ARRIVAL: (
        ("shall we see what the stars", DialoguePhase.SEEING),
        ("shall we explore the chart", DialoguePhase.SEEING),
        ("explore what the stars say", DialoguePhase.SEEING),
        ("look at the chart", DialoguePhase.SEEING),
        ("seeing phase", DialoguePhase.SEEING),
        ("why did this happen", DialoguePhase.SEEING),
        ("cosmic weather", DialoguePhase.SEEING),
        ("ready to move to seeing", DialoguePhase.SEEING),
    ),
    DialoguePhase.SEEING: (
        ("sit with this", DialoguePhase.MEETING),
        ("meeting phase", DialoguePhase.MEETING),
        ("stay with what", DialoguePhase.MEETING),
        ("meet what", DialoguePhase.MEETING),
        ("ready to meet", DialoguePhase.MEETING),
        ("sit with the", DialoguePhase.MEETING),
    ),
    DialoguePhase.MEETING: (
        ("offer a practice", DialoguePhase.RELEASE),
        ("release phase", DialoguePhase.RELEASE),
        ("a practice i can offer", DialoguePhase.RELEASE),
        ("one practice", DialoguePhase.RELEASE),
        ("ready for a practice", DialoguePhase.RELEASE),
        ("something has shifted", DialoguePhase.RELEASE),
        ("something moved", DialoguePhase.RELEASE),
        ("spaciousness", DialoguePhase.RELEASE),
    ),
    DialoguePhase.RELEASE: (
        ("dedicate", DialoguePhase.DEDICATION),
        ("dedication", DialoguePhase.DEDICATION),
        ("seal the practice", DialoguePhase.DEDICATION),
        ("offer the merit", DialoguePhase.DEDICATION),
        ("dedication phase", DialoguePhase.DEDICATION),
    ),
    DialoguePhase.DEDICATION: (
        ("session is complete", DialoguePhase.COMPLETED),
        ("session is closing", DialoguePhase.COMPLETED),
        ("container is sealed", DialoguePhase.COMPLETED),
        ("practice is sealed", DialoguePhase.COMPLETED),
    ),
}

# Structured hint block: if the LLM emits one of these JSON-ish trailers, it
# wins over keyword detection. Matches the spec's
# ``{"phase_transition": "suggested", "next_phase": "seeing"}`` shape.
_HINT_BLOCK_RE = re.compile(
    r"\{[^{}]*\"phase_transition\"[^{}]*\}",
    re.IGNORECASE | re.DOTALL,
)

# Keywords that signal extraction of new insights from the response.
_EMOTION_KEYWORDS = (
    "grief",
    "fear",
    "anger",
    "sadness",
    "shame",
    "terror",
    "numbness",
    "rage",
    "longing",
    "grief",
    "despair",
    "helplessness",
)
_BODY_KEYWORDS = (
    "chest",
    "throat",
    "gut",
    "belly",
    "root",
    "solar plexus",
    "heart",
    "shoulders",
    "jaw",
    "stomach",
    "pelvis",
    "head",
)


class AsyncHealingDialogue:
    """Multi-turn LLM service for the healing dialogue.

    Wraps a :class:`ProviderRegistry` and exposes :meth:`respond` for one
    dialogue turn. Each call:

    1. Builds the phase-aware system prompt via
       :func:`build_system_prompt`.
    2. Converts the ``list[dict]`` message history to
       :class:`ChatMessage` objects.
    3. Picks the best healthy provider via ``registry.pick_best()``.
    4. Calls ``provider.generate(ChatRequest(...))``.
    5. Parses the response for a structured phase-transition hint (or
       detects one from conversational cues) and extracts any new
       insight keywords (emotions, body locations, themes).
    6. Returns the structured result dict.

    All methods are coroutines and must be ``await``ed.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    async def respond(
        self,
        messages: list[dict],
        phase: DialoguePhase,
        insights: dict | None = None,
        astrology_context: dict | None = None,
        somatic_findings: dict | None = None,
        *,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> dict:
        """Advance the dialogue one turn.

        Args:
            messages: Full conversation history as ``list[dict]`` of
                ``{"role": "user"|"assistant"|"system", "content": str}``.
                The newest message is typically a user turn.
            phase: The current :class:`DialoguePhase`. Used to build the
                phase-specific system prompt.
            insights: Accumulated insights from prior turns (themes,
                emotions, body_locations, chart_findings). Passed into the
                system prompt so the LLM can build on what was already
                surfaced.
            astrology_context: Chart / transit data (typically gathered
                during Seeing). Injected into the prompt when provided.
            somatic_findings: Body-location findings from Seeing/Meeting.
                Injected into the prompt when provided.
            temperature: Sampling temperature (default ``0.7``).
            max_tokens: Cap on response tokens (default ``800``).

        Returns:
            A dict with the keys::

                {
                    "content": str,            # LLM response text
                    "phase_hint": str | None,  # next phase value, or None
                    "insights_update": dict,   # new themes/emotions/body_locations
                }

        Raises:
            RuntimeError: If no healthy provider is available or generation
                fails outright. (Provider retries are handled inside the
                provider, not here.)
        """
        system_prompt = build_system_prompt(
            phase=phase,
            insights=insights,
            astrology_context=astrology_context,
            somatic_findings=somatic_findings,
        )

        chat_messages = self._coerce_messages(messages)
        if not chat_messages:
            raise ValueError("AsyncHealingDialogue.respond requires at least one message")

        provider = await self.registry.pick_best()
        if provider is None:
            raise RuntimeError("No healthy LLM provider available in the registry")

        request = ChatRequest(
            messages=chat_messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        logger.debug(
            "healing dialogue turn: session phase=%s provider=%s msgs=%d",
            phase.value,
            provider.name,
            len(chat_messages),
        )
        response = await provider.generate(request)
        content = response.content or ""

        phase_hint = self._detect_phase_hint(content, phase)
        insights_update = self._extract_insights(content, phase)

        return {
            "content": content,
            "phase_hint": phase_hint,
            "insights_update": insights_update,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_messages(messages: list[dict]) -> list[ChatMessage]:
        """Convert ``list[dict]`` → ``list[ChatMessage]``.

        Each dict must have ``role`` and ``content``. Unknown roles are
        coerced to ``"user"`` so a malformed client history never crashes
        the turn. The special ``system`` role is dropped here — the
        system prompt is supplied via ``ChatRequest.system_prompt``.
        """
        out: list[ChatMessage] = []
        for m in messages:
            role = str(m.get("role", "user")).lower()
            if role == "system":
                continue
            if role not in ("user", "assistant", "tool"):
                role = "user"
            content = str(m.get("content", ""))
            if not content:
                continue
            out.append(ChatMessage(role=role, content=content))  # type: ignore[arg-type]
        return out

    @classmethod
    def _detect_phase_hint(cls, content: str, current_phase: DialoguePhase) -> str | None:
        """Return the next-phase value when a transition cue is detected.

        Strategy:
        1. Look for an explicit JSON ``phase_transition`` hint block —
           if present and well-formed, that wins.
        2. Otherwise scan the response for the keyword cues tied to the
           current phase and return the matching next phase value.

        Returns ``None`` when no cue is detected (i.e. the session should
        stay in ``current_phase``).
        """
        if not content:
            return None

        hint = cls._parse_explicit_hint(content)
        if hint is not None:
            return hint

        lowered = content.lower()
        for cue, next_phase in _TRANSITION_CUES.get(current_phase, ()):
            if cue in lowered:
                return next_phase.value
        return None

    @staticmethod
    def _parse_explicit_hint(content: str) -> str | None:
        """Parse a structured ``phase_transition`` hint block, if present.

        Accepts either::

            {"phase_transition": "suggested", "next_phase": "seeing"}

        or a looser::

            {"next_phase": "seeing"}

        form. Returns the validated next-phase value, or ``None`` on any
        parse failure.
        """
        match = _HINT_BLOCK_RE.search(content)
        if not match:
            return None
        try:
            payload: dict[str, Any] = json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            return None
        raw_next = payload.get("next_phase") or payload.get("phase")
        if not isinstance(raw_next, str):
            return None
        try:
            return DialoguePhase(raw_next.lower()).value
        except ValueError:
            logger.debug("unknown next_phase in hint block: %r", raw_next)
            return None

    @classmethod
    def _extract_insights(cls, content: str, phase: DialoguePhase) -> dict:
        """Lightly extract new themes / emotions / body_locations from the turn.

        This is a keyword-based pass — the LLM may also surface insights more
        richly in its response, but this gives the caller a stable,
        structured update to merge into ``accumulated_insights`` without
        requiring a second LLM call.

        Returns a dict with optional keys ``emotions``, ``body_locations``,
        ``themes`` (all ``list[str]``). Empty lists are omitted.
        """
        if not content:
            return {}
        lowered = content.lower()
        update: dict[str, list[str]] = {}

        emotions = sorted({kw for kw in _EMOTION_KEYWORDS if kw in lowered})
        if emotions:
            update["emotions"] = emotions

        body = sorted({kw for kw in _BODY_KEYWORDS if kw in lowered})
        if body:
            update["body_locations"] = body

        # Phase-specific theme tagging — what's the LLM emphasizing?
        if phase is DialoguePhase.SEEING or phase is DialoguePhase.MEETING:
            themes: list[str] = []
            if "chart" in lowered or "transit" in lowered or "saturn" in lowered:
                themes.append("cosmic_timing")
            if "fear" in lowered or "survival" in lowered:
                themes.append("survival_fear")
            if "grief" in lowered or "loss" in lowered:
                themes.append("grief")
            if themes:
                update["themes"] = themes

        return update


__all__ = ["AsyncHealingDialogue"]
