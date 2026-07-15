"""
Geocoding Service for Vajra.Stream
Resolves city/town names to latitude, longitude, and timezone using geopy.

geopy and timezonefinder are imported lazily so that this module can be
imported (and patched in tests) without the optional geopy dependency
being installed.
"""

import logging

logger = logging.getLogger(__name__)


class GeocodingService:
    def __init__(self):
        # Lazy-init: actual geolocator/tf are created on first use.
        self._geolocator = None
        self._tf = None

    def _ensure_clients(self):
        """Lazily create the geopy Nominatim geolocator and TimezoneFinder."""
        if self._geolocator is None:
            from geopy.geocoders import Nominatim

            self._geolocator = Nominatim(user_agent="vajra_stream_astrology")
        if self._tf is None:
            from timezonefinder import TimezoneFinder

            self._tf = TimezoneFinder()

    def get_coordinates_and_timezone(self, location_name: str) -> dict:
        """
        Resolves a location name to lat, lon, and timezone.
        Returns a dict with 'latitude', 'longitude', 'timezone', and 'address'.
        """
        try:
            self._ensure_clients()
            location = self._geolocator.geocode(location_name, timeout=10)
            if not location:
                return {"error": f"Location '{location_name}' not found."}

            lat = location.latitude
            lon = location.longitude
            tz = self._tf.timezone_at(lng=lon, lat=lat)

            return {"latitude": lat, "longitude": lon, "timezone": tz or "UTC", "address": location.address}
        except Exception as e:
            # Catch broadly — geopy exc types are lazily imported too.
            logger.error(f"Geocoding error for {location_name}: {e}")
            return {"error": str(e)}


geocoding_service = GeocodingService()
