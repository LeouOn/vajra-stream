"""
Grimoire & Correspondence Database — esoteric reference data service.

Manages a structured, multi-corpus database of esoteric knowledge:
- 10 Planetary Correspondences (metals, minerals, herbs, radionics rates, frequencies, chakras)
- 78 Tarot Cards (Rider-Waite-Smith Major and Minor Arcana, symbolism, astrology)
- 64 I Ching Hexagrams (trigram components, Wilhelm-Baynes judgments and line texts)
- Sacred Mantras & Dharanis (Bija syllables, deity alignments, healing intents, frequencies)
- Mahayana Sutras (Heart Sutra, Diamond Sutra, Lotus Sutra, Sanghata passages)
- Healing Frequencies & Meridians (Solfeggio, planetary, brainwave, chakra tunings)

Used by the divination API, radionics operator, LLM tutor, and frontend Grimoire Explorer.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CORRESPONDENCES: dict[str, dict[str, Any]] = {
    "sun": {
        "planet": "Sun",
        "metal": "Gold",
        "minerals": ["Citrine", "Sunstone", "Amber", "Tiger's Eye", "Pyrite"],
        "herbs": ["Chamomile", "St. John's Wort", "Calendula", "Frankincense", "Saffron", "Rosemary", "Cinnamon"],
        "rates": [19, 48, 81],
        "frequencies": [194.18, 528.0],
        "chakra": "Solar Plexus",
        "element": "Fire",
        "day": "Sunday",
        "moon_phase": "Full Moon",
        "archetypes": ["The Sovereign", "The Solar Hero", "Apollo", "Helios", "Ra"],
        "influence": "Vitality, illumination, authority, self-realization, life force, conscious willpower",
    },
    "moon": {
        "planet": "Moon",
        "metal": "Silver",
        "minerals": ["Moonstone", "Pearl", "Selenite", "Labradorite", "Opal"],
        "herbs": ["Jasmine", "Mugwort", "White Rose", "Lotus", "Myrrh", "Sandalwood", "Lemon Balm"],
        "rates": [20, 52, 73],
        "frequencies": [210.42, 432.0],
        "chakra": "Sacral / Third Eye",
        "element": "Water",
        "day": "Monday",
        "moon_phase": "New / Waxing Moon",
        "archetypes": ["The High Priestess", "The Lunar Mother", "Artemis", "Luna", "Isis"],
        "influence": "Emotions, subconscious mind, dreams, intuitive perception, cyclic renewal, protection",
    },
    "mercury": {
        "planet": "Mercury",
        "metal": "Quicksilver / Brass",
        "minerals": ["Agate", "Fluorite", "Sodalite", "Aventurine", "Blue Lace Agate"],
        "herbs": ["Lavender", "Peppermint", "Dill", "Fennel", "Gotu Kola", "Valerian", "Lemongrass"],
        "rates": [8, 33, 44],
        "frequencies": [141.27, 448.0],
        "chakra": "Throat",
        "element": "Air",
        "day": "Wednesday",
        "moon_phase": "First Quarter",
        "archetypes": ["The Messenger", "The Magus", "Hermes", "Thoth", "Anubis"],
        "influence": "Communication, intellect, trading, technology, travel, translation of esoteric truth",
    },
    "venus": {
        "planet": "Venus",
        "metal": "Copper",
        "minerals": ["Rose Quartz", "Emerald", "Malachite", "Jade", "Rhodonite"],
        "herbs": ["Rose", "Yarrow", "Thyme", "Vanilla", "Cardamom", "Hibiscus", "Damiana"],
        "rates": [15, 22, 63],
        "frequencies": [221.23, 639.0],
        "chakra": "Heart",
        "element": "Earth / Water",
        "day": "Friday",
        "moon_phase": "Waxing Gibbous",
        "archetypes": ["The Lover", "The Divine Feminine", "Aphrodite", "Lakshmi", "Hathor"],
        "influence": "Compassion, beauty, harmonic relationships, artistic creation, prosperity, attraction",
    },
    "mars": {
        "planet": "Mars",
        "metal": "Iron",
        "minerals": ["Red Jasper", "Hematite", "Carnelian", "Bloodstone", "Garnet"],
        "herbs": ["Nettle", "Ginger", "Garlic", "Cayenne", "Black Pepper", "Dragon's Blood", "Basil"],
        "rates": [9, 16, 27],
        "frequencies": [144.72, 288.0],
        "chakra": "Root / Solar Plexus",
        "element": "Fire",
        "day": "Tuesday",
        "moon_phase": "Waxing Crescent",
        "archetypes": ["The Warrior", "The Protector", "Ares", "Kartikeya", "Archangel Michael"],
        "influence": "Courage, dynamic action, boundary defense, vitality, transformative fire, determination",
    },
    "jupiter": {
        "planet": "Jupiter",
        "metal": "Tin",
        "minerals": ["Lapis Lazuli", "Amethyst", "Blue Topaz", "Turquoise", "Sugilite"],
        "herbs": ["Sage", "Dandelion", "Borage", "Nutmeg", "Clove", "Hyssop", "Meadowsweet"],
        "rates": [3, 11, 84],
        "frequencies": [183.58, 888.0],
        "chakra": "Third Eye / Crown",
        "element": "Air / Fire",
        "day": "Thursday",
        "moon_phase": "Full Moon",
        "archetypes": ["The Guru", "The Hierophant", "Zeus", "Brihaspati", "Thor"],
        "influence": "Expansion, wisdom, benevolence, abundance, philosophical insight, spiritual luck",
    },
    "saturn": {
        "planet": "Saturn",
        "metal": "Lead",
        "minerals": ["Black Tourmaline", "Obsidian", "Onyx", "Smoky Quartz", "Shungite"],
        "herbs": ["Horsetail", "Comfrey", "Patchouli", "Cypress", "Myrrh", "Lobelia", "Solomon's Seal"],
        "rates": [4, 49, 88],
        "frequencies": [147.85, 396.0],
        "chakra": "Root",
        "element": "Earth",
        "day": "Saturday",
        "moon_phase": "Waning / Dark Moon",
        "archetypes": ["The Timekeeper", "The Hermit", "Cronus", "Yama", "Shani"],
        "influence": "Discipline, karmic resolution, structure, boundaries, deep grounding, endurance",
    },
    "uranus": {
        "planet": "Uranus",
        "metal": "Zinc / Platinum",
        "minerals": ["Aquamarine", "Amazonite", "Lepidolite", "Moldavite", "Labradorite"],
        "herbs": ["Gotu Kola", "Guarana", "Calamus", "Kava Kava", "Nutmeg"],
        "rates": [17, 62, 91],
        "frequencies": [207.36, 741.0],
        "chakra": "Crown / Brow",
        "element": "Air / Cosmic Ether",
        "day": "Wednesday",
        "moon_phase": "Disseminating Moon",
        "archetypes": ["The Awakener", "The Revolutionary", "Prometheus", "Ouranos"],
        "influence": "Sudden awakening, liberation, breakthrough insight, cosmic consciousness, originality",
    },
    "neptune": {
        "planet": "Neptune",
        "metal": "Bronze / Neptunium",
        "minerals": ["Amethyst", "Larimar", "Celestite", "Fluorite", "Aquamarine"],
        "herbs": ["Blue Lotus", "Damiana", "Mugwort", "Passionflower", "Skullcap"],
        "rates": [21, 57, 79],
        "frequencies": [211.44, 852.0],
        "chakra": "Third Eye / Soul Star",
        "element": "Water / Mystic Ether",
        "day": "Monday",
        "moon_phase": "Balsamic Moon",
        "archetypes": ["The Mystic", "The Dreamer", "Poseidon", "Avalokiteshvara"],
        "influence": "Spiritual transcendence, visionary dreams, universal compassion, ego dissolution",
    },
    "pluto": {
        "planet": "Pluto",
        "metal": "Tungsten / Plutonium",
        "minerals": ["Obsidian", "Black Diamond", "Garnet", "Stibnite", "Charoite"],
        "herbs": ["Black Cohosh", "Ashwagandha", "Wormwood", "Mandrake", "Elderberry"],
        "rates": [13, 39, 93],
        "frequencies": [140.25, 963.0],
        "chakra": "Earth Star / Kundalini Base",
        "element": "Fire / Nether Earth",
        "day": "Tuesday",
        "moon_phase": "New Moon",
        "archetypes": ["The Alchemist", "The Transformer", "Hades", "Kali", "Bhairava"],
        "influence": "Regeneration, rebirth, shadow integration, deep transmutation, primal kundalini power",
    },
}


class GrimoireService:
    """Multi-corpus esoteric knowledge and correspondence manager."""

    _instance: "GrimoireService | None" = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "GrimoireService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._knowledge_dir = self._resolve_knowledge_dir()
        self._tarot_cards: list[dict[str, Any]] = []
        self._iching_hexagrams: list[dict[str, Any]] = []
        self._mantras: list[dict[str, Any]] = []
        self._sutras: list[dict[str, Any]] = []
        self._frequencies: list[dict[str, Any]] = []
        self._healing_entries: list[dict[str, Any]] = []
        self._load_corpora()

    def _resolve_knowledge_dir(self) -> Path:
        """Find the root knowledge/ directory reliably."""
        candidates = [
            Path(__file__).resolve().parents[3] / "knowledge",
            Path.cwd() / "knowledge",
            Path(__file__).resolve().parents[2] / "knowledge",
        ]
        for c in candidates:
            if c.exists() and c.is_dir():
                return c
        return candidates[0]

    def _load_json_safe(self, filename: str) -> Any:
        path = self._knowledge_dir / filename
        if not path.exists():
            logger.warning("Knowledge file not found: %s", path)
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load knowledge file %s: %s", path, e)
            return None

    def _load_corpora(self) -> None:
        """Load and index JSON corpora into memory."""
        # 1. Tarot
        tarot_data = self._load_json_safe("tarot_deck.json")
        if tarot_data and isinstance(tarot_data, dict):
            self._tarot_cards = tarot_data.get("cards", [])

        # 2. I Ching
        iching_data = self._load_json_safe("iching.json")
        if iching_data and isinstance(iching_data, dict):
            self._iching_hexagrams = iching_data.get("hexagrams", [])

        # 3. Mantras & Dharanis
        mantras_list: list[dict[str, Any]] = []
        mantras_data = self._load_json_safe("mantras.json")
        if mantras_data and isinstance(mantras_data, dict):
            for tradition_key, tradition_val in mantras_data.items():
                if isinstance(tradition_val, dict):
                    for mantra_id, item in tradition_val.items():
                        if isinstance(item, dict):
                            entry = dict(item)
                            entry["id"] = f"mantra_{tradition_key}_{mantra_id}"
                            entry["category_key"] = tradition_key
                            mantras_list.append(entry)

        dharanis_data = self._load_json_safe("dharanis.json")
        if dharanis_data and isinstance(dharanis_data, list):
            for d in dharanis_data:
                if isinstance(d, dict):
                    entry = dict(d)
                    entry["id"] = f"dharani_{d.get('id', '')}"
                    entry["category_key"] = "dharani"
                    entry["meaning"] = d.get("purpose", "")
                    mantras_list.append(entry)

        self._mantras = mantras_list

        # 4. Sutras
        sutra_data = self._load_json_safe("sutra_passages.json")
        if sutra_data and isinstance(sutra_data, dict):
            self._sutras = sutra_data.get("sutra_passages", [])

        # 5. Frequencies
        freq_data = self._load_json_safe("frequencies.json")
        if freq_data and isinstance(freq_data, dict):
            freq_list = []
            for sub_cat, items in freq_data.items():
                if isinstance(items, dict):
                    for item_id, val in items.items():
                        if isinstance(val, dict):
                            entry = dict(val)
                            entry["id"] = f"freq_{sub_cat}_{item_id}"
                            entry["sub_category"] = sub_cat
                            freq_list.append(entry)
                elif isinstance(items, list):
                    for idx, val in enumerate(items):
                        if isinstance(val, dict):
                            entry = dict(val)
                            entry["id"] = f"freq_{sub_cat}_{idx}"
                            entry["sub_category"] = sub_cat
                            freq_list.append(entry)
            self._frequencies = freq_list

        # 6. Healing Knowledge
        healing_data = self._load_json_safe("healing_knowledge.json")
        if healing_data and isinstance(healing_data, dict):
            h_list = []
            for key, val in healing_data.items():
                if isinstance(val, dict):
                    for sub_id, item in val.items():
                        if isinstance(item, dict):
                            entry = dict(item)
                            entry["id"] = f"healing_{key}_{sub_id}"
                            entry["domain"] = key
                            h_list.append(entry)
            self._healing_entries = h_list

    def get_categories(self) -> list[dict[str, Any]]:
        """Return catalog of available corpora with counts and icons."""
        return [
            {
                "key": "all",
                "name": "All Correspondences",
                "icon": "🌟",
                "count": (
                    len(CORRESPONDENCES)
                    + len(self._tarot_cards)
                    + len(self._iching_hexagrams)
                    + len(self._mantras)
                    + len(self._sutras)
                    + len(self._frequencies)
                ),
                "description": "Unified esoteric knowledge across all cosmological systems",
            },
            {
                "key": "planets",
                "name": "Planetary Correspondences",
                "icon": "🪐",
                "count": len(CORRESPONDENCES),
                "description": "10 Planets, metals, crystals, herbs, radionics rates, and frequencies",
            },
            {
                "key": "tarot",
                "name": "Tarot Codex",
                "icon": "🃏",
                "count": len(self._tarot_cards),
                "description": "78 Rider-Waite-Smith cards with upright/reversed meanings and archetypes",
            },
            {
                "key": "iching",
                "name": "I Ching Book of Changes",
                "icon": "☯️",
                "count": len(self._iching_hexagrams),
                "description": "64 Hexagrams, trigram components, judgments, and line transformations",
            },
            {
                "key": "mantras",
                "name": "Mantras & Dharanis",
                "icon": "📿",
                "count": len(self._mantras),
                "description": "Sacred Buddhist & Vedic mantras, Bija syllables, and resonance tunings",
            },
            {
                "key": "sutras",
                "name": "Sacred Sutras",
                "icon": "📜",
                "count": len(self._sutras),
                "description": "Mahayana wisdom passages from Heart, Diamond, Lotus, and Sanghata sutras",
            },
            {
                "key": "frequencies",
                "name": "Healing & Frequencies",
                "icon": "💎",
                "count": len(self._frequencies) + len(self._healing_entries),
                "description": "Solfeggio, planetary, brainwave, organ meridians, and crystal therapies",
            },
        ]

    def get_planet_correspondences(self, name: str) -> dict[str, Any] | None:
        """Fetch correspondences for a specific planet."""
        name_lower = name.lower().strip()
        return CORRESPONDENCES.get(name_lower)

    def search(self, query: str, category: str | None = None) -> list[dict[str, Any]]:
        """Search across all grimoire corpora with optional category filtering."""
        query_lower = query.lower().strip()
        cat = category.lower().strip() if category else None
        if cat == "all":
            cat = None

        results: list[dict[str, Any]] = []

        # 1. Search Planets
        if cat is None or cat == "planets":
            for k, v in CORRESPONDENCES.items():
                match = not query_lower or (
                    query_lower in k
                    or query_lower in v["planet"].lower()
                    or query_lower in v.get("metal", "").lower()
                    or query_lower in v.get("element", "").lower()
                    or query_lower in v.get("chakra", "").lower()
                    or query_lower in v.get("influence", "").lower()
                    or any(query_lower in m.lower() for m in v.get("minerals", []))
                    or any(query_lower in h.lower() for h in v.get("herbs", []))
                    or any(query_lower in a.lower() for a in v.get("archetypes", []))
                )
                if match:
                    results.append(
                        {
                            "id": f"planet_{k}",
                            "category": "planets",
                            "title": f"🪐 {v['planet']}",
                            "subtitle": f"{v.get('chakra', '')} Chakra · {v.get('element', '')}",
                            "description": v.get("influence", ""),
                            "planet": v["planet"],
                            "metal": v.get("metal"),
                            "element": v.get("element"),
                            "chakra": v.get("chakra"),
                            "minerals": v.get("minerals", []),
                            "herbs": v.get("herbs", []),
                            "rates": v.get("rates", []),
                            "frequencies": v.get("frequencies", []),
                            "archetypes": v.get("archetypes", []),
                            "day": v.get("day"),
                            "moon_phase": v.get("moon_phase"),
                            "details": v,
                        }
                    )

        # 2. Search Tarot
        if cat is None or cat == "tarot":
            for c in self._tarot_cards:
                name = c.get("name", "")
                desc = c.get("desc", "")
                upright = c.get("upright", "")
                keywords = c.get("keywords", [])
                match = not query_lower or (
                    query_lower in name.lower()
                    or query_lower in desc.lower()
                    or query_lower in upright.lower()
                    or query_lower in c.get("arcana", "").lower()
                    or query_lower in c.get("element", "").lower()
                    or query_lower in c.get("ruler", "").lower()
                    or any(query_lower in kw.lower() for kw in keywords)
                )
                if match:
                    results.append(
                        {
                            "id": f"tarot_{c.get('id', name)}",
                            "category": "tarot",
                            "title": f"🃏 {name}",
                            "subtitle": f"{c.get('arcana', '').capitalize()} Arcana · {c.get('element', '')} · Ruler: {c.get('ruler', 'N/A')}",
                            "description": upright,
                            "keywords": keywords,
                            "element": c.get("element"),
                            "planet": c.get("ruler"),
                            "rates": [c.get("number", 0)],
                            "frequencies": [],
                            "minerals": [],
                            "herbs": [],
                            "details": c,
                        }
                    )

        # 3. Search I Ching
        if cat is None or cat == "iching":
            for h in self._iching_hexagrams:
                name = h.get("name", "")
                ch = h.get("chinese", "")
                eng = h.get("english", "")
                judgment = h.get("judgment", "")
                meaning = h.get("meaning", "")
                match = not query_lower or (
                    query_lower in name.lower()
                    or query_lower in eng.lower()
                    or query_lower in ch
                    or query_lower in judgment.lower()
                    or query_lower in meaning.lower()
                    or str(h.get("number", "")) == query_lower
                    or any(query_lower in kw.lower() for kw in h.get("keywords", []))
                )
                if match:
                    results.append(
                        {
                            "id": f"iching_{h.get('number', name)}",
                            "category": "iching",
                            "title": f"☯️ Hexagram {h.get('number')}: {ch} {name} ({eng})",
                            "subtitle": f"{h.get('upper_trigram')} above {h.get('lower_trigram')} · {h.get('element', '')}",
                            "description": judgment or meaning,
                            "keywords": h.get("keywords", []),
                            "element": h.get("element"),
                            "rates": [h.get("number", 0)],
                            "frequencies": [],
                            "minerals": [],
                            "herbs": [],
                            "details": h,
                        }
                    )

        # 4. Search Mantras
        if cat is None or cat == "mantras":
            for m in self._mantras:
                name = m.get("name", "")
                sanskrit = m.get("sanskrit", "")
                meaning = m.get("meaning", "")
                purpose = m.get("purpose", "")
                tradition = m.get("tradition", "")
                match = not query_lower or (
                    query_lower in name.lower()
                    or query_lower in sanskrit.lower()
                    or query_lower in meaning.lower()
                    or query_lower in purpose.lower()
                    or query_lower in tradition.lower()
                )
                if match:
                    freq = m.get("frequency_hz")
                    freqs = [freq] if freq else []
                    results.append(
                        {
                            "id": m.get("id", name),
                            "category": "mantras",
                            "title": f"📿 {name}",
                            "subtitle": f"{tradition} · Chakra: {m.get('chakra', 'Heart')}",
                            "description": f"{meaning} — {purpose}",
                            "chakra": m.get("chakra"),
                            "frequencies": freqs,
                            "rates": [],
                            "minerals": [],
                            "herbs": [],
                            "details": m,
                        }
                    )

        # 5. Search Sutras
        if cat is None or cat == "sutras":
            for s in self._sutras:
                sutra_title = s.get("sutra", "")
                chapter = s.get("chapter", "")
                passage = s.get("passage", "")
                theme = s.get("theme", "")
                tags = s.get("tags", [])
                match = not query_lower or (
                    query_lower in sutra_title.lower()
                    or query_lower in chapter.lower()
                    or query_lower in passage.lower()
                    or query_lower in theme.lower()
                    or any(query_lower in tag.lower() for tag in tags)
                )
                if match:
                    results.append(
                        {
                            "id": s.get("id", sutra_title),
                            "category": "sutras",
                            "title": f"📜 {sutra_title} — {chapter}",
                            "subtitle": f"Theme: {theme.capitalize()} · {s.get('sanskrit_name', '')}",
                            "description": passage[:320] + ("..." if len(passage) > 320 else ""),
                            "keywords": tags,
                            "frequencies": [],
                            "rates": [],
                            "minerals": [],
                            "herbs": [],
                            "details": s,
                        }
                    )

        # 6. Search Frequencies & Healing
        if cat is None or cat == "frequencies":
            for f in self._frequencies:
                label = f.get("label", f.get("name", ""))
                freq = f.get("freq", f.get("frequency", 0.0))
                desc = f.get("desc", f.get("description", f.get("purpose", "")))
                sub_cat = f.get("sub_category", "")
                match = not query_lower or (
                    query_lower in label.lower()
                    or query_lower in str(freq)
                    or query_lower in desc.lower()
                    or query_lower in sub_cat.lower()
                )
                if match:
                    results.append(
                        {
                            "id": f.get("id", label),
                            "category": "frequencies",
                            "title": f"💎 {label} ({freq} Hz)",
                            "subtitle": f"Category: {sub_cat.capitalize()}",
                            "description": desc,
                            "frequencies": [freq] if freq else [],
                            "rates": [],
                            "minerals": [],
                            "herbs": [],
                            "details": f,
                        }
                    )

        return results

    def get_all_in_category(self, category: str) -> list[dict[str, Any]]:
        """Return all items for a specific category without search filter."""
        return self.search("", category=category)

    def get_entry(self, category: str, entry_id: str) -> dict[str, Any] | None:
        """Find a single specific entry by ID."""
        for item in self.search("", category=category):
            if item.get("id") == entry_id or item.get("id") == f"{category}_{entry_id}":
                return item
        return None

    def get_planetary_hours(self, local_hour: int, weekday: int) -> dict[str, Any]:
        """
        Calculate traditional planetary hour correspondences.
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        day_rulers = ["moon", "mars", "mercury", "jupiter", "venus", "saturn", "sun"]
        chaldean = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]

        day_ruler = day_rulers[weekday % 7]
        start_idx = chaldean.index(day_ruler)
        hour_ruler_name = chaldean[(start_idx + local_hour) % 7]
        hour_ruler_data = CORRESPONDENCES[hour_ruler_name]

        return {
            "hour": local_hour,
            "day_ruler": CORRESPONDENCES[day_ruler]["planet"],
            "hour_ruler": hour_ruler_data["planet"],
            "metal": hour_ruler_data.get("metal", ""),
            "frequency_hz": hour_ruler_data.get("frequencies", [528.0])[0],
            "influence": hour_ruler_data.get("influence", ""),
            "herbs": hour_ruler_data.get("herbs", []),
            "minerals": hour_ruler_data.get("minerals", []),
            "rates": hour_ruler_data.get("rates", []),
        }


# Global singleton instance
grimoire_service = GrimoireService()
