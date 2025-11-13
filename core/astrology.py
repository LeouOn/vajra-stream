"""
Vajra.Stream Astrology Module
Kalachakra time-space calculations for auspicious timing
Uses Swiss Ephemeris for precise astrological calculations
"""

import swisseph as swe
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple, Optional
import math


class AstrologicalCalculator:
    """
    Calculate astrological data for timing practices
    Supports planetary positions, lunar phases, auspicious times
    """

    def __init__(self):
        # Set ephemeris path (uses built-in data)
        swe.set_ephe_path('')

        # Planet constants
        self.PLANETS = {
            'sun': swe.SUN,
            'moon': swe.MOON,
            'mercury': swe.MERCURY,
            'venus': swe.VENUS,
            'mars': swe.MARS,
            'jupiter': swe.JUPITER,
            'saturn': swe.SATURN,
            'uranus': swe.URANUS,
            'neptune': swe.NEPTUNE,
            'pluto': swe.PLUTO,
            'north_node': swe.MEAN_NODE,
        }

        # Zodiac signs
        self.SIGNS = [
            'Aries', 'Taurus', 'Gemini', 'Cancer',
            'Leo', 'Virgo', 'Libra', 'Scorpio',
            'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
        ]

    def get_julian_day(self, dt: datetime) -> float:
        """Convert datetime to Julian day number"""
        return swe.julday(dt.year, dt.month, dt.day,
                         dt.hour + dt.minute/60.0 + dt.second/3600.0)

    def get_planetary_positions(self, dt: datetime, location: Tuple[float, float] = None) -> Dict:
        """
        Get positions of all planets at given time
        location: (latitude, longitude) in degrees
        """
        jd = self.get_julian_day(dt)
        positions = {}

        for name, planet_id in self.PLANETS.items():
            # Calculate position (longitude, latitude, distance, speed in long, speed in lat, speed in dist)
            result = swe.calc_ut(jd, planet_id)
            longitude = result[0][0]

            # Convert to sign and degree
            sign_num = int(longitude / 30)
            degree_in_sign = longitude % 30

            positions[name] = {
                'longitude': longitude,
                'sign': self.SIGNS[sign_num],
                'degree': degree_in_sign,
                'formatted': f"{self.SIGNS[sign_num]} {degree_in_sign:.2f}°"
            }

        return positions

    def get_moon_phase(self, dt: datetime) -> Dict:
        """
        Calculate current moon phase
        Returns phase name, illumination, and angle
        """
        jd = self.get_julian_day(dt)

        # Get Sun and Moon positions
        sun_pos = swe.calc_ut(jd, swe.SUN)[0][0]
        moon_pos = swe.calc_ut(jd, swe.MOON)[0][0]

        # Calculate phase angle
        phase_angle = (moon_pos - sun_pos) % 360

        # Calculate illumination (0-100%)
        illumination = (1 - math.cos(math.radians(phase_angle))) / 2 * 100

        # Determine phase name
        if phase_angle < 45:
            phase_name = "New Moon"
        elif phase_angle < 90:
            phase_name = "Waxing Crescent"
        elif phase_angle < 135:
            phase_name = "First Quarter"
        elif phase_angle < 180:
            phase_name = "Waxing Gibbous"
        elif phase_angle < 225:
            phase_name = "Full Moon"
        elif phase_angle < 270:
            phase_name = "Waning Gibbous"
        elif phase_angle < 315:
            phase_name = "Last Quarter"
        else:
            phase_name = "Waning Crescent"

        return {
            'phase_name': phase_name,
            'illumination': illumination,
            'phase_angle': phase_angle,
            'is_new_moon': abs(phase_angle) < 5 or abs(phase_angle - 360) < 5,
            'is_full_moon': abs(phase_angle - 180) < 5
        }

    def get_lunar_mansion(self, dt: datetime) -> Dict:
        """
        Calculate current Nakshatra (lunar mansion)
        27 divisions of the zodiac used in Vedic astrology
        """
        jd = self.get_julian_day(dt)
        moon_pos = swe.calc_ut(jd, swe.MOON)[0][0]

        # Nakshatras are 13°20' each (360° / 27)
        nakshatra_num = int(moon_pos / (360/27))

        NAKSHATRAS = [
            'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
            'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
            'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
            'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta',
            'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
        ]

        return {
            'number': nakshatra_num + 1,
            'name': NAKSHATRAS[nakshatra_num],
            'moon_position': moon_pos
        }

    def calculate_auspicious_times(self, date: datetime, location: Tuple[float, float]) -> Dict:
        """
        Calculate auspicious times for practice
        location: (latitude, longitude)
        """
        lat, lon = location

        # Calculate sunrise and sunset
        jd = self.get_julian_day(date)

        # Rise and set times
        rise_result = swe.rise_trans(jd, swe.SUN, lon, lat, rsmi=swe.CALC_RISE)
        set_result = swe.rise_trans(jd, swe.SUN, lon, lat, rsmi=swe.CALC_SET)

        # Convert JD back to datetime
        def jd_to_datetime(jd_time):
            result = swe.revjul(jd_time)
            return datetime(result[0], result[1], result[2],
                          int(result[3]), int((result[3] % 1) * 60))

        sunrise = jd_to_datetime(rise_result[1][0]) if rise_result[0] >= 0 else None
        sunset = jd_to_datetime(set_result[1][0]) if set_result[0] >= 0 else None

        # Calculate Brahma Muhurta (96 minutes before sunrise - most auspicious time)
        brahma_muhurta = sunrise - timedelta(minutes=96) if sunrise else None

        # Calculate noon (peak solar energy)
        if sunrise and sunset:
            noon = sunrise + (sunset - sunrise) / 2
        else:
            noon = None

        # Moon rise and set
        moon_rise_result = swe.rise_trans(jd, swe.MOON, lon, lat, rsmi=swe.CALC_RISE)
        moon_set_result = swe.rise_trans(jd, swe.MOON, lon, lat, rsmi=swe.CALC_SET)

        moon_rise = jd_to_datetime(moon_rise_result[1][0]) if moon_rise_result[0] >= 0 else None
        moon_set = jd_to_datetime(moon_set_result[1][0]) if moon_set_result[0] >= 0 else None

        return {
            'sunrise': sunrise,
            'sunset': sunset,
            'noon': noon,
            'brahma_muhurta': brahma_muhurta,
            'moon_rise': moon_rise,
            'moon_set': moon_set,
            'location': {'latitude': lat, 'longitude': lon}
        }

    def get_current_energetics(self, dt: datetime = None, location: Tuple[float, float] = None) -> Dict:
        """
        Comprehensive reading of current astrological energetics
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)

        result = {
            'datetime': dt.isoformat(),
            'moon_phase': self.get_moon_phase(dt),
            'lunar_mansion': self.get_lunar_mansion(dt),
            'planetary_positions': self.get_planetary_positions(dt, location)
        }

        if location:
            result['auspicious_times'] = self.calculate_auspicious_times(dt, location)

        return result

    def recommend_frequencies_for_time(self, dt: datetime = None) -> List[float]:
        """
        Recommend frequencies based on astrological conditions
        """
        if dt is None:
            dt = datetime.now(pytz.UTC)

        frequencies = []

        # Get moon phase
        moon_phase = self.get_moon_phase(dt)

        # Base frequencies always included
        frequencies.extend([7.83, 136.1])  # Schumann + OM

        # Moon phase specific
        if moon_phase['is_full_moon']:
            frequencies.extend([210.42, 639])  # Moon frequency + connection
        elif moon_phase['is_new_moon']:
            frequencies.extend([396, 417])  # Release + new beginnings
        else:
            frequencies.append(528)  # Transformation

        # Get planetary positions
        positions = self.get_planetary_positions(dt)

        # Add planetary frequencies based on strong positions
        # Venus in prominent position - add love frequency
        if positions['venus']['degree'] < 5 or positions['venus']['degree'] > 25:
            frequencies.append(221.23)  # Venus frequency

        # Jupiter - add wisdom/expansion
        if positions['jupiter']['degree'] < 5 or positions['jupiter']['degree'] > 25:
            frequencies.append(183.58)  # Jupiter frequency

        return frequencies[:7]  # Return up to 7 frequencies

    def get_dharma_calendar_events(self, dt: datetime) -> List[str]:
        """
        Check for significant dharma calendar dates
        """
        events = []

        moon_phase = self.get_moon_phase(dt)

        # Full moon and new moon are important practice days
        if moon_phase['is_full_moon']:
            events.append("Full Moon - Auspicious for completion and dedication")

        if moon_phase['is_new_moon']:
            events.append("New Moon - Auspicious for new intentions and beginnings")

        # Check for eclipses (simplified - within 5 degrees of node)
        positions = self.get_planetary_positions(dt)
        sun_long = positions['sun']['longitude']
        moon_long = positions['moon']['longitude']
        node_long = positions['north_node']['longitude']

        # Check if sun or moon near nodes (eclipse possible)
        if abs(sun_long - node_long) < 10 or abs(sun_long - node_long - 180) < 10:
            events.append("Near Eclipse Point - Powerful for transformation")

        return events


def format_astrological_report(data: Dict) -> str:
    """
    Format astrological data into readable report
    """
    report = []
    report.append("=" * 60)
    report.append("ASTROLOGICAL TIMING REPORT")
    report.append("=" * 60)
    report.append(f"\nTime: {data['datetime']}")

    # Moon phase
    moon = data['moon_phase']
    report.append(f"\nMoon Phase: {moon['phase_name']}")
    report.append(f"Illumination: {moon['illumination']:.1f}%")

    # Lunar mansion
    nakshatra = data['lunar_mansion']
    report.append(f"\nLunar Mansion: {nakshatra['name']} (#{nakshatra['number']})")

    # Auspicious times
    if 'auspicious_times' in data:
        times = data['auspicious_times']
        report.append(f"\nAuspicious Times:")
        if times['brahma_muhurta']:
            report.append(f"  Brahma Muhurta: {times['brahma_muhurta'].strftime('%I:%M %p')}")
        if times['sunrise']:
            report.append(f"  Sunrise: {times['sunrise'].strftime('%I:%M %p')}")
        if times['noon']:
            report.append(f"  Solar Noon: {times['noon'].strftime('%I:%M %p')}")
        if times['sunset']:
            report.append(f"  Sunset: {times['sunset'].strftime('%I:%M %p')}")

    # Key planetary positions
    report.append(f"\nKey Planetary Positions:")
    for planet in ['sun', 'moon', 'venus', 'jupiter']:
        pos = data['planetary_positions'][planet]
        report.append(f"  {planet.title()}: {pos['formatted']}")

    report.append("=" * 60)

    return "\n".join(report)


if __name__ == "__main__":
    # Test the astrology module
    astro = AstrologicalCalculator()

    # Example: San Francisco coordinates
    sf_location = (37.7749, -122.4194)

    print("Testing Astrology Module")
    print("=" * 60)

    # Get current energetics
    now = datetime.now(pytz.UTC)
    data = astro.get_current_energetics(now, sf_location)

    # Print formatted report
    print(format_astrological_report(data))

    # Recommended frequencies
    print("\nRecommended Frequencies for Current Time:")
    freqs = astro.recommend_frequencies_for_time(now)
    for freq in freqs:
        print(f"  {freq} Hz")

    # Calendar events
    print("\nDharma Calendar Events:")
    events = astro.get_dharma_calendar_events(now)
    for event in events:
        print(f"  • {event}")

    print("\n✓ Astrology module test complete")
