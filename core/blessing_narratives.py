#!/usr/bin/env python3
"""
Blessing Narratives - Story Generation for Liberation and Transformation

Generates blissful stories about:
- Alternate possibilities and pure land arrivals
- Liberation from suffering realms (hell, hungry ghost, etc.)
- Empowerment of the powerless
- Healing and transformation for both victims and perpetrators
- Sacred narratives of compassion in action

This module provides both template-based and LLM-generated narratives
to help visualize and energize compassionate intentions.
"""

import random
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json

try:
    from core.compassionate_blessings import BlessingTarget, BlessingCategory
    HAS_BLESSINGS = True
except ImportError:
    HAS_BLESSINGS = False

try:
    from core.llm_integration import LLMClient, ConversationManager
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class NarrativeType(Enum):
    """Types of liberation narratives"""
    PURE_LAND_ARRIVAL = "pure_land_arrival"
    HELL_LIBERATION = "hell_liberation"
    HUNGRY_GHOST_NOURISHMENT = "hungry_ghost_nourishment"
    EMPOWERMENT = "empowerment"
    RECONCILIATION = "reconciliation"
    HEALING_JOURNEY = "healing_journey"
    ALTERNATE_TIMELINE = "alternate_timeline"
    DIVINE_INTERVENTION = "divine_intervention"
    SELF_REALIZATION = "self_realization"
    COLLECTIVE_AWAKENING = "collective_awakening"


class PureLandTradition(Enum):
    """Different pure land traditions"""
    SUKHAVATI = "sukhavati"  # Amitabha's Western Pure Land
    ABHIRATI = "abhirati"  # Akshobhya's Eastern Pure Land
    SHAMBHALA = "shambhala"  # Hidden kingdom of enlightenment
    TUSHITA = "tushita"  # Maitreya's pure land
    POTALA = "potala"  # Avalokiteshvara's pure land
    VIMALAKIRTI = "vimalakirti"  # Pure land of the householder
    UNIVERSAL_LIGHT = "universal_light"  # Non-denominational sacred space
    NATURE_PARADISE = "nature_paradise"  # Eden-like natural sanctuary
    ANCESTRAL_PEACE = "ancestral_peace"  # Reconnection with ancestors
    QUANTUM_HEALING = "quantum_healing"  # Science-integrated sacred space


@dataclass
class NarrativeTemplate:
    """Template for generating stories"""
    narrative_type: NarrativeType
    title: str
    opening: List[str]  # Multiple variations
    journey: List[str]  # Multiple plot points
    transformation: List[str]  # The moment of change
    resolution: List[str]  # The outcome
    dedication: List[str]  # Closing prayer/dedication
    tags: List[str]


@dataclass
class GeneratedStory:
    """A complete generated narrative"""
    target_name: str
    narrative_type: NarrativeType
    title: str
    story_text: str
    pure_land: Optional[PureLandTradition]
    generation_method: str  # 'template' or 'llm'
    timestamp: datetime
    dedication: str
    metadata: Dict


class PureLandDescriptions:
    """Vivid descriptions of various pure lands"""

    DESCRIPTIONS = {
        PureLandTradition.SUKHAVATI: {
            "name": "Sukhavati - The Land of Bliss",
            "description": """
As consciousness shifts, you find yourself in Sukhavati, the Western Pure Land of
Infinite Light. The ground beneath your feet is not earth but lapis lazuli, radiating
gentle blue light. Jeweled trees line pathways of gold, their branches heavy with
blossoms that sing dharma teachings in the breeze.

Seven-tiered pools reflect the sky, their waters possessing eight perfect qualities.
Lotus flowers of every color bloom spontaneously - those who arrive are born from
these lotuses, free from the womb-door, free from pain.

Amitabha Buddha sits in the center, radiating infinite light that dissolves all
suffering on contact. Celestial birds - cranes, peacocks, parrots - sing teachings
day and night. There is no darkness here, only the glow of liberation.

Every being in Sukhavati is golden-skinned, radiant, and destined for enlightenment.
Food appears by thought alone. Music plays from the trees. The very air teaches
the dharma.
            """,
            "activities": [
                "Listening to Amitabha Buddha's teachings",
                "Bathing in the eight-quality waters that wash away karma",
                "Meditation under wish-fulfilling trees",
                "Conversing with bodhisattvas and arhats",
                "Studying scriptures that appear spontaneously",
                "Visiting other pure lands via rainbow bridges"
            ],
            "sensory": {
                "sight": "Infinite light, jeweled trees, lotus pools, golden beings",
                "sound": "Dharma songs, celestial music, teaching birds",
                "smell": "Divine lotus, celestial incense, wish-fulfilling blossoms",
                "touch": "Soft lotus petals, warm healing waters, gentle breeze",
                "taste": "Ambrosial nectar, food of meditation",
                "mind": "Peace, clarity, joy, gradual enlightenment"
            }
        },

        PureLandTradition.SHAMBHALA: {
            "name": "Shambhala - The Hidden Kingdom",
            "description": """
You pass through a mystical barrier and find yourself in Shambhala, the hidden
kingdom of enlightened society. Ringed by snow-peaked mountains, this sacred land
exists in a slightly different dimension, accessible only to those whose karma ripens.

Crystal palaces rise from verdant valleys. The capital city, Kalapa, spirals in
concentric rings around a central palace where the Kalki king resides. Technology
and spirituality merge perfectly here - flying vehicles powered by meditation,
buildings constructed from solidified light.

Every citizen is a warrior-bodhisattva, trained in both martial and contemplative
arts. There is no poverty, no injustice, no oppression. The society operates on
principles of sacred kingship and enlightened governance.

Gardens produce food year-round. Libraries contain all wisdom. Meditation halls
vibrate with the power of thousands of practitioners achieving realization together.
            """,
            "activities": [
                "Training in the warrior path of compassion",
                "Studying in the great library of Kalapa",
                "Meditating with the Kalki lineage",
                "Cultivating enlightened society practices",
                "Preparing for the age when Shambhala will emerge",
                "Mastering the Kalachakra teachings"
            ],
            "sensory": {
                "sight": "Crystal palaces, snow peaks, rainbow banners, warriors in meditation",
                "sound": "Temple bells, mantras, dharma debates, ceremonial music",
                "smell": "Mountain air, juniper smoke, altar offerings",
                "touch": "Cool mountain breeze, warm community, strong friendships",
                "taste": "Pure water, vegetarian feasts, sacred medicines",
                "mind": "Warrior courage, bodhicitta, clear vision of enlightened society"
            }
        },

        PureLandTradition.UNIVERSAL_LIGHT: {
            "name": "The Realm of Universal Light",
            "description": """
You transition into a space beyond description, a realm of pure light and
unconditional love. This is not bound by any single tradition but reflects
the highest visions of all spiritual paths.

Here, consciousness itself is the landscape. Thoughts become visible as
colored light. Emotions resolve into their pure essences. All separation
dissolves in recognition of fundamental unity.

Beings here appear as they truly are - radiant expressions of consciousness,
free from the limitations of form. Communication is instant and complete,
mind to mind, heart to heart.

Healing happens spontaneously. Trauma dissolves in the light of awareness.
Ancient wounds close. Karmic knots untie themselves. The very atmosphere
is composed of compassion and wisdom.
            """,
            "activities": [
                "Direct knowing of ultimate truth",
                "Healing in pools of liquid light",
                "Communion with enlightened beings of all traditions",
                "Creating reality through pure intention",
                "Exploring infinite dimensions of consciousness",
                "Resting in the natural state"
            ],
            "sensory": {
                "sight": "Living light, geometric mandalas, rainbow bodies",
                "sound": "The music of the spheres, primordial AUM",
                "smell": "Beyond physical scent - the fragrance of truth",
                "touch": "Waves of bliss, currents of love",
                "taste": "Nectar of immortality, amrita",
                "mind": "Non-dual awareness, infinite peace, boundless love"
            }
        },

        PureLandTradition.NATURE_PARADISE: {
            "name": "The Garden of Original Innocence",
            "description": """
You awaken in a pristine wilderness, an Eden before the fall, nature in
perfect harmony. Ancient forests stretch in all directions, rivers run
crystal clear, and animals move without fear.

This is the Earth as it could be - fully healed, radiating vitality.
Every plant glows with health. The air tingles with prana. Sacred groves
pulse with gentle power.

Animals and humans communicate freely, recognizing each other as kin.
The lion lies with the lamb. The forest provides abundantly. Natural
springs offer healing waters.

Day transitions to night in a symphony of bird songs and firefly dances.
The stars shine with impossible clarity. The moon reflects in a thousand
lakes. This is home, remembered and restored.
            """,
            "activities": [
                "Communion with animals and plants",
                "Drinking from sacred springs",
                "Sleeping under ancient trees",
                "Gathering wild foods that nourish completely",
                "Swimming in pristine waters",
                "Learning from nature's wisdom"
            ],
            "sensory": {
                "sight": "Pristine wilderness, animals without fear, vibrant ecosystems",
                "sound": "Bird songs, flowing water, wind through trees",
                "smell": "Pine, wildflowers, rain on earth, sacred herbs",
                "touch": "Soft moss, cool streams, warm sun, gentle animals",
                "taste": "Wild berries, spring water, herbs that heal",
                "mind": "Primal peace, connection to all life, innocent joy"
            }
        }
    }

    @classmethod
    def get_description(cls, tradition: PureLandTradition) -> Dict:
        """Get full description of a pure land"""
        return cls.DESCRIPTIONS.get(tradition, cls.DESCRIPTIONS[PureLandTradition.UNIVERSAL_LIGHT])


class NarrativeTemplateLibrary:
    """Library of narrative templates for different story types"""

    @staticmethod
    def get_pure_land_arrival_template() -> NarrativeTemplate:
        """Template for arriving in a pure land"""
        return NarrativeTemplate(
            narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
            title="Arrival in the Land of Bliss",
            opening=[
                "As the final breath left the body, consciousness did not cease but transformed...",
                "In the moment between heartbeats, a doorway appeared - radiant, welcoming...",
                "The suffering that had seemed endless suddenly lifted, and ahead lay a path of light...",
                "Confusion and pain dissolved like morning mist, revealing a landscape of impossible beauty..."
            ],
            journey=[
                "Guides appeared - beings of light and compassion who had been waiting.",
                "Each step forward brought greater clarity, greater peace, greater recognition.",
                "The journey itself became healing, past traumas falling away like old clothes.",
                "Familiar presences emerged - loved ones, ancestors, enlightened beings..."
            ],
            transformation=[
                "And then, the full reality dawned: this was real, this was permanent, suffering had truly ended.",
                "In a flash of recognition, the true nature of mind became clear - luminous, empty, blissful.",
                "The accumulated pain of lifetimes dissolved in an instant of unconditional love.",
                "What seemed lost was found; what seemed broken was whole; what seemed ended was beginning."
            ],
            resolution=[
                "Now established in the pure land, awakening unfolds naturally, joyfully, inevitably.",
                "Every day brings deeper realization, sweeter peace, more complete healing.",
                "From this place of safety and love, the intention arises: may all beings join this liberation.",
                "The journey continues, but now it is a dance rather than a struggle, play rather than survival."
            ],
            dedication=[
                "May all beings who suffer find this same refuge.",
                "May the path be clear for all who seek liberation.",
                "May this vision inspire compassion in all who hear it.",
                "Gate gate pāragate pārasaṃgate bodhi svāhā"
            ],
            tags=["liberation", "pure_land", "rebirth", "healing", "refuge"]
        )

    @staticmethod
    def get_hell_liberation_template() -> NarrativeTemplate:
        """Template for liberation from hell realms"""
        return NarrativeTemplate(
            narrative_type=NarrativeType.HELL_LIBERATION,
            title="Liberation from the Hell Realms",
            opening=[
                "In the deepest darkness, where suffering seemed infinite and hope a distant memory...",
                "The fires of rage, the ice of hatred, the tortures of guilt - all seemed endless...",
                "Consciousness trapped in its own creations, burning in the hell of its making...",
                "Time stretched impossibly, each moment an eternity of agony..."
            ],
            journey=[
                "But even in the deepest hell, the light of compassion reaches.",
                "A tiny crack appears in the wall of suffering - perhaps a memory of kindness, a moment of regret.",
                "Through this opening, grace pours in: Medicine Buddha's healing light, Chenrezig's compassion.",
                "The hell itself begins to transform, the fires becoming purifying rather than punishing."
            ],
            transformation=[
                "In an instant of letting go, of genuine remorse and self-forgiveness, the realm shatters.",
                "What seemed solid becomes transparent; what seemed eternal reveals itself as momentary.",
                "The same mind that created this hell discovers it can create liberation.",
                "Bodhisattvas waiting at the gates welcome the newly freed being with immeasurable joy."
            ],
            resolution=[
                "The hell realm left behind, healing begins in earnest.",
                "Past actions are understood with compassion, their lessons integrated without self-torture.",
                "The being who suffered infinite pain now knows infinite compassion for all who suffer.",
                "From the lowest realm, the highest insights arise - this is the alchemy of liberation."
            ],
            dedication=[
                "For all beings trapped in states of extreme suffering, may liberation come swiftly.",
                "May the hells be emptied, may compassion reach even the darkest places.",
                "May all who have harmed find forgiveness and transformation.",
                "Om ah hum vajra guru pema siddhi hum"
            ],
            tags=["liberation", "hell_realms", "purification", "transformation", "redemption"]
        )

    @staticmethod
    def get_empowerment_template() -> NarrativeTemplate:
        """Template for the powerless gaining power"""
        return NarrativeTemplate(
            narrative_type=NarrativeType.EMPOWERMENT,
            title="The Awakening of Power",
            opening=[
                "For so long, powerlessness had been the only reality known...",
                "Voiceless, invisible, pushed to the margins - this was the world as it appeared.",
                "Every attempt to rise had been crushed, every hope disappointed.",
                "The systems of oppression seemed eternal, unchangeable, absolute..."
            ],
            journey=[
                "But something shifted - a spark of recognition: 'This is not who I truly am.'",
                "One voice joined another, then another - the isolated becoming community.",
                "Ancestral strength awakened, dormant powers stirring to life.",
                "Teachers appeared, allies emerged, resources manifested in unexpected ways."
            ],
            transformation=[
                "The moment of standing up, speaking out, refusing to accept the unacceptable.",
                "Power revealed itself not as domination but as authentic presence, clear voice, bold action.",
                "The oppressed became the empowered; the silenced found their roar.",
                "And in this empowerment, no desire for revenge - only fierce compassion and wise justice."
            ],
            resolution=[
                "Now wielding power with wisdom, helping others rise as they have risen.",
                "Creating systems of justice to replace systems of oppression.",
                "Using strength to protect the vulnerable, voice to speak for the silenced.",
                "The cycle broken: the formerly powerless now empower others, endlessly."
            ],
            dedication=[
                "May all who are oppressed find liberation and empowerment.",
                "May the powerless gain power, and may they use it wisely and compassionately.",
                "May systems of injustice transform into systems of equity and love.",
                "May all beings be free, and may all beings be fierce in their compassion."
            ],
            tags=["empowerment", "justice", "transformation", "activism", "liberation"]
        )

    @staticmethod
    def get_reconciliation_template() -> NarrativeTemplate:
        """Template for healing between abuser and abused"""
        return NarrativeTemplate(
            narrative_type=NarrativeType.RECONCILIATION,
            title="The Healing of Both Sides",
            opening=[
                "Two beings, bound by karma - one who harmed and one who was harmed.",
                "The wound between them seemed absolute, the separation unbridgeable.",
                "One carrying guilt and shame, the other trauma and rage.",
                "Both trapped in the past, unable to move forward..."
            ],
            journey=[
                "But in a space beyond ordinary time, healing becomes possible.",
                "The one who harmed finally sees the full impact of their actions - not to punish but to awaken.",
                "The one who was harmed sees the suffering that led to the harming - not to excuse but to understand.",
                "Both recognize: we are not our worst moments, nor our deepest wounds."
            ],
            transformation=[
                "Genuine remorse meets genuine boundaries - accountability without revenge.",
                "Forgiveness arises not as weakness but as sovereign choice, as liberation.",
                "The karmic knot untangles; the binding releases both beings.",
                "What was poison becomes medicine; what was wound becomes wisdom."
            ],
            resolution=[
                "Both now free, both now whole, both now committed to ending such cycles.",
                "The one who harmed becomes a healer; the one harmed becomes a teacher of resilience.",
                "Their reconciliation ripples outward, healing others in similar situations.",
                "The impossible becomes possible: complete healing for both sides."
            ],
            dedication=[
                "May all who have been harmed find healing, empowerment, and peace.",
                "May all who have harmed find genuine remorse, transformation, and right action.",
                "May the cycles of violence end in both victims and perpetrators.",
                "May wisdom and compassion heal what seemed eternally broken."
            ],
            tags=["reconciliation", "healing", "forgiveness", "transformation", "justice"]
        )

    @staticmethod
    def get_hungry_ghost_nourishment_template() -> NarrativeTemplate:
        """Template for hungry ghosts receiving nourishment"""
        return NarrativeTemplate(
            narrative_type=NarrativeType.HUNGRY_GHOST_NOURISHMENT,
            title="The Satisfaction of Infinite Hunger",
            opening=[
                "The hunger was everything - vast, aching, impossible to satisfy.",
                "A throat like a needle, a belly like a mountain, desire that burned like fire.",
                "Every attempt to consume ended in frustration, ashes in the mouth, emptiness.",
                "Wandering endlessly, seeking what could never be found through grasping..."
            ],
            journey=[
                "Then, unexpectedly: someone remembering, someone offering, someone dedicating merit.",
                "The burning began to cool; the ache began to ease.",
                "Not through consuming but through receiving - the food of compassion, the water of loving-kindness.",
                "With each offering, the capacity to receive grew; the throat opened, the belly softened."
            ],
            transformation=[
                "And finally understanding: the hunger was not for food but for love, for belonging, for worth.",
                "The moment of genuine satisfaction - not from taking but from being given to.",
                "The hungry ghost nature dissolving, replaced by simple, grateful presence.",
                "Nourished at last, truly fed, the desperate grasping finally releasing."
            ],
            resolution=[
                "No longer hungry, now able to give rather than only grasp.",
                "The offerings received create a fountain of generosity flowing outward.",
                "From the realm of insatiable hunger to the realm of abundant sharing.",
                "What was most cursed becomes most blessed - the satisfied one now feeds others."
            ],
            dedication=[
                "For all beings trapped in cycles of craving and dissatisfaction.",
                "May all hungry ghosts be fed, may all thirsts be quenched.",
                "May the offerings of the living reach the realms of the dead.",
                "Om ah hum, may all beings be nourished."
            ],
            tags=["hungry_ghost", "nourishment", "generosity", "satisfaction", "liberation"]
        )


class StoryGenerator:
    """Generates liberation narratives from templates or LLM"""

    def __init__(self, use_llm: bool = False, llm_provider: str = "ollama"):
        """
        Initialize story generator.

        Args:
            use_llm: Whether to use LLM for generation (vs templates)
            llm_provider: Which LLM provider to use
        """
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self.llm_client = None

        if use_llm and HAS_LLM:
            try:
                self.llm_client = LLMClient(provider=llm_provider)
            except Exception as e:
                print(f"Warning: Could not initialize LLM client: {e}")
                self.use_llm = False

    def generate_story(self,
                      target: Optional['BlessingTarget'] = None,
                      target_name: str = "Unknown Being",
                      narrative_type: NarrativeType = NarrativeType.PURE_LAND_ARRIVAL,
                      pure_land: PureLandTradition = PureLandTradition.UNIVERSAL_LIGHT,
                      custom_context: str = "") -> GeneratedStory:
        """
        Generate a liberation narrative.

        Args:
            target: BlessingTarget object (if available)
            target_name: Name of being receiving blessing
            narrative_type: Type of narrative to generate
            pure_land: Which pure land tradition (if applicable)
            custom_context: Additional context for generation

        Returns:
            GeneratedStory object
        """
        if target:
            target_name = target.name or target_name

        if self.use_llm and self.llm_client:
            return self._generate_with_llm(
                target_name, narrative_type, pure_land, custom_context
            )
        else:
            return self._generate_from_template(
                target_name, narrative_type, pure_land, custom_context
            )

    def _generate_from_template(self,
                                target_name: str,
                                narrative_type: NarrativeType,
                                pure_land: PureLandTradition,
                                custom_context: str) -> GeneratedStory:
        """Generate story from templates"""

        # Get appropriate template
        if narrative_type == NarrativeType.PURE_LAND_ARRIVAL:
            template = NarrativeTemplateLibrary.get_pure_land_arrival_template()
        elif narrative_type == NarrativeType.HELL_LIBERATION:
            template = NarrativeTemplateLibrary.get_hell_liberation_template()
        elif narrative_type == NarrativeType.EMPOWERMENT:
            template = NarrativeTemplateLibrary.get_empowerment_template()
        elif narrative_type == NarrativeType.RECONCILIATION:
            template = NarrativeTemplateLibrary.get_reconciliation_template()
        elif narrative_type == NarrativeType.HUNGRY_GHOST_NOURISHMENT:
            template = NarrativeTemplateLibrary.get_hungry_ghost_nourishment_template()
        else:
            template = NarrativeTemplateLibrary.get_pure_land_arrival_template()

        # Build story from template
        story_parts = []

        # Title
        story_parts.append(f"# {template.title}\n")
        story_parts.append(f"*For {target_name}*\n\n")

        # If pure land arrival, include description
        if narrative_type == NarrativeType.PURE_LAND_ARRIVAL:
            pl_desc = PureLandDescriptions.get_description(pure_land)
            story_parts.append(f"## {pl_desc['name']}\n\n")
            story_parts.append(pl_desc['description'].strip() + "\n\n")
            story_parts.append("---\n\n")

        # Opening
        story_parts.append("## The Journey Begins\n\n")
        story_parts.append(random.choice(template.opening) + "\n\n")

        # Journey
        story_parts.append("## The Path Unfolds\n\n")
        for segment in random.sample(template.journey, min(3, len(template.journey))):
            story_parts.append(segment + "\n\n")

        # Transformation
        story_parts.append("## The Moment of Liberation\n\n")
        story_parts.append(random.choice(template.transformation) + "\n\n")

        # Resolution
        story_parts.append("## The New Reality\n\n")
        story_parts.append(random.choice(template.resolution) + "\n\n")

        # If pure land, add activities
        if narrative_type == NarrativeType.PURE_LAND_ARRIVAL:
            pl_desc = PureLandDescriptions.get_description(pure_land)
            story_parts.append("## Life in the Pure Land\n\n")
            story_parts.append("Here, each day brings:\n\n")
            for activity in random.sample(pl_desc['activities'], min(4, len(pl_desc['activities']))):
                story_parts.append(f"- {activity}\n")
            story_parts.append("\n")

        # Dedication
        story_parts.append("---\n\n## Dedication\n\n")
        for dedication in template.dedication:
            story_parts.append(f"*{dedication}*\n\n")

        # Custom context if provided
        if custom_context:
            story_parts.append(f"\n---\n\n*{custom_context}*\n")

        story_text = "".join(story_parts)

        return GeneratedStory(
            target_name=target_name,
            narrative_type=narrative_type,
            title=template.title,
            story_text=story_text,
            pure_land=pure_land if narrative_type == NarrativeType.PURE_LAND_ARRIVAL else None,
            generation_method="template",
            timestamp=datetime.now(),
            dedication="\n".join(template.dedication),
            metadata={
                "template_tags": template.tags,
                "custom_context": custom_context
            }
        )

    def _generate_with_llm(self,
                          target_name: str,
                          narrative_type: NarrativeType,
                          pure_land: PureLandTradition,
                          custom_context: str) -> GeneratedStory:
        """Generate story using LLM"""

        # Build prompt for LLM
        prompt_parts = []

        prompt_parts.append(
            f"Generate a beautiful, compassionate story of liberation and healing "
            f"for a being named '{target_name}'.\n\n"
        )

        if narrative_type == NarrativeType.PURE_LAND_ARRIVAL:
            pl_desc = PureLandDescriptions.get_description(pure_land)
            prompt_parts.append(
                f"This is a story of arriving in {pl_desc['name']}.\n\n"
                f"Pure Land Description:\n{pl_desc['description']}\n\n"
                f"Create a narrative that:\n"
                f"1. Describes the transition from suffering to this pure land\n"
                f"2. Includes vivid sensory details of the arrival\n"
                f"3. Shows the healing and transformation that occurs\n"
                f"4. Ends with dedication of merit for all beings\n"
            )

        elif narrative_type == NarrativeType.HELL_LIBERATION:
            prompt_parts.append(
                f"This is a story of liberation from extreme suffering in hell realms.\n\n"
                f"Create a narrative that:\n"
                f"1. Honors the depth of the suffering without dwelling on graphic details\n"
                f"2. Shows how compassion reaches even the darkest places\n"
                f"3. Depicts the moment of liberation and transformation\n"
                f"4. Emphasizes forgiveness, healing, and new beginning\n"
                f"5. Ends with dedication for all beings in extreme suffering\n"
            )

        elif narrative_type == NarrativeType.EMPOWERMENT:
            prompt_parts.append(
                f"This is a story of the powerless gaining power and agency.\n\n"
                f"Create a narrative that:\n"
                f"1. Acknowledges the reality of oppression and powerlessness\n"
                f"2. Shows the awakening of inner strength and outer support\n"
                f"3. Depicts empowerment as wise, compassionate use of power\n"
                f"4. Shows the empowered helping others rise\n"
                f"5. Ends with dedication for all oppressed beings\n"
            )

        elif narrative_type == NarrativeType.RECONCILIATION:
            prompt_parts.append(
                f"This is a story of healing between one who harmed and one who was harmed.\n\n"
                f"Create a narrative that:\n"
                f"1. Honors the pain of both sides\n"
                f"2. Shows genuine accountability without excusing harm\n"
                f"3. Depicts forgiveness as empowerment, not weakness\n"
                f"4. Shows transformation for both victim and perpetrator\n"
                f"5. Ends with dedication for healing all cycles of violence\n"
            )

        prompt_parts.append(
            f"\nAdditional context: {custom_context}\n\n" if custom_context else ""
        )

        prompt_parts.append(
            "Make the story uplifting, healing, and spiritually profound. "
            "Use vivid imagery and emotional resonance. "
            "Write in a style that is both literary and accessible.\n\n"
            "Format with markdown headers for different sections."
        )

        full_prompt = "".join(prompt_parts)

        try:
            response = self.llm_client.generate(full_prompt)
            story_text = response.get('response', '')

            # Extract title if present
            title_match = story_text.split('\n')[0]
            title = title_match.strip('#').strip() if '#' in title_match else "Liberation Story"

            return GeneratedStory(
                target_name=target_name,
                narrative_type=narrative_type,
                title=title,
                story_text=story_text,
                pure_land=pure_land if narrative_type == NarrativeType.PURE_LAND_ARRIVAL else None,
                generation_method="llm",
                timestamp=datetime.now(),
                dedication="May this story benefit all beings",
                metadata={
                    "llm_provider": self.llm_provider,
                    "custom_context": custom_context,
                    "model": response.get('model', 'unknown')
                }
            )

        except Exception as e:
            print(f"LLM generation failed: {e}. Falling back to template.")
            return self._generate_from_template(
                target_name, narrative_type, pure_land, custom_context
            )

    def generate_batch_stories(self,
                              targets: List['BlessingTarget'],
                              narrative_type: NarrativeType = NarrativeType.PURE_LAND_ARRIVAL,
                              pure_land: PureLandTradition = PureLandTradition.UNIVERSAL_LIGHT,
                              max_stories: int = 10) -> List[GeneratedStory]:
        """
        Generate stories for multiple targets.

        Args:
            targets: List of BlessingTarget objects
            narrative_type: Type of narrative
            pure_land: Pure land tradition (if applicable)
            max_stories: Maximum number of stories to generate

        Returns:
            List of GeneratedStory objects
        """
        stories = []

        for target in targets[:max_stories]:
            story = self.generate_story(
                target=target,
                narrative_type=narrative_type,
                pure_land=pure_land
            )
            stories.append(story)

        return stories


class StoryExporter:
    """Export stories in various formats"""

    @staticmethod
    def export_as_markdown(story: GeneratedStory, filepath: str):
        """Export story as markdown file"""
        with open(filepath, 'w') as f:
            f.write(story.story_text)

    @staticmethod
    def export_as_json(story: GeneratedStory, filepath: str):
        """Export story metadata as JSON"""
        data = {
            "target_name": story.target_name,
            "narrative_type": story.narrative_type.value,
            "title": story.title,
            "story_text": story.story_text,
            "pure_land": story.pure_land.value if story.pure_land else None,
            "generation_method": story.generation_method,
            "timestamp": story.timestamp.isoformat(),
            "dedication": story.dedication,
            "metadata": story.metadata
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def export_collection(stories: List[GeneratedStory], directory: str):
        """Export multiple stories to a directory"""
        from pathlib import Path
        Path(directory).mkdir(parents=True, exist_ok=True)

        # Create index file
        index_path = Path(directory) / "INDEX.md"
        with open(index_path, 'w') as f:
            f.write("# Liberation Stories Collection\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Stories: {len(stories)}\n\n")

            for i, story in enumerate(stories, 1):
                filename = f"story_{i:03d}_{story.target_name.replace(' ', '_')[:30]}.md"
                f.write(f"{i}. [{story.title}](./{filename}) - *{story.target_name}*\n")

                # Export individual story
                story_path = Path(directory) / filename
                StoryExporter.export_as_markdown(story, str(story_path))


# Example usage
if __name__ == "__main__":
    print("Blessing Narratives System - Story Generation for Liberation\n")

    # Initialize generator (template-based)
    generator = StoryGenerator(use_llm=False)

    # Generate a pure land arrival story
    print("Generating Pure Land Arrival story...")
    story1 = generator.generate_story(
        target_name="Unknown Souls in the Bardo",
        narrative_type=NarrativeType.PURE_LAND_ARRIVAL,
        pure_land=PureLandTradition.SUKHAVATI
    )

    print(f"\nTitle: {story1.title}")
    print(f"Method: {story1.generation_method}")
    print("\n" + "="*70)
    print(story1.story_text[:500] + "...")

    # Generate hell liberation story
    print("\n" + "="*70)
    print("\nGenerating Hell Liberation story...")
    story2 = generator.generate_story(
        target_name="Beings in Extreme Suffering",
        narrative_type=NarrativeType.HELL_LIBERATION
    )

    print(f"\nTitle: {story2.title}")
    print("\n" + "="*70)
    print(story2.story_text[:500] + "...")
