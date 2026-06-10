"""
88 Buddhas Repentance — Narrative Explorer & Ritual Service

Provides story-generation, random-buddha exploration, and full
confession ritual support for the 88-Buddha Repentance practice
(八十八佛大懺悔文). The practice combines 53 past Buddhas with
35 Confession Buddhas for profound karmic purification.

Usage:
    service = EightyEightBuddhas()
    # Get a random Buddha for contemplation
    buddha = service.random_buddha()

    # Generate a narrative about a specific Buddha
    story = service.generate_buddha_narrative("Shakyamuni", llm=operator.creative_llm)

    # Get the full confession sequence
    sequence = service.get_confession_sequence()
"""

import json
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BuddhaEntry:
    """A single Buddha from the 88-Buddha collection."""

    index: int
    name_chinese: str
    name_pinyin: str
    name_sanskrit: str
    category: str  # "past" or "confession"
    meaning: str
    realm: str = ""
    light: str = ""
    epithet: str = ""


class EightyEightBuddhas:
    """
    Service for working with the 88-Buddha Repentance practice.

    Loads the full 88-Buddha text from knowledge/eighty_eight_buddhas.json
    and provides narrative generation, random exploration, and ritual
    structure support.
    """

    def __init__(self, llm=None):
        self.llm = llm
        self._data: dict[str, Any] = {}
        self._buddhas: list[BuddhaEntry] = []
        self._load_data()

    def _load_data(self):
        """Load the 88-Buddha data from the knowledge base."""
        path = Path(__file__).parent.parent / "knowledge" / "eighty_eight_buddhas.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {}

        self._buddhas = []
        if isinstance(self._data, list):
            for b in self._data:
                if isinstance(b, dict):
                    group = b.get("group", "confession")
                    category = "past" if group == "fifty_three" else "confession"
                    self._buddhas.append(
                        BuddhaEntry(
                            index=b.get("index", 0),
                            name_chinese=b.get("chinese", b.get("name_chinese", "")),
                            name_pinyin=b.get("pinyin", b.get("name_pinyin", "")),
                            name_sanskrit=b.get("sanskrit", b.get("name_sanskrit", "")),
                            category=category,
                            meaning=b.get("meaning", ""),
                            realm=b.get("quality", b.get("realm", "")),
                            light=b.get("quality", b.get("light", "")),
                            epithet=b.get("translation", ""),
                        )
                    )

    # ─── Public API ───────────────────────────────────────────

    @property
    def buddha_count(self) -> int:
        return len(self._buddhas)

    def random_buddha(self, category: str | None = None) -> BuddhaEntry:
        """Return a random Buddha from the collection."""
        pool = self._buddhas
        if category:
            pool = [b for b in pool if b.category == category]
        return random.choice(pool) if pool else self._buddhas[0]

    def get_buddha_by_name(self, name: str) -> BuddhaEntry | None:
        """Find a Buddha by Chinese name (partial match)."""
        for b in self._buddhas:
            if name.lower() in b.name_chinese.lower() or name.lower() in b.name_sanskrit.lower():
                return b
        return None

    def get_confession_sequence(self) -> dict[str, Any]:
        """Get the full confession ritual structure."""
        past_buddhas = [b for b in self._buddhas if b.category == "past"]
        confession_buddhas = [b for b in self._buddhas if b.category == "confession"]

        return {
            "title": "八十八佛大懺悔文",
            "title_pinyin": "Bāshíbā Fó Dà Chànhuǐ Wén",
            "title_english": "The Great Repentance Text of the 88 Buddhas",
            "opening_verse": {
                "chinese": "大慈大悲愍众生 大喜大舍济含识",
                "pinyin": "Dà cí dà bēi mǐn zhòng shēng, dà xǐ dà shě jì hán shí",
                "english": "With great loving-kindness and compassion, pity all sentient beings; with great joy and equanimity, liberate all conscious creatures.",
            },
            "fifty_three_past_buddhas": [
                {
                    "index": b.index,
                    "name_chinese": b.name_chinese,
                    "name_pinyin": b.name_pinyin,
                    "name_sanskrit": b.name_sanskrit,
                    "light": b.light if b.light else f"{b.name_chinese} 如來",
                }
                for b in past_buddhas
            ],
            "thirty_five_confession_buddhas": [
                {
                    "index": b.index,
                    "name_chinese": b.name_chinese,
                    "name_pinyin": b.name_pinyin,
                    "name_sanskrit": b.name_sanskrit,
                    "confession_line": f"南無{b.name_chinese}" if b.name_chinese else "",
                }
                for b in confession_buddhas
            ],
            "closing_dedication": {
                "chinese": "愿以此功德 普及于一切 我等与众生 皆共成佛道",
                "english": "May this merit extend universally to all; may we together with all beings accomplish the Buddha Way.",
            },
        }

    def generate_buddha_narrative(
        self,
        buddha_name: str,
        llm=None,
        depth: str = "contemplation",  # "brief", "contemplation", "narrative"
    ) -> dict[str, Any]:
        """
        Generate a narrative about a specific Buddha.

        Args:
            buddha_name: Chinese or Sanskrit name of the Buddha
            llm: Optional LLM instance (defaults to self.llm)
            depth: 'brief' (2-3 lines), 'contemplation' (paragraph), 'narrative' (full story)
        """
        buddha = self.get_buddha_by_name(buddha_name)
        if not buddha:
            return {"error": f"Buddha not found: {buddha_name}"}

        narrative_llm = llm or self.llm

        if depth == "brief":
            text = self._brief_narrative(buddha)
        elif (
            narrative_llm
            and hasattr(narrative_llm, "generate")
            and (hasattr(narrative_llm, "client") or hasattr(narrative_llm, "local_model"))
        ):
            text = self._llm_narrative(buddha, narrative_llm, depth)
        else:
            text = self._contemplation_narrative(buddha)

        return {
            "buddha": {
                "name_chinese": buddha.name_chinese,
                "name_pinyin": buddha.name_pinyin,
                "name_sanskrit": buddha.name_sanskrit,
                "category": buddha.category,
                "meaning": buddha.meaning,
                "realm": buddha.realm,
                "light": buddha.light,
            },
            "narrative": text,
            "depth": depth,
            "generated_at": datetime.now().isoformat(),
        }

    def generate_repentance_narrative(self, intention: str = "", llm=None) -> dict[str, Any]:
        """
        Generate a full repentance narrative invoking all 88 Buddhas.

        Selects 7 representative Buddhas (one per day of the week concept),
        generates a narrative for each, and composes a confession liturgy.
        """
        narrative_llm = llm or self.llm
        # Select 7 representative Buddhas spanning both categories
        past = [b for b in self._buddhas if b.category == "past"]
        confession = [b for b in self._buddhas if b.category == "confession"]
        selected = random.sample(past, min(4, len(past))) + random.sample(confession, min(3, len(confession)))
        random.shuffle(selected)

        narratives = []
        for buddha in selected:
            narratives.append(
                {
                    "name": buddha.name_chinese,
                    "pinyin": buddha.name_pinyin,
                    "meaning": buddha.meaning,
                    "narrative": self._contemplation_narrative(buddha),
                }
            )

        # Compose the full liturgy
        liturgy_parts = []
        liturgy_parts.append("八十八佛大懺悔文")
        liturgy_parts.append("The Great Repentance of the 88 Buddhas\n")
        liturgy_parts.append(
            f"Intention: {intention or 'purification of all negative karma accumulated since beginningless time'}\n"
        )

        liturgy_parts.append("─" * 50)
        liturgy_parts.append("I. OPENING ASPIRATION")
        liturgy_parts.append("大慈大悲愍众生 大喜大舍济含识")
        liturgy_parts.append("")

        liturgy_parts.append("II. HOMAGE TO THE 53 PAST BUDDHAS")
        for b in past[:8]:
            liturgy_parts.append(f"  · {b.name_chinese} ({b.name_pinyin})")
        liturgy_parts.append(f"  ... and all {len(past)} past Buddhas")
        liturgy_parts.append("")

        liturgy_parts.append("III. HOMAGE TO THE 35 CONFESSION BUDDHAS")
        for b in confession[:5]:
            liturgy_parts.append(f"  · {b.name_chinese} ({b.name_pinyin})")
        liturgy_parts.append(f"  ... and all {len(confession)} confession Buddhas")
        liturgy_parts.append("")

        liturgy_parts.append("IV. ILLUMINATED CONTEMPLATIONS")
        for n in narratives:
            liturgy_parts.append(f"\n  {n['name']} ({n['pinyin']}) — {n['meaning']}")
            liturgy_parts.append(f"  {n['narrative'][:200]}")
        liturgy_parts.append("")

        liturgy_parts.append("V. DEDICATION")
        liturgy_parts.append("愿以此功德 普及于一切 我等与众生 皆共成佛道\nMay this merit extend to all beings.")

        return {
            "title": "88-Buddha Repentance Liturgy",
            "selected_buddhas": [
                {"name": b.name_chinese, "pinyin": b.name_pinyin, "meaning": b.meaning} for b in selected
            ],
            "liturgy": "\n".join(liturgy_parts),
            "narratives": narratives,
            "total_buddhas": len(self._buddhas),
            "generated_at": datetime.now().isoformat(),
        }

    def explore_by_element(self, element: str = "Fire") -> list[BuddhaEntry]:
        """Find Buddhas associated with a specific Wu Xing element."""
        return [
            b
            for b in self._buddhas
            if element.lower() in (b.light or "").lower() or element.lower() in (b.realm or "").lower()
        ]

    def explore_by_realm(self, realm_keyword: str = "purification") -> list[BuddhaEntry]:
        """Find Buddhas associated with a specific realm or quality."""
        return [
            b
            for b in self._buddhas
            if realm_keyword.lower() in (b.realm or "").lower() + " " + (b.meaning or "").lower()
        ]

    # ─── Internal Narrative Builders ─────────────────────────

    def _brief_narrative(self, buddha: BuddhaEntry) -> str:
        """Generate a brief 2-line narrative."""
        category_text = (
            "past Buddha who appeared in the world" if buddha.category == "past" else "confession Buddha who purifies"
        )
        return (
            f"{buddha.name_chinese} ({buddha.name_sanskrit}) is a {category_text}."
            f"{' Their name means: ' + buddha.meaning + '.' if buddha.meaning else ''}"
            f"{' Realm: ' + buddha.realm + '.' if buddha.realm else ''}"
        )

    def _contemplation_narrative(self, buddha: BuddhaEntry) -> str:
        """Generate a meditative contemplation paragraph."""
        name = buddha.name_chinese
        meaning = buddha.meaning
        light = buddha.light
        realm = buddha.realm
        category = "of the fortunate eon" if buddha.category == "past" else "who purifies all obscurations"

        parts = [
            f"Contemplate {name} ({buddha.name_pinyin}), a transcendent Buddha {category},",
        ]
        if meaning:
            parts.append(f'whose sacred name means "{meaning}."')
        if light:
            parts.append(f"From their body emanates {light},")
        if realm:
            parts.append(f"illuminating the {realm}.")
        parts.append(
            "As you recite their name with sincere devotion,"
            " visualize this Buddha before you, radiating boundless compassion."
            " Every negative karma you have ever created dissolves like mist before the rising sun."
            " Feel the warmth of their blessing permeate every cell of your being."
        )

        return " ".join(parts)

    def _llm_narrative(self, buddha: BuddhaEntry, llm, depth: str) -> str:
        """Generate a narrative using the LLM."""
        context = (
            f"Buddha Name (Chinese): {buddha.name_chinese}\n"
            f"Pinyin: {buddha.name_pinyin}\n"
            f"Sanskrit: {buddha.name_sanskrit}\n"
            f"Meaning: {buddha.meaning}\n"
            f"Realm: {buddha.realm}\n"
            f"Emanated Light: {buddha.light}\n"
            f"Category: {'53 Past Buddhas' if buddha.category == 'past' else '35 Confession Buddhas'}\n"
        )

        if depth == "contemplation":
            prompt = (
                f"{context}\n"
                f"Write a brief, poetic contemplation (3-4 sentences) about this Buddha, "
                f"suitable for guided meditation. Include the meaning of their name, the quality "
                f"of their light, and how contemplating them purifies specific karma. "
                f"Use vivid, luminous imagery. Write only the contemplation."
            )
        else:
            prompt = (
                f"{context}\n"
                f"Write a short sacred narrative (5-7 sentences) about this Buddha — their "
                f"vows, their realm, their emanated light, and the specific karmic obscurations "
                f"they help purify. Write in the style of a sutra or visionary account. "
                f"Include the meaning of their name as a dharma teaching. "
                f"Make it inspiring and beautiful. Write only the narrative."
            )

        try:
            result = llm.generate(
                prompt=prompt,
                system_prompt="You are a dharma scribe composing sacred narratives. Your words carry blessing power.",
                max_tokens=300 if depth == "narrative" else 200,
                temperature=0.7,
            )
            return result.strip() if result else self._contemplation_narrative(buddha)
        except Exception:
            return self._contemplation_narrative(buddha)


# Convenience instance
_eighty_eight_buddhas_instance: EightyEightBuddhas | None = None


def get_eighty_eight_buddhas() -> EightyEightBuddhas:
    global _eighty_eight_buddhas_instance
    if _eighty_eight_buddhas_instance is None:
        _eighty_eight_buddhas_instance = EightyEightBuddhas()
    return _eighty_eight_buddhas_instance
