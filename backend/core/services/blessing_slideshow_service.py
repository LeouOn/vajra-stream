"""
Compassionate Blessing Slideshow Service

Automatically cycles through photographs with overlaid mantras and positive
intentions for rapid blessing transmission to unknown beings.

Inspired by:
- Prayer wheel rapid repetition
- Radionics witness sample principle
- Subliminal positive messaging
- Ken Ogger's systematic compassion techniques
- Tibetan Buddhist dedication practices
"""

import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import hashlib
import secrets


class IntentionType(str, Enum):
    """Types of positive intentions"""
    LOVE = "love"
    HEALING = "healing"
    PEACE = "peace"
    PROTECTION = "protection"
    REUNION = "reunion"
    IDENTIFICATION = "identification"
    LIBERATION = "liberation"
    WISDOM = "wisdom"
    COMPASSION = "compassion"
    SAFETY = "safety"
    COMFORT = "comfort"
    BLESSING = "blessing"


class MantraType(str, Enum):
    """Sacred mantras for overlaying"""
    CHENREZIG = "chenrezig"  # Om Mani Padme Hum
    MEDICINE_BUDDHA = "medicine_buddha"  # Tayata Om...
    TARA = "tara"  # Om Tare Tuttare Ture Soha
    VAJRASATTVA = "vajrasattva"  # Om Vajrasattva Hum
    AMITABHA = "amitabha"  # Om Ami Dewa Hrih
    MANJUSHRI = "manjushri"  # Om Ah Ra Pa Tsa Na Dhih
    METTA = "metta"  # Loving-kindness phrases
    CUSTOM = "custom"


# Mantra text definitions
MANTRA_TEXTS = {
    MantraType.CHENREZIG: "ॐ मणि पद्मे हूँ | OM MANI PADME HUM",
    MantraType.MEDICINE_BUDDHA: "तयता ॐ भैषज्ये भैषज्ये महाभैषज्ये राज समुद्गते स्वाहा",
    MantraType.TARA: "ॐ तारे तुत्तारे तुरे स्वाहा | OM TARE TUTTARE TURE SOHA",
    MantraType.VAJRASATTVA: "ॐ वज्रसत्व हूँ | OM VAJRASATTVA HUM",
    MantraType.AMITABHA: "ॐ अमि देव ह्रीः | OM AMI DEWA HRIH",
    MantraType.MANJUSHRI: "ॐ आः र प च न धीः | OM AH RA PA TSA NA DHIH",
    MantraType.METTA: "May you be happy. May you be safe. May you be peaceful. May you be loved.",
}


@dataclass
class IntentionSet:
    """Set of intentions to overlay on images"""
    primary_mantra: MantraType
    custom_mantra: Optional[str] = None
    intentions: List[IntentionType] = field(default_factory=list)
    dedication: str = "May all beings benefit"
    repetitions_per_photo: int = 108  # Traditional Buddhist number

    def get_mantra_text(self) -> str:
        """Get the actual mantra text"""
        if self.primary_mantra == MantraType.CUSTOM and self.custom_mantra:
            return self.custom_mantra
        return MANTRA_TEXTS.get(self.primary_mantra, "")

    def get_intentions_text(self) -> List[str]:
        """Get intention phrases"""
        intention_phrases = {
            IntentionType.LOVE: "May you be surrounded by love",
            IntentionType.HEALING: "May you be healed and whole",
            IntentionType.PEACE: "May you find peace",
            IntentionType.PROTECTION: "May you be protected from all harm",
            IntentionType.REUNION: "May you be reunited with your loved ones",
            IntentionType.IDENTIFICATION: "May you be known and recognized",
            IntentionType.LIBERATION: "May you be free from all suffering",
            IntentionType.WISDOM: "May you have clarity and wisdom",
            IntentionType.COMPASSION: "May you receive compassion",
            IntentionType.SAFETY: "May you be safe and secure",
            IntentionType.COMFORT: "May you find comfort and rest",
            IntentionType.BLESSING: "May you be blessed",
        }
        return [intention_phrases[i] for i in self.intentions]


@dataclass
class PhotoRecord:
    """Record of a photo in the slideshow"""
    file_path: str
    filename: str
    file_hash: str
    added_time: float
    times_blessed: int = 0
    total_mantra_repetitions: int = 0
    last_blessed_time: Optional[float] = None


@dataclass
class SlideshowStats:
    """Statistics for a slideshow session"""
    total_photos: int = 0
    photos_blessed: int = 0
    total_blessings_sent: int = 0
    total_mantras_repeated: int = 0
    session_duration: float = 0.0
    average_time_per_photo: float = 0.0
    intentions_used: List[str] = field(default_factory=list)
    mantra_used: str = ""


@dataclass
class SlideshowSession:
    """Active slideshow session"""
    session_id: str
    directory_path: str
    intention_set: IntentionSet
    photos: List[PhotoRecord]
    current_index: int = 0
    is_active: bool = True
    start_time: float = field(default_factory=time.time)
    pause_time: Optional[float] = None
    stats: SlideshowStats = field(default_factory=SlideshowStats)
    loop_mode: bool = True
    display_duration_ms: int = 2000  # Time to display each photo
    rng_session_id: Optional[str] = None  # Link to RNG monitoring

    def get_current_photo(self) -> Optional[PhotoRecord]:
        """Get current photo"""
        if 0 <= self.current_index < len(self.photos):
            return self.photos[self.current_index]
        return None

    def advance(self) -> bool:
        """Advance to next photo. Returns True if advanced, False if at end"""
        if not self.photos:
            return False

        self.current_index += 1

        # Check if we've reached the end
        if self.current_index >= len(self.photos):
            if self.loop_mode:
                self.current_index = 0  # Loop back
                return True
            else:
                self.is_active = False  # End session
                return False

        return True

    def record_blessing(self, photo: PhotoRecord):
        """Record that a photo has been blessed"""
        photo.times_blessed += 1
        photo.total_mantra_repetitions += self.intention_set.repetitions_per_photo
        photo.last_blessed_time = time.time()

        self.stats.photos_blessed += 1
        self.stats.total_blessings_sent += 1
        self.stats.total_mantras_repeated += self.intention_set.repetitions_per_photo


class BlessingSlideshowService:
    """
    Service for managing blessing slideshows

    This system cycles through photographs of beings who need blessings,
    overlaying mantras and positive intentions in rapid succession,
    similar to a high-speed prayer wheel for visual witness samples.
    """

    SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    def __init__(self):
        self.sessions: Dict[str, SlideshowSession] = {}
        self.photo_cache: Dict[str, Set[str]] = {}  # directory -> set of file hashes

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of file for deduplication"""
        try:
            with open(file_path, 'rb') as f:
                # Read first 8KB for speed
                data = f.read(8192)
                return hashlib.md5(data).hexdigest()
        except Exception:
            # Fallback to filename-based hash
            return hashlib.md5(file_path.encode()).hexdigest()

    def scan_directory(
        self,
        directory_path: str,
        recursive: bool = False,
        deduplicate: bool = True
    ) -> List[PhotoRecord]:
        """
        Scan directory for image files

        Args:
            directory_path: Path to directory containing photos
            recursive: Whether to scan subdirectories
            deduplicate: Whether to skip duplicate files (by hash)

        Returns:
            List of PhotoRecord objects
        """
        photos = []
        seen_hashes = set()

        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Directory does not exist: {directory_path}")

        # Choose scanning method
        if recursive:
            files = path.rglob('*')
        else:
            files = path.glob('*')

        for file_path in files:
            # Skip if not a file
            if not file_path.is_file():
                continue

            # Check if image file
            if file_path.suffix.lower() not in self.SUPPORTED_IMAGE_EXTENSIONS:
                continue

            # Calculate hash
            file_hash = self._calculate_file_hash(str(file_path))

            # Skip if duplicate
            if deduplicate and file_hash in seen_hashes:
                continue

            seen_hashes.add(file_hash)

            # Create record
            photo = PhotoRecord(
                file_path=str(file_path),
                filename=file_path.name,
                file_hash=file_hash,
                added_time=time.time()
            )
            photos.append(photo)

        # Cache the hashes for this directory
        self.photo_cache[directory_path] = seen_hashes

        return photos

    def create_session(
        self,
        directory_path: str,
        intention_set: IntentionSet,
        session_id: Optional[str] = None,
        loop_mode: bool = True,
        display_duration_ms: int = 2000,
        recursive: bool = False,
        rng_session_id: Optional[str] = None
    ) -> str:
        """
        Create a new blessing slideshow session

        Args:
            directory_path: Path to directory with photos
            intention_set: Set of mantras and intentions to use
            session_id: Optional custom session ID
            loop_mode: Whether to loop back to start when reaching end
            display_duration_ms: How long to display each photo (ms)
            recursive: Scan subdirectories
            rng_session_id: Optional RNG session for monitoring

        Returns:
            Session ID
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = f"blessing_slideshow_{int(time.time())}_{secrets.token_hex(4)}"

        # Scan directory for photos
        photos = self.scan_directory(directory_path, recursive=recursive)

        if not photos:
            raise ValueError(f"No photos found in directory: {directory_path}")

        # Initialize stats
        stats = SlideshowStats(
            total_photos=len(photos),
            intentions_used=[i.value for i in intention_set.intentions],
            mantra_used=intention_set.primary_mantra.value
        )

        # Create session
        session = SlideshowSession(
            session_id=session_id,
            directory_path=directory_path,
            intention_set=intention_set,
            photos=photos,
            stats=stats,
            loop_mode=loop_mode,
            display_duration_ms=display_duration_ms,
            rng_session_id=rng_session_id
        )

        self.sessions[session_id] = session

        return session_id

    def get_current_slide(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current slide information

        Returns:
            Dict with photo info, mantra, intentions, and overlay data
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return None

        photo = session.get_current_photo()
        if not photo:
            return None

        # Build overlay data
        overlay_data = {
            "mantra_text": session.intention_set.get_mantra_text(),
            "mantra_repetitions": session.intention_set.repetitions_per_photo,
            "intentions": session.intention_set.get_intentions_text(),
            "dedication": session.intention_set.dedication,
            "display_duration_ms": session.display_duration_ms
        }

        return {
            "photo": {
                "file_path": photo.file_path,
                "filename": photo.filename,
                "times_blessed": photo.times_blessed,
                "total_mantra_repetitions": photo.total_mantra_repetitions,
                "last_blessed_time": photo.last_blessed_time
            },
            "session": {
                "session_id": session.session_id,
                "current_index": session.current_index,
                "total_photos": len(session.photos),
                "is_active": session.is_active,
                "loop_mode": session.loop_mode,
                "rng_session_id": session.rng_session_id
            },
            "overlay": overlay_data,
            "progress": {
                "current": session.current_index + 1,
                "total": len(session.photos),
                "percentage": ((session.current_index + 1) / len(session.photos)) * 100 if session.photos else 0
            }
        }

    def advance_slide(self, session_id: str, record_blessing: bool = True) -> bool:
        """
        Advance to next slide

        Args:
            session_id: Session to advance
            record_blessing: Whether to record blessing for current photo

        Returns:
            True if advanced successfully, False if session ended
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return False

        # Record blessing for current photo
        if record_blessing:
            photo = session.get_current_photo()
            if photo:
                session.record_blessing(photo)

        # Advance to next
        return session.advance()

    def pause_session(self, session_id: str) -> bool:
        """Pause a session"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.pause_time = time.time()
        return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused session"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        if session.pause_time:
            # Add paused duration to start time (to not count pause time)
            pause_duration = time.time() - session.pause_time
            session.start_time += pause_duration
            session.pause_time = None

        return True

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """
        Stop a session and return final statistics

        Returns:
            Final session statistics
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}

        session.is_active = False

        # Calculate final stats
        session.stats.session_duration = time.time() - session.start_time
        if session.stats.photos_blessed > 0:
            session.stats.average_time_per_photo = (
                session.stats.session_duration / session.stats.photos_blessed
            )

        return self.get_session_stats(session_id)

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get current session statistics"""
        session = self.sessions.get(session_id)
        if not session:
            return {}

        current_duration = time.time() - session.start_time

        return {
            "session_id": session.session_id,
            "directory": session.directory_path,
            "is_active": session.is_active,
            "total_photos": session.stats.total_photos,
            "photos_blessed": session.stats.photos_blessed,
            "total_blessings_sent": session.stats.total_blessings_sent,
            "total_mantras_repeated": session.stats.total_mantras_repeated,
            "session_duration": current_duration,
            "average_time_per_photo": (
                current_duration / session.stats.photos_blessed
                if session.stats.photos_blessed > 0 else 0
            ),
            "intentions_used": session.stats.intentions_used,
            "mantra_used": session.stats.mantra_used,
            "current_progress": {
                "current_index": session.current_index,
                "current_photo": session.current_index + 1,
                "total_photos": len(session.photos),
                "percentage": ((session.current_index + 1) / len(session.photos)) * 100 if session.photos else 0
            },
            "rng_session_id": session.rng_session_id
        }

    def get_all_sessions(self) -> List[str]:
        """Get list of all session IDs"""
        return list(self.sessions.keys())

    def get_photo_list(self, session_id: str) -> List[Dict[str, Any]]:
        """Get list of all photos in session with their blessing counts"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        return [
            {
                "filename": photo.filename,
                "file_path": photo.file_path,
                "times_blessed": photo.times_blessed,
                "total_mantra_repetitions": photo.total_mantra_repetitions,
                "last_blessed_time": photo.last_blessed_time
            }
            for photo in session.photos
        ]

    def jump_to_photo(self, session_id: str, index: int) -> bool:
        """Jump to specific photo index"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        if 0 <= index < len(session.photos):
            session.current_index = index
            return True

        return False


# Global service instance
_blessing_slideshow_service: Optional[BlessingSlideshowService] = None


def get_blessing_slideshow_service() -> BlessingSlideshowService:
    """Get or create global blessing slideshow service"""
    global _blessing_slideshow_service
    if _blessing_slideshow_service is None:
        _blessing_slideshow_service = BlessingSlideshowService()
    return _blessing_slideshow_service
