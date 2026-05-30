"""
Grimoire & Correspondence Database — esoteric reference data service.

Manages a structured database of magical correspondences including planetary
associations, elemental attributes, colour symbolism, herbal and crystal
references, and ritual timing data. Used by the radionics operator and
outlook generator to enrich context with traditional esoteric knowledge.
"""

from typing import Any

CORRESPONDENCES = {
    "sun": {
        "planet": "Sun",
        "metal": "Gold",
        "minerals": ["Citrine", "Sunstone", "Amber", "Tiger's Eye"],
        "herbs": ["Chamomile", "St. John's Wort", "Calendula", "Frankincense", "Saffron", "Rosemary"],
        "rates": [19, 48, 81],
        "frequencies": [194.18, 528.0],
        "chakra": "Solar Plexus",
        "archetypes": ["The Sovereign", "The Solar Hero", "Apollo", "Helios"],
        "influence": "Vitality, growth, authority, consciousness, health",
    },
    "moon": {
        "planet": "Moon",
        "metal": "Silver",
        "minerals": ["Moonstone", "Pearl", "Selenite", "Labradorite"],
        "herbs": ["Jasmine", "Mugwort", "White Rose", "Lotus", "Myrrh", "Sandalwood"],
        "rates": [20, 52, 73],
        "frequencies": [210.42, 432.0],
        "chakra": "Sacral / Third Eye",
        "archetypes": ["The High Priestess", "The Lunar Mother", "Artemis", "Luna"],
        "influence": "Emotions, subconscious, intuition, dreams, protection",
    },
    "mercury": {
        "planet": "Mercury",
        "metal": "Quicksilver / Brass",
        "minerals": ["Agate", "Fluorite", "Sodalite", "Aventurine"],
        "herbs": ["Lavender", "Peppermint", "Dill", "Fennel", "Gotu Kola", "Valerian"],
        "rates": [8, 33, 44],
        "frequencies": [141.27, 448.0],
        "chakra": "Throat",
        "archetypes": ["The Messenger", "The Trickster", "Hermes", "Thoth"],
        "influence": "Communication, intellect, trade, technology, travel",
    },
    "venus": {
        "planet": "Venus",
        "metal": "Copper",
        "minerals": ["Rose Quartz", "Emerald", "Malachite", "Jade"],
        "herbs": ["Rose", "Yarrow", "Thyme", "Vanilla", "Cardamom", "Hibiscus"],
        "rates": [15, 22, 63],
        "frequencies": [221.23, 639.0],
        "chakra": "Heart",
        "archetypes": ["The Lover", "The Artist", "Aphrodite", "Lakshmi"],
        "influence": "Love, beauty, relationships, attraction, creativity, harmony",
    },
    "mars": {
        "planet": "Mars",
        "metal": "Iron",
        "minerals": ["Red Jasper", "Hematite", "Carnelian", "Bloodstone"],
        "herbs": ["Nettle", "Ginger", "Garlic", "Cayenne", "Black Pepper", "Dragon's Blood"],
        "rates": [9, 16, 27],
        "frequencies": [144.72, 288.0],
        "chakra": "Root / Solar Plexus",
        "archetypes": ["The Warrior", "The Defender", "Ares", "Kartikeya"],
        "influence": "Courage, action, drive, assertiveness, protection, fire",
    },
    "jupiter": {
        "planet": "Jupiter",
        "metal": "Tin",
        "minerals": ["Lapis Lazuli", "Amethyst", "Blue Topaz", "Turquoise"],
        "herbs": ["Sage", "Dandelion", "Borage", "Nutmeg", "Clove", "Hyssop"],
        "rates": [3, 11, 84],
        "frequencies": [183.58, 888.0],
        "chakra": "Third Eye / Crown",
        "archetypes": ["The Guru", "The Philosopher", "Zeus", "Brihaspati"],
        "influence": "Expansion, wisdom, luck, abundance, higher knowledge",
    },
    "saturn": {
        "planet": "Saturn",
        "metal": "Lead",
        "minerals": ["Black Tourmaline", "Obsidian", "Onyx", "Smoky Quartz"],
        "herbs": ["Horsetail", "Comfrey", "Patchouli", "Cypress", "Myrrh", "Lobelia"],
        "rates": [4, 49, 88],
        "frequencies": [147.85, 396.0],
        "chakra": "Root",
        "archetypes": ["The Cronus", "The Time-Keeper", "Yama", "Shani"],
        "influence": "Discipline, karma, boundaries, time, structure, grounding",
    },
}


class GrimoireService:
    """Esoteric database lookup manager"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def get_planet_correspondences(self, name: str) -> dict[str, Any] | None:
        """Fetch correspondences for a specific planet"""
        name_lower = name.lower().strip()
        return CORRESPONDENCES.get(name_lower)

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search the grimoire for matches in herbs, minerals, metals, or archetypes"""
        query_lower = query.lower().strip()
        results = []

        for k, v in CORRESPONDENCES.items():
            # Check fields
            if (
                query_lower in k
                or query_lower in v["planet"].lower()
                or query_lower in v["metal"].lower()
                or any(query_lower in m.lower() for m in v["minerals"])
                or any(query_lower in h.lower() for h in v["herbs"])
                or any(query_lower in a.lower() for a in v["archetypes"])
                or query_lower in v["chakra"].lower()
                or query_lower in v["influence"].lower()
            ):
                results.append(v)

        return results

    def get_planetary_hours(self, local_hour: int, weekday: int) -> dict[str, Any]:
        """
        Calculate traditional planetary hour correspondences
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        # Traditional Day Rulers
        day_rulers = ["moon", "mars", "mercury", "jupiter", "venus", "saturn", "sun"]
        # Chaldean Sequence (Hour Rulers: Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon)
        chaldean = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]

        day_ruler = day_rulers[weekday % 7]

        # Chaldean order index of day ruler
        start_idx = chaldean.index(day_ruler)
        # Shift Chaldean sequence based on local hour
        hour_ruler_name = chaldean[(start_idx + local_hour) % 7]

        hour_ruler_data = CORRESPONDENCES[hour_ruler_name]

        return {
            "hour": local_hour,
            "day_ruler": CORRESPONDENCES[day_ruler]["planet"],
            "hour_ruler": hour_ruler_data["planet"],
            "metal": hour_ruler_data["metal"],
            "frequency_hz": hour_ruler_data["frequencies"][0],
            "influence": hour_ruler_data["influence"],
            "herbs": hour_ruler_data["herbs"],
            "minerals": hour_ruler_data["minerals"],
        }


# Global instance
grimoire_service = GrimoireService()
