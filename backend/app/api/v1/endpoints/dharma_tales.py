"""
Dharma Tales API endpoints for Vajra.Stream
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


def _get_dharma_tales_generator():
    try:
        from backend.core.orchestrator_bridge import orchestrator_bridge

        if not orchestrator_bridge.initialized:
            orchestrator_bridge.initialize()

        orchestrator = orchestrator_bridge.get_orchestrator()
        if orchestrator:
            dharma_tales = getattr(orchestrator, "dharma_tales", None)
            if dharma_tales:
                return dharma_tales
    except Exception as e:
        logger.warning(f"Could not get dharma tales from orchestrator: {e}")

    from core.dharma_tales import DharmaTalesGenerator

    logger.info("Falling back to DharmaTalesGenerator without LLM integration")
    return DharmaTalesGenerator(llm_integration=None)


class TaleRequest(BaseModel):
    theme: str | None = None
    tradition: str | None = None
    length: str = "medium"
    use_llm: bool = True


class TeachingStoryRequest(BaseModel):
    archetype: str | None = None
    challenge: str | None = None
    tradition: str = "zen"
    teaching: str | None = None


@router.post("/tale/generate")
async def generate_tale(request: TaleRequest):
    try:
        logger.info(f"Generating dharma tale: theme={request.theme}, tradition={request.tradition}")

        dharma_tales = _get_dharma_tales_generator()

        tale = dharma_tales.generate_tale(
            theme=request.theme, tradition=request.tradition, length=request.length, use_llm=request.use_llm
        )

        return {
            "status": "success",
            "tale": tale,
            "theme": request.theme,
            "tradition": request.tradition,
            "length": request.length,
        }
    except Exception as e:
        logger.error(f"Error generating tale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tale/parable")
async def generate_parable(topic: str, use_llm: bool = True):
    try:
        dharma_tales = _get_dharma_tales_generator()
        parable = dharma_tales.generate_parable(topic=topic, use_llm=use_llm)

        return {"status": "success", "parable": parable, "topic": topic}
    except Exception as e:
        logger.error(f"Error generating parable: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tale/themes")
async def list_themes():
    try:
        dharma_tales = _get_dharma_tales_generator()
        themes = dharma_tales.list_themes()

        return {"status": "success", "themes": themes}
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tale/traditions")
async def list_traditions():
    try:
        dharma_tales = _get_dharma_tales_generator()
        traditions = dharma_tales.list_traditions()

        return {"status": "success", "traditions": traditions}
    except Exception as e:
        logger.error(f"Error listing traditions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teaching-story/generate")
async def generate_teaching_story(request: TeachingStoryRequest):
    try:
        dharma_tales = _get_dharma_tales_generator()
        story = dharma_tales.generate_teaching_story(
            archetype=request.archetype,
            challenge=request.challenge,
            tradition=request.tradition,
            teaching=request.teaching,
        )

        return {"status": "success", "story": story, "archetype": request.archetype, "tradition": request.tradition}
    except Exception as e:
        logger.error(f"Error generating teaching story: {e}")
        raise HTTPException(status_code=500, detail=str(e))
