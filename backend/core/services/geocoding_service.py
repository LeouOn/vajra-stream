"""
Geocoding Service for Vajra.Stream
Resolves city/town names to latitude, longitude, and timezone using geopy.
"""

import logging

from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)


class GeocodingService:
    def __init__(self):
        # Nominatim requires a distinct user agent
        self.geolocator = Nominatim(user_agent="vajra_stream_astrology")
        self.tf = TimezoneFinder()

    def get_coordinates_and_timezone(self, location_name: str) -> dict:
        """
        Resolves a location name to lat, lon, and timezone.
        Returns a dict with 'latitude', 'longitude', 'timezone', and 'address'.
        """
        try:
            location = self.geolocator.geocode(location_name, timeout=10)
            if not location:
                return {"error": f"Location '{location_name}' not found."}

            lat = location.latitude
            lon = location.longitude
            tz = self.tf.timezone_at(lng=lon, lat=lat)

            return {"latitude": lat, "longitude": lon, "timezone": tz or "UTC", "address": location.address}
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding error for {location_name}: {e}")
            return {"error": "Geocoding service unavailable."}
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
            return {"error": str(e)}


geocoding_service = GeocodingService()
