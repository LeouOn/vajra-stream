"""
Energetic Anatomy API Endpoints for Vajra.Stream
Meridians, chakras, and energetic visualization
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import logging
import sys
import os
import base64
import io

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../../'))

from core.meridian_visualization import MeridianVisualizer, BodyPosition
from core.energetic_anatomy import EnergeticAnatomyDatabase, Tradition

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances
visualizer = MeridianVisualizer()
anatomy_db = EnergeticAnatomyDatabase()

# Request Models
class ChakraVisualizationRequest(BaseModel):
    width: int = Field(default=1200, ge=400, le=4000, description="Image width")
    height: int = Field(default=1600, ge=600, le=5000, description="Image height")
    show_labels: bool = Field(default=True, description="Show Sanskrit names")
    glow_effect: bool = Field(default=True, description="Add glow effects")
    format: str = Field(default="png", description="Output format (png, jpg)")

class MeridianVisualizationRequest(BaseModel):
    tradition: str = Field(default="taoist", description="Tradition: taoist, tibetan, yogic")
    width: int = Field(default=1200, ge=400, le=4000, description="Image width")
    height: int = Field(default=1600, ge=600, le=5000, description="Image height")
    show_flow_direction: bool = Field(default=True, description="Show energy flow arrows")
    element_colors: bool = Field(default=True, description="Use five element colors")
    format: str = Field(default="png", description="Output format (png, jpg)")

class CentralChannelRequest(BaseModel):
    width: int = Field(default=1200, ge=400, le=4000, description="Image width")
    height: int = Field(default=1800, ge=600, le=5000, description="Image height")
    show_sushumna: bool = Field(default=True, description="Show central channel (Sushumna)")
    show_ida_pingala: bool = Field(default=True, description="Show left/right channels (Ida/Pingala)")
    show_chakras: bool = Field(default=True, description="Show chakras at intersections")
    format: str = Field(default="png", description="Output format (png, jpg)")

class ImbalanceAnalysisRequest(BaseModel):
    symptoms: List[str] = Field(..., description="List of symptoms")
    tradition: str = Field(default="taoist", description="Tradition to use for analysis")

# Response Models
class VisualizationResponse(BaseModel):
    status: str
    image_data: str  # Base64 encoded
    width: int
    height: int
    format: str
    description: str

# Endpoints

@router.post("/visualize/chakras", response_model=VisualizationResponse)
async def visualize_chakras(request: ChakraVisualizationRequest):
    """Generate seven chakras visualization"""
    try:
        logger.info(f"🌈 Generating chakra visualization ({request.width}x{request.height})")

        # Create visualization
        viz = MeridianVisualizer(width=request.width, height=request.height)
        image = viz.create_seven_chakras_diagram()

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=request.format.upper())
        img_byte_arr.seek(0)

        # Encode as base64
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        return VisualizationResponse(
            status="success",
            image_data=img_base64,
            width=request.width,
            height=request.height,
            format=request.format,
            description="Seven chakras diagram with Sanskrit names and traditional colors"
        )

    except Exception as e:
        logger.error(f"❌ Chakra visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visualize/meridians", response_model=VisualizationResponse)
async def visualize_meridians(request: MeridianVisualizationRequest):
    """Generate meridian map visualization"""
    try:
        logger.info(f"🌊 Generating meridian visualization ({request.tradition})")

        # Create visualization
        viz = MeridianVisualizer(width=request.width, height=request.height)
        image = viz.create_elemental_meridian_map()

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=request.format.upper())
        img_byte_arr.seek(0)

        # Encode as base64
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        return VisualizationResponse(
            status="success",
            image_data=img_base64,
            width=request.width,
            height=request.height,
            format=request.format,
            description=f"{request.tradition.title()} meridian system with five element correspondences"
        )

    except Exception as e:
        logger.error(f"❌ Meridian visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/visualize/central-channel", response_model=VisualizationResponse)
async def visualize_central_channel(request: CentralChannelRequest):
    """Generate central channel (Sushumna, Ida, Pingala) visualization"""
    try:
        logger.info(f"⚡ Generating central channel visualization")

        # Create visualization
        viz = MeridianVisualizer(width=request.width, height=request.height)
        image = viz.create_central_channel_diagram()

        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=request.format.upper())
        img_byte_arr.seek(0)

        # Encode as base64
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        return VisualizationResponse(
            status="success",
            image_data=img_base64,
            width=request.width,
            height=request.height,
            format=request.format,
            description="Central channel (Sushumna) with Ida and Pingala nadis"
        )

    except Exception as e:
        logger.error(f"❌ Central channel visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traditions")
async def list_traditions():
    """List all energetic anatomy traditions"""
    return {
        "status": "success",
        "traditions": [
            {
                "id": "taoist",
                "name": "Taoist (Chinese Medicine)",
                "meridians": 12,
                "elements": 5,
                "description": "12 primary meridians with five element correspondences"
            },
            {
                "id": "tibetan",
                "name": "Tibetan Buddhist",
                "channels": 3,
                "chakras": 5,
                "winds": 5,
                "description": "Central, left, right channels with five chakras and five winds"
            },
            {
                "id": "yogic",
                "name": "Hindu Yogic",
                "nadis": 3,
                "chakras": 7,
                "description": "Sushumna, Ida, Pingala nadis with seven chakras"
            }
        ]
    }


@router.get("/chakras")
async def list_chakras():
    """List all chakras with properties"""
    return {
        "status": "success",
        "chakras": [
            {
                "sanskrit": "Muladhara",
                "english": "Root",
                "location": "Base of spine",
                "element": "Earth",
                "color": "Red",
                "frequency": 396,
                "qualities": ["Grounding", "Stability", "Survival"]
            },
            {
                "sanskrit": "Svadhisthana",
                "english": "Sacral",
                "location": "Lower abdomen",
                "element": "Water",
                "color": "Orange",
                "frequency": 417,
                "qualities": ["Creativity", "Sexuality", "Emotions"]
            },
            {
                "sanskrit": "Manipura",
                "english": "Solar Plexus",
                "location": "Upper abdomen",
                "element": "Fire",
                "color": "Yellow",
                "frequency": 528,
                "qualities": ["Power", "Will", "Transformation"]
            },
            {
                "sanskrit": "Anahata",
                "english": "Heart",
                "location": "Center of chest",
                "element": "Air",
                "color": "Green",
                "frequency": 639,
                "qualities": ["Love", "Compassion", "Connection"]
            },
            {
                "sanskrit": "Vishuddha",
                "english": "Throat",
                "location": "Throat",
                "element": "Ether",
                "color": "Blue",
                "frequency": 741,
                "qualities": ["Expression", "Truth", "Communication"]
            },
            {
                "sanskrit": "Ajna",
                "english": "Third Eye",
                "location": "Between eyebrows",
                "element": "Light",
                "color": "Indigo",
                "frequency": 852,
                "qualities": ["Intuition", "Insight", "Perception"]
            },
            {
                "sanskrit": "Sahasrara",
                "english": "Crown",
                "location": "Top of head",
                "element": "Consciousness",
                "color": "Violet/White",
                "frequency": 963,
                "qualities": ["Unity", "Enlightenment", "Divine Connection"]
            }
        ]
    }


@router.get("/meridians")
async def list_meridians():
    """List all meridians with properties"""
    return {
        "status": "success",
        "meridians": [
            {"name": "Lung", "element": "Metal", "yin_yang": "Yin", "hours": "3-5 AM"},
            {"name": "Large Intestine", "element": "Metal", "yin_yang": "Yang", "hours": "5-7 AM"},
            {"name": "Stomach", "element": "Earth", "yin_yang": "Yang", "hours": "7-9 AM"},
            {"name": "Spleen", "element": "Earth", "yin_yang": "Yin", "hours": "9-11 AM"},
            {"name": "Heart", "element": "Fire", "yin_yang": "Yin", "hours": "11 AM-1 PM"},
            {"name": "Small Intestine", "element": "Fire", "yin_yang": "Yang", "hours": "1-3 PM"},
            {"name": "Bladder", "element": "Water", "yin_yang": "Yang", "hours": "3-5 PM"},
            {"name": "Kidney", "element": "Water", "yin_yang": "Yin", "hours": "5-7 PM"},
            {"name": "Pericardium", "element": "Fire", "yin_yang": "Yin", "hours": "7-9 PM"},
            {"name": "Triple Warmer", "element": "Fire", "yin_yang": "Yang", "hours": "9-11 PM"},
            {"name": "Gallbladder", "element": "Wood", "yin_yang": "Yang", "hours": "11 PM-1 AM"},
            {"name": "Liver", "element": "Wood", "yin_yang": "Yin", "hours": "1-3 AM"}
        ],
        "five_elements": [
            {"name": "Wood", "season": "Spring", "organs": ["Liver", "Gallbladder"], "emotion": "Anger/Kindness"},
            {"name": "Fire", "season": "Summer", "organs": ["Heart", "Small Intestine"], "emotion": "Joy/Anxiety"},
            {"name": "Earth", "season": "Late Summer", "organs": ["Spleen", "Stomach"], "emotion": "Worry/Empathy"},
            {"name": "Metal", "season": "Autumn", "organs": ["Lung", "Large Intestine"], "emotion": "Grief/Courage"},
            {"name": "Water", "season": "Winter", "organs": ["Kidney", "Bladder"], "emotion": "Fear/Wisdom"}
        ]
    }


@router.post("/analyze-imbalance")
async def analyze_energetic_imbalance(request: ImbalanceAnalysisRequest):
    """Analyze energetic imbalances based on symptoms"""
    try:
        logger.info(f"🔍 Analyzing imbalance: {len(request.symptoms)} symptoms")

        # Simple pattern matching (in real implementation, would use more sophisticated analysis)
        recommendations = []

        if "tired" in str(request.symptoms).lower() or "fatigue" in str(request.symptoms).lower():
            recommendations.append({
                "meridian": "Kidney",
                "element": "Water",
                "suggestion": "Tonify Kidney meridian, rest 5-7 PM, practice grounding"
            })

        if "anxious" in str(request.symptoms).lower() or "worry" in str(request.symptoms).lower():
            recommendations.append({
                "chakra": "Manipura (Solar Plexus)",
                "frequency": 528,
                "suggestion": "Balance solar plexus, use 528 Hz, practice breathwork"
            })

        if "throat" in str(request.symptoms).lower() or "communication" in str(request.symptoms).lower():
            recommendations.append({
                "chakra": "Vishuddha (Throat)",
                "frequency": 741,
                "suggestion": "Activate throat chakra, use 741 Hz, practice authentic expression"
            })

        return {
            "status": "success",
            "symptoms": request.symptoms,
            "tradition": request.tradition,
            "recommendations": recommendations,
            "general_advice": "Consult with a qualified practitioner for personalized guidance"
        }

    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
