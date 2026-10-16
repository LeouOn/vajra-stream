"""The true sky at a moment and place: computed positions, a camera, pixel coordinates.

The honest-instrument rule (docs/DEVELOPMENT_ROADMAP.md) forbids letting an
image model paint the Moon: told "a waxing crescent moon" it paints whatever
crescent it likes. So a folio witness is rendered with an empty sky and the
real sky is drawn onto it afterwards (``core/sky_composite.py``). This module
is the math for that, pure functions with no I/O:

* :func:`compute_sky` asks the Swiss Ephemeris for the Sun, Moon and the
  bright planets at a UTC instant and turns them into apparent altitude /
  azimuth for an observer, plus the Moon's illuminated fraction and the
  orientation of its bright limb *as that observer sees it* (Meeus,
  *Astronomical Algorithms*, ch. 14 and 48: the bright limb's position angle
  minus the parallactic angle). It returns ``None`` when the ephemeris is not
  installed or fails; nothing here ever invents a sky.
* :func:`plan_sky` points a simple, documented camera and maps every body to
  pixels (:func:`project`), deciding what is drawn and why the rest is not.
* :func:`sky_caption_facts` / :func:`overlay_caption_fact` turn that into the
  ``caption_facts`` shown beside the image.

The camera
    Faces the Moon's azimuth when the Moon is up; otherwise the brightest
    drawable planet's; otherwise the equator (due south for a northern
    observer, due north for a southern one). Its horizontal field of view is
    :data:`HFOV_DEG`, the horizon sits at :data:`HORIZON_FRACTION` of the image
    height, and the projection is linear in both axes (equirectangular: one
    pixel is ``HFOV_DEG / width`` degrees of azimuth and of altitude). The
    camera does not tilt, so a body higher than the top edge is out of frame.

Conventions: azimuth is degrees from north through east (0-360). Altitudes
are apparent (atmospheric refraction included; the Moon's also corrected for
its parallax). The bright-limb angle is measured from the local vertical
("up" in the picture) counter-clockwise, which is the direction the sky
turns from north to east for someone looking at it.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from config.settings import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from core.image_prompts import caption_fact, moon_phase_words
from core.provenance import Provenance

logger = logging.getLogger(__name__)

#: Horizontal field of view of the witness camera, degrees.
HFOV_DEG = 60.0
#: Where the horizon sits, as a fraction of the image height from the top.
HORIZON_FRACTION = 0.85
#: The Moon is drawn this many times its true apparent size so it reads at all
#: (at true size it would be about eight pixels across in a 1024 px frame).
MOON_SCALE = 5.0
#: Planets are drawn only once the Sun is this far below the horizon (civil twilight over).
PLANETS_VISIBLE_SUN_ALT = -6.0
#: Sun altitude above which the sky is "daytime" (upper limb on the horizon, refraction included).
DAY_SUN_ALT = -0.833
#: Sun altitude above which the sky is still "twilight" rather than "night" (nautical twilight).
TWILIGHT_SUN_ALT = -12.0
#: Mean equatorial radius of the Earth, km (for the Moon's horizontal parallax).
EARTH_RADIUS_KM = 6378.14
AU_KM = 149_597_870.7

#: The bright planets a witness sky may show, in the order they are listed.
PLANETS: tuple[str, ...] = ("Venus", "Jupiter", "Mars", "Saturn", "Mercury")

#: Body status values in a plan.
DRAWN = "drawn"
OUT_OF_FRAME = "out_of_frame"
BELOW_HORIZON = "below_horizon"
DAYLIGHT = "daylight"

_STATUS_WORDS = {
    DRAWN: "drawn",
    OUT_OF_FRAME: "out of frame",
    BELOW_HORIZON: "below horizon",
    DAYLIGHT: "not drawn (daylight)",
}

_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


# -- small angle helpers -------------------------------------------------------------


def wrap180(deg: float) -> float:
    """``deg`` folded into (-180, 180]."""
    out = (deg + 180.0) % 360.0 - 180.0
    return 180.0 if out == -180.0 else out


def compass(az: float) -> str:
    """16-point compass word for an azimuth (degrees from north through east)."""
    return _COMPASS[int(((az % 360.0) + 11.25) // 22.5) % 16]


def limb_direction_words(angle_from_vertical: float) -> str:
    """Where a bright limb at this angle (CCW from up) points in the picture: "lower right", ..."""
    words = ("up", "upper left", "left", "lower left", "down", "lower right", "right", "upper right")
    return words[int(((angle_from_vertical % 360.0) + 22.5) // 45.0) % 8]


def limb_unit_vector(angle_from_vertical: float) -> tuple[float, float]:
    """Image-space unit vector (x right, y down) of a direction ``angle`` degrees CCW from up."""
    rad = math.radians(angle_from_vertical)
    return (-math.sin(rad), -math.cos(rad))


# -- spherical astronomy (pure) ------------------------------------------------------


def equatorial_to_horizontal(ra: float, dec: float, lst: float, lat: float) -> tuple[float, float]:
    """``(altitude, azimuth)`` in degrees of a body at right ascension/declination ``ra``/``dec``.

    ``lst`` is the local sidereal time in degrees; azimuth is from north through east.
    """
    h = math.radians(lst - ra)
    phi, d = math.radians(lat), math.radians(dec)
    sin_alt = math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.cos(h)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    az = math.degrees(
        math.atan2(-math.sin(h) * math.cos(d), math.cos(phi) * math.sin(d) - math.sin(phi) * math.cos(d) * math.cos(h))
    )
    return alt, az % 360.0


def parallactic_angle(hour_angle: float, dec: float, lat: float) -> float:
    """The parallactic angle ``q`` (degrees, Meeus 14.1): the tilt of the zenith direction from north."""
    h, d, phi = math.radians(hour_angle), math.radians(dec), math.radians(lat)
    return math.degrees(math.atan2(math.sin(h), math.tan(phi) * math.cos(d) - math.sin(d) * math.cos(h)))


def bright_limb_position_angle(sun_ra: float, sun_dec: float, moon_ra: float, moon_dec: float) -> float:
    """Position angle of the Moon's bright limb midpoint, degrees from north through east (Meeus 48.5)."""
    a0, d0 = math.radians(sun_ra), math.radians(sun_dec)
    a, d = math.radians(moon_ra), math.radians(moon_dec)
    chi = math.atan2(
        math.cos(d0) * math.sin(a0 - a),
        math.sin(d0) * math.cos(d) - math.cos(d0) * math.sin(d) * math.cos(a0 - a),
    )
    return math.degrees(chi) % 360.0


def refraction(true_alt: float) -> float:
    """Atmospheric refraction in degrees to add to a true altitude (Saemundsson; 10 °C, 1010 hPa)."""
    if true_alt < -1.0:
        return 0.0
    return (1.02 / math.tan(math.radians(true_alt + 10.3 / (true_alt + 5.11)))) / 60.0


def moon_topocentric_alt(geocentric_alt: float, distance_km: float) -> float:
    """The Moon's altitude seen from the surface: lowered by its horizontal parallax (up to ~1°)."""
    parallax = math.asin(min(1.0, EARTH_RADIUS_KM / distance_km))
    return geocentric_alt - math.degrees(parallax * math.cos(math.radians(geocentric_alt)))


def sky_period(sun_alt: float | None) -> str | None:
    """``"day"``, ``"twilight"`` or ``"night"`` from the Sun's apparent altitude (``None`` if unknown)."""
    if sun_alt is None:
        return None
    if sun_alt > DAY_SUN_ALT:
        return "day"
    if sun_alt > TWILIGHT_SUN_ALT:
        return "twilight"
    return "night"


# -- the ephemeris -------------------------------------------------------------------


def _as_utc(when: datetime | str | None) -> datetime | None:
    """A UTC datetime; naive values are taken as UTC (that is how folios stamp ``sealed_at``)."""
    if when is None:
        return None
    if isinstance(when, str):
        try:
            when = datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc)


def _round(value: float, places: int = 2) -> float:
    return round(float(value), places)


def compute_sky(when: datetime | str | None, lat: float, lon: float) -> dict[str, Any] | None:
    """The Sun, Moon and bright planets for an observer at ``lat``/``lon`` (degrees, east positive).

    Returns ``None`` if ``when`` is unusable or the Swiss Ephemeris is missing
    or fails: a sky that cannot be computed is not drawn, never guessed.
    """
    at = _as_utc(when)
    if at is None:
        return None
    try:
        import swisseph as swe
    except ImportError:
        return None
    try:
        hours = at.hour + at.minute / 60.0 + (at.second + at.microsecond / 1e6) / 3600.0
        jd = swe.julday(at.year, at.month, at.day, hours)
        lst = (swe.sidtime(jd) * 15.0 + lon) % 360.0
        moshier = False

        def equatorial(body: int) -> tuple[float, float, float]:
            nonlocal moshier
            xx, flag = swe.calc_ut(jd, body, swe.FLG_EQUATORIAL)
            moshier = moshier or bool(flag & swe.FLG_MOSEPH)
            return xx[0], xx[1], xx[2]

        def ecliptic_lon(body: int) -> float:
            return float(swe.calc_ut(jd, body)[0][0])

        sun_ra, sun_dec, _ = equatorial(swe.SUN)
        sun_alt, sun_az = equatorial_to_horizontal(sun_ra, sun_dec, lst, lat)
        sun_alt += refraction(sun_alt)

        moon_ra, moon_dec, moon_dist_au = equatorial(swe.MOON)
        moon_alt, moon_az = equatorial_to_horizontal(moon_ra, moon_dec, lst, lat)
        moon_alt = moon_topocentric_alt(moon_alt, moon_dist_au * AU_KM)
        moon_alt += refraction(moon_alt)
        pheno = swe.pheno_ut(jd, swe.MOON)
        phase_angle, fraction, diameter = float(pheno[0]), float(pheno[1]), float(pheno[3])
        elongation = (ecliptic_lon(swe.MOON) - ecliptic_lon(swe.SUN)) % 360.0
        chi = bright_limb_position_angle(sun_ra, sun_dec, moon_ra, moon_dec)
        q = parallactic_angle(lst - moon_ra, moon_dec, lat)

        planets: list[dict[str, Any]] = []
        for name in PLANETS:
            body = getattr(swe, name.upper())
            ra, dec, _ = equatorial(body)
            alt, az = equatorial_to_horizontal(ra, dec, lst, lat)
            alt += refraction(alt)
            magnitude = float(swe.pheno_ut(jd, body)[4])
            planets.append({"name": name, "alt": _round(alt), "az": _round(az), "magnitude": _round(magnitude, 1)})
    except Exception as exc:  # an ephemeris failure must not break a witness
        logger.warning("compute_sky(%s, %s, %s) failed: %s", at, lat, lon, exc)
        return None

    return {
        "at": at.isoformat(),
        "ephemeris": "Swiss Ephemeris (Moshier)" if moshier else "Swiss Ephemeris",
        "observer": {"lat": float(lat), "lon": float(lon)},
        "local_sidereal_deg": _round(lst, 3),
        "sun": {"alt": _round(sun_alt), "az": _round(sun_az)},
        "period": sky_period(sun_alt),
        "moon": {
            "alt": _round(moon_alt),
            "az": _round(moon_az),
            "illumination": _round(fraction * 100.0, 1),
            "phase_angle": _round(phase_angle),
            "elongation": _round(elongation),
            "waxing": elongation < 180.0,
            "apparent_diameter_deg": round(diameter, 4),
            "bright_limb_position_angle": _round(chi),
            "parallactic_angle": _round(q),
            "bright_limb_from_vertical": _round((chi - q) % 360.0),
        },
        "planets": planets,
    }


# -- the camera and the projection -----------------------------------------------------


@dataclass(frozen=True)
class Camera:
    """A level camera: azimuth it faces, horizontal field of view, horizon height."""

    azimuth: float
    basis: str
    hfov: float = HFOV_DEG
    horizon_fraction: float = HORIZON_FRACTION

    def as_dict(self, width: int, height: int) -> dict[str, Any]:
        out = asdict(self)
        out.update(
            projection="linear (equirectangular), level, no tilt",
            azimuth=_round(self.azimuth),
            vfov=_round(self.hfov * height / width),
            degrees_per_pixel=round(self.hfov / width, 5),
            top_edge_alt=_round(self.horizon_fraction * height * self.hfov / width),
            width=width,
            height=height,
        )
        return out


def project(alt: float, az: float, camera: Camera, width: int, height: int) -> tuple[float, float]:
    """Pixel ``(x, y)`` of a body at ``alt``/``az`` (may fall outside the image)."""
    scale = width / camera.hfov  # pixels per degree, both axes
    x = width / 2.0 + wrap180(az - camera.azimuth) * scale
    y = camera.horizon_fraction * height - alt * scale
    return x, y


def classify(alt: float, az: float, camera: Camera, width: int, height: int, margin: float = 0.0) -> str:
    """``below_horizon`` / ``out_of_frame`` / ``drawn`` for a body (``margin``: pixels it needs inside)."""
    if alt < 0.0:
        return BELOW_HORIZON
    x, y = project(alt, az, camera, width, height)
    if abs(wrap180(az - camera.azimuth)) > 90.0:
        return OUT_OF_FRAME  # behind the camera
    if margin <= x <= width - margin and margin <= y <= height - margin:
        return DRAWN
    return OUT_OF_FRAME


def _planets_visible(sky: dict[str, Any]) -> bool:
    return float(sky["sun"]["alt"]) < PLANETS_VISIBLE_SUN_ALT


def choose_camera(sky: dict[str, Any]) -> Camera:
    """Face the Moon if it is up, else the brightest planet that may be drawn, else the equator."""
    moon = sky["moon"]
    if moon["alt"] >= 0.0:
        return Camera(azimuth=float(moon["az"]), basis="Moon")
    if _planets_visible(sky):
        up = [p for p in sky["planets"] if p["alt"] >= 0.0]
        if up:
            best = min(up, key=lambda p: p["magnitude"])
            return Camera(azimuth=float(best["az"]), basis=f"brightest planet up ({best['name']})")
    if sky["observer"]["lat"] >= 0.0:
        return Camera(azimuth=180.0, basis="due south (nothing drawable above the horizon)")
    return Camera(azimuth=0.0, basis="due north (nothing drawable above the horizon)")


def moon_radius_px(sky: dict[str, Any], width: int, camera: Camera, scale: float = MOON_SCALE) -> float:
    """Drawn radius of the Moon in pixels (``scale`` times its apparent radius)."""
    return float(sky["moon"]["apparent_diameter_deg"]) / 2.0 * scale * width / camera.hfov


def plan_sky(
    sky: dict[str, Any],
    width: int,
    height: int,
    camera: Camera | None = None,
    moon_scale: float = MOON_SCALE,
) -> dict[str, Any]:
    """Where each body goes on a ``width`` x ``height`` image, and whether it is drawn (and why not)."""
    camera = camera or choose_camera(sky)
    moon = dict(sky["moon"])
    radius = moon_radius_px(sky, width, camera, moon_scale)
    x, y = project(moon["alt"], moon["az"], camera, width, height)
    # the whole disk must be inside the frame to be drawn (a clipped disk would misstate the phase)
    status = classify(moon["alt"], moon["az"], camera, width, height, margin=radius)
    moon.update(x=_round(x, 1), y=_round(y, 1), radius_px=_round(radius, 1), scale=moon_scale, status=status)
    moon["drawn"] = status == DRAWN

    planets_visible = _planets_visible(sky)
    planets: list[dict[str, Any]] = []
    for planet in sky["planets"]:
        entry = dict(planet)
        px, py = project(entry["alt"], entry["az"], camera, width, height)
        status = classify(entry["alt"], entry["az"], camera, width, height, margin=2.0)
        if status == DRAWN and not planets_visible:
            status = DAYLIGHT
        entry.update(x=_round(px, 1), y=_round(py, 1), status=status, drawn=status == DRAWN)
        planets.append(entry)

    return {
        **{k: v for k, v in sky.items() if k not in ("moon", "planets")},
        "camera": camera.as_dict(width, height),
        "moon": moon,
        "planets": planets,
    }


# -- caption facts ---------------------------------------------------------------------


def _fact(label: str, value: str, provenance: Provenance) -> dict[str, str]:
    return caption_fact(label, value, provenance)


def _position_words(alt: float, az: float) -> str:
    return f"altitude {alt:.1f}°, azimuth {az:.1f}° ({compass(az)})"


def observer_for(record: dict[str, Any] | None) -> tuple[float, float, str]:
    """``(lat, lon, source)`` for a folio: its own ``location`` if it has one, else the default.

    A location is ``{"lat"|"latitude": .., "lon"|"lng"|"longitude": ..}`` under
    ``location``, or top-level ``latitude``/``longitude``. ``source`` is
    ``"folio"`` or ``"default"`` (``config/settings.py`` DEFAULT_LATITUDE/LONGITUDE).
    """
    record = record or {}
    loc = record.get("location") if isinstance(record.get("location"), dict) else record
    lat = next((loc.get(k) for k in ("lat", "latitude") if loc.get(k) is not None), None)
    lon = next((loc.get(k) for k in ("lon", "lng", "longitude") if loc.get(k) is not None), None)
    try:
        if lat is not None and lon is not None and -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0:
            return float(lat), float(lon), "folio"
    except (TypeError, ValueError):
        pass
    return float(DEFAULT_LATITUDE), float(DEFAULT_LONGITUDE), "default"


def observer_fact(lat: float, lon: float, source: str) -> dict[str, str]:
    """Where the sky was computed for; a default location says so."""
    where = f"{lat:.4f}°, {lon:.4f}°"
    if source == "folio":
        return _fact("Sky observer", f"{where} (the folio's location)", "record")
    return _fact("Sky observer", f"{where} (default location from config/settings.py; the folio has none)", "record")


def sky_caption_facts(sky: dict[str, Any]) -> list[dict[str, str]]:
    """Computed caption facts for a :func:`compute_sky` result (no camera needed)."""
    moon = sky["moon"]
    facts = [
        _fact(
            "Moon at sealing",
            f"{moon['illumination']:.0f}% illuminated, {moon_phase_words(moon)}",
            "computed",
        )
    ]
    if moon["alt"] < 0.0:
        facts.append(
            _fact("Moon in the sky", f"Moon below horizon at sealing (altitude {moon['alt']:.1f}°)", "computed")
        )
    else:
        limb = moon["bright_limb_from_vertical"]
        facts.append(
            _fact(
                "Moon in the sky",
                f"{_position_words(moon['alt'], moon['az'])}; bright limb toward the "
                f"{limb_direction_words(limb)} ({limb:.0f}° from the vertical)",
                "computed",
            )
        )
    for planet in sky["planets"]:
        if planet["alt"] < 0.0:
            value = f"below horizon (altitude {planet['alt']:.1f}°)"
        else:
            value = f"{_position_words(planet['alt'], planet['az'])}, magnitude {planet['magnitude']:.1f}"
        facts.append(_fact(planet["name"], value, "computed"))
    facts.append(_fact("Sun at sealing", f"altitude {sky['sun']['alt']:.1f}° ({sky['period']})", "computed"))
    return facts


def unavailable_fact(reason: str = "Swiss Ephemeris unavailable") -> dict[str, str]:
    """The caption when no sky could be computed: say so, draw nothing."""
    return _fact("Sky at sealing", f"could not be computed ({reason}); no sky is drawn on the image", "record")


def overlay_caption_fact(plan: dict[str, Any]) -> dict[str, str]:
    """What the composite shows: camera, Moon scale, and each body's drawn / not-drawn status."""
    cam = plan["camera"]
    groups: dict[str, list[str]] = {}
    moon = plan["moon"]
    groups.setdefault(moon["status"], []).append("Moon")
    for planet in plan["planets"]:
        groups.setdefault(planet["status"], []).append(planet["name"])
    parts = [
        f"camera faces azimuth {cam['azimuth']:.0f}° ({compass(cam['azimuth'])}), "
        f"{cam['hfov']:.0f}° wide, horizon {cam['horizon_fraction']:.0%} down, "
        f"top edge at altitude {cam['top_edge_alt']:.0f}°"
    ]
    if moon["drawn"]:
        parts.append(f"Moon drawn at {moon['scale']:g}× apparent size")
    for status in (DRAWN, OUT_OF_FRAME, DAYLIGHT, BELOW_HORIZON):
        if groups.get(status):
            parts.append(f"{_STATUS_WORDS[status]}: {', '.join(groups[status])}")
    return _fact("Sky overlay", "; ".join(parts), "computed")


# -- the scene prompt --------------------------------------------------------------------


# For a devotional painting (no horizon to draw the computed sky against).
EMPTY_BACKGROUND_CLAUSE = (
    "The background sky is clear and empty: no moon, no stars, no planets and no celestial bodies."
)


def empty_sky_clause(period: str | None) -> str:
    """Prompt words for a scene whose sky is left empty for the computed sky to be drawn on."""
    kind = {"day": "daytime ", "twilight": "twilight ", "night": "night "}.get(period or "", "")
    return (
        f"A low horizon under a wide, clear, open {kind}sky that fills the upper frame; "
        "the sky is empty, with no moon, no stars, no planets and no celestial bodies."
    )
