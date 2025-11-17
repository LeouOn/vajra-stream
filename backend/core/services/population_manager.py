"""
Target Population Manager Service

Manages populations that receive automated blessings.
Supports both online and offline storage with JSON persistence.
"""

import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import secrets


class PopulationCategory(str, Enum):
    """Categories of populations"""
    MISSING_PERSONS = "missing_persons"
    UNIDENTIFIED_REMAINS = "unidentified_remains"
    DISASTER_VICTIMS = "disaster_victims"
    CONFLICT_ZONES = "conflict_zones"
    REFUGEES = "refugees"
    HOSPITAL_PATIENTS = "hospital_patients"
    NATURAL_DISASTER = "natural_disaster"
    HUMANITARIAN_CRISIS = "humanitarian_crisis"
    MEMORIAL = "memorial"
    ENDANGERED_SPECIES = "endangered_species"
    CUSTOM = "custom"


class SourceType(str, Enum):
    """Source types for populations"""
    MANUAL = "manual"
    LOCAL_DIRECTORY = "local_directory"
    RSS_FEED = "rss_feed"
    NEWS_API = "news_api"
    GDACS = "gdacs"
    RELIEF_WEB = "relief_web"
    CUSTOM_API = "custom_api"


@dataclass
class TargetPopulation:
    """A population/group that receives blessings"""

    # Identity
    id: str
    name: str
    description: str
    category: PopulationCategory

    # Source
    source_type: SourceType
    source_url: Optional[str] = None
    directory_path: Optional[str] = None

    # Configuration
    mantra_preference: str = "chenrezig"  # MantraType
    intentions: List[str] = field(default_factory=lambda: ["love", "healing", "peace"])
    repetitions_per_photo: int = 108
    display_duration_ms: int = 2000

    # Priority & Scheduling
    priority: int = 5  # 1-10, higher = more urgent
    is_urgent: bool = False
    is_active: bool = True

    # History
    added_time: float = field(default_factory=time.time)
    last_blessed_time: Optional[float] = None
    total_blessings_sent: int = 0
    total_mantras_repeated: int = 0
    total_session_duration: float = 0.0

    # Metadata
    photo_count: int = 0
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    # Offline Support
    offline_available: bool = True
    last_sync_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['category'] = self.category.value
        data['source_type'] = self.source_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TargetPopulation':
        """Create from dictionary"""
        # Convert string enums back
        data['category'] = PopulationCategory(data['category'])
        data['source_type'] = SourceType(data['source_type'])
        return cls(**data)


class PopulationManager:
    """
    Manages target populations for automated blessing

    Features:
    - CRUD operations
    - JSON persistence (offline-first)
    - Directory scanning for photo counts
    - Statistics tracking
    - Export/import for backup
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize population manager

        Args:
            storage_path: Path to JSON storage file
                         Default: ~/.vajra-stream/populations.json
        """
        if storage_path is None:
            home = Path.home()
            vajra_dir = home / ".vajra-stream"
            vajra_dir.mkdir(exist_ok=True)
            storage_path = str(vajra_dir / "populations.json")

        self.storage_path = storage_path
        self.populations: Dict[str, TargetPopulation] = {}
        self._load()

    def _load(self):
        """Load populations from JSON file"""
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load populations
            for pop_data in data.get('populations', []):
                pop = TargetPopulation.from_dict(pop_data)
                self.populations[pop.id] = pop

        except Exception as e:
            print(f"Error loading populations: {e}")

    def _save(self):
        """Save populations to JSON file"""
        try:
            data = {
                'version': '1.0',
                'last_updated': time.time(),
                'populations': [pop.to_dict() for pop in self.populations.values()]
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving populations: {e}")
            raise

    def _count_photos(self, directory_path: str) -> int:
        """Count image files in directory"""
        if not directory_path or not os.path.exists(directory_path):
            return 0

        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        count = 0

        try:
            path = Path(directory_path)
            for file in path.iterdir():
                if file.is_file() and file.suffix.lower() in image_extensions:
                    count += 1
        except Exception:
            pass

        return count

    def create_population(
        self,
        name: str,
        description: str,
        category: PopulationCategory,
        source_type: SourceType,
        directory_path: Optional[str] = None,
        source_url: Optional[str] = None,
        mantra_preference: str = "chenrezig",
        intentions: Optional[List[str]] = None,
        repetitions_per_photo: int = 108,
        display_duration_ms: int = 2000,
        priority: int = 5,
        is_urgent: bool = False,
        tags: Optional[List[str]] = None,
        notes: str = "",
        population_id: Optional[str] = None
    ) -> TargetPopulation:
        """
        Create a new target population

        Args:
            name: Population name
            description: Description of population
            category: Population category
            source_type: Where population data comes from
            directory_path: Path to photo directory (for local sources)
            source_url: URL for online sources
            mantra_preference: Default mantra
            intentions: List of intentions
            repetitions_per_photo: Mantra repetitions per photo
            display_duration_ms: Display duration in slideshow
            priority: Priority 1-10
            is_urgent: Mark as urgent
            tags: Optional tags
            notes: Optional notes
            population_id: Optional custom ID

        Returns:
            Created TargetPopulation
        """
        # Generate ID if not provided
        if population_id is None:
            population_id = f"pop_{int(time.time())}_{secrets.token_hex(4)}"

        # Default intentions
        if intentions is None:
            intentions = ["love", "healing", "peace"]

        # Count photos if directory provided
        photo_count = 0
        offline_available = False
        if directory_path:
            photo_count = self._count_photos(directory_path)
            offline_available = True

        # Create population
        population = TargetPopulation(
            id=population_id,
            name=name,
            description=description,
            category=category,
            source_type=source_type,
            source_url=source_url,
            directory_path=directory_path,
            mantra_preference=mantra_preference,
            intentions=intentions,
            repetitions_per_photo=repetitions_per_photo,
            display_duration_ms=display_duration_ms,
            priority=priority,
            is_urgent=is_urgent,
            photo_count=photo_count,
            tags=tags or [],
            notes=notes,
            offline_available=offline_available
        )

        # Save
        self.populations[population.id] = population
        self._save()

        return population

    def update_population(
        self,
        population_id: str,
        **updates
    ) -> Optional[TargetPopulation]:
        """
        Update a population

        Args:
            population_id: ID of population to update
            **updates: Fields to update

        Returns:
            Updated population or None if not found
        """
        population = self.populations.get(population_id)
        if not population:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(population, key):
                # Handle enum conversions
                if key == 'category' and isinstance(value, str):
                    value = PopulationCategory(value)
                elif key == 'source_type' and isinstance(value, str):
                    value = SourceType(value)

                setattr(population, key, value)

        # Recount photos if directory changed
        if 'directory_path' in updates:
            population.photo_count = self._count_photos(population.directory_path)
            population.offline_available = bool(population.directory_path)

        self._save()
        return population

    def delete_population(self, population_id: str) -> bool:
        """
        Delete a population

        Args:
            population_id: ID of population to delete

        Returns:
            True if deleted, False if not found
        """
        if population_id in self.populations:
            del self.populations[population_id]
            self._save()
            return True
        return False

    def get_population(self, population_id: str) -> Optional[TargetPopulation]:
        """Get a population by ID"""
        return self.populations.get(population_id)

    def get_all_populations(self) -> List[TargetPopulation]:
        """Get all populations"""
        return list(self.populations.values())

    def get_active_populations(self) -> List[TargetPopulation]:
        """Get all active populations"""
        return [p for p in self.populations.values() if p.is_active]

    def get_by_category(
        self,
        category: PopulationCategory
    ) -> List[TargetPopulation]:
        """Get populations by category"""
        return [p for p in self.populations.values() if p.category == category]

    def get_urgent_populations(self) -> List[TargetPopulation]:
        """Get urgent populations"""
        return [p for p in self.populations.values() if p.is_urgent and p.is_active]

    def record_blessing_session(
        self,
        population_id: str,
        blessings_sent: int,
        mantras_repeated: int,
        session_duration: float
    ) -> bool:
        """
        Record statistics from a blessing session

        Args:
            population_id: Population that was blessed
            blessings_sent: Number of blessings sent
            mantras_repeated: Number of mantras repeated
            session_duration: Duration in seconds

        Returns:
            True if recorded, False if population not found
        """
        population = self.populations.get(population_id)
        if not population:
            return False

        population.last_blessed_time = time.time()
        population.total_blessings_sent += blessings_sent
        population.total_mantras_repeated += mantras_repeated
        population.total_session_duration += session_duration

        self._save()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        populations = list(self.populations.values())

        return {
            'total_populations': len(populations),
            'active_populations': len([p for p in populations if p.is_active]),
            'urgent_populations': len([p for p in populations if p.is_urgent]),
            'total_blessings_sent': sum(p.total_blessings_sent for p in populations),
            'total_mantras_repeated': sum(p.total_mantras_repeated for p in populations),
            'total_session_duration': sum(p.total_session_duration for p in populations),
            'categories': {
                cat.value: len([p for p in populations if p.category == cat])
                for cat in PopulationCategory
            },
            'never_blessed': len([p for p in populations if p.last_blessed_time is None]),
            'offline_available': len([p for p in populations if p.offline_available])
        }

    def export_data(self) -> Dict[str, Any]:
        """Export all data for backup"""
        return {
            'version': '1.0',
            'exported_at': time.time(),
            'populations': [pop.to_dict() for pop in self.populations.values()]
        }

    def import_data(self, data: Dict[str, Any], merge: bool = False) -> int:
        """
        Import data from backup

        Args:
            data: Exported data
            merge: If True, merge with existing. If False, replace all.

        Returns:
            Number of populations imported
        """
        if not merge:
            self.populations.clear()

        count = 0
        for pop_data in data.get('populations', []):
            pop = TargetPopulation.from_dict(pop_data)
            self.populations[pop.id] = pop
            count += 1

        self._save()
        return count


# Global instance
_population_manager: Optional[PopulationManager] = None


def get_population_manager() -> PopulationManager:
    """Get or create global population manager instance"""
    global _population_manager
    if _population_manager is None:
        _population_manager = PopulationManager()
    return _population_manager
