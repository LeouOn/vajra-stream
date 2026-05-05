"""
Vajra.Stream - Dharma Tales Generator
AI-powered teaching stories and parables
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class DharmaTalesGenerator:
    """
    Generate dharma teaching stories and parables using LLM
    Each tale teaches a principle through narrative
    """

    def __init__(self, llm_integration=None):
        """
        Initialize Dharma Tales Generator

        Args:
            llm_integration: LLMIntegration instance for story generation
        """
        self.llm = llm_integration

        self.traditional_tales = self._load_traditional_tales()

        self.archetypes = [
            "The Lost Traveler",
            "The Wise Old One",
            "The Greedy Merchant",
            "The Angry Warrior",
            "The Curious Child",
            "The Healed Healer",
            "The Attached Monk",
            "The Liberated Slave",
            "The Blind Oracle",
            "The Two Brothers"
        ]

        self.themes = [
            "impermanence",
            "compassion",
            "emptiness",
            "interdependence",
            "right_action",
            "mindfulness",
            "wisdom",
            "equanimity",
            "letting_go",
            "true_self"
        ]

        self.traditions = [
            "Theravada",
            "Mahayana",
            "Vajrayana",
            "Zen",
            "Taoist",
            "Sufi",
            "Hindu",
            "Christian mystical"
        ]

    def _load_traditional_tales(self) -> Dict:
        """Load library of traditional dharma tales"""
        return {
            "the_ burning_house": {
                "source": "Lotus Sutra",
                "tradition": "Mahayana",
                "theme": "impermanence",
                "summary": "A father uses the promise of toys to lure his children from a burning house."
            },
            "the_arrow": {
                "source": "Acintita Sutra",
                "tradition": "Theravada",
                "theme": "wisdom",
                "summary": "A man is wounded by a poison arrow but refuses treatment, demanding to know who shot it."
            },
            "the_ raft": {
                "source": "Majjhima Nikaya",
                "tradition": "Theravada",
                "theme": "letting_go",
                "summary": "A man crosses a river using a raft, then must decide whether to carry it."
            },
            "the_mirror": {
                "source": "Yogacara",
                "tradition": "Mahayana",
                "theme": "emptiness",
                "summary": "A man sees his reflection in a mirror and becomes attached to it."
            },
            "the_waves": {
                "source": "Zen",
                "tradition": "Zen",
                "theme": "interdependence",
                "summary": "A master asks: when waves rise and fall in the ocean, does the ocean rise and fall?"
            }
        }

    def generate_tale(self, theme: str = None, tradition: str = None,
                      length: str = "medium", use_llm: bool = True) -> str:
        """
        Generate a dharma teaching tale

        Args:
            theme: Theme of the tale (impermanence, compassion, etc.)
            tradition: Narrative tradition (Zen, Sufi, etc.)
            length: 'short' (1 paragraph), 'medium' (2-3 paragraphs), 'long' (full story)
            use_llm: Use LLM for generation (if available)

        Returns:
            Generated story text
        """
        import random

        if theme is None:
            theme = random.choice(self.themes)

        if tradition is None:
            tradition = random.choice(self.traditions)

        if use_llm and self.llm:
            return self._generate_llm_tale(theme, tradition, length)
        else:
            return self._generate_template_tale(theme, tradition, length)

    def _generate_llm_tale(self, theme: str, tradition: str, length: str) -> str:
        """Generate tale using LLM"""
        length_map = {
            'short': 'a brief parable of 2-3 sentences',
            'medium': 'a short teaching story of one paragraph',
            'long': 'a complete teaching tale with setting, conflict, and resolution in 2-3 paragraphs'
        }

        prompt = f"""Write a dharma teaching tale or parable in the {tradition} tradition.

Theme: {theme}
Length: {length_map.get(length, 'a short teaching story')}

The tale should:
- Teach a spiritual principle through narrative
- Be accessible to practitioners of any level
- Include a moment of insight or turning point
- End with a subtle teaching, not explicit moral

Write only the story itself, no introduction or explanation."""

        result = self.llm.generate(
            prompt,
            system_prompt="You are a wise dharma teacher who writes teaching parables. You write with clarity, depth, and poetic sensibility. Your tales reveal truth through story.",
            max_tokens=800 if length == 'long' else 400,
            temperature=0.8
        )

        return result

    def _generate_template_tale(self, theme: str, tradition: str, length: str) -> str:
        """Generate tale from template when LLM unavailable"""
        archetype = self._random_element(self.archetypes)
        setting = self._get_setting(tradition)
        teaching = self._get_teaching(theme)

        if length == 'short':
            return f"""In a {setting}, there was {archetype}. One day, {teaching['setup']}. Through this, they discovered: {teaching['moral']}"""

        return f"""In a {setting}, there lived {archetype}.

{teaching['setup']}

As events unfolded, {teaching['conflict']}

In the end, {teaching['resolution']} The true teaching emerged: {teaching['moral']}

-- From the {tradition} tradition"""

    def _random_element(self, seq):
        import random
        return random.choice(seq)

    def _get_setting(self, tradition: str) -> str:
        settings = {
            "Theravada": "village near an ancient forest monastery",
            "Mahayana": "realm where celestial beings teach earthly beings",
            "Vajrayana": "mysterious valley hidden in the Himalayas",
            "Zen": "small temple garden where snow falls silently",
            "Taoist": "mountain hermitage where clouds gather",
            "Sufi": "caravanserai where travelers rest by night",
            "Hindu": "ashram by the sacred river where seekers gather",
            "Christian mystical": "quiet monastery where light filters through ancient windows"
        }
        return settings.get(tradition, "simple place where truth can be seen")

    def _get_teaching(self, theme: str) -> Dict:
        teachings = {
            "impermanence": {
                "setup": "the flowers bloomed brilliantly, drawing all to admire them",
                "conflict": "the wind began to blow, and petals scattered like memories",
                "resolution": "those who clung to the fallen petals suffered, while others saw beauty in change",
                "moral": "all that arises passes away; rest in the unchanging awareness"
            },
            "compassion": {
                "setup": "a traveler encountered another in great suffering",
                "conflict": "the sufferer pushed away all who tried to help, yet the traveler remained",
                "resolution": "through patient presence, the traveler showed that love needs no object",
                "moral": "true compassion is unconditional, like sunlight that falls equally on all"
            },
            "emptiness": {
                "setup": "a merchant counted his treasures, believing wealth would satisfy",
                "conflict": "the treasures appeared solid, yet when examined closely, dissolved like mist",
                "resolution": "the merchant realized that what he possessed was never truly his",
                "moral": "all phenomena are empty of inherent existence, yet conventionally functional"
            },
            "interdependence": {
                "setup": "a weaver created cloth from threads of many colors",
                "conflict": "each thread alone seemed ordinary, but none could support the whole cloth alone",
                "resolution": "the weaving showed that each thread both supports and is supported by all others",
                "moral": "things exist through dependent origination; self cannot stand apart"
            },
            "wisdom": {
                "setup": "a scholar collected many teachings but found no peace",
                "conflict": "the teachings were like a map of the shore, not the ocean itself",
                "resolution": "finally, the scholar sat still and discovered what the maps could never show",
                "moral": "direct experience transcends all conceptual understanding"
            }
        }
        return teachings.get(theme, teachings["impermanence"])

    def generate_parable(self, topic: str, use_llm: bool = True) -> str:
        """
        Generate a short parable on a specific topic

        Args:
            topic: Topic for the parable (e.g., "letting go of attachment")
            use_llm: Use LLM for generation

        Returns:
            Short parable text
        """
        if use_llm and self.llm:
            prompt = f"""Write a brief dharma parable on this topic: {topic}

The parable should be 3-5 sentences, telling a simple story that illuminates the topic.
End with a single sentence that captures the teaching.
Write only the parable itself."""

            return self.llm.generate(
                prompt,
                system_prompt="You are a wise dharma teacher. You write parables that reveal profound truths through simple narratives.",
                max_tokens=200,
                temperature=0.8
            )
        else:
            return f"""A seeker asked a master about {topic}.

The master held up a cup, then kept pouring until water spilled.
The seeker understood: sometimes we must let the old overflow before the new can fill us.

True understanding requires emptying what we think we know."""

    def generate_teaching_story(self, archetype: str = None, challenge: str = None,
                               tradition: str = "Zen", use_llm: bool = True) -> str:
        """
        Generate a full teaching story with character arc

        Args:
            archetype: The main character type
            challenge: The spiritual challenge they face
            tradition: Narrative tradition style
            use_llm: Use LLM for generation

        Returns:
            Full teaching story
        """
        if archetype is None:
            import random
            archetype = random.choice(self.archetypes)

        if challenge is None:
            import random
            challenge = random.choice(self.themes)

        if use_llm and self.llm:
            prompt = f"""Write a complete dharma teaching story in the {tradition} tradition.

Main character: {archetype}
Spiritual challenge: {challenge}

The story should have:
- A clear setting and protagonist
- A conflict that mirrors the spiritual challenge
- A turning point or moment of insight
- A resolution that embodies the teaching

Length: 2-3 paragraphs
Write the story only, no commentary."""

            return self.llm.generate(
                prompt,
                system_prompt="You are a dharma teacher who writes transformative teaching stories. Your narratives carry the power to shift consciousness.",
                max_tokens=600,
                temperature=0.8
            )
        else:
            return self._generate_template_tale(challenge, tradition, "long")

    def list_themes(self) -> List[str]:
        """Return list of available themes"""
        return self.themes.copy()

    def list_traditions(self) -> List[str]:
        """Return list of available traditions"""
        return self.traditions.copy()

    def get_traditional_tales(self) -> Dict:
        """Return the library of traditional tales"""
        return self.traditional_tales.copy()


def create_dharma_tales_generator(llm_integration=None) -> DharmaTalesGenerator:
    """
    Factory function to create DharmaTalesGenerator

    Args:
        llm_integration: Optional LLMIntegration instance

    Returns:
        DharmaTalesGenerator instance
    """
    return DharmaTalesGenerator(llm_integration)


if __name__ == "__main__":
    print("Dharma Tales Generator")
    print("=" * 60)

    generator = DharmaTalesGenerator()

    print("\nAvailable themes:", ", ".join(generator.list_themes()))
    print("Available traditions:", ", ".join(generator.list_traditions()))

    print("\n" + "=" * 60)
    print("Generating sample tales without LLM:")
    print("=" * 60)

    for theme in ["impermanence", "compassion"]:
        print(f"\n--- Tale on {theme} ---")
        tale = generator.generate_tale(theme=theme, use_llm=False)
        print(tale)

    print("\n" + "=" * 60)
    print("Note: With LLM enabled, stories would be more creative and varied.")
    print("=" * 60)