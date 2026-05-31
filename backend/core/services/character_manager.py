"""
Character Manager Service

Manages characters woven into narrative generation and blessings.
Supports JSON persistence at ~/.vajra-stream/characters.json.
"""

import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class CharacterRole(str, Enum):
    """esoterically oriented roles for characters"""

    MASTER = "master"
    STUDENT = "student"
    ALCHEMIST = "alchemist"
    HERO = "hero"
    DEITY = "deity"
    GUARDIAN = "guardian"
    CUSTOM = "custom"


class CharacterSourceType(str, Enum):
    """Where the character data originated from"""

    MANUAL = "manual"
    GENERATED = "generated"
    MYTHOLOGY = "mythology"
    HISTORICAL = "historical"


@dataclass
class NarrativeCharacter:
    """A character personality woven into parables and narrative blessings"""

    # Identity
    id: str
    name: str
    role: CharacterRole
    description: str
    source_type: CharacterSourceType

    # ESOTERIC / CONFIGURATION
    dialogue_style: str = "cryptic and profound"
    associated_realms: list[str] = field(default_factory=list)  # IDs of realms they frequent
    mantra_preference: str | None = None
    elemental_anchor: str = "space"  # earth, water, fire, air, space, aether
    grounding_sense: str = ""
    channeling_state: str = ""
    anchoring_ritual: str = ""

    # System Tracking
    priority: int = 5  # 1-10
    is_active: bool = True
    exp: int = 0
    level: int = 1
    energy: int = 100  # Consumed by practices
    state: str = "Idle"  # Idle, Resting, Practicing, Channeling
    added_time: float = field(default_factory=time.time)
    last_used_time: float | None = None
    total_narratives_featured: int = 0
    history_log: list[str] = field(default_factory=list)
    relics: list[str] = field(default_factory=list)

    # Notes & Tags
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON saving"""
        data = asdict(self)
        data["role"] = self.role.value
        data["source_type"] = self.source_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NarrativeCharacter":
        """Create from dict"""
        data["role"] = CharacterRole(data["role"])
        data["source_type"] = CharacterSourceType(data["source_type"])
        return cls(**data)


class CharacterManager:
    """Manages characters for narrative generation, including JSON persistence and defaults seeding."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            home = Path.home()
            vajra_dir = home / ".vajra-stream"
            vajra_dir.mkdir(exist_ok=True)
            storage_path = str(vajra_dir / "characters.json")

        self.storage_path = storage_path
        self.characters: dict[str, NarrativeCharacter] = {}
        self._load()
        if not self.characters:
            self._seed_defaults()

    def _load(self):
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)
            for char_data in data.get("characters", []):
                char = NarrativeCharacter.from_dict(char_data)
                self.characters[char.id] = char
        except Exception as e:
            print(f"Error loading characters: {e}")

    def reload(self):
        """Re-read the JSON file from disk — call this after external seeding."""
        self.characters.clear()
        self._load()
        if not self.characters:
            self._seed_defaults()

    def _save(self):
        try:
            data = {
                "version": "1.0",
                "last_updated": time.time(),
                "characters": [c.to_dict() for c in self.characters.values()],
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving characters: {e}")
            raise

    def _seed_defaults(self):
        """Seed default archetypes into characters list"""
        defaults = [
            NarrativeCharacter(
                id="char_zhao_master",
                name="Zen Master Zhao",
                role=CharacterRole.MASTER,
                description="An enigmatic Zen master who teaches through paradox, koans, and sudden silent gestures.",
                source_type=CharacterSourceType.HISTORICAL,
                dialogue_style="Enigmatic zen riddles (Koans) and sharp, paradoxical remarks",
                associated_realms=["loc_sukhavati", "loc_bodh_gaya"],
                mantra_preference="om_mani_padme_hum",
                elemental_anchor="space",
                priority=6,
                notes="Classic Zen teacher archetype.",
            ),
            NarrativeCharacter(
                id="char_hermes_alchemist",
                name="Alchemist Hermes",
                role=CharacterRole.ALCHEMIST,
                description="A master of hermetic arts and chemical transmutations, carrying the caduceus.",
                source_type=CharacterSourceType.MYTHOLOGY,
                dialogue_style="Esoteric, verbose analogies about base metals, sulfur, and salt",
                associated_realms=["loc_alexandria", "loc_meru"],
                mantra_preference="custom",
                elemental_anchor="fire",
                priority=5,
                notes="Guide for alchemical parables.",
            ),
            NarrativeCharacter(
                id="char_chenrezig_deity",
                name="Bodhisattva Chenrezig",
                role=CharacterRole.DEITY,
                description="The multi-armed Lord of Universal Compassion, radiating white light of empathy.",
                source_type=CharacterSourceType.MYTHOLOGY,
                dialogue_style="Serene, highly compassionate, speaking of ultimate liberation and selflessness",
                associated_realms=["loc_sukhavati", "loc_kailash", "loc_bodh_gaya"],
                mantra_preference="om_mani_padme_hum",
                elemental_anchor="aether",
                priority=8,
                notes="Invocational deity of mercy.",
            ),
            NarrativeCharacter(
                id="char_suchandra_hero",
                name="King Suchandra",
                role=CharacterRole.HERO,
                description="The first Dharma King of Shambhala who requested and received the Kalachakra teachings.",
                source_type=CharacterSourceType.HISTORICAL,
                dialogue_style="Regal, righteous, commanding yet spiritually wise and precise",
                associated_realms=["loc_shambhala"],
                mantra_preference="custom",
                elemental_anchor="earth",
                priority=6,
                notes="Ruler of Shambhala.",
            ),
        ]
        for char in defaults:
            self.characters[char.id] = char
        self._save()

    def create_character(
        self,
        name: str,
        role: CharacterRole,
        description: str,
        source_type: CharacterSourceType,
        dialogue_style: str = "cryptic and profound",
        associated_realms: list[str] = None,
        mantra_preference: str | None = None,
        elemental_anchor: str = "space",
        grounding_sense: str = "",
        channeling_state: str = "",
        anchoring_ritual: str = "",
        priority: int = 5,
        is_active: bool = True,
        tags: list[str] = None,
        notes: str = "",
        character_id: str | None = None,
    ) -> NarrativeCharacter:
        """Create a new character and save to list"""
        if character_id is None:
            character_id = f"char_{int(time.time())}_{secrets.token_hex(4)}"

        char = NarrativeCharacter(
            id=character_id,
            name=name,
            role=role,
            description=description,
            source_type=source_type,
            dialogue_style=dialogue_style,
            associated_realms=associated_realms or [],
            mantra_preference=mantra_preference,
            elemental_anchor=elemental_anchor,
            grounding_sense=grounding_sense,
            channeling_state=channeling_state,
            anchoring_ritual=anchoring_ritual,
            priority=priority,
            is_active=is_active,
            tags=tags or [],
            notes=notes,
        )
        self.characters[char.id] = char
        self._save()
        return char

    def update_character(self, character_id: str, **updates) -> NarrativeCharacter | None:
        char = self.characters.get(character_id)
        if not char:
            return None
        for key, val in updates.items():
            if hasattr(char, key):
                if key == "role" and isinstance(val, str):
                    val = CharacterRole(val)
                elif key == "source_type" and isinstance(val, str):
                    val = CharacterSourceType(val)
                setattr(char, key, val)
        self._save()
        return char

    def delete_character(self, character_id: str) -> bool:
        if character_id in self.characters:
            del self.characters[character_id]
            self._save()
            return True
        return False

    def get_character(self, character_id: str) -> NarrativeCharacter | None:
        return self.characters.get(character_id)

    def get_all_characters(self) -> list[NarrativeCharacter]:
        return list(self.characters.values())

    def add_exp_and_log(self, character_id: str, exp_amount: int, event_summary: str):
        """Award EXP and log history to a character."""
        char = self.characters.get(character_id)
        if not char:
            return
        
        char.exp += exp_amount
        # Simple leveling logic (e.g., 100 exp = 1 level)
        if char.exp >= char.level * 100:
            char.level += 1
            char.history_log.append(f"Reached Level {char.level}!")
            
        char.history_log.append(event_summary)
        
        # Keep history log reasonable
        if len(char.history_log) > 50:
            char.history_log = char.history_log[-50:]
            
        self._save()

    def update_state(self, character_id: str, new_state: str, energy_change: int = 0):
        """Update a character's state and energy."""
        char = self.characters.get(character_id)
        if not char:
            return
        char.state = new_state
        char.energy = max(0, min(100, char.energy + energy_change))
        self._save()

    def add_relic(self, character_id: str, relic_name: str):
        """Award a relic to a character."""
        char = self.characters.get(character_id)
        if not char:
            return
        if relic_name not in char.relics:
            char.relics.append(relic_name)
            char.history_log.append(f"Discovered relic: {relic_name}")
            self._save()

    def get_active_characters(self) -> list[NarrativeCharacter]:
        return [c for c in self.characters.values() if c.is_active]

    def get_by_role(self, role: CharacterRole) -> list[NarrativeCharacter]:
        return [c for c in self.characters.values() if c.role == role]

    def record_character_feature(self, character_id: str) -> bool:
        char = self.characters.get(character_id)
        if not char:
            return False
        char.last_used_time = time.time()
        char.total_narratives_featured += 1
        self._save()
        return True

    def export_data(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "exported_at": time.time(),
            "characters": [c.to_dict() for c in self.characters.values()],
        }

    def import_data(self, data: dict[str, Any], merge: bool = False) -> int:
        if not merge:
            self.characters.clear()
        count = 0
        for char_data in data.get("characters", []):
            char = NarrativeCharacter.from_dict(char_data)
            self.characters[char.id] = char
            count += 1
        self._save()
        return count


# Global instance
_character_manager: CharacterManager | None = None


def get_character_manager() -> CharacterManager:
    global _character_manager
    if _character_manager is None:
        _character_manager = CharacterManager()
    return _character_manager
