"""
Divination Suite Service (Tarot, I Ching, Geomancy)
"""

import random
import secrets
from typing import Any

# Minimal definitions for Tarot card registry to save space while providing rich symbols
TAROT_MAJOR = {
    0: {
        "name": "The Fool",
        "element": "Air",
        "hebrew": "Aleph",
        "ruler": "Uranus",
        "meaning": "New beginnings, spontaneous adventure, faith",
    },
    1: {
        "name": "The Magician",
        "element": "Air",
        "hebrew": "Beth",
        "ruler": "Mercury",
        "meaning": "Willpower, manifestation, resourcefulness",
    },
    2: {
        "name": "The High Priestess",
        "element": "Water",
        "hebrew": "Gimel",
        "ruler": "Moon",
        "meaning": "Intuition, sacred secrets, subconscious",
    },
    3: {
        "name": "The Empress",
        "element": "Earth",
        "hebrew": "Daleth",
        "ruler": "Venus",
        "meaning": "Abundance, creativity, nature, mothering",
    },
    4: {
        "name": "The Emperor",
        "element": "Fire",
        "hebrew": "Heh",
        "ruler": "Aries",
        "meaning": "Structure, authority, fathering, discipline",
    },
    5: {
        "name": "The Hierophant",
        "element": "Earth",
        "hebrew": "Vav",
        "ruler": "Taurus",
        "meaning": "Tradition, spiritual guidance, conformity",
    },
    6: {
        "name": "The Lovers",
        "element": "Air",
        "hebrew": "Zayin",
        "ruler": "Gemini",
        "meaning": "Alignment of values, choices, harmony",
    },
    7: {
        "name": "The Chariot",
        "element": "Water",
        "hebrew": "Heth",
        "ruler": "Cancer",
        "meaning": "Determination, control, victory over obstacles",
    },
    8: {
        "name": "Strength",
        "element": "Fire",
        "hebrew": "Teth",
        "ruler": "Leo",
        "meaning": "Inner strength, patience, compassion",
    },
    9: {
        "name": "The Hermit",
        "element": "Earth",
        "hebrew": "Yod",
        "ruler": "Virgo",
        "meaning": "Inner guidance, solitude, introspection",
    },
    10: {
        "name": "Wheel of Fortune",
        "element": "Fire",
        "hebrew": "Kaph",
        "ruler": "Jupiter",
        "meaning": "Good luck, cycles of change, destiny",
    },
    11: {
        "name": "Justice",
        "element": "Air",
        "hebrew": "Lamed",
        "ruler": "Libra",
        "meaning": "Fairness, truth, law, cause and effect",
    },
    12: {
        "name": "The Hanged Man",
        "element": "Water",
        "hebrew": "Mem",
        "ruler": "Neptune",
        "meaning": "Surrender, release, new perspective",
    },
    13: {
        "name": "Death",
        "element": "Water",
        "hebrew": "Nun",
        "ruler": "Scorpio",
        "meaning": "Endings, transition, regeneration",
    },
    14: {
        "name": "Temperance",
        "element": "Fire",
        "hebrew": "Samekh",
        "ruler": "Sagittarius",
        "meaning": "Balance, alchemy, moderation",
    },
    15: {
        "name": "The Devil",
        "element": "Earth",
        "hebrew": "Ayin",
        "ruler": "Capricorn",
        "meaning": "Bondage, shadow self, materialism",
    },
    16: {
        "name": "The Tower",
        "element": "Fire",
        "hebrew": "Peh",
        "ruler": "Mars",
        "meaning": "Sudden upheaval, revelation, breakdown",
    },
    17: {
        "name": "The Star",
        "element": "Air",
        "hebrew": "Tzaddi",
        "ruler": "Aquarius",
        "meaning": "Hope, renewal, cosmic inspiration",
    },
    18: {
        "name": "The Moon",
        "element": "Water",
        "hebrew": "Qoph",
        "ruler": "Pisces",
        "meaning": "Illusion, fear, subconscious guidance",
    },
    19: {
        "name": "The Sun",
        "element": "Fire",
        "hebrew": "Resh",
        "ruler": "Sun",
        "meaning": "Vitality, warmth, success, truth",
    },
    20: {
        "name": "Judgement",
        "element": "Fire/Spirit",
        "hebrew": "Shin",
        "ruler": "Pluto",
        "meaning": "Awakening, rebirth, inner calling",
    },
    21: {
        "name": "The World",
        "element": "Earth",
        "hebrew": "Tav",
        "ruler": "Saturn",
        "meaning": "Completion, integration, travel",
    },
}

SUITS = ["Wands", "Cups", "Swords", "Pentacles"]
SUIT_ELEMENTS = {"Wands": "Fire", "Cups": "Water", "Swords": "Air", "Pentacles": "Earth"}
COURTS = ["Page", "Knight", "Queen", "King"]

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
        self.deck = self._build_tarot_deck()

    def _build_tarot_deck(self) -> list[dict[str, Any]]:
        deck = []
        # Add Major Arcana
        for key, val in TAROT_MAJOR.items():
            card = {
                "id": f"major_{key}",
                "name": val["name"],
                "arcana": "major",
                "number": key,
                "element": val["element"],
                "hebrew": val["hebrew"],
                "ruler": val["ruler"],
                "meaning": val["meaning"],
            }
            deck.append(card)

        # Add Minor Arcana
        for suit in SUITS:
            element = SUIT_ELEMENTS[suit]
            # Aces
            deck.append(
                {
                    "id": f"minor_{suit.lower()}_1",
                    "name": f"Ace of {suit}",
                    "arcana": "minor",
                    "number": 1,
                    "suit": suit,
                    "element": element,
                    "meaning": f"Core seed of {element} energy, potential, inspiration",
                }
            )
            # 2 to 10
            for i in range(2, 11):
                deck.append(
                    {
                        "id": f"minor_{suit.lower()}_{i}",
                        "name": f"{i} of {suit}",
                        "arcana": "minor",
                        "number": i,
                        "suit": suit,
                        "element": element,
                        "meaning": f"Numeric manifestation of {suit} energy: stage {i}",
                    }
                )
            # Courts
            for idx, court in enumerate(COURTS, 11):
                deck.append(
                    {
                        "id": f"minor_{suit.lower()}_{court.lower()}",
                        "name": f"{court} of {suit}",
                        "arcana": "minor",
                        "number": idx,
                        "suit": suit,
                        "element": element,
                        "meaning": f"Personification of {court} energy in the realm of {suit}",
                    }
                )
        return deck

    def draw_tarot(self, count: int = 1) -> list[dict[str, Any]]:
        """Securely draws cards from the deck, including card orientations (reversed or upright)"""
        shuffled = list(self.deck)
        random.shuffle(shuffled)

        drawn = []
        for i in range(min(count, len(shuffled))):
            card = dict(shuffled[i])
            # Draw orientation (reversed with 30% chance)
            is_reversed = secrets.randbelow(10) < 3
            card["reversed"] = is_reversed
            card["orientation"] = "reversed" if is_reversed else "upright"
            card["svg"] = self._render_tarot_card_svg(card)
            drawn.append(card)

        return drawn

    def _render_tarot_card_svg(self, card: dict[str, Any]) -> str:
        """Draws a beautiful neon vector representation of the Tarot card"""
        name = card["name"]
        element = card["element"]
        hebrew = card.get("hebrew", "")
        ruler = card.get("ruler", "")
        orientation = card["orientation"]

        glow_color = (
            "#00ffff"
            if element == "Water"
            else "#ff00ff"
            if element == "Fire"
            else "#00ff00"
            if element == "Earth"
            else "#ffea00"
        )

        svg = f"""<svg viewBox="0 0 240 380" xmlns="http://www.w3.org/2000/svg" style="background:#0b132b; border-radius:16px;">
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
  <rect x="10" y="10" width="220" height="360" rx="12" fill="none" stroke="{glow_color}" stroke-width="2" filter="url(#card-glow)"/>

  <!-- Astrological/Hebrew Letter Indicators -->
  {f'<text x="25" y="35" fill="{glow_color}" font-size="12" font-family="monospace">{hebrew}</text>' if hebrew else ""}
  {f'<text x="215" y="35" fill="{glow_color}" font-size="12" font-family="monospace" text-anchor="end">{ruler}</text>' if ruler else ""}

  <!-- Central Archetypal Symbol Shape -->
  <circle cx="120" cy="180" r="45" fill="none" stroke="{glow_color}" stroke-width="1.5" stroke-dasharray="4,4"/>
  <polygon points="120,115 155,190 85,190" fill="none" stroke="{glow_color}" stroke-width="2" filter="url(#card-glow)"/>

  <!-- Title -->
  <text x="120" y="320" fill="#ffffff" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">{name}</text>
  <text x="120" y="340" fill="{glow_color}" font-size="10" font-family="sans-serif" text-anchor="middle" letter-spacing="1.5">{orientation.upper()} ({element.upper()})</text>
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

        primary_name, primary_desc = self._get_hexagram_details(primary_pattern)
        relating_name, relating_desc = self._get_hexagram_details(relating_pattern)

        return {
            "cast_lines": lines,
            "primary": {"pattern": primary_pattern, "name": primary_name, "meaning": primary_desc},
            "relating": {"pattern": relating_pattern, "name": relating_name, "meaning": relating_desc},
            "changing_lines": changing_indices,
            "has_changes": len(changing_indices) > 0,
            "svg": self._render_hexagram_svg(primary_pattern, relating_pattern, lines),
        }

    def _get_hexagram_details(self, pattern: list[int]) -> tuple[str, str]:
        # Compact mapping of binary values to standard hexagrams
        bin_str = "".join(str(b) for b in pattern)
        # Hexagram names & meanings dictionary
        HEXAGRAM_MAP = {
            "111111": ("Ch'ien / The Creative", "Pure active energy, leadership, persistent action"),
            "000000": ("K'un / The Receptive", "Pure yielding energy, nurturing, dedication, patience"),
            "100010": (
                "Chun / Difficulty at the Beginning",
                "Sprouting seed, dynamic growth against initial obstacles",
            ),
            "010001": ("Meng / Youthful Folly", "Inexperience, requirement of a teacher, open-minded study"),
            "111010": ("Hsü / Waiting", "Patience, collecting strength, letting things mature naturally"),
            "010111": ("Sung / Conflict", "Disputes, need to seek arbitration, stop half-way"),
            "010000": ("Shih / The Army", "Leadership, collective discipline, alignment towards a goal"),
            "000010": ("Pi / Holding Together", "Union, alliance, mutual support and community strength"),
            "111011": ("Hsiao Ch'u / Taming Power of Small", "Gentle restraint, small progress, accumulating wind"),
            "110111": ("Lü / Treading", "Conduct, cautious stepping, moving gracefully amidst danger"),
            "111000": ("T'ai / Peace", "Harmonious flow, heaven and earth meeting, alignment"),
            "000111": ("P'i / Standstill", "Stagnation, retreat of noble influences, blockages"),
            "101111": ("T'ung Jen / Fellowship", "Union with others in the open, shared vision"),
            "111101": ("Ta Yu / Great Possession", "Abundant light, wealth, supreme clarity and rule of virtue"),
            "000100": ("Ch'ien / Modesty", "Self-deprecation, keeping low, high values without pride"),
            "001000": ("Yü / Enthusiasm", "Vibrant motivation, movement follows music, readiness"),
            "100110": ("Sui / Following", "Adapting, yielding leadership to flow of time"),
            "011001": ("Ku / Work on the Decayed", "Renovating what was broken, fixing parental errors"),
            "110000": ("Lin / Approach", "Approaching spring, warm influence, growth opportunity"),
            "000011": ("Kuan / Contemplation", "Looking down, meditation, viewing the whole field"),
            "100101": ("Shih Ho / Biting Through", "Removing obstacles, energetic enforcement of law"),
            "101001": ("Pi / Grace", "Aesthetic beauty, decoration, temporary outer form"),
            "000001": ("Po / Splitting Apart", "Disintegration, collapse of rotten structures"),
            "100000": ("Fu / Return", "The turning point, return of light, recovery of energy"),
            "100111": ("Wu Wang / Innocence", "Natural behavior, acting without ulterior motives"),
            "111001": ("Ta Ch'u / Great Taming Power", "Focus, storing wisdom, preparation for large work"),
            "100001": ("I / Nourishment", "Providing food, monitoring what enters mouth and mind"),
            "011110": (
                "Ta Kuo / Preponderance of the Great",
                "Heavy beam bends, crisis requiring extraordinary action",
            ),
            "010010": ("K'an / The Abyssal (Water)", "Double danger, maintaining trust, flowing through deep chasms"),
            "101101": ("Li / The Clinging (Fire)", "Illumination, clarity, dependency on fuel, consciousness"),
            "001110": ("Hsien / Influence", "Mutual attraction, courtship, receptive harmony"),
            "011100": ("Heng / Duration", "Persistence, stable marriage of earth/wind forces"),
            "001111": ("Tun / Retreat", "Strategic withdrawal, saving energy in times of decline"),
            "111100": (
                "Ta Chuang / Power of the Great",
                "Steer holds horns, avoiding head-on clashes, inner discipline",
            ),
            "000101": ("Chin / Progress", "Sun rising over earth, dynamic advancement and honor"),
            "101000": ("Ming I / Darkening of the Light", "Hiding light under a basket, survival during tyranny"),
            "101011": ("Chia Jen / The Family", "Internal order, domestic discipline and alignment"),
            "110101": ("K'uei / Opposition", "Different paths, finding alignment on minor matters"),
            "001010": ("Chien / Obstruction", "Mountain before water, need to stop and regroup"),
            "010100": ("Hsieh / Deliverance", "Release of tension, forgiveness, moving forward quickly"),
            "110001": ("Sun / Decrease", "Reducing excess, concentrating on simplicity"),
            "100011": ("I / Increase", "Expanding, helping the lower classes, time for undertaking"),
            "111110": ("Kuai / Breakthrough", "Decisive resolution, clearing out remaining obstacles"),
            "011111": ("Kou / Coming to Meet", "Sudden temptation, dynamic female influence, caution"),
            "000110": ("Ts'ui / Gathering Together", "Mass convergence, alignment of leadership and sacrifices"),
            "011000": ("Sheng / Pushing Upward", "Gradual vertical progress, steady effort and growth"),
            "010110": ("K'un / Oppression", "Exhaustion, dry well, testing of resolve and speechlessness"),
            "011010": ("Ching / The Well", "Inexhaustible source of life-force, maintaining the structure"),
            "101110": ("Ko / Revolution", "Discarding old skins, seasonal change, timing is critical"),
            "011101": ("Ting / The Cauldron", "Vessel of transformation, spiritual nourishment, alchemy"),
            "100100": (
                "Chen / The Arousing (Thunder)",
                "Startling thunder, awakening, initial fear turning to laughter",
            ),
            "001001": (
                "Kên / Keeping Still (Mountain)",
                "Meditation, stopping action at the right time, spine alignment",
            ),
            "001011": ("Chien / Development", "Slow progress, wild geese flying in formation"),
            "110100": ("Kuei Mei / The Marrying Maiden", "Impulsive action before correctness, lack of authority"),
            "101100": ("Feng / Abundance", "Peak illumination, transient glory, preparing for decline"),
            "001101": ("Lü / The Wanderer", "Moving through foreign lands, cautious behavior, temporary shelter"),
            "011011": ("Sun / The Gentle (Wind)", "Penetrating influence, flexibility, persistent action"),
            "110110": ("Tui / The Joyous (Lake)", "Joy, shared discourse, friendly persuasion, openness"),
            "010011": ("Huan / Dispersion", "Dissolving blockages, crossing the great water"),
            "110010": ("Chieh / Limitation", "Frugality, boundary definition, keeping moderation"),
            "110011": ("Chung Fu / Inner Truth", "Pigs and fishes aligned, supreme sincerity, faith"),
            "001100": ("Hsiao Kuo / Preponderance of the Small", "Keeping low, avoiding flight, attention to detail"),
            "101010": ("Chi Chi / After Completion", "Boiling water on fire, perfect order fading to chaos"),
            "010101": ("Wei Chi / Before Completion", "Fire above water, potential, the young fox wetting its tail"),
        }
        return HEXAGRAM_MAP.get(bin_str, ("Unknown Hexagram", "Esoteric transformation"))

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
