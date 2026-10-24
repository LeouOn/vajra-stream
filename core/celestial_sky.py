"""
core.celestial_sky — Real-time celestial dome calculations for an observer's place.

Calculates Altitude (-90° to +90°) and Azimuth (0° to 360°, North=0, East=90)
for visible planets, Moon phase/illumination, and sacred Vedic fixed stars / nakshatras
above any observer location (latitude, longitude) at any given UTC time.

Frames. The Sun, Moon and planets come from the Swiss Ephemeris as geocentric apparent
places and are then corrected for diurnal parallax (Meeus, Astronomical Algorithms ch. 40;
oblate Earth, observer at sea level), so their altitude/azimuth are what an observer at
(latitude, longitude) sees: topocentric. The correction is largest for the Moon (up to ~1°),
8.8" for the Sun and at most ~32" for a planet. Right ascension and declination in the
payload stay geocentric apparent, and ``position_frame`` names the frame of the
altitude/azimuth. Altitudes are geometric (no atmospheric refraction). The correction is a
pure function of its arguments: swisseph's ``set_topo`` is process-global and the routes run
in a thread pool, so this module never calls it. The fixed stars have no measurable parallax
and are only precessed (J2000 -> of date).
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Try loading swisseph
try:
    import swisseph as swe

    swe.set_ephe_path("")
    HAS_SWISSEPH = True
except ImportError:
    swe = None  # type: ignore[assignment]
    HAS_SWISSEPH = False

SIGNS = [
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

SIGN_GLYPHS = {
    "Aries": "♈",
    "Taurus": "♉",
    "Gemini": "♊",
    "Cancer": "♋",
    "Leo": "♌",
    "Virgo": "♍",
    "Libra": "♎",
    "Scorpio": "♏",
    "Sagittarius": "♐",
    "Capricorn": "♑",
    "Aquarius": "♒",
    "Pisces": "♓",
}

PLANET_INFO: dict[str, dict[str, Any]] = {
    "sun": {
        "name": "Sun",
        "glyph": "☉",
        "swe_id": 0,
        "color": "#f59e0b",
        "esoteric_quality": "Atman · Radiance · Sovereign Consciousness",
    },
    "moon": {
        "name": "Moon",
        "glyph": "☽",
        "swe_id": 1,
        "color": "#e2e8f0",
        "esoteric_quality": "Soma · Mind (Manas) · Subconscious Tides",
    },
    "mercury": {
        "name": "Mercury",
        "glyph": "☿",
        "swe_id": 2,
        "color": "#10b981",
        "esoteric_quality": "Budha · Discriminating Intellect (Buddhi)",
    },
    "venus": {
        "name": "Venus",
        "glyph": "♀",
        "swe_id": 3,
        "color": "#f472b6",
        "esoteric_quality": "Shukra · Harmonics · Divine Beauty & Devotion",
    },
    "mars": {
        "name": "Mars",
        "glyph": "♂",
        "swe_id": 4,
        "color": "#ef4444",
        "esoteric_quality": "Mangala · Focused Will · Courageous Transmission",
    },
    "jupiter": {
        "name": "Jupiter",
        "glyph": "♃",
        "swe_id": 5,
        "color": "#a855f7",
        "esoteric_quality": "Guru · Expansive Grace · Wisdom & Dharma",
    },
    "saturn": {
        "name": "Saturn",
        "glyph": "♄",
        "swe_id": 6,
        "color": "#facc15",
        "esoteric_quality": "Shani · Sacred Boundary · Deep Discipline & Realization",
    },
    "uranus": {
        "name": "Uranus",
        "glyph": "♅",
        "swe_id": 7,
        "color": "#06b6d4",
        "esoteric_quality": "Awakening Lightning · Intuitive Insight",
    },
    "neptune": {
        "name": "Neptune",
        "glyph": "♆",
        "swe_id": 8,
        "color": "#38bdf8",
        "esoteric_quality": "Ocean of Clear Light · Mystical Dissolution",
    },
    "pluto": {
        "name": "Pluto",
        "glyph": "♇",
        "swe_id": 9,
        "color": "#8b5cf6",
        "esoteric_quality": "Primordial Transformation · Death & Rebirth",
    },
}

# Sacred Fixed Stars with their Vedic / Sanskrit correspondences
# The "ra"/"dec" values are J2000 positions (equinox J2000). The single stars
# are Yale BSC5 catalogue positions; the Pleiades entry is the exception: an
# approximate cluster-level representative (56.75, 24.11), 0.11 deg from
# Alcyone (HR 1165, 56.87, 24.105), not a BSC5 position. They are precessed to
# the equinox of date by _precess_j2000_to_date() at use time - the table
# itself stays as catalogued.
SACRED_FIXED_STARS: list[dict[str, Any]] = [
    {
        "id": "sirius",
        "name": "Sirius (Mrigavyadha / Lubdhaka)",
        "sanskrit": "मृगव्याध (Lubdhaka)",
        "ra": 101.287,
        "dec": -16.716,
        "magnitude": -1.46,
        "color": "#a6d8ff",
        "nakshatra": "Ardra / Rudra",
        "quality": "Supreme Cosmic Fire · Great Spiritual Sun",
    },
    {
        "id": "vega",
        "name": "Vega (Abhijit)",
        "sanskrit": "अभिजित् (Abhijit)",
        "ra": 279.234,
        "dec": 38.784,
        "magnitude": 0.03,
        "color": "#b5e2ff",
        "nakshatra": "Abhijit (The Victorious 28th)",
        "quality": "Unvanquished Auspiciousness · Sovereign Stillness",
    },
    {
        "id": "arcturus",
        "name": "Arcturus (Swati)",
        "sanskrit": "स्वाती (Svāti)",
        "ra": 213.915,
        "dec": 19.182,
        "magnitude": -0.05,
        "color": "#ffd79e",
        "nakshatra": "Swati (The Independent Pearl)",
        "quality": "Self-Effort · Breath of Prana · Vayu",
    },
    {
        "id": "spica",
        "name": "Spica (Chitra)",
        "sanskrit": "चित्रा (Citrā)",
        "ra": 201.298,
        "dec": -11.161,
        "magnitude": 0.98,
        "color": "#c8e1ff",
        "nakshatra": "Chitra (The Multicolored Jewel)",
        "quality": "Divine Architecture · Vishvakarma",
    },
    {
        "id": "aldebaran",
        "name": "Aldebaran (Rohini)",
        "sanskrit": "रोहिणी (Rohiṇī)",
        "ra": 68.980,
        "dec": 16.509,
        "magnitude": 0.85,
        "color": "#ff9d70",
        "nakshatra": "Rohini (The Red Empress of Brahma)",
        "quality": "Fertility · Creative Manifestation · Soma Vessel",
    },
    {
        "id": "antares",
        "name": "Antares (Jyeshtha)",
        "sanskrit": "ज्येष्ठा (Jyeṣṭhā)",
        "ra": 247.352,
        "dec": -26.432,
        "magnitude": 1.06,
        "color": "#ff6b6b",
        "nakshatra": "Jyeshtha (The Senior Elder of Indra)",
        "quality": "Spiritual Mastery · Inner Kundalini Fire",
    },
    {
        "id": "betelgeuse",
        "name": "Betelgeuse (Ardra)",
        "sanskrit": "आर्द्रा (Ārdrā)",
        "ra": 88.793,
        "dec": 7.407,
        "magnitude": 0.50,
        "color": "#ffa066",
        "nakshatra": "Ardra (Cosmic Teardrop of Compassion)",
        "quality": "Purification through Storm · Compassionate Rain",
    },
    {
        "id": "polaris",
        "name": "Polaris (Dhruva)",
        "sanskrit": "ध्रुव (Dhruva)",
        "ra": 37.954,
        "dec": 89.264,
        "magnitude": 1.98,
        "color": "#f8fafc",
        "nakshatra": "Celestial North Axis",
        "quality": "The Immovable Center · Non-Dual Steadfastness",
    },
    {
        "id": "regulus",
        "name": "Regulus (Magha)",
        "sanskrit": "मघा (Maghā)",
        "ra": 152.093,
        "dec": 11.967,
        "magnitude": 1.36,
        "color": "#cce0ff",
        "nakshatra": "Magha (The Throne of Ancestral Light)",
        "quality": "Spiritual Lineage · Pitri Blessings · Royal Heart",
    },
    {
        "id": "pleiades",
        "name": "Pleiades (Krittika)",
        "sanskrit": "कृत्तिका (Kṛttikā)",
        "ra": 56.75,
        "dec": 24.11,
        "magnitude": 1.6,
        "color": "#a5f3fc",
        "nakshatra": "Krittika (The Flame of Agni)",
        "quality": "Razor of Discernment · Purification of Karma",
    },
]


def _horizontal_unrounded(ra_deg: float, dec_deg: float, lst_deg: float, lat_deg: float) -> tuple[float, float]:
    """Altitude and azimuth, unrounded, of the equatorial place (RA, Dec) for an observer at ``lat_deg``.

    The place is taken as given: pass a topocentric RA/Dec (see :func:`_topocentric_equatorial`) to get
    what the observer sees, or a geocentric one (the stars, whose parallax is nil) to get the direction
    from the Earth's centre.
    """
    h_rad = math.radians((lst_deg - ra_deg) % 360.0)
    lat_rad = math.radians(lat_deg)
    dec_rad = math.radians(dec_deg)

    sin_alt = math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(h_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt_deg = math.degrees(math.asin(sin_alt))

    y = -math.cos(dec_rad) * math.sin(h_rad)
    x = math.sin(dec_rad) * math.cos(lat_rad) - math.cos(dec_rad) * math.sin(lat_rad) * math.cos(h_rad)
    az_deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

    return alt_deg, az_deg


def _equatorial_to_horizontal(ra_deg: float, dec_deg: float, lst_deg: float, lat_deg: float) -> tuple[float, float]:
    """Convert Right Ascension and Declination to Altitude and Azimuth, rounded to 2 decimals."""
    alt_deg, az_deg = _horizontal_unrounded(ra_deg, dec_deg, lst_deg, lat_deg)
    return round(alt_deg, 2), round(az_deg, 2)


# Meeus, Astronomical Algorithms ch. 40: the Earth's equatorial horizontal parallax is 8.794" at
# 1 AU, so a body Δ AU away has sin(π) = sin(8.794") / Δ (the Earth's equatorial radius in AU is sin(8.794")).
_SIN_PARALLAX_AT_1_AU = math.sin(math.radians(8.794 / 3600.0))
# Meeus ch. 11: polar / equatorial radius b/a = 1 - f for the IAU 1976 flattening f = 1/298.257.
_EARTH_AXIS_RATIO = 0.99664719


def _observer_terms(lat_deg: float) -> tuple[float, float]:
    """Meeus ch. 11: ρ·sin(φ') and ρ·cos(φ') for an observer at sea level at geodetic latitude ``lat_deg``.

    φ' is the geocentric latitude and ρ the distance from the Earth's centre in equatorial radii. The
    geodetic latitude is the one a map or GPS gives, and the request's ``latitude``.
    """
    lat_rad = math.radians(lat_deg)
    u = math.atan2(_EARTH_AXIS_RATIO * math.sin(lat_rad), math.cos(lat_rad))
    return _EARTH_AXIS_RATIO * math.sin(u), math.cos(u)


def _topocentric_equatorial(
    ra_deg: float, dec_deg: float, distance_au: float, lst_deg: float, lat_deg: float
) -> tuple[float, float]:
    """Right ascension and declination of a body as seen from the observer's place (diurnal parallax).

    Meeus ch. 40. ``ra_deg``/``dec_deg``/``distance_au`` are the body's geocentric apparent place and
    distance (what ``swe.calc_ut(..., FLG_EQUATORIAL)`` returns), ``lst_deg`` the local apparent sidereal
    time and ``lat_deg`` the observer's geodetic latitude (height 0). Pure: no ephemeris, no global state.
    """
    if not (math.isfinite(distance_au) and distance_au > 0.0):
        raise ValueError(f"distance must be a positive, finite number of AU, got {distance_au!r}")
    sin_parallax = _SIN_PARALLAX_AT_1_AU / distance_au
    rho_sin, rho_cos = _observer_terms(lat_deg)
    hour_angle = math.radians((lst_deg - ra_deg) % 360.0)
    dec = math.radians(dec_deg)
    denominator = math.cos(dec) - rho_cos * sin_parallax * math.cos(hour_angle)
    delta_ra = math.atan2(-rho_cos * sin_parallax * math.sin(hour_angle), denominator)
    topo_dec = math.atan2((math.sin(dec) - rho_sin * sin_parallax) * math.cos(delta_ra), denominator)
    return (ra_deg + math.degrees(delta_ra)) % 360.0, math.degrees(topo_dec)


def _topocentric_horizontal(
    ra_deg: float, dec_deg: float, distance_au: float, lst_deg: float, lat_deg: float
) -> tuple[float, float]:
    """Unrounded altitude and azimuth of a body as seen from the observer's place (parallax applied)."""
    topo_ra, topo_dec = _topocentric_equatorial(ra_deg, dec_deg, distance_au, lst_deg, lat_deg)
    return _horizontal_unrounded(topo_ra, topo_dec, lst_deg, lat_deg)


def _precess_j2000_to_date(ra_deg: float, dec_deg: float, jd: float) -> tuple[float, float]:
    """Precess a J2000 catalogue position to the mean equinox of date.

    IAU 1976 (Lieske et al. 1977) precession angles zeta, z and theta, with
    T in Julian centuries from J2000. The angles are carried in DEGREES for
    the RA/Dec arithmetic and converted to radians only inside the
    trigonometry: adding a radian-valued zeta to a degree-valued RA shrinks
    the precession by 57x, which is the mistake this helper exists to prevent.

    Nutation and aberration are ignored, each below ~0.006 deg. Proper motion
    is not modelled either (the catalogue carries none): it is small for most
    stars, but a few fast ones exceed that - Arcturus moves about 2.3 arcsec/yr,
    roughly 0.017 deg over 26 years and 0.13 deg at either end of 1800-2200.
    """
    t = (jd - 2451545.0) / 36525.0
    zeta_deg = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t**3) / 3600.0
    z_deg = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t**3) / 3600.0
    theta_deg = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t**3) / 3600.0

    a = math.radians(ra_deg + zeta_deg)
    d = math.radians(dec_deg)
    theta = math.radians(theta_deg)

    sin_dec = math.sin(d) * math.cos(theta) + math.cos(d) * math.sin(theta) * math.cos(a)
    dec_of_date = math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))
    numerator = math.cos(d) * math.sin(a)
    denominator = math.cos(theta) * math.cos(d) * math.cos(a) - math.sin(theta) * math.sin(d)
    ra_of_date = (z_deg + math.degrees(math.atan2(numerator, denominator))) % 360.0

    return ra_of_date, dec_of_date


def calculate_night_sky(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    dt: datetime | None = None,
) -> dict[str, Any]:
    """Calculate the real-time visible celestial dome above (latitude, longitude).

    The Sun, Moon and planets' ``altitude``/``azimuth`` are topocentric: corrected for the diurnal
    parallax of an observer at sea level at ``latitude`` (the Moon sits up to ~1° lower than its
    geocentric place, the Sun 8.8" and the planets less than 32"). ``right_ascension`` and
    ``declination`` stay geocentric apparent. ``position_frame`` says which frame the
    altitude/azimuth are in: ``"topocentric"`` normally, ``"geocentric"`` for the approximate
    fallback used when the Swiss Ephemeris is missing (it has no distances to correct with).
    Altitudes are geometric: no atmospheric refraction.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Compute Julian day
    hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3.6e9
    if HAS_SWISSEPH and swe is not None:
        tjd_ut = swe.julday(dt.year, dt.month, dt.day, hour_decimal)
        gast_hours = swe.sidtime(tjd_ut)
        lst_deg = (gast_hours * 15.0 + longitude) % 360.0
    else:
        # Fallback approximate Julian Day and GMST
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3
        jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        tjd_ut = jdn - 0.5 + hour_decimal / 24.0
        d = tjd_ut - 2451545.0
        gmst = (18.697374558 + 24.06570982441908 * d) % 24.0
        lst_deg = (gmst * 15.0 + longitude) % 360.0

    lst_hours = lst_deg / 15.0
    h = int(lst_hours)
    m = int((lst_hours - h) * 60)
    s = int(round(((lst_hours - h) * 60 - m) * 60))
    lst_hms = f"{h:02d}:{m:02d}:{s:02d}"

    planets: list[dict[str, Any]] = []
    sun_lon_ecl = 0.0
    moon_lon_ecl = 0.0
    position_frame = "topocentric" if HAS_SWISSEPH and swe is not None else "geocentric"

    for pid, info in PLANET_INFO.items():
        if HAS_SWISSEPH and swe is not None:
            # Equatorial, geocentric apparent; the distance (AU) is what the parallax needs
            xx_eq, _ = swe.calc_ut(tjd_ut, info["swe_id"], swe.FLG_EQUATORIAL)
            ra_deg, dec_deg, distance_au = xx_eq[0], xx_eq[1], xx_eq[2]
            # Ecliptic for sign
            xx_ecl, _ = swe.calc_ut(tjd_ut, info["swe_id"], 0)
            lon_ecl = xx_ecl[0]
            if pid == "sun":
                sun_lon_ecl = lon_ecl
            elif pid == "moon":
                moon_lon_ecl = lon_ecl
            topo_alt, topo_az = _topocentric_horizontal(ra_deg, dec_deg, distance_au, lst_deg, latitude)
            alt_deg, az_deg = round(topo_alt, 2), round(topo_az, 2)
        else:
            # Deterministic fallback positions (no distances, so no parallax: see position_frame)
            lon_ecl = (info["swe_id"] * 36.0 + dt.timetuple().tm_yday) % 360.0
            ra_deg = lon_ecl
            dec_deg = 23.44 * math.sin(math.radians(lon_ecl))
            alt_deg, az_deg = _equatorial_to_horizontal(ra_deg, dec_deg, lst_deg, latitude)

        sign_idx = int(lon_ecl // 30) % 12
        sign_name = SIGNS[sign_idx]

        planets.append(
            {
                "id": pid,
                "name": info["name"],
                "glyph": info["glyph"],
                "altitude": alt_deg,
                "azimuth": az_deg,
                "right_ascension": round(ra_deg, 2),
                "declination": round(dec_deg, 2),
                "longitude_ecliptic": round(lon_ecl, 2),
                "sign": sign_name,
                "sign_glyph": SIGN_GLYPHS.get(sign_name, ""),
                "sign_degree": round(lon_ecl % 30, 2),
                "visible": alt_deg > 0.0,
                "color": info["color"],
                "esoteric_quality": info["esoteric_quality"],
            }
        )

    # Moon phase & illumination
    phase_angle = (moon_lon_ecl - sun_lon_ecl) % 360.0
    illumination = round((1.0 - math.cos(math.radians(phase_angle))) / 2.0 * 100.0, 1)
    phase_names = [
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    ]
    phase_idx = int(((phase_angle + 22.5) % 360.0) // 45)
    moon_phase_name = phase_names[phase_idx]

    moon_entry = next((p for p in planets if p["id"] == "moon"), None)
    moon_data = {
        "altitude": moon_entry["altitude"] if moon_entry else 0.0,
        "azimuth": moon_entry["azimuth"] if moon_entry else 0.0,
        "phase_name": moon_phase_name,
        "illumination": illumination,
        "illumination_pct": illumination,
        "visible": moon_entry["visible"] if moon_entry else False,
        "sign": moon_entry["sign"] if moon_entry else "Aries",
    }

    # Sacred Stars: the table is catalogued at J2000, so precess each star to
    # the equinox of date before pairing it with the of-date sidereal time.
    stars: list[dict[str, Any]] = []
    for s in SACRED_FIXED_STARS:
        ra_deg, dec_deg = _precess_j2000_to_date(s["ra"], s["dec"], tjd_ut)
        alt_deg, az_deg = _equatorial_to_horizontal(ra_deg, dec_deg, lst_deg, latitude)
        stars.append(
            {
                "id": s["id"],
                "name": s["name"],
                "sanskrit": s["sanskrit"],
                "altitude": alt_deg,
                "azimuth": az_deg,
                "magnitude": s["magnitude"],
                # The table's J2000 position, no precession applied, so a client can precess it to
                # another instant itself. The Pleiades value is a cluster-level representative.
                "ra_j2000": round(s["ra"], 4),
                "dec_j2000": round(s["dec"], 4),
                "visible": alt_deg > 0.0,
                "color": s["color"],
                "nakshatra": s["nakshatra"],
                "quality": s["quality"],
                "zenith_distance": round(max(0.0, 90.0 - alt_deg), 2),
            }
        )

    visible_planets = [p for p in planets if p["visible"]]
    visible_stars = [s for s in stars if s["visible"]]

    return {
        "status": "success",
        "timestamp_utc": dt.isoformat(),
        "observer": {
            "latitude": latitude,
            "longitude": longitude,
            "local_sidereal_time_deg": round(lst_deg, 2),
            "local_sidereal_time_hms": lst_hms,
        },
        "moon": moon_data,
        "planets": planets,
        "visible_planets_count": len(visible_planets),
        "sacred_stars": stars,
        "visible_stars_count": len(visible_stars),
        "position_frame": position_frame,
    }
