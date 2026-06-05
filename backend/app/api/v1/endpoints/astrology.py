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

import sqlite3
import json
import os
from pathlib import Path
from backend.app.config import settings

def get_db_path():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        project_root = Path(__file__).parent.parent.parent.parent.parent
        db_path = str((project_root / db_path).resolve())
    return db_path

def init_db():
    from core.schema import init_db as _core_init_db  # noqa: WPS433

    _core_init_db()

# Initialize saved charts table
init_db()

def _get_aspect_influence(p1: str, p2: str, aspect: str) -> str:
    influences = {
        "conjunction": "Concentrated energy focus. Direct fusion of two principles.",
        "trine": "Harmonious flow of energy. Talent and opportunities open up naturally.",
        "sextile": "Supportive connections. Minor effort yields positive opportunities.",
        "square": "Tension and challenge. Friction calls for adjustments and action.",
        "opposition": "Polarization and relationship awareness. Conflict or balance needed."
    }
    return influences.get(aspect.lower(), "Astrological interaction of planetary energies.")


@router.get("/current")
async def get_current_astrology(datetime_str: str = None, latitude: float = None, longitude: float = None):
    """Get current astrological data or calculate for custom datetime & location"""
    try:
        logger.info(f"🌙 Astrology data request: dt={datetime_str}, lat={latitude}, lon={longitude}")

        from datetime import datetime

        import pytz

        from backend.core.services.vajra_service import vajra_service

        calc_dt = None
        if datetime_str:
            clean_dt = datetime_str
            if clean_dt.endswith("Z"):
                clean_dt = clean_dt[:-1] + "+00:00"
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
    """Get current zodiac positions using real calculations"""
    try:
        logger.info("♈ Zodiac positions request")
        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
        western = astrology_data.get("western", {})
        positions = western.get("positions", {})

        sun_pos = positions.get("sun", {})
        moon_pos = positions.get("moon", {})
        asc_pos = positions.get("ascendant", {})

        sun_sign = sun_pos.get("sign", "Aries")
        moon_sign = moon_pos.get("sign", "Aries")
        rising_sign = asc_pos.get("sign", "Aries")

        res_positions = {
            "sun": {
                "sign": sun_sign,
                "degrees": sun_pos.get("degree", 0.0),
                "element": _get_element(sun_sign),
            },
            "moon": {
                "sign": moon_sign,
                "degrees": moon_pos.get("degree", 0.0),
                "element": _get_element(moon_sign),
                "phase": astrology_data.get("moon_phase", {}).get("phase_name", "unknown"),
            },
            "rising_sign": rising_sign,
            "timestamp": asyncio.get_event_loop().time(),
        }

        return {"status": "success", "zodiac_positions": res_positions}
    except Exception as e:
        logger.error(f"❌ Zodiac positions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transits")
async def get_current_transits():
    """Get current planetary transits (real calculations in orb)"""
    try:
        logger.info("🌍 Planetary transits request")
        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
        western = astrology_data.get("western", {})
        aspects = western.get("aspects", [])

        transits = []
        for asp in aspects:
            transits.append({
                "planet": asp["planet1"].title(),
                "type": asp["aspect"].lower(),
                "aspecting_planet": asp["planet2"].title(),
                "orb": round(abs(asp["angle"] - {
                    "Conjunction": 0, "Sextile": 60, "Square": 90, "Trine": 120, "Opposition": 180
                }.get(asp["aspect"], 0)), 2),
                "influence": _get_aspect_influence(asp["planet1"], asp["planet2"], asp["aspect"])
            })

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
    """Get current elemental balance using real calculations"""
    try:
        logger.info("🔥 Elemental balance request")
        from backend.core.services.vajra_service import vajra_service

        astrology_data = await vajra_service._get_astrology_data()
        western = astrology_data.get("western", {})
        elements = western.get("elements", {"Fire": 25, "Earth": 25, "Air": 25, "Water": 25})

        normalized_elements = {k.lower(): v for k, v in elements.items()}
        dominant = max(normalized_elements, key=normalized_elements.get)

        val_max = max(normalized_elements.values())
        val_min = min(normalized_elements.values())
        balance = "harmonious" if val_max - val_min < 15 else "imbalanced"

        return {
            "status": "success",
            "elements": normalized_elements,
            "dominant_element": dominant,
            "balance": balance,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger.error(f"❌ Elemental balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



def _get_moon_phase_description(phase_input) -> str:
    """Get description of moon phase"""
    if isinstance(phase_input, dict):
        phase = phase_input.get("phase_name", "unknown")
    else:
        phase = phase_input
        
    phase = str(phase).lower()
    
    if "new" in phase:
        key = "new"
    elif "waxing" in phase or "first quarter" in phase:
        key = "waxing"
    elif "full" in phase:
        key = "full"
    elif "waning" in phase or "last quarter" in phase:
        key = "waning"
    else:
        key = "unknown"

    descriptions = {
        "new": "New Moon - Time for new beginnings and setting intentions",
        "waxing": "Waxing Moon - Building energy, growth phase",
        "full": "Full Moon - Peak energy, manifestation time",
        "waning": "Waning Moon - Releasing, letting go phase",
        "unknown": "Moon phase unknown - check astronomical data",
    }
    return descriptions.get(key, descriptions["unknown"])


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


# ---- New Geocoding & Charting Endpoints ----

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class GeocodeRequest(BaseModel):
    city_name: str

@router.post("/geocode")
async def geocode_city(req: GeocodeRequest):
    """Search for a city and return its lat, lon, and timezone"""
    from backend.core.services.geocoding_service import geocoding_service
    result = geocoding_service.get_coordinates_and_timezone(req.city_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

class NatalChartRequest(BaseModel):
    name: str
    birth_time_iso: str
    birth_city: str

@router.post("/natal-chart")
async def generate_natal_chart(req: NatalChartRequest):
    """Generate a natal chart and export raw JSON data"""
    from backend.core.services.astrology_chart_service import astrology_chart_service
    result = astrology_chart_service.get_natal_chart(req.name, req.birth_time_iso, req.birth_city)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

class TransitRequest(BaseModel):
    name: str
    birth_time_iso: str
    birth_city: str
    current_time_iso: Optional[str] = None

@router.post("/daily-horoscope")
async def generate_daily_horoscope(req: TransitRequest):
    """Generate a daily transit horoscope compared against natal chart"""
    from backend.core.services.astrology_chart_service import astrology_chart_service
    result = astrology_chart_service.get_daily_transit(req.name, req.birth_time_iso, req.birth_city, req.current_time_iso)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

class SynastryRequest(BaseModel):
    name_a: str
    time_a: str
    city_a: str
    name_b: str
    time_b: str
    city_b: str

@router.post("/synastry")
async def generate_synastry(req: SynastryRequest):
    """Generate synastry (compatibility) aspects between two charts"""
    from backend.core.services.astrology_chart_service import astrology_chart_service
    result = astrology_chart_service.get_synastry(req.name_a, req.time_a, req.city_a, req.name_b, req.time_b, req.city_b)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


class SavedChartBase(BaseModel):
    name: str
    birth_time_iso: str
    latitude: float
    longitude: float
    timezone: str
    city: str
    description: Optional[str] = ""
    tags: Optional[str] = ""
    notes: Optional[str] = ""

class SavedChartCreate(BaseModel):
    name: str
    birth_time_iso: str
    city: str
    description: Optional[str] = ""
    tags: Optional[str] = ""
    notes: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None

class SavedChartResponse(SavedChartBase):
    id: int
    cached_chart_data: Optional[str] = None
    created_at: str
    updated_at: str

class RecalculateRequest(BaseModel):
    pass

class TransitToNatalRequest(BaseModel):
    transit_time_iso: Optional[str] = None

class SavedChartsImportRequest(BaseModel):
    charts: List[SavedChartBase]

class SavedChartsCompareRequest(BaseModel):
    chart_id_a: int
    chart_id_b: int


@router.get("/charts", response_model=List[SavedChartResponse])
async def list_saved_charts():
    """List all saved charts"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_natal_charts ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error listing charts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/export")
async def export_saved_charts():
    """Export all charts as JSON with versioning and cached data"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name, birth_time_iso, latitude, longitude, timezone, city, description, tags, notes, cached_chart_data FROM saved_natal_charts")
        rows = cursor.fetchall()
        conn.close()
        
        charts_list = []
        for row in rows:
            d = dict(row)
            if d.get("cached_chart_data"):
                try:
                    d["cached_data"] = json.loads(d["cached_chart_data"])
                except Exception:
                    d["cached_data"] = None
            d.pop("cached_chart_data", None)
            charts_list.append(d)
            
        import datetime as dt_mod
        return {
            "version": "2.0",
            "exported_at": dt_mod.datetime.now().isoformat(),
            "system": "vajra-stream-astrology",
            "charts": charts_list
        }
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/{chart_id}", response_model=SavedChartResponse)
async def get_saved_chart(chart_id: int):
    """Get a specific saved chart"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_natal_charts WHERE id = ?", (chart_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Chart not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts", response_model=SavedChartResponse)
async def create_saved_chart(chart: SavedChartCreate):
    """Save a new chart, geocoding if coordinates are omitted"""
    try:
        lat = chart.latitude
        lon = chart.longitude
        tz = chart.timezone

        # Geocode if not fully provided (preserve original city name)
        if lat is None or lon is None or tz is None:
            from backend.core.services.geocoding_service import geocoding_service
            geo = geocoding_service.get_coordinates_and_timezone(chart.city)
            if "error" in geo:
                raise HTTPException(status_code=400, detail=f"Geocoding failed for {chart.city}: {geo['error']}")
            lat = geo["latitude"]
            lon = geo["longitude"]
            tz = geo["timezone"]

        # Pre-calculate and cache chart data
        from core.astrology import AstrologicalCalculator
        import pytz
        from dateutil import parser
        
        calc = AstrologicalCalculator()
        dt = parser.parse(chart.birth_time_iso)
        if dt.tzinfo is None:
            dt = pytz.timezone(tz).localize(dt)
        chart_data = calc.get_comprehensive_astrology(dt, (lat, lon))
        cached_data = json.dumps(chart_data)

        now_str = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO saved_natal_charts 
            (name, birth_time_iso, latitude, longitude, timezone, city, description, tags, notes, cached_chart_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (chart.name, chart.birth_time_iso, lat, lon, tz, chart.city, chart.description, chart.tags, chart.notes, cached_data, now_str, now_str))
        chart_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": chart_id,
            "name": chart.name,
            "birth_time_iso": chart.birth_time_iso,
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "city": chart.city,
            "description": chart.description,
            "tags": chart.tags,
            "notes": chart.notes,
            "cached_chart_data": cached_data,
            "created_at": now_str,
            "updated_at": now_str
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/charts/{chart_id}", response_model=SavedChartResponse)
async def update_saved_chart(chart_id: int, chart: SavedChartCreate):
    """Update details of an existing chart and recalculate cache"""
    try:
        lat = chart.latitude
        lon = chart.longitude
        tz = chart.timezone

        # Geocode if not fully provided (preserve original city name)
        if lat is None or lon is None or tz is None:
            from backend.core.services.geocoding_service import geocoding_service
            geo = geocoding_service.get_coordinates_and_timezone(chart.city)
            if "error" in geo:
                raise HTTPException(status_code=400, detail=f"Geocoding failed for {chart.city}: {geo['error']}")
            lat = geo["latitude"]
            lon = geo["longitude"]
            tz = geo["timezone"]

        # Pre-calculate and cache chart data
        from core.astrology import AstrologicalCalculator
        import pytz
        from dateutil import parser
        
        calc = AstrologicalCalculator()
        dt = parser.parse(chart.birth_time_iso)
        if dt.tzinfo is None:
            dt = pytz.timezone(tz).localize(dt)
        chart_data = calc.get_comprehensive_astrology(dt, (lat, lon))
        cached_data = json.dumps(chart_data)

        now_str = datetime.datetime.now().isoformat()
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # Verify it exists
        cursor.execute("SELECT created_at FROM saved_natal_charts WHERE id = ?", (chart_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Chart not found")
        created_at = row[0]

        cursor.execute("""
            UPDATE saved_natal_charts 
            SET name = ?, birth_time_iso = ?, latitude = ?, longitude = ?, timezone = ?, city = ?, description = ?, tags = ?, notes = ?, cached_chart_data = ?, updated_at = ?
            WHERE id = ?
        """, (chart.name, chart.birth_time_iso, lat, lon, tz, chart.city, chart.description, chart.tags, chart.notes, cached_data, now_str, chart_id))
        
        conn.commit()
        conn.close()

        return {
            "id": chart_id,
            "name": chart.name,
            "birth_time_iso": chart.birth_time_iso,
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "city": chart.city,
            "description": chart.description,
            "tags": chart.tags,
            "notes": chart.notes,
            "cached_chart_data": cached_data,
            "created_at": created_at,
            "updated_at": now_str
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/charts/{chart_id}")
async def delete_saved_chart(chart_id: int):
    """Delete a saved chart"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_natal_charts WHERE id = ?", (chart_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Chart {chart_id} deleted."}
    except Exception as e:
        logger.error(f"Error deleting chart: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/{chart_id}/recalculate")
async def recalculate_chart(chart_id: int):
    """Re-run calculations and update cache"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_natal_charts WHERE id = ?", (chart_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Chart not found")
        
        chart = dict(row)
        from core.astrology import AstrologicalCalculator
        import pytz
        from dateutil import parser
        
        calc = AstrologicalCalculator()
        dt = parser.parse(chart["birth_time_iso"])
        if dt.tzinfo is None:
            dt = pytz.timezone(chart["timezone"]).localize(dt)
        
        chart_data = calc.get_comprehensive_astrology(dt, (chart["latitude"], chart["longitude"]))
        cached_data = json.dumps(chart_data)
        
        now_str = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE saved_natal_charts
            SET cached_chart_data = ?, updated_at = ?
            WHERE id = ?
        """, (cached_data, now_str, chart_id))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "cached_chart_data": chart_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recalculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/{chart_id}/transits")
async def get_chart_transits(chart_id: int, req: TransitToNatalRequest):
    """Full transit-to-natal aspects, Vedic Gochara, and Chinese BaZi clashes"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_natal_charts WHERE id = ?", (chart_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Chart not found")
            
        chart = dict(row)
        
        from core.astrology import AstrologicalCalculator
        import pytz
        from dateutil import parser
        import datetime as dt_mod
        
        calc = AstrologicalCalculator()
        
        # Parse birth date
        birth_dt = parser.parse(chart["birth_time_iso"])
        if birth_dt.tzinfo is None:
            birth_dt = pytz.timezone(chart["timezone"]).localize(birth_dt)
            
        # Parse transit date
        if req.transit_time_iso:
            transit_dt = parser.parse(req.transit_time_iso)
            if transit_dt.tzinfo is None:
                transit_dt = pytz.timezone(chart["timezone"]).localize(transit_dt)
        else:
            transit_dt = dt_mod.datetime.now(pytz.timezone(chart["timezone"]))
            
        # 1. Western Transit aspects
        western_aspects = calc.get_transits_to_natal(birth_dt, (chart["latitude"], chart["longitude"]), transit_dt)
        
        # 2. Vedic Gochara
        gochara = calc.get_vedic_gochara(birth_dt, (chart["latitude"], chart["longitude"]), transit_dt)
        
        # 3. Chinese BaZi Day Pillar clash
        bazi_transits = calc.compare_bazi_transits(birth_dt, transit_dt)
        
        return {
            "status": "success",
            "data": {
                "name": chart["name"],
                "birth_time_iso": chart["birth_time_iso"],
                "transit_time": transit_dt.isoformat(),
                "aspects": western_aspects,
                "gochara": gochara,
                "bazi_clashes": bazi_transits
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transit-to-natal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/{chart_id}/vedic-dasha")
async def get_chart_vedic_dasha(chart_id: int):
    """Vimshottari Dasha periods for the saved chart"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_natal_charts WHERE id = ?", (chart_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Chart not found")
            
        chart = dict(row)
        
        from core.astrology import AstrologicalCalculator
        import pytz
        from dateutil import parser
        
        calc = AstrologicalCalculator()
        birth_dt = parser.parse(chart["birth_time_iso"])
        if birth_dt.tzinfo is None:
            birth_dt = pytz.timezone(chart["timezone"]).localize(birth_dt)
            
        dashas = calc.calculate_vimshottari_dasha(birth_dt, (chart["latitude"], chart["longitude"]))
        return {"status": "success", "dashas": dashas}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vedic dasha calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/compare")
async def compare_saved_charts(req: SavedChartsCompareRequest):
    """Compare two saved charts for synastry (compatibility)"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Fetch Subject A
        cursor.execute("SELECT * FROM saved_natal_charts WHERE id = ?", (req.chart_id_a,))
        row_a = cursor.fetchone()
        
        # Fetch Subject B
        cursor.execute("SELECT * FROM saved_natal_charts WHERE id = ?", (req.chart_id_b,))
        row_b = cursor.fetchone()
        
        conn.close()
        
        if not row_a or not row_b:
            raise HTTPException(status_code=404, detail="One or both charts not found")
            
        chart_a = dict(row_a)
        chart_b = dict(row_b)
        
        from backend.core.services.astrology_chart_service import astrology_chart_service
        result = astrology_chart_service.get_synastry(
            chart_a["name"], chart_a["birth_time_iso"], chart_a["city"],
            chart_b["name"], chart_b["birth_time_iso"], chart_b["city"]
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        # Calculate element harmony scoring
        data_a = json.loads(chart_a["cached_chart_data"]) if chart_a.get("cached_chart_data") else None
        data_b = json.loads(chart_b["cached_chart_data"]) if chart_b.get("cached_chart_data") else None
        
        scoring = {}
        if data_a and data_b:
            elem_a = data_a.get("western", {}).get("dominant_element", "")
            elem_b = data_b.get("western", {}).get("dominant_element", "")
            
            harmony_matrix = {
                ("Fire", "Fire"): "High passion and energy alignment.",
                ("Fire", "Air"): "Excellent combination, air feeds fire's inspiration.",
                ("Fire", "Earth"): "Earth can ground fire, but may smother enthusiasm.",
                ("Fire", "Water"): "Steam relationship. Highly emotional and volatile.",
                ("Earth", "Earth"): "Very stable, practical and security-focused.",
                ("Earth", "Water"): "Nurturing combination, water makes earth fertile.",
                ("Earth", "Air"): "Highly intellectual but can lack emotional depth.",
                ("Air", "Air"): "Exceptional mental alignment, constant communication.",
                ("Air", "Water"): "Can create emotional detachment vs sensitivity friction.",
                ("Water", "Water"): "Extreme emotional resonance, highly intuitive bond."
            }
            
            pair = tuple(sorted([elem_a, elem_b]))
            harmony_desc = harmony_matrix.get(pair, "Compatibility description unavailable.")
            
            # Count aspect types
            aspects = result.get("data", {}).get("aspects", [])
            harmonious = {"trine", "sextile", "conjunction"}
            challenging = {"square", "opposition"}
            harmonies = len([a for a in aspects if a.get("aspect", "").lower() in harmonious])
            tensions = len([a for a in aspects if a.get("aspect", "").lower() in challenging])
            
            score = 50 + (harmonies * 5) - (tensions * 5)
            score = max(0, min(100, score))
            
            scoring = {
                "compatibility_score": score,
                "harmony_count": harmonies,
                "tension_count": tensions,
                "description": harmony_desc,
                "element_a": elem_a,
                "element_b": elem_b
            }
            
        result["data"]["scoring"] = scoring
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synastry comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charts/import")
async def import_saved_charts(req: dict):
    """Import charts from JSON file, merging by name/city or appending"""
    try:
        charts = req.get("charts", [])
        if not charts and isinstance(req, list):
            charts = req
            
        import datetime as dt_mod
        now_str = dt_mod.datetime.now().isoformat()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        imported_count = 0
        for chart in charts:
            name = chart.get("name")
            birth_time_iso = chart.get("birth_time_iso")
            lat = chart.get("latitude", 0.0)
            lon = chart.get("longitude", 0.0)
            tz = chart.get("timezone", "UTC")
            city = chart.get("city", "Unknown")
            description = chart.get("description", "")
            tags = ",".join(chart.get("tags", [])) if isinstance(chart.get("tags"), list) else chart.get("tags", "")
            notes = chart.get("notes", "")
            
            cached_data = None
            if "cached_data" in chart and chart["cached_data"]:
                cached_data = json.dumps(chart["cached_data"])
            elif "cached_chart_data" in chart and chart["cached_chart_data"]:
                cached_data = chart["cached_chart_data"]
                
            if not cached_data:
                try:
                    from core.astrology import AstrologicalCalculator
                    import pytz
                    from dateutil import parser
                    
                    calc = AstrologicalCalculator()
                    dt = parser.parse(birth_time_iso)
                    if dt.tzinfo is None:
                        dt = pytz.timezone(tz).localize(dt)
                    chart_data = calc.get_comprehensive_astrology(dt, (lat, lon))
                    cached_data = json.dumps(chart_data)
                except Exception:
                    pass

            cursor.execute("SELECT id FROM saved_natal_charts WHERE name = ? AND city = ?", (name, city))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE saved_natal_charts
                    SET birth_time_iso = ?, latitude = ?, longitude = ?, timezone = ?, description = ?, tags = ?, notes = ?, cached_chart_data = ?, updated_at = ?
                    WHERE id = ?
                """, (birth_time_iso, lat, lon, tz, description, tags, notes, cached_data, now_str, existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO saved_natal_charts
                    (name, birth_time_iso, latitude, longitude, timezone, city, description, tags, notes, cached_chart_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, birth_time_iso, lat, lon, tz, city, description, tags, notes, cached_data, now_str, now_str))
                
            imported_count += 1
            
        conn.commit()
        conn.close()
        return {"status": "success", "imported": imported_count}
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

