"""
Tests for core.celestial_sky — topocentric celestial night-sky dome calculations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from core.celestial_sky import PLANET_INFO, SACRED_FIXED_STARS, calculate_night_sky


@pytest.mark.unit
def test_calculate_night_sky_structure():
    """calculate_night_sky returns a complete dictionary with observer, moon, planets, and stars."""
    dt = datetime(2026, 9, 6, 21, 0, 0, tzinfo=timezone.utc)
    res = calculate_night_sky(latitude=37.7749, longitude=-122.4194, dt=dt)

    assert "timestamp_utc" in res
    assert "observer" in res
    assert "moon" in res
    assert "planets" in res
    assert "sacred_stars" in res

    obs = res["observer"]
    assert obs["latitude"] == 37.7749
    assert obs["longitude"] == -122.4194
    assert "local_sidereal_time_deg" in obs
    assert "local_sidereal_time_hms" in obs

    # Planets count matches PLANET_INFO
    assert len(res["planets"]) == len(PLANET_INFO)
    for p in res["planets"]:
        assert "id" in p
        assert "name" in p
        assert "glyph" in p
        assert -90.0 <= p["altitude"] <= 90.0
        assert 0.0 <= p["azimuth"] <= 360.0
        assert "sign" in p
        assert "visible" in p
        assert isinstance(p["visible"], bool)

    # Moon data
    moon = res["moon"]
    assert "phase_name" in moon
    assert 0.0 <= moon["illumination"] <= 100.0
    assert "altitude" in moon

    # Stars count matches SACRED_FIXED_STARS
    assert len(res["sacred_stars"]) == len(SACRED_FIXED_STARS)
    for s in res["sacred_stars"]:
        assert "id" in s
        assert "name" in s
        assert "sanskrit" in s
        assert -90.0 <= s["altitude"] <= 90.0
        assert 0.0 <= s["azimuth"] <= 360.0
        assert "nakshatra" in s
        assert "quality" in s


@pytest.mark.unit
def test_calculate_night_sky_polaris_near_latitude():
    """Polaris altitude should closely approximate observer latitude in Northern hemisphere."""
    lat = 37.7749
    lon = -122.4194
    dt = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    res = calculate_night_sky(latitude=lat, longitude=lon, dt=dt)

    polaris = next((s for s in res["sacred_stars"] if s["id"] == "polaris"), None)
    assert polaris is not None
    # Polaris Dec is ~89.26°, so its altitude should be within 1.5° of latitude
    assert abs(polaris["altitude"] - lat) < 1.5


# ---------------------------------------------------------------------------
# W2-E - the sacred fixed stars are catalogued at J2000 and must be precessed
# to the equinox of date before they are turned into alt/az.
#
# The literals below are copied from the frozen independent astropy oracle
# docs/notes/earthsky/wave2/oracle/oracle_stars.json, VARIANT A (the full
# ICRS -> AltAz chain: precession + nutation + aberration, pressure=0, no
# refraction). The oracle file is never imported by the test.
#
# Subset rule (deliberate, not accidental):
#   instants - the three the row names: 1800-01-01, 2026-10-22T02:00Z and
#              2199-12-31 (both ends of the catalogue's span, and today);
#   places   - five of the oracle's eleven: San Francisco (the app's
#              default), Reykjavik and Tromso (north; Tromso is inside the
#              arctic circle), McMurdo (south polar) and Cape Town (southern
#              mid-latitude);
#   stars    - the seven sacred stars the oracle carries. Aldebaran and
#              Regulus are not in the oracle's star set and the Pleiades are
#              a cluster rather than one catalogue star, so those three are
#              covered by the rigidity test instead.
#
# Tolerance 0.02 deg: precession-only sits within 0.0101 deg of variant A
# (nutation + aberration, per the oracle report) and the backend's own sidereal
# time agrees with the oracle's apparent LST to 0.0066 deg (same report).
# ---------------------------------------------------------------------------

_SACRED_ORACLE_STARS = ("sirius", "vega", "arcturus", "spica", "antares", "betelgeuse", "polaris")

_ORACLE_INSTANT_PLACES = {
    "1800-01-01T00:00:00Z": (
        ("San Francisco", 37.7749, -122.4194),
        ("Reykjavik", 64.15, -21.94),
        ("Tromso", 69.65, 18.96),
        ("McMurdo", -77.85, 166.67),
        ("Cape Town", -33.92, 18.42),
    ),
    "2026-10-22T02:00:00Z": (
        ("San Francisco", 37.7749, -122.4194),
        ("Reykjavik", 64.15, -21.94),
        ("Tromso", 69.65, 18.96),
        ("McMurdo", -77.85, 166.67),
        ("Cape Town", -33.92, 18.42),
    ),
    "2199-12-31T23:59:00Z": (
        ("San Francisco", 37.7749, -122.4194),
        ("Reykjavik", 64.15, -21.94),
        ("Tromso", 69.65, 18.96),
        ("McMurdo", -77.85, 166.67),
        ("Cape Town", -33.92, 18.42),
    ),
}

_ORACLE_LITERALS = {
    "1800-01-01T00:00:00Z": {
        "San Francisco": {
            "sirius": (-34.4236, 84.5458),
            "vega": (43.3961, 290.7282),
            "arcturus": (-13.2927, 309.065),
            "spica": (-44.2411, 296.3985),
            "antares": (-18.3097, 250.8991),
            "betelgeuse": (-9.5088, 72.8958),
            "polaris": (39.2026, 1.3032),
        },
        "Reykjavik": {
            "sirius": (7.7842, 160.0993),
            "vega": (13.8711, 344.7428),
            "arcturus": (1.7052, 43.3044),
            "spica": (-21.9596, 66.5487),
            "antares": (-50.7321, 20.3599),
            "betelgeuse": (32.9471, 170.9726),
            "polaris": (64.835, 356.2482),
        },
        "Tromso": {
            "sirius": (2.6434, 199.4534),
            "vega": (19.4464, 17.9328),
            "arcturus": (18.0539, 80.7111),
            "spica": (-5.8015, 103.5106),
            "antares": (-36.1297, 65.8708),
            "betelgeuse": (24.1074, 216.5884),
            "polaris": (69.0942, 355.2747),
        },
        "McMurdo": {
            "sirius": (4.6205, 191.5221),
            "vega": (-26.644, 9.1453),
            "arcturus": (-12.9623, 307.426),
            "spica": (14.3541, 289.1112),
            "antares": (37.0579, 334.1292),
            "betelgeuse": (-19.507, 178.9682),
            "polaris": (-78.2157, 8.2838),
        },
        "Cape Town": {
            "sirius": (65.1434, 309.5332),
            "vega": (-72.2615, 68.5082),
            "arcturus": (-13.252, 74.4881),
            "spica": (14.0097, 92.884),
            "antares": (-10.8573, 131.7913),
            "betelgeuse": (38.3773, 316.841),
            "polaris": (-34.3779, 357.9534),
        },
    },
    "2026-10-22T02:00:00Z": {
        "San Francisco": {
            "sirius": (-64.4401, 39.1209),
            "vega": (75.3533, 279.821),
            "arcturus": (16.2416, 281.8021),
            "spica": (-11.9577, 264.8788),
            "antares": (10.2663, 224.449),
            "betelgeuse": (-37.3636, 37.1447),
            "polaris": (37.5687, 0.7448),
        },
        "Reykjavik": {
            "sirius": (-3.996, 121.2001),
            "vega": (23.4943, 312.0795),
            "arcturus": (-6.7223, 4.1477),
            "spica": (-35.8281, 20.6299),
            "antares": (-47.9149, 319.3848),
            "betelgeuse": (22.9978, 123.6801),
            "polaris": (64.7673, 0.2185),
        },
        "Tromso": {
            "sirius": (2.2053, 158.8614),
            "vega": (19.4478, 343.6043),
            "arcturus": (4.2892, 42.3175),
            "spica": (-21.4227, 63.0914),
            "antares": (-46.2997, 15.2623),
            "betelgeuse": (27.4461, 169.1753),
            "polaris": (70.175, 359.0154),
        },
        "McMurdo": {
            "sirius": (9.4531, 232.1212),
            "vega": (-30.8191, 45.8534),
            "arcturus": (-7.2019, 347.6549),
            "spica": (22.1954, 332.8242),
            "antares": (37.7656, 23.4351),
            "betelgeuse": (-16.3391, 223.7096),
            "polaris": (-78.4745, 0.0021),
        },
        "Cape Town": {
            "sirius": (63.3958, 55.4189),
            "vega": (-72.8158, 292.4497),
            "arcturus": (-47.6926, 98.8727),
            "spica": (-19.2878, 119.0455),
            "antares": (-28.6639, 168.5889),
            "betelgeuse": (47.5474, 15.1033),
            "polaris": (-33.3886, 359.6061),
        },
    },
    "2199-12-31T23:59:00Z": {
        "San Francisco": {
            "sirius": (-38.2858, 81.8584),
            "vega": (46.0933, 290.0275),
            "arcturus": (-11.6065, 304.338),
            "spica": (-41.6887, 289.4228),
            "antares": (-14.1668, 246.8396),
            "betelgeuse": (-13.6257, 69.1727),
            "polaris": (37.0846, 0.2631),
        },
        "Reykjavik": {
            "sirius": (6.5976, 155.8006),
            "vega": (14.6633, 342.0334),
            "arcturus": (-1.4441, 39.5318),
            "spica": (-25.9887, 62.1275),
            "antares": (-52.3324, 11.5798),
            "betelgeuse": (32.4752, 164.4593),
            "polaris": (64.4743, 1.4862),
        },
        "Tromso": {
            "sirius": (2.6796, 195.022),
            "vega": (19.4615, 15.0241),
            "arcturus": (14.687, 76.9799),
            "spica": (-9.5929, 99.2088),
            "antares": (-38.8714, 59.5871),
            "betelgeuse": (25.2168, 210.6605),
            "polaris": (70.3183, 0.7921),
        },
        "McMurdo": {
            "sirius": (5.2897, 195.9145),
            "vega": (-27.1414, 12.1697),
            "arcturus": (-10.3607, 311.6832),
            "spica": (17.4463, 294.0964),
            "antares": (38.4115, 341.116),
            "betelgeuse": (-19.5112, 184.8032),
            "polaris": (-78.2596, 357.1317),
        },
        "Cape Town": {
            "sirius": (68.2577, 317.5094),
            "vega": (-74.8559, 65.3547),
            "arcturus": (-16.1828, 78.5667),
            "spica": (10.6538, 97.6068),
            "antares": (-13.9517, 136.6779),
            "betelgeuse": (41.3087, 322.9048),
            "polaris": (-33.2521, 0.3266),
        },
    },
}


def _great_circle_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle separation of two points given as (latitude, longitude)-like pairs in degrees.

    The same formula serves equatorial (dec, ra) and horizontal (alt, az)
    coordinates: both are latitude/longitude on the same celestial sphere.
    """
    p1 = (
        math.cos(math.radians(lat1)) * math.cos(math.radians(lon1)),
        math.cos(math.radians(lat1)) * math.sin(math.radians(lon1)),
        math.sin(math.radians(lat1)),
    )
    p2 = (
        math.cos(math.radians(lat2)) * math.cos(math.radians(lon2)),
        math.cos(math.radians(lat2)) * math.sin(math.radians(lon2)),
        math.sin(math.radians(lat2)),
    )
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(p1, p2))))
    return math.degrees(math.acos(dot))


def _horizontal_from_equatorial(ra_deg: float, dec_deg: float, lst_deg: float, lat_deg: float) -> tuple[float, float]:
    """Plain spherical-trig alt/az, written out here so the negative control does not lean on the code under test."""
    h = math.radians((lst_deg - ra_deg) % 360.0)
    dec = math.radians(dec_deg)
    lat = math.radians(lat_deg)
    sin_alt = math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(h)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    y = -math.cos(dec) * math.sin(h)
    x = math.sin(dec) * math.cos(lat) - math.cos(dec) * math.sin(lat) * math.cos(h)
    return alt, math.degrees(math.atan2(y, x)) % 360.0


@pytest.mark.unit
def test_sacred_stars_match_the_oracle_altaz():
    """Every oracle-covered sacred star lands on astropy's altitude/azimuth."""
    for instant, places in _ORACLE_INSTANT_PLACES.items():
        dt = datetime.fromisoformat(instant.replace("Z", "+00:00"))
        for place, lat, lon in places:
            res = calculate_night_sky(latitude=lat, longitude=lon, dt=dt)
            got = {s["id"]: s for s in res["sacred_stars"]}
            for star_id in _SACRED_ORACLE_STARS:
                alt_expected, az_expected = _ORACLE_LITERALS[instant][place][star_id]
                sep = _great_circle_deg(got[star_id]["altitude"], got[star_id]["azimuth"], alt_expected, az_expected)
                assert sep <= 0.02, f"{star_id} at {instant} {place}: {sep:.4f} deg from the oracle literal"


@pytest.mark.unit
def test_unprecessed_sacred_stars_miss_the_oracle():
    """Negative control: the raw J2000 table values miss the same literal by far more than 0.02 deg.

    Without this the oracle test above could pass for the wrong reason (a
    wrong-but-consistent convention); this proves the literal really does
    bite on the missing precession.
    """
    instant = "1800-01-01T00:00:00Z"
    place, lat, lon = ("Cape Town", -33.92, 18.42)
    dt = datetime.fromisoformat(instant.replace("Z", "+00:00"))
    res = calculate_night_sky(latitude=lat, longitude=lon, dt=dt)
    lst_deg = res["observer"]["local_sidereal_time_deg"]
    table = {s["id"]: s for s in SACRED_FIXED_STARS}

    misses = []
    for star_id in _SACRED_ORACLE_STARS:
        alt_expected, az_expected = _ORACLE_LITERALS[instant][place][star_id]
        alt, az = _horizontal_from_equatorial(table[star_id]["ra"], table[star_id]["dec"], lst_deg, lat)
        sep = _great_circle_deg(alt, az, alt_expected, az_expected)
        misses.append((star_id, sep))
    worst_id, worst_sep = max(misses, key=lambda item: item[1])
    assert worst_sep > 0.02, f"{worst_id} unprecessed is only {worst_sep:.4f} deg from the oracle literal"


@pytest.mark.unit
def test_sacred_stars_keep_their_sky_separations():
    """Precession is a rotation, so the angle between two stars never changes.

    This is how the Pleiades are covered: they are a cluster, not one
    catalogue star, so the oracle has no value for them. Their separation
    from a neighbour must still equal the J2000 separation.
    """
    dt = datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc)
    res = calculate_night_sky(latitude=37.7749, longitude=-122.4194, dt=dt)
    got = {s["id"]: s for s in res["sacred_stars"]}
    table = {s["id"]: s for s in SACRED_FIXED_STARS}

    for left, right in (("pleiades", "aldebaran"), ("pleiades", "sirius"), ("polaris", "vega")):
        after = _great_circle_deg(
            got[left]["altitude"], got[left]["azimuth"], got[right]["altitude"], got[right]["azimuth"]
        )
        before = _great_circle_deg(table[left]["dec"], table[left]["ra"], table[right]["dec"], table[right]["ra"])
        assert abs(after - before) <= 0.02, f"{left}-{right}: {after:.4f} deg after vs {before:.4f} deg at J2000"


@pytest.mark.unit
def test_precession_helper_is_the_identity_at_j2000():
    """The precession helper must do nothing at J2000 and must move a star by degrees, not millidegrees."""
    from core.celestial_sky import _precess_j2000_to_date

    for ra, dec in ((0.0, 0.0), (101.287, -16.716), (279.234, 38.784), (37.954, 89.264)):
        ra_out, dec_out = _precess_j2000_to_date(ra, dec, 2451545.0)
        assert abs(ra_out - ra) < 1e-9
        assert abs(dec_out - dec) < 1e-9

    # 75 years on (T = 0.75), the Lieske angles are zeta = 0.480511,
    # z = 0.480635, theta = 0.417493 deg, so the first-order shift of Sirius's
    # right ascension is zeta + z + theta*sin(alpha)*tan(dec) = 0.8382 deg.
    # Treating the angles as radians instead of degrees would shift it by
    # 0.0146 deg - 57x too little.
    ra_out, _ = _precess_j2000_to_date(101.287, -16.716, 2451545.0 + 75 * 365.25)
    assert 0.83 < abs(ra_out - 101.287) < 0.85


# ---------------------------------------------------------------------------
# W2-J - the Sun, Moon and planets must NOT be precessed.
#
# swisseph's FLG_EQUATORIAL positions are already of date, so only the fixed
# stars (catalogued at J2000) go through _precess_j2000_to_date(). The star
# tests above pass just as well if the planets are precessed too (codex W2-R3
# mutated it and all six still passed), so the planets get their own absolute
# check against values that never touch core/celestial_sky.py.
#
# Literals: the first stored sample of the range-start-1950, reference-instant
# and range-end-2049 series of the frozen independent swisseph oracle
# docs/notes/earthsky/wave3/oracle/oracle_series.json (W3-O, dev-g1; never
# imported): Greenwich apparent sidereal time in degrees and, per body, the
# sub-point (declination, longitude), 6 decimals. Right ascension is
# (longitude + GAST) mod 360 and the local sidereal time is GAST + the observer's
# east longitude; the alt/az below comes from the plain trig written in this
# file (_horizontal_from_equatorial), not from the code under test.
#
# Tolerance 0.02 deg: the live path is geocentric FLG_EQUATORIAL like the oracle,
# so the difference is the 2-decimal rounding of the payload (<= 0.007 deg).
# Precessing a planet that is already of date moves it by 0.36 deg in 2026 and
# 0.7 deg in 1950 and 2049, so the tolerance has a wide margin on both sides.
# ---------------------------------------------------------------------------

# fmt: off
_ORACLE_SUBPOINTS = {
    "1950-01-01T00:00:00Z": (100.074889, {"sun": (-23.070745, -179.190125), "moon": (24.152475, -41.623221), "mercury": (-21.471271, -158.193384), "venus": (-15.151219, -140.840023), "mars": (1.425609, 82.953053), "jupiter": (-19.219106, -151.026413), "saturn": (6.02797, 71.008585), "uranus": (23.689732, -7.145126), "neptune": (-5.311897, 96.452131), "pluto": (23.293343, 42.890947)}),
    "2026-10-22T02:00:00Z": (60.525374, {"sun": (-11.007857, 146.134973), "moon": (-8.166358, -82.026291), "mercury": (-20.950958, 166.816606), "venus": (-18.577703, 146.828615), "mars": (18.117215, 75.840007), "jupiter": (14.468023, 85.046805), "saturn": (1.457574, -50.312277), "uranus": (20.982867, 2.575479), "neptune": (-0.383032, -57.844113), "pluto": (-23.630336, -114.080202)}),
    "2049-12-31T00:00:00Z": (99.863937, {"sun": (-23.074502, -179.279204), "moon": (5.862345, -96.947512), "mercury": (-20.378924, 171.298866), "venus": (-23.62335, -178.950323), "mars": (-16.181367, 124.981588), "jupiter": (20.194466, 24.302209), "saturn": (-20.860346, -160.296093), "uranus": (4.392108, 71.93627), "neptune": (16.963429, -48.166724), "pluto": (-20.486817, -115.65482)}),
}
# fmt: on

_PLANET_PLACES = (("San Francisco", 37.7749, -122.4194), ("Cape Town", -33.92, 18.42))


def _oracle_altaz(instant: str, body_id: str, lat: float, lon: float) -> tuple[float, float]:
    gast, subpoints = _ORACLE_SUBPOINTS[instant]
    dec, sub_lon = subpoints[body_id]
    return _horizontal_from_equatorial((sub_lon + gast) % 360.0, dec, (gast + lon) % 360.0, lat)


@pytest.mark.unit
def test_sun_moon_and_planets_land_on_the_oracle_altaz():
    """Absolute check of the Sun, Moon and eight planets: 3 instants x 2 places x 10 bodies."""
    for instant in _ORACLE_SUBPOINTS:
        dt = datetime.fromisoformat(instant.replace("Z", "+00:00"))
        for place, lat, lon in _PLANET_PLACES:
            res = calculate_night_sky(latitude=lat, longitude=lon, dt=dt)
            got = {p["id"]: p for p in res["planets"]}
            assert set(got) == set(_ORACLE_SUBPOINTS[instant][1])
            for body_id in got:
                alt_expected, az_expected = _oracle_altaz(instant, body_id, lat, lon)
                sep = _great_circle_deg(got[body_id]["altitude"], got[body_id]["azimuth"], alt_expected, az_expected)
                assert sep <= 0.02, f"{body_id} at {instant} {place}: {sep:.4f} deg from the oracle sub-point"
            moon = res["moon"]
            alt_expected, az_expected = _oracle_altaz(instant, "moon", lat, lon)
            assert (
                _great_circle_deg(moon["altitude"], moon["azimuth"], alt_expected, az_expected) <= 0.02
            ), f"moon block at {instant} {place}"


@pytest.mark.unit
def test_precessing_the_planets_would_miss_the_oracle():
    """Negative control: run the oracle's of-date positions through the star precession and every body misses.

    Without this the absolute check above could be satisfied by a tolerance
    that is too loose to see the mistake it exists for.
    """
    from core.celestial_sky import _precess_j2000_to_date

    for instant, (gast, subpoints) in _ORACLE_SUBPOINTS.items():
        jd = 2440587.5 + datetime.fromisoformat(instant.replace("Z", "+00:00")).timestamp() / 86400.0
        for place, lat, lon in _PLANET_PLACES:
            for body_id, (dec, sub_lon) in subpoints.items():
                ra_wrong, dec_wrong = _precess_j2000_to_date((sub_lon + gast) % 360.0, dec, jd)
                alt, az = _horizontal_from_equatorial(ra_wrong, dec_wrong, (gast + lon) % 360.0, lat)
                alt_expected, az_expected = _oracle_altaz(instant, body_id, lat, lon)
                sep = _great_circle_deg(alt, az, alt_expected, az_expected)
                assert sep > 0.02, f"{body_id} at {instant} {place}: precessing it moves it only {sep:.4f} deg"


# ---------------------------------------------------------------------------
# W2-J item 3 - each sacred star also carries its J2000 catalogue position, so
# the dome's scrub mode can precess it to another instant itself.
# ---------------------------------------------------------------------------

_SACRED_STAR_KEYS = {
    "id",
    "name",
    "sanskrit",
    "altitude",
    "azimuth",
    "magnitude",
    "visible",
    "color",
    "nakshatra",
    "quality",
    "zenith_distance",
    "ra_j2000",
    "dec_j2000",
}


@pytest.mark.unit
def test_sacred_star_entries_have_exactly_these_keys_and_carry_the_j2000_position():
    """The two new keys are additive; every other key is unchanged. The J2000 position is the table value, unprecessed."""
    for instant in ("1800-01-01T00:00:00Z", "2026-10-22T02:00:00Z", "2199-12-31T23:59:00Z"):
        dt = datetime.fromisoformat(instant.replace("Z", "+00:00"))
        stars = calculate_night_sky(latitude=37.7749, longitude=-122.4194, dt=dt)["sacred_stars"]
        assert [s["id"] for s in stars] == [t["id"] for t in SACRED_FIXED_STARS]
        for star, entry in zip(stars, SACRED_FIXED_STARS):
            assert set(star) == _SACRED_STAR_KEYS, (instant, star["id"])
            assert isinstance(star["ra_j2000"], float) and isinstance(star["dec_j2000"], float)
            assert star["ra_j2000"] == round(entry["ra"], 4), (instant, star["id"])
            assert star["dec_j2000"] == round(entry["dec"], 4), (instant, star["id"])


@pytest.mark.unit
def test_j2000_positions_are_the_published_values_and_the_pleiades_stay_cluster_level():
    """Hand-copied literals, so a wrong table cannot pass by being compared with itself."""
    dt = datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc)
    got = {s["id"]: s for s in calculate_night_sky(latitude=37.7749, longitude=-122.4194, dt=dt)["sacred_stars"]}
    assert (got["sirius"]["ra_j2000"], got["sirius"]["dec_j2000"]) == (101.287, -16.716)
    assert (got["vega"]["ra_j2000"], got["vega"]["dec_j2000"]) == (279.234, 38.784)
    assert (got["polaris"]["ra_j2000"], got["polaris"]["dec_j2000"]) == (37.954, 89.264)
    # an approximate cluster-level representative, 0.11 deg from Alcyone (HR 1165), not a BSC5 star position
    assert (got["pleiades"]["ra_j2000"], got["pleiades"]["dec_j2000"]) == (56.75, 24.11)
