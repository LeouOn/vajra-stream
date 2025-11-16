"""
Blessings API Endpoints for Vajra.Stream
Blessing narrative generation and compassionate blessings
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../../'))

try:
    from core.blessing_narratives import BlessingNarrativeGenerator, BlessingTarget
    from core.compassionate_blessings import CompassionateBlessingGenerator, BlessingTradition
    HAS_BLESSING_MODULES = True
except ImportError:
    HAS_BLESSING_MODULES = False
    logger = logging.getLogger(__name__)
    logger.warning("Blessing modules not available")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances
if HAS_BLESSING_MODULES:
    narrative_generator = BlessingNarrativeGenerator()
    compassionate_generator = CompassionateBlessingGenerator()

# Request Models
class BlessingNarrativeRequest(BaseModel):
    target_name: str = Field(..., description="Name of person, place, or situation")
    target_type: str = Field(default="person", description="Type: person, place, event, situation")
    intention: str = Field(..., description="Primary intention for the blessing")
    tradition: str = Field(default="universal", description="Spiritual tradition")
    length: str = Field(default="medium", description="Length: short, medium, long")
    include_dedication: bool = Field(default=True, description="Include dedication of merit")

class CompassionateBlessingRequest(BaseModel):
    recipients: List[str] = Field(..., description="List of recipients")
    intention: str = Field(..., description="Blessing intention")
    tradition: str = Field(default="buddhist", description="Tradition: buddhist, tibetan, zen, universal")
    include_mantra: bool = Field(default=True, description="Include sacred mantra")
    include_dedication: bool = Field(default=True, description="Include dedication")

class MassLiberationRequest(BaseModel):
    event_name: str = Field(..., description="Name of event (disaster, conflict, etc.)")
    location: str = Field(..., description="Location")
    estimated_souls: int = Field(default=1000, ge=1, description="Estimated number affected")
    duration_minutes: int = Field(default=108, ge=1, le=1080, description="Duration of blessing")

# Response Models
class BlessingResponse(BaseModel):
    status: str
    blessing_text: str
    tradition: str
    recipients: List[str]
    mantra: Optional[str] = None
    dedication: Optional[str] = None
    metadata: Dict[str, Any]

# Endpoints

@router.post("/generate-narrative", response_model=BlessingResponse)
async def generate_blessing_narrative(request: BlessingNarrativeRequest):
    """Generate a blessing narrative"""
    try:
        if not HAS_BLESSING_MODULES:
            raise HTTPException(status_code=501, detail="Blessing modules not available")

        logger.info(f"🙏 Generating blessing for {request.target_name}")

        # Generate blessing (placeholder - would use actual generator)
        blessing_templates = {
            "universal": f"""
May {request.target_name} be filled with loving-kindness.
May {request.target_name} be well.
May {request.target_name} be peaceful and at ease.
May {request.target_name} be happy.

May {request.intention} be fulfilled for the highest good of all.

May all beings everywhere share in these blessings.
            """,
            "buddhist": f"""
May {request.target_name} be free from suffering and the causes of suffering.
May {request.target_name} find happiness and the causes of happiness.
May {request.target_name} never be separated from the supreme bliss that is beyond all suffering.
May {request.target_name} abide in equanimity, free from attachment and aversion.

With the intention of {request.intention}, may all beings benefit.

Om Mani Padme Hum
            """,
            "tibetan": f"""
In the vast expanse of the primordial ground,
May {request.target_name} rest in the natural state.
May the luminous clarity of awareness dawn,
Dispelling the darkness of ignorance.

With the intention of {request.intention},
May all obscurations be purified,
May all positive qualities increase,
May ultimate realization be swiftly attained.

Om Ah Hum Vajra Guru Padma Siddhi Hum
            """
        }

        blessing_text = blessing_templates.get(request.tradition, blessing_templates["universal"])

        dedication = None
        if request.include_dedication:
            dedication = f"""
By this merit may {request.target_name} and all beings
Attain omniscience.
Having defeated the enemy, wrongdoing,
May all beings be liberated from the ocean of cyclic existence,
Troubled by the waves of birth, aging, sickness, and death.

May the precious mind of enlightenment
Arise where it has not yet arisen.
Where it has arisen, may it not decline,
But ever increase, higher and higher.
            """

        mantra = {
            "universal": "Om Shanti Shanti Shanti",
            "buddhist": "Om Mani Padme Hum",
            "tibetan": "Om Ah Hum Vajra Guru Padma Siddhi Hum",
            "zen": "Gate Gate Paragate Parasamgate Bodhi Svaha"
        }.get(request.tradition, "Om")

        return BlessingResponse(
            status="success",
            blessing_text=blessing_text.strip(),
            tradition=request.tradition,
            recipients=[request.target_name],
            mantra=mantra if request.include_dedication else None,
            dedication=dedication.strip() if request.include_dedication else None,
            metadata={
                "target_type": request.target_type,
                "intention": request.intention,
                "length": request.length,
                "generated_at": "2025-11-16"
            }
        )

    except Exception as e:
        logger.error(f"❌ Blessing generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compassionate", response_model=BlessingResponse)
async def generate_compassionate_blessing(request: CompassionateBlessingRequest):
    """Generate a compassionate blessing"""
    try:
        logger.info(f"💖 Generating compassionate blessing for {len(request.recipients)} recipients")

        recipients_str = ", ".join(request.recipients)

        blessing_text = f"""
May {recipients_str} be filled with loving-kindness.
May you be safe and protected.
May you be healthy and strong.
May you live with ease and in harmony.

May your hearts be filled with compassion,
Your minds with wisdom,
Your lives with joy.

May {request.intention} be realized for the benefit of all beings.

May all beings everywhere, without exception,
Experience the same boundless love, compassion, and care.
            """

        mantra = None
        if request.include_mantra:
            mantra = {
                "buddhist": "Om Mani Padme Hum",
                "tibetan": "Om Tare Tuttare Ture Soha",  # Green Tara
                "zen": "Namu Amida Butsu",
                "universal": "Om Shanti"
            }.get(request.tradition, "Om Mani Padme Hum")

        dedication = None
        if request.include_dedication:
            dedication = "By the power of this blessing, may all beings find peace, happiness, and liberation from suffering."

        return BlessingResponse(
            status="success",
            blessing_text=blessing_text.strip(),
            tradition=request.tradition,
            recipients=request.recipients,
            mantra=mantra,
            dedication=dedication,
            metadata={
                "intention": request.intention,
                "recipient_count": len(request.recipients)
            }
        )

    except Exception as e:
        logger.error(f"❌ Compassionate blessing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mass-liberation")
async def mass_liberation_blessing(request: MassLiberationRequest):
    """Special blessing for mass liberation events"""
    try:
        logger.info(f"🕊️ Mass liberation blessing: {request.event_name}, {request.estimated_souls} souls")

        blessing_text = f"""
For all those affected by {request.event_name} in {request.location},

May the {request.estimated_souls} souls find immediate peace and liberation.
May all suffering cease in this very moment.
May the light of wisdom guide each being to the highest rebirth.

May those who remain find solace, healing, and the strength to continue.
May compassion arise in all hearts.
May this tragedy become a cause for awakening.

To all beings caught in the cycle of suffering:
May you be free.
May you find peace.
May you attain the deathless state.

Namo Amitabha Buddha
Om Mani Padme Hum
Om Ah Hum

May all beings benefit from this dedication.
        """

        # Calculate recitation count for duration
        mantra_count = request.duration_minutes * 10  # ~10 mantras per minute

        return {
            "status": "success",
            "event": request.event_name,
            "location": request.location,
            "estimated_souls": request.estimated_souls,
            "blessing_text": blessing_text.strip(),
            "primary_mantra": "Namo Amitabha Buddha",
            "recommended_recitation_count": mantra_count,
            "duration_minutes": request.duration_minutes,
            "dedication": f"Dedicated to the liberation of all {request.estimated_souls} souls affected by {request.event_name}",
            "special_instruction": "Recite with deep compassion, visualizing each being finding peace and liberation"
        }

    except Exception as e:
        logger.error(f"❌ Mass liberation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traditions")
async def list_traditions():
    """List available blessing traditions"""
    return {
        "status": "success",
        "traditions": [
            {
                "id": "universal",
                "name": "Universal / Interfaith",
                "description": "Inclusive blessings suitable for all backgrounds",
                "primary_mantra": "Om Shanti"
            },
            {
                "id": "buddhist",
                "name": "Buddhist",
                "description": "Mahayana Buddhist loving-kindness blessings",
                "primary_mantra": "Om Mani Padme Hum"
            },
            {
                "id": "tibetan",
                "name": "Tibetan Buddhist",
                "description": "Vajrayana blessings with deity practices",
                "primary_mantra": "Om Ah Hum Vajra Guru Padma Siddhi Hum"
            },
            {
                "id": "zen",
                "name": "Zen Buddhist",
                "description": "Simple, direct blessings in Zen style",
                "primary_mantra": "Namu Amida Butsu"
            },
            {
                "id": "yogic",
                "name": "Yogic / Hindu",
                "description": "Vedic and yogic blessings",
                "primary_mantra": "Om Namah Shivaya"
            }
        ]
    }


@router.get("/templates")
async def list_blessing_templates():
    """List available blessing templates"""
    return {
        "status": "success",
        "templates": [
            {
                "id": "healing",
                "name": "Healing Blessing",
                "description": "For physical, emotional, or spiritual healing",
                "use_cases": ["illness", "injury", "emotional trauma"]
            },
            {
                "id": "protection",
                "name": "Protection Blessing",
                "description": "For safety and protection",
                "use_cases": ["travel", "dangerous situations", "spiritual protection"]
            },
            {
                "id": "liberation",
                "name": "Liberation Blessing",
                "description": "For those who have passed",
                "use_cases": ["death", "transition", "memorial"]
            },
            {
                "id": "compassion",
                "name": "Compassion Blessing",
                "description": "For cultivating loving-kindness",
                "use_cases": ["conflict resolution", "relationship healing", "global peace"]
            },
            {
                "id": "wisdom",
                "name": "Wisdom Blessing",
                "description": "For clarity and understanding",
                "use_cases": ["decision making", "study", "spiritual practice"]
            }
        ]
    }
