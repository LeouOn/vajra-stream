"""
Astrology API endpoints for Vajra.Stream
"""

import asyncio
import datetime
import json
import logging
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_path():
    """Resolve the SQLite database path.

    Delegates to ``core.schema.get_db_path`` so that this endpoint and
    :func:`core.schema.init_db` operate on the *same* DB file. Previously
    this function walked up 5 parents from the endpoint file, landing
    inside ``backend/`` and creating a *second* ``vajra_stream.db`` that
    lacked every table defined in the centralized schema — leading to
    ``no such table: saved_natal_charts`` errors on fresh checkouts.
    """
    from core.schema import get_db_path as _core_get_db_path

    return _core_get_db_path()


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
        "opposition": "Polarization and relationship awareness. Conflict or balance needed.",
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
            transits.append(
                {
                    "planet": asp["planet1"].title(),
                    "type": asp["aspect"].lower(),
                    "aspecting_planet": asp["planet2"].title(),
                    "orb": round(
                        abs(
                            asp["angle"]
                            - {"Conjunction": 0, "Sextile": 60, "Square": 90, "Trine": 120, "Opposition": 180}.get(
                                asp["aspect"], 0
                            )
                        ),
                        2,
                    ),
                    "influence": _get_aspect_influence(asp["planet1"], asp["planet2"], asp["aspect"]),
                }
            )

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
    current_time_iso: str | None = None


@router.post("/daily-horoscope")
async def generate_daily_horoscope(req: TransitRequest):
    """Generate a daily transit horoscope compared against natal chart"""
    from backend.core.services.astrology_chart_service import astrology_chart_service

    result = astrology_chart_service.get_daily_transit(
        req.name, req.birth_time_iso, req.birth_city, req.current_time_iso
    )
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

    result = astrology_chart_service.get_synastry(
        req.name_a, req.time_a, req.city_a, req.name_b, req.time_b, req.city_b
    )
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
    description: str | None = ""
    tags: str | None = ""
    notes: str | None = ""


class SavedChartCreate(BaseModel):
    name: str
    birth_time_iso: str
    city: str
    description: str | None = ""
    tags: str | None = ""
    notes: str | None = ""
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None


class SavedChartResponse(SavedChartBase):
    id: int
    cached_chart_data: str | None = None
    created_at: str
    updated_at: str


class RecalculateRequest(BaseModel):
    pass


class TransitToNatalRequest(BaseModel):
    transit_time_iso: str | None = None


class SavedChartsImportRequest(BaseModel):
    charts: list[SavedChartBase]


class SavedChartsCompareRequest(BaseModel):
    chart_id_a: int
    chart_id_b: int


@router.get("/charts", response_model=list[SavedChartResponse])
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
        cursor.execute(
            "SELECT name, birth_time_iso, latitude, longitude, timezone, city, description, tags, notes, cached_chart_data FROM saved_natal_charts"
        )
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
            "charts": charts_list,
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
        import pytz
        from dateutil import parser

        from core.astrology import AstrologicalCalculator

        calc = AstrologicalCalculator()
        dt = parser.parse(chart.birth_time_iso)
        if dt.tzinfo is None:
            dt = pytz.timezone(tz).localize(dt)
        chart_data = calc.get_comprehensive_astrology(dt, (lat, lon))
        cached_data = json.dumps(chart_data)

        now_str = datetime.datetime.now().isoformat()

        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO saved_natal_charts
            (name, birth_time_iso, latitude, longitude, timezone, city, description, tags, notes, cached_chart_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                chart.name,
                chart.birth_time_iso,
                lat,
                lon,
                tz,
                chart.city,
                chart.description,
                chart.tags,
                chart.notes,
                cached_data,
                now_str,
                now_str,
            ),
        )
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
            "updated_at": now_str,
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
        import pytz
        from dateutil import parser

        from core.astrology import AstrologicalCalculator

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

        cursor.execute(
            """
            UPDATE saved_natal_charts
            SET name = ?, birth_time_iso = ?, latitude = ?, longitude = ?, timezone = ?, city = ?, description = ?, tags = ?, notes = ?, cached_chart_data = ?, updated_at = ?
            WHERE id = ?
        """,
            (
                chart.name,
                chart.birth_time_iso,
                lat,
                lon,
                tz,
                chart.city,
                chart.description,
                chart.tags,
                chart.notes,
                cached_data,
                now_str,
                chart_id,
            ),
        )

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
            "updated_at": now_str,
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
        import pytz
        from dateutil import parser

        from core.astrology import AstrologicalCalculator

        calc = AstrologicalCalculator()
        dt = parser.parse(chart["birth_time_iso"])
        if dt.tzinfo is None:
            dt = pytz.timezone(chart["timezone"]).localize(dt)

        chart_data = calc.get_comprehensive_astrology(dt, (chart["latitude"], chart["longitude"]))
        cached_data = json.dumps(chart_data)

        now_str = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            UPDATE saved_natal_charts
            SET cached_chart_data = ?, updated_at = ?
            WHERE id = ?
        """,
            (cached_data, now_str, chart_id),
        )

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

        import datetime as dt_mod

        import pytz
        from dateutil import parser

        from core.astrology import AstrologicalCalculator

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
                "bazi_clashes": bazi_transits,
            },
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

        import pytz
        from dateutil import parser

        from core.astrology import AstrologicalCalculator

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
            chart_a["name"],
            chart_a["birth_time_iso"],
            chart_a["city"],
            chart_b["name"],
            chart_b["birth_time_iso"],
            chart_b["city"],
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
                ("Water", "Water"): "Extreme emotional resonance, highly intuitive bond.",
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
                "element_b": elem_b,
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
                    import pytz
                    from dateutil import parser

                    from core.astrology import AstrologicalCalculator

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
                cursor.execute(
                    """
                    UPDATE saved_natal_charts
                    SET birth_time_iso = ?, latitude = ?, longitude = ?, timezone = ?, description = ?, tags = ?, notes = ?, cached_chart_data = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (birth_time_iso, lat, lon, tz, description, tags, notes, cached_data, now_str, existing[0]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO saved_natal_charts
                    (name, birth_time_iso, latitude, longitude, timezone, city, description, tags, notes, cached_chart_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (name, birth_time_iso, lat, lon, tz, city, description, tags, notes, cached_data, now_str, now_str),
                )

            imported_count += 1

        conn.commit()
        conn.close()
        return {"status": "success", "imported": imported_count}
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Per-Calc Endpoints for the 8 New Astrological Systems (Task 17)
# ============================================================================
# These endpoints expose the new calculator methods (Tasks 5-12) one at a
# time. They are pure compute — no caching, no persistence, no auth. The
# batch extraction endpoint (Task 15) is responsible for persistence; the
# `AstrologicalCalculator` is reconstructed per request so requests are
# stateless and safe to call concurrently.

from typing import Literal  # noqa: E402

import pytz  # noqa: E402
from dateutil import parser as _dt_parser  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402


def _parse_dt(date_iso: str) -> datetime.datetime:
    """Parse an ISO-8601 datetime string into a tz-aware UTC datetime."""
    if not date_iso:
        raise HTTPException(status_code=422, detail="date_iso is required")
    clean = date_iso[:-1] + "+00:00" if date_iso.endswith("Z") else date_iso
    try:
        dt = datetime.datetime.fromisoformat(clean)
    except ValueError:
        try:
            dt = _dt_parser.parse(date_iso)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid date_iso: {exc}") from exc
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt


class DateLocationRequest(BaseModel):
    """Shared (date_iso, lat, lon) request body for snapshot calcs."""

    date_iso: str = Field(..., description="ISO-8601 datetime string (UTC recommended)")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees")


class LotsRequest(DateLocationRequest):
    sect: Literal["day", "night"] = Field("day", description="Day/night birth sect for Fortune/Spirit swap")


class OrbRequest(DateLocationRequest):
    orb: float = Field(1.5, gt=0.0, le=10.0, description="Conjunction orb in degrees")


class SecondaryProgressionsRequest(BaseModel):
    natal_date_iso: str
    natal_lat: float = Field(..., ge=-90.0, le=90.0)
    natal_lon: float = Field(..., ge=-180.0, le=180.0)
    target_date_iso: str


class SolarReturnRequest(BaseModel):
    natal_date_iso: str
    natal_lat: float = Field(..., ge=-90.0, le=90.0)
    natal_lon: float = Field(..., ge=-180.0, le=180.0)
    return_year: int = Field(..., ge=1900, le=2200)
    return_lat: float | None = Field(None, ge=-90.0, le=90.0)
    return_lon: float | None = Field(None, ge=-180.0, le=180.0)


class ProfectionRequest(BaseModel):
    natal_date_iso: str
    target_year: int = Field(..., ge=1900, le=2200)


class SolarArcRequest(BaseModel):
    natal_date_iso: str
    natal_lat: float = Field(..., ge=-90.0, le=90.0)
    natal_lon: float = Field(..., ge=-180.0, le=180.0)
    target_date_iso: str


class YearAheadRequest(BaseModel):
    natal_date_iso: str
    natal_lat: float = Field(..., ge=-90.0, le=90.0)
    natal_lon: float = Field(..., ge=-180.0, le=180.0)
    start_date_iso: str | None = None
    end_date_iso: str | None = None
    orb: float = Field(1.0, gt=0.0, le=10.0)


class AstrocartographyRequest(BaseModel):
    date_iso: str
    step_degrees: float = Field(5.0, gt=0.0, le=45.0)


@router.post("/lots")
async def post_lots(req: LotsRequest):
    """Hellenistic lots (Fortune, Spirit, Eros, Necessity, Courage, Victory, Nemesis)."""
    try:
        from core.astrology import AstrologicalCalculator

        dt = _parse_dt(req.date_iso)
        calc = AstrologicalCalculator()
        lots = calc.get_hellenistic_lots(dt, (req.lat, req.lon), sect=req.sect)
        return {"status": "success", "sect": req.sect, "lots": lots}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"lots endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/midpoints")
async def post_midpoints(req: OrbRequest):
    """Midpoint of every pair of 10 planets (45 midpoints)."""
    try:
        from core.astrology import AstrologicalCalculator

        dt = _parse_dt(req.date_iso)
        calc = AstrologicalCalculator()
        midpoints = calc.get_midpoints(dt, (req.lat, req.lon), orb=req.orb)
        return {"status": "success", "orb": req.orb, "count": len(midpoints), "midpoints": midpoints}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"midpoints endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/antiscia")
async def post_antiscia(req: DateLocationRequest):
    """Antiscion + contrantiscion for each of the 10 planets."""
    try:
        from core.astrology import AstrologicalCalculator

        dt = _parse_dt(req.date_iso)
        calc = AstrologicalCalculator()
        antiscia = calc.get_antiscia(dt, (req.lat, req.lon))
        return {"status": "success", "antiscia": antiscia}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"antiscia endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fixed-stars")
async def post_fixed_stars(req: OrbRequest):
    """Royal stars + Spica/Algol/Sirius with precession-adjusted longitudes."""
    try:
        from core.astrology import AstrologicalCalculator

        dt = _parse_dt(req.date_iso)
        calc = AstrologicalCalculator()
        stars = calc.get_fixed_stars(dt, (req.lat, req.lon), orb=req.orb)
        return {"status": "success", "orb": req.orb, "stars": stars}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fixed-stars endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secondary-progressions")
async def post_secondary_progressions(req: SecondaryProgressionsRequest):
    """Day-for-year secondary progressions with progressed Moon phase."""
    try:
        from core.astrology import AstrologicalCalculator

        natal_dt = _parse_dt(req.natal_date_iso)
        target_dt = _parse_dt(req.target_date_iso)
        calc = AstrologicalCalculator()
        result = calc.get_secondary_progressions(natal_dt, (req.natal_lat, req.natal_lon), target_dt)
        return {"status": "success", "progressions": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"secondary-progressions endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/solar-return")
async def post_solar_return(req: SolarReturnRequest):
    """Solar return chart for the given year at natal or relocated location."""
    try:
        from core.astrology import AstrologicalCalculator

        natal_dt = _parse_dt(req.natal_date_iso)
        return_loc = None
        if req.return_lat is not None and req.return_lon is not None:
            return_loc = (req.return_lat, req.return_lon)
        calc = AstrologicalCalculator()
        result = calc.get_solar_return(
            natal_dt,
            (req.natal_lat, req.natal_lon),
            return_year=req.return_year,
            return_location=return_loc,
        )
        return {"status": "success", "solar_return": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"solar-return endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profection")
async def post_profection(req: ProfectionRequest):
    """Annual profection: profected Asc sign + lord for the target year."""
    try:
        from core.astrology import AstrologicalCalculator

        natal_dt = _parse_dt(req.natal_date_iso)
        calc = AstrologicalCalculator()
        result = calc.get_profection(natal_dt, target_year=req.target_year)
        return {"status": "success", "profection": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"profection endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/solar-arc")
async def post_solar_arc(req: SolarArcRequest):
    """Solar arc directions: every natal body shifted by progressed Sun - natal Sun."""
    try:
        from core.astrology import AstrologicalCalculator

        natal_dt = _parse_dt(req.natal_date_iso)
        target_dt = _parse_dt(req.target_date_iso)
        calc = AstrologicalCalculator()
        result = calc.get_solar_arc_directions(natal_dt, (req.natal_lat, req.natal_lon), target_dt)
        return {"status": "success", "solar_arc": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"solar-arc endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/year-ahead")
async def post_year_ahead(req: YearAheadRequest):
    """Year-ahead transit timeline: lunations, ingresses, transits-to-natal."""
    try:
        from core.astrology import AstrologicalCalculator

        natal_dt = _parse_dt(req.natal_date_iso)
        start_dt = _parse_dt(req.start_date_iso) if req.start_date_iso else None
        end_dt = _parse_dt(req.end_date_iso) if req.end_date_iso else None
        calc = AstrologicalCalculator()
        result = calc.get_year_ahead_timeline(
            natal_dt,
            (req.natal_lat, req.natal_lon),
            start=start_dt,
            end=end_dt,
            orb=req.orb,
        )
        return {"status": "success", "year_ahead": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"year-ahead endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/astrocartography")
async def post_astrocartography(req: AstrocartographyRequest):
    """Astrocartography lines: AC/DC/MC/IC per planet (coarse, step_degrees sampling)."""
    try:
        from core.astrology import AstrologicalCalculator

        dt = _parse_dt(req.date_iso)
        calc = AstrologicalCalculator()
        result = calc.get_astrocartography_lines(dt, step_degrees=req.step_degrees)
        return {"status": "success", "step_degrees": req.step_degrees, "lines": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"astrocartography endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
