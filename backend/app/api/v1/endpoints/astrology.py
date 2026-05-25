"""
Astrology API endpoints for Vajra.Stream
"""

import asyncio
import datetime
import logging

from fastapi import APIRouter, HTTPException

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/current")
async def get_current_astrology(datetime_str: str = None, latitude: float = None, longitude: float = None):
    """Get current astrological data or calculate for custom datetime & location"""
    try:
        logger.info(f"🌙 Astrology data request: dt={datetime_str}, lat={latitude}, lon={longitude}")

        from backend.core.services.vajra_service import vajra_service
        from datetime import datetime
        import pytz

        calc_dt = None
        if datetime_str:
            clean_dt = datetime_str
            if clean_dt.endswith('Z'):
                clean_dt = clean_dt[:-1] + '+00:00'
            try:
                calc_dt = datetime.fromisoformat(clean_dt)
            except ValueError:
                try:
                    from dateutil import parser
                    calc_dt = parser.parse(datetime_str)
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")
            
            if calc_dt and calc_dt.tzinfo is None:
                if latitude is not None and longitude is not None:
                    import datetime as dt_mod
                    offset_hours = round(longitude * 2.0 / 15.0) / 2.0
                    tz_offset = dt_mod.timezone(dt_mod.timedelta(hours=offset_hours))
                    calc_dt = calc_dt.replace(tzinfo=tz_offset)
                else:
                    calc_dt = calc_dt.replace(tzinfo=pytz.UTC)

        location = None
        if latitude is not None and longitude is not None:
            location = (latitude, longitude)

        astrology_data = await vajra_service._get_astrology_data(dt=calc_dt, location=location)

        return {"status": "success", "astrology": astrology_data, "timestamp": asyncio.get_event_loop().time()}
    except Exception as e:
        logger.error(f"❌ Current astrology data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moon-phase")
async def get_moon_phase():
    """Get current moon phase"""
    try:
        logger.info("🌙 Moon phase request")

        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
        moon_phase = astrology_data.get("moon_phase", "unknown")

        return {
            "status": "success",
            "moon_phase": moon_phase,
            "description": _get_moon_phase_description(moon_phase),
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"❌ Moon phase error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/planetary-positions")
async def get_planetary_positions():
    """Get current planetary positions"""
    try:
        logger.info("🪐 Planetary positions request")

        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
        planetary_positions = astrology_data.get("planetary_positions", {})

        return {
            "status": "success",
            "planetary_positions": planetary_positions,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"❌ Planetary positions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auspicious-times")
async def get_auspicious_times():
    """Get auspicious timing for spiritual practices"""
    try:
        logger.info("⏰ Auspicious times request")

        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
        auspicious_times = astrology_data.get("auspicious_times", [])

        return {
            "status": "success",
            "auspicious_times": auspicious_times,
            "description": "Recommended times for meditation and spiritual practices",
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"❌ Auspicious times error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/planetary-hours")
async def get_planetary_hours():
    """Get current planetary hour"""
    try:
        logger.info("🕐 Planetary hours request")
        from backend.core.services.vajra_service import vajra_service
        astrology_data = await vajra_service._get_astrology_data()
        hours_data = astrology_data.get("planetary_hours", {})
        return hours_data
    except Exception as e:
        logger.error(f"❌ Planetary hours error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/western")
async def get_western_astrology():
    """Get comprehensive Western astrology data"""
    try:
        logger.info("♈ Western astrology request")
        from backend.core.services.vajra_service import vajra_service
        astrology_data = await vajra_service._get_astrology_data()
        return {"status": "success", "western": astrology_data.get("western", {})}
    except Exception as e:
        logger.error(f"❌ Western astrology error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indian")
async def get_indian_astrology():
    """Get comprehensive Indian (Vedic) astrology/Panchang data"""
    try:
        logger.info("🕉️ Indian astrology request")
        from backend.core.services.vajra_service import vajra_service
        astrology_data = await vajra_service._get_astrology_data()
        return {"status": "success", "indian": astrology_data.get("indian", {})}
    except Exception as e:
        logger.error(f"❌ Indian astrology error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chinese")
async def get_chinese_astrology():
    """Get comprehensive Chinese astrology/BaZi data"""
    try:
        logger.info("☯️ Chinese astrology request")
        from backend.core.services.vajra_service import vajra_service
        astrology_data = await vajra_service._get_astrology_data()
        return {"status": "success", "chinese": astrology_data.get("chinese", {})}
    except Exception as e:
        logger.error(f"❌ Chinese astrology error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zodiac-positions")
async def get_zodiac_positions():
    """Get current zodiac positions"""
    try:
        logger.info("♈ Zodiac positions request")

        # Mock zodiac positions (in real implementation, would calculate from ephemeris)
        zodiac_signs = [
            "Aries",
            "Taurus",
            "Gemini",
            "Cancer",
            "Leo",
            "Virgo",
            "Libra",
            "Scorpio",
            "Sagittarius",
            "Capricorn",
            "Aquarius",
            "Pisces",
        ]

        # Simulate current positions (would use actual astronomical calculations)
        now = datetime.datetime.now()
        day_of_year = now.timetuple().tm_yday
        sun_sign_index = (day_of_year // 30) % 12
        moon_sign_index = (sun_sign_index + 3) % 12  # Moon moves faster

        positions = {
            "sun": {
                "sign": zodiac_signs[sun_sign_index],
                "degrees": (day_of_year % 30) * 12,
                "element": _get_element(zodiac_signs[sun_sign_index]),
            },
            "moon": {
                "sign": zodiac_signs[moon_sign_index],
                "degrees": ((day_of_year * 12) % 30) * 12,
                "element": _get_element(zodiac_signs[moon_sign_index]),
                "phase": "waxing",  # Would calculate actual phase
            },
            "rising_sign": zodiac_signs[(sun_sign_index + 1) % 12],
            "timestamp": asyncio.get_event_loop().time(),
        }

        return {"status": "success", "zodiac_positions": positions}
    except Exception as e:
        logger.error(f"❌ Zodiac positions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transits")
async def get_current_transits():
    """Get current planetary transits"""
    try:
        logger.info("🌍 Planetary transits request")

        # Mock transits (in real implementation, would calculate from ephemeris)
        transits = [
            {
                "planet": "Mercury",
                "type": "retrograde",
                "start_date": "2024-01-15",
                "end_date": "2024-02-05",
                "influence": "Communication challenges, technology issues",
            },
            {
                "planet": "Venus",
                "type": "trine",
                "aspecting_planet": "Jupiter",
                "orb": 3,
                "influence": "Harmonious relationships, creative inspiration",
            },
            {
                "planet": "Mars",
                "type": "square",
                "aspecting_planet": "Saturn",
                "orb": 2,
                "influence": "Frustration, need for discipline",
            },
        ]

        return {
            "status": "success",
            "transits": transits,
            "count": len(transits),
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"❌ Planetary transits error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/elements")
async def get_elemental_balance():
    """Get current elemental balance"""
    try:
        logger.info("🔥 Elemental balance request")

        # Calculate elemental balance based on planetary positions
        elements = {
            "fire": 25,  # Aries, Leo, Sagittarius
            "earth": 25,  # Taurus, Virgo, Capricorn
            "air": 25,  # Gemini, Libra, Aquarius
            "water": 25,  # Cancer, Scorpio, Pisces
        }

        # Add some variation based on current time
        now = datetime.datetime.now()
        hour_factor = now.hour / 24.0

        elements["fire"] += hour_factor * 10
        elements["water"] += (1 - hour_factor) * 10

        return {
            "status": "success",
            "elements": elements,
            "dominant_element": max(elements, key=elements.get),
            "balance": "harmonious" if max(elements.values()) - min(elements.values()) < 20 else "imbalanced",
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"❌ Elemental balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_moon_phase_description(phase: str) -> str:
    """Get description of moon phase"""
    descriptions = {
        "new": "New Moon - Time for new beginnings and setting intentions",
        "waxing": "Waxing Moon - Building energy, growth phase",
        "full": "Full Moon - Peak energy, manifestation time",
        "waning": "Waning Moon - Releasing, letting go phase",
        "unknown": "Moon phase unknown - check astronomical data",
    }
    return descriptions.get(phase, descriptions["unknown"])


def _get_planet_description(planet: str) -> str:
    """Get description of planet's influence"""
    descriptions = {
        "Sun": "Vitality, consciousness, self-expression, leadership",
        "Moon": "Emotions, intuition, nurturing, subconscious",
        "Mercury": "Communication, intellect, learning, technology",
        "Venus": "Love, beauty, harmony, creativity, relationships",
        "Mars": "Action, courage, conflict, physical energy",
        "Jupiter": "Expansion, wisdom, abundance, spirituality",
        "Saturn": "Discipline, structure, limitations, karma",
    }
    return descriptions.get(planet, "Unknown planetary influence")


def _get_element(sign: str) -> str:
    """Get element associated with zodiac sign"""
    elements = {
        "Aries": "fire",
        "Leo": "fire",
        "Sagittarius": "fire",
        "Taurus": "earth",
        "Virgo": "earth",
        "Capricorn": "earth",
        "Gemini": "air",
        "Libra": "air",
        "Aquarius": "air",
        "Cancer": "water",
        "Scorpio": "water",
        "Pisces": "water",
    }
    return elements.get(sign, "unknown")
