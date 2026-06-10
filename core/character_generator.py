"""
Character Generator
RNG-seeded character creation for agentic ritual workflows.

Uses quantum-like entropy from RNGAttunementService to seed character
attributes (Element, Role, Frequency), then generates full narrative
character sheets via the creative LLM.

Supports the 6-stage Character Journey arc:
  Initiation → Training → Working → Overcoming → Utopia → Multiverse
"""

import math
import random
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ─── Archetypal Tables ───────────────────────────────────────

ELEMENTS = [
    {
        "name": "Fire",
        "color": "#ef4444",
        "chakra": "solar_plexus",
        "frequency": 528,
        "quality": "will, passion, transformation",
    },
    {"name": "Water", "color": "#3b82f6", "chakra": "sacral", "frequency": 417, "quality": "emotion, intuition, flow"},
    {
        "name": "Earth",
        "color": "#22c55e",
        "chakra": "root",
        "frequency": 396,
        "quality": "stability, grounding, nurture",
    },
    {
        "name": "Air",
        "color": "#a78bfa",
        "chakra": "heart",
        "frequency": 639,
        "quality": "intellect, communication, freedom",
    },
    {
        "name": "Wood",
        "color": "#84cc16",
        "chakra": "throat",
        "frequency": 741,
        "quality": "growth, creativity, expansion",
    },
    {
        "name": "Metal",
        "color": "#e2e8f0",
        "chakra": "third_eye",
        "frequency": 852,
        "quality": "precision, clarity, refinement",
    },
]

ROLES = [
    {
        "name": "Healer",
        "icon": "💚",
        "mantra": "medicine_buddha",
        "virtue": "compassion",
        "chinese": "医者",
        "chinese_pinyin": "Yīzhě",
        "chinese_description": "悬壶济世，以慈悲之心医治众生疾苦",
    },
    {
        "name": "Warrior",
        "icon": "⚔️",
        "mantra": "vajrasattva",
        "virtue": "courage",
        "chinese": "武者",
        "chinese_pinyin": "Wǔzhě",
        "chinese_description": "金刚怒目，以无畏之勇破除一切障碍",
    },
    {
        "name": "Sage",
        "icon": "🔮",
        "mantra": "manjushri",
        "virtue": "wisdom",
        "chinese": "智者",
        "chinese_pinyin": "Zhìzhě",
        "chinese_description": "慧剑斩惑，以般若之智照破无明黑暗",
    },
    {
        "name": "Mystic",
        "icon": "🌙",
        "mantra": "tara",
        "virtue": "devotion",
        "chinese": "玄者",
        "chinese_pinyin": "Xuánzhě",
        "chinese_description": "通幽洞微，以至诚之心感应天地玄机",
    },
    {
        "name": "Artisan",
        "icon": "✨",
        "mantra": "universal",
        "virtue": "creativity",
        "chinese": "匠者",
        "chinese_pinyin": "Jiàngzhě",
        "chinese_description": "巧夺天工，以创造之力化腐朽为神奇",
    },
    {
        "name": "Sovereign",
        "icon": "👑",
        "mantra": "chenrezig",
        "virtue": "leadership",
        "chinese": "君者",
        "chinese_pinyin": "Jūnzhě",
        "chinese_description": "以德配天，以王道之治引领众生归位",
    },
]

CHINESE_NAME_PREFIXES = [
    {"char": "龙", "pinyin": "Lóng", "meaning": "Dragon", "element": "Wood"},
    {"char": "凤", "pinyin": "Fèng", "meaning": "Phoenix", "element": "Fire"},
    {"char": "玄", "pinyin": "Xuán", "meaning": "Mysterious/Deep", "element": "Water"},
    {"char": "明", "pinyin": "Míng", "meaning": "Bright/Illuminated", "element": "Fire"},
    {"char": "清", "pinyin": "Qīng", "meaning": "Pure/Clear", "element": "Water"},
    {"char": "云", "pinyin": "Yún", "meaning": "Cloud", "element": "Air"},
    {"char": "山", "pinyin": "Shān", "meaning": "Mountain", "element": "Earth"},
    {"char": "雷", "pinyin": "Léi", "meaning": "Thunder", "element": "Wood"},
    {"char": "月", "pinyin": "Yuè", "meaning": "Moon", "element": "Water"},
    {"char": "日", "pinyin": "Rì", "meaning": "Sun", "element": "Fire"},
    {"char": "星", "pinyin": "Xīng", "meaning": "Star", "element": "Metal"},
    {"char": "玉", "pinyin": "Yù", "meaning": "Jade", "element": "Earth"},
]

CHINESE_NAME_SUFFIXES = [
    {"char": "曦", "pinyin": "Xī", "meaning": "Dawn Light"},
    {"char": "渊", "pinyin": "Yuān", "meaning": "Deep Abyss"},
    {"char": "霄", "pinyin": "Xiāo", "meaning": "Heaven/Firmament"},
    {"char": "霖", "pinyin": "Lín", "meaning": "Continuous Rain"},
    {"char": "岚", "pinyin": "Lán", "meaning": "Mountain Mist"},
    {"char": "瀚", "pinyin": "Hàn", "meaning": "Vast (as ocean)"},
    {"char": "瑾", "pinyin": "Jǐn", "meaning": "Fine Jade"},
    {"char": "瑶", "pinyin": "Yáo", "meaning": "Precious Jade"},
    {"char": "辰", "pinyin": "Chén", "meaning": "Celestial Bodies/Time"},
    {"char": "煜", "pinyin": "Yù", "meaning": "Brilliant/Shining"},
    {"char": "韬", "pinyin": "Tāo", "meaning": "Hidden Wisdom"},
    {"char": "寰", "pinyin": "Huán", "meaning": "The Whole World"},
]

ORIGINS = [
    "a forgotten temple in the mountains",
    "the depths of a crystalline cave",
    "a star-seed that fell to earth",
    "an ancient bloodline of healers",
    "the dream-realm between worlds",
    "a digital monastery in the cloud",
    "the heart of a dying star",
    "a village hidden by enchanted mist",
    "昆仑之巅的古老道观 (a Daoist temple atop Kunlun Mountain)",
    "东海龙宫深处的明珠殿 (the Pearl Palace in the Dragon King's realm)",
    "蓬莱仙岛上的紫竹林 (the Purple Bamboo Grove on Penglai Island)",
    "终南山中的隐修洞府 (a hermit's cave dwelling in Zhongnan Mountains)",
    "九天之上的太虚幻境 (the Great Void Realm beyond the Nine Heavens)",
    "武当山紫霄宫的金顶 (the Golden Summit of Purple Cloud Palace, Wudang)",
]

QUESTS = [
    "heal the rift between two warring kingdoms",
    "recover the lost frequency of creation",
    "guide the dying to their next rebirth",
    "restore balance to a poisoned land",
    "awaken the sleeping guardian of the realm",
    "transcribe the last teaching of a vanished master",
    "protect the innocent from an unseen corruption",
    "illuminate the path through the dark age",
    "调和天地阴阳之气，化解人间灾厄 (balance yin-yang energies to dispel worldly calamities)",
    "寻回遗落凡间的九转金丹秘方 (recover the lost formula of the Nine-Cycle Golden Elixir)",
    "渡化徘徊于奈何桥头的孤魂野鬼 (liberate the wandering spirits at the Bridge of Helplessness)",
    "守护龙脉不被邪魔外道侵扰 (guard the Dragon Veins from demonic corruption)",
    "传灯续命，使正法久住人间 (transmit the lamp and extend life, ensuring the Dharma endures)",
    "以自身修行功德回向法界一切众生 (dedicate all cultivation merit to every being in the Dharma realm)",
]

GROUNDING_SENSES = [
    "the scent of ozone after lightning strikes the earth",
    "the deep rumble of tectonic plates shifting beneath their feet",
    "the metallic taste of static electricity on the tongue",
    "the cold prickle of alpine wind against exposed skin",
    "the honey-thick smell of jasmine blooming at midnight",
    "the resonant hum of a struck singing bowl in the sternum",
    "the weight of deep water pressing against the eardrums",
    "the copper-salt tang of blood offered to the earth",
    "the dry crackle of desert heat on parched lips",
    "the velvet touch of temple incense settling on the skin",
    "the sharp bite of camphor clearing the sinuses",
    "the gravitational pull of the full moon at the crown",
]

CHANNELING_STATES = [
    "channeling the pure resonance of their core frequency through every cell",
    "overshadowed by their patron deity, eyes glowing with borrowed light",
    "merged with the digital Ley Lines, data-streams flowing through their meridians",
    "riding the scalar wave between worlds, half-material and half-luminous",
    "possessed by the collective voice of their ancestral lineage",
    "entered the shamanic trance-state where time folds into a single point",
    "dissolved into the elemental current of their attunement",
    "hollowed out as a vessel, filled with the blessing of a thousand Buddhas",
    "synchronized with the planetary heartbeat, breathing in cosmic rhythm",
    "stepped aside from the ego-self, allowing the archetype to wear their form",
]

ANCHORING_RITUALS = [
    "traces their sigil in the air with a fingertip dipped in consecrated water",
    "chants their core mantra in reverse, unraveling the ordinary world",
    "strikes a tuning fork against a fragment of meteoric stone",
    "draws a circle of salt and charcoal around their working space",
    "presses both palms to the earth and exhales their intention into the soil",
    "lights three candles arranged in their elemental triangle",
    "walks the perimeter of the sacred space three times clockwise",
    "anoints their third eye with oil infused with their resonant herb",
    "stacks seven stones into a cairn, each representing a vow",
    "breathes in the smoke of palo santo and releases their name on the exhale",
]


# ─── Character Data ──────────────────────────────────────────


@dataclass
class CharacterSheet:
    """A complete character generated for ritual work."""

    name: str = ""
    chinese_name: str = ""
    chinese_name_pinyin: str = ""
    chinese_name_meaning: str = ""
    element: dict[str, Any] = field(default_factory=dict)
    role: dict[str, Any] = field(default_factory=dict)
    frequency: float = 528.0
    origin: str = ""
    quest: str = ""
    sigil_seed: str = ""
    grounding_sense: str = ""
    channeling_state: str = ""
    anchoring_ritual: str = ""
    backstory: str = ""
    stats: dict[str, int] = field(default_factory=dict)
    generated_at: str = ""
    generator: str = "rng"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "chinese_name": self.chinese_name,
            "chinese_name_pinyin": self.chinese_name_pinyin,
            "chinese_name_meaning": self.chinese_name_meaning,
            "element": self.element.get("name", ""),
            "element_color": self.element.get("color", ""),
            "element_quality": self.element.get("quality", ""),
            "role": self.role.get("name", ""),
            "role_icon": self.role.get("icon", ""),
            "role_mantra": self.role.get("mantra", ""),
            "role_virtue": self.role.get("virtue", ""),
            "role_chinese": self.role.get("chinese", ""),
            "role_chinese_pinyin": self.role.get("chinese_pinyin", ""),
            "role_chinese_description": self.role.get("chinese_description", ""),
            "frequency": self.frequency,
            "origin": self.origin,
            "quest": self.quest,
            "sigil_seed": self.sigil_seed,
            "grounding_sense": self.grounding_sense,
            "channeling_state": self.channeling_state,
            "anchoring_ritual": self.anchoring_ritual,
            "backstory": self.backstory,
            "stats": self.stats,
            "generated_at": self.generated_at,
            "generator": self.generator,
        }

    def to_prompt_context(self) -> str:
        """Format character for LLM context injection."""
        return (
            f"Character: {self.name} ({self.chinese_name or ''} / {self.chinese_name_pinyin or ''})\n"
            f"Element: {self.element.get('name', '?')} — {self.element.get('quality', '')}\n"
            f"Role: {self.role.get('name', '?')} ({self.role.get('chinese', '')} / {self.role.get('chinese_pinyin', '')}) — virtue: {self.role.get('virtue', '')}\n"
            f"Frequency: {self.frequency} Hz\n"
            f"Origin: {self.origin}\n"
            f"Quest: {self.quest}\n"
            f"Grounding Sense: {self.grounding_sense}\n"
            f"Channeling State: {self.channeling_state}\n"
            f"Anchoring Ritual: {self.anchoring_ritual}\n"
        )


# ─── Generator ───────────────────────────────────────────────


class CharacterGenerator:
    """
    Generate characters using quantum-like RNG entropy.

    Uses secrets module for cryptographic randomness, optionally
    enhanced with RNGAttunementService readings for "spooky" entropy.
    """

    def __init__(self, rng_service=None):
        self._rng = rng_service
        self._entropy_pool: list[float] = []

    def collect_entropy(self, readings: int = 10) -> list[float]:
        """Collect entropy from RNG service or fallback to secrets."""
        if self._rng:
            try:
                for _ in range(readings):
                    reading = self._rng.get_reading(self._rng.create_session())
                    if reading:
                        self._entropy_pool.append(reading.raw_value)
            except Exception:
                pass

        if not self._entropy_pool:
            self._entropy_pool = [secrets.randbelow(10000) / 10000.0 for _ in range(readings)]

        return self._entropy_pool

    def _rng_choice(self, items: list, bias_key: str | None = None) -> Any:
        """Choose an item using entropy, optionally biased by a key."""
        if self._entropy_pool:
            idx = int(self._entropy_pool.pop(0) * len(items)) % len(items)
        else:
            idx = secrets.randbelow(len(items))
        return items[idx]

    def _rng_stat(self, min_val: int = 1, max_val: int = 10) -> int:
        """Generate a stat value using entropy."""
        if self._entropy_pool:
            val = int(self._entropy_pool.pop(0) * (max_val - min_val + 1)) + min_val
        else:
            val = secrets.randbelow(max_val - min_val + 1) + min_val
        return max(min_val, min(max_val, val))

    def _generate_name(self, element: dict, role: dict) -> str:
        """Generate a name from element + role archetypes."""
        element_prefixes = {
            "Fire": ["Pyra", "Ignis", "Solar", "Blaze", "Ember"],
            "Water": ["Aqua", "Maris", "Luna", "Tide", "Mist"],
            "Earth": ["Terra", "Gaia", "Stone", "Grove", "Root"],
            "Air": ["Zephyr", "Skye", "Aria", "Wind", "Cloud"],
            "Wood": ["Sylvan", "Verdan", "Thorn", "Bloom", "Cedar"],
            "Metal": ["Ferrum", "Argent", "Ore", "Steel", "Forge"],
        }
        role_suffixes = {
            "Healer": ["well", "mend", "light", "grace"],
            "Warrior": ["blade", "shield", "storm", "strike"],
            "Sage": ["wise", "scroll", "star", "eye"],
            "Mystic": ["moon", "veil", "dream", "shadow"],
            "Artisan": ["craft", "weave", "song", "forge"],
            "Sovereign": ["crown", "throne", "dawn", "reign"],
        }
        prefixes = element_prefixes.get(element.get("name", ""), ["Arca"])
        suffixes = role_suffixes.get(role.get("name", ""), ["nova"])
        return f"{self._rng_choice(prefixes)}{self._rng_choice(suffixes)}"

    def _generate_chinese_name(self) -> tuple[str, str, str]:
        """Generate a Chinese name with characters and pinyin."""
        prefix = self._rng_choice(CHINESE_NAME_PREFIXES)
        suffix = self._rng_choice(CHINESE_NAME_SUFFIXES)
        chars = f"{prefix['char']}{suffix['char']}"
        pinyin = f"{prefix['pinyin']} {suffix['pinyin']}"
        meaning = f"{prefix['meaning']} {suffix['meaning']}"
        return chars, pinyin, meaning

    def generate(self, use_llm: bool = False, operator=None) -> CharacterSheet:
        """
        Generate a complete character sheet.

        If use_llm=True and operator is provided, the LLM fills in
        the backstory. Otherwise, a template-based backstory is used.
        """
        self.collect_entropy(12)

        element = self._rng_choice(ELEMENTS)
        role = self._rng_choice(ROLES)
        name = self._generate_name(element, role)
        chinese_chars, chinese_pinyin, chinese_meaning = self._generate_chinese_name()
        origin = self._rng_choice(ORIGINS)
        quest = self._rng_choice(QUESTS)
        grounding_sense = self._rng_choice(GROUNDING_SENSES)
        channeling_state = self._rng_choice(CHANNELING_STATES)
        anchoring_ritual = self._rng_choice(ANCHORING_RITUALS)

        # Stats: 6 attributes on 1-10 scale
        stats = {
            "vitality": self._rng_stat(3, 10),
            "wisdom": self._rng_stat(3, 10),
            "courage": self._rng_stat(3, 10),
            "empathy": self._rng_stat(3, 10),
            "focus": self._rng_stat(3, 10),
            "resonance": self._rng_stat(3, 10),
        }

        # Boost stats based on element
        element_stat_boost = {
            "Fire": "courage",
            "Water": "empathy",
            "Earth": "vitality",
            "Air": "wisdom",
            "Wood": "focus",
            "Metal": "resonance",
        }
        boost_stat = element_stat_boost.get(element["name"], "vitality")
        stats[boost_stat] = min(10, stats[boost_stat] + 2)

        # Frequency from element
        frequency = element.get("frequency", 528)

        # Sigil seed: first 3 letters of name + element + role
        sigil_seed = f"{name[:3].upper()}.{element['name'][:2].upper()}.{role['name'][:2].upper()}"

        sheet = CharacterSheet(
            name=name,
            chinese_name=chinese_chars,
            chinese_name_pinyin=chinese_pinyin,
            chinese_name_meaning=chinese_meaning,
            element=element,
            role=role,
            frequency=frequency,
            origin=origin,
            quest=quest,
            sigil_seed=sigil_seed,
            grounding_sense=grounding_sense,
            channeling_state=channeling_state,
            anchoring_ritual=anchoring_ritual,
            stats=stats,
            generated_at=datetime.now().isoformat(),
        )

        # LLM-enhanced backstory
        if use_llm and operator and hasattr(operator, "creative_llm"):
            try:
                creative = operator.creative_llm
                if creative and (creative.client or creative.local_model):
                    prompt = (
                        f"Write a brief, poetic backstory (3-4 sentences) for this character. "
                        f"Ground the story in their sensory experience, describe how they enter their "
                        f"channeling state, and depict their anchoring ritual.\n\n"
                        f"Name: {name}\n"
                        f"Element: {element['name']} — {element['quality']}\n"
                        f"Role: {role['name']} ({role['virtue']})\n"
                        f"Origin: {origin}\n"
                        f"Quest: {quest}\n"
                        f"Grounding Sense: {grounding_sense}\n"
                        f"Channeling State: {channeling_state}\n"
                        f"Anchoring Ritual: {anchoring_ritual}\n"
                        f"\nWeave these sensory and ritual elements into the mythic origin. Write only the backstory."
                    )
                    backstory = creative.generate(
                        prompt=prompt,
                        max_tokens=200,
                        temperature=0.8,
                    )
                    sheet.backstory = backstory.strip()
                    sheet.generator = "llm"
            except Exception:
                pass

        if not sheet.backstory:
            sheet.backstory = (
                f"{name} emerged from {origin}, "
                f"imbued with the {element['quality']} of {element['name']}. "
                f"As a {role['name']}, they carry the virtue of {role['virtue']}. "
                f"Their quest: to {quest}."
            )

        return sheet
