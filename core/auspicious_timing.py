"""
Auspicious Timing Engine
Provides "green window" detection for ritual workflows using planetary hours,
tithi, nakshatra, and planetary transits from the existing AstrologyEngine.

The core concept: each ritual genre (healing, victory, wisdom, etc.) has
favorable and unfavorable planetary conditions. The engine checks current
conditions and returns a go/no-go signal with timing recommendations.
"""

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
        "Saturn",
        "Jupiter",
        "Mars",
        "Sun",
        "Venus",
        "Mercury",
        "Moon",
    ]

    WEEKDAY_RULERS = [
        "Moon",  # Monday
        "Mars",  # Tuesday
        "Mercury",  # Wednesday
        "Jupiter",  # Thursday
        "Venus",  # Friday
        "Saturn",  # Saturday
        "Sun",  # Sunday
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
        return {genre: self.check(genre).to_dict() for genre in GENRE_PLANETARY_HOURS}

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
                        "Shukla Pratipada",
                        "Shukla Dwitiya",
                        "Shukla Tritiya",
                        "Shukla Chaturthi",
                        "Shukla Panchami",
                        "Shukla Shashthi",
                        "Shukla Saptami",
                        "Shukla Ashtami",
                        "Shukla Navami",
                        "Shukla Dashami",
                        "Shukla Ekadashi",
                        "Shukla Dwadashi",
                        "Shukla Trayodashi",
                        "Shukla Chaturdashi",
                        "Purnima",
                        "Krishna Pratipada",
                        "Krishna Dwitiya",
                        "Krishna Tritiya",
                        "Krishna Chaturthi",
                        "Krishna Panchami",
                        "Krishna Shashthi",
                        "Krishna Saptami",
                        "Krishna Ashtami",
                        "Krishna Navami",
                        "Krishna Dashami",
                        "Krishna Ekadashi",
                        "Krishna Dwadashi",
                        "Krishna Trayodashi",
                        "Krishna Chaturdashi",
                        "Amavasya",
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
                "Om Vajrasattva Hum",
            ),
            ("healing", "Saturn"): (
                "Saturn's weight can ground healing energy deeply. Begin with a grounding mantra, "
                "then direct the stabilized energy to the healing target.",
                "Om Shanti Shanti Shanti",
            ),
            ("compassion", "Mars"): (
                "Mars' warrior energy becomes fierce compassion. Visualize the red light of Mars "
                "transforming into Chenrezig's thousand arms reaching out.",
                "Om Mani Padme Hum",
            ),
            ("compassion", "Saturn"): (
                "Saturn's discipline gives compassion structure. Use the heaviness as a foundation "
                "for a compassion that lasts beyond the ritual.",
                "Om Mani Padme Hum",
            ),
            ("wisdom", "Mars"): (
                "Mars' drive becomes the sword of Manjushri — cutting through illusion. "
                "The aggressive energy sharpens discernment.",
                "Om Ah Ra Pa Tsa Na Dhih",
            ),
            ("wisdom", "Saturn"): (
                "Saturn deepens wisdom through patience. This hour favors slow, contemplative "
                "wisdom work rather than sudden insight.",
                "Om Ah Ra Pa Tsa Na Dhih",
            ),
            ("creativity", "Mars"): (
                "Mars brings creative fire. Channel it through rapid ideation and bold expression. "
                "This is the hour of the lightning-strike inspiration.",
                "Om Ah Hum",
            ),
            ("creativity", "Saturn"): (
                "Saturn structures creativity into lasting form. This is the hour for editing, "
                "refining, and giving permanent shape to creative visions.",
                "Om Ah Hum",
            ),
            ("prosperity", "Mars"): (
                "Mars' drive fuels assertive abundance work. Focus on taking bold action toward "
                "prosperity rather than passive attraction.",
                "Om Shrim Klim Mahalakshmyai Namaha",
            ),
            ("prosperity", "Saturn"): (
                "Saturn builds lasting wealth through discipline. This hour favors long-term "
                "prosperity planning and structural abundance.",
                "Om Shrim Klim Mahalakshmyai Namaha",
            ),
            ("protection", "Moon"): (
                "The Moon softens protection — shift from fortress walls to nurturing boundaries. "
                "Visualize a sphere of silver moonlight rather than iron shields.",
                "Om Tare Tuttare Ture Soha",
            ),
            ("protection", "Venus"): (
                "Venus transforms protection into loving guardianship. Call on Tara's compassionate "
                "protection rather than Mars' warlike defense.",
                "Om Tare Tuttare Ture Soha",
            ),
            ("victory", "Saturn"): (
                "Saturn delays victory but makes it decisive. This is the hour of strategic patience "
                "— set the conditions for victory rather than forcing the outcome.",
                "Om Vajra Guru Padma Siddhi Hum",
            ),
            ("victory", "Moon"): (
                "The Moon makes victory fluid — adapt tactics moment by moment. Victory comes "
                "through responsiveness rather than force.",
                "Om Vajra Guru Padma Siddhi Hum",
            ),
            ("purification", "Venus"): (
                "Venus purifies through love and beauty. Use art, music, or devotional practice "
                "as the purification vehicle.",
                "Om Benza Satto Hung",
            ),
            ("purification", "Sun"): (
                "The Sun purifies through illumination — bring what's hidden into the light. "
                "This is the hour of radical transparency.",
                "Om Benza Satto Hung",
            ),
            # ─── Bodhicitta Transmutations (all genres) ───
            ("healing", "Bodhicitta"): (
                "When conditions challenge healing, invoke bodhicitta — the awakened heart. "
                "The pain you feel is the doorway to compassion for all who suffer. "
                "Transform personal healing into universal bodhisattva activity.",
                "Om Mani Padme Hum",
            ),
            ("compassion", "Bodhicitta"): (
                "The difficult hour is the perfect teacher. Each obstacle is a reminder of "
                "why we practice — for the liberation of ALL beings without exception. "
                "Let this resistance deepen your bodhicitta resolve.",
                "Om Mani Padme Hum",
            ),
            ("wisdom", "Bodhicitta"): (
                "The union of wisdom and compassion is the heart of bodhicitta. "
                "Conventional wisdom may be blocked, but the wisdom that sees emptiness "
                "naturally gives rise to boundless love. Rest in that space.",
                "Gate Gate Paragate Parasamgate Bodhi Svaha",
            ),
            ("creativity", "Bodhicitta"): (
                "The creative block is the birthplace of bodhicitta. "
                "When the small self can't create, the vast bodhisattva heart creates for all. "
                "Let your creativity become an offering to every being.",
                "Om Ah Hum Vajra Guru Padma Siddhi Hum",
            ),
            ("prosperity", "Bodhicitta"): (
                "True prosperity is the wealth of bodhicitta — inexhaustible and shared with all. "
                "When material channels feel blocked, generate the wealth of the awakened heart. "
                "All abundance flows from the wish to benefit others.",
                "Om Dzambhala Dzalentraye Svaha",
            ),
            ("protection", "Bodhicitta"): (
                "The ultimate protection is bodhicitta — the diamond armor of compassion. "
                "No force can harm one whose sole purpose is the benefit of all beings. "
                "Wrap yourself in the intention of bodhicitta.",
                "Om Tare Tuttare Ture Soha",
            ),
            ("victory", "Bodhicitta"): (
                "The bodhisattva's victory is not conquest but liberation. "
                "When resistance is strong, remember: the true enemy is self-cherishing. "
                "Victory comes through surrendering the self to the service of all.",
                "Om Vajrasattva Hum",
            ),
        }

        key = (genre, hour)
        if key in TRANSMUTATIONS:
            return TRANSMUTATIONS[key]

        # Generic transmutation for any unmatched combination
        return (
            f"{hour} hour challenges {genre} work. Begin with a brief purification or grounding "
            f"practice to transmute the energy before proceeding with the main ritual.",
            "Om Ah Hum",
        )

    def _find_next_favorable(self, favorable_hours: list[str]) -> tuple[int, str]:
        """Find minutes until the next favorable planetary hour."""
        now = datetime.now()
        current_idx = (now.hour + now.weekday() * 2) % 7

        # Search forward through the Chaldean cycle
        for offset in range(1, 25):  # Check up to 24 hours ahead
            future_idx = (current_idx + offset) % 7
            planet = self.CHALDEAN_ORDER[future_idx]
            if planet in favorable_hours:
                minutes = offset * 60  # Rough: each planet rules ~1 hour
                # More precise: calculate actual minutes to that hour
                current_minutes = now.minute
                minutes = offset * 60 - current_minutes
                if minutes < 1:
                    minutes = 5  # Minimum wait
                return minutes, planet

        return 60, favorable_hours[0]  # Fallback

    def get_timing_wheel_data(
        self,
        lat: float | None = None,
        lon: float | None = None,
        target_dt: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Build full 24-hour Auspicious Timing Wheel data structure.
        Includes 24 planetary hour slices, moon ring, tithi, nakshatra, Saka Dawa multiplier,
        genre compatibility, and upcoming green windows.
        """
        from datetime import timedelta

        from core.situation_geometry import DEFAULT_LAT, DEFAULT_LNG

        dt = target_dt or datetime.now()
        latitude = lat if lat is not None else DEFAULT_LAT
        longitude = lon if lon is not None else DEFAULT_LNG
        location = (latitude, longitude)

        # 1. Exact or estimated planetary hours calculation
        exact_hours = None
        if self.engine:
            try:
                exact_hours = self.engine.calculate_exact_planetary_hours(dt, location)
            except Exception:
                exact_hours = None

        if not exact_hours or exact_hours.get("status") != "success":
            # Fallback estimation based on 6:00 AM sunrise and 6:00 PM sunset
            weekday_idx = dt.weekday()
            day_ruler = self.WEEKDAY_RULERS[weekday_idx]
            start_ruler_idx = self.CHALDEAN_ORDER.index(day_ruler)
            day_rulers = [self.CHALDEAN_ORDER[(start_ruler_idx + i) % 7] for i in range(12)]
            night_rulers = [self.CHALDEAN_ORDER[(start_ruler_idx + 12 + i) % 7] for i in range(12)]

            sunrise = dt.replace(hour=6, minute=0, second=0, microsecond=0)
            sunset = dt.replace(hour=18, minute=0, second=0, microsecond=0)
            is_daytime = 6 <= dt.hour < 18
            hour_idx = (dt.hour - 6) % 12 if is_daytime else (dt.hour - 18) % 12
            current_ruler = day_rulers[hour_idx] if is_daytime else night_rulers[hour_idx]
            day_hour_dur = timedelta(minutes=60)
            night_hour_dur = timedelta(minutes=60)
            prev_sunset = sunset if dt.hour >= 18 else sunset - timedelta(days=1)
        else:
            day_rulers = exact_hours["day_rulers"]
            night_rulers = exact_hours["night_rulers"]
            is_daytime = exact_hours["is_daytime"]
            hour_idx = exact_hours["hour_index"] - 1
            current_ruler = exact_hours["current_planetary_hour"]
            day_ruler = exact_hours["day_planet"]

            times = self.engine.calculate_auspicious_times(dt, location) if self.engine else {}
            sunrise = times.get("sunrise") or dt.replace(hour=6, minute=0, second=0, microsecond=0)
            sunset = times.get("sunset") or dt.replace(hour=18, minute=0, second=0, microsecond=0)
            day_hour_dur = (sunset - sunrise) / 12

            if dt >= sunset:
                prev_sunset = sunset
                next_day_times = (
                    self.engine.calculate_auspicious_times(dt + timedelta(days=1), location) if self.engine else {}
                )
                next_sunrise = next_day_times.get("sunrise") or (sunrise + timedelta(days=1))
            elif dt < sunrise:
                prev_day_times = (
                    self.engine.calculate_auspicious_times(dt - timedelta(days=1), location) if self.engine else {}
                )
                prev_sunset = prev_day_times.get("sunset") or (sunset - timedelta(days=1))
                next_sunrise = sunrise
            else:
                prev_sunset = sunset
                next_day_times = (
                    self.engine.calculate_auspicious_times(dt + timedelta(days=1), location) if self.engine else {}
                )
                next_sunrise = next_day_times.get("sunrise") or (sunrise + timedelta(days=1))
            night_hour_dur = (next_sunrise - prev_sunset) / 12

        # 2. Build 24 planetary hour slices
        hour_slices: list[dict[str, Any]] = []

        # 12 day hours
        for i in range(12):
            ruler = day_rulers[i]
            h_start = sunrise + day_hour_dur * i
            h_end = sunrise + day_hour_dur * (i + 1)
            is_curr = is_daytime and (hour_idx == i)

            affinities = {}
            for g, cfg in GENRE_PLANETARY_HOURS.items():
                if ruler in cfg.get("favorable", []):
                    affinities[g] = "favorable"
                elif ruler in cfg.get("neutral", []):
                    affinities[g] = "neutral"
                else:
                    affinities[g] = "unfavorable"

            hour_slices.append(
                {
                    "index": i,
                    "period": "day",
                    "hour_number": i + 1,
                    "ruler": ruler,
                    "start_time": h_start.isoformat(),
                    "end_time": h_end.isoformat(),
                    "is_current": is_curr,
                    "affinities": affinities,
                }
            )

        # 12 night hours
        for i in range(12):
            ruler = night_rulers[i]
            h_start = prev_sunset + night_hour_dur * i
            h_end = prev_sunset + night_hour_dur * (i + 1)
            is_curr = (not is_daytime) and (hour_idx == i)

            affinities = {}
            for g, cfg in GENRE_PLANETARY_HOURS.items():
                if ruler in cfg.get("favorable", []):
                    affinities[g] = "favorable"
                elif ruler in cfg.get("neutral", []):
                    affinities[g] = "neutral"
                else:
                    affinities[g] = "unfavorable"

            hour_slices.append(
                {
                    "index": i + 12,
                    "period": "night",
                    "hour_number": i + 1,
                    "ruler": ruler,
                    "start_time": h_start.isoformat(),
                    "end_time": h_end.isoformat(),
                    "is_current": is_curr,
                    "affinities": affinities,
                }
            )

        # 3. Moon Phase and Tithi
        moon_data = self._get_moon_phase()
        phase_name = moon_data.get("phase_name", "Waxing Gibbous")
        phase_angle = moon_data.get("phase_angle", 120.0)

        glyph_idx = int(((phase_angle + 22.5) % 360) / 45) % 8
        moon_glyphs = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
        moon_glyph = moon_glyphs[glyph_idx]

        tithi_name = self._get_tithi()
        nakshatra_name = self._get_nakshatra()
        nakshatra_quality = NAKSHATRA_QUALITIES.get(nakshatra_name, "")
        saka = check_saka_dawa(dt)

        # 4. Genre Assessment and Upcoming Windows
        genre_windows = {}
        next_optimal_windows: dict[str, list[dict[str, Any]]] = {}

        for g, cfg in GENRE_PLANETARY_HOURS.items():
            win = self.check(g)
            genre_windows[g] = win.to_dict()

            fav_slices = []
            for s in hour_slices:
                if s["ruler"] in cfg.get("favorable", []):
                    fav_slices.append(
                        {
                            "period": s["period"],
                            "hour_number": s["hour_number"],
                            "ruler": s["ruler"],
                            "start_time": s["start_time"],
                            "end_time": s["end_time"],
                            "is_current": s["is_current"],
                        }
                    )
            next_optimal_windows[g] = fav_slices

        return {
            "status": "success",
            "datetime": dt.isoformat(),
            "location": {"latitude": latitude, "longitude": longitude},
            "current_planetary_hour": {
                "ruler": current_ruler,
                "day_planet": day_ruler,
                "is_daytime": is_daytime,
                "hour_number": hour_idx + 1,
            },
            "moon": {
                "phase_name": phase_name,
                "phase_angle": phase_angle,
                "glyph": moon_glyph,
                "tithi": tithi_name,
                "nakshatra": nakshatra_name,
                "nakshatra_quality": nakshatra_quality,
            },
            "saka_dawa": saka,
            "hourly_slices": hour_slices,
            "genre_windows": genre_windows,
            "next_optimal_windows": next_optimal_windows,
        }


# Convenience
_timing_instance: AuspiciousTiming | None = None


def get_timing_wheel(
    lat: float | None = None,
    lon: float | None = None,
    target_dt: datetime | None = None,
) -> dict[str, Any]:
    """Get the full 24-hour Auspicious Timing Wheel data structure."""
    global _timing_instance
    if _timing_instance is None:
        _timing_instance = AuspiciousTiming()
    return _timing_instance.get_timing_wheel_data(lat=lat, lon=lon, target_dt=target_dt)


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


def _saka_practice_payload() -> dict[str, Any] | None:
    """Attach the Saka Dawa sadhana catalog entry when it exists."""
    try:
        from core.models.practice import Practice

        practices = Practice.get_default_practices()
        saka = next(
            (p for p in practices if "saka" in p.name.lower() or "saka" in getattr(p, "id", "").lower()),
            None,
        )
        if saka is None:
            return None
        return {
            "id": saka.id,
            "name": saka.name,
            "tradition": getattr(saka, "tradition", ""),
            "description": getattr(saka, "description", ""),
            "genre": saka.genre,
            "merit_multiplier": saka.merit_multiplier,
            "blessing_prompt": saka.base_prompt_template,
            "preferred_hours": getattr(saka, "preferred_planetary_hours", []),
        }
    except Exception:
        return None


def check_saka_dawa(target_date: datetime | None = None) -> dict[str, Any]:
    """Check whether ``target_date`` falls in Saka Dawa (4th Tibetan month).

    Anchored to published Phugpa/CTA Losar dates, not the Chinese lunar
    month. See ``core.tibetan_calendar``.
    """
    from core.tibetan_calendar import saka_dawa_status

    result = saka_dawa_status(target_date)
    practice = _saka_practice_payload()
    if practice is not None:
        result["practice"] = practice

    if result.get("is_duchen"):
        result["message"] = "Saka Dawa Duchen — full moon of the 4th Tibetan month " "(Losar-anchored). Merit ×100,000."
    elif result.get("is_saka_dawa"):
        result["message"] = (
            "Saka Dawa holy month is active (4th month after Losar "
            f"{result.get('losar')}). Duchen {result.get('saka_dawa_duchen')}. "
            "Merit ×10,000."
        )
    elif result.get("saka_dawa_duchen"):
        days = result.get("days_until_duchen")
        result["message"] = (
            f"Not in Saka Dawa. Next Duchen {result.get('saka_dawa_duchen')}"
            + (f" ({days} days)." if days is not None else ".")
            + f" Month runs {result.get('saka_dawa_month_start')} to "
            f"{result.get('saka_dawa_month_end')}."
        )
    else:
        result.setdefault("message", "Saka Dawa date is unavailable for this year.")
    return result
