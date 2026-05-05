"""
Dharma Tales API endpoints for Vajra.Stream
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class TaleRequest(BaseModel):
    theme: Optional[str] = None
    tradition: Optional[str] = None
    length: str = "medium"
    use_llm: bool = True


class TeachingStoryRequest(BaseModel):
    archetype: Optional[str] = None
    challenge: Optional[str] = None
    tradition: str = "zen"
    teaching: Optional[str] = None


@router.post("/tale/generate")
async def generate_tale(request: TaleRequest):
    """Generate a dharma teaching tale"""
    try:
        logger.info(f"Generating dharma tale: theme={request.theme}, tradition={request.tradition}")

        from backend.core.orchestrator_bridge import orchestrator_bridge
        from scripts.unified_orchestrator import UnifiedOrchestrator

        if not orchestrator_bridge.initialized:
            orchestrator_bridge.initialize()

        orchestrator = orchestrator_bridge.get_orchestrator()
        if not orchestrator:
            raise HTTPException(status_code=500, detail="Orchestrator not available")

        dharma_tales = getattr(orchestrator, 'dharma_tales', None)
        if not dharma_tales:
            from core.dharma_tales import DharmaTalesGenerator
            dharma_tales = DharmaTalesGenerator(llm_integration=None)
            orchestrator.dharma_tales = dharma_tales

        tale = dharma_tales.generate_tale(
            theme=request.theme,
            tradition=request.tradition,
            length=request.length,
            use_llm=request.use_llm
        )

        return {
            "status": "success",
            "tale": tale,
            "theme": request.theme,
            "tradition": request.tradition,
            "length": request.length
        }
    except Exception as e:
        logger.error(f"Error generating tale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tale/parable")
async def generate_parable(topic: str, use_llm: bool = True):
    """Generate a teaching parable"""
    try:
        from core.dharma_tales import DharmaTalesGenerator

        dtg = DharmaTalesGenerator(llm_integration=None)
        parable = dtg.generate_parable(topic=topic, use_llm=use_llm)

        return {
            "status": "success",
            "parable": parable,
            "topic": topic
        }
    except Exception as e:
        logger.error(f"Error generating parable: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tale/themes")
async def list_themes():
    """List available tale themes"""
    try:
        from core.dharma_tales import DharmaTalesGenerator

        dtg = DharmaTalesGenerator(llm_integration=None)
        themes = dtg.list_themes()

        return {
            "status": "success",
            "themes": themes
        }
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tale/traditions")
async def list_traditions():
    """List available traditions"""
    try:
        from core.dharma_tales import DharmaTalesGenerator

        dtg = DharmaTalesGenerator(llm_integration=None)
        traditions = dtg.list_traditions()

        return {
            "status": "success",
            "traditions": traditions
        }
    except Exception as e:
        logger.error(f"Error listing traditions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teaching-story/generate")
async def generate_teaching_story(request: TeachingStoryRequest):
    """Generate a teaching story with archetype and challenge"""
    try:
        from core.dharma_tales import DharmaTalesGenerator

        dtg = DharmaTalesGenerator(llm_integration=None)
        story = dtg.generate_teaching_story(
            archetype=request.archetype,
            challenge=request.challenge,
            tradition=request.tradition,
            teaching=request.teaching
        )

        return {
            "status": "success",
            "story": story,
            "archetype": request.archetype,
            "tradition": request.tradition
        }
    except Exception as e:
        logger.error(f"Error generating teaching story: {e}")
        raise HTTPException(status_code=500, detail=str(e))