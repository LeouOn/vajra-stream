"""
Divination Suite API Endpoints (Tarot, I Ching, Geomancy)
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.services.divination_service import SPREAD_POSITIONS, divination_service
from backend.core.services.grimoire_service import grimoire_service
from backend.core.services.mops_engine import mops_engine

router = APIRouter(prefix="/divination", tags=["divination"])


class DrawTarotRequest(BaseModel):
    count: int | None = 3


class InterpretRequest(BaseModel):
    system: str = "Tarot"
    question: str
    details: dict[str, Any]


@router.post("/tarot/draw")
async def draw_tarot(payload: DrawTarotRequest):
    """Draw Tarot cards (1, 3, or 10 Celtic Cross)"""
    try:
        # Increment MOPS for divination
        mops_engine.record_event("divination", 500)

        cards = divination_service.draw_tarot(payload.count)
        return {
            "status": "success",
            "cards": cards,
            "count": len(cards),
            "spread": [dict(p) for p in SPREAD_POSITIONS.get(payload.count, [])],
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/iching/cast")
async def cast_iching():
    """Cast an I Ching hexagram (6 lines, primary + relating)"""
    try:
        # Increment MOPS for divination
        mops_engine.record_event("divination", 500)

        result = divination_service.cast_i_ching()
        return {"status": "success", "cast": result, "timestamp": asyncio.get_event_loop().time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/geomancy/shield")
async def cast_geomancy():
    """Cast a Geomantic Shield Chart projected into the 12 Houses"""
    try:
        mops_engine.record_event("divination", 500)
        result = divination_service.cast_geomancy()
        return {"status": "success", "chart": result, "timestamp": asyncio.get_event_loop().time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geomancy/elemental-balance")
async def geomancy_elemental_balance():
    """Cast a geomancy shield and compare its elemental balance with the current Western chart.
    Returns both elemental distributions and a harmony score."""
    try:
        mops_engine.record_event("divination", 500)
        result = divination_service.cast_geomancy()

        # Compute elemental balance from geomantic figures
        geo_elements = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0}
        figures = result.get("figures", {})
        for name, fig in figures.items():
            elem = fig.get("element", "")
            if elem in geo_elements:
                geo_elements[elem] += 1

        # Get Western chart elemental balance
        western_elements = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0}
        try:
            from datetime import datetime

            from backend.core.services.vajra_service import vajra_service

            astro = await vajra_service._get_astrology_data(datetime.now(), (37.7749, -122.4194))
            western_data = astro.get("western", {})
            western_elements = western_data.get("elements", {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0})
        except Exception:
            pass

        # Compare: compute harmony score (0-1) based on proportional similarity
        geo_total = sum(geo_elements.values()) or 1
        west_total = sum(western_elements.values()) or 1
        geo_pct = {k: v / geo_total for k, v in geo_elements.items()}
        west_pct = {k: v / west_total for k, v in western_elements.items()}
        harmony = 1 - sum(abs(geo_pct[k] - west_pct[k]) for k in geo_elements) / 2

        # Find the Judge figure
        judge = figures.get("Judge", {})

        return {
            "status": "success",
            "geomancy_elements": geo_elements,
            "western_elements": western_elements,
            "harmony_score": round(harmony, 3),
            "harmony_quality": "excellent"
            if harmony > 0.8
            else "good"
            if harmony > 0.6
            else "neutral"
            if harmony > 0.4
            else "discordant",
            "judge": {
                "name": judge.get("name", "Unknown"),
                "element": judge.get("element", ""),
                "ruler": judge.get("ruler", ""),
                "meaning": judge.get("meaning", ""),
            },
            "chart": result,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geomancy/astrological-shield")
async def cast_astrological_geomancy():
    """Cast a Geomantic Shield where the Mothers are seeded by real planetary aspects
    instead of random numbers. The current transit aspects determine the initial figures."""
    try:
        mops_engine.record_event("divination", 500)

        # Get current Western aspects
        aspects = []
        try:
            from datetime import datetime

            from backend.core.services.vajra_service import vajra_service

            astro = await vajra_service._get_astrology_data(datetime.now(), (37.7749, -122.4194))
            aspects = astro.get("western", {}).get("aspects", [])[:4]  # Top 4 aspects
        except Exception:
            pass

        # Map planet → its geomantic figure(s)
        PLANET_FIGURES = {
            "sun": ["Fortuna Major", "Fortuna Minor"],
            "moon": ["Via", "Populus"],
            "mercury": ["Conjunctio", "Albus"],
            "venus": ["Amissio", "Puella"],
            "mars": ["Puer", "Rubeus"],
            "jupiter": ["Acquisitio", "Laetitia"],
            "saturn": ["Tristitia", "Carcer"],
        }

        # Seed Mothers from aspects if available, otherwise fall back to random
        import secrets

        from backend.core.services.divination_service import GEOMANTIC_FIGURES

        mothers = {}
        for i in range(1, 5):
            if i <= len(aspects):
                asp = aspects[i - 1]
                # Use planet1's geomantic figure for this Mother
                p1_figures = PLANET_FIGURES.get(asp.get("planet1", ""), ["Via"])
                fig_name = p1_figures[0]
                fig_pattern = GEOMANTIC_FIGURES.get(fig_name, {}).get("pattern", [1, 1, 1, 1])
                mothers[f"Mother {i}"] = list(fig_pattern)
            else:
                mothers[f"Mother {i}"] = [secrets.randbelow(2) + 1 for _ in range(4)]

        # Compute the rest of the shield from the seeded Mothers
        daughters = {}
        for i in range(1, 5):
            daughters[f"Daughter {i}"] = [
                mothers["Mother 1"][i - 1],
                mothers["Mother 2"][i - 1],
                mothers["Mother 3"][i - 1],
                mothers["Mother 4"][i - 1],
            ]

        def add_figures(a, b):
            return [2 if (x + y) % 2 == 0 else 1 for x, y in zip(a, b)]

        nieces = {
            "Niece 1": add_figures(mothers["Mother 1"], mothers["Mother 2"]),
            "Niece 2": add_figures(mothers["Mother 3"], mothers["Mother 4"]),
            "Niece 3": add_figures(daughters["Daughter 1"], daughters["Daughter 2"]),
            "Niece 4": add_figures(daughters["Daughter 3"], daughters["Daughter 4"]),
        }
        right_witness = add_figures(nieces["Niece 1"], nieces["Niece 2"])
        left_witness = add_figures(nieces["Niece 3"], nieces["Niece 4"])
        judge = add_figures(right_witness, left_witness)

        all_figures = {}
        all_figures.update(mothers)
        all_figures.update(daughters)
        all_figures.update(nieces)
        all_figures["Right Witness"] = right_witness
        all_figures["Left Witness"] = left_witness
        all_figures["Judge"] = judge

        resolved = {}
        for name, pattern in all_figures.items():
            fig_name, details = divination_service._get_geomancy_figure_details(pattern)
            resolved[name] = {"name": fig_name, "pattern": pattern, **details}

        # House projection
        house_order = [
            "Mother 1",
            "Mother 2",
            "Mother 3",
            "Mother 4",
            "Daughter 1",
            "Daughter 2",
            "Daughter 3",
            "Daughter 4",
            "Niece 1",
            "Niece 2",
            "Niece 3",
            "Niece 4",
        ]
        houses = {i + 1: resolved.get(house_order[i], {}) for i in range(12)}

        svg = divination_service._render_geomancy_shield_svg({k: v["pattern"] for k, v in resolved.items()})

        # Elemental balance
        geo_elements = {"Fire": 0, "Water": 0, "Air": 0, "Earth": 0}
        for fig in resolved.values():
            elem = fig.get("element", "")
            if elem in geo_elements:
                geo_elements[elem] += 1

        return {
            "status": "success",
            "seeded_by_aspects": len([a for a in aspects[:4] if a]),
            "aspect_seeds": [
                f"{a.get('planet1', '?')} {a.get('aspect', '?')} {a.get('planet2', '?')}" for a in aspects[:4]
            ],
            "chart": {"figures": resolved, "houses": houses, "svg": svg},
            "geomancy_elements": geo_elements,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/geomancy/talisman")
async def generate_geomancy_talisman(intention: str = "protection and clarity", kamea: str = "saturn"):
    """Generate a geomantic talisman — a sacred SVG combining a geomantic figure
    with a planetary kamea (magic square), charged with the user's intention."""
    try:
        mops_engine.record_event("divination", 300)
        # Cast a shield to get the Judge figure
        result = divination_service.cast_geomancy()
        judge = result.get("figures", {}).get("Judge", {})
        judge_name = judge.get("name", "Via")
        judge_element = judge.get("element", "Fire")
        judge_ruler = judge.get("ruler", "Moon")

        # Planetary kameas (magic squares)
        KAMEAS = {
            "saturn": {"size": 3, "grid": [4, 9, 2, 3, 5, 7, 8, 1, 6], "color": "#334155"},
            "jupiter": {"size": 4, "grid": [4, 14, 15, 1, 9, 7, 6, 12, 5, 11, 10, 8, 16, 2, 3, 13], "color": "#3b82f6"},
            "mars": {
                "size": 5,
                "grid": [11, 24, 7, 20, 3, 4, 12, 25, 8, 16, 17, 5, 13, 21, 9, 10, 18, 1, 14, 22, 23, 6, 19, 2, 15],
                "color": "#ef4444",
            },
            "sun": {
                "size": 6,
                "grid": [
                    6,
                    32,
                    3,
                    34,
                    35,
                    1,
                    7,
                    11,
                    27,
                    28,
                    8,
                    30,
                    19,
                    14,
                    16,
                    15,
                    23,
                    24,
                    18,
                    20,
                    22,
                    21,
                    17,
                    13,
                    25,
                    29,
                    10,
                    9,
                    26,
                    12,
                    36,
                    5,
                    33,
                    4,
                    2,
                    31,
                ],
                "color": "#fbbf24",
            },
            "venus": {
                "size": 7,
                "grid": [
                    22,
                    47,
                    16,
                    41,
                    10,
                    35,
                    4,
                    5,
                    23,
                    48,
                    17,
                    42,
                    11,
                    29,
                    30,
                    6,
                    24,
                    49,
                    18,
                    36,
                    12,
                    13,
                    31,
                    7,
                    25,
                    43,
                    19,
                    37,
                    38,
                    14,
                    32,
                    1,
                    26,
                    44,
                    20,
                    21,
                    39,
                    8,
                    33,
                    2,
                    27,
                    45,
                    46,
                    15,
                    40,
                    9,
                    34,
                    3,
                    28,
                ],
                "color": "#f472b6",
            },
            "mercury": {
                "size": 8,
                "grid": [
                    8,
                    58,
                    59,
                    5,
                    4,
                    62,
                    63,
                    1,
                    49,
                    15,
                    14,
                    52,
                    53,
                    11,
                    10,
                    56,
                    41,
                    23,
                    22,
                    44,
                    45,
                    19,
                    18,
                    48,
                    32,
                    34,
                    35,
                    29,
                    28,
                    38,
                    39,
                    25,
                    40,
                    26,
                    27,
                    37,
                    36,
                    30,
                    31,
                    33,
                    17,
                    47,
                    46,
                    20,
                    21,
                    43,
                    42,
                    24,
                    9,
                    55,
                    54,
                    12,
                    13,
                    51,
                    50,
                    16,
                    64,
                    2,
                    3,
                    61,
                    60,
                    6,
                    7,
                    57,
                ],
                "color": "#a78bfa",
            },
            "moon": {
                "size": 9,
                "grid": [
                    37,
                    78,
                    29,
                    70,
                    21,
                    62,
                    13,
                    54,
                    5,
                    6,
                    38,
                    79,
                    30,
                    71,
                    22,
                    63,
                    14,
                    46,
                    47,
                    7,
                    39,
                    80,
                    31,
                    72,
                    23,
                    55,
                    15,
                    16,
                    48,
                    8,
                    40,
                    81,
                    32,
                    64,
                    24,
                    56,
                    57,
                    17,
                    49,
                    9,
                    41,
                    73,
                    33,
                    65,
                    25,
                    26,
                    58,
                    18,
                    50,
                    1,
                    42,
                    74,
                    34,
                    66,
                    67,
                    27,
                    59,
                    10,
                    51,
                    2,
                    43,
                    75,
                    35,
                    36,
                    68,
                    19,
                    60,
                    11,
                    52,
                    3,
                    44,
                    76,
                    77,
                    28,
                    69,
                    20,
                    61,
                    12,
                    53,
                    4,
                    45,
                ],
                "color": "#e2e8f0",
            },
        }

        k_data = KAMEAS.get(kamea, KAMEAS["saturn"])
        n = k_data["size"]
        grid = k_data["grid"]
        color = k_data["color"]

        # Build SVG talisman
        cell_size = 48
        padding = 60
        total = n * cell_size
        width = total + padding * 2
        height = total + padding * 2 + 80

        svg_parts = [
            f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background:#0a0a1a;border-radius:16px;">'
        ]
        svg_parts.append(
            '<defs><filter id="glow"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        )
        svg_parts.append(
            f'<text x="{width / 2}" y="30" fill="#fff" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">Geomantic Talisman</text>'
        )
        svg_parts.append(
            f'<text x="{width / 2}" y="48" fill="{color}" font-size="10" font-family="monospace" text-anchor="middle">{kamea.upper()} KAMEA · {judge_name.upper()} · {intention.upper()}</text>'
        )

        # Kamea grid
        for i, val in enumerate(grid):
            row = i // n
            col = i % n
            x = padding + col * cell_size
            y = padding + row * cell_size + 20
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="none" stroke="{color}" stroke-width="1" opacity="0.4"/>'
            )
            svg_parts.append(
                f'<text x="{x + cell_size / 2}" y="{y + cell_size / 2 + 5}" fill="{color}" font-size="12" font-family="monospace" text-anchor="middle" opacity="0.7">{val}</text>'
            )

        # Sigil trace (simple line connecting the intention letters via kamea)
        sigil_letters = [c.upper() for c in intention if c.isalpha()][:12]
        if sigil_letters:
            svg_parts.append('<polyline points="')
            for ch in sigil_letters:
                val = ord(ch) - 64
                if 1 <= val <= n * n:
                    idx = val - 1
                    row = idx // n
                    col = idx % n
                    x = padding + col * cell_size + cell_size / 2
                    y = padding + row * cell_size + cell_size / 2 + 20
                    svg_parts.append(f"{x},{y} ")
            svg_parts.append(
                '" fill="none" stroke="#ffd700" stroke-width="2" stroke-dasharray="4,3" filter="url(#glow)" opacity="0.8"/>'
            )

        # Judge figure name
        svg_parts.append(
            f'<text x="{width / 2}" y="{height - 30}" fill="{color}" font-size="12" font-family="monospace" text-anchor="middle">Figure: {judge_name} · Element: {judge_element} · Ruler: {judge_ruler}</text>'
        )
        svg_parts.append(
            f'<text x="{width / 2}" y="{height - 12}" fill="#666" font-size="9" font-family="monospace" text-anchor="middle">{judge.get("meaning", "")[:80]}</text>'
        )
        svg_parts.append("</svg>")

        return {
            "status": "success",
            "talisman_svg": "\n".join(svg_parts),
            "judge": {
                "name": judge_name,
                "element": judge_element,
                "ruler": judge_ruler,
                "meaning": judge.get("meaning", ""),
            },
            "kamea": kamea,
            "intention": intention,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interpret")
async def interpret_divination(payload: InterpretRequest):
    """Interpret divination readings using local/cloud LLM operator"""
    try:
        # Construct interpretation prompt
        prompt = (
            f"Please provide a deep, esoteric interpretation for a {payload.system} reading. "
            f"The user's question was: '{payload.question}'.\n\n"
            f"Reading details: {payload.details}\n\n"
            f"Explain the correspondences, astrological rulers, and elemental flows with compassion and wisdom."
        )

        # Route to local/cloud chat endpoint logic
        from backend.app.api.v1.endpoints.llm import ChatMessage, ChatRequest, chat_interaction

        chat_req = ChatRequest(messages=[ChatMessage(role="user", content=prompt)], provider="auto")

        response = await chat_interaction(chat_req)
        return {"status": "success", "interpretation": response.response, "timestamp": asyncio.get_event_loop().time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eighty-eight-buddhas/random")
async def random_buddha():
    """Return a random Buddha entry from the 88-Buddha collection."""
    try:
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        b = svc.random_buddha()
        return {
            "name_chinese": b.name_chinese,
            "name_pinyin": b.name_pinyin,
            "name_sanskrit": b.name_sanskrit,
            "category": b.category,
            "meaning": b.meaning,
            "realm": b.realm,
            "light": b.light,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eighty-eight-buddhas/narrative")
async def buddha_narrative(name: str = "", depth: str = "contemplation"):
    """Generate a narrative about a specific Buddha from the 88."""
    try:
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        result = svc.generate_buddha_narrative(buddha_name=name, depth=depth)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eighty-eight-buddhas/confession")
async def eighty_eight_confession(intention: str = ""):
    """Get the full 88-Buddha confession liturgy with selected Buddha narratives."""
    try:
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        result = svc.generate_repentance_narrative(intention=intention)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/eighty-eight-buddhas/recite/start")
async def start_eighty_eight_recitation(intention: str = "愿一切众生离苦得乐", interval_seconds: float = 3.0):
    """Start continuous 88-Buddha recitation loop with TTS."""
    try:
        from core.buddha_recitation_loop import get_recitation_loop

        loop = get_recitation_loop()
        await loop.start(intention=intention, interval_seconds=interval_seconds)
        return loop.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/eighty-eight-buddhas/recite/stop")
async def stop_eighty_eight_recitation():
    """Stop the 88-Buddha recitation loop."""
    try:
        from core.buddha_recitation_loop import get_recitation_loop

        loop = get_recitation_loop()
        await loop.stop()
        return loop.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eighty-eight-buddhas/recite/status")
async def eighty_eight_recitation_status():
    """Get current 88-Buddha recitation loop status."""
    try:
        from core.buddha_recitation_loop import get_recitation_loop

        loop = get_recitation_loop()
        return loop.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grimoire/search")
async def search_grimoire(query: str):
    """Search correspondences grimoire"""
    try:
        results = grimoire_service.search(query)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
