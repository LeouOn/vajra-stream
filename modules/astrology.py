"""
Astrology Module
Wraps astrology and astrocartography functionality
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interfaces import EventBus


class AstrologyService:
    """Unified astrology and astrocartography service"""

    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self._astro_engine = None
        self._astrocartography = None

    @property
    def astrology(self):
        """Get astrology engine"""
        if self._astro_engine is None:
            try:
                from core.astrology import AstrologyEngine
                self._astro_engine = AstrologyEngine()
            except ImportError:
                self._astro_engine = None
        return self._astro_engine

    @property
    def astrocartography(self):
        """Get astrocartography analyzer"""
        if self._astrocartography is None:
            try:
                from core.astrocartography import AstrocartographyAnalyzer
                self._astrocartography = AstrocartographyAnalyzer()
            except ImportError:
                self._astrocartography = None
        return self._astrocartography

    def calculate_natal_chart(
        self,
        birth_date: datetime,
        latitude: float,
        longitude: float,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate natal chart"""
        if self.astrology is None:
            return {
                'error': 'Astrology engine not available - astropy not installed.\n'
                         'Install with: pip install astropy astroquery\n'
                         'Or install all dependencies: pip install -r requirements.txt'
            }

        try:
            chart = self.astrology.calculate_chart(
                date=birth_date,
                lat=latitude,
                lon=longitude,
                name=name
            )
            return {
                'status': 'success',
                'chart': chart,
                'birth_date': birth_date.isoformat(),
                'location': {'latitude': latitude, 'longitude': longitude}
            }
        except Exception as e:
            return {'error': str(e)}

    def get_current_transits(
        self,
        natal_chart: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get current planetary transits"""
        if self.astrology is None:
            return {
                'error': 'Astrology engine not available - astropy not installed.\n'
                         'Install with: pip install astropy astroquery\n'
                         'Or install all dependencies: pip install -r requirements.txt'
            }

        try:
            transits = self.astrology.get_transits(
                natal_chart=natal_chart,
                transit_date=datetime.now()
            )
            return {
                'status': 'success',
                'transits': transits,
                'date': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}

    def analyze_location_energy(
        self,
        natal_chart: Dict[str, Any],
        target_latitude: float,
        target_longitude: float
    ) -> Dict[str, Any]:
        """Analyze energetic influence of a location (astrocartography)"""
        if self.astrocartography is None:
            return {
                'error': 'Astrocartography not available - astropy not installed.\n'
                         'Install with: pip install astropy astroquery\n'
                         'Or install all dependencies: pip install -r requirements.txt'
            }

        try:
            analysis = self.astrocartography.analyze_location(
                chart=natal_chart,
                lat=target_latitude,
                lon=target_longitude
            )
            return {
                'status': 'success',
                'analysis': analysis,
                'location': {
                    'latitude': target_latitude,
                    'longitude': target_longitude
                }
            }
        except Exception as e:
            return {'error': str(e)}

    def find_power_places(
        self,
        natal_chart: Dict[str, Any],
        intention: str = "general"
    ) -> Dict[str, Any]:
        """Find energetically favorable locations"""
        if self.astrocartography is None:
            return {
                'error': 'Astrocartography not available - astropy not installed.\n'
                         'Install with: pip install astropy astroquery\n'
                         'Or install all dependencies: pip install -r requirements.txt'
            }

        try:
            places = self.astrocartography.find_power_places(
                chart=natal_chart,
                intention=intention
            )
            return {
                'status': 'success',
                'intention': intention,
                'power_places': places
            }
        except Exception as e:
            return {'error': str(e)}

    def get_planetary_positions(
        self,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get current planetary positions"""
        if self.astrology is None:
            return {
                'error': 'Astrology engine not available - astropy not installed.\n'
                         'Install with: pip install astropy astroquery\n'
                         'Or install all dependencies: pip install -r requirements.txt'
            }

        if date is None:
            date = datetime.now()

        try:
            positions = self.astrology.get_planetary_positions(date)
            return {
                'status': 'success',
                'date': date.isoformat(),
                'positions': positions
            }
        except Exception as e:
            return {'error': str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get status of astrology subsystems"""
        return {
            'astrology_engine': self.astrology is not None,
            'astrocartography': self.astrocartography is not None
        }
