"""
Personal Healing API endpoints for Vajra.Stream
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chakra", tags=["chakra"])


class ChakraBalanceRequest(BaseModel):
    intention: str = "balance"
    sequence_type: str = "full"


class ChakraInfoRequest(BaseModel):
    chakra_name: str


class HealingFrequenciesRequest(BaseModel):
    chakra_name: str
    intention: str = "balance"


class HealingSequenceRequest(BaseModel):
    sequence_type: str = "full"
    duration_per: int = 60


@router.post("/balance")
async def balance_chakras(request: ChakraBalanceRequest):
    """Balance all chakras for given intention"""
    try:
        logger.info(f"Balancing chakras for intention: {request.intention}")

        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        sequence = phm.create_chakra_healing_sequence(sequence_type=request.sequence_type, duration_per=60)

        return {"status": "success", "intention": request.intention, "sequence": sequence}
    except Exception as e:
        logger.error(f"Error balancing chakras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{chakra_name}")
async def get_chakra_info(chakra_name: str):
    """Get information about a specific chakra"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        info = phm.get_chakra_info(chakra_name)

        if not info:
            raise HTTPException(status_code=404, detail=f"Chakra '{chakra_name}' not found")

        return {"status": "success", "chakra": info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chakra info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_chakras():
    """Get all chakra data"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        chakras = phm.get_all_chakras()

        return {"status": "success", "chakras": chakras}
    except Exception as e:
        logger.error(f"Error getting all chakras: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/frequencies")
async def get_healing_frequencies(request: HealingFrequenciesRequest):
    """Get healing frequencies for a chakra"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        frequencies = phm.get_healing_frequencies(chakra_name=request.chakra_name, intention=request.intention)

        return {
            "status": "success",
            "chakra": request.chakra_name,
            "intention": request.intention,
            "frequencies": frequencies,
        }
    except Exception as e:
        logger.error(f"Error getting healing frequencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sequence")
async def create_healing_sequence(request: HealingSequenceRequest):
    """Create a chakra healing sequence"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        sequence = phm.create_chakra_healing_sequence(
            sequence_type=request.sequence_type, duration_per=request.duration_per
        )

        return {"status": "success", "sequence": sequence}
    except Exception as e:
        logger.error(f"Error creating healing sequence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meridian/{meridian_name}")
async def get_meridian_info(meridian_name: str):
    """Get information about a meridian"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        info = phm.get_meridian_info(meridian_name)

        if not info:
            raise HTTPException(status_code=404, detail=f"Meridian '{meridian_name}' not found")

        return {"status": "success", "meridian": info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting meridian info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/element/{element}")
async def get_elemental_healing(element: str):
    """Get healing frequencies for an element"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        frequencies = phm.get_elemental_healing_frequencies(element)

        return {"status": "success", "element": element, "frequencies": frequencies}
    except Exception as e:
        logger.error(f"Error getting elemental healing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emotional/{emotion}")
async def get_emotional_frequencies(emotion: str):
    """Get frequencies for emotional healing"""
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()
        frequencies = phm.get_emotional_frequencies(emotion)

        return {"status": "success", "emotion": emotion, "frequencies": frequencies}
    except Exception as e:
        logger.error(f"Error getting emotional frequencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
