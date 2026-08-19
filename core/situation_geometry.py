"""
core.situation_geometry — Canonical coordinates and spatial defaults for Vajra.Stream.

Single source of truth for geographical defaults across backend services,
mirrored in frontend/src/lib/geo.ts (DEFAULT_LAT / DEFAULT_LNG).
"""

from __future__ import annotations

import logging
import re

from config.settings import DEFAULT_LATITUDE, DEFAULT_LONGITUDE

logger = logging.getLogger(__name__)

DEFAULT_LAT = DEFAULT_LATITUDE
DEFAULT_LNG = DEFAULT_LONGITUDE
DEFAULT_COORDS = (DEFAULT_LATITUDE, DEFAULT_LONGITUDE)

# Abstract / Universal targets that represent the whole field (honesty rule: no fake pin)
NON_GEOGRAPHIC_TARGETS = {
    "all beings",
    "all sentient beings",
    "the field",
    "field",
    "world peace",
    "universe",
    "sentient beings",
    "cosmos",
    "earth",
    "all life",
    "the planet",
}

# Canonical known location dictionary (lat, lon)
KNOWN_LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "japan": (36.0, 138.0),
    "tokyo": (35.6762, 139.6503),
    "osaka": (34.6937, 135.5023),
    "indonesia": (-2.0, 118.0),
    "bali": (-8.4095, 115.1889),
    "java": (-7.6145, 110.7122),
    "sumatra": (-0.5897, 101.3431),
    "sulawesi": (-1.4300, 121.4456),
    "jakarta": (-6.2088, 106.8456),
    "philippines": (13.0, 122.0),
    "manila": (14.5995, 120.9842),
    "cebu": (10.3157, 123.8854),
    "china": (35.0, 105.0),
    "beijing": (39.9042, 116.4074),
    "shanghai": (31.2304, 121.4737),
    "tibet": (31.6927, 88.0924),
    "lhasa": (29.6525, 91.1721),
    "sichuan": (30.6517, 104.0764),
    "india": (20.0, 78.0),
    "dharamsala": (32.2190, 76.3234),
    "bodh gaya": (24.6961, 84.9869),
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "nepal": (28.0, 84.0),
    "kathmandu": (27.7172, 85.3240),
    "lumbini": (27.4842, 83.2760),
    "bhutan": (27.5142, 90.4336),
    "thimphu": (27.4728, 89.6393),
    "turkey": (39.0, 35.0),
    "istanbul": (41.0082, 28.9784),
    "ankara": (39.9334, 32.8597),
    "iran": (32.0, 53.0),
    "tehran": (35.6892, 51.3890),
    "pakistan": (30.0, 70.0),
    "islamabad": (33.6844, 73.0479),
    "mexico": (23.0, -102.0),
    "mexico city": (19.4326, -99.1332),
    "oaxaca": (17.0732, -96.7266),
    "united states": (38.0, -97.0),
    "usa": (38.0, -97.0),
    "us": (38.0, -97.0),
    "california": (36.7783, -119.4179),
    "los angeles": (34.0522, -118.2437),
    "san francisco": (37.7749, -122.4194),
    "new york": (40.7128, -74.0060),
    "hawaii": (19.8968, -155.5828),
    "alaska": (64.2008, -149.4937),
    "chile": (-35.0, -71.0),
    "santiago": (-33.4489, -70.6693),
    "peru": (-10.0, -76.0),
    "lima": (-12.0464, -77.0428),
    "ecuador": (-2.0, -77.0),
    "quito": (-0.1807, -78.4678),
    "italy": (42.0, 13.0),
    "rome": (41.9028, 12.4964),
    "greece": (39.0, 22.0),
    "athens": (37.9838, 23.7275),
    "iceland": (65.0, -18.0),
    "reykjavik": (64.1466, -21.9426),
    "new zealand": (-41.0, 174.0),
    "auckland": (-36.8485, 174.7633),
    "papua new guinea": (-6.0, 144.0),
    "solomon islands": (-9.6457, 160.1562),
    "fiji": (-17.7134, 178.0650),
    "tonga": (-21.1789, -175.1982),
    "vanuatu": (-15.3767, 166.9592),
    "myanmar": (22.0, 96.0),
    "yangon": (16.8661, 96.1951),
    "bangladesh": (24.0, 90.0),
    "dhaka": (23.8103, 90.4125),
    "thailand": (15.0, 101.0),
    "bangkok": (13.7563, 100.5018),
    "chiang mai": (18.7883, 98.9853),
    "vietnam": (14.0, 108.0),
    "hanoi": (21.0285, 105.8542),
    "afghanistan": (34.0, 67.0),
    "kabul": (34.5553, 69.2075),
    "iraq": (33.0, 44.0),
    "baghdad": (33.3152, 44.3661),
    "syria": (35.0, 39.0),
    "damascus": (33.5138, 36.2765),
    "yemen": (15.0, 48.0),
    "sanaa": (15.3694, 44.1910),
    "sudan": (15.0, 30.0),
    "khartoum": (15.5007, 32.5599),
    "ethiopia": (9.0, 40.0),
    "addis ababa": (9.0320, 38.7482),
    "somalia": (6.0, 47.0),
    "mogadishu": (2.0469, 45.3182),
    "congo": (-4.0, 22.0),
    "drc": (-4.0383, 21.7587),
    "democratic republic of the congo": (-4.0383, 21.7587),
    "rwanda": (-1.9403, 29.8739),
    "kigali": (-1.9441, 30.0619),
    "nigeria": (9.0, 8.0),
    "lagos": (6.5244, 3.3792),
    "ukraine": (49.0, 31.0),
    "kyiv": (50.4501, 30.5234),
    "gaza": (31.5017, 34.4668),
    "palestine": (31.9522, 35.2332),
    "israel": (31.0461, 34.8516),
    "jerusalem": (31.7683, 35.2137),
    "lebanon": (33.8547, 35.8623),
    "beirut": (33.8938, 35.5018),
    "haiti": (19.0, -72.0),
    "port-au-prince": (18.5944, -72.3074),
    "colombia": (4.0, -72.0),
    "bogota": (4.7110, -74.0721),
    "venezuela": (7.0, -66.0),
    "caracas": (10.4806, -66.9036),
    "brazil": (-10.0, -55.0),
    "rio de janeiro": (-22.9068, -43.1729),
    "sao paulo": (-23.5505, -46.6333),
    "argentina": (-34.0, -64.0),
    "buenos aires": (-34.6037, -58.3816),
    "australia": (-25.0, 135.0),
    "sydney": (-33.8688, 151.2093),
    "melbourne": (-37.8136, 144.9631),
    "france": (47.0, 2.0),
    "paris": (48.8566, 2.3522),
    "germany": (51.0, 10.0),
    "berlin": (52.5200, 13.4050),
    "spain": (40.0, -4.0),
    "madrid": (40.4168, -3.7038),
    "portugal": (39.0, -8.0),
    "lisbon": (38.7223, -9.1393),
    "morocco": (32.0, -6.0),
    "marrakech": (31.6295, -7.9811),
    "algeria": (28.0, 3.0),
    "algiers": (36.7538, 3.0588),
    "egypt": (27.0, 30.0),
    "cairo": (30.0444, 31.2357),
    "south africa": (-29.0, 24.0),
    "cape town": (-33.9249, 18.4241),
    "kenya": (0.0, 38.0),
    "nairobi": (-1.2921, 36.8219),
    "tanzania": (-6.0, 35.0),
    "madagascar": (-20.0, 47.0),
    "canada": (56.0, -106.0),
    "vancouver": (49.2827, -123.1207),
    "toronto": (43.6532, -79.3832),
    "russia": (61.0, 95.0),
    "moscow": (55.7558, 37.6173),
    "south korea": (36.0, 128.0),
    "seoul": (37.5665, 126.9780),
    "north korea": (40.0, 127.0),
    "pyongyang": (39.0392, 125.7625),
    "taiwan": (23.5, 121.0),
    "taipei": (25.0330, 121.5654),
    "malaysia": (4.0, 102.0),
    "kuala lumpur": (3.1390, 101.6869),
    "singapore": (1.3521, 103.8198),
    "united kingdom": (55.0, -3.0),
    "uk": (55.0, -3.0),
    "london": (51.5074, -0.1278),
    "uae": (23.4241, 53.8478),
    "dubai": (25.2048, 55.2708),
    "mongolia": (46.8625, 103.8467),
    "sri lanka": (7.8731, 80.7718),
    "colombo": (6.9271, 79.8612),
}

# Sorted keys by length descending
_SORTED_GEO_KEYS = sorted(KNOWN_LOCATION_COORDS.keys(), key=len, reverse=True)

# In-memory target resolution cache (target_string -> (lat, lon) or None)
_RESOLVE_CACHE: dict[str, tuple[float, float] | None] = {}


def resolve_target_coordinates(target_str: str | None, allow_geocoding: bool = True) -> tuple[float, float] | None:
    """
    Resolve a target or intention string to (latitude, longitude).
    Follows honesty rules: returns None for abstract/universal targets ('all beings').

    Resolution order:
    1. Direct match in KNOWN_LOCATION_COORDS.
    2. Segmented / substring match against KNOWN_LOCATION_COORDS.
    3. Live GeocodingService lookup via Nominatim (with LRU caching).
    """
    if not target_str:
        return None

    clean = re.sub(r"[()[\]#\-_/]", " ", target_str.lower())
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean or clean in NON_GEOGRAPHIC_TARGETS:
        return None

    if clean in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[clean]

    # 1. Direct match
    if clean in KNOWN_LOCATION_COORDS:
        coords = KNOWN_LOCATION_COORDS[clean]
        _RESOLVE_CACHE[clean] = coords
        return coords

    # 2. Segment match (e.g. "East Java, Indonesia" -> checks "East Java" first)
    segments = [s.strip() for s in re.split(r"[,;]+", clean) if s.strip()]
    if len(segments) > 1:
        for seg in segments:
            if seg in KNOWN_LOCATION_COORDS:
                coords = KNOWN_LOCATION_COORDS[seg]
                _RESOLVE_CACHE[clean] = coords
                return coords
            for key in _SORTED_GEO_KEYS:
                if re.search(rf"\b{re.escape(key)}\b", seg, re.IGNORECASE):
                    coords = KNOWN_LOCATION_COORDS[key]
                    _RESOLVE_CACHE[clean] = coords
                    return coords

    # 3. Longest word-boundary match across full string
    for key in _SORTED_GEO_KEYS:
        if re.search(rf"\b{re.escape(key)}\b", clean, re.IGNORECASE):
            coords = KNOWN_LOCATION_COORDS[key]
            _RESOLVE_CACHE[clean] = coords
            return coords

    # 4. Token match (tokens longer than 2 chars)
    tokens = [t for t in re.split(r"\s+", clean) if len(t) > 2]
    for token in tokens:
        if token in KNOWN_LOCATION_COORDS:
            coords = KNOWN_LOCATION_COORDS[token]
            _RESOLVE_CACHE[clean] = coords
            return coords

    # 5. Geocoding Service fallback if enabled
    if allow_geocoding:
        try:
            from backend.core.services.geocoding_service import geocoding_service

            res = geocoding_service.get_coordinates_and_timezone(target_str)
            if res and "latitude" in res and "longitude" in res:
                coords = (float(res["latitude"]), float(res["longitude"]))
                _RESOLVE_CACHE[clean] = coords
                return coords
        except Exception as e:
            logger.debug("Geocoding lookup failed for '%s': %s", target_str, e)

    _RESOLVE_CACHE[clean] = None
    return None


__all__ = [
    "DEFAULT_LAT",
    "DEFAULT_LNG",
    "DEFAULT_LATITUDE",
    "DEFAULT_LONGITUDE",
    "DEFAULT_COORDS",
    "KNOWN_LOCATION_COORDS",
    "NON_GEOGRAPHIC_TARGETS",
    "resolve_target_coordinates",
]
