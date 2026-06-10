"""
Auspicious Timing Engine
Provides "green window" detection for ritual workflows using planetary hours,
tithi, nakshatra, and planetary transits from the existing AstrologyEngine.

The core concept: each ritual genre (healing, victory, wisdom, etc.) has
favorable and unfavorable planetary conditions. The engine checks current
conditions and returns a go/no-go signal with timing recommendations.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# ─── Genre ↔ Planetary Correspondences ───────────────────────

GENRE_PLANETARY_HOURS = {
    "healing": {
        "favorable": ["Jupiter", "Venus", "Moon", "Sun"],
        "neutral": ["Mercury"],
        "unfavorable": ["Saturn", "Mars"],
        "best_tithi": ["Shukla Panchami", "Shukla Dashami", "Shukla Ekadashi"],
        "avoid_tithi": ["Krishna Chaturdashi", "Amavasya"],
    },
    "victory": {
        "favorable": ["Mars", "Sun", "Jupiter"],
        "neutral": ["Mercury", "Venus"],
        "unfavorable": ["Saturn", "Moon"],
    },
    "wisdom": {
        "favorable": ["Mercury", "Jupiter", "Moon"],
        "neutral": ["Venus", "Sun"],
        "unfavorable": ["Mars", "Saturn"],
    },
    "purification": {
        "favorable": ["Saturn", "Mars", "Moon"],
        "neutral": ["Mercury", "Jupiter"],
        "unfavorable": ["Venus", "Sun"],
    },
    "compassion": {
        "favorable": ["Moon", "Venus", "Jupiter"],
        "neutral": ["Mercury", "Sun"],
        "unfavorable": ["Mars", "Saturn"],
    },
    "prosperity": {
        "favorable": ["Venus", "Jupiter", "Mercury"],
        "neutral": ["Sun", "Moon"],
        "unfavorable": ["Saturn", "Mars"],
    },
    "protection": {
        "favorable": ["Mars", "Saturn", "Sun"],
        "neutral": ["Jupiter", "Mercury"],
        "unfavorable": ["Moon", "Venus"],
    },
    "creativity": {
        "favorable": ["Venus", "Moon", "Mercury"],
        "neutral": ["Jupiter", "Sun"],
        "unfavorable": ["Saturn", "Mars"],
    },
}

# Nakshatra qualities relevant to ritual work
NAKSHATRA_QUALITIES = {
    "Ashwini": "swift action, healing, new beginnings",
    "Bharani": "transformation, letting go, intensity",
    "Krittika": "purification, cutting through, fire",
    "Rohini": "growth, nurturing, abundance, creativity",
    "Mrigashira": "searching, curiosity, gentle pursuit",
    "Ardra": "storm, destruction of old, emotional release",
    "Punarvasu": "return, renewal, second chances",
    "Pushya": "nourishment, wisdom, auspicious for all",
    "Ashlesha": "depth, secrets, kundalini, transformation",
    "Magha": "ancestors, power, authority, legacy",
    "Purva Phalguni": "pleasure, creativity, relaxation",
    "Uttara Phalguni": "contracts, commitment, patronage, structure",
    "Hasta": "skill, craftsmanship, precision, healing hands",
    "Chitra": "beauty, architecture, divine design",
    "Swati": "independence, transformation, wind",
    "Vishakha": "determination, breakthrough, dual purpose",
    "Anuradha": "devotion, friendship, persistence",
    "Jyeshtha": "seniority, protection, occult power",
    "Mula": "roots, destruction of illusion, deep investigation",
    "Purva Ashadha": "invigoration, victory, early success",
    "Uttara Ashadha": "complete victory, lasting achievement",
    "Shravana": "listening, learning, wisdom transmission",
    "Dhanishta": "wealth, rhythm, music, synchronization",
    "Shatabhisha": "healing, hundreds of medicines, concealment",
    "Purva Bhadrapada": "transformation through fire, sacrifice",
    "Uttara Bhadrapada": "depth, ocean, final dissolution",
    "Revati": "nourishment, safe passage, completion",
}


@dataclass
class TimingWindow:
    """Result of a timing assessment — always permissive, never blocks."""
    go: bool = True  # Always true — rituals can always proceed
    planetary_hour: str = ""
    tithi: str = ""
    nakshatra: str = ""
    quality: str = ""  # "excellent", "good", "challenging", "transmutative"
    message: str = ""
    transmutation: str = ""  # How to work with challenging conditions
    transmutation_mantra: str = ""  # Specific mantra for transmutation
    wait_minutes: int = 0
    next_favorable_hour: str = ""  # For time-shifted scheduling
    time_shift_available: bool = False  # Can schedule broadcast for favorable window
    recommended_approach: str = ""  # "direct", "transmute_first", "time_shift", "non_linear"
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "go": self.go,
            "planetary_hour": self.planetary_hour,
            "tithi": self.tithi,
            "nakshatra": self.nakshatra,
            "quality": self.quality,
            "message": self.message,
            "transmutation": self.transmutation,
            "transmutation_mantra": self.transmutation_mantra,
            "wait_minutes": self.wait_minutes,
            "next_favorable_hour": self.next_favorable_hour,
            "time_shift_available": self.time_shift_available,
            "recommended_approach": self.recommended_approach,
        }


class AuspiciousTiming:
    """
    Checks planetary conditions against ritual genres.

    Usage:
        timing = AuspiciousTiming()
        window = timing.check("healing")
        if window.go:
            sequencer.start(...)
        else:
            print(f"Wait {window.wait_minutes}min for {window.next_favorable_hour}")
    """

    # Chaldean order of planetary hours
    CHALDEAN_ORDER = [
        "Saturn", "Jupiter", "Mars", "Sun",
        "Venus", "Mercury", "Moon",
    ]

    def __init__(self, astrology_engine=None):
        self._engine = astrology_engine

    @property
    def engine(self):
        if self._engine is None:
            try:
                from core.astrology import AstrologicalCalculator
                self._engine = AstrologicalCalculator()
            except ImportError:
                self._engine = None
        return self._engine

    def check(self, genre: str = "healing") -> TimingWindow:
        """
        Assess current conditions for a ritual genre — ALWAYS permissive.

        Never blocks. Instead provides:
        - Quality rating (excellent/good/challenging/transmutative)
        - Transmutation guidance for challenging conditions
        - Time-shift option for scheduling at the favorable window
        - Non-linear visualization approach

        The ritual can always proceed. The question is HOW, not IF.
        """
        hour = self._get_planetary_hour()
        tithi = self._get_tithi()
        nakshatra = self._get_nakshatra()
        config = GENRE_PLANETARY_HOURS.get(genre, GENRE_PLANETARY_HOURS["healing"])
        nakshatra_quality = NAKSHATRA_QUALITIES.get(nakshatra, "")

        # ─── Assess conditions (never block) ───
        if hour in config["favorable"]:
            hour_rating = "favorable"
        elif hour in config["neutral"]:
            hour_rating = "neutral"
        else:
            hour_rating = "challenging"

        tithi_blocked = "avoid_tithi" in config and tithi in config["avoid_tithi"]
        tithi_excellent = "best_tithi" in config and tithi in config["best_tithi"]

        # ─── Determine quality and approach ───
        if hour_rating == "favorable" and tithi_excellent:
            quality = "excellent"
            approach = "direct"
            transmutation = ""
            mantra = ""
        elif hour_rating == "favorable":
            quality = "good"
            approach = "direct"
            transmutation = ""
            mantra = ""
        elif hour_rating == "challenging" and tithi_blocked:
            quality = "transmutative"
            approach = "transmute_first"
            transmutation, mantra = self._get_transmutation(genre, hour)
        elif hour_rating == "challenging":
            quality = "challenging"
            approach = "transmute_first"
            transmutation, mantra = self._get_transmutation(genre, hour)
        elif tithi_blocked:
            quality = "transmutative"
            approach = "non_linear"
            transmutation = f"Tithi {tithi} challenges {genre} work. Visualize the ritual occurring at the next {config.get('best_tithi', ['favorable tithi'])[0]}."
            mantra = "Gate Gate Paragate Parasamgate Bodhi Svaha"
        else:
            quality = "good"
            approach = "direct"
            transmutation = ""
            mantra = ""

        # ─── Calculate time-shift option ───
        wait, next_fav = self._find_next_favorable(config["favorable"])
        time_shift = wait > 0

        # ─── Compose message ───
        if quality == "excellent":
            message = (
                f"PERFECT TIMING — {hour} hour + {tithi} creates an excellent window for {genre}. "
                f"Nakshatra {nakshatra} ({nakshatra_quality}). Proceed directly."
            )
        elif quality == "good":
            message = (
                f"FAVORABLE — {hour} hour is good for {genre}. "
                f"Tithi: {tithi}. Nakshatra: {nakshatra}. Proceed with confidence."
            )
        elif quality == "challenging":
            message = (
                f"CHALLENGING — {hour} hour is not ideal for {genre}, but workable. "
                f"{transmutation}. Tithi: {tithi}. Nakshatra: {nakshatra}."
            )
        else:
            message = (
                f"TRANSMUTATIVE — {hour} hour + {tithi} create resistance for {genre}. "
                f"{transmutation}. Time-shift available: {next_fav} hour in ~{wait}min."
            )

        return TimingWindow(
            go=True,  # Always
            planetary_hour=hour,
            tithi=tithi,
            nakshatra=nakshatra,
            quality=quality,
            message=message,
            transmutation=transmutation,
            transmutation_mantra=mantra,
            wait_minutes=wait,
            next_favorable_hour=next_fav,
            time_shift_available=time_shift,
            recommended_approach=approach,
        )

    def get_current_conditions(self) -> dict[str, Any]:
        """Get all current timing conditions for display."""
        return {
            "planetary_hour": self._get_planetary_hour(),
            "tithi": self._get_tithi(),
            "nakshatra": self._get_nakshatra(),
            "nakshatra_quality": NAKSHATRA_QUALITIES.get(self._get_nakshatra(), ""),
            "moon_phase": self._get_moon_phase(),
        }

    def get_all_genre_windows(self) -> dict[str, dict[str, Any]]:
        """Check timing for all known genres."""
        return {
            genre: self.check(genre).to_dict()
            for genre in GENRE_PLANETARY_HOURS
        }

    # ─── Internal calculations ─────────────────────────────────

    def _get_planetary_hour(self) -> str:
        """Get current planetary hour ruler."""
        now = datetime.now()
        # Simplified: use the day-of-week + hour calculation
        # Full calculation needs sunrise time, but this is good enough for ritual work
        weekday = now.weekday()  # 0=Mon, 6=Sun
        hour_index = (now.hour + (weekday * 2)) % 7
        return self.CHALDEAN_ORDER[hour_index]

    def _get_tithi(self) -> str:
        """Get current tithi from astrology engine or fallback."""
        if self.engine:
            try:
                moon = self.engine.get_moon_phase(datetime.now())
                if moon:
                    age_days = moon.get("phase_angle", 0) / 360 * 29.53
                    tithi_index = int(age_days % 30)
                    tithi_names = [
                        "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya",
                        "Shukla Chaturthi", "Shukla Panchami", "Shukla Shashthi",
                        "Shukla Saptami", "Shukla Ashtami", "Shukla Navami",
                        "Shukla Dashami", "Shukla Ekadashi", "Shukla Dwadashi",
                        "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
                        "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya",
                        "Krishna Chaturthi", "Krishna Panchami", "Krishna Shashthi",
                        "Krishna Saptami", "Krishna Ashtami", "Krishna Navami",
                        "Krishna Dashami", "Krishna Ekadashi", "Krishna Dwadashi",
                        "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya",
                    ]
                    return tithi_names[tithi_index] if tithi_index < 30 else "Unknown"
            except Exception:
                pass
        return "Unknown"

    def _get_nakshatra(self) -> str:
        """Get current nakshatra from astrology engine or fallback."""
        if self.engine:
            try:
                moon = self.engine.get_moon_phase(datetime.now())
                if moon:
                    nakshatra_index = int((moon.get("phase_angle", 0) / 360 * 27) % 27)
                    nakshatras = list(NAKSHATRA_QUALITIES.keys())
                    return nakshatras[nakshatra_index] if nakshatra_index < 27 else "Unknown"
            except Exception:
                pass
        return "Unknown"

    def _get_moon_phase(self) -> dict[str, Any]:
        """Get moon phase data."""
        if self.engine:
            try:
                return self.engine.get_moon_phase(datetime.now()) or {}
            except Exception:
                pass
        return {}

    def _get_transmutation(self, genre: str, hour: str) -> tuple[str, str]:
        """Get transmutation guidance for a challenging hour-genre combination."""
        TRANSMUTATIONS = {
            ("healing", "Mars"): (
                "Channel Mars' fire through Vajrasattva purification before the healing broadcast. "
                "The intensity becomes surgical precision.",
                "Om Vajrasattva Hum"
            ),
            ("healing", "Saturn"): (
                "Saturn's weight can ground healing energy deeply. Begin with a grounding mantra, "
                "then direct the stabilized energy to the healing target.",
                "Om Shanti Shanti Shanti"
            ),
            ("compassion", "Mars"): (
                "Mars' warrior energy becomes fierce compassion. Visualize the red light of Mars "
                "transforming into Chenrezig's thousand arms reaching out.",
                "Om Mani Padme Hum"
            ),
            ("compassion", "Saturn"): (
                "Saturn's discipline gives compassion structure. Use the heaviness as a foundation "
                "for a compassion that lasts beyond the ritual.",
                "Om Mani Padme Hum"
            ),
            ("wisdom", "Mars"): (
                "Mars' drive becomes the sword of Manjushri — cutting through illusion. "
                "The aggressive energy sharpens discernment.",
                "Om Ah Ra Pa Tsa Na Dhih"
            ),
            ("wisdom", "Saturn"): (
                "Saturn deepens wisdom through patience. This hour favors slow, contemplative "
                "wisdom work rather than sudden insight.",
                "Om Ah Ra Pa Tsa Na Dhih"
            ),
            ("creativity", "Mars"): (
                "Mars brings creative fire. Channel it through rapid ideation and bold expression. "
                "This is the hour of the lightning-strike inspiration.",
                "Om Ah Hum"
            ),
            ("creativity", "Saturn"): (
                "Saturn structures creativity into lasting form. This is the hour for editing, "
                "refining, and giving permanent shape to creative visions.",
                "Om Ah Hum"
            ),
            ("prosperity", "Mars"): (
                "Mars' drive fuels assertive abundance work. Focus on taking bold action toward "
                "prosperity rather than passive attraction.",
                "Om Shrim Klim Mahalakshmyai Namaha"
            ),
            ("prosperity", "Saturn"): (
                "Saturn builds lasting wealth through discipline. This hour favors long-term "
                "prosperity planning and structural abundance.",
                "Om Shrim Klim Mahalakshmyai Namaha"
            ),
            ("protection", "Moon"): (
                "The Moon softens protection — shift from fortress walls to nurturing boundaries. "
                "Visualize a sphere of silver moonlight rather than iron shields.",
                "Om Tare Tuttare Ture Soha"
            ),
            ("protection", "Venus"): (
                "Venus transforms protection into loving guardianship. Call on Tara's compassionate "
                "protection rather than Mars' warlike defense.",
                "Om Tare Tuttare Ture Soha"
            ),
            ("victory", "Saturn"): (
                "Saturn delays victory but makes it decisive. This is the hour of strategic patience "
                "— set the conditions for victory rather than forcing the outcome.",
                "Om Vajra Guru Padma Siddhi Hum"
            ),
            ("victory", "Moon"): (
                "The Moon makes victory fluid — adapt tactics moment by moment. Victory comes "
                "through responsiveness rather than force.",
                "Om Vajra Guru Padma Siddhi Hum"
            ),
            ("purification", "Venus"): (
                "Venus purifies through love and beauty. Use art, music, or devotional practice "
                "as the purification vehicle.",
                "Om Benza Satto Hung"
            ),
            ("purification", "Sun"): (
                "The Sun purifies through illumination — bring what's hidden into the light. "
                "This is the hour of radical transparency.",
                "Om Benza Satto Hung"
            ),
            # ─── Bodhicitta Transmutations (all genres) ───
            ("healing", "Bodhicitta"): (
                "When conditions challenge healing, invoke bodhicitta — the awakened heart. "
                "The pain you feel is the doorway to compassion for all who suffer. "
                "Transform personal healing into universal bodhisattva activity.",
                "Om Mani Padme Hum"
            ),
            ("compassion", "Bodhicitta"): (
                "The difficult hour is the perfect teacher. Each obstacle is a reminder of "
                "why we practice — for the liberation of ALL beings without exception. "
                "Let this resistance deepen your bodhicitta resolve.",
                "Om Mani Padme Hum"
            ),
            ("wisdom", "Bodhicitta"): (
                "The union of wisdom and compassion is the heart of bodhicitta. "
                "Conventional wisdom may be blocked, but the wisdom that sees emptiness "
                "naturally gives rise to boundless love. Rest in that space.",
                "Gate Gate Paragate Parasamgate Bodhi Svaha"
            ),
            ("creativity", "Bodhicitta"): (
                "The creative block is the birthplace of bodhicitta. "
                "When the small self can't create, the vast bodhisattva heart creates for all. "
                "Let your creativity become an offering to every being.",
                "Om Ah Hum Vajra Guru Padma Siddhi Hum"
            ),
            ("prosperity", "Bodhicitta"): (
                "True prosperity is the wealth of bodhicitta — inexhaustible and shared with all. "
                "When material channels feel blocked, generate the wealth of the awakened heart. "
                "All abundance flows from the wish to benefit others.",
                "Om Dzambhala Dzalentraye Svaha"
            ),
            ("protection", "Bodhicitta"): (
                "The ultimate protection is bodhicitta — the diamond armor of compassion. "
                "No force can harm one whose sole purpose is the benefit of all beings. "
                "Wrap yourself in the intention of bodhicitta.",
                "Om Tare Tuttare Ture Soha"
            ),
            ("victory", "Bodhicitta"): (
                "The bodhisattva's victory is not conquest but liberation. "
                "When resistance is strong, remember: the true enemy is self-cherishing. "
                "Victory comes through surrendering the self to the service of all.",
                "Om Vajrasattva Hum"
            ),
        }

        key = (genre, hour)
        if key in TRANSMUTATIONS:
            return TRANSMUTATIONS[key]

        # Generic transmutation for any unmatched combination
        return (
            f"{hour} hour challenges {genre} work. Begin with a brief purification or grounding "
            f"practice to transmute the energy before proceeding with the main ritual.",
            "Om Ah Hum"
        )

    def _find_next_favorable(self, favorable_hours: list[str]) -> tuple[int, str]:
        """Find minutes until the next favorable planetary hour."""
        now = datetime.now()
        current_idx = (now.hour + now.weekday() * 2) % 7
        current_planet = self.CHALDEAN_ORDER[current_idx]

        # Search forward through the Chaldean cycle
        for offset in range(1, 25):  # Check up to 24 hours ahead
            future_idx = (current_idx + offset) % 7
            planet = self.CHALDEAN_ORDER[future_idx]
            if planet in favorable_hours:
                minutes = offset * 60  # Rough: each planet rules ~1 hour
                # More precise: calculate actual minutes to that hour
                target_hour = (now.hour + offset) % 24
                current_minutes = now.minute
                minutes = offset * 60 - current_minutes
                if minutes < 1:
                    minutes = 5  # Minimum wait
                return minutes, planet

        return 60, favorable_hours[0]  # Fallback


# Convenience
_timing_instance: AuspiciousTiming | None = None


def check_auspicious_window(genre: str = "healing") -> TimingWindow:
    """Quick check: is now a good time for this ritual genre?"""
    global _timing_instance
    if _timing_instance is None:
        _timing_instance = AuspiciousTiming()
    return _timing_instance.check(genre)


def get_all_windows() -> dict[str, dict[str, Any]]:
    """Get timing windows for all genres."""
    global _timing_instance
    if _timing_instance is None:
        _timing_instance = AuspiciousTiming()
    return _timing_instance.get_all_genre_windows()


def check_saka_dawa(target_date: datetime = None) -> dict[str, Any]:
    """
    Check if a given date falls within the Saka Dawa month (4th Tibetan lunar month).
    We use the Chinese lunar calendar via lunar_python as a close proxy for the 
    Tibetan lunar calendar. The 15th day (full moon) is Saka Dawa Duchen.
    """
    try:
        from lunar_python import Lunar, Solar
    except ImportError:
        # Fallback if library missing
        return {
            "is_saka_dawa": False,
            "multiplier": 1,
            "current_date": target_date.isoformat() if target_date else datetime.now().isoformat(),
            "error": "lunar_python not installed"
        }
    
    dt = target_date or datetime.now()
    solar = Solar.fromYmd(dt.year, dt.month, dt.day)
    lunar = Lunar.fromSolar(solar)
    
    lunar_month = lunar.getMonth()
    lunar_day = lunar.getDay()
    
    # 4th Lunar month is Saga Dawa
    # Month > 0 handles leap months in lunar calendar logic
    is_saka_dawa = (abs(lunar_month) == 4)
    is_duchen = is_saka_dawa and (lunar_day == 15)
    
    # Merit multiplier rules
    multiplier = 1
    if is_duchen:
        multiplier = 100000
    elif is_saka_dawa:
        multiplier = 10000
        
    return {
        "is_saka_dawa": is_saka_dawa,
        "multiplier": multiplier,
        "current_date": dt.isoformat(),
        "is_duchen": is_duchen,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day
    }

