"""
Astrology Chart Service using Kerykeion (v5.x factory API)
Provides Natal, Transit, and Synastry calculations and structured exports.

kerykeion is imported lazily so the module can be imported without the
optional dependency being installed.
"""

import datetime
import logging
from dataclasses import dataclass
from datetime import date as _date
from typing import Any
from zoneinfo import ZoneInfo

from backend.core.services.geocoding_service import geocoding_service
from core.astro.timezone_policy import (
    TimezonePolicyError,
    UnknownTimezone,
    resolve_local,
)

logger = logging.getLogger(__name__)

#: How far a zone's UTC offset may sit from the solar time implied by the
#: longitude before the service says so. Three hours is deliberately loose: some
#: real zones are far from solar time (Xinjiang at ~87 E keeps Beijing time, about
#: 2.2 h off; India is about 0.4 h off). It is a WARNING and never an error,
#: because either the coordinates or the zone could be the wrong one, and only
#: the caller can say which.
SOLAR_TIME_TOLERANCE_HOURS = 3.0

# Canonical sign names for normalization (Kerykeion v5 uses abbreviations)
_SIGN_NORMALIZE = {
    "Ari": "Aries",
    "Tau": "Taurus",
    "Gem": "Gemini",
    "Can": "Cancer",
    "Leo": "Leo",
    "Vir": "Virgo",
    "Lib": "Libra",
    "Sco": "Scorpio",
    "Sag": "Sagittarius",
    "Cap": "Capricorn",
    "Aqu": "Aquarius",
    "Pis": "Pisces",
}


@dataclass(frozen=True)
class _ResolvedInstant:
    """One birth or transit time, resolved to a single UTC instant.

    Attributes:
        utc: The instant, aware, UTC.
        zone: The IANA name of the city the time was read in.
        offset: That zone's UTC offset at ``utc``.
        is_dst: Whether the zone database calls ``utc`` daylight time.
        warnings: Notes about anything the caller should know.
        lat: Latitude of the city.
        lng: Longitude of the city.
        time_assumed: True when the caller gave no time of day, so midnight was
            assumed. The instant is then real but the chart is not trustworthy:
            the Ascendant, the houses and the angles all move through the day.
    """

    utc: datetime.datetime
    zone: str
    offset: datetime.timedelta
    is_dst: bool | None
    warnings: tuple[str, ...]
    lat: float
    lng: float
    time_assumed: bool = False

    def as_payload(self) -> dict[str, Any]:
        """The additive ``time_resolution`` object for the response."""
        return {
            "utc_iso": self.utc.isoformat(),
            "offset": self.offset.total_seconds() / 3600.0,
            "is_dst": self.is_dst,
            "zone": self.zone,
            "warnings": list(self.warnings),
            "time_assumed": self.time_assumed,
        }


class AstrologyChartService:
    def _resolve_instant(
        self,
        dt_str: str,
        city_name: str,
        *,
        ambiguous: str | None = None,
        nonexistent: str | None = None,
        what: str = "birth",
    ) -> _ResolvedInstant:
        """Turn (an ISO timestamp, a city) into ONE UTC instant plus metadata.

        Rules, in order:

        * A timestamp that CARRIES an offset (or ``Z``/``z``) is an exact instant.
          It is kept. The city's zone does not override it. If the city's zone
          disagrees with the offset the caller gave, that is a warning, not an
          error.
        * A timestamp WITHOUT an offset is a wall-clock reading in the city's zone.
          It is resolved strictly: an ambiguous reading (a fall-back overlap) or a
          nonexistent one (a spring-forward gap) raises unless the caller opted in
          with ``ambiguous`` / ``nonexistent``.
        * A DATE-ONLY timestamp carries no time of day. It is accepted, but the
          response says so loudly: ``time_assumed`` is true and a warning says the
          Ascendant, houses and angles are not reliable. Detection is by PARSING
          (``date.fromisoformat``), so it behaves the same on 3.10, 3.11 and 3.13 -
          on 3.11+ ``datetime.fromisoformat`` alone would quietly read a date as
          midnight.
        * Seconds are kept. Microseconds are not supported by kerykeion and are
          truncated, with a warning when they were non-zero.

        Raises
        ------
        TimezonePolicyError
            For an ambiguous or nonexistent wall time, or an unknown zone. The
            HTTP layer turns this into 422.
        ValueError
            For an unparseable timestamp or a failed geocode. Today's behaviour
            for those is a 500 with the error string.
        """
        # --- parse ---------------------------------------------------------- #
        text = dt_str
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        date_only = _is_date_only(text)
        try:
            parsed = datetime.datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Could not parse datetime {dt_str!r}: {exc}") from exc

        # --- geocode -------------------------------------------------------- #
        geo = geocoding_service.get_coordinates_and_timezone(city_name)
        if "error" in geo:
            raise ValueError(f"Geocoding failed for {city_name}: {geo['error']}")
        zone_name = geo["timezone"]
        lat = geo["latitude"]
        lng = geo["longitude"]

        # The zone is validated ONCE, for both the aware and the naive path, so
        # the two paths cannot disagree about the status or the message. A zone the
        # system IANA database does not know is a ZONE problem (422); a geocoder
        # that returned no "timezone" key at all is a GEOCODER failure (500),
        # which is the KeyError below.
        zone = _load_zone_or_raise(zone_name)

        warnings: list[str] = []

        if date_only:
            warnings.append(
                f"no time of {what} given: 00:00 local assumed; the Ascendant, the "
                f"houses and the angles are NOT reliable"
            )
        if parsed.microsecond:
            warnings.append(
                f"Microseconds are not supported by kerykeion; truncated " f"{parsed.microsecond} us from {dt_str!r}."
            )
            parsed = parsed.replace(microsecond=0)

        # --- resolve -------------------------------------------------------- #
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            # The caller gave an exact instant. Keep it.
            given_offset = parsed.utcoffset()
            utc = parsed.astimezone(datetime.timezone.utc)
            city_local = utc.astimezone(zone)
            city_offset = city_local.utcoffset()
            city_is_dst = city_local.dst() not in (None, datetime.timedelta(0))
            if city_offset != given_offset:
                warnings.append(
                    f"offset {_format_offset(given_offset)} differs from "
                    f"{zone_name} ({_format_offset(city_offset)}) at that instant; "
                    f"using the offset you gave"
                )
            warnings.extend(_plausibility_warnings(zone, zone_name, utc, lng))
            return _ResolvedInstant(
                utc=utc,
                zone=zone_name,
                offset=city_offset,
                is_dst=city_is_dst,
                warnings=tuple(warnings),
                lat=lat,
                lng=lng,
                time_assumed=date_only,
            )

        # Naive wall time: the city supplies the zone, resolved strictly.
        resolution = resolve_local(parsed, zone_name, ambiguous=ambiguous, nonexistent=nonexistent)
        warnings.extend(resolution.warnings)
        warnings.extend(_plausibility_warnings(zone, zone_name, resolution.utc, lng))
        return _ResolvedInstant(
            utc=resolution.utc,
            zone=resolution.zone,
            offset=resolution.utc_offset,
            is_dst=resolution.is_dst,
            warnings=tuple(warnings),
            lat=lat,
            lng=lng,
            time_assumed=date_only,
        )

    @staticmethod
    def _subject_from_instant(instant: _ResolvedInstant, name: str):
        """Build a kerykeion subject for an unambiguous instant.

        Kerykeion takes naive local fields plus ``tz_str`` and cannot be told
        which side of a DST fold was meant. So the UTC wall fields are passed with
        ``tz_str="UTC"``: the fields and the zone then agree by construction and
        the result is one instant, not a guess. Houses and the angles depend on
        lat/lng and on UT, not on ``tz_str``, so nothing else moves.
        """
        from kerykeion import AstrologicalSubjectFactory

        utc = instant.utc
        return AstrologicalSubjectFactory.from_birth_data(
            name=name,
            year=utc.year,
            month=utc.month,
            day=utc.day,
            hour=utc.hour,
            minute=utc.minute,
            seconds=utc.second,
            lng=instant.lng,
            lat=instant.lat,
            tz_str="UTC",
            online=False,
        )

    def _create_subject(
        self,
        name: str,
        dt_str: str,
        city_name: str,
        *,
        ambiguous: str | None = None,
        nonexistent: str | None = None,
    ):
        """Helper to create Kerykeion subject from ISO string and city.

        The instant is resolved by :meth:`_resolve_instant`; the subject is then
        built from the UTC wall fields so the result is unambiguous.
        """
        instant = self._resolve_instant(dt_str, city_name, ambiguous=ambiguous, nonexistent=nonexistent, what="birth")
        return self._subject_from_instant(instant, name)

    def _normalize_sign(self, sign: str) -> str:
        """Expand abbreviated sign names from Kerykeion v5 to full names."""
        return _SIGN_NORMALIZE.get(sign, sign)

    def _serialize_point(self, point_obj) -> dict[str, Any]:
        """Extract data from a Kerykeion v5 point model (Pydantic)."""
        if not point_obj:
            return {}
        try:
            data = point_obj.model_dump()
            # Normalize abbreviated sign names
            if "sign" in data:
                data["sign"] = self._normalize_sign(data["sign"])
            return data
        except Exception:
            return str(point_obj)

    def get_natal_chart(
        self,
        name: str,
        birth_time_iso: str,
        birth_city: str,
        *,
        ambiguous: str | None = None,
        nonexistent: str | None = None,
    ) -> dict[str, Any]:
        """Generate a natal chart with structured raw data export."""
        try:
            instant = self._resolve_instant(
                birth_time_iso, birth_city, ambiguous=ambiguous, nonexistent=nonexistent, what="birth"
            )
            subject = self._subject_from_instant(instant, name)

            planet_names = [
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
                "mean_node",
                "true_node",
                "chiron",
            ]
            planets = {}
            for p_name in planet_names:
                p_obj = getattr(subject, p_name, None)
                if p_obj:
                    planets[p_name] = self._serialize_point(p_obj)

            house_names = [
                "first_house",
                "second_house",
                "third_house",
                "fourth_house",
                "fifth_house",
                "sixth_house",
                "seventh_house",
                "eighth_house",
                "ninth_house",
                "tenth_house",
                "eleventh_house",
                "twelfth_house",
            ]
            houses = {}
            for h_name in house_names:
                h_obj = getattr(subject, h_name, None)
                if h_obj:
                    houses[h_name] = self._serialize_point(h_obj)

            raw_data = {
                "subject": name,
                "city": birth_city,
                "datetime": birth_time_iso,
                "sun": self._serialize_point(subject.sun),
                "moon": self._serialize_point(subject.moon),
                "ascendant": self._serialize_point(subject.first_house),
                "planets": planets,
                "houses": houses,
                "time_resolution": instant.as_payload(),
            }
            return {"status": "success", "data": raw_data}
        except TimezonePolicyError:
            raise
        except Exception as e:
            logger.error(f"Natal chart error: {e}")
            return {"error": str(e)}

    def get_daily_transit(
        self,
        name: str,
        birth_time_iso: str,
        birth_city: str,
        current_time_iso: str | None = None,
        *,
        ambiguous: str | None = None,
        nonexistent: str | None = None,
    ) -> dict[str, Any]:
        """Compare natal chart with current transits using the v5 AspectsFactory.

        The transit chart is built from a UTC INSTANT, never from the wall fields
        of a UTC clock read as if it were the birth city's local clock.

        * ``current_time_iso`` WITH an offset is kept as the instant it names.
        * ``current_time_iso`` WITHOUT an offset is a wall-clock reading in the
          NATAL city's zone (the same zone the birth was read in) and is resolved
          there, strictly.
        * No ``current_time_iso`` means now, as an aware UTC instant.
        """
        from kerykeion import AspectsFactory

        try:
            instant = self._resolve_instant(
                birth_time_iso, birth_city, ambiguous=ambiguous, nonexistent=nonexistent, what="birth"
            )
            natal_subject = self._subject_from_instant(instant, name)

            # --- the transit instant ---------------------------------------- #
            transit_warnings: list[str] = []
            transit_time_assumed = False
            if current_time_iso:
                text = current_time_iso
                if text.endswith(("Z", "z")):
                    text = text[:-1] + "+00:00"
                transit_time_assumed = _is_date_only(text)
                try:
                    parsed = datetime.datetime.fromisoformat(text)
                except ValueError as exc:
                    raise ValueError(f"Could not parse datetime {current_time_iso!r}: {exc}") from exc
                if parsed.microsecond:
                    transit_warnings.append(
                        f"Microseconds are not supported by kerykeion; truncated "
                        f"{parsed.microsecond} us from {current_time_iso!r}."
                    )
                    parsed = parsed.replace(microsecond=0)
                if transit_time_assumed:
                    transit_warnings.append(
                        "no transit time given: 00:00 local assumed; the transit " "positions are NOT reliable"
                    )
                if parsed.tzinfo is not None and parsed.utcoffset() is not None:
                    # The caller gave an exact instant. Keep it, and report the
                    # NATAL city's zone honestly: the transit chart is drawn at the
                    # natal coordinates, so that is the zone it belongs to. The
                    # caller's offset is kept in the instant, and a disagreement
                    # with the zone is said out loud, exactly as on the birth path.
                    given_offset = parsed.utcoffset()
                    transit_utc = parsed.astimezone(datetime.timezone.utc)
                    transit_zone = instant.zone
                    zone_local = transit_utc.astimezone(ZoneInfo(transit_zone))
                    transit_offset = zone_local.utcoffset()
                    transit_is_dst = zone_local.dst() not in (None, datetime.timedelta(0))
                    if transit_offset != given_offset:
                        transit_warnings.append(
                            f"offset {_format_offset(given_offset)} differs from "
                            f"{transit_zone} ({_format_offset(transit_offset)}) at that "
                            f"instant; using the offset you gave"
                        )
                else:
                    resolution = resolve_local(
                        parsed,
                        instant.zone,
                        ambiguous=ambiguous,
                        nonexistent=nonexistent,
                    )
                    transit_utc = resolution.utc
                    transit_offset = resolution.utc_offset
                    transit_is_dst = resolution.is_dst
                    transit_zone = resolution.zone
                    transit_warnings.extend(resolution.warnings)
            else:
                transit_utc = datetime.datetime.now(datetime.timezone.utc)
                transit_offset = datetime.timedelta(0)
                transit_is_dst = False
                transit_zone = "UTC"

            transit_subject = self._subject_from_instant(
                _ResolvedInstant(
                    utc=transit_utc,
                    zone=transit_zone,
                    offset=transit_offset,
                    is_dst=transit_is_dst,
                    warnings=(),
                    lat=instant.lat,
                    lng=instant.lng,
                ),
                "Transit",
            )

            # Use AspectsFactory for transit-natal relationship
            result = AspectsFactory.dual_chart_aspects(natal_subject, transit_subject)
            aspects_list = []

            for aspect in result.aspects:
                aspects_list.append(
                    {
                        "natal_planet": aspect.p1_name,
                        "transit_planet": aspect.p2_name,
                        "aspect": aspect.aspect,
                        "orb": aspect.orbit,
                        "exactness": 1.0 - (aspect.orbit / 8.0),  # approximate
                    }
                )

            return {
                "status": "success",
                "data": {
                    "subject": name,
                    "transit_time": transit_utc.isoformat(),
                    "aspects": aspects_list,
                    "time_resolution": instant.as_payload(),
                    "transit_time_resolution": {
                        "utc_iso": transit_utc.isoformat(),
                        "offset": transit_offset.total_seconds() / 3600.0,
                        "is_dst": transit_is_dst,
                        "zone": transit_zone,
                        "warnings": list(transit_warnings),
                        "time_assumed": transit_time_assumed,
                    },
                },
            }
        except TimezonePolicyError:
            raise
        except Exception as e:
            logger.error(f"Transit error: {e}")
            return {"error": str(e)}

    def get_synastry(
        self,
        name_a: str,
        time_a: str,
        city_a: str,
        name_b: str,
        time_b: str,
        city_b: str,
        *,
        ambiguous: str | None = None,
        nonexistent: str | None = None,
        ambiguous_b: str | None = None,
        nonexistent_b: str | None = None,
    ) -> dict[str, Any]:
        """Compare two natal charts for compatibility using the v5 AspectsFactory.

        The ``ambiguous`` / ``nonexistent`` opt-ins apply to BOTH people, and
        ``ambiguous_b`` / ``nonexistent_b`` override them for the SECOND person
        only. That is how two people in different cities can need DIFFERENT
        answers: one may sit in a fall-back overlap while the other is unique. A
        person whose time is unique is never moved by an opt-in meant for
        somebody else.

        The two people may need opposite answers (A ambiguous and B not, or B
        ambiguous and A not). With only the shared pair that is impossible: the
        opt-in reaches both, and a gap for B with only ``ambiguous`` set raises
        ``NonexistentLocalTime`` before any chart is built.
        """
        from kerykeion import AspectsFactory

        try:
            instant_a = self._resolve_instant(
                time_a, city_a, ambiguous=ambiguous, nonexistent=nonexistent, what="birth"
            )
            instant_b = self._resolve_instant(
                time_b,
                city_b,
                ambiguous=ambiguous_b if ambiguous_b is not None else ambiguous,
                nonexistent=nonexistent_b if nonexistent_b is not None else nonexistent,
                what="birth",
            )
            subject_a = self._subject_from_instant(instant_a, name_a)
            subject_b = self._subject_from_instant(instant_b, name_b)

            result = AspectsFactory.dual_chart_aspects(subject_a, subject_b)
            aspects_list = []

            for aspect in result.aspects:
                aspects_list.append(
                    {
                        "person_a_planet": aspect.p1_name,
                        "person_b_planet": aspect.p2_name,
                        "aspect": aspect.aspect,
                        "orb": aspect.orbit,
                    }
                )

            return {
                "status": "success",
                "data": {
                    "person_a": name_a,
                    "person_b": name_b,
                    "aspects": aspects_list,
                    "time_resolution_a": instant_a.as_payload(),
                    "time_resolution_b": instant_b.as_payload(),
                },
            }
        except TimezonePolicyError:
            raise
        except Exception as e:
            logger.error(f"Synastry error: {e}")
            return {"error": str(e)}


def _is_date_only(text: str) -> bool:
    """Whether an ISO string carries a DATE but no TIME.

    Detected by PARSING, not by length: ``date.fromisoformat`` succeeds only for
    a date-only string and has been strict since 3.7, so this behaves the same
    on 3.10, 3.11 and 3.13. On 3.11+ ``datetime.fromisoformat`` alone would read
    ``"1990-07-04"`` as midnight without saying so.
    """
    try:
        _date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _load_zone_or_raise(zone_name: str) -> ZoneInfo:
    """Load an IANA zone, or raise the policy's typed error.

    The message is the policy module's: the name is truncated and the
    interpreter's own text is left out, because that text can contain a
    filesystem path. Used for BOTH the aware and the naive path so the two
    cannot disagree about the status or the wording.
    """
    if not isinstance(zone_name, str):
        raise UnknownTimezone(str(zone_name))
    try:
        return ZoneInfo(zone_name)
    except Exception as exc:  # ZoneInfoNotFoundError, ValueError, TypeError
        raise UnknownTimezone(zone_name) from exc


def _plausibility_warnings(zone: ZoneInfo, zone_name: str, utc: datetime.datetime, lng: float) -> list[str]:
    """Warn when the geocoded zone does not fit the geocoded longitude.

    The comparison uses the zone's STANDARD offset - ``utcoffset() - dst()`` -
    and not the offset in force at that instant, so a country that observes
    daylight time is not flagged for it. China is the case that matters: it keeps
    Beijing time in the far west, so Xinjiang at ~87 E is about 2.2 h from solar
    time in winter and 3.2 h in summer, and neither should be called a defect.

    A warning, never an error. The live geocoder returns ``"UTC"`` when
    timezonefinder has no match, which silently charts the wall clock as UTC;
    this says so instead.
    """
    warnings: list[str] = []
    if not isinstance(lng, int | float):
        return warnings
    local = utc.astimezone(zone)
    offset = local.utcoffset()
    if offset is None:
        return warnings
    dst = local.dst() or datetime.timedelta(0)
    standard_hours = (offset - dst).total_seconds() / 3600.0
    solar_hours = lng / 15.0
    # A clock offset is MODULO 24 h. The naive difference would report 24.45 h for
    # Pacific/Apia (+13 at 172 W), which is a correct pair, because the date line
    # puts the longitude on the far side of Greenwich. Wrap the difference.
    difference = abs(((standard_hours - solar_hours + 12.0) % 24.0) - 12.0)
    if zone_name == "UTC" and difference > SOLAR_TIME_TOLERANCE_HOURS:
        warnings.append(
            f"the geocoded zone is exactly 'UTC' but the longitude {lng} is "
            f"{abs(lng):.2f} deg from Greenwich (solar time {solar_hours:+.2f} h); "
            f"'UTC' is usually a fallback when the timezone database has no match, "
            f"so the wall clock may be wrong"
        )
    elif difference > SOLAR_TIME_TOLERANCE_HOURS:
        warnings.append(
            f"the geocoded zone {zone_name} has a standard offset of UTC{standard_hours:+.2f} h "
            f"but the longitude {lng} implies solar time {solar_hours:+.2f} h; they differ by "
            f"{difference:.2f} h, more than the {SOLAR_TIME_TOLERANCE_HOURS:.1f} h "
            f"tolerance, so the coordinates and the zone may not belong together"
        )
    return warnings


def _format_offset(delta: datetime.timedelta | None) -> str:
    """Render a UTC offset as +HH:MM, for warning messages."""
    if delta is None:
        return "none"
    total = int(delta.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return f"{sign}{total // 3600:02d}:{(total % 3600) // 60:02d}"


astrology_chart_service = AstrologyChartService()
