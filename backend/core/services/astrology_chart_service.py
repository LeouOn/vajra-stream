"""
Astrology Chart Service using Kerykeion
Provides Natal, Transit, and Synastry calculations and structured exports.
"""
import datetime
import logging
import json
from typing import Dict, Any

from kerykeion import AstrologicalSubject, SynastryAspects

from backend.core.services.geocoding_service import geocoding_service

logger = logging.getLogger(__name__)


class AstrologyChartService:
    def _create_subject(self, name: str, dt_str: str, city_name: str) -> AstrologicalSubject:
        """Helper to create AstrologicalSubject from ISO string and city"""
        # Parse datetime
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(dt_str)

        # Geocode
        geo = geocoding_service.get_coordinates_and_timezone(city_name)
        if "error" in geo:
            raise ValueError(f"Geocoding failed for {city_name}: {geo['error']}")

        return AstrologicalSubject(
            name,
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            lng=geo["longitude"],
            lat=geo["latitude"],
            tz_str=geo["timezone"],
            city=city_name
        )

    def _serialize_planet(self, planet_obj) -> Dict[str, Any]:
        """Safely extract data from a Kerykeion planet object"""
        if not planet_obj:
            return {}
        try:
            # If it's a pydantic model in newer kerykeion versions
            if hasattr(planet_obj, "model_dump"):
                return planet_obj.model_dump()
            elif hasattr(planet_obj, "dict"):
                return planet_obj.dict()
            else:
                return {
                    "name": getattr(planet_obj, "name", ""),
                    "sign": getattr(planet_obj, "sign", ""),
                    "sign_num": getattr(planet_obj, "sign_num", -1),
                    "position": getattr(planet_obj, "position", 0.0),
                    "abs_pos": getattr(planet_obj, "abs_pos", 0.0),
                    "retrograde": getattr(planet_obj, "retrograde", False),
                    "house": getattr(planet_obj, "house", "")
                }
        except Exception:
            return str(planet_obj)
            
    def _serialize_house(self, house_obj) -> Dict[str, Any]:
        if not house_obj:
            return {}
        try:
            if hasattr(house_obj, "model_dump"):
                return house_obj.model_dump()
            elif hasattr(house_obj, "dict"):
                return house_obj.dict()
            else:
                return {
                    "name": getattr(house_obj, "name", ""),
                    "sign": getattr(house_obj, "sign", ""),
                    "position": getattr(house_obj, "position", 0.0),
                    "abs_pos": getattr(house_obj, "abs_pos", 0.0)
                }
        except Exception:
            return str(house_obj)

    def get_natal_chart(self, name: str, birth_time_iso: str, birth_city: str) -> Dict[str, Any]:
        """Generate a natal chart with structured raw data export."""
        try:
            subject = self._create_subject(name, birth_time_iso, birth_city)
            
            planet_names = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "mean_node", "true_node", "chiron"]
            planets = {}
            for p_name in planet_names:
                p_obj = getattr(subject, p_name, None)
                if p_obj:
                    planets[p_name] = self._serialize_planet(p_obj)
                
            house_names = ["first_house", "second_house", "third_house", "fourth_house", "fifth_house", 
                           "sixth_house", "seventh_house", "eighth_house", "ninth_house", "tenth_house", 
                           "eleventh_house", "twelfth_house"]
            houses = {}
            for h_name in house_names:
                h_obj = getattr(subject, h_name, None)
                if h_obj:
                    houses[h_name] = self._serialize_house(h_obj)

            raw_data = {
                "subject": name,
                "city": birth_city,
                "datetime": birth_time_iso,
                "sun": self._serialize_planet(subject.sun),
                "moon": self._serialize_planet(subject.moon),
                "ascendant": self._serialize_house(subject.first_house),
                "planets": planets,
                "houses": houses
            }
            return {"status": "success", "data": raw_data}
        except Exception as e:
            logger.error(f"Natal chart error: {e}")
            return {"error": str(e)}

    def get_daily_transit(self, name: str, birth_time_iso: str, birth_city: str, current_time_iso: str = None) -> Dict[str, Any]:
        """Compare natal chart with current transits."""
        try:
            natal_subject = self._create_subject(name, birth_time_iso, birth_city)
            
            # Use provided current time or now
            if current_time_iso:
                if current_time_iso.endswith("Z"):
                    current_time_iso = current_time_iso[:-1] + "+00:00"
                now = datetime.datetime.fromisoformat(current_time_iso)
            else:
                now = datetime.datetime.now(datetime.timezone.utc)
                
            transit_subject = AstrologicalSubject(
                "Transit",
                now.year, now.month, now.day, now.hour, now.minute,
                lng=natal_subject.lng, lat=natal_subject.lat, 
                tz_str=natal_subject.tz_str, city=natal_subject.city
            )
            
            # Use SynastryAspects for Transit-Natal relationship
            aspects = SynastryAspects(natal_subject, transit_subject)
            aspects_list = []
            
            # Extract relevant aspects
            for aspect in aspects.get_relevant_aspects():
                aspects_list.append({
                    "natal_planet": aspect.p1_name,
                    "transit_planet": aspect.p2_name,
                    "aspect": aspect.aspect,
                    "orb": aspect.orbit,
                    "exactness": 1.0 - (aspect.orbit / 8.0) # Approx
                })
                
            return {
                "status": "success", 
                "data": {
                    "subject": name,
                    "transit_time": now.isoformat(),
                    "aspects": aspects_list
                }
            }
        except Exception as e:
            logger.error(f"Transit error: {e}")
            return {"error": str(e)}

    def get_synastry(self, name_a: str, time_a: str, city_a: str, name_b: str, time_b: str, city_b: str) -> Dict[str, Any]:
        """Compare two natal charts for compatibility."""
        try:
            subject_a = self._create_subject(name_a, time_a, city_a)
            subject_b = self._create_subject(name_b, time_b, city_b)
            
            aspects = SynastryAspects(subject_a, subject_b)
            aspects_list = []
            
            for aspect in aspects.get_relevant_aspects():
                aspects_list.append({
                    "person_a_planet": aspect.p1_name,
                    "person_b_planet": aspect.p2_name,
                    "aspect": aspect.aspect,
                    "orb": aspect.orbit
                })
                
            return {
                "status": "success",
                "data": {
                    "person_a": name_a,
                    "person_b": name_b,
                    "aspects": aspects_list
                }
            }
        except Exception as e:
            logger.error(f"Synastry error: {e}")
            return {"error": str(e)}

astrology_chart_service = AstrologyChartService()
