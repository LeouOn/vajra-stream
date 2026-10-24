"""W4-T1: the live /night-sky Sun, Moon and planet positions are topocentric.

``calculate_night_sky`` used to hand swisseph's geocentric RA/Dec straight to the
equatorial -> horizontal step, so its altitude/azimuth were for an observer at the
Earth's centre although every docstring said "topocentric". The Moon (horizontal
parallax 54'-61') sat up to ~1 deg higher in the payload than it does at the
observer's place. The fix applies the diurnal parallax (Meeus, Astronomical
Algorithms ch. 40, oblate Earth, observer at sea level) to every body before the
horizontal step, as a pure function: swisseph's ``set_topo`` is process-global and
FastAPI runs the sync routes in a thread pool, so production code never calls it.

Two independent oracles, neither touching the code under test:

* swisseph itself: ``set_topo(lon, lat, 0)`` + ``FLG_TOPOCTR | FLG_EQUATORIAL`` (live in
  this file), then the plain spherical trigonometry written below.
* astropy: TETE (true equator/equinox of date) -> ITRS -> AltAz with the observer on the
  WGS84 ellipsoid, no refraction, UT1 := UTC like the backend. Frozen as literals below,
  produced by docs/notes/earthsky/wave4/t1/build_astropy_oracle.py (the test never
  imports astropy). Both oracles are fed swisseph's geocentric apparent place, so the
  comparison isolates the parallax and the horizontal conversion, not the ephemeris.

Tolerances. The helper is compared unrounded: the Moon to 0.001 deg and the Sun and
planets to 0.0004 deg (the two oracles agree with each other to ~0.0001 deg). The
payload is rounded to 2 decimals, which alone is worth up to 0.0071 deg of great-circle
distance, so it is compared at 0.0075 deg - the rounding bound plus oracle noise - and
the unrounded helper tests are what hold the Sun and planets to the finer figure.
"""

from __future__ import annotations

import math
from datetime import datetime

import pytest

from core import celestial_sky
from core.celestial_sky import calculate_night_sky

swe = pytest.importorskip("swisseph")
swe.set_ephe_path("")

# Same ids as core.celestial_sky.PLANET_INFO, written out so a wrong id there is not copied here.
BODY_IDS = {
    "sun": 0,
    "moon": 1,
    "mercury": 2,
    "venus": 3,
    "mars": 4,
    "jupiter": 5,
    "saturn": 6,
    "uranus": 7,
    "neptune": 8,
    "pluto": 9,
}

# (label, latitude, east longitude): the equator, a high latitude, the southern hemisphere,
# the far south and one place 6 arc-minutes from the north pole.
PLACES = (
    ("san-francisco", 37.7749, -122.4194),
    ("equator-greenwich", 0.0, 0.0),
    ("tromso", 69.65, 18.96),
    ("cape-town", -33.92, 18.42),
    ("sydney", -33.87, 151.21),
    ("mcmurdo", -77.85, 166.67),
    ("near-north-pole", 89.9, 100.0),
    ("delhi", 28.61, 77.21),
)
INSTANTS = ("2026-03-20T14:46:00Z", "2026-10-22T02:00:00Z", "2026-07-01T00:00:00Z")
# Found by a 15-minute scan of 2026 and then frozen (see build_astropy_oracle.py).
SPECIAL = (
    ("moon-low-sf", 37.7749, -122.4194, "2026-01-01T13:30:00Z"),  # Moon 3.9 deg up geocentric, 2.9 deg from the place
    ("moon-zenith-eq", 0.0, 0.0, "2026-02-05T02:45:00Z"),  # Moon within 0.6 deg of the zenith
    (
        "moon-flip-sf",
        37.7749,
        -122.4194,
        "2026-01-03T00:15:00Z",
    ),  # above the horizon geocentric, below it from the place
)
CASES = [(f"{label}|{when}", lat, lon, when) for label, lat, lon in PLACES for when in INSTANTS] + [
    (f"{label}|{when}", lat, lon, when) for label, lat, lon, when in SPECIAL
]
CASE_IDS = [case[0] for case in CASES]

HELPER_TOLERANCE = {"moon": 0.001}
HELPER_TOLERANCE_DEFAULT = 0.0004
PAYLOAD_TOLERANCE = 0.0075
ORACLES_AGREE = 0.0005

# Oracle B, frozen: astropy topocentric (altitude, azimuth) in degrees, 5 places, per case and body.
# Regenerate with docs/notes/earthsky/wave4/t1/build_astropy_oracle.py (astropy_oracle.json beside it).
# fmt: off
_ASTROPY_ALTAZ = {
    "san-francisco|2026-03-20T14:46:00Z": {
        "sun": (5.70659, 94.44352),
        "moon": (-2.15472, 74.78552),
        "mercury": (16.41945, 113.50784),
        "venus": (-3.56738, 79.46001),
        "mars": (12.05656, 109.14808),
        "jupiter": (-28.66364, 350.1868),
        "saturn": (1.86473, 91.83717),
        "uranus": (-20.8064, 41.51702),
        "neptune": (3.71317, 93.50911),
        "pluto": (22.71194, 148.87511),
    },
    "san-francisco|2026-10-22T02:00:00Z": {
        "sun": (-7.85, 262.12346),
        "moon": (29.77606, 131.82492),
        "mercury": (1.38168, 241.88522),
        "venus": (-11.83756, 255.55221),
        "mars": (-31.53008, 339.552),
        "jupiter": (-31.73902, 328.32324),
        "saturn": (14.9719, 100.01708),
        "uranus": (-11.76519, 51.37925),
        "neptune": (19.58731, 106.54358),
        "pluto": (28.09618, 171.337),
    },
    "san-francisco|2026-07-01T00:00:00Z": {
        "sun": (39.81625, 270.03593),
        "moon": (-51.21875, 84.52047),
        "mercury": (50.98848, 251.29985),
        "venus": (65.59224, 212.7078),
        "mars": (6.84073, 290.276),
        "jupiter": (55.80737, 249.47271),
        "saturn": (-36.23165, 311.36062),
        "uranus": (8.83289, 289.44714),
        "neptune": (-43.86382, 319.46952),
        "pluto": (-61.71216, 66.99341),
    },
    "equator-greenwich|2026-03-20T14:46:00Z": {
        "sun": (50.34912, 270.0),
        "moon": (64.97199, 297.90522),
        "mercury": (29.8021, 261.43495),
        "venus": (66.14962, 285.22843),
        "mars": (35.87191, 261.08411),
        "jupiter": (21.15847, 65.30706),
        "saturn": (54.97998, 269.46166),
        "uranus": (64.61213, 38.47512),
        "neptune": (52.49432, 269.19001),
        "pluto": (-1.17076, 247.18603),
    },
    "equator-greenwich|2026-10-22T02:00:00Z": {
        "sun": (-54.59614, 109.24305),
        "moon": (6.95996, 261.7549),
        "mercury": (-65.40648, 149.219),
        "venus": (-52.51182, 121.56164),
        "mars": (13.44285, 71.35373),
        "jupiter": (4.79531, 75.47997),
        "saturn": (39.67218, 271.89369),
        "uranus": (68.86673, 6.68279),
        "neptune": (32.15506, 269.54745),
        "pluto": (-21.95048, 244.39501),
    },
    "equator-greenwich|2026-07-01T00:00:00Z": {
        "sun": (-66.86398, 357.77792),
        "moon": (61.24636, 153.87107),
        "mercury": (-64.00847, 316.22853),
        "venus": (-43.5174, 292.96932),
        "mars": (-46.36045, 60.01211),
        "jupiter": (-59.26003, 313.35707),
        "saturn": (-4.90903, 86.59015),
        "uranus": (-48.037, 58.02323),
        "neptune": (4.47857, 89.50132),
        "pluto": (53.34047, 131.16564),
    },
    "tromso|2026-03-20T14:46:00Z": {
        "sun": (10.43345, 240.22637),
        "moon": (25.22077, 225.7747),
        "mercury": (-3.13576, 257.01853),
        "venus": (20.87169, 225.47362),
        "mars": (-0.88777, 251.37023),
        "jupiter": (35.43079, 122.90951),
        "saturn": (11.50461, 235.62609),
        "uranus": (39.93872, 183.08406),
        "neptune": (10.60562, 237.99304),
        "pluto": (-28.31451, 280.73926),
    },
    "tromso|2026-10-22T02:00:00Z": {
        "sun": (-22.66394, 57.94835),
        "moon": (-12.38057, 277.47544),
        "mercury": (-37.6087, 38.84241),
        "venus": (-30.07723, 59.84313),
        "mars": (28.17221, 115.446),
        "jupiter": (21.76085, 107.61906),
        "saturn": (8.44631, 250.94803),
        "uranus": (40.33421, 200.21302),
        "neptune": (4.1928, 257.47097),
        "pluto": (-36.38891, 303.71797),
    },
    "tromso|2026-07-01T00:00:00Z": {
        "sun": (3.66553, 16.55581),
        "moon": (-5.84166, 185.09362),
        "mercury": (-1.90388, 0.30414),
        "venus": (-2.09781, 335.91945),
        "mars": (8.79598, 54.09315),
        "jupiter": (0.24899, 355.85792),
        "saturn": (8.0356, 102.0367),
        "uranus": (8.71572, 51.91553),
        "neptune": (8.42153, 111.95905),
        "pluto": (-3.08753, 170.52118),
    },
    "cape-town|2026-03-20T14:46:00Z": {
        "sun": (26.03051, 289.17564),
        "moon": (29.84257, 312.25227),
        "mercury": (13.79233, 270.2729),
        "venus": (33.95147, 307.37882),
        "mars": (18.75431, 273.92872),
        "jupiter": (16.79433, 46.10212),
        "saturn": (29.82193, 292.2091),
        "uranus": (36.4347, 357.69348),
        "neptune": (28.01729, 290.24749),
        "pluto": (-2.37286, 240.30201),
    },
    "cape-town|2026-10-22T02:00:00Z": {
        "sun": (-23.06475, 122.43926),
        "moon": (-4.92943, 257.3727),
        "mercury": (-27.42142, 146.54199),
        "venus": (-18.12131, 128.60227),
        "mars": (14.54434, 55.83101),
        "jupiter": (10.33112, 64.61911),
        "saturn": (16.66057, 283.48832),
        "uranus": (33.06062, 342.29181),
        "neptune": (11.5816, 277.44592),
        "pluto": (-16.85392, 224.89163),
    },
    "cape-town|2026-07-01T00:00:00Z": {
        "sun": (-71.27698, 120.66761),
        "moon": (80.08526, 331.85318),
        "mercury": (-74.5296, 180.78062),
        "venus": (-61.05709, 239.2492),
        "mars": (-37.26692, 89.38927),
        "jupiter": (-75.92027, 199.45452),
        "saturn": (9.22657, 79.53761),
        "uranus": (-39.36812, 89.98747),
        "neptune": (18.54385, 76.3134),
        "pluto": (75.63565, 44.2021),
    },
    "sydney|2026-03-20T14:46:00Z": {
        "sun": (-54.63184, 161.00565),
        "moon": (-66.92638, 196.83992),
        "mercury": (-39.25812, 138.54809),
        "venus": (-61.73161, 192.01076),
        "mars": (-42.57354, 145.28692),
        "jupiter": (-8.10416, 292.2332),
        "saturn": (-55.32445, 169.00603),
        "uranus": (-47.54393, 262.25563),
        "neptune": (-54.676, 164.81213),
        "pluto": (-7.90917, 124.37578),
    },
    "sydney|2026-10-22T02:00:00Z": {
        "sun": (66.67013, 347.33404),
        "moon": (-25.22564, 119.47377),
        "mercury": (71.10134, 50.87189),
        "venus": (74.2133, 344.56115),
        "mars": (1.48907, 293.08595),
        "jupiter": (10.69994, 295.66188),
        "saturn": (-51.84461, 143.5848),
        "uranus": (-59.48788, 253.17144),
        "neptune": (-46.22625, 135.41548),
        "pluto": (9.26087, 112.31427),
    },
    "sydney|2026-07-01T00:00:00Z": {
        "sun": (26.37196, 30.61207),
        "moon": (-19.49618, 219.84015),
        "mercury": (20.87878, 48.39235),
        "venus": (4.37538, 66.84537),
        "mars": (34.98601, 347.64318),
        "jupiter": (16.33394, 50.42162),
        "saturn": (25.27354, 293.31781),
        "uranus": (34.78781, 350.25769),
        "neptune": (19.69299, 284.55663),
        "pluto": (-10.65993, 232.55635),
    },
    "mcmurdo|2026-03-20T14:46:00Z": {
        "sun": (-10.87661, 153.16121),
        "moon": (-24.14068, 170.70157),
        "mercury": (-0.98323, 133.90985),
        "venus": (-18.06508, 169.77524),
        "mars": (-2.06895, 139.8885),
        "jupiter": (-24.43622, 265.56586),
        "saturn": (-10.97038, 157.88675),
        "uranus": (-30.01425, 212.70495),
        "neptune": (-10.57931, 155.38253),
        "pluto": (19.78172, 106.6664),
    },
    "mcmurdo|2026-10-22T02:00:00Z": {
        "sun": (22.33989, 338.14418),
        "moon": (2.68686, 112.47324),
        "mercury": (33.09838, 0.16343),
        "venus": (29.93371, 338.20515),
        "mars": (-17.87377, 273.13138),
        "jupiter": (-12.38985, 281.24641),
        "saturn": (-11.12471, 142.20128),
        "uranus": (-32.61967, 197.68572),
        "neptune": (-8.25296, 134.89467),
        "pluto": (25.32944, 84.75061),
    },
    "mcmurdo|2026-07-01T00:00:00Z": {
        "sun": (-11.32014, 13.37598),
        "moon": (13.37459, 204.78029),
        "mercury": (-8.05249, 30.48096),
        "venus": (-9.67616, 55.0963),
        "mars": (-9.20769, 335.15295),
        "jupiter": (-10.66571, 34.72526),
        "saturn": (0.4498, 288.54515),
        "uranus": (-9.57641, 337.30359),
        "neptune": (1.36948, 278.75942),
        "pluto": (13.98819, 219.89129),
    },
    "near-north-pole|2026-03-20T14:46:00Z": {
        "sun": (-0.07866, 319.64935),
        "moon": (10.21304, 302.05325),
        "mercury": (-7.5226, 339.91243),
        "venus": (6.04059, 303.11048),
        "mars": (-7.30541, 333.7903),
        "jupiter": (23.01242, 213.09738),
        "saturn": (-0.3799, 315.01835),
        "uranus": (19.62339, 263.58531),
        "neptune": (-0.56695, 317.50232),
        "pluto": (-22.90703, 11.27826),
    },
    "near-north-pole|2026-10-22T02:00:00Z": {
        "sun": (-10.94087, 133.87901),
        "moon": (-9.19051, 2.0268),
        "mercury": (-20.91425, 113.21858),
        "venus": (-18.51761, 133.19586),
        "mars": (18.207, 204.17344),
        "jupiter": (14.5643, 194.95989),
        "saturn": (1.37032, 330.3135),
        "uranus": (20.96975, 277.46257),
        "neptune": (-0.47583, 337.84383),
        "pluto": (-23.71328, 34.10481),
    },
    "near-north-pole|2026-07-01T00:00:00Z": {
        "sun": (23.13205, 99.00856),
        "moon": (-26.01184, 266.60318),
        "mercury": (18.43098, 81.32744),
        "venus": (16.38068, 55.85694),
        "mars": (20.25306, 139.53169),
        "jupiter": (20.52025, 76.57964),
        "saturn": (3.49668, 185.08309),
        "uranus": (20.81181, 137.31024),
        "neptune": (0.5939, 194.47907),
        "pluto": (-23.10876, 250.69789),
    },
    "delhi|2026-03-20T14:46:00Z": {
        "sun": (-23.3704, 283.63141),
        "moon": (-3.5696, 284.29148),
        "mercury": (-44.41888, 289.16881),
        "venus": (-6.0517, 280.33877),
        "mars": (-39.16902, 285.06022),
        "jupiter": (79.14252, 240.7975),
        "saturn": (-19.55402, 280.79006),
        "uranus": (34.37973, 275.16781),
        "neptune": (-21.78562, 281.97264),
        "pluto": (-78.11886, 296.59931),
    },
    "delhi|2026-10-22T02:00:00Z": {
        "sun": (12.61526, 110.18051),
        "moon": (-62.1488, 312.23145),
        "mercury": (-9.53441, 108.74857),
        "venus": (7.88037, 116.22822),
        "mars": (79.43223, 187.11718),
        "jupiter": (74.10261, 151.18326),
        "saturn": (-31.49028, 291.59814),
        "uranus": (22.87132, 282.27555),
        "neptune": (-38.64874, 295.24113),
        "pluto": (-78.71354, 66.41365),
    },
    "delhi|2026-07-01T00:00:00Z": {
        "sun": (-0.21721, 63.30177),
        "moon": (7.49895, 235.1905),
        "mercury": (-16.4258, 57.5488),
        "venus": (-34.74712, 39.58999),
        "mars": (32.42851, 83.16762),
        "jupiter": (-18.49274, 52.84913),
        "saturn": (59.67909, 143.02803),
        "uranus": (30.70562, 81.65195),
        "neptune": (60.78579, 162.77331),
        "pluto": (20.64118, 226.85527),
    },
    "moon-low-sf|2026-01-01T13:30:00Z": {
        "sun": (-22.06666, 102.62843),
        "moon": (2.85116, 302.39595),
        "mercury": (-13.10671, 110.44772),
        "venus": (-21.41544, 103.88419),
        "mars": (-24.17461, 102.07164),
        "jupiter": (30.06332, 275.67169),
        "saturn": (-55.62219, 6.88125),
        "uranus": (-13.23356, 308.0406),
        "neptune": (-53.62341, 2.04567),
        "pluto": (-40.88612, 89.3526),
    },
    "moon-zenith-eq|2026-02-05T02:45:00Z": {
        "sun": (-49.46982, 115.01673),
        "moon": (89.49257, 272.09953),
        "mercury": (-59.81436, 118.86433),
        "venus": (-56.41647, 118.04273),
        "mars": (-43.0826, 116.13941),
        "jupiter": (20.09546, 294.2381),
        "saturn": (-85.8029, 235.72547),
        "uranus": (-29.33471, 292.40829),
        "neptune": (-85.62432, 255.38677),
        "pluto": (-36.79448, 119.20179),
    },
    "moon-flip-sf|2026-01-03T00:15:00Z": {
        "sun": (7.09443, 233.74755),
        "moon": (-0.84173, 54.00334),
        "mercury": (-1.68569, 240.24399),
        "venus": (6.05008, 233.88564),
        "mars": (7.72217, 231.99307),
        "jupiter": (-13.30407, 47.87327),
        "saturn": (46.82069, 160.07062),
        "uranus": (25.99704, 84.72846),
        "neptune": (48.07748, 155.44253),
        "pluto": (19.34677, 216.82416),
    },
}
# fmt: on


# -- the independent instruments --------------------------------------------------------------


def _moment(when: str) -> datetime:
    return datetime.fromisoformat(when.replace("Z", "+00:00"))


def _julian_day(moment: datetime) -> float:
    return swe.julday(
        moment.year, moment.month, moment.day, moment.hour + moment.minute / 60.0 + moment.second / 3600.0
    )


def _local_sidereal_deg(jd: float, lon: float) -> float:
    return (swe.sidtime(jd) * 15.0 + lon) % 360.0


def _horizontal(ra_deg: float, dec_deg: float, lst_deg: float, lat_deg: float) -> tuple[float, float]:
    """Plain spherical trigonometry, unrounded: altitude and azimuth (north 0, east 90)."""
    h = math.radians((lst_deg - ra_deg) % 360.0)
    dec = math.radians(dec_deg)
    lat = math.radians(lat_deg)
    sin_alt = math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(h)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    y = -math.cos(dec) * math.sin(h)
    x = math.sin(dec) * math.cos(lat) - math.cos(dec) * math.sin(lat) * math.cos(h)
    return alt, math.degrees(math.atan2(y, x)) % 360.0


def _separation(alt1: float, az1: float, alt2: float, az2: float) -> float:
    """Great-circle distance in degrees (haversine: still accurate at 1e-4 deg, where acos is not)."""
    a1, a2 = math.radians(alt1), math.radians(alt2)
    h = math.sin((a2 - a1) / 2.0) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(math.radians(az2 - az1) / 2.0) ** 2
    return math.degrees(2.0 * math.asin(min(1.0, math.sqrt(h))))


def _geocentric(body: str, jd: float) -> tuple[float, float, float]:
    """swisseph's geocentric apparent place: right ascension and declination in degrees, distance in AU."""
    xx = swe.calc_ut(jd, BODY_IDS[body], swe.FLG_EQUATORIAL)[0]
    return xx[0], xx[1], xx[2]


def _geocentric_altaz(body: str, jd: float, lat: float, lon: float) -> tuple[float, float]:
    """What the payload used to carry: the geocentric place seen from an observer at the Earth's centre."""
    ra, dec, _ = _geocentric(body, jd)
    return _horizontal(ra, dec, _local_sidereal_deg(jd, lon), lat)


def _swiss_topocentric_altaz(body: str, jd: float, lat: float, lon: float) -> tuple[float, float]:
    """Oracle A: swisseph's own topocentric place (set_topo + FLG_TOPOCTR), then the trigonometry above."""
    swe.set_topo(lon, lat, 0.0)
    try:
        xx = swe.calc_ut(jd, BODY_IDS[body], swe.FLG_EQUATORIAL | swe.FLG_TOPOCTR)[0]
    finally:
        swe.set_topo(0.0, 0.0, 0.0)
    return _horizontal(xx[0], xx[1], _local_sidereal_deg(jd, lon), lat)


def _case(case_id: str) -> tuple[str, float, float, str, float]:
    _, lat, lon, when = next(case for case in CASES if case[0] == case_id)
    return case_id, lat, lon, when, _julian_day(_moment(when))


def _helper():
    return celestial_sky._topocentric_horizontal  # missing before W4-T1: the tests that need it fail, not the import


def _tolerance(body: str) -> float:
    return HELPER_TOLERANCE.get(body, HELPER_TOLERANCE_DEFAULT)


# -- the helper against both oracles ------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("case_id", CASE_IDS)
def test_helper_matches_the_swisseph_topocentric_oracle(case_id: str):
    _, lat, lon, _, jd = _case(case_id)
    lst = _local_sidereal_deg(jd, lon)
    misses = {}
    for body in BODY_IDS:
        ra, dec, dist = _geocentric(body, jd)
        got = _helper()(ra, dec, dist, lst, lat)
        want = _swiss_topocentric_altaz(body, jd, lat, lon)
        misses[body] = _separation(*got, *want)
    bad = {body: round(miss, 5) for body, miss in misses.items() if miss > _tolerance(body)}
    assert not bad, f"{case_id}: helper vs swisseph TOPOCTR beyond tolerance (deg): {bad}"


@pytest.mark.unit
@pytest.mark.parametrize("case_id", CASE_IDS)
def test_helper_matches_the_astropy_oracle(case_id: str):
    _, lat, lon, _, jd = _case(case_id)
    lst = _local_sidereal_deg(jd, lon)
    misses = {}
    for body in BODY_IDS:
        ra, dec, dist = _geocentric(body, jd)
        misses[body] = _separation(*_helper()(ra, dec, dist, lst, lat), *_ASTROPY_ALTAZ[case_id][body])
    bad = {body: round(miss, 5) for body, miss in misses.items() if miss > _tolerance(body)}
    assert not bad, f"{case_id}: helper vs astropy beyond tolerance (deg): {bad}"


@pytest.mark.unit
@pytest.mark.parametrize("case_id", CASE_IDS)
def test_the_two_oracles_agree_with_each_other(case_id: str):
    """The instrument check: if these two disagree, a miss above means nothing."""
    _, lat, lon, _, jd = _case(case_id)
    for body in BODY_IDS:
        swiss = _swiss_topocentric_altaz(body, jd, lat, lon)
        assert _separation(*swiss, *_ASTROPY_ALTAZ[case_id][body]) <= ORACLES_AGREE, f"{case_id} {body}"


# -- the payload ----------------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("case_id", CASE_IDS)
def test_payload_altaz_is_topocentric_within_the_two_decimal_rounding(case_id: str):
    _, lat, lon, when, jd = _case(case_id)
    result = calculate_night_sky(latitude=lat, longitude=lon, dt=_moment(when))
    planets = {p["id"]: p for p in result["planets"]}
    assert set(planets) == set(BODY_IDS)
    for body, planet in planets.items():
        got = (planet["altitude"], planet["azimuth"])
        swiss = _separation(*got, *_swiss_topocentric_altaz(body, jd, lat, lon))
        astropy = _separation(*got, *_ASTROPY_ALTAZ[case_id][body])
        assert swiss <= PAYLOAD_TOLERANCE, f"{case_id} {body}: {swiss:.5f} deg from swisseph TOPOCTR"
        assert astropy <= PAYLOAD_TOLERANCE, f"{case_id} {body}: {astropy:.5f} deg from astropy"
    moon = result["moon"]
    assert (moon["altitude"], moon["azimuth"], moon["visible"]) == (
        planets["moon"]["altitude"],
        planets["moon"]["azimuth"],
        planets["moon"]["visible"],
    )


@pytest.mark.unit
@pytest.mark.parametrize("case_id", CASE_IDS)
def test_the_payload_is_the_rounded_helper_result_for_every_body(case_id: str):
    """The wiring: every body, the Sun and planets included, goes through the helper with swisseph's own
    geocentric place and distance. The 0.0075 deg oracle comparison above cannot see a skipped correction on
    the Sun or a planet (their parallax is below the rounding), so this pins it exactly; the helper itself is
    held to 0.0004 deg by the oracles."""
    _, lat, lon, when, jd = _case(case_id)
    lst = _local_sidereal_deg(jd, lon)
    planets = {p["id"]: p for p in calculate_night_sky(latitude=lat, longitude=lon, dt=_moment(when))["planets"]}
    for body in BODY_IDS:
        ra, dec, dist = _geocentric(body, jd)
        alt, az = _helper()(ra, dec, dist, lst, lat)
        assert (planets[body]["altitude"], planets[body]["azimuth"]) == (
            round(alt, 2),
            round(az, 2),
        ), f"{case_id} {body}"


@pytest.mark.unit
def test_the_payload_names_its_frame_and_keeps_right_ascension_and_declination_geocentric():
    """``position_frame`` is additive; RA/Dec stay the catalogue-style geocentric apparent place."""
    _, lat, lon, when, jd = _case("tromso|2026-03-20T14:46:00Z")
    result = calculate_night_sky(latitude=lat, longitude=lon, dt=_moment(when))
    assert result["position_frame"] == "topocentric"
    for planet in result["planets"]:
        ra, dec, _ = _geocentric(planet["id"], jd)
        assert planet["right_ascension"] == round(ra, 2), planet["id"]
        assert planet["declination"] == round(dec, 2), planet["id"]


@pytest.mark.unit
def test_visible_follows_the_topocentric_altitude():
    """moon-flip-sf: 0.17 deg above the horizon geocentrically, 0.84 deg below it from the place."""
    case_id, lat, lon, when, jd = _case("moon-flip-sf|2026-01-03T00:15:00Z")
    geocentric_alt, _ = _geocentric_altaz("moon", jd, lat, lon)
    assert geocentric_alt > 0.1  # the old payload would have called the Moon visible
    result = calculate_night_sky(latitude=lat, longitude=lon, dt=_moment(when))
    moon = next(p for p in result["planets"] if p["id"] == "moon")
    assert moon["altitude"] < -0.5
    assert moon["visible"] is False
    assert result["moon"]["visible"] is False
    assert result["visible_planets_count"] == sum(1 for p in result["planets"] if p["visible"])


@pytest.mark.unit
def test_production_code_never_calls_swisseph_set_topo(monkeypatch):
    """set_topo is process-global and the routes run in a thread pool: the maths must stay pure."""

    def boom(*_args, **_kwargs):
        raise AssertionError("calculate_night_sky must not call swe.set_topo")

    monkeypatch.setattr(celestial_sky.swe, "set_topo", boom)
    _, lat, lon, when, _ = _case("sydney|2026-10-22T02:00:00Z")
    assert calculate_night_sky(latitude=lat, longitude=lon, dt=_moment(when))["position_frame"] == "topocentric"


@pytest.mark.unit
def test_the_approximate_fallback_does_not_claim_a_frame_it_did_not_apply(monkeypatch):
    """Without swisseph there is no distance to take a parallax from: say so instead of saying topocentric."""
    monkeypatch.setattr(celestial_sky, "HAS_SWISSEPH", False)
    result = calculate_night_sky(latitude=37.7749, longitude=-122.4194, dt=_moment("2026-03-20T14:46:00Z"))
    assert result["position_frame"] == "geocentric"
    assert len(result["planets"]) == len(BODY_IDS)


# -- negative controls: the checks above can fail --------------------------------------------------


@pytest.mark.unit
def test_the_old_geocentric_value_misses_a_low_moon_by_more_than_half_a_degree():
    """Without this, tolerances that are too loose would pass the old payload too."""
    lows = []
    for case_id in CASE_IDS:
        _, lat, lon, when, jd = _case(case_id)
        oracle = _swiss_topocentric_altaz("moon", jd, lat, lon)
        if 0.0 < oracle[0] < 10.0:
            lows.append((case_id, lat, lon, when, jd, oracle))
    assert any(case[0].startswith("moon-low-sf") for case in lows), "the frozen low-Moon case is no longer low"
    for case_id, lat, lon, when, jd, oracle in lows:
        old = _geocentric_altaz("moon", jd, lat, lon)
        assert _separation(*old, *oracle) > 0.5, f"{case_id}: the geocentric Moon is within 0.5 deg of the oracle"
        moon = calculate_night_sky(latitude=lat, longitude=lon, dt=_moment(when))["moon"]
        assert _separation(moon["altitude"], moon["azimuth"], *old) > 0.5, f"{case_id}: payload still geocentric"


@pytest.mark.unit
@pytest.mark.parametrize("body", ["sun", "moon", "mercury", "venus", "mars"])
def test_leaving_out_the_parallax_would_fail_the_tolerance_for_each_near_body(body: str):
    """For these bodies the parallax somewhere in the grid exceeds twice the tolerance, so a skipped
    correction cannot hide (Jupiter and beyond move less than 0.0005 deg: below what the oracles separate)."""
    worst = 0.0
    for case_id in CASE_IDS:
        _, lat, lon, _, jd = _case(case_id)
        worst = max(
            worst, _separation(*_geocentric_altaz(body, jd, lat, lon), *_swiss_topocentric_altaz(body, jd, lat, lon))
        )
    assert worst > 2 * _tolerance(body), f"{body}: geocentric is only {worst:.5f} deg from the oracle at worst"


# -- the pure parallax helper on its own ------------------------------------------------------------

_AU_PER_EARTH_RADIUS = math.sin(math.radians(8.794 / 3600.0))  # Meeus: the equatorial horizontal parallax at 1 AU


@pytest.mark.unit
def test_a_body_at_the_zenith_of_an_equatorial_observer_has_no_parallax():
    """On the equator the geodetic and geocentric verticals coincide, so the zenith is the one direction parallax spares."""
    lst = 123.0
    ra, dec = celestial_sky._topocentric_equatorial(lst, 0.0, 0.00257, lst, 0.0)
    assert ra == pytest.approx(lst, abs=1e-9)
    assert dec == pytest.approx(0.0, abs=1e-9)


@pytest.mark.unit
@pytest.mark.parametrize("distance_au", [0.00257, 0.0026, 0.4, 1.0, 30.0])
def test_a_body_on_the_geocentric_horizon_drops_by_the_angle_the_earth_radius_subtends(distance_au: float):
    """Equator, hour angle 90 deg, declination 0: the topocentric vector is (-R, d) in Earth-centred axes,
    so the altitude is -atan(R / d). Written as vectors here, not with the code's formula."""
    lst = 200.0
    got_alt, _ = celestial_sky._topocentric_horizontal(lst - 90.0, 0.0, distance_au, lst, 0.0)
    want_alt = -math.degrees(math.atan2(_AU_PER_EARTH_RADIUS, distance_au))
    assert got_alt == pytest.approx(want_alt, abs=1e-8)


@pytest.mark.unit
def test_a_body_at_a_huge_distance_comes_back_unchanged():
    ra, dec = celestial_sky._topocentric_equatorial(10.0, 20.0, 1e12, 77.0, 45.0)
    assert ra == pytest.approx(10.0, abs=1e-9)
    assert dec == pytest.approx(20.0, abs=1e-9)


@pytest.mark.unit
def test_the_observer_is_on_the_oblate_earth_not_a_sphere():
    """45 deg geodetic latitude is 44.8076 deg geocentric: tan(phi') = (1 - f)^2 tan(phi) with f = 1/298.257."""
    rho_sin, rho_cos = celestial_sky._observer_terms(45.0)
    assert math.degrees(math.atan2(rho_sin, rho_cos)) == pytest.approx(
        math.degrees(math.atan((1 - 1 / 298.257) ** 2)), abs=2e-4
    )
    assert 0.9966 < math.hypot(rho_sin, rho_cos) < 1.0
    assert celestial_sky._observer_terms(0.0) == pytest.approx((0.0, 1.0), abs=1e-12)
    assert celestial_sky._observer_terms(90.0)[0] == pytest.approx(0.99664719, abs=1e-8)


@pytest.mark.unit
@pytest.mark.parametrize("distance_au", [0.0, -1.0, float("nan"), float("inf")])
def test_a_distance_that_is_not_positive_and_finite_is_refused(distance_au: float):
    with pytest.raises(ValueError):
        celestial_sky._topocentric_equatorial(10.0, 20.0, distance_au, 77.0, 45.0)
