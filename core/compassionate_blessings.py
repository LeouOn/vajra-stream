"""
Compassionate Blessing System — targeted intention/blessing infrastructure.

Provides the data model, persistence, and allocation algorithms for directing
healing intentions to specific beings or populations. Integrates astrocartographic
coordinates, radionics rates, and temporal/spatial targeting for precise
blessing transmission.

Key components:
- :class:`BlessingTarget` — dataclass representing an individual or group
  with identity, location, temporal data, and blessing tracking.
- :class:`BlessingDatabase` — SQLite-backed CRUD for targets, sessions, and dedications.
- :class:`BlessingAllocator` — three allocation strategies: equitable, urgent,
  and priority-weighted.
- :class:`BlessingCoordinate` / :class:`GeoCoordinate` — multi-dimensional
  targeting (Julian day, lat/lon, natal chart, radionics rates).

Dependencies:
    sqlite3, hashlib (stdlib).
    Optional: :class:`~core.astrocartography.CalendarConverter` for date conversion.

Exports:
    BlessingCategory, MantraType — enums.
    GeoCoordinate, BlessingCoordinate, BlessingTarget — data classes.
    BlessingDatabase, BlessingAllocator — core services.
    create_target — convenience factory function.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BlessingCategory(Enum):
    """Categories of beings receiving blessings."""

    MISSING_PERSON = "missing_person"
    UNIDENTIFIED_REMAINS = "unidentified_remains"
    SHELTER_ANIMAL = "shelter_animal"
    REFUGEE = "refugee"
    INCARCERATED = "incarcerated"
    HOMELESS = "homeless"
    ENDANGERED_SPECIES = "endangered_species"
    HUNGRY_GHOST = "hungry_ghost"  # Buddhist cosmology - beings in suffering
    LAND_SPIRIT = "land_spirit"  # Spirits at sites of suffering
    DECEASED = "deceased"
    SUFFERING_UNKNOWN = "suffering_unknown"  # General category
    ALL_SENTIENT_BEINGS = "all_sentient_beings"  # Broadest scope


class MantraType(Enum):
    """Types of mantras for different blessing purposes."""

    CHENREZIG = "om_mani_padme_hum"  # Universal compassion
    MEDICINE_BUDDHA = "bekandze"  # Healing
    GREEN_TARA = "om_tare_tuttare"  # Protection from suffering
    VAJRASATTVA = "vajrasattva_100"  # Purification
    AMITABHA = "om_ami_dewa_hri"  # Peaceful death, liberation
    CUSTOM = "custom"


@dataclass
class GeoCoordinate:
    """Geographic location data."""

    latitude: float
    longitude: float
    location_name: str = ""
    timezone: str = "UTC"

    def to_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_name": self.location_name,
            "timezone": self.timezone,
        }


@dataclass
class BlessingCoordinate:
    """
    Multi-dimensional coordinate for precise blessing targeting.

    Combines temporal, spatial, and astrological data for optimal
    energetic transmission.
    """

    # Temporal layer
    julian_day: float
    calendar_system: str = "auto"  # julian/gregorian/auto
    reference_datetime: datetime | None = None  # Birth, discovery, etc.

    # Spatial layer
    location: GeoCoordinate | None = None

    # Astrological layer
    natal_chart_data: dict | None = None
    dominant_planetary_lines: list[dict] = field(default_factory=list)
    active_parans: list[dict] = field(default_factory=list)

    # Radionics layer
    witness_data: dict = field(default_factory=dict)
    radionics_rate: list[int] | None = None

    def to_dict(self) -> dict:
        return {
            "julian_day": self.julian_day,
            "calendar_system": self.calendar_system,
            "reference_datetime": self.reference_datetime.isoformat() if self.reference_datetime else None,
            "location": self.location.to_dict() if self.location else None,
            "natal_chart_data": self.natal_chart_data,
            "dominant_planetary_lines": self.dominant_planetary_lines,
            "active_parans": self.active_parans,
            "witness_data": self.witness_data,
            "radionics_rate": self.radionics_rate,
        }


@dataclass
class BlessingTarget:
    """
    Individual or group receiving directed compassion.

    Represents a being or group of beings in the database,
    with as much information as is known.
    """

    # Identity (as much as known)
    identifier: str  # Unique ID
    name: str | None = None  # "Unknown" if not known
    category: BlessingCategory = BlessingCategory.SUFFERING_UNKNOWN

    # Description
    description: str = ""
    case_number: str | None = None

    # Temporal data
    relevant_date: datetime | None = None  # Birth, disappearance, death, etc.
    discovery_date: datetime | None = None
    last_updated: datetime = field(default_factory=datetime.now)

    # Blessing coordinates
    coordinates: BlessingCoordinate | None = None

    # Media/witness
    photograph_path: str | None = None
    additional_data: dict = field(default_factory=dict)

    # Blessing tracking
    mantras_dedicated: int = 0
    prayer_wheel_rotations: int = 0
    dedication_sessions: list[datetime] = field(default_factory=list)

    # Intention
    intention: str = "Complete liberation from suffering"

    # Priority/urgency (1-10, 10 highest)
    priority: int = 5

    def generate_identifier(self) -> str:
        """Generate unique identifier if not provided."""
        if self.identifier:
            return self.identifier

        # Create hash from available data
        data_str = f"{self.name or 'unknown'}_{self.category.value}_{self.relevant_date or datetime.now()}"
        hash_obj = hashlib.md5(data_str.encode())
        return f"{self.category.value}_{hash_obj.hexdigest()[:12]}"

    def to_dict(self) -> dict:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "case_number": self.case_number,
            "relevant_date": self.relevant_date.isoformat() if self.relevant_date else None,
            "discovery_date": self.discovery_date.isoformat() if self.discovery_date else None,
            "last_updated": self.last_updated.isoformat(),
            "coordinates": self.coordinates.to_dict() if self.coordinates else None,
            "photograph_path": self.photograph_path,
            "additional_data": self.additional_data,
            "mantras_dedicated": self.mantras_dedicated,
            "prayer_wheel_rotations": self.prayer_wheel_rotations,
            "dedication_sessions": [dt.isoformat() for dt in self.dedication_sessions],
            "intention": self.intention,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlessingTarget":
        """Create from dictionary."""
        # Parse dates
        relevant_date = datetime.fromisoformat(data["relevant_date"]) if data.get("relevant_date") else None
        discovery_date = datetime.fromisoformat(data["discovery_date"]) if data.get("discovery_date") else None
        last_updated = datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else datetime.now()

        # Parse dedication sessions
        dedication_sessions = [datetime.fromisoformat(dt) for dt in data.get("dedication_sessions", [])]

        # Parse location if present
        coordinates = None
        if data.get("coordinates"):
            coord_data = data["coordinates"]
            location = None
            if coord_data.get("location"):
                loc_data = coord_data["location"]
                location = GeoCoordinate(
                    latitude=loc_data["latitude"],
                    longitude=loc_data["longitude"],
                    location_name=loc_data.get("location_name", ""),
                    timezone=loc_data.get("timezone", "UTC"),
                )

            ref_dt = (
                datetime.fromisoformat(coord_data["reference_datetime"])
                if coord_data.get("reference_datetime")
                else None
            )

            coordinates = BlessingCoordinate(
                julian_day=coord_data["julian_day"],
                calendar_system=coord_data.get("calendar_system", "auto"),
                reference_datetime=ref_dt,
                location=location,
                natal_chart_data=coord_data.get("natal_chart_data"),
                dominant_planetary_lines=coord_data.get("dominant_planetary_lines", []),
                active_parans=coord_data.get("active_parans", []),
                witness_data=coord_data.get("witness_data", {}),
                radionics_rate=coord_data.get("radionics_rate"),
            )

        return cls(
            identifier=data["identifier"],
            name=data.get("name"),
            category=BlessingCategory(data.get("category", BlessingCategory.SUFFERING_UNKNOWN.value)),
            description=data.get("description", ""),
            case_number=data.get("case_number"),
            relevant_date=relevant_date,
            discovery_date=discovery_date,
            last_updated=last_updated,
            coordinates=coordinates,
            photograph_path=data.get("photograph_path"),
            additional_data=data.get("additional_data", {}),
            mantras_dedicated=data.get("mantras_dedicated", 0),
            prayer_wheel_rotations=data.get("prayer_wheel_rotations", 0),
            dedication_sessions=dedication_sessions,
            intention=data.get("intention", "Complete liberation from suffering"),
            priority=data.get("priority", 5),
        )


class BlessingDatabase:
    """SQLite-backed database for blessing targets, sessions, and dedications.

    Manages three tables:
    - ``blessing_targets`` — individuals/groups receiving blessings.
    - ``blessing_sessions`` — recorded practice sessions.
    - ``mantra_dedications`` — per-target dedication counts linked to sessions.

    All JSON-serialisable fields (coordinates, additional data, dedication
    sessions) are stored as TEXT columns. Thread-safe for single-writer usage;
    not designed for concurrent access.

    Attributes:
        db_path: Path to the SQLite file (default ``"vajra_stream.db"``).
    """

    def __init__(self, db_path: str = "vajra_stream.db"):
        """Initialize database."""
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Ensure the schema is present.

        All three tables (``blessing_targets``, ``blessing_sessions``,
        ``mantra_dedications``) are owned by the centralized migration
        runner in :mod:`core.schema`. We delegate here so there is
        exactly one place that creates them, and so re-running this
        constructor is a true no-op.
        """
        from core.schema import init_db as _core_init_db

        _core_init_db()

    def add_target(self, target: BlessingTarget):
        """Add a blessing target to the database."""
        if not target.identifier:
            target.identifier = target.generate_identifier()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO blessing_targets
            (identifier, name, category, description, case_number,
             relevant_date, discovery_date, last_updated,
             coordinates_json, photograph_path, additional_data_json,
             mantras_dedicated, prayer_wheel_rotations,
             dedication_sessions_json, intention, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                target.identifier,
                target.name,
                target.category.value,
                target.description,
                target.case_number,
                target.relevant_date.isoformat() if target.relevant_date else None,
                target.discovery_date.isoformat() if target.discovery_date else None,
                target.last_updated.isoformat(),
                json.dumps(target.coordinates.to_dict()) if target.coordinates else None,
                target.photograph_path,
                json.dumps(target.additional_data),
                target.mantras_dedicated,
                target.prayer_wheel_rotations,
                json.dumps([dt.isoformat() for dt in target.dedication_sessions]),
                target.intention,
                target.priority,
            ),
        )

        conn.commit()
        conn.close()

    def get_target(self, identifier: str) -> BlessingTarget | None:
        """Retrieve a blessing target."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM blessing_targets WHERE identifier = ?
        """,
            (identifier,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_target(row)

    def _row_to_target(self, row: tuple) -> BlessingTarget:
        """Reconstruct a BlessingTarget from a blessing_targets row tuple.
        Single source of truth for column-order mapping — keeps get_target(),
        get_all_targets(), and get_targets_by_category() in sync with the DDL.
        """
        data = {
            "identifier": row[0],
            "name": row[1],
            "category": row[2],
            "description": row[3],
            "case_number": row[4],
            "relevant_date": row[5],
            "discovery_date": row[6],
            "last_updated": row[7],
            "coordinates": json.loads(row[8]) if row[8] else None,
            "photograph_path": row[9],
            "additional_data": json.loads(row[10]) if row[10] else {},
            "mantras_dedicated": row[11],
            "prayer_wheel_rotations": row[12],
            "dedication_sessions": json.loads(row[13]) if row[13] else [],
            "intention": row[14],
            "priority": row[15],
        }
        return BlessingTarget.from_dict(data)

    def get_targets_by_category(self, category: BlessingCategory) -> list[BlessingTarget]:
        """Get all targets in a category — single SELECT, no N+1."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM blessing_targets WHERE category = ?",
            (category.value,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_target(row) for row in rows]

    def get_all_targets(self) -> list[BlessingTarget]:
        """Get all blessing targets — single SELECT, no N+1."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM blessing_targets")
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_target(row) for row in rows]

    def update_blessing_count(self, identifier: str, mantras: int = 0, rotations: int = 0):
        """Increment mantra/rotation counts atomically — single UPDATE, no race."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Append the new dedication timestamp to the JSON array (or start one)
        now_iso = datetime.now().isoformat()
        cursor.execute(
            """
            UPDATE blessing_targets
            SET mantras_dedicated = mantras_dedicated + ?,
                prayer_wheel_rotations = prayer_wheel_rotations + ?,
                dedication_sessions_json = json_insert(
                    COALESCE(dedication_sessions_json, '[]'),
                    '$[#]',
                    ?
                ),
                last_updated = ?
            WHERE identifier = ?
        """,
            (mantras, rotations, now_iso, now_iso, identifier),
        )
        conn.commit()
        conn.close()

    def record_session(
        self,
        mantra_type: str,
        total_mantras: int,
        total_rotations: int,
        targets_blessed: int,
        allocation_method: str,
        notes: str = "",
        astrological_data: dict = None,
    ) -> int:
        """Record a blessing session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO blessing_sessions
            (session_date, mantra_type, total_mantras, total_rotations,
             targets_blessed, allocation_method, notes, astrological_data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now().isoformat(),
                mantra_type,
                total_mantras,
                total_rotations,
                targets_blessed,
                allocation_method,
                notes,
                json.dumps(astrological_data) if astrological_data else None,
            ),
        )

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return session_id

    def record_dedication(
        self,
        target_identifier: str,
        session_id: int,
        mantra_type: str,
        mantras_count: int,
        dedicator: str = "",
        notes: str = "",
    ):
        """Record individual dedication to a target."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO mantra_dedications
            (target_identifier, session_id, mantra_type, mantras_count,
             dedication_date, dedicator, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (target_identifier, session_id, mantra_type, mantras_count, datetime.now().isoformat(), dedicator, notes),
        )

        conn.commit()
        conn.close()

        # Update target counts
        self.update_blessing_count(target_identifier, mantras=mantras_count)

    def get_statistics(self) -> dict:
        """Get overall blessing statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total targets
        cursor.execute("SELECT COUNT(*) FROM blessing_targets")
        total_targets = cursor.fetchone()[0]

        # Targets by category
        cursor.execute("""
            SELECT category, COUNT(*) FROM blessing_targets GROUP BY category
        """)
        by_category = {row[0]: row[1] for row in cursor.fetchall()}

        # Total mantras dedicated
        cursor.execute("SELECT SUM(mantras_dedicated) FROM blessing_targets")
        total_mantras = cursor.fetchone()[0] or 0

        # Total rotations
        cursor.execute("SELECT SUM(prayer_wheel_rotations) FROM blessing_targets")
        total_rotations = cursor.fetchone()[0] or 0

        # Total sessions
        cursor.execute("SELECT COUNT(*) FROM blessing_sessions")
        total_sessions = cursor.fetchone()[0]

        conn.close()

        return {
            "total_targets": total_targets,
            "by_category": by_category,
            "total_mantras_dedicated": total_mantras,
            "total_prayer_wheel_rotations": total_rotations,
            "total_sessions": total_sessions,
        }


class BlessingAllocator:
    """Static methods for distributing mantra/blessing counts across targets.

    Three allocation strategies (all return ``{identifier: count}`` dicts):
    - :meth:`allocate_equitable` — equal shares with remainder distribution.
    - :meth:`allocate_urgent` — weighted by ``days_waiting × priority``.
    - :meth:`allocate_weighted` — proportionally to target priority (1–10).
    """

    @staticmethod
    def allocate_equitable(total_mantras: int, targets: list[BlessingTarget]) -> dict[str, int]:
        """Equal distribution to all targets."""
        if not targets:
            return {}

        mantras_per_target = total_mantras // len(targets)
        remainder = total_mantras % len(targets)

        allocation = {}
        for i, target in enumerate(targets):
            allocation[target.identifier] = mantras_per_target
            # Distribute remainder to first N targets
            if i < remainder:
                allocation[target.identifier] += 1

        return allocation

    @staticmethod
    def allocate_urgent(total_mantras: int, targets: list[BlessingTarget]) -> dict[str, int]:
        """Priority to those waiting longest or with highest urgency."""
        if not targets:
            return {}

        # Calculate urgency score
        now = datetime.now()
        urgency_scores = []

        for target in targets:
            # Days since relevant date (missing, discovered, etc.)
            if target.relevant_date:
                days_waiting = (now - target.relevant_date).days
            else:
                days_waiting = 0

            # Combine with priority
            urgency = days_waiting * target.priority
            urgency_scores.append((target.identifier, urgency))

        # Sort by urgency (highest first)
        urgency_scores.sort(key=lambda x: x[1], reverse=True)

        # Allocate proportionally to urgency
        total_urgency = sum(score for _, score in urgency_scores)

        allocation = {}
        allocated = 0

        for identifier, urgency in urgency_scores:
            if total_urgency > 0:
                portion = (urgency / total_urgency) * total_mantras
                mantras = int(portion)
            else:
                mantras = total_mantras // len(targets)

            allocation[identifier] = mantras
            allocated += mantras

        # Distribute any remainder to highest urgency
        remainder = total_mantras - allocated
        if remainder > 0 and urgency_scores:
            allocation[urgency_scores[0][0]] += remainder

        return allocation

    @staticmethod
    def allocate_weighted(total_mantras: int, targets: list[BlessingTarget]) -> dict[str, int]:
        """Weighted by priority scores."""
        if not targets:
            return {}

        # Sum of all priorities
        total_priority = sum(target.priority for target in targets)

        allocation = {}
        allocated = 0

        for target in targets:
            if total_priority > 0:
                portion = (target.priority / total_priority) * total_mantras
                mantras = int(portion)
            else:
                mantras = total_mantras // len(targets)

            allocation[target.identifier] = mantras
            allocated += mantras

        # Distribute remainder to highest priority
        remainder = total_mantras - allocated
        if remainder > 0:
            highest_priority = max(targets, key=lambda t: t.priority)
            allocation[highest_priority.identifier] += remainder

        return allocation


# Convenience functions
def create_target(
    name: str,
    category: BlessingCategory,
    location: tuple[float, float] | None = None,
    date: datetime | None = None,
    description: str = "",
    priority: int = 5,
) -> BlessingTarget:
    """
    Quick function to create a blessing target.

    Args:
        name: Name (or "Unknown")
        category: BlessingCategory
        location: (latitude, longitude) tuple
        date: Relevant date (birth, disappearance, etc.)
        description: Description
        priority: 1-10, 10 highest

    Returns:
        BlessingTarget ready to add to database
    """
    # Create location if provided
    geo_loc = None
    if location:
        geo_loc = GeoCoordinate(latitude=location[0], longitude=location[1])

    # Create coordinates if we have location and/or date
    coords = None
    if geo_loc or date:
        from core.astrocartography import CalendarConverter

        if date:
            jd = CalendarConverter.date_to_julian_day(
                date.year, date.month, date.day, date.hour, date.minute, date.second
            )
        else:
            # Use current time
            now = datetime.now()
            jd = CalendarConverter.date_to_julian_day(now.year, now.month, now.day, now.hour, now.minute, now.second)

        coords = BlessingCoordinate(julian_day=jd, reference_datetime=date, location=geo_loc)

    return BlessingTarget(
        identifier="",  # Will be auto-generated
        name=name,
        category=category,
        description=description,
        relevant_date=date,
        coordinates=coords,
        priority=priority,
    )


if __name__ == "__main__":
    # Demo
    print("=" * 70)
    print("COMPASSIONATE BLESSING SYSTEM")
    print("=" * 70)

    # Initialize database
    db = BlessingDatabase()

    # Create some example targets
    print("\n1. CREATING BLESSING TARGETS")
    print("-" * 70)

    # Missing person
    target1 = create_target(
        name="Unknown - Case #12345",
        category=BlessingCategory.MISSING_PERSON,
        location=(40.7128, -74.0060),  # NYC
        date=datetime(2020, 6, 15, 14, 30),
        description="Missing since June 2020",
        priority=8,
    )
    db.add_target(target1)
    print(f"Added: {target1.name} ({target1.category.value})")

    # Shelter animal
    target2 = create_target(
        name="Max - Dog #A789",
        category=BlessingCategory.SHELTER_ANIMAL,
        location=(34.0522, -118.2437),  # LA
        date=datetime(2024, 12, 1),
        description="Awaiting adoption",
        priority=6,
    )
    db.add_target(target2)
    print(f"Added: {target2.name} ({target2.category.value})")

    # All sentient beings (universal)
    target3 = create_target(
        name="All Sentient Beings",
        category=BlessingCategory.ALL_SENTIENT_BEINGS,
        description="Universal compassion for all",
        priority=10,
    )
    db.add_target(target3)
    print(f"Added: {target3.name} ({target3.category.value})")

    # Get statistics
    print("\n2. DATABASE STATISTICS")
    print("-" * 70)

    stats = db.get_statistics()
    print(f"Total targets: {stats['total_targets']}")
    print("By category:")
    for cat, count in stats["by_category"].items():
        print(f"  {cat}: {count}")

    # Allocate mantras
    print("\n3. BLESSING ALLOCATION")
    print("-" * 70)

    all_targets = db.get_all_targets()
    total_mantras = 10000  # e.g., recited 10,000 Om Mani Padme Hum

    print(f"Allocating {total_mantras} mantras...")

    # Try different allocation methods
    print("\nEquitable allocation:")
    equitable = BlessingAllocator.allocate_equitable(total_mantras, all_targets)
    for target_id, count in equitable.items():
        target = db.get_target(target_id)
        print(f"  {target.name}: {count} mantras")

    print("\nUrgent allocation (priority to longest waiting):")
    urgent = BlessingAllocator.allocate_urgent(total_mantras, all_targets)
    for target_id, count in urgent.items():
        target = db.get_target(target_id)
        print(f"  {target.name}: {count} mantras")

    print("\nWeighted allocation (by priority):")
    weighted = BlessingAllocator.allocate_weighted(total_mantras, all_targets)
    for target_id, count in weighted.items():
        target = db.get_target(target_id)
        print(f"  {target.name}: {count} mantras")

    # Record a session
    print("\n4. RECORDING BLESSING SESSION")
    print("-" * 70)

    session_id = db.record_session(
        mantra_type="om_mani_padme_hum",
        total_mantras=total_mantras,
        total_rotations=0,
        targets_blessed=len(all_targets),
        allocation_method="equitable",
        notes="Daily practice dedication",
    )

    print(f"Session recorded (ID: {session_id})")

    # Update targets with allocated mantras
    for target_id, count in equitable.items():
        db.record_dedication(
            target_identifier=target_id,
            session_id=session_id,
            mantra_type="om_mani_padme_hum",
            mantras_count=count,
            dedicator="Practitioner",
        )

    # Final statistics
    print("\n5. UPDATED STATISTICS")
    print("-" * 70)

    stats = db.get_statistics()
    print(f"Total mantras dedicated: {stats['total_mantras_dedicated']}")
    print(f"Total sessions: {stats['total_sessions']}")

    print("\n" + "=" * 70)
    print("May all merit from this practice benefit all beings.")
    print("May they be free from suffering and the causes of suffering.")
    print("=" * 70)
