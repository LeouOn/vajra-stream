"""
Divination Suite API Endpoints (Tarot, I Ching, Geomancy)
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.services.divination_service import divination_service
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
        return {"status": "success", "cards": cards, "count": len(cards), "timestamp": asyncio.get_event_loop().time()}
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
        # Increment MOPS for divination
        mops_engine.record_event("divination", 500)

        result = divination_service.cast_geomancy()
        return {"status": "success", "chart": result, "timestamp": asyncio.get_event_loop().time()}
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


@router.get("/grimoire/search")
async def search_grimoire(query: str):
    """Search correspondences grimoire"""
    try:
        results = grimoire_service.search(query)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
