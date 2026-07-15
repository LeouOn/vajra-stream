"""
Divination Suite Service — Tarot, I Ching, and Geomancy readings.

Provides a unified interface for three divination systems:
- **Tarot** — 78-card Rider-Waite-Smith deck with spreads and interpretations.
- **I Ching** — 64 hexagrams with changing lines and classical commentary.
- **Geomancy** — 16 figures derived from random seed generation.
"""

import json
import random
import secrets
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------------
# Tarot deck — single source of truth is knowledge/tarot_deck.json
# ----------------------------------------------------------------------------


def _resolve_knowledge_path(filename: str) -> Path:
    """Resolve a knowledge/ file robustly from several candidate roots.

    divination_service.py lives at backend/core/services/; the knowledge dir
    sits at the project root. We probe a few ancestors so the loader works
    regardless of the working directory or how the module is imported.
    """
    candidates = [
        # backend/core/services/divination_service.py -> project root
        Path(__file__).resolve().parent.parent.parent.parent / "knowledge" / filename,
        # CWD-based fallback
        Path.cwd() / "knowledge" / filename,
        Path.cwd() / filename,
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    # Return the most likely default so the error message is helpful.
    return candidates[0]


TAROT_DECK_PATH = _resolve_knowledge_path("tarot_deck.json")

# Spread layouts keyed by draw count. Each entry carries:
#   - id:     1-based positional index (backward compat)
#   - name:   human-readable slot label (Past / Present / Future / ...)
#   - position: layout coordinate token used by the frontend renderer
#               ("center", "left", "right", "cross", "below", "above",
#                or "1".."10" for the Celtic Cross numbered stations)
#   - label:  short descriptive subtitle (backward compat)
# The 1-card Focus, 3-card Past/Present/Future, 5-card cross, and the
# 10-card Celtic Cross are the canonical spreads surfaced through the API.
SPREAD_POSITIONS: dict[int, list[dict[str, Any]]] = {
    1: [{"id": 1, "name": "Focus", "position": "center", "label": "The central issue"}],
    3: [
        {"id": 1, "name": "Past", "position": "left", "label": "What has been"},
        {"id": 2, "name": "Present", "position": "center", "label": "Where you are now"},
        {"id": 3, "name": "Future", "position": "right", "label": "What is coming"},
    ],
    5: [
        {"id": 1, "name": "Present", "position": "center", "label": "The heart of the matter"},
        {"id": 2, "name": "Challenge", "position": "cross", "label": "What crosses you"},
        {"id": 3, "name": "Past", "position": "below", "label": "Foundation beneath"},
        {"id": 4, "name": "Future", "position": "above", "label": "What crowns you"},
        {"id": 5, "name": "Advice", "position": "right", "label": "The way forward"},
    ],
    10: [
        {"id": 1, "name": "Present", "position": "1", "label": "The heart of the matter"},
        {"id": 2, "name": "Challenge", "position": "2", "label": "Crossing card"},
        {"id": 3, "name": "Foundation", "position": "3", "label": "Subconscious root"},
        {"id": 4, "name": "Recent Past", "position": "4", "label": "Passing influence"},
        {"id": 5, "name": "Crown", "position": "5", "label": "Conscious goal"},
        {"id": 6, "name": "Near Future", "position": "6", "label": "Coming into action"},
        {"id": 7, "name": "Self", "position": "7", "label": "Your attitude"},
        {"id": 8, "name": "Environment", "position": "8", "label": "External influences"},
        {"id": 9, "name": "Hopes & Fears", "position": "9", "label": "Hidden desires"},
        {"id": 10, "name": "Outcome", "position": "10", "label": "Final resolution"},
    ],
}

GEOMANTIC_FIGURES = {
    "Via": {
        "pattern": [1, 1, 1, 1],
        "translation": "The Way",
        "ruler": "Moon",
        "element": "Water",
        "meaning": "Movement, change, simplicity, flow",
    },
    "Populus": {
        "pattern": [2, 2, 2, 2],
        "translation": "The People",
        "ruler": "Moon",
        "element": "Water",
        "meaning": "Gathering, consensus, diffusion, passivity",
    },
    "Conjunctio": {
        "pattern": [2, 1, 1, 2],
        "translation": "The Conjunction",
        "ruler": "Mercury",
        "element": "Air",
        "meaning": "Union, meeting, agreement, logic",
    },
    "Albus": {
        "pattern": [2, 2, 1, 2],
        "translation": "The White",
        "ruler": "Mercury",
        "element": "Air",
        "meaning": "Wisdom, clarity, peace, purification",
    },
    "Amissio": {
        "pattern": [1, 2, 1, 2],
        "translation": "Loss",
        "ruler": "Venus",
        "element": "Earth",
        "meaning": "Letting go, financial loss, love gain, spiritual decay",
    },
    "Acquisitio": {
        "pattern": [2, 1, 2, 1],
        "translation": "Gain",
        "ruler": "Jupiter",
        "element": "Fire",
        "meaning": "Increase, wealth, expansion, success",
    },
    "Fortuna Major": {
        "pattern": [2, 2, 1, 1],
        "translation": "Greater Fortune",
        "ruler": "Sun",
        "element": "Fire",
        "meaning": "Inner victory, light, supreme success, protection",
    },
    "Fortuna Minor": {
        "pattern": [1, 1, 2, 2],
        "translation": "Lesser Fortune",
        "ruler": "Sun",
        "element": "Fire",
        "meaning": "External speed, quick success, unstable growth",
    },
    "Laetitia": {
        "pattern": [1, 2, 2, 2],
        "translation": "Joy",
        "ruler": "Jupiter",
        "element": "Air",
        "meaning": "Joy, laughter, expansion, good news, health",
    },
    "Tristitia": {
        "pattern": [2, 2, 2, 1],
        "translation": "Sorrow",
        "ruler": "Saturn",
        "element": "Earth",
        "meaning": "Sadness, structure, grounding, foundations, confinement",
    },
    "Puer": {
        "pattern": [1, 1, 2, 1],
        "translation": "The Boy",
        "ruler": "Mars",
        "element": "Fire",
        "meaning": "Impulsiveness, fight, vigor, initiative, anger",
    },
    "Puella": {
        "pattern": [1, 2, 1, 1],
        "translation": "The Girl",
        "ruler": "Venus",
        "element": "Water",
        "meaning": "Beauty, harmony, affection, superficial joy",
    },
    "Rubeus": {
        "pattern": [2, 1, 2, 2],
        "translation": "Red",
        "ruler": "Mars",
        "element": "Fire",
        "meaning": "Passion, blood, danger, warning, force",
    },
    "Carcer": {
        "pattern": [1, 2, 2, 1],
        "translation": "Prison",
        "ruler": "Saturn",
        "element": "Earth",
        "meaning": "Restriction, boundary, isolation, concentration, security",
    },
    "Caput Draconis": {
        "pattern": [2, 1, 1, 1],
        "translation": "Dragon's Head",
        "ruler": "North Node",
        "element": "Earth",
        "meaning": "Entry point, new beginnings, gain, spiritual growth",
    },
    "Cauda Draconis": {
        "pattern": [1, 1, 1, 2],
        "translation": "Dragon's Tail",
        "ruler": "South Node",
        "element": "Fire",
        "meaning": "Exit point, endings, purging, karma, decline",
    },
}


class DivinationService:
    """Calculates layouts and casts divination states using secure RNG values"""

    def __init__(self):
        self.deck = self._load_tarot_deck()
        self.iching = self._load_iching()

    def _load_tarot_deck(self) -> list[dict[str, Any]]:
        """Load the 78-card Tarot deck from knowledge/tarot_deck.json (single source of truth).

        Falls back to an empty deck if the file is missing so that import never fails hard;
        callers should detect the empty deck. Each card carries its full data record:
        id, name, arcana, number, element, keywords, upright, reversed, desc, and (for
        major) hebrew/ruler/zodiac, and (for minor) suit/rank.
        """
        try:
            with open(TAROT_DECK_PATH, encoding="utf-8") as f:
                data = json.load(f)
            cards = data.get("cards", [])
            if cards:
                return cards
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _load_iching(self) -> list[dict[str, Any]]:
        """Load the 64 I Ching hexagrams from knowledge/iching.json (single source of truth)."""
        try:
            iching_path = _resolve_knowledge_path("iching.json")
            with open(iching_path, encoding="utf-8") as f:
                data = json.load(f)
            hexagrams = data.get("hexagrams", [])
            if hexagrams:
                return hexagrams
        except (OSError, json.JSONDecodeError):
            pass
        return []

    @staticmethod
    def _secure_shuffle(items: list, seed: int | None = None) -> list:
        """Fisher–Yates shuffle. Uses ``secrets`` (CSPRNG) by default; when ``seed`` is
        provided, uses a deterministic ``random.Random`` instance so draws are reproducible
        (useful for tests, replays, and ritual re-cast)."""
        shuffled = list(items)
        n = len(shuffled)
        if seed is not None:
            rng = random.Random(seed)
            for i in range(n - 1, 0, -1):
                j = rng.randint(0, i)
                shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
            return shuffled
        # CSPRNG path: secrets-based Fisher–Yates
        for i in range(n - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
        return shuffled

    def draw_tarot(self, count: int = 1, seed: int | None = None) -> list[dict[str, Any]]:
        """Securely draws ``count`` cards from the deck with upright/reversed orientation.

        Each drawn card keeps full backward-compatible fields (``name``, ``svg``,
        ``reversed``, ``orientation``, ``meaning``, ``element``, ``hebrew``, ``ruler``)
        and additionally carries ``keywords``, ``desc`` and, when part of a known spread,
        a ``position`` mapping. When ``seed`` is given the draw is deterministic.

        Backward-compatible return shape: a list of card dicts (this preserves the contract
        used by outlook_generator, the LLM tools, and the API endpoint which wraps the list).
        """
        count = max(0, min(count, len(self.deck)))
        if count == 0:
            return []

        shuffled = self._secure_shuffle(self.deck, seed=seed)
        positions = SPREAD_POSITIONS.get(count, [])

        drawn = []
        for i in range(count):
            card = dict(shuffled[i])
            # The JSON holds both upright and reversed divinatory TEXT under the
            # ``upright`` / ``reversed`` keys. Extract them BEFORE we overwrite the
            # ``reversed`` key with the orientation boolean (kept for backward compat
            # — consumers like OperationsPanel read ``card.reversed`` as a bool).
            upright_text = card.get("upright", "")
            reversed_text = card.get("reversed", "")
            # Preserve the reversed meaning text under an unambiguous key.
            card["reversed_meaning"] = reversed_text
            # Draw orientation (reversed ~30% of the time).
            if seed is not None:
                is_reversed = random.Random(seed + i + 1).randint(0, 9) < 3
            else:
                is_reversed = secrets.randbelow(10) < 3
            card["reversed"] = is_reversed
            card["orientation"] = "reversed" if is_reversed else "upright"
            # Surface the matching meaning text for this orientation.
            card["meaning"] = reversed_text if is_reversed else upright_text
            card["svg"] = self._render_tarot_card_svg(card)
            if i < len(positions):
                card["position"] = positions[i]
            drawn.append(card)

        return drawn

    def draw_tarot_spread(self, count: int = 1, seed: int | None = None) -> dict[str, Any]:
        """Convenience wrapper returning the spread envelope (cards + spread metadata).

        The plain ``draw_tarot`` still returns a bare list for backward compatibility;
        this method returns the richer envelope that includes the spread layout.
        """
        cards = self.draw_tarot(count=count, seed=seed)
        return {
            "cards": cards,
            "count": len(cards),
            "spread": [dict(p) for p in SPREAD_POSITIONS.get(count, [])],
        }

    # Element -> neon glow color (preserves the existing neon aesthetic)
    _ELEMENT_COLORS = {
        "Water": "#00ffff",
        "Fire": "#ff00ff",
        "Earth": "#00ff00",
        "Air": "#ffea00",
    }

    # Standard playing-card pip layouts (x,y) for N pips in the central art region.
    # Centered at x=120, vertical span ~y130-y250.
    _PIP_LAYOUTS = {
        2: [(120, 145), (120, 235)],
        3: [(120, 135), (120, 190), (120, 245)],
        4: [(95, 150), (145, 150), (95, 230), (145, 230)],
        5: [(95, 150), (145, 150), (120, 190), (95, 230), (145, 230)],
        6: [(95, 140), (145, 140), (95, 190), (145, 190), (95, 240), (145, 240)],
        7: [(95, 135), (145, 135), (120, 165), (95, 205), (145, 205), (95, 245), (145, 245)],
        8: [(95, 135), (145, 135), (120, 162), (95, 200), (145, 200), (120, 218), (95, 245), (145, 245)],
        9: [(95, 135), (145, 135), (95, 175), (145, 175), (120, 190), (95, 205), (145, 205), (95, 245), (145, 245)],
        10: [
            (95, 130),
            (145, 130),
            (120, 155),
            (95, 180),
            (145, 180),
            (95, 200),
            (145, 200),
            (120, 225),
            (95, 250),
            (145, 250),
        ],
    }

    @classmethod
    def _glow_color(cls, element: str) -> str:
        return cls._ELEMENT_COLORS.get(element, "#ffea00")

    @staticmethod
    def _suit_symbol(suit: str, cx: float, cy: float, color: str, scale: float = 1.0) -> str:
        """Render a single suit pip at (cx, cy) with the neon aesthetic."""
        if suit == "Wands":
            return (
                f'<g transform="translate({cx} {cy}) scale({scale})">'
                f'<line x1="0" y1="-18" x2="0" y2="18" stroke="{color}" stroke-width="2.5" filter="url(#card-glow)"/>'
                f'<path d="M 0 -16 Q -7 -20 -9 -11 M 0 -16 Q 7 -20 9 -11" fill="none" stroke="{color}" stroke-width="1.4"/>'
                f'<path d="M 0 16 Q -5 20 -7 26 M 0 16 Q 5 20 7 26" fill="none" stroke="{color}" stroke-width="1.4"/>'
                f"</g>"
            )
        if suit == "Cups":
            return (
                f'<g transform="translate({cx} {cy}) scale({scale})">'
                f'<path d="M -12 -10 L 12 -10 L 8 6 L -8 6 Z" fill="none" stroke="{color}" stroke-width="2" filter="url(#card-glow)"/>'
                f'<line x1="-12" y1="-10" x2="12" y2="-10" stroke="{color}" stroke-width="2"/>'
                f'<line x1="0" y1="6" x2="0" y2="14" stroke="{color}" stroke-width="2"/>'
                f'<line x1="-9" y1="14" x2="9" y2="14" stroke="{color}" stroke-width="2"/>'
                f"</g>"
            )
        if suit == "Swords":
            return (
                f'<g transform="translate({cx} {cy}) scale({scale})">'
                f'<line x1="0" y1="-22" x2="0" y2="12" stroke="{color}" stroke-width="2.2" filter="url(#card-glow)"/>'
                f'<polygon points="0,-22 -4,-13 4,-13" fill="{color}"/>'
                f'<line x1="-10" y1="9" x2="10" y2="9" stroke="{color}" stroke-width="2.2"/>'
                f'<line x1="-5" y1="15" x2="5" y2="15" stroke="{color}" stroke-width="1.6"/>'
                f'<circle cx="0" cy="16" r="2" fill="{color}"/>'
                f"</g>"
            )
        # Pentacles: circle + inscribed pentagram
        return (
            f'<g transform="translate({cx} {cy}) scale({scale})">'
            f'<circle cx="0" cy="0" r="15" fill="none" stroke="{color}" stroke-width="1.8" filter="url(#card-glow)"/>'
            f'<polygon points="0,-12 7.05,9.7 -11.4,-3.7 11.4,-3.7 -7.05,9.7" fill="none" stroke="{color}" stroke-width="1.3"/>'
            f"</g>"
        )

    @classmethod
    def _minor_art(cls, card: dict[str, Any], color: str) -> str:
        """Render the central artwork for a Minor Arcana card as suit pips or a court figure."""
        suit = card.get("suit", "")
        rank = card.get("rank", "")
        # Court cards: large central symbol + crown to denote rank.
        if rank in ("Page", "Knight", "Queen", "King"):
            crown_y = 120
            figure_y = 200
            parts = [
                # Crown (denotes court status), style varies subtly by rank
                f'<path d="M {120 - 18} {crown_y + 8} L {120 - 18} {crown_y - 6} L {120 - 9} {crown_y + 2} '
                f"L {120} {crown_y - 10} L {120 + 9} {crown_y + 2} L {120 + 18} {crown_y - 6} "
                f'L {120 + 18} {crown_y + 8} Z" fill="none" stroke="{color}" stroke-width="1.8" filter="url(#card-glow)"/>',
                f'<text x="120" y="{crown_y + 24}" fill="{color}" font-size="9" font-family="monospace" text-anchor="middle" letter-spacing="2">{rank.upper()}</text>',
                cls._suit_symbol(suit, 120, figure_y, color, scale=1.7),
                # Rank tag
                f'<text x="120" y="245" fill="{color}" font-size="8" font-family="sans-serif" text-anchor="middle" opacity="0.8">OF {suit.upper()}</text>',
            ]
            return "\n  ".join(parts)
        # Ace: one large central symbol.
        if rank == "Ace" or card.get("number") == 1:
            return cls._suit_symbol(suit, 120, 190, color, scale=2.2)
        # Numbered 2-10: pip arrangement.
        n = card.get("number", 2)
        positions = cls._PIP_LAYOUTS.get(n, [(120, 190)])
        return "\n  ".join(cls._suit_symbol(suit, x, y, color, scale=1.0) for x, y in positions)

    @classmethod
    def _major_art(cls, number: int, color: str) -> str:
        """Render a unique central glyph for each of the 22 Major Arcana cards."""
        c = color
        # Build each glyph explicitly for clarity and uniqueness. All fragments
        # are centred around the art region (≈120, 190).
        if number == 0:  # The Fool
            return (
                f'<circle cx="180" cy="130" r="9" fill="none" stroke="{c}" stroke-width="1.6" filter="url(#card-glow)"/>'
                f'<path d="M 120 135 Q 130 150 145 160" fill="none" stroke="{c}" stroke-width="1.4"/>'  # wand
                f'<circle cx="120" cy="160" r="7" fill="none" stroke="{c}" stroke-width="1.5"/>'  # head
                f'<line x1="120" y1="167" x2="120" y2="195" stroke="{c}" stroke-width="1.8"/>'  # body
                f'<line x1="110" y1="215" x2="130" y2="215" stroke="{c}" stroke-width="2.2" filter="url(#card-glow)"/>'  # cliff
                f'<path d="M 95 215 L 95 250 L 145 250 L 145 215" fill="none" stroke="{c}" stroke-width="1.2" opacity="0.6"/>'  # rock
            )
        if number == 1:  # The Magician: infinity above table with 4 element marks
            return (
                f'<path d="M 105 135 Q 95 125 110 125 Q 120 125 120 135 Q 120 145 130 145 Q 145 145 135 135 Q 135 125 125 125 Q 120 125 120 135" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # lemniscate
                f'<rect x="80" y="220" width="80" height="40" fill="none" stroke="{c}" stroke-width="1.5"/>'  # table
                f'<circle cx="95" cy="240" r="4" fill="none" stroke="{c}" stroke-width="1.3"/>'  # cup
                f'<polygon points="145,236 142,244 148,244" fill="{c}"/>'  # sword
                f'<line x1="108" y1="234" x2="108" y2="246" stroke="{c}" stroke-width="1.5"/>'  # wand
                f'<polygon points="130,238 133,242 137,242 133.5,244.5 135,248 130,246 125,248 126.5,244.5 123,242 127,242" fill="none" stroke="{c}" stroke-width="1"/>'  # pentacle
            )
        if number == 2:  # The High Priestess: crescent moon + pillars
            return (
                f'<rect x="55" y="120" width="14" height="150" fill="none" stroke="{c}" stroke-width="1.6"/>'  # dark pillar
                f'<rect x="171" y="120" width="14" height="150" fill="none" stroke="{c}" stroke-width="1.6"/>'  # light pillar
                f'<path d="M 110 150 A 14 14 0 1 0 130 150 A 11 11 0 1 1 110 150 Z" fill="none" stroke="{c}" stroke-width="1.6" filter="url(#card-glow)"/>'  # crescent
                f'<rect x="108" y="185" width="24" height="30" fill="none" stroke="{c}" stroke-width="1.4"/>'  # scroll
                f'<line x1="112" y1="195" x2="128" y2="195" stroke="{c}" stroke-width="1"/><line x1="112" y1="202" x2="128" y2="202" stroke="{c}" stroke-width="1"/>'
            )
        if number == 3:  # The Empress: heart + wheat
            return (
                f'<path d="M 120 150 C 100 130 80 155 120 195 C 160 155 140 130 120 150 Z" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # heart
                f'<g transform="translate(120 225)">'
                f'<line x1="0" y1="0" x2="0" y2="20" stroke="{c}" stroke-width="1.6"/>'
                f'<path d="M 0 4 Q -8 2 -10 -2 M 0 10 Q -8 8 -10 4 M 0 16 Q -8 14 -10 10" fill="none" stroke="{c}" stroke-width="1"/>'
                f'<path d="M 0 4 Q 8 2 10 -2 M 0 10 Q 8 8 10 4 M 0 16 Q 8 14 10 10" fill="none" stroke="{c}" stroke-width="1"/>'
                f"</g>"
            )
        if number == 4:  # The Emperor: ram's horns / throne
            return (
                f'<rect x="95" y="155" width="50" height="70" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # throne
                f'<line x1="95" y1="155" x2="80" y2="140" stroke="{c}" stroke-width="1.4"/>'  # armrest
                f'<line x1="145" y1="155" x2="160" y2="140" stroke="{c}" stroke-width="1.4"/>'
                f'<path d="M 95 140 Q 80 140 78 152 Q 90 150 95 158" fill="none" stroke="{c}" stroke-width="1.5"/>'  # ram horn L
                f'<path d="M 145 140 Q 160 140 162 152 Q 150 150 145 158" fill="none" stroke="{c}" stroke-width="1.5"/>'  # ram horn R
                f'<circle cx="120" cy="130" r="6" fill="none" stroke="{c}" stroke-width="1.4"/>'  # crown orb
            )
        if number == 5:  # The Hierophant: triple cross
            return (
                f'<line x1="120" y1="120" x2="120" y2="250" stroke="{c}" stroke-width="2.2" filter="url(#card-glow)"/>'  # vertical
                f'<line x1="100" y1="150" x2="140" y2="150" stroke="{c}" stroke-width="2"/>'  # upper bar
                f'<line x1="105" y1="170" x2="135" y2="170" stroke="{c}" stroke-width="2"/>'  # middle bar
                f'<line x1="108" y1="190" x2="132" y2="190" stroke="{c}" stroke-width="2"/>'  # lower bar
                f'<path d="M 90 250 Q 120 240 150 250" fill="none" stroke="{c}" stroke-width="1.4"/>'  # base arch
            )
        if number == 6:  # The Lovers: two figures beneath an angel/sun
            return (
                f'<circle cx="120" cy="130" r="10" fill="none" stroke="{c}" stroke-width="1.6" filter="url(#card-glow)"/>'  # sun/angel
                f'<circle cx="95" cy="210" r="7" fill="none" stroke="{c}" stroke-width="1.5"/>'  # left head
                f'<line x1="95" y1="217" x2="95" y2="245" stroke="{c}" stroke-width="1.6"/>'  # left body
                f'<circle cx="145" cy="210" r="7" fill="none" stroke="{c}" stroke-width="1.5"/>'  # right head
                f'<line x1="145" y1="217" x2="145" y2="245" stroke="{c}" stroke-width="1.6"/>'  # right body
                f'<path d="M 102 225 Q 120 235 138 225" fill="none" stroke="{c}" stroke-width="1.3"/>'  # joining hands
            )
        if number == 7:  # The Chariot: winged wheel
            return (
                f'<circle cx="120" cy="200" r="26" fill="none" stroke="{c}" stroke-width="2" filter="url(#card-glow)"/>'  # wheel
                f'<line x1="120" y1="174" x2="120" y2="226" stroke="{c}" stroke-width="1.4"/>'  # spokes
                f'<line x1="94" y1="200" x2="146" y2="200" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="102" y1="182" x2="138" y2="218" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="138" y1="182" x2="102" y2="218" stroke="{c}" stroke-width="1.4"/>'
                f'<path d="M 95 165 Q 110 150 120 165 Q 130 150 145 165" fill="none" stroke="{c}" stroke-width="1.6"/>'  # wings/canopy
                f'<rect x="105" y="155" width="30" height="14" fill="none" stroke="{c}" stroke-width="1.4"/>'  # canopy box
            )
        if number == 8:  # Strength: lemniscate + lion hint
            return (
                f'<path d="M 100 130 Q 88 122 88 135 Q 88 148 105 142 Q 120 135 135 142 Q 152 148 152 135 Q 152 122 140 130 Q 130 138 120 135 Q 110 138 100 130 Z" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # lemniscate
                f'<circle cx="120" cy="210" r="30" fill="none" stroke="{c}" stroke-width="1.6"/>'  # lion mane
                f'<circle cx="120" cy="210" r="18" fill="none" stroke="{c}" stroke-width="1.3"/>'  # lion face
                f'<circle cx="112" cy="206" r="2" fill="{c}"/><circle cx="128" cy="206" r="2" fill="{c}"/>'  # eyes
                f'<path d="M 114 218 Q 120 222 126 218" fill="none" stroke="{c}" stroke-width="1.3"/>'  # mouth
            )
        if number == 9:  # The Hermit: lantern
            return (
                f'<line x1="120" y1="120" x2="120" y2="250" stroke="{c}" stroke-width="2" filter="url(#card-glow)"/>'  # staff
                f'<line x1="120" y1="135" x2="120" y2="120" stroke="{c}" stroke-width="2"/>'  # staff top
                f'<polygon points="105,150 135,150 130,175 110,175" fill="none" stroke="{c}" stroke-width="1.8"/>'  # lantern
                f'<polygon points="113,158 127,158 124,170 116,170" fill="{c}" opacity="0.8"/>'  # lantern light
                f'<path d="M 110 140 L 130 140" stroke="{c}" stroke-width="1.4"/>'  # lantern cap
                f'<circle cx="120" cy="120" r="5" fill="none" stroke="{c}" stroke-width="1.3"/>'  # hand
            )
        if number == 10:  # Wheel of Fortune: spoked wheel
            return (
                f'<circle cx="120" cy="190" r="38" fill="none" stroke="{c}" stroke-width="2" filter="url(#card-glow)"/>'
                f'<circle cx="120" cy="190" r="8" fill="none" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="120" y1="152" x2="120" y2="228" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="82" y1="190" x2="158" y2="190" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="93" y1="163" x2="147" y2="217" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="147" y1="163" x2="93" y2="217" stroke="{c}" stroke-width="1.4"/>'
                f'<polygon points="120,155 124,185 120,180 116,185" fill="{c}"/>'  # pointer
            )
        if number == 11:  # Justice: scales
            return (
                f'<line x1="120" y1="130" x2="120" y2="220" stroke="{c}" stroke-width="2.2" filter="url(#card-glow)"/>'  # stand
                f'<line x1="90" y1="150" x2="150" y2="150" stroke="{c}" stroke-width="2"/>'  # beam
                f'<line x1="90" y1="150" x2="90" y2="162" stroke="{c}" stroke-width="1.3"/>'  # left chain
                f'<line x1="150" y1="150" x2="150" y2="162" stroke="{c}" stroke-width="1.3"/>'  # right chain
                f'<path d="M 80 162 Q 90 175 100 162" fill="none" stroke="{c}" stroke-width="1.6"/>'  # left pan
                f'<path d="M 140 162 Q 150 175 160 162" fill="none" stroke="{c}" stroke-width="1.6"/>'  # right pan
                f'<line x1="95" y1="220" x2="145" y2="220" stroke="{c}" stroke-width="2"/>'  # base
                f'<line x1="120" y1="125" x2="120" y2="135" stroke="{c}" stroke-width="2"/>'  # sword hint top
            )
        if number == 12:  # The Hanged Man: inverted figure
            return (
                f'<line x1="90" y1="115" x2="150" y2="115" stroke="{c}" stroke-width="2.4" filter="url(#card-glow)"/>'  # gibbet
                f'<line x1="120" y1="115" x2="120" y2="140" stroke="{c}" stroke-width="1.6"/>'  # rope
                f'<circle cx="120" cy="148" r="6" fill="none" stroke="{c}" stroke-width="1.5"/>'  # head (lower)
                f'<line x1="120" y1="154" x2="120" y2="185" stroke="{c}" stroke-width="1.8"/>'  # torso
                f'<line x1="108" y1="175" x2="132" y2="175" stroke="{c}" stroke-width="1.6"/>'  # arms (crossed, inverted)
                f'<line x1="113" y1="185" x2="120" y2="205" stroke="{c}" stroke-width="1.6"/>'  # left leg
                f'<line x1="127" y1="185" x2="120" y2="205" stroke="{c}" stroke-width="1.6"/>'  # right leg
                f'<circle cx="120" cy="148" r="9" fill="none" stroke="{c}" stroke-width="1" opacity="0.6"/>'  # halo
            )
        if number == 13:  # Death: skull + banner
            return (
                f'<circle cx="120" cy="180" r="22" fill="none" stroke="{c}" stroke-width="2" filter="url(#card-glow)"/>'  # skull
                f'<circle cx="111" cy="177" r="4" fill="{c}"/>'  # left eye
                f'<circle cx="129" cy="177" r="4" fill="{c}"/>'  # right eye
                f'<path d="M 113 192 L 117 198 L 120 192 L 123 198 L 127 192" fill="none" stroke="{c}" stroke-width="1.3"/>'  # teeth
                f'<rect x="112" y="202" width="16" height="8" fill="none" stroke="{c}" stroke-width="1.3"/>'  # jaw
                f'<path d="M 95 145 Q 120 138 145 145 L 150 152 Q 120 160 90 152 Z" fill="none" stroke="{c}" stroke-width="1.5"/>'  # banner
            )
        if number == 14:  # Temperance: two cups + wings / flowing
            return (
                f'<path d="M 80 145 Q 100 135 120 145 Q 140 135 160 145" fill="none" stroke="{c}" stroke-width="1.6" filter="url(#card-glow)"/>'  # wings
                f'<path d="M 70 150 Q 85 140 95 150" fill="none" stroke="{c}" stroke-width="1.3"/>'
                f'<path d="M 145 150 Q 155 140 170 150" fill="none" stroke="{c}" stroke-width="1.3"/>'
                f'<path d="M 95 175 L 145 175 L 138 200 L 102 200 Z" fill="none" stroke="{c}" stroke-width="1.6"/>'  # left cup
                f'<path d="M 102 175 L 138 175" stroke="{c}" stroke-width="1.6"/>'
                f'<path d="M 95 180 Q 120 195 145 180" fill="none" stroke="{c}" stroke-width="1.4"/>'  # flowing water
                f'<path d="M 95 200 L 145 200" stroke="{c}" stroke-width="1.6"/>'  # right cup
                f'<path d="M 102 200 L 138 200 L 132 222 L 108 222 Z" fill="none" stroke="{c}" stroke-width="1.6"/>'
            )
        if number == 15:  # The Devil: inverted pentagram + horns
            return (
                f'<circle cx="120" cy="190" r="34" fill="none" stroke="{c}" stroke-width="1.6" filter="url(#card-glow)"/>'
                f'<polygon points="120,170 128,194 108,180 132,180 112,194" fill="none" stroke="{c}" stroke-width="1.8"/>'  # inverted pentagram
                f'<path d="M 92 145 Q 100 130 108 145" fill="none" stroke="{c}" stroke-width="1.6"/>'  # left horn
                f'<path d="M 132 145 Q 140 130 148 145" fill="none" stroke="{c}" stroke-width="1.6"/>'  # right horn
                f'<line x1="95" y1="240" x2="105" y2="225" stroke="{c}" stroke-width="1.4"/>'  # chain L
                f'<line x1="145" y1="240" x2="135" y2="225" stroke="{c}" stroke-width="1.4"/>'  # chain R
                f'<circle cx="100" cy="243" r="4" fill="none" stroke="{c}" stroke-width="1.3"/>'
                f'<circle cx="140" cy="243" r="4" fill="none" stroke="{c}" stroke-width="1.3"/>'
            )
        if number == 16:  # The Tower: lightning-struck tower
            return (
                f'<rect x="100" y="140" width="40" height="100" fill="none" stroke="{c}" stroke-width="2" filter="url(#card-glow)"/>'  # tower
                f'<polygon points="95,140 120,118 145,140" fill="none" stroke="{c}" stroke-width="1.8"/>'  # crown/roof
                f'<rect x="110" y="155" width="8" height="14" fill="none" stroke="{c}" stroke-width="1.3"/>'  # window
                f'<rect x="122" y="155" width="8" height="14" fill="none" stroke="{c}" stroke-width="1.3"/>'
                f'<polygon points="78,110 86,116 82,124 90,120 96,128" fill="none" stroke="{c}" stroke-width="1.8"/>'  # lightning bolt
                f'<line x1="86" y1="116" x2="120" y2="140" stroke="{c}" stroke-width="1.8"/>'  # bolt striking
                f'<circle cx="80" cy="250" r="3" fill="{c}"/><circle cx="160" cy="250" r="3" fill="{c}"/>'  # falling figures hint
            )
        if number == 17:  # The Star: 8-pointed star
            star_pts = []
            for i in range(16):
                ang = -90 + i * 22.5
                import math

                r = 30 if i % 2 == 0 else 13
                star_pts.append(
                    f"{120 + r * math.cos(math.radians(ang)):.1f},{190 + r * math.sin(math.radians(ang)):.1f}"
                )
            small_pts = []
            for i in range(8):
                ang = -90 + i * 45
                small_pts.append(
                    f"{120 + 50 * math.cos(math.radians(ang)):.1f},{190 + 50 * math.sin(math.radians(ang)):.1f}"
                )
            return (
                f'<polygon points="{" ".join(small_pts)}" fill="none" stroke="{c}" stroke-width="1" opacity="0.4"/>'  # outer ring of small stars
                f'<polygon points="{" ".join(star_pts)}" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # central 8-point star
                f'<path d="M 110 235 Q 120 250 130 235" fill="none" stroke="{c}" stroke-width="1.4"/>'  # water
                f'<line x1="100" y1="250" x2="140" y2="250" stroke="{c}" stroke-width="1.4"/>'
            )
        if number == 18:  # The Moon: crescent + drops/towers
            return (
                f'<circle cx="120" cy="170" r="28" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # full moon
                f'<path d="M 130 152 A 20 20 0 1 0 130 188 A 16 16 0 1 1 130 152 Z" fill="{c}" opacity="0.25"/>'  # inner crescent shadow
                f'<rect x="78" y="220" width="14" height="30" fill="none" stroke="{c}" stroke-width="1.4"/>'  # left tower
                f'<rect x="148" y="220" width="14" height="30" fill="none" stroke="{c}" stroke-width="1.4"/>'  # right tower
                f'<path d="M 105 215 Q 108 225 105 235 M 115 215 Q 118 228 114 240 M 125 215 Q 128 228 124 240 M 135 215 Q 138 225 135 235" fill="none" stroke="{c}" stroke-width="1.2"/>'  # dew drops
            )
        if number == 19:  # The Sun: radiant sun
            rays = ""
            for i in range(12):
                ang = i * 30
                rays += f'<line x1="120" y1="190" x2="120" y2="0" stroke="{c}" stroke-width="1.2" transform="rotate({ang} 120 190)" opacity="0.5"/>'
            return (
                rays
                + f'<circle cx="120" cy="190" r="34" fill="none" stroke="{c}" stroke-width="2" filter="url(#card-glow)"/>'  # sun face
                + f'<circle cx="110" cy="185" r="2.5" fill="{c}"/><circle cx="130" cy="185" r="2.5" fill="{c}"/>'  # eyes
                + f'<path d="M 108 200 Q 120 210 132 200" fill="none" stroke="{c}" stroke-width="1.6"/>'  # smile
                + f'<circle cx="120" cy="245" r="5" fill="none" stroke="{c}" stroke-width="1.3"/>'  # sunflower
            )
        if number == 20:  # Judgement: trumpet
            return (
                f'<path d="M 85 150 L 155 130 L 155 150 L 100 165 Z" fill="none" stroke="{c}" stroke-width="1.8" filter="url(#card-glow)"/>'  # trumpet bell
                f'<line x1="85" y1="150" x2="70" y2="155" stroke="{c}" stroke-width="1.6"/>'  # mouthpiece
                f'<line x1="155" y1="135" x2="165" y2="125" stroke="{c}" stroke-width="1.4"/>'
                f'<line x1="155" y1="145" x2="165" y2="155" stroke="{c}" stroke-width="1.4"/>'  # banner from trumpet
                f'<path d="M 155 145 Q 175 150 165 160" fill="none" stroke="{c}" stroke-width="1.4"/>'
                f'<rect x="95" y="210" width="50" height="35" fill="none" stroke="{c}" stroke-width="1.4"/>'  # coffin
                f'<line x1="105" y1="210" x2="105" y2="245" stroke="{c}" stroke-width="1"/>'  # figure rising
                f'<line x1="135" y1="210" x2="135" y2="245" stroke="{c}" stroke-width="1"/>'
                f'<path d="M 95 245 Q 120 250 145 245" fill="none" stroke="{c}" stroke-width="1.3"/>'  # ground
            )
        if number == 21:  # The World: dancer in wreath + 4 corner creatures
            import math

            wreath_pts = []
            for i in range(40):
                ang = i * 9
                r = 42 if i % 2 == 0 else 40
                wreath_pts.append(
                    f"{120 + r * math.cos(math.radians(ang)):.1f},{190 + r * math.sin(math.radians(ang)):.1f}"
                )
            return (
                f'<ellipse cx="120" cy="190" rx="44" ry="58" fill="none" stroke="{c}" stroke-width="1.6" filter="url(#card-glow)"/>'  # wreath
                f'<circle cx="120" cy="185" r="8" fill="none" stroke="{c}" stroke-width="1.5"/>'  # dancer head
                f'<line x1="120" y1="193" x2="120" y2="215" stroke="{c}" stroke-width="1.8"/>'  # body
                f'<line x1="108" y1="205" x2="132" y2="205" stroke="{c}" stroke-width="1.6"/>'  # arms
                f'<line x1="113" y1="215" x2="120" y2="232" stroke="{c}" stroke-width="1.5"/>'  # leg sash
                f'<line x1="127" y1="215" x2="120" y2="232" stroke="{c}" stroke-width="1.5"/>'
                # four corner creatures (lion, eagle, bull, angel) as small symbols
                f'<text x="70" y="135" fill="{c}" font-size="11" text-anchor="middle">♂</text>'  # corner marks
                f'<text x="170" y="135" fill="{c}" font-size="11" text-anchor="middle">♔</text>'
                f'<text x="70" y="255" fill="{c}" font-size="11" text-anchor="middle">♉</text>'
                f'<text x="170" y="255" fill="{c}" font-size="11" text-anchor="middle">♎</text>'
            )
        return ""  # fallback

    def _render_tarot_card_svg(self, card: dict[str, Any]) -> str:
        """Renders a neon vector representation of the Tarot card.

        Major Arcana cards each receive a unique central glyph; Minor Arcana cards
        render their suit pips in traditional playing-card arrangements (Aces show
        one large pip, court cards a crowned figure). Reversed cards rotate the
        central artwork 180° around the card centre (the border, Hebrew/ruler
        indicators, title and orientation label stay upright so the card remains
        legible).
        """
        name = card["name"]
        element = card["element"]
        hebrew = card.get("hebrew", "")
        ruler = card.get("ruler", "")
        orientation = card["orientation"]
        arcana = card.get("arcana", "major")
        color = self._glow_color(element)
        is_reversed = orientation == "reversed"

        # Build the central artwork.
        if arcana == "minor":
            art = self._minor_art(card, color)
        else:
            art = self._major_art(card.get("number", 0), color)

        # Wrap the artwork in a 180° rotation group when reversed.
        if is_reversed:
            art = f'<g transform="rotate(180 120 190)">\n  {art}\n  </g>'

        svg = f"""<svg viewBox="0 0 240 380" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background:#0b132b; border-radius:16px;">
  <defs>
    <filter id="card-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <!-- Card Border -->
  <rect x="10" y="10" width="220" height="360" rx="12" fill="none" stroke="{color}" stroke-width="2" filter="url(#card-glow)"/>

  <!-- Astrological/Hebrew Letter Indicators -->
  {f'<text x="25" y="35" fill="{color}" font-size="12" font-family="monospace">{hebrew}</text>' if hebrew else ""}
  {f'<text x="215" y="35" fill="{color}" font-size="12" font-family="monospace" text-anchor="end">{ruler}</text>' if ruler else ""}

  <!-- Central Artwork{" (rotated 180 — reversed)" if is_reversed else ""} -->
  {art}

  <!-- Title -->
  <text x="120" y="320" fill="#ffffff" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">{name}</text>
  <text x="120" y="340" fill="{color}" font-size="10" font-family="sans-serif" text-anchor="middle" letter-spacing="1.5">{orientation.upper()} ({element.upper()})</text>
</svg>"""
        return svg

    def cast_i_ching(self) -> dict[str, Any]:
        """Casts an I Ching hexagram line by line using yarrow probabilities"""
        lines = []
        # Draw 6 lines bottom-up (line 1 to line 6)
        for _ in range(6):
            # Yarrow probabilities:
            # 6: Old Yin (changing) -> 1/16
            # 7: Young Yang -> 5/16
            # 8: Young Yin -> 7/16
            # 9: Old Yang (changing) -> 3/16
            rnd = secrets.randbelow(16)
            if rnd == 0:
                line_val = 6
            elif rnd <= 5:
                line_val = 7
            elif rnd <= 12:
                line_val = 8
            else:
                line_val = 9
            lines.append(line_val)

        # Compile hexagram patterns
        primary_pattern = [1 if (v == 7 or v == 9) else 0 for v in lines]
        relating_pattern = [1 if (v == 7 or v == 8) else (0 if v == 6 else 1) for v in lines]  # Change changing lines

        changing_indices = [i + 1 for i, v in enumerate(lines) if v == 6 or v == 9]

        primary_details = self._get_hexagram_details(primary_pattern)
        relating_details = self._get_hexagram_details(relating_pattern)

        # Resolve changing line details
        changing_lines_details = []
        for idx in changing_indices:
            line_idx = idx - 1
            line_val = lines[line_idx]
            line_meaning = (
                primary_details["lines"][line_idx]
                if primary_details.get("lines") and len(primary_details["lines"]) > line_idx
                else ""
            )
            changing_lines_details.append(
                {
                    "line": idx,
                    "value": line_val,
                    "type": "Old Yin" if line_val == 6 else "Old Yang",
                    "meaning": line_meaning,
                }
            )

        return {
            "cast_lines": lines,
            "primary": primary_details,
            "relating": relating_details,
            "changing_lines": changing_indices,
            "changing_lines_details": changing_lines_details,
            "has_changes": len(changing_indices) > 0,
            "svg": self._render_hexagram_svg(primary_pattern, relating_pattern, lines),
        }

    def _get_hexagram_details(self, pattern: list[int]) -> dict[str, Any]:
        # Compact mapping of binary values to standard hexagrams
        bin_str = "".join(str(b) for b in pattern)

        # 1. Try finding in loaded JSON database
        if hasattr(self, "iching") and self.iching:
            for hexagram in self.iching:
                if hexagram.get("pattern") == bin_str:
                    full_name = f"{hexagram['name_pinyin']} / {hexagram['name_english']}"
                    return {
                        "pattern": bin_str,
                        "name": full_name,
                        "name_chinese": hexagram["name_chinese"],
                        "name_pinyin": hexagram["name_pinyin"],
                        "name_english": hexagram["name_english"],
                        "meaning": hexagram["meaning"],
                        "judgment": hexagram["judgment"],
                        "images": hexagram["images"],
                        "lines": hexagram["lines"],
                    }

        # 2. Defensive fallback (unreachable in practice: iching.json ships all 64
        #        binary patterns, so the loop above always returns).
        return {
            "pattern": bin_str,
            "name": "Unknown Hexagram",
            "name_chinese": "",
            "name_pinyin": "Unknown",
            "name_english": "Unknown Hexagram",
            "meaning": "Esoteric transformation",
            "judgment": "Esoteric transformation",
            "images": "",
            "lines": [],
        }

    def _render_hexagram_svg(self, primary: list[int], relating: list[int], raw_lines: list[int]) -> str:
        """Renders the primary and relating hexagrams side by side"""
        width = 400
        height = 200

        # Primary line segments (draw bottom to top)
        svg_lines = []
        for i, val in enumerate(reversed(raw_lines)):
            y = 35 + i * 25
            is_yang = val == 7 or val == 9
            is_changing = val == 6 or val == 9

            # Primary line
            color = "#00ffff" if is_yang else "#ff00ff"
            glow = 'filter="url(#hex-glow)"' if is_changing else ""

            if is_yang:
                svg_lines.append(f'<line x1="40" y1="{y}" x2="160" y2="{y}" stroke="{color}" stroke-width="7" {glow}/>')
            else:
                svg_lines.append(f'<line x1="40" y1="{y}" x2="90" y2="{y}" stroke="{color}" stroke-width="7" {glow}/>')
                svg_lines.append(
                    f'<line x1="110" y1="{y}" x2="160" y2="{y}" stroke="{color}" stroke-width="7" {glow}/>'
                )

            # Changing indicator
            if is_changing:
                svg_lines.append(f'<circle cx="100" cy="{y}" r="4" fill="#ffffff" filter="url(#hex-glow)"/>')

        # Relating line segments
        for i, val in enumerate(reversed(relating)):
            y = 35 + i * 25
            is_yang = val == 1
            color = "#00ff00"

            if is_yang:
                svg_lines.append(f'<line x1="240" y1="{y}" x2="360" y2="{y}" stroke="{color}" stroke-width="7"/>')
            else:
                svg_lines.append(f'<line x1="240" y1="{y}" x2="290" y2="{y}" stroke="{color}" stroke-width="7"/>')
                svg_lines.append(f'<line x1="310" y1="{y}" x2="360" y2="{y}" stroke="{color}" stroke-width="7"/>')

        lines_svg = "\n  ".join(svg_lines)

        svg = f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:#080e1a; border-radius:12px;">
  <defs>
    <filter id="hex-glow" filterUnits="userSpaceOnUse" x="0" y="0" width="400" height="200">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <!-- Titles -->
  <text x="100" y="20" fill="#ffffff" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">PRIMARY</text>
  <text x="300" y="20" fill="#ffffff" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">RELATING</text>

  <!-- Line Drawings -->
  {lines_svg}
</svg>"""
        return svg

    def cast_geomancy(self) -> dict[str, Any]:
        """Casts a complete Geomantic Shield Chart from 4 Mothers"""
        # Generate 4 random Mothers (each line 1 or 2 dots)
        mothers = {}
        for i in range(1, 5):
            mothers[f"Mother {i}"] = [secrets.randbelow(2) + 1 for _ in range(4)]

        # Daughters 1-4
        daughters = {}
        for i in range(1, 5):
            # Line index mapping
            daughters[f"Daughter {i}"] = [
                mothers["Mother 1"][i - 1],
                mothers["Mother 2"][i - 1],
                mothers["Mother 3"][i - 1],
                mothers["Mother 4"][i - 1],
            ]

        # Helpers to add figures
        def add_figures(fig_a: list[int], fig_b: list[int]) -> list[int]:
            return [2 if (a + b) % 2 == 0 else 1 for a, b in zip(fig_a, fig_b)]

        # Nieces 1-4
        nieces = {
            "Niece 1": add_figures(mothers["Mother 1"], mothers["Mother 2"]),
            "Niece 2": add_figures(mothers["Mother 3"], mothers["Mother 4"]),
            "Niece 3": add_figures(daughters["Daughter 1"], daughters["Daughter 2"]),
            "Niece 4": add_figures(daughters["Daughter 3"], daughters["Daughter 4"]),
        }

        # Witnesses
        right_witness = add_figures(nieces["Niece 1"], nieces["Niece 2"])
        left_witness = add_figures(nieces["Niece 3"], nieces["Niece 4"])

        # Judge
        judge = add_figures(right_witness, left_witness)

        # Reconciler
        reconciler = add_figures(mothers["Mother 1"], judge)

        # Assemble shield chart list
        all_figures = {}
        all_figures.update(mothers)
        all_figures.update(daughters)
        all_figures.update(nieces)
        all_figures["Right Witness"] = right_witness
        all_figures["Left Witness"] = left_witness
        all_figures["Judge"] = judge
        all_figures["Reconciler"] = reconciler

        # Resolve names and meanings
        resolved = {}
        for name, pattern in all_figures.items():
            fig_name, details = self._get_geomancy_figure_details(pattern)
            resolved[name] = {
                "pattern": pattern,
                "name": fig_name,
                "translation": details["translation"],
                "ruler": details["ruler"],
                "element": details["element"],
                "meaning": details["meaning"],
            }

        # Project into 12 Astrological Houses
        # House 1 = Mother 1, House 2 = Mother 2, etc.
        house_mapping = {
            1: resolved["Mother 1"],
            2: resolved["Mother 2"],
            3: resolved["Mother 3"],
            4: resolved["Mother 4"],
            5: resolved["Daughter 1"],
            6: resolved["Daughter 2"],
            7: resolved["Daughter 3"],
            8: resolved["Daughter 4"],
            9: resolved["Niece 1"],
            10: resolved["Niece 2"],
            11: resolved["Niece 3"],
            12: resolved["Niece 4"],
        }

        return {"figures": resolved, "houses": house_mapping, "svg": self._render_geomancy_shield_svg(resolved)}

    def _get_geomancy_figure_details(self, pattern: list[int]) -> tuple[str, dict[str, Any]]:
        for name, data in GEOMANTIC_FIGURES.items():
            if data["pattern"] == pattern:
                return name, data
        return "Unknown", {
            "translation": "Mystery",
            "ruler": "Cosmos",
            "element": "Spirit",
            "meaning": "Divine alignment",
        }

    def _render_geomancy_shield_svg(self, resolved: dict[str, Any]) -> str:
        """Generates a complex visual representation of the geomantic shield chart"""
        width = 500
        height = 300

        # Draw a hierarchy tree matching the shield chart logic
        # Positions:
        # row 1 (top): Mothers 1-4, Daughters 1-4
        # row 2: Nieces 1-4
        # row 3: Witnesses
        # row 4 (bottom): Judge

        def render_dots(pat: list[int], cx: float, cy: float, color: str) -> str:
            dots_svg = []
            for idx, count in enumerate(pat):
                dy = cy - 20 + idx * 12
                if count == 1:
                    dots_svg.append(f'<circle cx="{cx}" cy="{dy}" r="3" fill="{color}"/>')
                else:
                    dots_svg.append(f'<circle cx="{cx - 6}" cy="{dy}" r="3" fill="{color}"/>')
                    dots_svg.append(f'<circle cx="{cx + 6}" cy="{dy}" r="3" fill="{color}"/>')
            return "\n".join(dots_svg)

        fig_positions = [
            # Top Row: Mothers & Daughters (indices 1-8)
            ("Mother 1", 30, 60, "#00ffff"),
            ("Mother 2", 85, 60, "#00ffff"),
            ("Mother 3", 140, 60, "#00ffff"),
            ("Mother 4", 195, 60, "#00ffff"),
            ("Daughter 1", 260, 60, "#ff00ff"),
            ("Daughter 2", 315, 60, "#ff00ff"),
            ("Daughter 3", 370, 60, "#ff00ff"),
            ("Daughter 4", 425, 60, "#ff00ff"),
            # Second Row: Nieces (indices 9-12)
            ("Niece 1", 57, 140, "#00ff00"),
            ("Niece 2", 167, 140, "#00ff00"),
            ("Niece 3", 287, 140, "#00ff00"),
            ("Niece 4", 397, 140, "#00ff00"),
            # Third Row: Witnesses (indices 13-14)
            ("Right Witness", 112, 210, "#ffea00"),
            ("Left Witness", 342, 210, "#ffea00"),
            # Bottom Row: Judge
            ("Judge", 227, 270, "#ffffff"),
        ]

        shapes = []
        for name, x, y, color in fig_positions:
            pat = resolved[name]["pattern"]
            fig_name = resolved[name]["name"]

            # Card Container
            shapes.append(f"""
  <!-- {name} container -->
  <rect x="{x - 22}" y="{y - 32}" width="44" height="64" rx="4" fill="none" stroke="{color}" stroke-width="1" opacity="0.3"/>
  <text x="{x}" y="{y - 35}" fill="{color}" font-size="7" font-family="sans-serif" text-anchor="middle">{fig_name}</text>
  {render_dots(pat, x, y, color)}
            """)

        # Draw connector lines showing structure sum
        connectors = [
            # Row 1 to Row 2
            (30, 60, 85, 60, 57, 140),  # M1 + M2 -> N1
            (140, 60, 195, 60, 167, 140),  # M3 + M4 -> N2
            (260, 60, 315, 60, 287, 140),  # D1 + D2 -> N3
            (370, 60, 425, 60, 397, 140),  # D3 + D4 -> N4
            # Row 2 to Row 3
            (57, 140, 167, 140, 112, 210),  # N1 + N2 -> RW
            (287, 140, 397, 140, 342, 210),  # N3 + N4 -> LW
            # Row 3 to Row 4
            (112, 210, 342, 210, 227, 270),  # RW + LW -> J
        ]

        lines = []
        for x1, y1, x2, y2, tx, ty in connectors:
            lines.append(
                f'<path d="M {x1} {y1 + 32} L {tx} {ty - 32} M {x2} {y2 + 32} L {tx} {ty - 32}" stroke="#334155" stroke-width="1.2" stroke-dasharray="2,2"/>'
            )

        lines_svg = "\n  ".join(lines)
        shapes_svg = "\n".join(shapes)

        svg = f"""<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:#070d19; border-radius:16px;">
  <!-- Connecting Links -->
  {lines_svg}

  <!-- Rendered Figures -->
  {shapes_svg}
</svg>"""
        return svg


# Global instance
divination_service = DivinationService()
