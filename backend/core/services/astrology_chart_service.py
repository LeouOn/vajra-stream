"""
Astrology Chart Service using Kerykeion (v5.x factory API)
Provides Natal, Transit, and Synastry calculations and structured exports.

kerykeion is imported lazily so the module can be imported without the
optional dependency being installed.
"""

import datetime
import logging
from typing import Any

from backend.core.services.geocoding_service import geocoding_service

logger = logging.getLogger(__name__)

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


class AstrologyChartService:
    def _create_subject(self, name: str, dt_str: str, city_name: str):
        """Helper to create Kerykeion subject from ISO string and city using the v5 factory API."""
        from kerykeion import AstrologicalSubjectFactory

        # Parse datetime
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(dt_str)

        # Geocode
        geo = geocoding_service.get_coordinates_and_timezone(city_name)
        if "error" in geo:
            raise ValueError(f"Geocoding failed for {city_name}: {geo['error']}")

        return AstrologicalSubjectFactory.from_birth_data(
            name=name,
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            lng=geo["longitude"],
            lat=geo["latitude"],
            tz_str=geo["timezone"],
            online=False,
        )

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

    def get_natal_chart(self, name: str, birth_time_iso: str, birth_city: str) -> dict[str, Any]:
        """Generate a natal chart with structured raw data export."""
        try:
            subject = self._create_subject(name, birth_time_iso, birth_city)

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
            }
            return {"status": "success", "data": raw_data}
        except Exception as e:
            logger.error(f"Natal chart error: {e}")
            return {"error": str(e)}

    def get_daily_transit(
        self, name: str, birth_time_iso: str, birth_city: str, current_time_iso: str | None = None
    ) -> dict[str, Any]:
        """Compare natal chart with current transits using the v5 AspectsFactory."""
        from kerykeion import AspectsFactory, AstrologicalSubjectFactory

        try:
            natal_subject = self._create_subject(name, birth_time_iso, birth_city)

            # Use provided current time or now
            if current_time_iso:
                if current_time_iso.endswith("Z"):
                    current_time_iso = current_time_iso[:-1] + "+00:00"
                now = datetime.datetime.fromisoformat(current_time_iso)
            else:
                now = datetime.datetime.now(datetime.timezone.utc)

            transit_subject = AstrologicalSubjectFactory.from_birth_data(
                name="Transit",
                year=now.year,
                month=now.month,
                day=now.day,
                hour=now.hour,
                minute=now.minute,
                lng=natal_subject.lng,
                lat=natal_subject.lat,
                tz_str=natal_subject.tz_str,
                online=False,
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
                    "transit_time": now.isoformat(),
                    "aspects": aspects_list,
                },
            }
        except Exception as e:
            logger.error(f"Transit error: {e}")
            return {"error": str(e)}

    def get_synastry(
        self, name_a: str, time_a: str, city_a: str, name_b: str, time_b: str, city_b: str
    ) -> dict[str, Any]:
        """Compare two natal charts for compatibility using the v5 AspectsFactory."""
        from kerykeion import AspectsFactory

        try:
            subject_a = self._create_subject(name_a, time_a, city_a)
            subject_b = self._create_subject(name_b, time_b, city_b)

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
                },
            }
        except Exception as e:
            logger.error(f"Synastry error: {e}")
            return {"error": str(e)}


astrology_chart_service = AstrologyChartService()
