# core/ritual_generator.py
"""Sacred Ritual Text Generator for Compassion Broadcasts.

Orchestrates astrology, tarot, I Ching, geomancy, dharma tales,
and LLM narrative generation into a unified ritual document.

Each ritual contains:
  1. Invocation — formal liturgical opening
  2. Situational Prayer — LLM-generated prayer for the specific situation
  3. Dharma Teaching — parable relevant to the suffering
  4. Divination Correspondences — current astrology + tarot + I Ching
  5. Hero Journey Narrative — the archetypal path through suffering
  6. Dedication — closing verses dedicating merit

Works with or without an LLM — rich fallback templates when unavailable.
"""
from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Map suffering_type → sutra theme/tags for passage selection.
# Used by _select_sutra_passage() to pull a thematically relevant
# passage from knowledge/sutra_passages.json.
_SUFFERING_TO_SUTRA_TAGS: dict[str, list[str]] = {
    "earthquake": ["protection", "disaster", "healing"],
    "war": ["protection", "peace", "patience", "purification"],
    "illness": ["healing", "purification"],
    "death": ["impermanence", "emptiness", "death", "ancestral", "liberation", "bardo", "wisdom"],
    "displacement": ["impermanence", "protection"],
    "dedication_of_endeavors": ["dedication", "loss", "wealth", "money"],
    "universal": ["dedication", "emptiness", "generosity", "wisdom", "non_duality", "healing", "purification"],
    "anger": ["patience", "forbearance", "anger", "transformation", "purification"],
    "purification": ["purification", "confession", "karma", "renewal"],
    "fear": ["protection", "healing", "emptiness", "wisdom"],
}

# Map suffering_type → dharani_id in knowledge/dharanis.json.
# Used by _select_dharani() to include a protective/purifying dharani
# recitation in the ritual invocation section.
_SUFFERING_TO_DHARANI: dict[str, str] = {
    "earthquake": "great_compassion_dharani",        # Avalokiteshvara — compassion for victims
    "war": "great_compassion_dharani",                # Compassion for all sides
    "illness": "medicine_buddha_dharani",             # Bhaiṣajyaguru — healing
    "death": "ushnisha_vijaya_dharani",               # Namgyalma — liberation of deceased
    "displacement": "amitabha_pure_land_dharani",     # Amitabha — refuge/rebirth
    "dedication_of_endeavors": "cundi_dharani",       # Cundi — wish-fulfilling/abundance
    "universal": "great_compassion_dharani",          # Universal compassion
    "anger": "vajrasattva_hundred_syllable",          # Vajrasattva — purifies anger
    "purification": "vajrasattva_hundred_syllable",   # Vajrasattva — the purification dharani
    "fear": "green_tara_dharani",                      # Green Tara — remover of fear
}


@lru_cache(maxsize=1)
def _load_sutra_db() -> dict:
    """Load knowledge/sutra_passages.json once (cached for the session).

    Returns the parsed JSON dict. Empty dict on missing/corrupt file so
    callers can fall back gracefully without a ritual-blocking exception.
    """
    path = Path(__file__).resolve().parent.parent / "knowledge" / "sutra_passages.json"
    if not path.exists():
        logger.debug("sutra_passages.json not found at %s", path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load sutra_passages.json: %s", exc)
        return {}


@lru_cache(maxsize=1)
def _load_dharanis_db() -> list[dict]:
    """Load knowledge/dharanis.json once (cached for the session).

    Returns a list of dharani entry dicts. Empty list on missing/corrupt
    file so callers can fall back gracefully.
    """
    path = Path(__file__).resolve().parent.parent / "knowledge" / "dharanis.json"
    if not path.exists():
        logger.debug("dharanis.json not found at %s", path)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load dharanis.json: %s", exc)
        return []


@dataclass
class RitualText:
    """A complete generated ritual document."""

    intention: str
    timestamp: str
    invocation: str
    situational_prayer: str
    dharma_teaching: str
    divination_correspondences: str
    hero_journey: str
    dedication: str
    carrier_frequencies: list[float] = field(default_factory=list)
    solfeggio_names: list[str] = field(default_factory=list)
    mantras_dedicated: int = 0
    targets: list[str] = field(default_factory=list)
    tradition: str = "vajrayana"

    def to_markdown(self) -> str:
        """Render as a complete markdown document."""
        lines = [
            f"# Sacred Ritual: {self.intention}",
            f"",
            f"*Generated {self.timestamp}*",
            f"*Tradition: {self.tradition.title()}*",
            f"",
            "---",
            "",
            "## I. Invocation",
            "",
            self.invocation,
            "",
            "---",
            "",
            "## II. Prayer for This Moment",
            "",
            self.situational_prayer,
            "",
            "---",
            "",
            "## III. Dharma Teaching",
            "",
            self.dharma_teaching,
            "",
            "---",
            "",
            "## IV. Divination Correspondences",
            "",
            self.divination_correspondences,
            "",
            "---",
            "",
            "## V. The Hero's Journey Through Suffering",
            "",
            self.hero_journey,
            "",
            "---",
            "",
            "## VI. Dedication of Merit",
            "",
            self.dedication,
            "",
            "---",
            "",
            "### Broadcast Details",
            "",
            f"- **Carrier Frequencies:** {', '.join(f'{f:.2f} Hz' for f in self.carrier_frequencies)}",
            f"- **Solfeggio Tones:** {', '.join(self.solfeggio_names)}",
            f"- **Mantras Dedicated:** {self.mantras_dedicated}",
            f"- **Targets:** {', '.join(self.targets)}",
            f"- **Tradition:** {self.tradition}",
            "",
            "*Om Mani Padme Hum*",
        ]
        return "\n".join(lines)


class RitualGenerator:
    """Composes complete sacred ritual texts for compassion broadcasts."""

    # Deity selections by suffering type
    DEITY_MAP = {
        "earthquake": {
            "primary": "Ksitigarbha (Earth Treasury Bodhisattva)",
            "secondary": ["Chenrezig (Avalokiteshvara)", "Amitabha Buddha"],
            "mantra": "Om Mani Padme Hum",
            "quality": "earth healing, protection of the deceased, karmic purification",
        },
        "war": {
            "primary": "Mahakala (Great Black One)",
            "secondary": ["Green Tara", "Chenrezig"],
            "mantra": "Om Tare Tuttare Ture Soha",
            "quality": "protection, removing fear, swift intervention",
        },
        "illness": {
            "primary": "Medicine Buddha (Bhaisajyaguru)",
            "secondary": ["Chenrezig", "White Tara"],
            "mantra": "Tayata Om Bekanze Bekanze Maha Bekanze Radza Samudgate Soha",
            "quality": "healing, medicine, alleviation of suffering",
        },
        "death": {
            "primary": "Amitabha Buddha (Boundless Light)",
            "secondary": ["Chenrezig", "Ksitigarbha"],
            "mantra": "Namo Amitabha Buddha",
            "quality": "rebirth in Pure Land, peaceful transition, liberation",
        },
        "displacement": {
            "primary": "Green Tara (Swift Savior)",
            "secondary": ["Chenrezig", "Amitabha"],
            "mantra": "Om Tare Tuttare Ture Soha",
            "quality": "swift protection, removing obstacles, finding refuge",
        },
        "universal": {
            "primary": "Chenrezig (Avalokiteshvara, Bodhisattva of Compassion)",
            "secondary": ["Amitabha Buddha", "Medicine Buddha", "Green Tara"],
            "mantra": "Om Mani Padme Hum",
            "quality": "universal compassion, loving-kindness, liberation of all beings",
        },
        "dedication_of_endeavors": {
            "primary": "Dzambhala (Yellow Wealth Buddha)",
            "secondary": ["Vaisravana (Wealth Protector)", "Chenrezig (Avalokiteshvara)", "Green Tara"],
            "mantra": "Om Dzambhala Dzalim Dzale Svaha",
            "quality": "transforming material resources into spiritual merit, abundance through generosity",
        },
        "anger": {
            "primary": "Vajrasattva (Diamond Being)",
            "secondary": ["Green Tara (Swift Savior)", "Chenrezig (Avalokiteshvara)"],
            "mantra": "Om Vajrasattva Hum",
            "quality": "purification of anger, forgiveness, transforming hostility into compassion",
        },
        "purification": {
            "primary": "Vajrasattva (Diamond Being)",
            "secondary": ["Chenrezig (Avalokiteshvara)", "Medicine Buddha (Bhaisajyaguru)"],
            "mantra": "Om Vajrasattva Hum",
            "quality": "purification of negative karma, confession, karmic renewal",
        },
        "fear": {
            "primary": "Green Tara (Swift Savior)",
            "secondary": ["Chenrezig (Avalokiteshvara)", "Medicine Buddha (Bhaisajyaguru)"],
            "mantra": "Om Tare Tuttare Ture Soha",
            "quality": "removing fear, swift protection, liberation from anxiety and dread",
        },
    }

    # Tarot arcana for divination section
    MAJOR_ARCANA = [
        ("The Fool", "new beginnings, leap of faith, trust in the universe"),
        ("The Star", "hope, healing, renewal after disaster"),
        ("The Tower", "sudden change, destruction of the old, revelation"),
        ("Death", "transformation, endings, transition to new form"),
        ("The World", "completion, integration, wholeness"),
        ("The Sun", "vitality, joy, clarity after darkness"),
        ("The Empress", "nurturing, abundance, the Great Mother"),
        ("Strength", "inner courage, gentle power, taming the beast"),
        ("The Hermit", "inner guidance, solitude, finding light within"),
        ("Judgement", "rebirth, awakening, calling to higher purpose"),
        ("Temperance", "balance, moderation, healing through blending"),
        ("The Magician", "power, transformation, channeling divine energy"),
    ]

    # I Ching hexagrams relevant to suffering and healing
    HEXAGRAMS = [
        (11, "Tai / Peace", "Heaven above Earth — harmony returns after turmoil"),
        (24, "Fu / Return", "The turning point — light returns after darkness"),
        (35, "Chin / Progress", "Fire above Earth — rapid progress, recognition"),
        (40, "Hsieh / Deliverance", "Thunder and Rain — release from difficulty"),
        (41, "Sun / Decrease", "Mountain above Lake — simplification, letting go"),
        (42, "I / Increase", "Wind above Thunder — growth, benefit, expansion"),
        (45, "Ts'ui / Gathering Together", "Lake above Earth — community, collective force"),
        (46, "Sheng / Pushing Upward", "Earth above Wood — steady growth, ascending"),
        (47, "K'un / Oppression", "Lake above Water — exhaustion, finding inner strength"),
        (48, "Ching / The Well", "Water above Wood — nourishment, depth, renewal"),
        (49, "Ko / Revolution", "Lake above Fire — transformation, molting"),
        (63, "Chi Chi / After Completion", "Water above Fire — completion, new beginning"),
    ]

    def __init__(self, llm=None):
        self.llm = llm
        self._rng = random.Random()

    def _select_sutra_passage(self, suffering_type: str) -> str | None:
        """Select a thematically relevant sutra passage for the suffering type.

        Loads knowledge/sutra_passages.json, maps suffering_type → theme tags,
        and returns one matching passage formatted for inclusion in a ritual.
        Returns None if no passage matches or the DB is unavailable.

        Args:
            suffering_type: One of the keys returned by detect_suffering_type().

        Returns:
            Formatted passage string (header + passage + context), or None.
        """
        db = _load_sutra_db()
        if not db:
            return None

        passages = db.get("sutra_passages", [])
        if not passages:
            return None

        target_tags = set(_SUFFERING_TO_SUTRA_TAGS.get(suffering_type, ["dedication"]))

        # Score each passage by tag overlap with the target tags.
        # Keep only passages that share at least one tag.
        scored: list[tuple[int, dict]] = []
        for p in passages:
            passage_tags = set(p.get("tags", []))
            overlap = len(passage_tags & target_tags)
            if overlap > 0:
                scored.append((overlap, p))

        if not scored:
            return None

        # Prefer higher-scoring passages; pick randomly among the top tier.
        scored.sort(key=lambda kv: -kv[0])
        top_score = scored[0][0]
        top_tier = [p for score, p in scored if score == top_score]
        chosen = self._rng.choice(top_tier)

        sutra_name = chosen.get("sutra", "the Sutras")
        chapter = chosen.get("chapter", "")
        passage = chosen.get("passage", "").strip()
        context = chosen.get("context", "").strip()

        header = f"**From {sutra_name}"
        if chapter:
            header += f" — {chapter}"
        header += ":**"

        parts = [header, "", passage]
        if context:
            parts.extend(["", f"_{context}_"])

        return "\n".join(parts)

    def _with_sutra(self, teaching: str, suffering_type: str) -> str:
        """Append a thematically matched sutra passage to a teaching.

        If no passage matches (DB missing or no tag overlap), returns the
        teaching unchanged. Used by generate_dharma_teaching() so both the
        LLM path and the fallback path receive the same sutra enrichment.
        """
        sutra = self._select_sutra_passage(suffering_type)
        if sutra:
            return f"{teaching}\n\n{sutra}"
        return teaching

    def _select_dharani(self, suffering_type: str) -> str | None:
        """Select a protective/purifying dharani for the suffering type.

        Maps suffering_type → dharani_id via _SUFFERING_TO_DHARANI, loads
        knowledge/dharanis.json, and returns the dharani text formatted for
        inclusion in the ritual invocation. Returns None if no match or DB
        is unavailable.

        Args:
            suffering_type: One of the keys returned by detect_suffering_type().

        Returns:
            Formatted dharani block (header + Sanskrit text), or None.
        """
        dharani_id = _SUFFERING_TO_DHARANI.get(suffering_type)
        if not dharani_id:
            return None

        entries = _load_dharanis_db()
        if not entries:
            return None

        entry = next((e for e in entries if e.get("id") == dharani_id), None)
        if entry is None:
            return None

        name = entry.get("name", dharani_id)
        sanskrit_name = entry.get("sanskrit", "")
        deity = entry.get("deity", "")
        text = entry.get("text_sanskrit", "").strip()

        if not text:
            return None

        header = f"**Dharani of {deity}** ({name})"
        if sanskrit_name:
            header += f"\n*{sanskrit_name}*"

        return f"{header}\n\n{text}"

    def detect_suffering_type(self, intention: str) -> str:
        """Detect the type of suffering from the intention text."""
        lower = intention.lower()
        if any(w in lower for w in ["earthquake", "seismic", "tremor"]):
            return "earthquake"
        if any(w in lower for w in ["war", "conflict", "battle", "soldier", "missile"]):
            return "war"
        if any(w in lower for w in ["illness", "cancer", "disease", "sick", "pandemic"]):
            return "illness"
        if any(w in lower for w in ["death", "deceased", "passed", "transitioned", "bardo"]):
            return "death"
        if any(w in lower for w in ["refugee", "displaced", "homeless", "evacuee"]):
            return "displacement"
        if any(w in lower for w in ["anger", "angry", "rage", "furious", "resentment", "grudge", "forgiveness", "enemy", "hostility", "hatred", "wrath", "bitter", "annoyed", "frustrated"]):
            return "anger"
        if any(w in lower for w in ["purification", "purify", "confession", "confess", "karma", "negative karma", "cleansing", "atone", "regret", "guilt", "mistake i", "wrong i"]):
            return "purification"
        if any(w in lower for w in ["fear", "afraid", "anxious", "anxiety", "panic", "worry", "worried", "terror", "dread", "scared", "frightened", "phobia"]):
            return "fear"
        if any(w in lower for w in ["dedication", "endeavor", "endeavour", "resources", "money", "loss", "investment", "wealth", "offering", "all that i", "everything i"]):
            return "dedication_of_endeavors"
        return "universal"

    def generate_invocation(self, intention: str, tradition: str = "vajrayana") -> str:
        """Generate formal liturgical invocation."""
        suffering_type = self.detect_suffering_type(intention)
        deities = self.DEITY_MAP.get(suffering_type, self.DEITY_MAP["universal"])
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        lines = [
            f"*On this day, {timestamp}, we invoke the boundless compassion of the Buddhas and Bodhisattvas.*",
            "",
            f"We call upon **{deities['primary']}**,",
            f"whose quality is {deities['quality']}.",
            "",
        ]
        if deities["secondary"]:
            lines.append("We call upon:")
            for d in deities["secondary"]:
                lines.append(f"  - **{d}**")
            lines.append("")

        lines.extend([
            f"May your wisdom-light illuminate all beings affected by: {intention}",
            "",
            f"May your compassion flow without boundary, without exception, without condition.",
            f"May your mantra — *{deities['mantra']}* — resonate through every realm.",
            "",
            "We request your presence, your blessing, your power.",
            "Accept this offering of practice.",
            "",
            "*OM AH HUM* (3x)",
        ])

        # Append the deity's dharani for extended protection/purification.
        # The dharani is a longer recitation that amplifies the invocation.
        dharani = self._select_dharani(suffering_type)
        if dharani:
            lines.extend([
                "",
                "---",
                "",
                "**Dharani Recitation**",
                "",
                dharani,
                "",
                "*Recite with single-pointed concentration. Each syllable purifies, "
                "protects, and liberates. May the resonance of this dharani reach "
                "all beings in all realms.*",
            ])

        return "\n".join(lines)

    def generate_situational_prayer(self, intention: str, targets: list[str], llm=None) -> str:
        """Generate LLM-powered prayer for the specific situation."""
        target_text = "\n".join(f"  - To {t}" for t in targets) if targets else "  - To all suffering beings"

        # Try LLM generation
        if llm:
            try:
                # Handle both LegacyLLMIntegration and LLMService
                has_backend = hasattr(llm, "client") and llm.client
                if not has_backend:
                    has_backend = hasattr(llm, "local_model") and llm.local_model
                if not has_backend:
                    has_backend = hasattr(llm, "generate")  # LLMService wraps generate
                if has_backend:
                    prompt = (
                        f"Write a compassionate Buddhist prayer (3-4 paragraphs) for the following situation:\n\n"
                        f"Situation: {intention}\n\n"
                        f"Those affected:\n{target_text}\n\n"
                        f"Write from the heart. Address them directly. Include specific wishes "
                        f"for healing, protection, peace, and liberation. Use simple, beautiful language. "
                        f"Do not use headers or titles. End with 'Om Mani Padme Hum.'"
                    )
                    result = llm.generate(prompt=prompt, system_prompt="You are a compassionate Buddhist practitioner writing prayers.", max_tokens=500, temperature=0.8)
                    if result and len(result.strip()) > 100:
                        return result.strip()
            except Exception as e:
                logger.warning(f"LLM prayer generation failed: {e}")

        # Fallback template
        return self._fallback_prayer(intention, targets)

    def _fallback_prayer(self, intention: str, targets: list[str]) -> str:
        """Rich fallback prayer when LLM is unavailable."""
        suffering_type = self.detect_suffering_type(intention)
        prayers = {
            "earthquake": f"""To all beings affected by the earthquake:

To those trapped and waiting — may rescue come swiftly. May the hands that dig through rubble be guided by compassion. May every breath you take draw you closer to safety.

To those who have lost their homes — may shelter appear. May the community around you open their doors. May you know that this displacement is temporary, but the love that surrounds you is eternal.

To those who grieve — may your tears be prayers. May each one water the seed of enlightenment. May you find in your loss a deeper connection to the impermanence that Buddha taught.

To those who have passed — may you not be afraid. The light you see is the wisdom of Amitabha. Follow it. You are not alone. You are held by boundless compassion.

To the earth herself — may you find equilibrium. May your trembling cease. May stability return to the land that has sheltered so many.

*Om Mani Padme Hum.*""",

            "universal": f"""To all beings across all realms who are suffering in this moment:

To those in pain — may your suffering be known, may it be held, may it transform.

To those who are afraid — may fear dissolve in the vast space of awareness. May you discover that the one who is afraid is also the one who is free.

To those who are alone — may you feel the presence of all the Buddhas and Bodhisattvas who have ever lived. They are with you now. They have always been with you.

To those who grieve — may your grief be a gateway. May what feels like an ending reveal itself as a beginning. May the one you lost be closer than breath.

To those who are dying — may the clear light appear. May you recognize it as your own true nature. May you not be afraid.

To those who have died — may you find swift passage. May the bardo be brief. May liberation be immediate.

*Om Mani Padme Hum.*""",

            "dedication_of_endeavors": f"""To all beings across all realms who have invested, spent, lost, and given:

To whatever resources I have gathered and spent —
whether in concentrated effort or scattered moments,
whether for the benefit of others or from my own selfish needs,
whether it returns to me or flows away forever —
may every dollar, every hour, every breath of effort
become a cause for the awakening of all beings.

To the thousands lost — may they become thousands of prayers.
To the time spent in confusion — may it become time spent in clarity.
To every mistake — may it become a teaching.
To every loss — may it become a liberation.

May the fruit of all my endeavors — past, present, and future —
ripens as happiness for mother sentient beings.
Whether it comes back for me or not, may it bring good fruition.

I offer it all — without exception, without regret, without condition.
May it bring lasting happiness for all beings throughout space and time.

*Om Dzambhala Dzalim Dzale Svaha.*""",

            "anger": f"""To all beings who burn with the fire of anger:

To the one who is furious — may you see that this anger is not your enemy. It is a wave in the ocean of your mind. It arose from conditions, and it will pass. You do not need to act on it. You do not need to suppress it. Just watch it. Let it burn itself out in the space of awareness.

To the one you are angry at — may they be free from suffering. May they be free from the conditions that caused them to harm you. They, too, are caught in the web of karma. They, too, are suffering. Your anger toward them does not hurt them — but it burns you.

To the space between you — may forgiveness flower there. Not because what happened was acceptable, but because holding onto the coal of anger only burns your own hand. Forgiveness is not weakness. It is the courage to let go.

To Vajrasattva — Diamond Being — may your purity cut through this anger like a diamond through glass. May the hundred-syllable mantra wash clean the karma of hostility. May what was rigid become fluid. May what was hot become cool. May what was weaponized become medicine.

*Om Vajrasattva Hum.*""",

            "purification": f"""To all beings who carry the weight of past actions:

To the one who has done wrong — may you know that acknowledgment is the first step of purification. You are not your past. You are not your mistakes. The dharma does not ask you to forget — it asks you to transform.

To the karma you have created — may it be seen, confessed, and released. Not hidden in shame, not justified in pride, but held honestly in the light of awareness. What is seen clearly begins to dissolve.

To Vajrasattva — Diamond Being — may your hundred-syllable mantra be the water that washes the mirror of mind. May every syllable purify a layer of obscuration. May the diamond nature beneath all karma shine through.

To the path ahead — may you walk it with the lightness of one who has been cleansed. Not with the heaviness of guilt, but with the clarity of wisdom. Not with the fear of repeating the past, but with the determination to create a different future.

May all beings — every one of whom has been both harmed and harmer across countless lives — find the purification that leads to awakening.

*Om Vajrasattva Hum.*""",

            "fear": f"""To all beings who tremble with fear:

To the one who is afraid — may you know that fear is not weakness. It is the mind trying to protect you from a future that hasn't arrived. It is a shadow on the wall, cast by the lamp of your own imagination. The shadow cannot harm you. But grasping at it — that is what wears you down.

To Green Tara — Swift Savior, she who steps down from the lotus to answer cries without delay — we call upon you. Your right foot is extended, ready to spring into action. You do not hesitate. You do not deliberate. You ACT. May your swiftness cut through the paralysis of fear.

To the fear itself — we do not fight you. We do not suppress you. We see you. You are the echo of ancient survival, the mind's alarm system ringing after the danger has passed. Thank you for trying to protect us. But you may rest now. The present moment is safe. The breath moving in and out is proof: in this moment, you are okay.

To all beings who live in chronic fear — may they discover what the Heart Sutra teaches: that the one who is afraid is itself empty. When the one who fears is seen through, what remains is vast, open, unafraid. Not because fear was defeated, but because the one who could be afraid was never truly there.

*Om Tare Tuttare Ture Soha.*""",
        }
        return prayers.get(suffering_type, prayers["universal"])

    def generate_dharma_teaching(self, intention: str, llm=None) -> str:
        """Generate a dharma teaching or parable relevant to the suffering."""
        suffering_type = self.detect_suffering_type(intention)

        # Try LLM
        if llm:
            try:
                has_backend = hasattr(llm, "client") and llm.client
                if not has_backend:
                    has_backend = hasattr(llm, "local_model") and llm.local_model
                if not has_backend:
                    has_backend = hasattr(llm, "generate")
                if has_backend:
                    prompt = (
                        f"Tell a short Buddhist parable or teaching story (2-3 paragraphs) about "
                        f"finding meaning, compassion, or liberation in the face of: {intention}. "
                        f"Make it specific, evocative, and rooted in dharma. No titles or headers."
                    )
                    result = llm.generate(prompt=prompt, system_prompt="You are a wise dharma teacher.", max_tokens=400, temperature=0.7)
                    if result and len(result.strip()) > 100:
                        return self._with_sutra(result.strip(), suffering_type)
            except Exception as e:
                logger.warning(f"LLM teaching generation failed: {e}")

        # Fallback teachings
        teachings = {
            "earthquake": """A monk asked the Master: "When the very earth shakes beneath us, where shall we find refuge?"

The Master placed his hand on the ground and said: "Here."

"But Master, the earth itself is unstable!"

"Every thing is unstable," the Master replied. "The earth, the mountains, the sky, your body, your mind — all arise and pass away. This is not a tragedy. This is the door to freedom."

"But then what can we rely on?"

"Compassion," said the Master. "Compassion is the one thing that grows stronger when everything else falls apart. When the buildings crumble, compassion builds. When the earth splits, compassion bridges. When all seems lost, compassion finds a way. This is why Chenrezig has a thousand hands — not to hold the world still, but to reach into every crack and crevice where suffering hides, and pull it into the light."

The monk bowed. And in that moment, the trembling stopped — not the earth's trembling, but the trembling in his own heart.""",

            "universal": """The Buddha said: "Monks, suppose a man were to throw a yoke with a single hole into the great ocean. And suppose a blind turtle who surfaces only once every hundred years were to rise at the very spot where the yoke floated. That probability — the turtle putting its neck through the hole — is how rare it is to obtain a precious human rebirth."

"Having obtained this rare rebirth, what should one do?" a monk asked.

"Practice compassion without exception," the Buddha replied. "For every being you encounter — every insect, every enemy, every stranger, every dying friend — has been your mother in a past life. They have fed you, held you, wept for you. Now they wander in suffering, not knowing why."

"Is compassion enough?" the monk asked.

"Compassion is the seed. Wisdom is the water. Together they grow the bodhi tree under which all beings can rest. Do not wait for perfect understanding before you begin. Begin now, with whatever you have. The universe will meet you halfway."

And the monks went forth, each one carrying compassion like a lamp into the darkness.""",

            "dedication_of_endeavors": """A great merchant named Sadaprudita once traded across seven kingdoms. He amassed vast wealth — gold, silks, jewels beyond counting. He thought his wealth would bring him happiness, and for a time it did.

One day, a great storm sank all his ships. Bandits raided his caravans. A fire consumed his warehouses. In a single week, he lost everything — thousands upon thousands of pieces of gold, a lifetime of accumulated effort.

He sat in the ashes of his warehouse and wept. "All those years," he said. "All that work. All gone."

An old monk passed by and asked: "What do you mourn?"

"My wealth! My life's work! Gone in a week!"

"Was it yours?" the monk asked gently.

"Of course it was mine! I earned it with my own hands!"

"Then where is it now? If it was truly yours, you should be able to call it back."

The merchant was silent.

"The wealth was never yours," the monk said. "It flowed through your hands for a time, that is all. What is truly yours is what you did with it while it passed through — the workers you fed, the temples you built, the beggars you turned away or welcomed. That karma, that is yours. The gold was just a visitor."

"But I lost so much," the merchant whispered.

"You lost nothing that was yours," the monk replied. "But you gained something invaluable: you now understand impermanence not as a concept, but as a lived experience. This understanding is worth more than all the gold in seven kingdoms. Now — take this understanding and dedicate the merit of everything you ever did, every coin you ever spent, to the liberation of all beings. The loss becomes the path."

The merchant bowed. And from that day forward, whatever he earned — a little or a lot — he offered it all. Not because he was forced to, but because he understood that offering is the only use of wealth that cannot be taken away by storm or bandit or fire.

This is the perfection of generosity: not giving because you have plenty, but giving because you understand that having and losing are the same dream.""",

            "anger": """A monk came to his teacher, trembling with rage. "Someone has wronged me terribly," he said. "I cannot forgive them. The anger is eating me alive."

The teacher said nothing. He went to the kitchen and returned with two pieces of coal — glowing red-hot from the fire. He placed one in his own hand, and offered the other to the monk.

"Take it," the teacher said.

The monk reached for it, then pulled back. "It's too hot! It will burn me!"

"Yes," the teacher replied. "And you have been holding a hot coal in your mind for how many days now? You think it is burning the person who wronged you. But they are sleeping peacefully. You are the one with burns."

The monk was silent.

"The coal of anger," the teacher continued, placing his own piece back in the fire, "has a purpose. It can forge. It can illuminate. But only if you set it down and use it consciously. The one who holds it suffers. The one who sets it down and builds a fire with it — that one warms everyone around them."

"What if I cannot set it down?" the monk asked.

"Then practice," the teacher said. "Every day, try to hold it a little more loosely. Notice the space between you and the anger — the awareness that watches the anger but is not the anger. Rest in that space. Gradually, the anger will release itself."

"And the person who wronged me?"

"The Buddha said: 'Hatred does not cease by hatred, but by love alone.' You do not need to love what they did. You need to love yourself enough to let go of the coal."

The monk bowed. And slowly, day by day, he opened his hand.""",

            "purification": """A student asked the Master: "I have committed many wrong actions in my past. Can they ever be purified, or am I condemned to carry them forever?"

The Master took the student to a river that flowed near the temple. The water was muddy, churned up by recent rains.

"Look at this water," the Master said. "It is clouded now. But is the water itself impure? Or is it simply mixed with mud?"

"The water itself is clear," the student replied. "It is mixed with mud."

"And if we let it sit?" the Master asked.

They waited. Gradually, the mud sank to the bottom. The water became clear again.

"Your mind is like this water," the Master said. "The wrong actions you have committed are like mud. They cloud the mind, yes. But they are not the mind itself. The clear water — your buddha-nature — is always there, beneath the mud."

"But how do I make the mud sink?" the student asked.

"Confession," the Master said. "Not guilt — guilt stirs up the mud. Confession. Acknowledgment. The honest seeing of what you have done, without denial and without self-punishment. When you see clearly, the mud settles."

"And Vajrasattva?"

"Vajrasattva is the diamond that cuts through the mud. When you recite the hundred-syllable mantra with sincere heart, you are not asking a deity to fix you. You are invoking the diamond nature of your own mind — the part of you that has never been stained, that cannot be stained, that is already pure."

"Already pure?" the student asked, confused.

"The mud settles because it was never part of the water. Your karma settles because it was never part of you. It is a pattern, not a nature. Patterns change. Natures do not. Your nature is already awake."

The student looked at the now-clear water and wept — not from guilt, but from relief.""",

            "fear": """A woman came to the monastery, trembling. "I am afraid all the time," she said. "Afraid of the future, afraid of losing what I have, afraid of death. The fear follows me everywhere."

The teacher listened, then asked: "Where is the fear right now? In this moment, sitting here, drinking tea — where is it?"

She paused. "It is... in my chest. A tightness."

"And what is the tightness afraid of? Right now, in this exact moment — what danger is present?"

She looked around the quiet room. The incense burning. The bird outside. The warmth of the cup in her hands. "There is no danger here," she admitted.

"Then the fear is not about now," the teacher said gently. "The fear is about a future that has not arrived. And when that future arrives — if it arrives — it will arrive as the present moment. And in the present moment, you will handle it, just as you have handled every present moment your entire life."

"But I feel it physically," she said. "My heart races. My hands shake."

"Yes. The body responds to the mind's projections as if they were real. This is the body's kindness — it is trying to protect you. But the body cannot tell the difference between a tiger in the room and a tiger in the imagination. Your job is not to stop the body's alarm. Your job is to see clearly: the tiger is not here."

"And when it IS here?" she asked. "When the thing I fear actually happens?"

"Then you will be present," the teacher said. "And presence is always stronger than fear. Every crisis you have ever survived — you survived because you were present in that moment. Fear is the rehearsal for a play that may never be performed. And even if it is performed, the rehearsal does not help. Only presence helps."

"Then what do I do with the fear?" she asked.

"Sit with it," the teacher said. "Do not push it away. Do not follow its stories. Just sit. Let the tightness be tight. Let the heart race. And notice: you are still here. You are still breathing. The fear has been with you your whole life, and you are still alive. It is terrible company, perhaps. But it has not killed you."

She sat. And slowly, the tightness loosened. Not because the fear was defeated — but because the one who was afraid had finally stopped running.""",
        }
        return self._with_sutra(teachings.get(suffering_type, teachings["universal"]), suffering_type)

    def generate_divination(self, intention: str, astrology_data: dict | None = None) -> str:
        """Generate divination correspondences: astrology + tarot + I Ching."""
        lines = []

        # Astrology
        if astrology_data:
            western = astrology_data.get("western", {})
            positions = western.get("positions", {})
            sun = positions.get("sun", {})
            moon = positions.get("moon", {})
            asc = positions.get("ascendant", {})

            lines.append("**Current Astrological Correspondences:**")
            lines.append("")
            if sun:
                lines.append(f"- **Sun:** {sun.get('sign', '?')} {sun.get('degree', 0):.1f} degrees — the conscious light illuminating this moment")
            if moon:
                lines.append(f"- **Moon:** {moon.get('sign', '?')} {moon.get('degree', 0):.1f} degrees — the emotional quality flowing through this practice")
            if asc:
                lines.append(f"- **Ascendant:** {asc.get('sign', '?')} — the lens through which compassion manifests")
            lines.append("")

            # Vedic
            indian = astrology_data.get("indian", {})
            panchanga = indian.get("panchanga", {})
            if panchanga:
                tithi = panchanga.get("tithi", {})
                nakshatra = panchanga.get("nakshatra", {})
                if tithi:
                    lines.append(f"- **Tithi:** {tithi.get('name', '?')} — the lunar phase supporting this practice")
                if nakshatra:
                    lines.append(f"- **Nakshatra:** {nakshatra.get('name', '?')} — the stellar mansion presiding")
                lines.append("")
        else:
            lines.append("**Astrology:** *(data unavailable — practice timed by universal compassion, not planetary alignment)*")
            lines.append("")

        # Tarot
        card = self._rng.choice(self.MAJOR_ARCANA)
        lines.append(f"**Tarot Card Drawn:** {card[0]}")
        lines.append(f"*{card[1]}*")
        lines.append(f"This card speaks to the energy present in this moment of practice.")
        lines.append("")

        # I Ching
        hexagram = self._rng.choice(self.HEXAGRAMS)
        lines.append(f"**I Ching Hexagram:** #{hexagram[0]} — {hexagram[1]}")
        lines.append(f"*{hexagram[2]}*")
        lines.append("")

        # Geomancy (simplified)
        geomancy_figures = [
            ("Via", "the path forward — a journey through changing conditions"),
            ("Populus", "the people — community gathering, collective strength"),
            ("Fortuna Major", "greater fortune — success through perseverance"),
            ("Amissio", "loss — letting go so new growth can emerge"),
            ("Acquisitio", "gain — receiving what is needed, abundance"),
            ("Conjunctio", "union — coming together, reconciliation"),
            ("Carcer", "restriction — patience within limitation"),
            ("Tristitia", "sorrow — the earth energy that grounds grief into wisdom"),
        ]
        figure = self._rng.choice(geomancy_figures)
        lines.append(f"**Geomantic Figure:** {figure[0]}")
        lines.append(f"*{figure[1]}*")
        lines.append("")

        return "\n".join(lines)

    def generate_hero_journey(self, intention: str, targets: list[str]) -> str:
        """Generate the archetypal hero's journey narrative through suffering."""
        suffering_type = self.detect_suffering_type(intention)

        journeys = {
            "earthquake": f"""**The Six Stages of the Journey Through Earthquake:**

**1. The Awakening** — The earth speaks. What was solid shifts. In an instant, the illusion of stability is revealed. This is not cruelty — it is the dharma teaching impermanence through the very ground beneath our feet.

**2. The Forge** — Those who survive become stronger than they knew. Rescuers discover courage they never suspected. Communities discover bonds they never tested. The forge of catastrophe tempers the steel of compassion.

**3. The Great Work** — Now begins the real practice: rebuilding not just structures but hearts. Every blanket distributed is a prayer. Every hand extended is a mudra. Every tear wiped is a blessing. The Great Work is not separate from ordinary kindness.

**4. The Shadow Trial** — The darkest hour comes not during the quake but after — when the adrenaline fades and the grief sets in. When the world moves on but you are still standing in the rubble of your life. This is when compassion matters most. Not the compassion of action, but the compassion of presence.

**5. The Golden Age** — The community that emerges from disaster is not the same one that existed before. Something has been forged. Bonds have been tested and proven. The golden age is not a return to the past — it is a new beginning built on the foundation of what was lost.

**6. The Infinite Return** — The story does not end. The compassion generated in this moment ripples outward through all time. Every mantra recited, every frequency broadcast, every prayer spoken — these do not dissipate. They return, again and again, in forms we cannot predict. The circle closes and opens simultaneously.""",

            "universal": f"""**The Six Stages of the Journey Through Universal Suffering:**

**1. The Awakening** — Suffering is not a mistake. It is the friction that awakens consciousness. Without it, we would sleep forever in the dream of separation. The first noble truth is not pessimism — it is diagnosis.

**2. The Forge** — Every being who suffers is being forged. The fire of pain burns away what is inessential. What remains is the pure gold of awareness — the recognition that you are not your suffering, you are the space in which suffering arises and dissolves.

**3. The Great Work** — The bodhisattva does not wait for personal liberation before helping others. The Great Work is helping others *as* the path to liberation. Every act of kindness is a step toward enlightenment. Every moment of compassion is a glimpse of buddhanature.

**4. The Shadow Trial** — There comes a moment when compassion itself feels like a burden. When the suffering of others is so vast that your heart cannot hold it. This is the test. Not the test of strength, but the test of surrender. Can you let your heart break open and still continue?

**5. The Golden Age** — The golden age is not a future utopia. It is the present moment seen clearly. When compassion flows without exception, every moment becomes golden. Every encounter becomes a meeting of buddhas.

**6. The Infinite Return** — The bodhisattva vow has no end because it has no beginning. "However innumerable beings are, I vow to save them all." This is not hyperbole. It is the recognition that compassion is the nature of mind itself. It will continue as long as there is suffering — which is to say, it will continue forever. And that is not a tragedy. It is the beauty of the path.""",

            "dedication_of_endeavors": f"""**The Six Stages of the Journey Through Loss and Offering:**

**1. The Loss** — Something you gathered slips through your fingers. Money, time, effort, hope — concentrated or scattered, it doesn't matter. The form it took is gone. This is not failure. This is the first lesson in the dana-paramita, the perfection of generosity: that which can be lost was never truly held.

**2. The Recognition** — You see clearly: everything invested — whether for others or for yourself, whether wisely or foolishly — was a transaction with impermanence. The loss is not punishment. It is simply the completion of a cycle. The question is not "why did I lose?" but "what do I do with the understanding that loss reveals?"

**3. The Offering** — You take everything — the gains and the losses, the wisdom and the mistakes, the selfish hours and the generous ones — and you offer it all. Not to a deity outside yourself, but to the awakened nature within everything. "May all my endeavors — without exception — ripen as happiness for beings." This is the moment wealth transforms into merit.

**4. The Transformation** — The offering changes both the giver and the gift. The $7,000 lost becomes 7,000 prayers. The time spent in confusion becomes time that taught clarity. The whittling-down of debt becomes the whittling-down of ego. What was loss is now practice. What was pain is now the path.

**5. The Abundance** — Not the abundance of bank accounts or portfolios, but the abundance of a heart that has nothing left to protect because it has already offered everything. This is true wealth — the wealth of Dzambhala, the Yellow Wealth Buddha, whose abundance is not measured in dollars but in the capacity to give without grasping.

**6. The Return** — "Whether it comes back to me or not." This is the key phrase. The bodhisattva does not practice generosity to get something back. But the paradox is: when you truly stop grasping, abundance flows naturally — not because you demand it, but because the mind that doesn't cling is itself the greatest treasure. The return is not the money. The return is the awakened heart.""",

            "anger": f"""**The Six Stages of the Journey Through Anger:**

**1. The Fire** — Anger arises like a flame. It feels powerful, righteous, justified. The mind says: "This is correct. I SHOULD be angry." And maybe it is correct — maybe the anger is pointing to a real injustice. But the question is not whether anger is justified. The question is whether you want to carry the hot coal any longer.

**2. The Pause** — Between the spark of anger and the act of retaliation, there is a gap. In that gap, everything is possible. The bodhisattva trains to find that gap — the breath, the moment of awareness, the space between stimulus and response. In that space, anger is seen rather than acted upon. And what is seen can be transformed.

**3. The Great Work** — The practice of kṣānti, the perfection of patience. Not suppressing anger, but digesting it. Sitting with it until it reveals its teaching. Anger is often protecting something deeper — fear, grief, vulnerability. When you sit long enough, the anger shows you what it is guarding. And then you can address the root, not the symptom.

**4. The Shadow Trial** — There comes a moment when the old pattern pulls strongly. The temptation to retaliate, to speak the sharp word, to send the cutting message. This is the trial. Not a test of willpower, but a test of remembrance — can you remember the gap? Can you remember the coal? Can you choose, in that moment, the path of patience over the path of reactivity?

**5. The Release** — Forgiveness arrives not as a decision but as a natural unfolding. One day you notice the anger is lighter. Another day it is gone. You did not defeat it. You simply stopped feeding it, and it starved. The person who wronged you is still who they are — but you are no longer defined by what they did.

**6. The Transformation** — The anger that burned you becomes the fuel for compassion. You understand suffering so deeply — your own and others' — that anger toward anyone feels like anger toward yourself. This is not weakness. This is the strength of one who has walked through fire and emerged luminous. The bodhisattva knows: every anger transformed is a being liberated.""",

            "purification": f"""**The Six Stages of the Journey Through Purification:**

**1. The Mirror** — You see yourself clearly. Not the self you present to others, but the self that has acted from ignorance, greed, and anger. The mirror is painful. But the mirror is also the first kindness — because without seeing, there is no transforming.

**2. The Confession** — You acknowledge. Not to a priest or a judge, but to yourself and to the field of awareness. "This is what I have done. These are the causes and conditions that led to it." No excuses, no self-flagellation — just honest seeing. This seeing IS the beginning of purification.

**3. The Great Work** — Vajrasattva practice. The hundred-syllable mantra. Each recitation washes a layer of obscuration from the mirror of mind. It is not magic — it is the systematic application of awareness to what was previously unconscious. What was hidden in darkness is brought to light, and in the light, it dissolves.

**4. The Shadow Trial** — Guilt whispers: "You can never be clean. What you have done defines you." This is the Mara of self-hatred, the most subtle obstacle on the path. The response is not to argue with guilt, but to see through it: Guilt is just another pattern, another cloud passing through the sky of mind. It is not the sky itself.

**5. The Clear Water** — The mud has settled. The water is clear. You realize it was always clear — the mud was just a visitor. This is the discovery of buddha-nature: the diamond beneath the dirt, the sky behind the clouds. You have not become someone new. You have simply reconnected with what you always were.

**6. The Vow** — "Having been purified, I now purify all beings." The merit of purification is dedicated outward. Every mantra recited, every confession made, every moment of clear seeing — these become the medicine for all beings who also carry the weight of karma. The purified one becomes a source of purity for others. The clear water flows outward and nourishes the world.""",

            "fear": f"""**The Six Stages of the Journey Through Fear:**

**1. The Alarm** — Fear arises as a wake-up call. The body sounds the alarm — heart racing, breath shallow, muscles tense. The mind, interpreting these signals, tells a story about what is coming, what might happen, what could be lost. The story is always about the future. The story is always terrifying. And the story is almost never accurate.

**2. The Turning** — There comes a moment when the one who is afraid stops running. Not a moment of bravery — bravery is for those who feel no fear. This is a moment of exhaustion, where running has become too heavy. The turning is when you look at the fear directly and say, with all your trembling: "I see you. What are you here to teach me?"

**3. The Great Work** — Tara practice begins. Om Tare Tuttare Ture Soha. Each syllable calls into presence the swift, fearless compassion of the vajra. The mantra does not promise that the fear will leave. The mantra promises that you will not face it alone. Tara's right foot is extended — ready to step down from the lotus to help. You invoke her not to remove the fear but to walk through it with you.

**4. The Shadow Trial** — The fear returns in subtler forms. It is no longer the obvious fear of the tiger in the room. It is the fear of rejection, the fear of failure, the fear of being seen. The fear of your own vastness. This is the deepest fear: that if you truly rest in awareness, the small self that has been defending itself will dissolve. And this is the death that Tara accompanies you through.

**5. The Release** — And then, one day, the fear simply does not grip you the same way. You do not know exactly when it happened. It was not a dramatic moment — it was a gradual softening. You notice it because a situation that would have terrified you six months ago now only registers as a minor inconvenience. The fear has become a messenger rather than a tyrant. It points; it does not paralyze.

**6. The Transformation** — The fear that once contracted you now opens you. You understand — with your whole body, not just your mind — that every being you have ever feared is also afraid. The stranger in the night, the critic, the dying: all are trembling with their own alarms. And so you extend compassion. Not fearlessness as the absence of fear, but fearlessness as the capacity to hold fear and act anyway. To hold the fear of the whole world in your heart and keep going. This is bodhicitta — the heart that cannot abandon any being, not because it is fearless, but because it is dedicated to the welfare of all.""",
        }
        return journeys.get(suffering_type, journeys["universal"])

    def generate_dedication(self, targets: list[str], mantras: int, frequencies: list[float], solfeggio_names: list[str]) -> str:
        """Generate dedication of merit verses."""
        lines = [
            "*Dedication of Merit*",
            "",
            "Whatever merit has been generated through this practice —",
            "through the mantras recited, the frequencies broadcast,",
            "the prayers spoken, the compassion aroused —",
            "",
            "May it flow without obstacle to:",
            "",
        ]
        for t in targets:
            lines.append(f"  * {t}")
        lines.extend([
            "",
            "May no being be excluded.",
            "May no boundary limit this dedication.",
            "May no condition diminish its power.",
            "",
            f"**{mantras} mantras** of Om Mani Padme Hum have been offered.",
            f"**{len(frequencies)} Solfeggio carrier frequencies** have resonated:",
        ])
        for freq, name in zip(frequencies, solfeggio_names):
            lines.append(f"  * {freq:.2f} Hz — {name}")
        lines.extend([
            "",
            "By this merit, may all beings attain complete enlightenment.",
            "May the earth find peace.",
            "May the waters be calm.",
            "May the air be pure.",
            "May all beings be happy.",
            "May all beings be free.",
            "",
            "*Gate gate paragate parasamgate bodhi svaha.*",
            "*Om Mani Padme Hum.*",
        ])
        return "\n".join(lines)

    def generate_full_ritual(
        self,
        intention: str,
        targets: list[str] | None = None,
        carrier_frequencies: list[float] | None = None,
        solfeggio_names: list[str] | None = None,
        mantras_dedicated: int = 108,
        astrology_data: dict | None = None,
        tradition: str = "vajrayana",
        llm=None,
    ) -> RitualText:
        """Compose a complete sacred ritual document."""
        targets = targets or ["all suffering beings"]
        carrier_frequencies = carrier_frequencies or [7.83, 528.0]
        solfeggio_names = solfeggio_names or ["Schumann Base", "Mi (Transformation)"]
        effective_llm = llm or self.llm
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        logger.info(f"Generating full ritual for: {intention}")

        invocation = self.generate_invocation(intention, tradition)
        prayer = self.generate_situational_prayer(intention, targets, effective_llm)
        teaching = self.generate_dharma_teaching(intention, effective_llm)
        divination = self.generate_divination(intention, astrology_data)
        hero_journey = self.generate_hero_journey(intention, targets)
        dedication = self.generate_dedication(targets, mantras_dedicated, carrier_frequencies, solfeggio_names)

        return RitualText(
            intention=intention,
            timestamp=timestamp,
            invocation=invocation,
            situational_prayer=prayer,
            dharma_teaching=teaching,
            divination_correspondences=divination,
            hero_journey=hero_journey,
            dedication=dedication,
            carrier_frequencies=carrier_frequencies,
            solfeggio_names=solfeggio_names,
            mantras_dedicated=mantras_dedicated,
            targets=targets,
            tradition=tradition,
        )

    def recite_ritual(self, ritual: RitualText, tts_provider=None) -> dict:
        """Queue TTS recitation of the ritual, section by section.

        Splits the ritual into 6 sections by markdown headers and recites
        each one sequentially. Designed to run simultaneously with the
        crystal bowl broadcast — the voice becomes part of the resonance
        field.

        Returns immediately if TTS is unavailable. Does not block the caller.
        If called from an async context, should be run in a background task.

        Args:
            ritual: The RitualText to recite.
            tts_provider: Optional TTS provider. If None, tries to get the
                         global provider from core.tts_provider.

        Returns:
            dict with sections_recited, status, and any errors.
        """
        import asyncio

        result = {
            "sections_recited": 0,
            "status": "skipped",
            "errors": [],
        }

        # Get TTS provider
        provider = tts_provider
        if provider is None:
            try:
                from core.tts_provider import get_tts_provider
                provider = get_tts_provider()
            except Exception:
                pass

        if provider is None:
            result["status"] = "no_tts_provider"
            result["errors"].append("TTS provider unavailable — broadcast continues silently")
            return result

        # Split ritual into sections by markdown headers
        sections = [
            ("Invocation", ritual.invocation),
            ("Prayer", ritual.situational_prayer),
            ("Teaching", ritual.dharma_teaching),
            ("Divination", ritual.divination_correspondences),
            ("Hero Journey", ritual.hero_journey),
            ("Dedication", ritual.dedication),
        ]

        async def _recite():
            # Lazy import — avoids circular dependency and loads only when TTS runs
            try:
                from core.sanskrit_tts import preprocess_for_tts
            except ImportError:
                preprocess_for_tts = None  # type: ignore[assignment]

            for section_name, text in sections:
                try:
                    # Strip markdown formatting for cleaner speech
                    clean = text.replace("**", "").replace("*", "").replace("#", "")
                    clean = clean.replace("---", "").strip()

                    if not clean:
                        continue

                    # Convert IAST Sanskrit → English phonetics so TTS can
                    # pronounce mantras and seed syllables correctly.
                    # (e.g., "Oṃ Maṇi Padme Hūṃ" → "Ohm Muh-nee Pud-may Hoom")
                    if preprocess_for_tts is not None:
                        clean = preprocess_for_tts(clean)

                    await provider.speak_async(
                        clean,
                        role="ritual_recitation",
                    )
                    result["sections_recited"] += 1

                    # Brief pause between sections
                    await asyncio.sleep(2)

                except Exception as e:
                    result["errors"].append(f"{section_name}: {e}")
                    logger.warning(f"TTS recitation failed for {section_name}: {e}")

            result["status"] = "completed" if result["sections_recited"] > 0 else "failed"

        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context — schedule the task
            asyncio.ensure_future(_recite())
            result["status"] = "queued"
        except RuntimeError:
            # No running loop — run synchronously
            try:
                asyncio.run(_recite())
            except Exception as e:
                result["status"] = "failed"
                result["errors"].append(str(e))

        return result


__all__ = ["RitualGenerator", "RitualText"]
