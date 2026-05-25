"""
Blessings Module
Adapter wrapping core/blessing_narratives and core/compassionate_blessings.

Provides rich narrative-generated blessings (pure land arrivals, hell liberation,
empowerment, reconciliation, healing journeys) and compassionate blessing
allocation/database functionality.
"""

import uuid
from datetime import datetime
from typing import Any

from infrastructure.event_bus import EnhancedEventBus
from modules.interfaces import BlessingGenerated, BlessingGenerator, EventBus


class BlessingService(BlessingGenerator):
    """Blessing generation service — wraps core narrative engine."""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self._story_generator = None
        self._blessing_db = None
        self._blessing_allocator = None

    # ------------------------------------------------------------------
    # Lazy-load core modules
    # ------------------------------------------------------------------

    @property
    def story_generator(self):
        """Lazy-load the narrative story generator."""
        if self._story_generator is None:
            from core.blessing_narratives import (
                NarrativeType,
                PureLandTradition,
                StoryGenerator,
            )

            self._narrative_type = NarrativeType
            self._pure_land_tradition = PureLandTradition
            self._story_generator = StoryGenerator(use_llm=False)
        return self._story_generator

    @property
    def blessing_db(self):
        """Lazy-load the compassionate blessings database."""
        if self._blessing_db is None:
            from core.compassionate_blessings import BlessingDatabase

            self._blessing_db = BlessingDatabase()
        return self._blessing_db

    @property
    def blessing_allocator(self):
        """Lazy-load the blessing allocator."""
        if self._blessing_allocator is None:
            from core.compassionate_blessings import BlessingAllocator

            self._blessing_allocator = BlessingAllocator()
        return self._blessing_allocator

    # ------------------------------------------------------------------
    # Narrative blessing generation (wraps core/blessing_narratives)
    # ------------------------------------------------------------------

    def generate_blessing(
        self,
        target_name: str,
        intention: str = "peace and happiness",
        tradition: str = "universal",
        include_mantra: bool = True,
        include_dedication: bool = True,
    ) -> dict[str, Any]:
        """
        Generate a rich narrative blessing using the core story engine.

        Maps tradition → narrative type for deep, immersive blessing stories:
        - universal → healing journey
        - buddhist → pure land arrival (Sukhavati)
        - tibetan → pure land arrival (Shambhala)
        - zen → pure land arrival (Universal Light)
        """
        # Map tradition to narrative type and pure land
        narrative_map = {
            "universal": ("healing_journey", "universal_light"),
            "buddhist": ("pure_land_arrival", "sukhavati"),
            "tibetan": ("pure_land_arrival", "shambhala"),
            "zen": ("pure_land_arrival", "universal_light"),
        }

        nt_key, pl_key = narrative_map.get(tradition, ("healing_journey", "universal_light"))

        try:
            # Use rich narrative engine
            nt = getattr(self._narrative_type, nt_key.upper())
            pl = getattr(self._pure_land_tradition, pl_key.upper())

            story = self.story_generator.generate_story(
                target_name=target_name,
                narrative_type=nt,
                pure_land=pl,
                custom_context=intention,
            )

            blessing_text = story.story_text
        except Exception:
            # Fallback: simple template if narrative engine fails
            blessing_text = self._fallback_blessing(target_name, intention, tradition)

        # Mantra selection
        mantra = None
        if include_mantra:
            mantra_map = {
                "universal": "Om Shanti Shanti Shanti",
                "buddhist": "Om Mani Padme Hum",
                "tibetan": "Om Ah Hum Vajra Guru Padma Siddhi Hum",
                "zen": "Namu Amida Butsu",
            }
            mantra = mantra_map.get(tradition, "Om")

        # Dedication
        dedication = None
        if include_dedication:
            dedications = [
                "By this merit, may all beings find peace, happiness, and liberation.",
                "May whatever merit arises from this practice benefit all beings throughout space and time.",
                "Gate gate pāragate pārasaṃgate bodhi svāhā",
                "May all beings be free from suffering and the causes of suffering.",
            ]
            import random

            dedication = random.choice(dedications)

        result = {
            "blessing_text": blessing_text.strip(),
            "target_name": target_name,
            "intention": intention,
            "tradition": tradition,
            "mantra": mantra,
            "dedication": dedication,
        }

        # Publish event
        if self.event_bus:
            event = BlessingGenerated(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                target_name=target_name,
                blessing_text=blessing_text[:500],  # Truncate for event
                tradition=tradition,
            )
            self.event_bus.publish(event)

        return result

    def generate_mass_liberation(
        self, event_name: str, location: str, souls_count: int = 1000, duration_minutes: int = 108
    ) -> dict[str, Any]:
        """
        Generate a mass liberation blessing using the hell-liberation narrative engine.
        """
        try:
            from core.blessing_narratives import NarrativeType

            story = self.story_generator.generate_story(
                target_name=f"{souls_count} souls affected by {event_name} in {location}",
                narrative_type=NarrativeType.HELL_LIBERATION,
                custom_context=f"Mass liberation for {souls_count} beings affected by {event_name}",
            )
            blessing_text = story.story_text
        except Exception:
            blessing_text = self._fallback_mass_liberation(event_name, location, souls_count)

        return {
            "event_name": event_name,
            "location": location,
            "souls_count": souls_count,
            "blessing_text": blessing_text.strip(),
            "primary_mantra": "Namo Amitabha Buddha",
            "duration_minutes": duration_minutes,
            "recitation_count": duration_minutes * 10,
        }

    def generate_narrative(
        self,
        target_name: str,
        narrative_type: str = "pure_land_arrival",
        pure_land: str = "sukhavati",
        custom_context: str = "",
    ) -> dict[str, Any]:
        """
        Generate a specific type of liberation narrative.

        narrative_type: pure_land_arrival, hell_liberation, empowerment,
                       reconciliation, hungry_ghost_nourishment, healing_journey
        pure_land: sukhavati, shambhala, universal_light, nature_paradise, abhirati
        """
        from core.blessing_narratives import NarrativeType, PureLandTradition

        nt = NarrativeType[narrative_type.upper()]
        pl = PureLandTradition[pure_land.upper()]

        story = self.story_generator.generate_story(
            target_name=target_name,
            narrative_type=nt,
            pure_land=pl,
            custom_context=custom_context,
        )

        return {
            "title": story.title,
            "story_text": story.story_text,
            "target_name": target_name,
            "narrative_type": narrative_type,
            "pure_land": pure_land,
            "generation_method": story.generation_method,
            "dedication": story.dedication,
        }

    def get_available_traditions(self) -> list[dict[str, Any]]:
        """Get available blessing traditions with narrative types."""
        return [
            {
                "id": "universal",
                "name": "Universal / Interfaith",
                "mantra": "Om Shanti",
                "narrative": "Healing Journey",
                "description": "A gentle path of restoration and wholeness",
            },
            {
                "id": "buddhist",
                "name": "Buddhist",
                "mantra": "Om Mani Padme Hum",
                "narrative": "Pure Land Arrival (Sukhavati)",
                "description": "Arrival in Amitabha's Western Pure Land of Bliss",
            },
            {
                "id": "tibetan",
                "name": "Tibetan Buddhist",
                "mantra": "Om Ah Hum Vajra Guru Padma Siddhi Hum",
                "narrative": "Pure Land Arrival (Shambhala)",
                "description": "The hidden kingdom of enlightened society",
            },
            {
                "id": "zen",
                "name": "Zen Buddhist",
                "mantra": "Namu Amida Butsu",
                "narrative": "Pure Land Arrival (Universal Light)",
                "description": "A realm of pure light beyond all tradition",
            },
        ]

    def get_narrative_types(self) -> list[dict[str, Any]]:
        """Get available narrative types."""
        return [
            {"id": "pure_land_arrival", "name": "Pure Land Arrival", "description": "Arrival in a blissful pure land"},
            {"id": "hell_liberation", "name": "Hell Liberation", "description": "Liberation from extreme suffering"},
            {"id": "empowerment", "name": "Empowerment", "description": "The powerless gaining power and voice"},
            {"id": "reconciliation", "name": "Reconciliation", "description": "Healing between harmed and harmer"},
            {
                "id": "hungry_ghost_nourishment",
                "name": "Hungry Ghost Nourishment",
                "description": "Satisfying infinite hunger",
            },
            {"id": "healing_journey", "name": "Healing Journey", "description": "Path of restoration and wholeness"},
        ]

    # ------------------------------------------------------------------
    # Compassionate blessing database (wraps core/compassionate_blessings)
    # ------------------------------------------------------------------

    def create_blessing_target(
        self,
        name: str,
        category: str = "suffering_unknown",
        location: tuple[float, float] | None = None,
        date: datetime | None = None,
        description: str = "",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Create a blessing target in the database."""
        from core.compassionate_blessings import BlessingCategory, create_target

        bc = BlessingCategory[category.upper()]
        target = create_target(
            name=name,
            category=bc,
            location=location,
            date=date,
            description=description,
            priority=priority,
        )
        self.blessing_db.add_target(target)
        return {"identifier": target.identifier, "name": target.name, "category": target.category.value}

    def get_blessing_targets(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get blessing targets, optionally filtered by category."""
        if category:
            from core.compassionate_blessings import BlessingCategory

            bc = BlessingCategory[category.upper()]
            targets = self.blessing_db.get_targets_by_category(bc)
        else:
            targets = self.blessing_db.get_all_targets()

        return [
            {
                "identifier": t.identifier,
                "name": t.name,
                "category": t.category.value,
                "mantras_dedicated": t.mantras_dedicated,
                "priority": t.priority,
            }
            for t in targets
        ]

    def get_blessing_stats(self) -> dict[str, Any]:
        """Get overall blessing statistics."""
        return self.blessing_db.get_statistics()

    def allocate_blessings(
        self, total_mantras: int, method: str = "equitable", category: str | None = None
    ) -> dict[str, Any]:
        """Allocate blessing mantras across targets using the specified method."""
        if category:
            from core.compassionate_blessings import BlessingCategory

            targets = self.blessing_db.get_targets_by_category(BlessingCategory[category.upper()])
        else:
            targets = self.blessing_db.get_all_targets()

        if method == "equitable":
            allocation = self.blessing_allocator.allocate_equitable(total_mantras, targets)
        elif method == "urgent":
            allocation = self.blessing_allocator.allocate_urgent(total_mantras, targets)
        elif method == "weighted":
            allocation = self.blessing_allocator.allocate_weighted(total_mantras, targets)
        else:
            allocation = self.blessing_allocator.allocate_equitable(total_mantras, targets)

        return {
            "total_mantras": total_mantras,
            "method": method,
            "targets_count": len(targets),
            "allocation": {
                tid: count
                for tid, count in allocation.items()
            },
        }

    # ------------------------------------------------------------------
    # Fallbacks (used when core modules fail to load)
    # ------------------------------------------------------------------

    def _fallback_blessing(self, target_name: str, intention: str, tradition: str) -> str:
        """Minimal fallback blessing template."""
        return f"""
May {target_name} be filled with loving-kindness.
May {target_name} be well.
May {target_name} be peaceful and at ease.
May {target_name} be happy.

May {intention} be fulfilled for the highest good.

May all beings everywhere share in these blessings.
        """

    def _fallback_mass_liberation(self, event_name: str, location: str, souls_count: int) -> str:
        """Minimal fallback mass liberation."""
        return f"""
For all those affected by {event_name} in {location},

May the {souls_count} souls find immediate peace and liberation.
May all suffering cease in this very moment.
May the light of wisdom guide each being to the highest rebirth.

May those who remain find solace, healing, and strength.

Namo Amitabha Buddha
Om Mani Padme Hum
        """
