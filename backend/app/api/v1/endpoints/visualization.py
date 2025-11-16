"""
Visualization API Endpoints
Web-based visualizations for browser viewing
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))

from container import container

router = APIRouter()


class VisualizationRequest(BaseModel):
    """Request model for visualization generation"""
    width: int = 1200
    height: int = 1200
    output_format: str = "png"


class RothkoRequest(BaseModel):
    """Request for Rothko art generation"""
    width: int = 1920
    height: int = 1080
    colors: Optional[List[str]] = None


class GeometryRequest(BaseModel):
    """Request for sacred geometry"""
    geometry_type: str = "flower_of_life"
    size: int = 800
    color: tuple = (255, 215, 0)


@router.get("/chakras")
async def visualize_chakras(width: int = 1200, height: int = 1600):
    """Generate and serve chakra visualization"""
    try:
        output_path = "/tmp/vajra_chakras_web.png"
        result_path = container.anatomy.visualize_chakras(width, height, output_path)

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=chakras.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate chakra visualization")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chakra visualization: {str(e)}")


@router.get("/meridians")
async def visualize_meridians(width: int = 1200, height: int = 1600):
    """Generate and serve meridian visualization"""
    try:
        output_path = "/tmp/vajra_meridians_web.png"
        result_path = container.anatomy.visualize_meridians(width, height, output_path)

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=meridians.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate meridian visualization")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating meridian visualization: {str(e)}")


@router.post("/rothko")
async def generate_rothko(request: RothkoRequest):
    """Generate Rothko-style abstract art"""
    try:
        output_path = "/tmp/vajra_rothko_web.png"
        result_path = container.visualization.generate_rothko_art(
            width=request.width,
            height=request.height,
            colors=request.colors,
            output_path=output_path
        )

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=rothko.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Rothko art")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Rothko art: {str(e)}")


@router.get("/rothko")
async def generate_rothko_get(width: int = 1920, height: int = 1080):
    """Generate Rothko-style abstract art (GET endpoint)"""
    try:
        output_path = "/tmp/vajra_rothko_web.png"
        result_path = container.visualization.generate_rothko_art(
            width=width,
            height=height,
            output_path=output_path
        )

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=rothko.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Rothko art")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Rothko art: {str(e)}")


@router.post("/sacred-geometry")
async def generate_sacred_geometry(request: GeometryRequest):
    """Generate sacred geometry"""
    try:
        output_path = "/tmp/vajra_geometry_web.png"
        result_path = container.visualization.render_sacred_geometry(
            geometry_type=request.geometry_type,
            size=request.size,
            color=request.color,
            output_path=output_path
        )

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=sacred_geometry.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate sacred geometry")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating sacred geometry: {str(e)}")


@router.get("/sacred-geometry/{geometry_type}")
async def generate_sacred_geometry_get(geometry_type: str, size: int = 800):
    """Generate sacred geometry (GET endpoint)"""
    try:
        output_path = f"/tmp/vajra_{geometry_type}_web.png"
        result_path = container.visualization.render_sacred_geometry(
            geometry_type=geometry_type,
            size=size,
            output_path=output_path
        )

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": f"inline; filename={geometry_type}.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate sacred geometry")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating sacred geometry: {str(e)}")


@router.get("/energy-field")
async def generate_energy_field(
    width: int = 800,
    height: int = 800,
    field_type: str = "aura"
):
    """Generate energetic field visualization"""
    try:
        output_path = "/tmp/vajra_energy_field_web.png"
        result_path = container.visualization.generate_energy_field(
            width=width,
            height=height,
            field_type=field_type,
            output_path=output_path
        )

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=energy_field.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate energy field")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating energy field: {str(e)}")


@router.get("/mandala")
async def generate_mandala(
    size: int = 1000,
    intention: str = "healing"
):
    """Generate healing mandala"""
    try:
        output_path = "/tmp/vajra_mandala_web.png"
        result_path = container.visualization.create_healing_mandala(
            intention=intention,
            size=size,
            output_path=output_path
        )

        if os.path.exists(result_path):
            return FileResponse(
                result_path,
                media_type="image/png",
                headers={"Content-Disposition": "inline; filename=mandala.png"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate mandala")

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating mandala: {str(e)}")


@router.get("/geometry-types")
async def list_geometry_types():
    """List available sacred geometry types"""
    return {
        "geometry_types": container.visualization.list_geometry_types()
    }


@router.get("/status")
async def visualization_status():
    """Get visualization system status"""
    return container.visualization.get_status()
