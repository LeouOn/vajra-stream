"""
Dharma Tales Module
Thin adapter wrapping core/dharma_tales.py for the DI container.
"""

from typing import Any

from modules.interfaces import EventBus


class DharmaTalesService:
    """Dharma tales generation service — wraps core DharmaTalesGenerator."""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self._generator = None

    @property
    def generator(self):
        if self._generator is None:
            from core.dharma_tales import DharmaTalesGenerator
            self._generator = DharmaTalesGenerator()
        return self._generator

    def generate_tale(
        self, theme: str | None = None, tradition: str | None = None, length: str = "medium", use_llm: bool = False
    ) -> dict[str, Any]:
        """Generate a dharma teaching tale."""
        tale_text = self.generator.generate_tale(
            theme=theme, tradition=tradition, length=length, use_llm=use_llm
        )
        return {
            "tale": tale_text,
            "theme": theme or "random",
            "tradition": tradition or "random",
            "length": length,
        }

    def generate_parable(self, topic: str, use_llm: bool = False) -> dict[str, Any]:
        """Generate a short parable on a topic."""
        parable = self.generator.generate_parable(topic, use_llm=use_llm)
        return {"parable": parable, "topic": topic}

    def generate_teaching_story(
        self, archetype: str | None = None, challenge: str | None = None, tradition: str = "Zen", use_llm: bool = False
    ) -> dict[str, Any]:
        """Generate a full teaching story."""
        story = self.generator.generate_teaching_story(
            archetype=archetype, challenge=challenge, tradition=tradition, use_llm=use_llm
        )
        return {"story": story, "archetype": archetype, "challenge": challenge, "tradition": tradition}

    def list_themes(self) -> list[str]:
        """List available tale themes."""
        return self.generator.list_themes()

    def list_traditions(self) -> list[str]:
        """List available narrative traditions."""
        return self.generator.list_traditions()

    def get_traditional_tales(self) -> dict[str, Any]:
        """Get the library of traditional tales."""
        return self.generator.get_traditional_tales()

    def get_status(self) -> dict[str, Any]:
        return {
            "available": True,
            "themes": len(self.list_themes()),
            "traditions": len(self.list_traditions()),
        }
