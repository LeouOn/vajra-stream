# core/llm/dharma.py
"""Native async DharmaLLM — the target API for new code.

This module provides :class:`AsyncDharmaLLM`, a Buddhist/dharma content
generator that talks directly to a :class:`~core.llm.registry.ProviderRegistry`
(no sync bridge, no event-loop gymnantics). It is the async successor to the
deprecated :class:`~core.llm_integration.DharmaLLM`.

Each method builds a prompt (same templates as the legacy ``DharmaLLM``),
asks the registry for the best healthy provider via
:meth:`ProviderRegistry.pick_best`, calls
``provider.generate(ChatRequest(...))``, and returns ``response.content``
as a plain ``str``.

Usage::

    from core.llm.bootstrap import build_default_registry
    from core.llm.dharma import AsyncDharmaLLM

    registry = build_default_registry()
    dharma = AsyncDharmaLLM(registry)
    prayer = await dharma.generate_prayer("peace and healing for all beings")
"""
from __future__ import annotations

import logging

from core.llm.models import ChatMessage, ChatRequest
from core.llm.registry import ProviderRegistry

logger = logging.getLogger(__name__)


# System prompt shared by all dharma generation methods. Identical to the
# legacy DharmaLLM.dharma_system string so output style is preserved.
DHARMA_SYSTEM_PROMPT = """You are a wise dharma teacher versed in Buddhist philosophy,
meditation practices, and contemplative traditions. You speak with clarity, compassion,
and depth. Your teachings are rooted in the Buddhadharma but accessible to all beings.
You draw from Theravada, Mahayana, and Vajrayana traditions as appropriate."""


class AsyncDharmaLLM:
    """Specialised async LLM interface for Buddhist / dharma content.

    Wraps a :class:`ProviderRegistry` and exposes five convenience methods
    covering the common spiritual content types: prayers, teachings,
    meditation instructions, dedications, and contemplation exercises.

    All methods are coroutines and must be ``await``ed.

    Attributes:
        registry: The underlying :class:`ProviderRegistry`.
        dharma_system: System prompt used for all generation calls.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry
        self.dharma_system = DHARMA_SYSTEM_PROMPT

    async def _generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Pick the best provider, run the prompt, return the text.

        Raises:
            RuntimeError: If no healthy provider is available or generation
                fails.
        """
        provider = await self.registry.pick_best()
        if provider is None:
            raise RuntimeError(
                "No healthy LLM provider available in the registry"
            )
        request = ChatRequest(
            messages=[ChatMessage(role="user", content=prompt)],
            system_prompt=self.dharma_system,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        response = await provider.generate(request)
        return response.content

    async def generate_prayer(
        self, intention: str, tradition: str = "universal"
    ) -> str:
        """Generate a prayer / aspiration based on an intention.

        Args:
            intention: What the prayer is for (e.g. ``"healing"``, ``"peace"``).
            tradition: Style hint — ``"universal"``, ``"buddhist"``,
                ``"tibetan"``, or ``"zen"``.
        """
        prompt = f"""Generate a beautiful prayer or aspiration for {intention}.

Style: {tradition}
Length: 3-5 lines
Tone: Heartfelt, sincere, universal in scope

The prayer should:
- Be inclusive of all beings
- Express genuine aspiration
- Be poetic but not flowery
- Suitable for contemplation

Generate only the prayer text, no explanation."""
        return await self._generate(prompt, max_tokens=200, temperature=0.8)

    async def generate_teaching(
        self, topic: str, length: str = "short"
    ) -> str:
        """Generate a dharma teaching on a topic.

        Args:
            topic: Teaching topic (e.g. ``"impermanence"``, ``"compassion"``).
            length: ``"short"`` (1 paragraph), ``"medium"`` (2-3), or
                ``"long"`` (4-6 paragraphs).
        """
        length_map = {
            "short": "1 paragraph",
            "medium": "2-3 paragraphs",
            "long": "4-6 paragraphs",
        }
        prompt = f"""Offer a teaching on {topic}.

Length: {length_map.get(length, "1 paragraph")}

The teaching should:
- Be clear and accessible
- Include practical application
- Be rooted in dharma wisdom
- Inspire practice

Generate the teaching:"""
        max_tokens_map = {"short": 300, "medium": 600, "long": 1200}
        return await self._generate(
            prompt,
            max_tokens=max_tokens_map.get(length, 300),
            temperature=0.7,
        )

    async def generate_meditation_instruction(self, practice: str) -> str:
        """Generate meditation instructions for a given practice.

        Args:
            practice: Type of meditation (e.g. ``"loving-kindness"``,
                ``"shamatha"``, ``"vipassana"``).
        """
        prompt = f"""Provide clear meditation instructions for {practice} practice.

Format:
1. Posture and preparation (brief)
2. Main practice instructions (detailed)
3. Closing (brief)

Keep it practical and clear. Suitable for beginners but also valuable for experienced practitioners.

Generate the instructions:"""
        return await self._generate(prompt, max_tokens=800, temperature=0.6)

    async def generate_dedication(self) -> str:
        """Generate a brief dedication of merit."""
        prompt = """Generate a brief dedication of merit to conclude a practice session.

2-4 lines that dedicate any benefit to all beings.

Generate only the dedication text:"""
        return await self._generate(prompt, max_tokens=150, temperature=0.8)

    async def generate_contemplation(self, theme: str) -> str:
        """Generate a contemplation exercise on a theme.

        Args:
            theme: Theme to contemplate (e.g. ``"death"``,
                ``"interdependence"``, ``"buddha-nature"``).
        """
        prompt = f"""Create a contemplation exercise on {theme}.

Format:
- Opening reflection question
- 2-3 points to consider
- Closing invitation

Make it profound yet accessible.

Generate the contemplation:"""
        return await self._generate(prompt, max_tokens=400, temperature=0.7)


__all__ = ["AsyncDharmaLLM", "DHARMA_SYSTEM_PROMPT"]
