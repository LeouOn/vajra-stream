"""
Vajra.Stream Astrology Module
Comprehensive time-space calculations for Western, Indian (Vedic), and Chinese systems.
Uses Swiss Ephemeris and lunar-python for precise, offline-first calculations.
"""

__version__ = "1.0.0"

import math
from datetime import datetime, timedelta

import pytz
import swisseph as swe


class AstrologicalCalculator:
    """Comprehensive astrological calculator for three major traditions.

    Supports Western Tropical, Indian Vedic (Sidereal/Panchanga), and Chinese
    Lunisolar (BaZi/Sheng Xiao) systems. Uses Swiss Ephemeris (swisseph) for
    precise planetary calculations and lunar-python for Chinese calendar data.

    All datetime arguments should be timezone-aware (``pytz.UTC`` or local tz).
    Location tuples are ``(latitude, longitude)`` in decimal degrees.

    Key methods:
        :meth:`get_comprehensive_astrology` — one-call consolidation of all three systems.
        :meth:`calculate_exact_planetary_hours` — Chaldean planetary hours.
        :meth:`recommend_frequencies_for_time` — audio frequencies for current energetics.

    Attributes:
        PLANETS: Dict mapping planet names to Swiss Ephemeris constants.
        SIGNS: List of 12 Western zodiac sign names.
        CHALDEAN_ORDER: Traditional planetary hour sequence.
        WEEKDAY_RULERS: Mapping of weekday index (Mon=0) to ruling planet.
    """

    def __init__(self):
        # Set ephemeris path (uses built-in data)
        swe.set_ephe_path("")

        # Planet constants
        self.PLANETS = {
            "sun": swe.SUN,
            "moon": swe.MOON,
            "mercury": swe.MERCURY,
            "venus": swe.VENUS,
            "mars": swe.MARS,
            "jupiter": swe.JUPITER,
            "saturn": swe.SATURN,
            "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE,
            "pluto": swe.PLUTO,
            "north_node": swe.MEAN_NODE,
            "chiron": swe.CHIRON,
        }

        # Zodiac signs (Western Tropical)
        self.SIGNS = [
            "Aries",
            "Taurus",
            "Gemini",
            "Cancer",
            "Leo",
            "Virgo",
            "Libra",
            "Scorpio",
            "Sagittarius",
            "Capricorn",
            "Aquarius",
            "Pisces",
        ]

        # Chaldean planetary hour order (descending speed)
        self.CHALDEAN_ORDER = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

        # Mapping weekdays (Monday=0 to Sunday=6) to their traditional rulers
        self.WEEKDAY_RULERS = {
            0: "Moon",  # Monday
            1: "Mars",  # Tuesday
            2: "Mercury",  # Wednesday
            3: "Jupiter",  # Thursday
            4: "Venus",  # Friday
            5: "Saturn",  # Saturday
            6: "Sun",  # Sunday
        }

    def get_julian_day(self, dt: datetime) -> float:
        """Convert a datetime to a Swiss Ephemeris Julian Day number.

        Timezone-aware datetimes are converted to UTC first; naive datetimes
        are treated as UTC.

        Args:
            dt: Datetime to convert (naive or tz-aware).

        Returns:
            float: Julian Day number suitable for ``swe.julday`` / ``swe.calc_ut``.
        """
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(pytz.UTC)
        else:
            dt_utc = dt
        return swe.julday(
            dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        )

    def _get_house_from_cusps(self, lon: float, cusps) -> int:
        # cusps is a 0-indexed tuple of size 12
        for i in range(12):
            c1 = cusps[i]
            c2 = cusps[(i + 1) % 12]
            if c2 > c1:
                if c1 <= lon < c2:
                    return i + 1
            else:  # wraps around 360
                if lon >= c1 or lon < c2:
                    return i + 1
        return 1

    # =========================================================================
    # WESTERN ASTROLOGY FUNCTIONS
    # =========================================================================

    def get_planetary_positions(self, dt: datetime, location: tuple[float, float] = None) -> dict:
        """Calculate tropical (Western) positions of all planets.

        Returns longitude, sign, degree-in-sign, and a formatted string
        for each planet in ``self.PLANETS``.

        Args:
            dt: Datetime for the calculation.
            location: Optional ``(latitude, longitude)`` tuple (currently unused
                for planetary positions but accepted for API compatibility).

        Returns:
            dict: ``{planet_name: {longitude, sign, degree, formatted}, ...}``
        """
        jd = self.get_julian_day(dt)
        positions = {}
        chiron_id = self.PLANETS.get("chiron")
        main_planets = {k: v for k, v in self.PLANETS.items() if k != "chiron"}

        for name, planet_id in main_planets.items():
            result = swe.calc_ut(jd, planet_id)
            longitude = result[0][0]
            speed = result[0][3]  # degrees per day — negative = retrograde

            sign_num = int(longitude / 30) % 12
            degree_in_sign = longitude % 30

            retrograde = speed < 0

            positions[name] = {
                "longitude": longitude,
                "sign": self.SIGNS[sign_num],
                "degree": degree_in_sign,
                "formatted": f"{self.SIGNS[sign_num]} {degree_in_sign:.2f}°{' ℞' if retrograde else ''}",
                "retrograde": retrograde,
                "speed": round(speed, 4),
            }

        if chiron_id is not None:
            try:
                chiron_result = swe.calc_ut(jd, chiron_id)
                cl = chiron_result[0][0]
                cs = chiron_result[0][3]
                csn = int(cl / 30) % 12
                positions["chiron"] = {
                    "longitude": cl,
                    "sign": self.SIGNS[csn],
                    "degree": cl % 30,
                    "formatted": f"{self.SIGNS[csn]} {cl % 30:.2f}°{' ℞' if cs < 0 else ''}",
                    "retrograde": cs < 0,
                    "speed": round(cs, 4),
                }
            except Exception:
                pass

        return positions

    def get_western_astrology(self, dt: datetime, location: tuple[float, float] = None) -> dict:
        """
        Calculate Western astrology elements: Tropical positions, Aspects, and Elemental Balance.
        """
        positions = self.get_planetary_positions(dt, location)

        # Calculate Ascendant and MC for Western
        jd = self.get_julian_day(dt)
        cusps = None
        if location:
            lat, lon = location
            houses, ascmc = swe.houses(jd, lat, lon, b"P")
            cusps = houses
            positions["ascendant"] = {
                "longitude": ascmc[0],
                "sign": self.SIGNS[int(ascmc[0] / 30) % 12],
                "degree": ascmc[0] % 30,
                "formatted": f"{self.SIGNS[int(ascmc[0] / 30) % 12]} {ascmc[0] % 30:.2f}°",
            }
            positions["midheaven"] = {
                "longitude": ascmc[1],
                "sign": self.SIGNS[int(ascmc[1] / 30) % 12],
                "degree": ascmc[1] % 30,
                "formatted": f"{self.SIGNS[int(ascmc[1] / 30) % 12]} {ascmc[1] % 30:.2f}°",
            }

        for name, info in positions.items():
            if name in ["ascendant", "midheaven"]:
                continue
            if cusps is not None:
                info["house"] = self._get_house_from_cusps(info["longitude"], cusps)
            else:
                info["house"] = None

        # 1. Elements and Modalities
        elements = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
        modalities = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}

        element_map = {
            "Aries": "Fire",
            "Leo": "Fire",
            "Sagittarius": "Fire",
            "Taurus": "Earth",
            "Virgo": "Earth",
            "Capricorn": "Earth",
            "Gemini": "Air",
            "Libra": "Air",
            "Aquarius": "Air",
            "Cancer": "Water",
            "Scorpio": "Water",
            "Pisces": "Water",
        }

        modality_map = {
            "Aries": "Cardinal",
            "Cancer": "Cardinal",
            "Libra": "Cardinal",
            "Capricorn": "Cardinal",
            "Taurus": "Fixed",
            "Leo": "Fixed",
            "Scorpio": "Fixed",
            "Aquarius": "Fixed",
            "Gemini": "Mutable",
            "Virgo": "Mutable",
            "Sagittarius": "Mutable",
            "Pisces": "Mutable",
        }

        # Weighting: Sun, Moon (3 points); personal planets (2 points); outer planets (1 point)
        weights = {
            "sun": 3,
            "moon": 3,
            "mercury": 2,
            "venus": 2,
            "mars": 2,
            "jupiter": 1,
            "saturn": 1,
            "uranus": 1,
            "neptune": 1,
            "pluto": 1,
        }

        for planet, info in positions.items():
            if planet in weights:
                weight = weights[planet]
                sign = info["sign"]
                elements[element_map[sign]] += weight
                modalities[modality_map[sign]] += weight

        # 2. Aspect calculations
        aspects = []
        planet_names = [p for p in positions.keys() if p not in ["ascendant", "midheaven"]]

        aspect_types = [
            {"name": "Conjunction", "angle": 0, "orb": 8},
            {"name": "Sextile", "angle": 60, "orb": 6},
            {"name": "Square", "angle": 90, "orb": 8},
            {"name": "Trine", "angle": 120, "orb": 8},
            {"name": "Opposition", "angle": 180, "orb": 8},
        ]

        for i in range(len(planet_names)):
            for j in range(i + 1, len(planet_names)):
                p1 = planet_names[i]
                p2 = planet_names[j]

                # Filter outer planet minor relationships to avoid clutter
                if p1 in ["uranus", "neptune", "pluto"] and p2 in ["uranus", "neptune", "pluto"]:
                    continue

                lon1 = positions[p1]["longitude"]
                lon2 = positions[p2]["longitude"]

                diff = abs(lon1 - lon2) % 360
                distance = min(diff, 360 - diff)

                for asp in aspect_types:
                    if abs(distance - asp["angle"]) <= asp["orb"]:
                        exactness = 1 - (abs(distance - asp["angle"]) / asp["orb"])
                        aspects.append(
                            {
                                "planet1": p1,
                                "planet2": p2,
                                "aspect": asp["name"],
                                "angle": distance,
                                "exactness": exactness,
                                "description": f"{p1.title()} {asp['name']} {p2.title()} (Orb: {abs(distance - asp['angle']):.2f}°)",
                            }
                        )

        return {
            "positions": positions,
            "elements": elements,
            "modalities": modalities,
            "dominant_element": max(elements, key=elements.get),
            "dominant_modality": max(modalities, key=modalities.get),
            "aspects": aspects,
            "houses": {
                f"house_{i + 1}": {
                    "longitude": cusps[i],
                    "sign": self.SIGNS[int(cusps[i] / 30) % 12],
                    "degree": cusps[i] % 30,
                    "formatted": f"{self.SIGNS[int(cusps[i] / 30) % 12]} {cusps[i] % 30:.2f}°",
                }
                for i in range(12)
            } if cusps is not None else {},
        }

    # =========================================================================
    # HELLENISTIC LOTS
    # =========================================================================

    def get_hellenistic_lots(
        self,
        dt: datetime,
        location: tuple[float, float] | None = None,
        sect: str = "day",
    ) -> dict:
        """Calculate the seven classical Hellenistic astrological lots.

        The seven lots are the foundational "places" (kleroi) of Hellenistic
        chart interpretation: Fortune (Tyche), Spirit (Daimon), Eros, Necessity
        (Ananke), Courage (Andreia), Victory (Nike), and Nemesis.

        Whole-sign placement is used: each lot is placed in the zodiac sign
        determined by its absolute longitude (0° Aries = 0°). The degree
        within the sign is ``lon mod 30``. This is the simplest and most
        reproducible placement for v1.

        Formulas (mod 360):
            Fortune (day):  ASC + Moon - Sun
            Fortune (night): ASC + Sun - Moon
            Spirit (day):   ASC + Sun - Moon
            Spirit (night): ASC + Moon - Sun
            Eros (day):     Spirit + Venus - Sun  (equivalently ASC + Venus - Moon)
            Necessity:      ASC + Mercury - Sun
            Courage:        ASC + Mars - Sun
            Victory:        ASC + Jupiter - Sun
            Nemesis:        ASC + Saturn - Sun

        Fortune and Spirit swap Sun and Moon by sect. The remaining five lots
        use the day-chart formula regardless of sect (this is a v1 simplification;
        some traditions swap Sun for Moon at night for the planetary lots too).

        Args:
            dt: Datetime for the chart (timezone-aware recommended).
            location: Optional ``(latitude, longitude)`` tuple. If ``None``,
                defaults to ``(0.0, 0.0)`` (equator / prime meridian).
            sect: ``"day"`` (default) or ``"night"`` — selects the Fortune /
                Spirit formula.

        Returns:
            dict: ``{lot_name: {"sign": str, "degree": float,
            "exact_longitude": float}, ...}`` for the 7 lots:
            ``fortune, spirit, eros, necessity, courage, victory, nemesis``.

        Raises:
            ValueError: If ``sect`` is not ``"day"`` or ``"night"``.
        """
        if sect not in ("day", "night"):
            raise ValueError(f"sect must be 'day' or 'night', got {sect!r}")

        if location is None:
            lat, lon = 0.0, 0.0
        else:
            lat, lon = location

        jd = self.get_julian_day(dt)

        cusps, ascmc = swe.houses_ex(jd, lat, lon, b"P")
        asc_lon = float(ascmc[0])

        positions = self.get_planetary_positions(dt, location)
        sun_lon = positions["sun"]["longitude"]
        moon_lon = positions["moon"]["longitude"]
        mercury_lon = positions["mercury"]["longitude"]
        venus_lon = positions["venus"]["longitude"]
        mars_lon = positions["mars"]["longitude"]
        jupiter_lon = positions["jupiter"]["longitude"]
        saturn_lon = positions["saturn"]["longitude"]

        if sect == "day":
            fortune_lon = (asc_lon + moon_lon - sun_lon) % 360
            spirit_lon = (asc_lon + sun_lon - moon_lon) % 360
        else:
            fortune_lon = (asc_lon + sun_lon - moon_lon) % 360
            spirit_lon = (asc_lon + moon_lon - sun_lon) % 360

        eros_lon = (spirit_lon + venus_lon - sun_lon) % 360
        necessity_lon = (asc_lon + mercury_lon - sun_lon) % 360
        courage_lon = (asc_lon + mars_lon - sun_lon) % 360
        victory_lon = (asc_lon + jupiter_lon - sun_lon) % 360
        nemesis_lon = (asc_lon + saturn_lon - sun_lon) % 360

        raw_lots = {
            "fortune": fortune_lon,
            "spirit": spirit_lon,
            "eros": eros_lon,
            "necessity": necessity_lon,
            "courage": courage_lon,
            "victory": victory_lon,
            "nemesis": nemesis_lon,
        }

        lots: dict = {}
        for name, lon in raw_lots.items():
            lon = lon % 360
            sign_idx = int(lon // 30) % 12
            lots[name] = {
                "sign": self.SIGNS[sign_idx],
                "degree": lon % 30,
                "exact_longitude": lon,
            }

        return lots

    # =========================================================================
    # INDIAN VEDIC ASTROLOGY FUNCTIONS (PANCHANG)
    # =========================================================================

    def get_indian_astrology(self, dt: datetime, location: tuple[float, float] = None) -> dict:
        """
        Calculate Indian (Vedic) astrology: Sidereal positions and Panchanga elements.
        """
        jd = self.get_julian_day(dt)

        # Calculate Ayanamsa (precession offset for Lahiri)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayanamsa = swe.get_ayanamsa_ut(jd)

        # Sanskrit Zodiac Signs (Rashis)
        rashis = [
            "Mesha (Aries)",
            "Vrishabha (Taurus)",
            "Mithuna (Gemini)",
            "Karka (Cancer)",
            "Simha (Leo)",
            "Kanya (Virgo)",
            "Tula (Libra)",
            "Vrischika (Scorpio)",
            "Dhanu (Sagittarius)",
            "Makara (Capricorn)",
            "Kumbha (Aquarius)",
            "Meena (Pisces)",
        ]

        # Calculate all planetary sidereal positions
        sidereal_positions = {}

        # Calculate Ascendant (Lagna)
        if location:
            lat, lon = location
            _, ascmc = swe.houses(jd, lat, lon, b"W")
            tropical_asc = ascmc[0]
            sidereal_asc = (tropical_asc - ayanamsa) % 360
            asc_rashi_idx = int(sidereal_asc / 30) % 12
            sidereal_positions["ascendant"] = {
                "longitude": sidereal_asc,
                "rashi": rashis[asc_rashi_idx],
                "rashi_name": rashis[asc_rashi_idx].split(" ")[0],
                "rashi_number": asc_rashi_idx + 1,
                "degree": sidereal_asc % 30,
                "formatted": f"{rashis[asc_rashi_idx]} {sidereal_asc % 30:.2f}°",
            }
        else:
            # Fallback if no location
            sidereal_asc = 0.0
            sidereal_positions["ascendant"] = {
                "longitude": sidereal_asc,
                "rashi": rashis[0],
                "rashi_name": rashis[0].split(" ")[0],
                "rashi_number": 1,
                "degree": 0.0,
                "formatted": f"{rashis[0]} 0.00°",
            }

        # Calculate standard planets
        chiron_id = self.PLANETS.get("chiron")
        main_planets = {k: v for k, v in self.PLANETS.items() if k != "chiron"}
        for name, planet_id in main_planets.items():
            result = swe.calc_ut(jd, planet_id, swe.FLG_SIDEREAL)
            sidereal_lon = result[0][0]
            rashi_idx = int(sidereal_lon / 30) % 12

            # Map name for front-end (mean node is Rahu)
            key_name = name
            if name == "north_node":
                key_name = "rahu"

            sidereal_positions[key_name] = {
                "longitude": sidereal_lon,
                "rashi": rashis[rashi_idx],
                "rashi_name": rashis[rashi_idx].split(" ")[0],
                "rashi_number": rashi_idx + 1,
                "degree": sidereal_lon % 30,
                "formatted": f"{rashis[rashi_idx]} {sidereal_lon % 30:.2f}°",
            }

        if chiron_id is not None:
            try:
                chiron_result = swe.calc_ut(jd, chiron_id, swe.FLG_SIDEREAL)
                cl = chiron_result[0][0]
                cr = int(cl / 30) % 12
                sidereal_positions["chiron"] = {
                    "longitude": cl,
                    "rashi": rashis[cr],
                    "rashi_name": rashis[cr].split(" ")[0],
                    "rashi_number": cr + 1,
                    "degree": cl % 30,
                    "formatted": f"{rashis[cr]} {cl % 30:.2f}°",
                }
            except Exception:
                pass

        # Add Ketu (opposite Rahu)
        if "rahu" in sidereal_positions:
            rahu_lon = sidereal_positions["rahu"]["longitude"]
            ketu_lon = (rahu_lon + 180) % 360
            ketu_rashi_idx = int(ketu_lon / 30) % 12
            sidereal_positions["ketu"] = {
                "longitude": ketu_lon,
                "rashi": rashis[ketu_rashi_idx],
                "rashi_name": rashis[ketu_rashi_idx].split(" ")[0],
                "rashi_number": ketu_rashi_idx + 1,
                "degree": ketu_lon % 30,
                "formatted": f"{rashis[ketu_rashi_idx]} {ketu_lon % 30:.2f}°",
            }

        # Retrieve Sun and Moon for legacy/internal references
        sidereal_sun_lon = sidereal_positions["sun"]["longitude"]
        sidereal_moon_lon = sidereal_positions["moon"]["longitude"]
        sun_pos_result = swe.calc_ut(jd, swe.SUN)
        moon_pos_result = swe.calc_ut(jd, swe.MOON)
        tropical_sun_lon = sun_pos_result[0][0]
        tropical_moon_lon = moon_pos_result[0][0]

        # 1. Tithi (Lunar Day)
        # Difference in longitude: Moon - Sun
        diff_lon = (tropical_moon_lon - tropical_sun_lon) % 360
        tithi_val = diff_lon / 12
        tithi_num = int(tithi_val) + 1
        tithi_progress = tithi_val % 1

        tithi_names = [
            "Prathama",
            "Dwitiya",
            "Tritiya",
            "Chaturthi",
            "Panchami",
            "Shasthi",
            "Saptami",
            "Ashtami",
            "Navami",
            "Dashami",
            "Ekadashi",
            "Dwadashi",
            "Trayodashi",
            "Chaturdashi",
            "Purnima/Amavasya",
        ]
        paksha = "Shukla (Waxing)" if tithi_num <= 15 else "Krishna (Waning)"
        norm_tithi = tithi_num if tithi_num <= 15 else tithi_num - 15
        tithi_name = tithi_names[norm_tithi - 1]

        if tithi_num == 15:
            tithi_name = "Purnima (Full Moon)"
        elif tithi_num == 30:
            tithi_name = "Amavasya (New Moon)"

        # 2. Nakshatra (Lunar Mansion)
        nakshatra_val = sidereal_moon_lon / (360 / 27)
        nakshatra_num = int(nakshatra_val) + 1
        nakshatra_progress = nakshatra_val % 1

        nakshatras = [
            "Ashwini",
            "Bharani",
            "Krittika",
            "Rohini",
            "Mrigashira",
            "Ardra",
            "Punarvasu",
            "Pushya",
            "Ashlesha",
            "Magha",
            "Purva Phalguni",
            "Uttara Phalguni",
            "Hasta",
            "Chitra",
            "Swati",
            "Vishakha",
            "Anuradha",
            "Jyeshtha",
            "Mula",
            "Purva Ashadha",
            "Uttara Ashadha",
            "Shravana",
            "Dhanishta",
            "Shatabhisha",
            "Purva Bhadrapada",
            "Uttara Bhadrapada",
            "Revati",
        ]
        nakshatra_name = nakshatras[(nakshatra_num - 1) % 27]

        # 3. Yoga
        yoga_val = (sidereal_sun_lon + sidereal_moon_lon) % 360 / (360 / 27)
        yoga_num = int(yoga_val) + 1
        yoga_progress = yoga_val % 1

        yogas = [
            "Vishkumbha",
            "Priti",
            "Ayushman",
            "Saubhagya",
            "Shobhana",
            "Atiganda",
            "Sukarma",
            "Dhriti",
            "Shula",
            "Ganda",
            "Vridhi",
            "Dhruva",
            "Vyaghata",
            "Harshana",
            "Vajra",
            "Siddhi",
            "Vyatipata",
            "Variyan",
            "Parigha",
            "Shiva",
            "Siddha",
            "Sadhya",
            "Shubha",
            "Shukla",
            "Brahma",
            "Indra",
            "Vaidhriti",
        ]
        yoga_name = yogas[(yoga_num - 1) % 27]

        # 4. Karana
        karana_val = diff_lon / 6
        karana_num = int(karana_val) + 1

        karana_names = [
            "Bava",
            "Balava",
            "Kaulava",
            "Taitila",
            "Gara",
            "Vanija",
            "Vishti (Bhadra)",
            "Shakuni",
            "Chatushpada",
            "Naga",
            "Kintughna",
        ]
        if karana_num == 1:
            karana_name = "Kintughna"
        elif karana_num >= 58:
            static_karanas = ["Shakuni", "Chatushpada", "Naga"]
            karana_name = static_karanas[min(karana_num - 58, 2)]
        else:
            cycle_idx = (karana_num - 2) % 7
            karana_name = karana_names[cycle_idx]

        # 5. Vara (Solar day starting at sunrise)
        local_date = dt
        sunrise_today = None
        if location:
            times = self.calculate_auspicious_times(local_date, location)
            sunrise_today = times.get("sunrise")

        if sunrise_today and local_date < sunrise_today:
            vara_idx = (local_date.weekday() - 1) % 7
        else:
            vara_idx = local_date.weekday()

        vara_names = [
            "Somavara (Monday)",
            "Mangalavara (Tuesday)",
            "Budhavara (Wednesday)",
            "Guruvara (Thursday)",
            "Sukravara (Friday)",
            "Sanivara (Saturday)",
            "Ravivara (Sunday)",
        ]
        vara_name = vara_names[vara_idx]

        return {
            "ayanamsa": ayanamsa,
            "sidereal_positions": sidereal_positions,
            "panchanga": {
                "tithi": {"number": tithi_num, "name": tithi_name, "paksha": paksha, "progress": tithi_progress},
                "nakshatra": {"number": nakshatra_num, "name": nakshatra_name, "progress": nakshatra_progress},
                "yoga": {"number": yoga_num, "name": yoga_name, "progress": yoga_progress},
                "karana": {"number": karana_num, "name": karana_name},
                "vara": {"name": vara_name, "index": vara_idx},
            },
        }

    # =========================================================================
    # CHINESE ASTROLOGY & LUNISOLAR FUNCTIONS
    # =========================================================================

    def get_chinese_astrology(self, dt: datetime) -> dict:
        """
        Calculate Chinese Astrology elements using lunar-python library.
        Returns Lunar Date, Sheng Xiao (Zodiac), BaZi, and Shichen.
        """
        try:
            from lunar_python import Lunar, Solar

            # Convert timezone to China Standard Time (UTC+8) which Chinese calendar uses
            dt_china = dt.astimezone(pytz.timezone("Asia/Shanghai"))

            solar_c = Solar.fromYmdHms(
                dt_china.year, dt_china.month, dt_china.day, dt_china.hour, dt_china.minute, dt_china.second
            )
            lunar_c = solar_c.getLunar()

            is_leap = lunar_c.getMonth() < 0
            month_num = abs(lunar_c.getMonth())

            bazi = lunar_c.getEightChar()

            # Translation mappings for English display & frontend compatibility
            stems_translation = {
                "甲": "Jia",
                "乙": "Yi",
                "丙": "Bing",
                "丁": "Ding",
                "戊": "Wu",
                "己": "Ji",
                "庚": "Geng",
                "辛": "Xin",
                "壬": "Ren",
                "癸": "Gui",
            }
            branches_translation = {
                "子": "Zi-Rat",
                "丑": "Chou-Ox",
                "寅": "Yin-Tiger",
                "卯": "Mao-Rabbit",
                "辰": "Chen-Dragon",
                "巳": "Si-Snake",
                "午": "Wu-Horse",
                "未": "Wei-Goat",
                "申": "Shen-Monkey",
                "酉": "You-Rooster",
                "戌": "Xu-Dog",
                "亥": "Hai-Pig",
            }
            animals_translation = {
                "鼠": "Rat",
                "牛": "Ox",
                "虎": "Tiger",
                "兔": "Rabbit",
                "龙": "Dragon",
                "蛇": "Snake",
                "马": "Horse",
                "羊": "Goat",
                "猴": "Monkey",
                "鸡": "Rooster",
                "狗": "Dog",
                "猪": "Pig",
            }
            solar_terms_translation = {
                "春分": "Chunfen (Spring Equinox)",
                "清明": "Qingming",
                "谷雨": "Guyu",
                "立夏": "Lixia (Start of Summer)",
                "小满": "Xiaoman",
                "芒种": "Mangzhong",
                "夏至": "Xiazhi (Summer Solstice)",
                "小暑": "Xiaoshu",
                "大暑": "Dashu",
                "立秋": "Liqiu (Start of Autumn)",
                "处暑": "Chushu",
                "白露": "Bailu",
                "秋分": "Qiufen (Autumn Equinox)",
                "寒露": "Hanlu",
                "霜降": "Shuangjiang",
                "立冬": "Lidong (Start of Winter)",
                "小雪": "Xiaoxue",
                "大雪": "Daxue",
                "冬至": "Dongzhi (Winter Solstice)",
                "小寒": "Xiaohan",
                "大寒": "Dahan",
                "立春": "Lichun (Start of Spring)",
                "雨水": "Yushui",
                "惊蛰": "Jingzhe",
            }

            def translate_pillar(pillar_str, wuxing_str):
                if len(pillar_str) >= 2:
                    s = pillar_str[0]
                    b = pillar_str[1]
                    trans_s = stems_translation.get(s, s)
                    trans_b = branches_translation.get(b, b)
                    return f"{pillar_str}/{trans_s}-{trans_b} ({wuxing_str})"
                return f"{pillar_str} ({wuxing_str})"

            # Earthly branches corresponding to Shichen
            shichen_branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
            shichen_names = [
                "Zi (Rat)",
                "Chou (Ox)",
                "Yin (Tiger)",
                "Mao (Rabbit)",
                "Chen (Dragon)",
                "Si (Snake)",
                "Wu (Horse)",
                "Wei (Goat)",
                "Shen (Monkey)",
                "You (Rooster)",
                "Xu (Dog)",
                "Hai (Pig)",
            ]

            # Shichen hour branch index based on local hour
            local_hour = dt.hour
            shichen_idx = ((local_hour + 1) // 2) % 12

            jieqi = lunar_c.getJieQi()
            translated_jieqi = f"{solar_terms_translation.get(jieqi, jieqi)} / {jieqi}" if jieqi else "None"

            zodiac_char = lunar_c.getYearShengXiao()
            zodiac_animal = f"{zodiac_char} / {animals_translation.get(zodiac_char, zodiac_char)}"

            return {
                "lunar_date": {
                    "year": lunar_c.getYear(),
                    "month": month_num,
                    "day": lunar_c.getDay(),
                    "is_leap": is_leap,
                    "formatted": lunar_c.toFullString(),
                },
                "zodiac_animal": zodiac_animal,
                "bazi": {
                    "year": translate_pillar(bazi.getYear(), bazi.getYearWuXing()),
                    "month": translate_pillar(bazi.getMonth(), bazi.getMonthWuXing()),
                    "day": translate_pillar(bazi.getDay(), bazi.getDayWuXing()),
                    "hour": translate_pillar(bazi.getTime(), bazi.getTimeWuXing()),
                },
                "shichen": {
                    "branch": shichen_branches[shichen_idx],
                    "name": shichen_names[shichen_idx],
                    "index": shichen_idx,
                },
                "solar_term": translated_jieqi,
            }
        except ImportError:
            # Fallback in case dependencies are not installed
            # Calculate simple mathematical stem/branch approximation using Julian Date
            jd = self.get_julian_day(dt)
            stems = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
            branches = [
                "Zi (Rat)",
                "Chou (Ox)",
                "Yin (Tiger)",
                "Mao (Rabbit)",
                "Chen (Dragon)",
                "Si (Snake)",
                "Wu (Horse)",
                "Wei (Goat)",
                "Shen (Monkey)",
                "You (Rooster)",
                "Xu (Dog)",
                "Hai (Pig)",
            ]

            # Stems and branches relative offset
            year_offset = (dt.year - 4) % 60
            year_stem = stems[year_offset % 10]
            year_branch = branches[year_offset % 12]

            # Approximate Solar Term based on Sun longitude
            # Solar terms are every 15 degrees of sun longitude starting from 0 (Spring Equinox)
            sun_pos, _ = swe.calc_ut(jd, swe.SUN)
            sun_lon = sun_pos[0]

            solar_terms = [
                "Chunfen (Spring Equinox)",
                "Qingming",
                "Guyu",
                "Lixia (Start of Summer)",
                "Xiaoman",
                "Mangzhong",
                "Xiazhi (Summer Solstice)",
                "Xiaoshu",
                "Dashu",
                "Liqiu (Start of Autumn)",
                "Chushu",
                "Bailu",
                "Qiufen (Autumn Equinox)",
                "Hanlu",
                "Shuangjiang",
                "Lidong (Start of Winter)",
                "Xiaoxue",
                "Daxue",
                "Dongzhi (Winter Solstice)",
                "Xiaohan",
                "Dahan",
                "Lichun (Start of Spring)",
                "Yushui",
                "Jingzhe",
            ]
            term_idx = int(sun_lon / 15) % 24

            return {
                "lunar_date": {
                    "year": dt.year,
                    "month": 1,
                    "day": 1,
                    "is_leap": False,
                    "formatted": f"Approximate Year {dt.year} (Offline Fallback)",
                },
                "zodiac_animal": branches[(dt.year - 4) % 12].split()[0],
                "bazi": {"year": f"{year_stem}-{year_branch}", "month": "Unknown", "day": "Unknown", "hour": "Unknown"},
                "shichen": {"branch": "Unknown", "name": "Unknown", "index": 0},
                "solar_term": solar_terms[term_idx],
            }

    # =========================================================================
    # AUXILIARY FUNCTIONS
    # =========================================================================

    def get_moon_phase(self, dt: datetime) -> dict:
        """Calculate the current moon phase.

        Computes the angular separation between Sun and Moon and derives
        phase name, percent illumination, and boolean flags for new/full moon.

        Args:
            dt: Datetime for the calculation.

        Returns:
            dict: ``{phase_name, illumination (0-100), phase_angle (0-360),
            is_new_moon, is_full_moon}``
        """
        jd = self.get_julian_day(dt)

        sun_pos = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_pos = swe.calc_ut(jd, swe.MOON)[0][0]

        phase_angle = (moon_pos - sun_pos) % 360
        illumination = (1 - math.cos(math.radians(phase_angle))) / 2 * 100

        if phase_angle < 45:
            phase_name = "New Moon"
        elif phase_angle < 90:
            phase_name = "Waxing Crescent"
        elif phase_angle < 135:
            phase_name = "First Quarter"
        elif phase_angle < 180:
            phase_name = "Waxing Gibbous"
        elif phase_angle < 225:
            phase_name = "Full Moon"
        elif phase_angle < 270:
            phase_name = "Waning Gibbous"
        elif phase_angle < 315:
            phase_name = "Last Quarter"
        else:
            phase_name = "Waning Crescent"

        return {
            "phase_name": phase_name,
            "illumination": illumination,
            "phase_angle": phase_angle,
            "is_new_moon": abs(phase_angle) < 5 or abs(phase_angle - 360) < 5,
            "is_full_moon": abs(phase_angle - 180) < 5,
        }

    def get_lunar_mansion(self, dt: datetime) -> dict:
        """Calculate the current Nakshatra (Vedic lunar mansion).

        Uses Lahiri ayanamsa for the sidereal Moon position, then maps it
        to one of the 27 traditional nakshatras.

        Args:
            dt: Datetime for the calculation.

        Returns:
            dict: ``{number (1-27), name, moon_position (sidereal degrees)}``
        """
        jd = self.get_julian_day(dt)

        swe.set_sid_mode(swe.SIDM_LAHIRI)
        swe.get_ayanamsa_ut(jd)

        result = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
        sidereal_moon_pos = result[0][0]

        nakshatra_num = int(sidereal_moon_pos / (360 / 27))

        NAKSHATRAS = [
            "Ashwini",
            "Bharani",
            "Krittika",
            "Rohini",
            "Mrigashira",
            "Ardra",
            "Punarvasu",
            "Pushya",
            "Ashlesha",
            "Magha",
            "Purva Phalguni",
            "Uttara Phalguni",
            "Hasta",
            "Chitra",
            "Swati",
            "Vishakha",
            "Anuradha",
            "Jyeshtha",
            "Mula",
            "Purva Ashadha",
            "Uttara Ashadha",
            "Shravana",
            "Dhanishta",
            "Shatabhisha",
            "Purva Bhadrapada",
            "Uttara Bhadrapada",
            "Revati",
        ]

        return {"number": nakshatra_num + 1, "name": NAKSHATRAS[nakshatra_num % 27], "moon_position": sidereal_moon_pos}

    def calculate_auspicious_times(self, date: datetime, location: tuple[float, float]) -> dict:
        """Calculate sunrise, sunset, solar noon, and Brahma Muhurta.

        Brahma Muhurta is the 96-minute period before sunrise, traditionally
        considered the most auspicious time for meditation and spiritual practice.

        Args:
            date: Datetime for the calculation.
            location: ``(latitude, longitude)`` tuple in decimal degrees.

        Returns:
            dict: ``{sunrise, sunset, noon, brahma_muhurta, location}``.
                Times are timezone-aware datetimes (or None for polar regions).
        """
        lat, lon = location
        jd = self.get_julian_day(date)

        # Swiss Ephemeris sunrise and sunset
        rise_result = swe.rise_trans(jd, swe.SUN, swe.CALC_RISE, [lon, lat, 0])
        set_result = swe.rise_trans(jd, swe.SUN, swe.CALC_SET, [lon, lat, 0])

        def jd_to_datetime(jd_time):
            result = swe.revjul(jd_time)
            # Create UTC timezone aware object
            dt_utc = datetime(
                result[0], result[1], result[2], int(result[3]), int((result[3] % 1) * 60), tzinfo=pytz.UTC
            )
            # Convert to local timezone of the input date
            if date.tzinfo:
                return dt_utc.astimezone(date.tzinfo)
            return dt_utc

        sunrise = jd_to_datetime(rise_result[1][0]) if rise_result[0] >= 0 else None
        sunset = jd_to_datetime(set_result[1][0]) if set_result[0] >= 0 else None

        # Brahma Muhurta (96 minutes before sunrise)
        brahma_muhurta = sunrise - timedelta(minutes=96) if sunrise else None

        # Solar noon
        if sunrise and sunset:
            noon = sunrise + (sunset - sunrise) / 2
        else:
            noon = None

        return {
            "sunrise": sunrise,
            "sunset": sunset,
            "noon": noon,
            "brahma_muhurta": brahma_muhurta,
            "location": {"latitude": lat, "longitude": lon},
        }

    def calculate_exact_planetary_hours(self, dt: datetime, location: tuple[float, float]) -> dict:
        """
        Calculate the exact planetary hour based on local sunrise and sunset.
        Returns the active ruler, remaining time, and full list for the day/night.
        """
        times = self.calculate_auspicious_times(dt, location)
        sunrise = times.get("sunrise")
        sunset = times.get("sunset")

        if not sunrise or not sunset:
            # Fallback if polar day/night where sunrise/sunset doesn't occur
            return {"current_planetary_hour": "Sun", "is_daytime": True, "description": "Polar day/night fallback"}

        # Determine day of week ruler (traditional weekday begins at sunrise)
        if dt < sunrise:
            # Before sunrise, we use previous day's weekday ruler
            logical_date = dt - timedelta(days=1)
        else:
            logical_date = dt

        weekday_idx = logical_date.weekday()  # Monday=0
        day_ruler = self.WEEKDAY_RULERS[weekday_idx]

        # Determine if it is currently daytime or nighttime
        is_daytime = sunrise <= dt < sunset

        if is_daytime:
            # Day hours: split sunrise to sunset into 12 periods
            hour_duration = (sunset - sunrise) / 12
            seconds_elapsed = (dt - sunrise).total_seconds()
            hour_idx = min(int(seconds_elapsed / hour_duration.total_seconds()), 11)
            time_remaining = (sunrise + hour_duration * (hour_idx + 1)) - dt
            start_time = sunrise + hour_duration * hour_idx
            end_time = sunrise + hour_duration * (hour_idx + 1)
        else:
            # Night hours: split sunset to next sunrise into 12 periods
            # Find next sunrise
            next_day_times = self.calculate_auspicious_times(dt + timedelta(days=1), location)
            next_sunrise = next_day_times.get("sunrise")

            if dt >= sunset:
                prev_sunset = sunset
            else:
                # Before today's sunrise, night started yesterday
                prev_day_times = self.calculate_auspicious_times(dt - timedelta(days=1), location)
                prev_sunset = prev_day_times.get("sunset")
                next_sunrise = sunrise

            hour_duration = (next_sunrise - prev_sunset) / 12
            seconds_elapsed = (dt - prev_sunset).total_seconds()
            hour_idx = min(int(seconds_elapsed / hour_duration.total_seconds()), 11)
            time_remaining = (prev_sunset + hour_duration * (hour_idx + 1)) - dt
            start_time = prev_sunset + hour_duration * hour_idx
            end_time = prev_sunset + hour_duration * (hour_idx + 1)

        # Calculate Chaldean order starting index
        start_ruler_idx = self.CHALDEAN_ORDER.index(day_ruler)

        # Calculate hourly rulers
        day_rulers = [self.CHALDEAN_ORDER[(start_ruler_idx + i) % 7] for i in range(12)]
        night_rulers = [self.CHALDEAN_ORDER[(start_ruler_idx + 12 + i) % 7] for i in range(12)]

        current_ruler = day_rulers[hour_idx] if is_daytime else night_rulers[hour_idx]

        descriptions = {
            "Sun": "Vitality, consciousness, identity, career and leadership.",
            "Moon": "Emotions, intuition, subconscious habits, nurturing.",
            "Mercury": "Communication, learning, trading, technical planning.",
            "Venus": "Love, arts, relationship harmony, beauty and comfort.",
            "Mars": "Action, courage, conflict resolution, physical exertion.",
            "Jupiter": "Expansion, wisdom teachings, abundance, spirituality.",
            "Saturn": "Discipline, structural building, boundaries, karmic meditation.",
        }

        return {
            "status": "success",
            "current_planetary_hour": current_ruler,
            "day_planet": day_ruler,
            "hour_index": hour_idx + 1,  # 1-12
            "is_daytime": is_daytime,
            "time_remaining_seconds": int(time_remaining.total_seconds()),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": descriptions.get(current_ruler, ""),
            "day_rulers": day_rulers,
            "night_rulers": night_rulers,
            "day_of_week": dt.strftime("%A"),
            "hour_of_day": dt.hour,
        }

    def get_current_energetics(self, dt: datetime = None, location: tuple[float, float] = None) -> dict:
        """Quick snapshot of current astrological energetics.

        Aggregates moon phase, lunar mansion, planetary positions, and
        (if location is provided) auspicious times into a single dict.

        Args:
            dt: Datetime (defaults to ``datetime.now(pytz.UTC)``).
            location: Optional ``(latitude, longitude)`` tuple.

        Returns:
            dict: ``{datetime, moon_phase, lunar_mansion, planetary_positions,
            [auspicious_times]}``
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)

        result = {
            "datetime": dt.isoformat(),
            "moon_phase": self.get_moon_phase(dt),
            "lunar_mansion": self.get_lunar_mansion(dt),
            "planetary_positions": self.get_planetary_positions(dt, location),
        }

        if location:
            result["auspicious_times"] = self.calculate_auspicious_times(dt, location)

        return result

    def get_comprehensive_astrology(self, dt: datetime = None, location: tuple[float, float] = None) -> dict:
        """Compute consolidated astrology across all three systems.

        This is the primary entry point — it aggregates Western, Indian (Vedic),
        Chinese, and planetary hour data into one response dict.

        Args:
            dt: Datetime (defaults to now in UTC; naive datetimes are localised to UTC).
            location: ``(latitude, longitude)`` tuple (defaults to San Francisco
                if not provided).

        Returns:
            dict: ``{datetime, location, western, indian, chinese, planetary_hours}``
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        # Default to San Francisco coordinates if location is not provided
        loc = location if location else (37.7749, -122.4194)

        western = self.get_western_astrology(dt, loc)
        indian = self.get_indian_astrology(dt, loc)
        chinese = self.get_chinese_astrology(dt)
        planetary_hours = self.calculate_exact_planetary_hours(dt, loc)

        return {
            "datetime": dt.isoformat(),
            "location": {"latitude": loc[0], "longitude": loc[1]},
            "western": western,
            "indian": indian,
            "chinese": chinese,
            "planetary_hours": planetary_hours,
        }

    def recommend_frequencies_for_time(self, dt: datetime = None) -> list[float]:
        """Recommend audio frequencies based on current astrological conditions.

        Always includes Schumann (7.83 Hz) and OM (136.1 Hz). Adds:
        - Full moon: Moon frequency (210.42) + connection (639).
        - New moon: release (396) + new beginnings (417).
        - Otherwise: transformation (528).
        - Venus/Jupiter at critical degrees: adds planetary frequencies.

        Args:
            dt: Datetime (defaults to now in UTC).

        Returns:
            list[float]: Up to 7 recommended frequencies.
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)

        frequencies = []
        moon_phase = self.get_moon_phase(dt)

        # Base frequencies always included: Schumann + OM
        frequencies.extend([7.83, 136.1])

        # Moon phase specific
        if moon_phase["is_full_moon"]:
            frequencies.extend([210.42, 639])  # Moon frequency + connection
        elif moon_phase["is_new_moon"]:
            frequencies.extend([396, 417])  # Release + new beginnings
        else:
            frequencies.append(528)  # Transformation

        # Planetary positions
        positions = self.get_planetary_positions(dt)

        # Add planetary frequencies based on prominence
        if positions["venus"]["degree"] < 5 or positions["venus"]["degree"] > 25:
            frequencies.append(221.23)  # Venus frequency

        if positions["jupiter"]["degree"] < 5 or positions["jupiter"]["degree"] > 25:
            frequencies.append(183.58)  # Jupiter frequency

        return frequencies[:7]  # Return up to 7 frequencies

    def get_dharma_calendar_events(self, dt: datetime) -> list[str]:
        """Check for significant dharma calendar events.

        Detects full moons, new moons, and eclipse proximity (Sun within
        10° of the lunar nodes).

        Args:
            dt: Datetime to check.

        Returns:
            list[str]: Human-readable event descriptions (may be empty).
        """
        events = []
        moon_phase = self.get_moon_phase(dt)

        if moon_phase["is_full_moon"]:
            events.append("Full Moon - Auspicious for completion, purification and dedication")

        if moon_phase["is_new_moon"]:
            events.append("New Moon - Auspicious for setting new intentions and seeds")

        # Check for eclipses (sun or moon near nodes)
        positions = self.get_planetary_positions(dt)
        sun_long = positions["sun"]["longitude"]
        node_long = positions["north_node"]["longitude"]

        if abs(sun_long - node_long) < 10 or abs(sun_long - node_long - 180) < 10:
            events.append("Near Eclipse Point - Intense karmic transformation phase")

        return events

    def calculate_chart(self, date: datetime, lat: float, lon: float, name: str = "") -> dict:
        """Compatibility wrapper for :class:`~core.outlook_generator.OutlookGenerator`.

        Delegates to :meth:`get_comprehensive_astrology`.

        Args:
            date: Datetime for the chart.
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.
            name: Optional chart name (unused; accepted for API compatibility).

        Returns:
            dict: Same as :meth:`get_comprehensive_astrology`.
        """
        return self.get_comprehensive_astrology(date, (lat, lon))

    def get_transits(self, natal_chart: dict = None, transit_date: datetime = None) -> list[dict]:
        """Compatibility wrapper for :class:`~core.outlook_generator.OutlookGenerator`.

        Extracts aspects from a natal chart's Western astrology data.

        Args:
            natal_chart: Dict with a ``"western"`` key (as returned by
                :meth:`get_comprehensive_astrology`).
            transit_date: Unused; accepted for API compatibility.

        Returns:
            list[dict]: Aspect list from the natal chart, or empty list.
        """
        if natal_chart and "western" in natal_chart:
            return natal_chart["western"].get("aspects", [])
        return []

    def get_transits_to_natal(
        self, natal_dt: datetime, natal_location: tuple[float, float], transit_dt: datetime = None
    ) -> list[dict]:
        """Compare current or specific transit planetary positions to natal positions.
        Returns transiting planets aspecting natal planets with orbs, aspect types, and descriptions."""
        if transit_dt is None:
            transit_dt = datetime.now(pytz.UTC)
            
        natal_positions = self.get_planetary_positions(natal_dt, natal_location)
        transit_positions = self.get_planetary_positions(transit_dt, natal_location)
        
        # Add Ascendant, MC, and 12 house cusps for natal if location is provided
        jd_natal = self.get_julian_day(natal_dt)
        if natal_location:
            lat, lon = natal_location
            houses, ascmc = swe.houses(jd_natal, lat, lon, b"P")
            natal_positions["ascendant"] = {
                "longitude": ascmc[0],
                "sign": self.SIGNS[int(ascmc[0] / 30) % 12],
                "degree": ascmc[0] % 30
            }
            natal_positions["midheaven"] = {
                "longitude": ascmc[1],
                "sign": self.SIGNS[int(ascmc[1] / 30) % 12],
                "degree": ascmc[1] % 30
            }
            for i in range(12):
                cusp_lon = houses[i]
                natal_positions[f"house_{i + 1}"] = {
                    "longitude": cusp_lon,
                    "sign": self.SIGNS[int(cusp_lon / 30) % 12],
                    "degree": cusp_lon % 30,
                }
            
        aspect_types = [
            {"name": "Conjunction", "angle": 0, "orb": 8},
            {"name": "Sextile", "angle": 60, "orb": 6},
            {"name": "Square", "angle": 90, "orb": 8},
            {"name": "Trine", "angle": 120, "orb": 8},
            {"name": "Opposition", "angle": 180, "orb": 8},
        ]
        
        aspects = []
        for t_name, t_pos in transit_positions.items():
            for n_name, n_pos in natal_positions.items():
                if t_name == "north_node" and n_name == "north_node":
                    continue
                
                t_lon = t_pos["longitude"]
                n_lon = n_pos["longitude"]
                
                diff = abs(t_lon - n_lon) % 360
                distance = min(diff, 360 - diff)
                
                for asp in aspect_types:
                    if abs(distance - asp["angle"]) <= asp["orb"]:
                        exactness = 1.0 - (abs(distance - asp["angle"]) / asp["orb"])
                        orb = abs(distance - asp["angle"])
                        aspects.append({
                            "transit_planet": t_name,
                            "natal_planet": n_name,
                            "aspect": asp["name"],
                            "angle": distance,
                            "orb": round(orb, 2),
                            "exactness": round(exactness, 2),
                            "description": f"Transit {t_name.title()} {asp['name']} Natal {n_name.title()} (Orb: {orb:.2f}°)"
                        })
                        
        return aspects

    def get_vedic_gochara(self, natal_dt: datetime, natal_location: tuple[float, float], transit_dt: datetime = None) -> dict:
        """Calculate Vedic Gochara (Transit planets relative to natal Moon Rashi)"""
        if transit_dt is None:
            transit_dt = datetime.now(pytz.UTC)
            
        natal_vedic = self.get_indian_astrology(natal_dt, natal_location)
        transit_vedic = self.get_indian_astrology(transit_dt, natal_location)
        
        natal_moon_rashi = natal_vedic["sidereal_positions"]["moon"]["rashi_number"]
        
        gochara = {}
        for planet, pos in transit_vedic["sidereal_positions"].items():
            if planet == "ascendant":
                continue
            transit_rashi = pos["rashi_number"]
            gochara_house = ((transit_rashi - natal_moon_rashi + 12) % 12) + 1
            gochara[planet] = {
                "transit_rashi": pos["rashi"],
                "transit_degree": pos["degree"],
                "gochara_house": gochara_house,
                "formatted": f"House {gochara_house} from Moon ({pos['rashi_name']})"
            }
        return gochara

    def calculate_vimshottari_dasha(self, birth_dt: datetime, location: tuple[float, float]) -> list[dict]:
        """Calculate Vimshottari Dasha periods for a birth chart."""
        vedic = self.get_indian_astrology(birth_dt, location)
        moon_lon = vedic["sidereal_positions"]["moon"]["longitude"]
        
        nak_width = 360.0 / 27.0
        nak_idx = int(moon_lon / nak_width)
        nak_progress = (moon_lon % nak_width) / nak_width
        
        dasha_order = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        dasha_years = {
            "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10,
            "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
        }
        
        first_dasha_idx = nak_idx % 9
        first_dasha_ruler = dasha_order[first_dasha_idx]
        first_dasha_total = dasha_years[first_dasha_ruler]
        
        remaining_ratio = 1.0 - nak_progress
        first_dasha_remaining = first_dasha_total * remaining_ratio
        
        current_time = birth_dt
        dashas = []
        
        first_end = current_time + timedelta(days=first_dasha_remaining * 365.25)
        dashas.append({
            "ruler": first_dasha_ruler,
            "start": current_time.isoformat(),
            "end": first_end.isoformat(),
            "duration_years": first_dasha_total,
            "remaining_years_at_birth": round(first_dasha_remaining, 2)
        })
        current_time = first_end
        
        idx = (first_dasha_idx + 1) % 9
        for _ in range(9):
            ruler = dasha_order[idx]
            duration = dasha_years[ruler]
            end_time = current_time + timedelta(days=duration * 365.25)
            dashas.append({
                "ruler": ruler,
                "start": current_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_years": duration,
                "remaining_years_at_birth": 0.0
            })
            current_time = end_time
            idx = (idx + 1) % 9
            
        return dashas

    def compare_bazi_transits(self, natal_dt: datetime, transit_dt: datetime = None) -> dict:
        """Compare transit BaZi pillars against natal BaZi pillars for clashes and harmonies."""
        if transit_dt is None:
            transit_dt = datetime.now(pytz.UTC)
            
        natal_chinese = self.get_chinese_astrology(natal_dt)
        transit_chinese = self.get_chinese_astrology(transit_dt)
        
        def extract_sb(pillar_str):
            if "/" in pillar_str:
                clean = pillar_str.split("/")[1].split(" ")[0]
                parts = clean.split("-")
                return parts[0], parts[1]
            return "Unknown", "Unknown"
            
        n_y_s, n_y_b = extract_sb(natal_chinese["bazi"]["year"])
        n_m_s, n_m_b = extract_sb(natal_chinese["bazi"]["month"])
        n_d_s, n_d_b = extract_sb(natal_chinese["bazi"]["day"])
        n_h_s, n_h_b = extract_sb(natal_chinese["bazi"]["hour"])
        
        t_y_s, t_y_b = extract_sb(transit_chinese["bazi"]["year"])
        t_m_s, t_m_b = extract_sb(transit_chinese["bazi"]["month"])
        t_d_s, t_d_b = extract_sb(transit_chinese["bazi"]["day"])
        t_h_s, t_h_b = extract_sb(transit_chinese["bazi"]["hour"])
        
        clash_map = {
            "Zi": "Wu", "Wu": "Zi",
            "Chou": "Wei", "Wei": "Chou",
            "Yin": "Shen", "Shen": "Yin",
            "Mao": "You", "You": "Mao",
            "Chen": "Xu", "Xu": "Chen",
            "Si": "Hai", "Hai": "Si"
        }
        
        harmony_map = {
            "Zi": "Chou", "Chou": "Zi",
            "Yin": "Hai", "Hai": "Yin",
            "Mao": "Xu", "Xu": "Mao",
            "Chen": "You", "You": "Chen",
            "Si": "Shen", "Shen": "Si",
            "Wu": "Wei", "Wei": "Wu"
        }
        
        interactions = []
        # 1. Same-type pillar pair checks: transit branch vs natal branch of same pillar
        pillar_pairs = [
            ("Year-Year", t_y_b, n_y_b),
            ("Month-Month", t_m_b, n_m_b),
            ("Day-Day", t_d_b, n_d_b),
            ("Hour-Hour", t_h_b, n_h_b),
        ]
        for pair_label, t_branch, n_branch in pillar_pairs:
            if t_branch == "Unknown" or n_branch == "Unknown":
                continue
            pillar_name = pair_label.split("-")[0]
            if clash_map.get(t_branch) == n_branch:
                interactions.append({
                    "pillar": pair_label,
                    "type": "Clash",
                    "description": f"Transit {pillar_name} branch {t_branch} CLASHES with Natal {pillar_name} branch {n_branch}. Dynamic change, potential conflict or breakthrough."
                })
            elif harmony_map.get(t_branch) == n_branch:
                interactions.append({
                    "pillar": pair_label,
                    "type": "Harmony",
                    "description": f"Transit {pillar_name} branch {t_branch} COMBINES with Natal {pillar_name} branch {n_branch}. Harmonious support, cooperation, and stability."
                })

        # 2. Cross-pillar: Transit Day branch (self) impacts all natal pillars
        for label, n_branch in [("Year (Sheng Xiao)", n_y_b), ("Month", n_m_b), ("Hour", n_h_b)]:
            if n_branch == "Unknown" or t_d_b == "Unknown":
                continue
            if clash_map.get(t_d_b) == n_branch:
                interactions.append({
                    "pillar": f"Day→{label}",
                    "type": "Clash",
                    "description": f"Transit Day branch {t_d_b} CLASHES with Natal {label} branch {n_branch}. Dynamic change, potential conflict or breakthrough."
                })
            elif harmony_map.get(t_d_b) == n_branch:
                interactions.append({
                    "pillar": f"Day→{label}",
                    "type": "Harmony",
                    "description": f"Transit Day branch {t_d_b} COMBINES with Natal {label} branch {n_branch}. Harmonious support, cooperation, and stability."
                })
                
        return {
            "transit_day_pillar": transit_chinese["bazi"]["day"].split(" ")[0] if "/" in transit_chinese["bazi"]["day"] else transit_chinese["bazi"]["day"],
            "natal_day_pillar": natal_chinese["bazi"]["day"].split(" ")[0] if "/" in natal_chinese["bazi"]["day"] else natal_chinese["bazi"]["day"],
            "interactions": interactions
        }



AstrologyEngine = AstrologicalCalculator

if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    astro = AstrologicalCalculator()
    now = datetime.now(pytz.UTC)
    sf = (37.7749, -122.4194)
    print("Testing Comprehensive Astrology System...")
    data = astro.get_comprehensive_astrology(now, sf)
    print(f"Western Dominant Element: {data['western']['dominant_element']}")
    print(f"Vedic Nakshatra: {data['indian']['panchanga']['nakshatra']['name']}")
    print(f"Chinese Animal: {data['chinese']['zodiac_animal']} - {data['chinese']['lunar_date']['formatted']}")
    print(f"Planetary Hour: {data['planetary_hours']['current_planetary_hour']}")
