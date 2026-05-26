"""
Location Manager Service

Manages locations and metaphysical realms for narrative generation and blessings.
Supports JSON persistence at ~/.vajra-stream/locations.json.
"""

import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class LocationType(str, Enum):
    """esoterically oriented types of locations"""

    EARTHLY_SACRED = "earthly_sacred"
    METAPHYSICAL_REALM = "metaphysical_realm"
    COSMIC_ANCHOR = "cosmic_anchor"
    HISTORICAL_ACADEMY = "historical_academy"
    CUSTOM = "custom"


class LocationSourceType(str, Enum):
    """Where the location data originated from"""

    MANUAL = "manual"
    GENERATED = "generated"
    MYTHOLOGY = "mythology"
    GEOGRAPHIC = "geographic"


@dataclass
class NarrativeLocation:
    """A location on Earth or a metaphysical realm where parables/blessings take place"""

    # Identity
    id: str
    name: str
    description: str
    location_type: LocationType
    source_type: LocationSourceType
    is_metaphysical: bool = False

    # Earthly coordinates (if applicable)
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "UTC"

    # Metaphysical dimensions (if applicable)
    celestial_coordinates: str | None = None  # e.g., "Taurus 15 degrees", "Sun conjunct Jupiter"
    dimension_frequency: float | None = None  # e.g., 528.0 for 528Hz, 432.0 for 432Hz

    # Esoteric settings
    realm_governor: str | None = None  # Ruler, guardian, or deity
    astrological_anchor: str | None = None  # Primary planetary line or star anchor
    elemental_affinity: str | None = None  # Fire, Water, Earth, Air, Space, Aether

    # System Tracking
    priority: int = 5  # 1-10
    is_active: bool = True
    added_time: float = field(default_factory=time.time)
    last_used_time: float | None = None
    total_narratives_featured: int = 0

    # Notes & Tags
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON saving"""
        data = asdict(self)
        data["location_type"] = self.location_type.value
        data["source_type"] = self.source_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NarrativeLocation":
        """Create from dict"""
        data["location_type"] = LocationType(data["location_type"])
        data["source_type"] = LocationSourceType(data["source_type"])
        return cls(**data)


class LocationManager:
    """Manages locations and realms for narrative generation, including JSON persistence and defaults seeding."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            home = Path.home()
            vajra_dir = home / ".vajra-stream"
            vajra_dir.mkdir(exist_ok=True)
            storage_path = str(vajra_dir / "locations.json")

        self.storage_path = storage_path
        self.locations: dict[str, NarrativeLocation] = {}
        self._load()
        if not self.locations:
            self._seed_defaults()

    def _load(self):
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)
            for loc_data in data.get("locations", []):
                loc = NarrativeLocation.from_dict(loc_data)
                self.locations[loc.id] = loc
        except Exception as e:
            print(f"Error loading locations: {e}")

    def reload(self):
        """Re-read the JSON file from disk — call this after external seeding."""
        self.locations.clear()
        self._load()
        if not self.locations:
            self._seed_defaults()

    def _save(self):
        try:
            data = {
                "version": "1.0",
                "last_updated": time.time(),
                "locations": [l.to_dict() for l in self.locations.values()],
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving locations: {e}")
            raise

    def _seed_defaults(self):
        """Seed default settings into locations list"""
        defaults = [
            NarrativeLocation(
                id="loc_sukhavati",
                name="Sukhavati (Pure Land)",
                description="The Western Pure Land of Ultimate Bliss governed by Amitabha Buddha, filled with lotus blossoms and jewels.",
                location_type=LocationType.METAPHYSICAL_REALM,
                source_type=LocationSourceType.MYTHOLOGY,
                is_metaphysical=True,
                celestial_coordinates="Western Quadrant / Infinite Light Gateway",
                dimension_frequency=528.0,
                realm_governor="Amitabha Buddha",
                astrological_anchor="Sun in Leo, Jupiter in Pisces",
                elemental_affinity="Lotus / Light",
                priority=7,
                notes="Primary Buddhist pure land.",
            ),
            NarrativeLocation(
                id="loc_shambhala",
                name="Shambhala Kingdom",
                description="The mythical kingdom hidden in the Himalayas, preserving the Kalachakra teachings.",
                location_type=LocationType.METAPHYSICAL_REALM,
                source_type=LocationSourceType.MYTHOLOGY,
                is_metaphysical=True,
                celestial_coordinates="Northern Axis / Secret Valley Grid",
                dimension_frequency=432.0,
                realm_governor="King Suchandra",
                astrological_anchor="North Node in Taurus",
                elemental_affinity="Aether",
                priority=6,
                notes="Place of esoteric wisdom.",
            ),
            NarrativeLocation(
                id="loc_kailash",
                name="Mount Kailash",
                description="A sacred peak in Tibet, revered as the spiritual center of the universe by four religions.",
                location_type=LocationType.EARTHLY_SACRED,
                source_type=LocationSourceType.GEOGRAPHIC,
                is_metaphysical=False,
                latitude=31.0667,
                longitude=81.3125,
                timezone="Asia/Shanghai",
                realm_governor="Shiva / Chakrasamvara",
                astrological_anchor="Saturn conjunct Midheaven",
                elemental_affinity="Earth / Ice",
                priority=8,
                notes="Sacred physical anchor point.",
            ),
            NarrativeLocation(
                id="loc_alexandria",
                name="Alexandria Hermetic Academy",
                description="The ancient intellectual sanctuary where Greek philosophy merged with Egyptian Hermetic wisdom.",
                location_type=LocationType.HISTORICAL_ACADEMY,
                source_type=LocationSourceType.GEOGRAPHIC,
                is_metaphysical=False,
                latitude=31.2001,
                longitude=29.9187,
                timezone="Africa/Cairo",
                realm_governor="Hermes Trismegistus",
                astrological_anchor="Mercury conjunct Ascendant",
                elemental_affinity="Fire / Air",
                priority=6,
                notes="Historical hermetic learning center.",
            ),
        ]
        for loc in defaults:
            self.locations[loc.id] = loc
        self._save()

    def create_location(
        self,
        name: str,
        description: str,
        location_type: LocationType,
        source_type: LocationSourceType,
        is_metaphysical: bool = False,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone: str = "UTC",
        celestial_coordinates: str | None = None,
        dimension_frequency: float | None = None,
        realm_governor: str | None = None,
        astrological_anchor: str | None = None,
        elemental_affinity: str | None = None,
        priority: int = 5,
        is_active: bool = True,
        tags: list[str] | None = None,
        notes: str = "",
        location_id: str | None = None,
    ) -> NarrativeLocation:
        if location_id is None:
            location_id = f"loc_{int(time.time())}_{secrets.token_hex(4)}"

        loc = NarrativeLocation(
            id=location_id,
            name=name,
            description=description,
            location_type=location_type,
            source_type=source_type,
            is_metaphysical=is_metaphysical,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            celestial_coordinates=celestial_coordinates,
            dimension_frequency=dimension_frequency,
            realm_governor=realm_governor,
            astrological_anchor=astrological_anchor,
            elemental_affinity=elemental_affinity,
            priority=priority,
            is_active=is_active,
            tags=tags or [],
            notes=notes,
        )
        self.locations[loc.id] = loc
        self._save()
        return loc

    def update_location(self, location_id: str, **updates) -> NarrativeLocation | None:
        loc = self.locations.get(location_id)
        if not loc:
            return None
        for key, val in updates.items():
            if hasattr(loc, key):
                if key == "location_type" and isinstance(val, str):
                    val = LocationType(val)
                elif key == "source_type" and isinstance(val, str):
                    val = LocationSourceType(val)
                setattr(loc, key, val)
        self._save()
        return loc

    def delete_location(self, location_id: str) -> bool:
        if location_id in self.locations:
            del self.locations[location_id]
            self._save()
            return True
        return False

    def get_location(self, location_id: str) -> NarrativeLocation | None:
        return self.locations.get(location_id)

    def get_all_locations(self) -> list[NarrativeLocation]:
        return list(self.locations.values())

    def get_active_locations(self) -> list[NarrativeLocation]:
        return [l for l in self.locations.values() if l.is_active]

    def get_by_type(self, location_type: LocationType) -> list[NarrativeLocation]:
        return [l for l in self.locations.values() if l.location_type == location_type]

    def record_location_feature(self, location_id: str) -> bool:
        loc = self.locations.get(location_id)
        if not loc:
            return False
        loc.last_used_time = time.time()
        loc.total_narratives_featured += 1
        self._save()
        return True

    def export_data(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "exported_at": time.time(),
            "locations": [l.to_dict() for l in self.locations.values()],
        }

    def import_data(self, data: dict[str, Any], merge: bool = False) -> int:
        if not merge:
            self.locations.clear()
        count = 0
        for loc_data in data.get("locations", []):
            loc = NarrativeLocation.from_dict(loc_data)
            self.locations[loc.id] = loc
            count += 1
        self._save()
        return count


# Global instance
_location_manager: LocationManager | None = None


def get_location_manager() -> LocationManager:
    global _location_manager
    if _location_manager is None:
        _location_manager = LocationManager()
    return _location_manager
