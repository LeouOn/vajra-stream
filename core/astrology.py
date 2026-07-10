"""
Vajra.Stream Astrology Module
Comprehensive time-space calculations for Western, Indian (Vedic), and Chinese systems.
Uses Swiss Ephemeris and lunar-python for precise, offline-first calculations.
"""

__version__ = "1.0.0"

import logging
import math
from datetime import datetime, timedelta

import pytz
import swisseph as swe

logger = logging.getLogger(__name__)


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
            }
            if cusps is not None
            else {},
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
    # MIDPOINTS + ANTISCIA (90°-WHEEL SYMMETRY TECHNIQUES)
    # =========================================================================

    def get_midpoints(
        self,
        dt: datetime,
        location: tuple[float, float] | None = None,
        orb: float = 1.5,
    ) -> dict:
        """Compute the midpoint of every unique pair of the 10 natal planets.

        A midpoint is the halfway point between two planetary longitudes on
        the 360° wheel. The 10 classical planets give ``10 choose 2 = 45``
        unique unordered pairs. Each pair key is alphabetically sorted
        (e.g. ``mercury_sun`` not ``sun_mercury``) so the output is
        stable and deterministic.

        The midpoint is computed on the *shorter arc* of the circle when the
        two planets are more than 180° apart. Concretely:

            midpoint = (P1.lon + P2.lon) / 2  (mod 360)

        with the two values averaged around the wheel. When ``abs(d) <= 180``,
        the midpoint is just the arithmetic mean. When ``abs(d) > 180``, the
        midpoint flips to the opposite arc — which the ``(P1 + P2) / 2``
        formula already handles correctly because the mod-360 wrap-around
        puts it on the shorter arc.

        Args:
            dt: Datetime for the chart (timezone-aware recommended).
            location: Optional ``(latitude, longitude)`` tuple. Currently
                unused for midpoint computation (it only affects house
                cusps, which we don't use here). Accepted for API symmetry
                with the rest of the calculator.
            orb: Aspect orb in degrees. Reserved for future "which planet
                is aspecting this midpoint" work. Not applied in v1.

        Returns:
            dict: ``{pair_key: {"sign": str, "degree": float,
            "exact_longitude": float}, ...}`` for all 45 unique planet
            pairs. ``pair_key`` is ``f"{p1}_{p2}"`` with ``p1 < p2``
            alphabetically.
        """
        planets = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]

        positions = self.get_planetary_positions(dt, location)
        longitudes = {p: positions[p]["longitude"] for p in planets}

        midpoints: dict = {}
        for i, p1 in enumerate(planets):
            for p2 in planets[i + 1 :]:
                a, b = sorted([p1, p2])
                lon1 = longitudes[a]
                lon2 = longitudes[b]
                midpoint_lon = (lon1 + lon2) / 2.0
                midpoint_lon = midpoint_lon % 360.0

                sign_idx = int(midpoint_lon // 30) % 12
                midpoints[f"{a}_{b}"] = {
                    "sign": self.SIGNS[sign_idx],
                    "degree": midpoint_lon % 30,
                    "exact_longitude": midpoint_lon,
                }

        return midpoints

    def get_antiscia(
        self,
        dt: datetime,
        location: tuple[float, float] | None = None,
    ) -> dict:
        """Compute the antiscion and contrantiscion of each of the 10 planets.

        Antiscia and contrantiscia are "mirror" points on the zodiac wheel:

          * **Antiscion**: the point equidistant from the planet, mirrored
            across the Cancer/Capricorn solstice axis (0° Cancer / 0°
            Capricorn, i.e. the 90° / 270° wheel positions). Formula:
            ``antiscion = (180 - lon) mod 360``.
          * **Contrantiscion**: the point equidistant from the planet,
            mirrored across the Aries/Libra equinox axis (0° Aries / 0°
            Libra, i.e. the 0° / 180° wheel positions). Formula:
            ``contrantiscion = (-lon) mod 360`` = ``(360 - lon) mod 360``.

        Two planets are "in antiscion" when one's antiscion equals the
        other's longitude (treated like a soft conjunction in traditional
        astrology). The 10 classical planets are returned, with the
        antiscion + contrantiscion of each, so downstream code can do the
        conjunction check without recomputing the mirrors.

        Args:
            dt: Datetime for the chart (timezone-aware recommended).
            location: Optional ``(latitude, longitude)`` tuple. Unused for
                antiscia/contrantiscia (they're pure longitude
                transformations). Accepted for API symmetry.

        Returns:
            dict: ``{planet_name: {"antiscion": {...}, "contrantiscion":
            {...}}, ...}`` for the 10 planets. Each nested object has
            ``sign`` (str), ``degree`` (float, 0-30), and
            ``exact_longitude`` (float, 0-360).
        """
        planets = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]

        positions = self.get_planetary_positions(dt, location)

        def _lon_to_sign_degree(lon: float) -> dict:
            lon = lon % 360.0
            sign_idx = int(lon // 30) % 12
            return {
                "sign": self.SIGNS[sign_idx],
                "degree": lon % 30,
                "exact_longitude": lon,
            }

        result: dict = {}
        for p in planets:
            lon = positions[p]["longitude"]
            antiscion_lon = (180.0 - lon) % 360.0
            contrantiscion_lon = (-lon) % 360.0
            result[p] = {
                "antiscion": _lon_to_sign_degree(antiscion_lon),
                "contrantiscion": _lon_to_sign_degree(contrantiscion_lon),
            }

        return result

    # =========================================================================
    # FIXED STARS (5 ROYAL STARS + SPICA + SIRIUS, with precession + conjunctions)
    # =========================================================================

    FIXED_STARS = {
        "regulus": {
            "name": "Regulus",
            "longitude_2000": 149.83,
            "constellation": "Leo",
            "nature": "Mars/Jupiter",
        },
        "aldebaran": {
            "name": "Aldebaran",
            "longitude_2000": 69.83,
            "constellation": "Taurus",
            "nature": "Mars",
        },
        "antares": {
            "name": "Antares",
            "longitude_2000": 249.83,
            "constellation": "Scorpio",
            "nature": "Mars/Jupiter",
        },
        "fomalhaut": {
            "name": "Fomalhaut",
            "longitude_2000": 333.83,
            "constellation": "Pisces",
            "nature": "Venus/Mercury",
        },
        "spica": {
            "name": "Spica",
            "longitude_2000": 203.83,
            "constellation": "Virgo",
            "nature": "Venus/Mars",
        },
        "algol": {
            "name": "Algol",
            "longitude_2000": 56.0,
            "constellation": "Taurus",
            "nature": "Saturn/Mars",
        },
        "sirius": {
            "name": "Sirius",
            "longitude_2000": 104.06,
            "constellation": "Canis Major",
            "nature": "Jupiter/Mars",
        },
    }

    def get_fixed_stars(
        self,
        dt: datetime,
        location: tuple[float, float] | None = None,
        orb: float = 1.0,
    ) -> dict:
        """Compute the positions and conjunctions of the 7 curated fixed stars.

        Returns the four royal stars of Persia (Regulus, Aldebaran, Antares,
        Fomalhaut), plus Spica, Algol, and Sirius. These are the most
        requested fixed stars in classical and medieval astrology.

        Each star's J2000.0 longitude is precession-adjusted to the chart
        date using the simplified tropical-rate formula:

            ``lon_t = lon_2000 + 0.01397 * (year - 2000)``

        where ``0.01397`` deg/yr is the standard precession rate of
        ~50.3 arcseconds/year expressed in degrees. This is accurate to
        better than 0.1 degree across 1900-2100 — well inside the orb
        used for fixed-star work.

        For each star we then find the nearest of the 10 natal planets and
        report the absolute orb. If that orb is within the user-supplied
        ``orb`` argument, the star is flagged as conjunct and the
        ``conjunct_planet`` field carries the planet name; otherwise
        ``conjunct_planet`` is ``None``.

        Args:
            dt: Datetime for the chart (timezone-aware recommended).
            location: Optional ``(latitude, longitude)`` tuple. Accepted
                for API symmetry with the rest of the calculator but
                unused — fixed-star longitudes are independent of the
                observer's location on Earth.
            orb: Conjunction orb in degrees (default ``1.0``). Stars
                within this many degrees of a natal planet are marked
                conjunct. Practical orbs are typically 0.5-2.0; the
                Royal Stars are usually worked at 1 degree.

        Returns:
            dict: ``{star_key: {"name", "sign", "degree",
            "exact_longitude", "constellation", "nature",
            "orb_to_nearest_planet", "conjunct_planet"}, ...}`` for
            the 7 fixed stars. ``conjunct_planet`` is the planet name
            when ``orb_to_nearest_planet <= orb``, else ``None``.

        Notes:
            Parans (in-paran with horizon/MC) are NOT computed in v1 —
            they require simultaneous culminations and are deferred.
        """
        if dt.tzinfo is not None:
            dt_utc = dt.astimezone(pytz.UTC)
        else:
            dt_utc = dt
        year = dt_utc.year

        positions = self.get_planetary_positions(dt, location)
        planet_lons = {p: positions[p]["longitude"] for p in positions}

        def _lon_to_sign_degree_fs(lon: float) -> dict:
            lon = lon % 360.0
            sign_idx = int(lon // 30) % 12
            return {
                "sign": self.SIGNS[sign_idx],
                "degree": lon % 30,
                "exact_longitude": lon,
            }

        result: dict = {}
        for key, star in self.FIXED_STARS.items():
            base = star["longitude_2000"]
            adjusted_lon = (base + 0.01397 * (year - 2000)) % 360.0
            lon_info = _lon_to_sign_degree_fs(adjusted_lon)

            nearest_planet = None
            nearest_orb = 360.0
            for pname, plon in planet_lons.items():
                diff = abs(adjusted_lon - plon) % 360.0
                distance = min(diff, 360.0 - diff)
                if distance < nearest_orb:
                    nearest_orb = distance
                    nearest_planet = pname

            conjunct_planet = nearest_planet if nearest_orb <= orb else None

            result[key] = {
                "name": star["name"],
                "sign": lon_info["sign"],
                "degree": lon_info["degree"],
                "exact_longitude": lon_info["exact_longitude"],
                "constellation": star["constellation"],
                "nature": star["nature"],
                "orb_to_nearest_planet": round(nearest_orb, 4),
                "conjunct_planet": conjunct_planet,
            }

        return result

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
            from lunar_python import Solar

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
            translated_jieqi = f"{solar_terms_translation.get(jieqi, jieqi)} / {jieqi}" if jieqi else None

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
            #
            # NOTE: this fallback produces bazi pillar strings WITHOUT the "/"
            # separator that ``compare_bazi_transits.extract_sb`` requires. Any
            # caller of ``compare_bazi_transits`` will therefore silently see an
            # empty ``interactions`` list when ``lunar_python`` is missing. We
            # log loudly here so deployments with a missing dependency are
            # diagnosable instead of producing mysteriously empty BaZi output.
            logger.warning(
                "lunar_python is not installed; falling back to approximate "
                "Chinese astrology. BaZi pillar format will be incomplete and "
                "compare_bazi_transits() will return no interactions. "
                "Install with: pip install lunar-python"
            )
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
                "degree": ascmc[0] % 30,
            }
            natal_positions["midheaven"] = {
                "longitude": ascmc[1],
                "sign": self.SIGNS[int(ascmc[1] / 30) % 12],
                "degree": ascmc[1] % 30,
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
                        # applying/separating: transit planet gaining on the
                        # exact aspect angle vs the natal target.
                        t_speed = t_pos.get("speed")
                        n_speed = n_pos.get("speed")
                        applying = None
                        if isinstance(t_speed, (int, float)) and isinstance(n_speed, (int, float)):
                            signed_delta = self._angular_delta_signed(t_lon, n_lon)
                            d_sep_dt = t_speed - n_speed
                            if signed_delta >= 0:
                                applying = d_sep_dt < 0
                            else:
                                applying = d_sep_dt > 0
                        aspects.append(
                            {
                                "transit_planet": t_name,
                                "natal_planet": n_name,
                                "aspect": asp["name"],
                                "angle": distance,
                                "orb": round(orb, 2),
                                "exactness": round(exactness, 2),
                                "applying": applying,
                                "description": f"Transit {t_name.title()} {asp['name']} Natal {n_name.title()} (Orb: {orb:.2f}°)",
                            }
                        )

        return aspects

    def get_vedic_gochara(
        self, natal_dt: datetime, natal_location: tuple[float, float], transit_dt: datetime = None
    ) -> dict:
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
                "formatted": f"House {gochara_house} from Moon ({pos['rashi_name']})",
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
            "Ketu": 7,
            "Venus": 20,
            "Sun": 6,
            "Moon": 10,
            "Mars": 7,
            "Rahu": 18,
            "Jupiter": 16,
            "Saturn": 19,
            "Mercury": 17,
        }

        first_dasha_idx = nak_idx % 9
        first_dasha_ruler = dasha_order[first_dasha_idx]
        first_dasha_total = dasha_years[first_dasha_ruler]

        remaining_ratio = 1.0 - nak_progress
        first_dasha_remaining = first_dasha_total * remaining_ratio

        current_time = birth_dt
        dashas = []

        first_end = current_time + timedelta(days=first_dasha_remaining * 365.25)
        dashas.append(
            {
                "ruler": first_dasha_ruler,
                "start": current_time.isoformat(),
                "end": first_end.isoformat(),
                "duration_years": first_dasha_total,
                "remaining_years_at_birth": round(first_dasha_remaining, 2),
            }
        )
        current_time = first_end

        idx = (first_dasha_idx + 1) % 9
        for _ in range(9):
            ruler = dasha_order[idx]
            duration = dasha_years[ruler]
            end_time = current_time + timedelta(days=duration * 365.25)
            dashas.append(
                {
                    "ruler": ruler,
                    "start": current_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_years": duration,
                    "remaining_years_at_birth": 0.0,
                }
            )
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
            "Zi": "Wu",
            "Wu": "Zi",
            "Chou": "Wei",
            "Wei": "Chou",
            "Yin": "Shen",
            "Shen": "Yin",
            "Mao": "You",
            "You": "Mao",
            "Chen": "Xu",
            "Xu": "Chen",
            "Si": "Hai",
            "Hai": "Si",
        }

        harmony_map = {
            "Zi": "Chou",
            "Chou": "Zi",
            "Yin": "Hai",
            "Hai": "Yin",
            "Mao": "Xu",
            "Xu": "Mao",
            "Chen": "You",
            "You": "Chen",
            "Si": "Shen",
            "Shen": "Si",
            "Wu": "Wei",
            "Wei": "Wu",
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
                interactions.append(
                    {
                        "pillar": pair_label,
                        "type": "Clash",
                        "description": f"Transit {pillar_name} branch {t_branch} CLASHES with Natal {pillar_name} branch {n_branch}. Dynamic change, potential conflict or breakthrough.",
                    }
                )
            elif harmony_map.get(t_branch) == n_branch:
                interactions.append(
                    {
                        "pillar": pair_label,
                        "type": "Harmony",
                        "description": f"Transit {pillar_name} branch {t_branch} COMBINES with Natal {pillar_name} branch {n_branch}. Harmonious support, cooperation, and stability.",
                    }
                )

        # 2. Cross-pillar: Transit Day branch (self) impacts all natal pillars
        for label, n_branch in [("Year (Sheng Xiao)", n_y_b), ("Month", n_m_b), ("Hour", n_h_b)]:
            if n_branch == "Unknown" or t_d_b == "Unknown":
                continue
            if clash_map.get(t_d_b) == n_branch:
                interactions.append(
                    {
                        "pillar": f"Day→{label}",
                        "type": "Clash",
                        "description": f"Transit Day branch {t_d_b} CLASHES with Natal {label} branch {n_branch}. Dynamic change, potential conflict or breakthrough.",
                    }
                )
            elif harmony_map.get(t_d_b) == n_branch:
                interactions.append(
                    {
                        "pillar": f"Day→{label}",
                        "type": "Harmony",
                        "description": f"Transit Day branch {t_d_b} COMBINES with Natal {label} branch {n_branch}. Harmonious support, cooperation, and stability.",
                    }
                )

        # 3. Cross-pillar pair checks: Harms (相害) and Zi-Mao mutual punishment (无礼之刑).
        # These are mutual pair relations not covered by clash/harmony. We test every
        # transit-pillar branch against every natal-pillar branch (skipping same-pillar
        # pairs already handled above) so that e.g. Transit Year vs Natal Day harms are
        # surfaced, not only Day-driven ones.
        harm_map = {
            "Zi": "Wei", "Wei": "Zi",
            "Chou": "Wu", "Wu": "Chou",
            "Yin": "Si", "Si": "Yin",
            "Mao": "Chen", "Chen": "Mao",
            "Shen": "Hai", "Hai": "Shen",
            "You": "Xu", "Xu": "You",
        }
        mutual_punishment_map = {  # 子卯 mutual punishment (无礼之刑)
            "Zi": "Mao", "Mao": "Zi",
        }
        natal_pillars_labeled = [
            ("Year", n_y_b),
            ("Month", n_m_b),
            ("Day", n_d_b),
            ("Hour", n_h_b),
        ]
        transit_pillars_labeled = [
            ("Year", t_y_b),
            ("Month", t_m_b),
            ("Day", t_d_b),
            ("Hour", t_h_b),
        ]
        for t_label, t_b in transit_pillars_labeled:
            if t_b == "Unknown":
                continue
            for n_label, n_b in natal_pillars_labeled:
                if n_b == "Unknown" or t_label == n_label:
                    continue
                pair_label = f"{t_label}→{n_label}"
                if harm_map.get(t_b) == n_b:
                    interactions.append(
                        {
                            "pillar": pair_label,
                            "type": "Harm",
                            "description": f"Transit {t_label} branch {t_b} HARMS Natal {n_label} branch {n_b}. Hidden friction, subtle obstruction, or interpersonal jealousy.",
                        }
                    )
                elif mutual_punishment_map.get(t_b) == n_b:
                    interactions.append(
                        {
                            "pillar": pair_label,
                            "type": "Punishment",
                            "description": f"Transit {t_label} branch {t_b} PUNISHES Natal {n_label} branch {n_b} (Zi-Mao 无礼之刑). Conflict, discourtesy, or legal/relational friction.",
                        }
                    )

        # 4. Set-based interactions across all 8 visible pillars (4 natal + 4 transit):
        #    - Three-Harmony trines 三合 (full and partial)
        #    - Three-way punishments 三刑 (Yin-Si-Shen, Chou-Xu-Wei)
        branch_to_sources: dict[str, list[str]] = {}
        for label, b in [
            ("Natal Year", n_y_b),
            ("Natal Month", n_m_b),
            ("Natal Day", n_d_b),
            ("Natal Hour", n_h_b),
            ("Transit Year", t_y_b),
            ("Transit Month", t_m_b),
            ("Transit Day", t_d_b),
            ("Transit Hour", t_h_b),
        ]:
            if b != "Unknown":
                branch_to_sources.setdefault(b, []).append(label)

        def _format_participants(branches: set[str]) -> str:
            parts = []
            for b in sorted(branches):
                sources = branch_to_sources.get(b, [])
                if sources:
                    parts.append(f"{b} ({', '.join(sources)})")
                else:
                    parts.append(b)
            return ", ".join(parts)

        trine_sets = [
            ({"Shen", "Zi", "Chen"}, "Water (水局)"),
            ({"Hai", "Mao", "Wei"}, "Wood (木局)"),
            ({"Yin", "Wu", "Xu"}, "Fire (火局)"),
            ({"Si", "You", "Chou"}, "Metal (金局)"),
        ]
        for trine, element in trine_sets:
            present = trine & branch_to_sources.keys()
            if len(present) == 3:
                interactions.append(
                    {
                        "pillar": "Three-Harmony",
                        "type": "Three-Harmony",
                        "description": f"Full Three-Harmony Trine {element}: {_format_participants(present)}. Three branches combine into a powerful supportive frame — major harmonious force.",
                    }
                )
            elif len(present) == 2:
                missing = next(iter(trine - present))
                interactions.append(
                    {
                        "pillar": "Three-Harmony (Partial)",
                        "type": "Three-Harmony (Partial)",
                        "description": f"Partial Three-Harmony {element}: {_format_participants(present)}. Awaiting {missing} to complete the trine — semi-supportive frame.",
                    }
                )

        three_way_punishments = [
            ({"Yin", "Si", "Shen"}, "Yin-Si-Shen (恃势之刑)"),
            ({"Chou", "Xu", "Wei"}, "Chou-Xu-Wei (无恩之刑)"),
        ]
        for punish_set, label in three_way_punishments:
            present = punish_set & branch_to_sources.keys()
            if len(present) == 3:
                interactions.append(
                    {
                        "pillar": "Three-Way Punishment",
                        "type": "Punishment",
                        "description": f"Full Three-Way Punishment {label}: {_format_participants(present)}. Three branches mutually punish — legal, health, or relationship turmoil; caution advised.",
                    }
                )

        return {
            "transit_day_pillar": transit_chinese["bazi"]["day"].split(" ")[0]
            if "/" in transit_chinese["bazi"]["day"]
            else transit_chinese["bazi"]["day"],
            "natal_day_pillar": natal_chinese["bazi"]["day"].split(" ")[0]
            if "/" in natal_chinese["bazi"]["day"]
            else natal_chinese["bazi"]["day"],
            "interactions": interactions,
        }

    YEAR_AHEAD_MAX_EVENTS = 500

    _BODY_DISPLAY = {
        "sun": "Sun",
        "moon": "Moon",
        "mercury": "Mercury",
        "venus": "Venus",
        "mars": "Mars",
        "jupiter": "Jupiter",
        "saturn": "Saturn",
        "uranus": "Uranus",
        "neptune": "Neptune",
        "pluto": "Pluto",
        "north_node": "North Node",
    }

    def get_year_ahead_timeline(
        self,
        natal_dt: datetime,
        natal_location: tuple[float, float],
        start: datetime | None = None,
        end: datetime | None = None,
        orb: float = 1.0,
    ) -> dict:
        """Compute a year-ahead transit timeline for a natal chart.

        Scans daily from ``start`` to ``end`` (default period: 365 days
        starting at ``natal_dt``) and emits events for the following
        categories:

        - ``lunar_phase`` — new moon and full moon, detected by
          illumination crossing the 5%/95% thresholds. 12 of each per
          year are typical. ``body="Moon"``.
        - ``ingress`` — Sun or Moon entering a new zodiac sign. The Sun
          changes sign roughly once per month (12/year); the Moon
          changes sign every ~2.5 days (~145/year).
        - ``transit`` — a transiting planet within ``orb`` degrees of a
          natal planet, conjunction only (v1). Other aspects are not
          computed.

        Event priority for the cap (highest first): lunar phases,
        ingresses, transits. When the cap is exceeded, transit events
        are dropped first so that lunations and ingresses always
        remain. All datetimes are returned in UTC ISO 8601.

        Args:
            natal_dt: Natal birth datetime (tz-aware or naive; naive
                datetimes are interpreted as UTC).
            natal_location: ``(latitude, longitude)`` of birth location.
            start: Period start (defaults to ``natal_dt``).
            end: Period end (defaults to ``start + timedelta(days=365)``).
            orb: Maximum orb in degrees for transit conjunctions
                (default 1.0°).

        Returns:
            dict: ``{"period": {"start": ISO, "end": ISO},
                    "events": [{date, type, body, sign,
                                aspect_to_natal, orb}, ...]}`` sorted
            ascending by date and capped at
            :attr:`YEAR_AHEAD_MAX_EVENTS` entries.
        """

        def _to_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return pytz.UTC.localize(dt)
            return dt.astimezone(pytz.UTC)

        natal_dt = _to_utc(natal_dt)
        if start is None:
            start = natal_dt
        else:
            start = _to_utc(start)
        if end is None:
            end = start + timedelta(days=365)
        else:
            end = _to_utc(end)

        if end <= start:
            return {
                "period": {"start": start.isoformat(), "end": end.isoformat()},
                "events": [],
            }

        natal_positions = self.get_planetary_positions(natal_dt, natal_location)
        natal_moon_illum = self.get_moon_phase(natal_dt)["illumination"]

        prev_positions = self.get_planetary_positions(start, natal_location)
        prev_sun_sign = prev_positions["sun"]["sign"]
        prev_moon_sign = prev_positions["moon"]["sign"]
        prev_illumination = self.get_moon_phase(start)["illumination"]

        non_transit_events: list[dict] = []
        transit_events: list[dict] = []

        # Scan at noon UTC each day for a stable anchor, and start on
        # the day after the anchor so we have a previous-day state to
        # compare against.
        scan_date = start.date() + timedelta(days=1)
        end_date = end.date()

        while scan_date <= end_date:
            scan_dt = datetime(
                scan_date.year,
                scan_date.month,
                scan_date.day,
                12,
                0,
                0,
                tzinfo=pytz.UTC,
            )
            if scan_dt > end:
                break

            positions = self.get_planetary_positions(scan_dt, natal_location)
            moon_sign = positions["moon"]["sign"]

            sun_sign = positions["sun"]["sign"]
            if sun_sign != prev_sun_sign:
                non_transit_events.append(
                    {
                        "date": scan_dt.isoformat(),
                        "type": "ingress",
                        "body": "Sun",
                        "sign": sun_sign,
                        "aspect_to_natal": None,
                        "orb": 0.0,
                    }
                )
            prev_sun_sign = sun_sign

            if moon_sign != prev_moon_sign:
                non_transit_events.append(
                    {
                        "date": scan_dt.isoformat(),
                        "type": "ingress",
                        "body": "Moon",
                        "sign": moon_sign,
                        "aspect_to_natal": None,
                        "orb": 0.0,
                    }
                )
            prev_moon_sign = moon_sign

            illumination = self.get_moon_phase(scan_dt)["illumination"]
            if prev_illumination is not None:
                # Threshold of 5% (illumination 0-100) matches the
                # ~12 new-moon crossings per year.
                if prev_illumination >= 5.0 and illumination < 5.0:
                    aspect = "returns to natal moon phase" if natal_moon_illum < 5.0 else None
                    non_transit_events.append(
                        {
                            "date": scan_dt.isoformat(),
                            "type": "lunar_phase",
                            "body": "Moon",
                            "sign": moon_sign,
                            "aspect_to_natal": aspect,
                            "orb": round(illumination, 2),
                        }
                    )
                elif prev_illumination <= 95.0 and illumination > 95.0:
                    aspect = "returns to natal moon phase" if natal_moon_illum > 95.0 else None
                    non_transit_events.append(
                        {
                            "date": scan_dt.isoformat(),
                            "type": "lunar_phase",
                            "body": "Moon",
                            "sign": moon_sign,
                            "aspect_to_natal": aspect,
                            "orb": round(illumination, 2),
                        }
                    )
            prev_illumination = illumination

            for planet_name, planet_pos in positions.items():
                transit_lon = planet_pos["longitude"]
                transit_sign = planet_pos["sign"]
                for natal_name, natal_pos in natal_positions.items():
                    natal_lon = natal_pos["longitude"]
                    diff = abs(transit_lon - natal_lon) % 360.0
                    distance = min(diff, 360.0 - diff)
                    if distance <= orb:
                        body_disp = self._BODY_DISPLAY.get(planet_name, planet_name.replace("_", " ").title())
                        natal_disp = self._BODY_DISPLAY.get(natal_name, natal_name.replace("_", " ").title())
                        transit_events.append(
                            {
                                "date": scan_dt.isoformat(),
                                "type": "transit",
                                "body": body_disp,
                                "sign": transit_sign,
                                "aspect_to_natal": f"conjunct natal {natal_disp}",
                                "orb": round(distance, 2),
                            }
                        )

            scan_date = scan_date + timedelta(days=1)

        # Cap: transit events are lowest priority and dropped first.
        cap = self.YEAR_AHEAD_MAX_EVENTS
        if len(non_transit_events) + len(transit_events) > cap:
            if len(non_transit_events) >= cap:
                non_transit_events.sort(key=lambda e: e["date"])
                final_events = non_transit_events[:cap]
            else:
                remaining = cap - len(non_transit_events)
                transit_events.sort(key=lambda e: e["date"])
                final_events = non_transit_events + transit_events[:remaining]
        else:
            final_events = non_transit_events + transit_events

        final_events.sort(key=lambda e: e["date"])

        return {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "events": final_events,
        }

    # =========================================================================
    # SECONDARY PROGRESSIONS (DAY-FOR-YEAR)
    # =========================================================================

    def get_secondary_progressions(
        self,
        natal_dt: datetime,
        natal_location: tuple[float, float] | None,
        target_dt: datetime,
    ) -> dict:
        """Compute a secondary-progressions chart (day-for-year).

        Secondary progressions are the most widely used "predictive" astrology
        technique. The classical formula — sometimes called "Naibod in
        miniature" — is to advance the natal chart by **one day of ephemeris
        time for each year of life** (and proportionally for partial years).
        So a person who is 30.5 years old is read at a "progressed date" of
        30.5 days after birth. This slows planetary motion dramatically:

        - Progressed Sun moves ~1° per year of life (its true motion is
          ~1°/day; we shrink it by 365.25×).
        - Progressed Moon moves ~12° per year of life (its true motion is
          ~13.2°/day, so ~0.036°/day-of-life).

        In v1 we expose the progressed positions only — the progressed Asc /
        MC and a progressed Moon phase. Progressed-to-natal aspects and
        progressed-to-progressed aspects are out of scope (see the plan).

        Args:
            natal_dt: Natal birth datetime. Naive datetimes are interpreted
                as UTC; tz-aware datetimes are converted to UTC internally.
            natal_location: ``(latitude, longitude)`` of birth location. If
                ``None``, defaults to ``(0.0, 0.0)`` (equator / prime
                meridian) — the Asc / MC angles are still computed at this
                fallback location so the result is well-defined.
            target_dt: The "now" for which we want the progressed chart.
                Age = ``(target_dt - natal_dt)`` in years (decimal, divided
                by 365.25 days).

        Returns:
            dict: ``{
                "progressed_date": "YYYY-MM-DDTHH:MM:SSZ",   # ISO 8601 UTC
                "positions": {
                    <planet>: {"sign": str, "degree": float,
                               "exact_longitude": float}, ...  # 10 planets
                },
                "angles": {
                    "asc": {"sign": str, "degree": float,
                            "exact_longitude": float},
                    "mc":  {"sign": str, "degree": float,
                            "exact_longitude": float},
                },
                "moon_phase_degrees": float,   # 0-360, prog_sun -> prog_moon
                "moon_phase_label":   str,     # one of 8 phase names
            }``

            ``moon_phase_degrees`` is measured as the **forward** angle from
            the progressed Sun to the progressed Moon (i.e. ``(prog_moon -
            prog_sun) mod 360``). A value near 0° means the progressed Moon
            is conjunct the progressed Sun (New); near 180° means it's
            opposite (Full); the four cardinal points are the quarters.
        """

        # 1) Normalize inputs to UTC.
        def _to_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return pytz.UTC.localize(dt)
            return dt.astimezone(pytz.UTC)

        natal_dt = _to_utc(natal_dt)
        target_dt = _to_utc(target_dt)

        if natal_location is None:
            lat, lon = 0.0, 0.0
        else:
            lat, lon = natal_location

        # Day-for-year: one day of ephemeris time per year of life.
        years_lived = (target_dt - natal_dt).days / 365.25
        progressed_dt = natal_dt + timedelta(days=years_lived)

        # 10 classical planets (North Node excluded to match get_midpoints /
        # get_antiscia — it's a calculated point, not a planet).
        planet_positions = self.get_planetary_positions(progressed_dt, (lat, lon))
        planets = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]

        def _lon_to_sign_degree(lon: float) -> dict:
            lon = lon % 360.0
            sign_idx = int(lon // 30) % 12
            return {
                "sign": self.SIGNS[sign_idx],
                "degree": lon % 30,
                "exact_longitude": lon,
            }

        positions = {p: _lon_to_sign_degree(planet_positions[p]["longitude"]) for p in planets}

        jd = self.get_julian_day(progressed_dt)
        _, ascmc = swe.houses_ex(jd, lat, lon, b"P")
        asc_lon = float(ascmc[0])
        mc_lon = float(ascmc[1])

        angles = {
            "asc": _lon_to_sign_degree(asc_lon),
            "mc": _lon_to_sign_degree(mc_lon),
        }

        prog_sun_lon = planet_positions["sun"]["longitude"]
        prog_moon_lon = planet_positions["moon"]["longitude"]
        moon_phase_degrees = (prog_moon_lon - prog_sun_lon) % 360.0
        moon_phase_label = self._moon_phase_label(moon_phase_degrees)

        return {
            "progressed_date": progressed_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "positions": positions,
            "angles": angles,
            "moon_phase_degrees": moon_phase_degrees,
            "moon_phase_label": moon_phase_label,
        }

    @staticmethod
    def _moon_phase_label(degrees: float) -> str:
        """Map a 0-360° Sun→Moon phase angle to one of 8 named phase labels.

        The eight labels are spaced at 45° intervals, centered on 0° / 45° /
        90° / ... / 315° (i.e. the cardinal phases sit at the *middle* of
        each 45° bucket, not at the boundary). The exact bucket edges, per
        spec, are:

            0.0-22.5°   -> "new"
            22.5-67.5°  -> "waxing crescent"
            67.5-112.5° -> "first quarter"
            112.5-157.5°-> "waxing gibbous"
            157.5-202.5°-> "full"
            202.5-247.5°-> "waning gibbous"
            247.5-292.5°-> "last quarter"
            292.5-337.5°-> "waning crescent"
            337.5-360°  -> "new"

        The labels wrap so 337.5°-360° folds back to ``"new"``. Out-of-range
        input raises ``ValueError``.
        """
        if degrees < 0.0 or degrees >= 360.0:
            raise ValueError(f"moon phase degrees must be in [0, 360), got {degrees!r}")
        labels = [
            "new",
            "waxing crescent",
            "first quarter",
            "waxing gibbous",
            "full",
            "waning gibbous",
            "last quarter",
            "waning crescent",
        ]
        return labels[int((degrees + 22.5) / 45.0) % 8]

    # =========================================================================
    # SOLAR ARC DIRECTIONS
    # =========================================================================

    def get_solar_arc_directions(
        self,
        natal_dt: datetime,
        natal_location: tuple[float, float] | None,
        target_dt: datetime,
    ) -> dict:
        """Compute solar-arc directions for a natal chart at a target date.

        Solar-arc directions are the simplest and most widely used predictive
        technique in traditional western astrology. The formula has two steps:

          1. Compute the **solar arc**: the difference (mod 360°) between the
             *secondary-progression Sun* and the natal Sun. Because the
             secondary-progression Sun advances ~1° per year of life, the
             solar arc in degrees is approximately equal to the native's age
             in years.
          2. Add that arc to every natal planet longitude and every natal
             angle (Asc, MC). The result is the **directed** position of
             each body.

        v1 returns the directed positions only. Directed-to-directed aspects,
        directed-to-natal aspects, Naibod arc, key cycles, and other direction
        variants are deliberately out of scope.

        Args:
            natal_dt: Natal birth datetime. Naive datetimes are interpreted
                as UTC; tz-aware datetimes are converted to UTC internally.
            natal_location: ``(latitude, longitude)`` of birth location. If
                ``None``, defaults to ``(0.0, 0.0)`` (equator / prime
                meridian) — the Asc / MC angles are still computed at this
                fallback location so the result is well-defined.
            target_dt: The "now" for which we want the directed chart.
                Solar arc ≈ ``(target_dt - natal_dt) / 365.25`` years in
                degrees.

        Returns:
            dict: ``{
                "solar_arc_degrees": float,   # 0-360
                "directed": {
                    <planet>: {"sign": str, "degree": float,
                               "exact_longitude": float},
                    ...  # 10 classical planets: sun, moon, mercury, venus,
                    #     mars, jupiter, saturn, uranus, neptune, pluto
                    "asc":     {"sign": str, "degree": float,
                                "exact_longitude": float},
                    "mc":      {"sign": str, "degree": float,
                                "exact_longitude": float},
                },
            }``

            Every directed longitude is ``(natal_longitude + solar_arc)
            mod 360``, so adding the same arc uniformly shifts the wheel.
        """

        # 1) Normalize inputs to UTC.
        def _to_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return pytz.UTC.localize(dt)
            return dt.astimezone(pytz.UTC)

        natal_dt = _to_utc(natal_dt)
        target_dt = _to_utc(target_dt)

        if natal_location is None:
            lat, lon = 0.0, 0.0
        else:
            lat, lon = natal_location

        # 2) Solar arc = progressed Sun - natal Sun (mod 360).
        natal_positions = self.get_planetary_positions(natal_dt, (lat, lon))
        natal_sun_lon = natal_positions["sun"]["longitude"]

        progressed = self.get_secondary_progressions(natal_dt, (lat, lon), target_dt)
        prog_sun_lon = progressed["positions"]["sun"]["exact_longitude"]

        solar_arc = (prog_sun_lon - natal_sun_lon) % 360.0

        # 3) Natal angles (Asc, MC) at birth, for the directed angles.
        jd_natal = self.get_julian_day(natal_dt)
        _, ascmc_natal = swe.houses_ex(jd_natal, lat, lon, b"P")
        natal_asc_lon = float(ascmc_natal[0])
        natal_mc_lon = float(ascmc_natal[1])

        # 4) Build the directed set.
        def _lon_to_sign_degree(lon: float) -> dict:
            lon = lon % 360.0
            sign_idx = int(lon // 30) % 12
            return {
                "sign": self.SIGNS[sign_idx],
                "degree": lon % 30,
                "exact_longitude": lon,
            }

        directed: dict = {}
        planets = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]
        for p in planets:
            natal_lon = natal_positions[p]["longitude"]
            directed_lon = (natal_lon + solar_arc) % 360.0
            directed[p] = _lon_to_sign_degree(directed_lon)

        directed["asc"] = _lon_to_sign_degree((natal_asc_lon + solar_arc) % 360.0)
        directed["mc"] = _lon_to_sign_degree((natal_mc_lon + solar_arc) % 360.0)

        return {
            "solar_arc_degrees": solar_arc,
            "directed": directed,
        }

    # =========================================================================
    # SOLAR RETURNS + PROFECTIONS
    # =========================================================================

    # Traditional (pre-modern) planetary rulerships. Modern astrology assigns
    # Uranus to Aquarius and Pluto to Scorpio; the profection framework
    # predates those discoveries and uses the seven-classical-planet scheme.
    PROFECTION_LORDS = {
        "Aries": "Mars",
        "Taurus": "Venus",
        "Gemini": "Mercury",
        "Cancer": "Moon",
        "Leo": "Sun",
        "Virgo": "Mercury",
        "Libra": "Venus",
        "Scorpio": "Mars",
        "Sagittarius": "Jupiter",
        "Capricorn": "Saturn",
        "Aquarius": "Saturn",
        "Pisces": "Jupiter",
    }

    def get_solar_return(
        self,
        natal_dt: datetime,
        natal_location: tuple[float, float] | None = None,
        return_year: int = 0,
        return_location: tuple[float, float] | None = None,
    ) -> dict:
        """Find the exact moment the transiting Sun returns to its natal longitude.

        A solar return chart is computed for the moment the Sun reaches the
        same ecliptic longitude it held at birth, observed during
        ``return_year``. The exact moment is independent of location (the
        Sun is effectively at infinity), but the chart houses/angles ARE
        location-dependent — by default the natal location is reused (the
        standard in solar return astrology, where the relocation question
        is read off the chart rather than baked in), and ``return_location``
        overrides that.

        The moment is found by binary search within ``return_year`` (Jan 1
        noon UTC to Dec 31 noon UTC). The Sun's apparent motion is ~1°/day,
        so 30 bisection iterations converge to sub-second precision.

        Args:
            natal_dt: Natal birth datetime. Naive datetimes are interpreted
                as UTC; tz-aware datetimes are converted to UTC internally.
            natal_location: ``(latitude, longitude)`` of birth location.
                Used as the default for ``return_location``.
            return_year: Calendar year in which to find the solar return
                (e.g., ``2026`` for the solar return in 2026).
            return_location: Optional ``(latitude, longitude)`` override
                for the chart location. Defaults to ``natal_location``;
                if both are ``None``, ``(0.0, 0.0)`` is used.

        Returns:
            dict: ``{
                "exact_moment": "YYYY-MM-DDTHH:MM:SS+00:00",  # ISO 8601 UTC
                "location":      (lat, lon),                   # the location used
                "positions":     {<planet>: {"longitude", "sign",
                                            "degree", ...}, ...},
                                                          # all 10 planets
                                                          # + ascendant + midheaven
                "angles": {
                    "asc": {...},  # ascendant dict (copy from positions)
                    "mc":  {...},  # midheaven  dict (copy from positions)
                },
            }``

            The Sun's ``exact_longitude`` in ``positions["sun"]`` should
            match the natal Sun's longitude to within ~0.5°.
        """
        if natal_location is None:
            natal_location = (0.0, 0.0)
        if return_location is None:
            return_location = natal_location

        natal_positions = self.get_planetary_positions(natal_dt)
        natal_sun_lon = natal_positions["sun"]["longitude"]

        # Search window: a full year starting Jan 1 of return_year noon UTC.
        # The Sun's apparent motion is ~365.25 days per cycle, so the solar
        # return can land on Jan 1-3 of return_year+1 for birthdays very
        # close to New Year. We include that tail in the search range so
        # the Sun is guaranteed to cross ``natal_sun_lon`` exactly once
        # within [start, end). Anchored at noon UTC for ephemeris stability.
        start = datetime(return_year, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        end = datetime(return_year + 1, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)

        def _sun_lon(dt: datetime) -> float:
            return self.get_planetary_positions(dt)["sun"]["longitude"]

        # Unwrap the target so it lives in the same monotonic space as the
        # search range. The Sun's apparent longitude wraps from 360 -> 0
        # at the Aries ingress (~Mar 20), so we shift the target by +360
        # whenever it would otherwise be "before" the start-of-year value.
        sun_lon_start = _sun_lon(start)
        if sun_lon_start <= natal_sun_lon:
            target_unwrapped = natal_sun_lon
        else:
            target_unwrapped = natal_sun_lon + 360.0

        # Binary search. 35 iterations over a 365-day window gives
        # ~365 / 2^35 seconds ≈ 10 nanoseconds — way below sub-second.
        lo, hi = start, end
        for _ in range(35):
            mid_dt = lo + (hi - lo) / 2
            cur = _sun_lon(mid_dt)
            if cur < sun_lon_start:
                cur += 360.0
            if cur < target_unwrapped:
                lo = mid_dt
            else:
                hi = mid_dt
            if (hi - lo).total_seconds() < 1.0:
                break

        exact_moment = lo + (hi - lo) / 2

        chart = self.get_western_astrology(exact_moment, return_location)
        positions = chart["positions"]

        return {
            "exact_moment": exact_moment.isoformat(),
            "location": return_location,
            "positions": positions,
            "angles": {
                "asc": positions.get("ascendant", {}),
                "mc": positions.get("midheaven", {}),
            },
        }

    def get_profection(
        self,
        natal_dt: datetime,
        target_year: int,
        profection_year_start: int = 0,
        natal_location: tuple[float, float] | None = None,
    ) -> dict:
        """Compute the annual profection for a target year.

        Profections rotate the Asc sign by one sign per year of life. The
        profection lord is the traditional planetary ruler of the
        profected sign. With the default ``profection_year_start=0``:

            age = target_year - natal_dt.year
            sign_offset = age % 12
            profected_sign_index = (natal_asc_index + sign_offset) % 12
            house_ruled = sign_offset + 1     # 1 through 12, wrapping yearly

        The 12-year cycle returns the profected sign to the natal sign at
        age 0, 12, 24, ...  At age 0 the profected sign IS the natal
        Asc sign and ``house_ruled == 1``.

        Traditional rulerships are used (see :attr:`PROFECTION_LORDS`).
        Modern rulerships assign Uranus to Aquarius and Pluto to Scorpio,
        but profections are a Hellenistic framework that predate those
        discoveries — Saturn rules Aquarius and Mars rules Scorpio.

        Args:
            natal_dt: Natal birth datetime. Naive datetimes are interpreted
                as UTC; tz-aware datetimes are converted to UTC internally.
            target_year: The year for which to compute the profection.
            profection_year_start: Optional offset to the year-of-life
                calculation. Default 0 (profections start at birth).
                Pass 1 to start the profection year one calendar year
                after birth (some traditions anchor the year at the
                birthday rather than the calendar year).
            natal_location: ``(latitude, longitude)`` of birth location.
                Required to compute the natal Asc sign. Defaults to
                ``(0.0, 0.0)`` if not provided (the Asc / MC angles are
                still computed at this fallback location so the result
                is well-defined).

        Returns:
            dict: ``{
                "age": int,                # target_year - natal_dt.year - profection_year_start
                "natal_asc_sign": str,     # e.g. "Leo"
                "profected_asc_sign": str, # e.g. "Sagittarius"  (natal + sign_offset)
                "profection_lord": str,    # e.g. "Jupiter"
                "house_ruled": int,        # 1-12 (sign_offset + 1)
            }``
        """
        if natal_location is None:
            natal_location = (0.0, 0.0)

        natal_chart = self.get_western_astrology(natal_dt, natal_location)
        natal_asc_sign = natal_chart["positions"]["ascendant"]["sign"]

        age = target_year - natal_dt.year - profection_year_start
        sign_offset = age % 12

        natal_asc_idx = self.SIGNS.index(natal_asc_sign)
        profected_asc_idx = (natal_asc_idx + sign_offset) % 12
        profected_asc_sign = self.SIGNS[profected_asc_idx]

        profection_lord = self.PROFECTION_LORDS[profected_asc_sign]
        house_ruled = sign_offset + 1

        return {
            "age": age,
            "natal_asc_sign": natal_asc_sign,
            "profected_asc_sign": profected_asc_sign,
            "profection_lord": profection_lord,
            "house_ruled": house_ruled,
        }

    # =========================================================================
    # ASTROCARTOGRAPHY (LOCATIONAL LINES)
    # =========================================================================

    # The 10 planets whose locational lines we draw. The lunar node is omitted
    # because the algorithm assumes a body that is well defined for the
    # 5°-step sweep; the node moves ~0.05°/day and its altitude crosses zero
    # at well-defined longitudes, but the existing caller (Task 17) only
    # consumes the classical 10. If you need the node, add it explicitly.
    ASTROCARTOGRAPHY_PLANETS = (
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
        "pluto",
    )

    def get_astrocartography_lines(
        self,
        dt: datetime,
        step_degrees: float = 5.0,
    ) -> dict:
        """Compute coarse astrocartography lines (AC/DC/MC/IC) per planet.

        Astrocartography is a locational astrology technique developed by
        Jim Lewis in the 1970s. The idea: every planet, at every moment, is
        rising somewhere, setting somewhere, culminating somewhere, and
        anti-culminating somewhere on Earth. The four "lines" for each
        planet are the world locations where that planet sits exactly on:

        - **AC** (Ascendant) — on the eastern horizon, altitude = 0,
          rising (going from below to above the horizon).
        - **DC** (Descendant) — on the western horizon, altitude = 0,
          setting (going from above to below).
        - **MC** (Midheaven) — on the upper meridian (due south in
          Swiss Ephemeris convention, azimuth 0°/360°).
        - **IC** (Imum Coeli) — on the lower meridian (due north,
          azimuth 180°).

        The v1 algorithm is a **coarse approximation**: for each of the 10
        planets, we sample the equator strip at ``lat=0`` across
        ``lon ∈ [-180, 180]`` in ``step_degrees`` increments, compute the
        planet's altitude and azimuth at each sample point via
        ``swe.azalt()``, and detect sign changes (crossings) in altitude
        and azimuth. Crossing longitudes are refined by linear
        interpolation between the bracketing samples.

        The 5° default step yields ~73 sample points per sweep, which is
        enough for visualization but not for production-level precision.
        For higher accuracy, refine each crossing with bisection (not
        implemented in v1 — this is documented as a follow-up).

        Limitations:

        - Sample latitude is fixed at 0°; non-equator AC/DC lines (which
          curve toward the poles as a function of declination) are not
          captured.
        - No planetary aspect lines (planet X square planet Y) — v1
          scope is the four angles per planet only.
        - Azimuth is reported by ``swe.azalt`` from south to west
          (0°=south, 90°=west, 180°=north, 270°=east).

        Args:
            dt: Datetime for the astrocartography snapshot. Naive
                datetimes are interpreted as UTC; tz-aware datetimes
                are converted to UTC internally.
            step_degrees: Longitude step in degrees for the equator
                sweep. Default 5.0°. Smaller = more sample points =
                more precise line crossings (and slower). Must be
                positive.

        Returns:
            dict: ``{
                <planet_name>: {
                    "ac": [(lat, lon), ...],  # rising crossings
                    "dc": [(lat, lon), ...],  # setting crossings
                    "mc": [(lat, lon), ...],  # upper meridian crossings
                    "ic": [(lat, lon), ...],  # lower meridian crossings
                },
                ...
            }``

            Each list contains 0-N crossing points as ``(lat, lon)``
            tuples (lat is always 0.0 in v1; lon is in ``[-180, 180]``).
        """
        if step_degrees <= 0:
            raise ValueError("step_degrees must be positive")

        if dt.tzinfo is None:
            dt_utc = pytz.UTC.localize(dt)
        else:
            dt_utc = dt.astimezone(pytz.UTC)
        jd_ut = self.get_julian_day(dt_utc)

        # Pre-compute equatorial coords (RA/Dec/distance) once per planet;
        # they are identical at every sample point on Earth at this instant.
        planet_equatorial: dict[str, tuple[float, float, float]] = {}
        for planet_name in self.ASTROCARTOGRAPHY_PLANETS:
            planet_id = self.PLANETS[planet_name]
            # swe.calc_ut returns ((ra, dec, dist, ...), flag) when the
            # FLG_EQUATORIAL flag is passed.
            result = swe.calc_ut(jd_ut, planet_id, swe.FLG_EQUATORIAL)
            ra, dec, dist = result[0][0], result[0][1], result[0][2]
            planet_equatorial[planet_name] = (ra, dec, dist)

        lons = []
        lon = -180.0
        while lon <= 180.0 + 1e-9:
            lons.append(lon)
            lon += step_degrees
        # Snap the last point to exactly 180.0 to avoid FP drift.
        if lons[-1] > 180.0:
            lons[-1] = 180.0

        # swe.azalt's geopos is (lon, lat, alt_m) — note the order is
        # east-positive longitude, north-positive latitude. atpress=0 and
        # attemp=0 select a sea-level standard atmosphere.
        geopos = [0.0, 0.0, 0.0]
        results: dict[str, dict[str, list[tuple[float, float]]]] = {}

        for planet_name in self.ASTROCARTOGRAPHY_PLANETS:
            ra, dec, dist = planet_equatorial[planet_name]
            xin = [ra, dec, dist]

            altitudes: list[float] = []
            azimuths: list[float] = []
            for sample_lon in lons:
                geopos[0] = sample_lon
                az_alt = swe.azalt(jd_ut, swe.EQU2HOR, geopos, 0, 0, xin)
                # swe.azalt returns (azimuth, true_altitude, apparent_altitude).
                azimuths.append(az_alt[0])
                altitudes.append(az_alt[1])

            ac: list[tuple[float, float]] = []
            dc: list[tuple[float, float]] = []
            mc: list[tuple[float, float]] = []
            ic: list[tuple[float, float]] = []

            for i in range(1, len(lons)):
                lon0, lon1 = lons[i - 1], lons[i]
                alt0, alt1 = altitudes[i - 1], altitudes[i]
                az0, az1 = azimuths[i - 1], azimuths[i]

                if alt0 < 0.0 < alt1:
                    frac = -alt0 / (alt1 - alt0)
                    ac.append((0.0, _wrap_lon(lon0 + frac * (lon1 - lon0))))
                elif alt0 > 0.0 > alt1:
                    frac = alt0 / (alt0 - alt1)
                    dc.append((0.0, _wrap_lon(lon0 + frac * (lon1 - lon0))))

                # Swiss Ephemeris azimuth runs 0..360 (measured from south).
                # MC is at azimuth 0/360 (upper meridian, due south), IC is
                # at azimuth 180 (lower meridian, due north). A sweep from
                # az=350 to az=10 therefore represents a single MC crossing
                # through 0, not a 340° swing.
                if az0 > 180.0 and az1 < 180.0:
                    frac = az0 / (az0 - az1)
                    mc.append((0.0, _wrap_lon(lon0 + frac * (lon1 - lon0))))
                elif (az0 < 180.0 < az1) or (az0 > 180.0 > az1):
                    frac = (180.0 - az0) / (az1 - az0)
                    ic.append((0.0, _wrap_lon(lon0 + frac * (lon1 - lon0))))

            results[planet_name] = {
                "ac": ac,
                "dc": dc,
                "mc": mc,
                "ic": ic,
            }

        return results

    def get_planet_house_map(self, dt: datetime, location: tuple[float, float] | None, house_system: str = "Placidus") -> dict:
        positions = self.get_planetary_positions(dt, location)

        if location is None:
            for name in positions:
                positions[name]["house_placidus"] = None
                positions[name]["house_whole_sign"] = None
            return positions

        lat, lon = location
        jd = self.get_julian_day(dt)
        cusps, ascmc = swe.houses(jd, lat, lon, b"P")

        asc_lon = ascmc[0]
        mc_lon = ascmc[1]
        asc_sign_index = int(asc_lon / 30) % 12

        for name, info in positions.items():
            planet_lon = info["longitude"]
            info["house_placidus"] = self._get_house_from_cusps(planet_lon, cusps)
            planet_sign_index = int(planet_lon / 30) % 12
            info["house_whole_sign"] = (planet_sign_index - asc_sign_index) % 12 + 1

        positions["ascendant"] = {
            "sign": self.SIGNS[int(asc_lon / 30) % 12],
            "degree": asc_lon % 30,
            "longitude": asc_lon,
            "house_placidus": 1,
            "house_whole_sign": 1,
        }

        positions["midheaven"] = {
            "sign": self.SIGNS[int(mc_lon / 30) % 12],
            "degree": mc_lon % 30,
            "longitude": mc_lon,
            "house_placidus": self._get_house_from_cusps(mc_lon, cusps),
            "house_whole_sign": (int(mc_lon / 30) % 12 - asc_sign_index) % 12 + 1,
        }

        return positions

    # =========================================================================
    # EXPORT SCHEMA v2 ADDITIONS (additive, non-breaking)
    # =========================================================================

    # swe.MEAN_NODE is what ``self.PLANETS["north_node"]`` maps to.
    NODE_TYPE = "mean"

    @staticmethod
    def _angular_delta_signed(a: float, b: float) -> float:
        """Signed shortest angular delta from ``a`` to ``b`` in ``[-180, 180]``."""
        return (b - a + 180.0) % 360.0 - 180.0

    def get_house_cusps(
        self, dt: datetime, location: tuple[float, float] | None
    ) -> dict:
        """Return explicit Placidus and Whole Sign house cusp longitudes.

        Both lists contain 12 ecliptic longitudes in ``[0, 360)``:

        * ``placidus`` — the 12 cusps returned by Swiss Ephemeris for the
          Placidus house system (``b"P"``). Cusp 1 is the Ascendant, cusp 4
          the Imum Coeli, cusp 7 the Descendant, cusp 10 the Midheaven.
        * ``whole_sign`` — for Whole Sign houses every cusp lands exactly on
          a sign boundary. Cusp 1 is the start longitude of the Ascendant's
          sign; each subsequent cusp is +30° from the previous.

        Args:
            dt: Datetime for the chart.
            location: ``(latitude, longitude)`` tuple, or ``None``. When
                ``None``, both lists are returned empty (no houses can be
                computed without a geographic location).

        Returns:
            dict: ``{"placidus": [12 floats], "whole_sign": [12 floats]}``.
        """
        if location is None:
            return {"placidus": [], "whole_sign": []}

        lat, lon = location
        jd = self.get_julian_day(dt)
        cusps, ascmc = swe.houses(jd, lat, lon, b"P")
        placidus = [float(cusps[i]) for i in range(12)]

        asc_lon = float(ascmc[0])
        asc_sign_index = int(asc_lon / 30) % 12
        whole_sign = [((asc_sign_index + i) % 12) * 30.0 for i in range(12)]
        return {"placidus": placidus, "whole_sign": whole_sign}

    def get_natal_aspects(
        self, dt: datetime, location: tuple[float, float] | None = None
    ) -> list[dict]:
        """Internal natal-to-natal aspects with applying/separating flag.

        ``applying`` is computed from the planets' geocentric angular speeds
        (``speed`` field from :meth:`get_planetary_positions`): if the faster
        body is closing the angular gap toward the exact aspect angle, the
        aspect is applying; otherwise it is separating. For pairs where one
        body has no speed (e.g. angles), ``applying`` is ``None``.

        Args:
            dt: Datetime for the chart.
            location: Optional ``(latitude, longitude)`` tuple.

        Returns:
            list[dict]: Each entry has ``planet_a``, ``planet_b``,
            ``aspect``, ``orb``, ``applying``.
        """
        positions = self.get_planetary_positions(dt, location)

        aspect_types = [
            {"name": "conjunction", "angle": 0, "orb": 8},
            {"name": "sextile", "angle": 60, "orb": 6},
            {"name": "square", "angle": 90, "orb": 8},
            {"name": "trine", "angle": 120, "orb": 8},
            {"name": "opposition", "angle": 180, "orb": 8},
        ]

        planet_names = [p for p in positions.keys() if p not in ("ascendant", "midheaven")]
        aspects: list[dict] = []
        for i in range(len(planet_names)):
            for j in range(i + 1, len(planet_names)):
                p1 = planet_names[i]
                p2 = planet_names[j]
                if p1 in ("uranus", "neptune", "pluto") and p2 in ("uranus", "neptune", "pluto"):
                    continue

                lon1 = positions[p1]["longitude"]
                lon2 = positions[p2]["longitude"]
                speed1 = positions[p1].get("speed")
                speed2 = positions[p2].get("speed")

                signed_delta = self._angular_delta_signed(lon1, lon2)
                distance = abs(signed_delta)

                for asp in aspect_types:
                    orb = abs(distance - asp["angle"])
                    if orb <= asp["orb"]:
                        applying = None
                        if isinstance(speed1, (int, float)) and isinstance(speed2, (int, float)):
                            # d_sep_dt = rate of change of (lon2 - lon1).
                            # Gap |signed_delta| shrinks when d_sep_dt has
                            # the opposite sign to signed_delta.
                            d_sep_dt = speed2 - speed1
                            if signed_delta >= 0:
                                applying = d_sep_dt < 0
                            else:
                                applying = d_sep_dt > 0
                        aspects.append(
                            {
                                "planet_a": p1,
                                "planet_b": p2,
                                "aspect": asp["name"],
                                "orb": round(orb, 2),
                                "applying": applying,
                            }
                        )
        return aspects

    def get_bazi_detailed(self, dt: datetime) -> dict:
        """Detailed BaZi (Four Pillars) decomposition with stems, branches,
        elements, day master, and the Five Elements tally.

        Complements :meth:`get_chinese_astrology` (which returns the
        pillar strings in a single translated string for display) with a
        machine-friendly, fully-decomposed shape. Falls back to ``None``
        pillars when ``lunar_python`` is unavailable so callers can detect
        the missing-dependency path without parsing display strings.

        Args:
            dt: Datetime for the chart (any timezone; converted to China
                Standard Time internally to match the Chinese lunisolar
                calendar).

        Returns:
            dict: ``{"pillars": [4 dicts], "day_master": dict,
            "five_elements": {Wood, Fire, Earth, Metal, Water}}``.
        """
        stem_elements = {
            "甲": "Wood", "乙": "Wood",
            "丙": "Fire", "丁": "Fire",
            "戊": "Earth", "己": "Earth",
            "庚": "Metal", "辛": "Metal",
            "壬": "Water", "癸": "Water",
        }
        stem_yin_yang = {
            "甲": "Yang", "丙": "Yang", "戊": "Yang", "庚": "Yang", "壬": "Yang",
            "乙": "Yin", "丁": "Yin", "己": "Yin", "辛": "Yin", "癸": "Yin",
        }
        branch_elements = {
            "子": "Water", "午": "Fire",
            "丑": "Earth", "未": "Earth", "辰": "Earth", "戌": "Earth",
            "寅": "Wood", "卯": "Wood",
            "巳": "Fire", "亥": "Water",
            "申": "Metal", "酉": "Metal",
        }
        five_elements_count = {"Wood": 0, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 0}

        try:
            from lunar_python import Solar
        except ImportError:
            logger.warning(
                "lunar_python is not installed; get_bazi_detailed() returning "
                "null pillars. Install with: pip install lunar-python"
            )
            return {
                "pillars": None,
                "day_master": None,
                "five_elements": dict(five_elements_count),
            }

        dt_china = dt.astimezone(pytz.timezone("Asia/Shanghai"))
        solar_c = Solar.fromYmdHms(
            dt_china.year, dt_china.month, dt_china.day,
            dt_china.hour, dt_china.minute, dt_china.second,
        )
        bazi = solar_c.getLunar().getEightChar()

        raw = {
            "year": (bazi.getYear(), bazi.getYearWuXing()),
            "month": (bazi.getMonth(), bazi.getMonthWuXing()),
            "day": (bazi.getDay(), bazi.getDayWuXing()),
            "hour": (bazi.getTime(), bazi.getTimeWuXing()),
        }

        pillars = []
        day_master = None
        for pillar_name in ("year", "month", "day", "hour"):
            pillar_str, wuxing_str = raw[pillar_name]
            stem_char = pillar_str[0] if len(pillar_str) >= 1 else ""
            branch_char = pillar_str[1] if len(pillar_str) >= 2 else ""
            stem_el = stem_elements.get(stem_char, "Unknown")
            branch_el = branch_elements.get(branch_char, "Unknown")
            element_label = (
                f"{stem_el}/{branch_el}"
                if (stem_el != "Unknown" or branch_el != "Unknown")
                else wuxing_str
            )

            if stem_el != "Unknown":
                five_elements_count[stem_el] += 1
            if branch_el != "Unknown":
                five_elements_count[branch_el] += 1

            pillars.append({
                "pillar": pillar_name,
                "stem": stem_char,
                "branch": branch_char,
                "stem_element": stem_el,
                "branch_element": branch_el,
                "element": element_label,
                "raw": pillar_str,
            })

            if pillar_name == "day" and stem_char:
                day_master = {
                    "stem": stem_char,
                    "element": stem_el,
                    "yin_yang": stem_yin_yang.get(stem_char, "Unknown"),
                }

        return {
            "pillars": pillars,
            "day_master": day_master,
            "five_elements": five_elements_count,
        }


def _wrap_lon(lon: float) -> float:
    """Normalize a longitude to ``[-180, 180]``.

    The astrocartography sweep can produce interpolated crossing
    longitudes slightly outside that range (e.g. ``-182.3`` when the
    bracket sat just past the antimeridian). This helper clamps them
    into the conventional range so downstream code (and the QA
    acceptance criteria) can rely on ``-180 <= lon <= 180``.
    """
    while lon > 180.0:
        lon -= 360.0
    while lon < -180.0:
        lon += 360.0
    return lon


def _shortest_angular_delta(a: float, b: float) -> float:
    """Return the signed shortest angular delta from ``a`` to ``b`` in
    ``[-180, 180]``. Used to unwrap azimuth samples that wrap around
    0/360.
    """
    d = (b - a + 180.0) % 360.0 - 180.0
    return d

AstrologyEngine = AstrologicalCalculator


def format_astrological_report(data: dict) -> str:
    """Pretty-print a ``get_current_energetics`` (or compatible) payload.

    Used by ``scripts/vajra_orchestrator.py`` and ``scripts/radionics_operation.py``
    for terminal / log output. Defensive — gracefully handles missing keys so
    the scripts don't crash when the backend returns a partial payload (e.g.
    fallback from ``vajra_service._get_astrology_data`` which omits several
    fields when ``self.astrology`` is None).

    Args:
        data: A dict from :meth:`AstrologicalCalculator.get_current_energetics`,
            or any object with the same shape. Expected keys (all optional):
            ``datetime``, ``moon_phase``, ``lunar_mansion``,
            ``planetary_positions``, ``auspicious_times``, ``planetary_hours``.

    Returns:
        str: Multi-line, plain-text report ready for ``print``.
    """
    lines: list[str] = []

    datetime_str = data.get("datetime")
    if datetime_str:
        lines.append(f"Timestamp: {datetime_str}")
        lines.append("")

    moon_phase = data.get("moon_phase")
    if moon_phase:
        mp_name = moon_phase.get("phase_name") or moon_phase.get("phase") or "—"
        mp_illum = moon_phase.get("illumination")
        # ``illumination`` is already 0–100 (see get_moon_phase line 1285:
        # ``illumination = (1 - math.cos(math.radians(phase_angle))) / 2 * 100``),
        # so just print as-is.
        mp_pct = (
            f" ({mp_illum:.1f}% illuminated)"
            if isinstance(mp_illum, (int, float))
            else ""
        )
        lines.append(f"Moon Phase: {mp_name}{mp_pct}")
        lines.append("")

    lunar_mansion = data.get("lunar_mansion")
    if lunar_mansion:
        lm_name = lunar_mansion.get("name") or "—"
        lines.append(f"Lunar Mansion: {lm_name}")
        lines.append("")

    planetary_positions = data.get("planetary_positions")
    if isinstance(planetary_positions, dict) and planetary_positions:
        lines.append("Planetary Positions:")
        for planet, info in planetary_positions.items():
            if not isinstance(info, dict):
                # Defensive — skip non-object values, same crash class as
                # the VedicPanchanga / AstrologyExtractionPanel fixes.
                continue
            sign = info.get("sign") or "—"
            degree = info.get("degree")
            deg_str = f"{degree:.2f}°" if isinstance(degree, (int, float)) else "—"
            retro = " (R)" if info.get("retrograde") else ""
            lines.append(f"  {planet.title()}: {sign} {deg_str}{retro}")
        lines.append("")

    auspicious = data.get("auspicious_times")
    if isinstance(auspicious, dict) and auspicious:
        lines.append("Auspicious Times:")
        for k, v in auspicious.items():
            lines.append(f"  {k.replace('_', ' ').title()}: {v}")
        lines.append("")

    planetary_hours = data.get("planetary_hours")
    if planetary_hours:
        ph_planet = planetary_hours.get("current_planetary_hour") or "—"
        ph_day = planetary_hours.get("day_planet") or "—"
        lines.append(f"Planetary Hour: {ph_planet} (day ruler: {ph_day})")

    if not lines:
        return "(no astrological data available)"
    return "\n".join(lines)


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
