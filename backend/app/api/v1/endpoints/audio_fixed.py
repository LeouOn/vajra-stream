"""
Vajra.Stream Audio API Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sys
import os

# Add project root to path for importing services
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from backend.core.services.audio_service_fixed import audio_service
except ImportError as e:
    print(f"Warning: Could not import audio service: {e}")
    audio_service = None

router = APIRouter(prefix="/audio", tags=["audio"])

@router.post("/generate")
async def generate_audio(request: dict):
    """Generate audio based on configuration"""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not available")
        
    try:
        result = await audio_service.generate_audio(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/play")
async def play_audio(request: dict):
    """Play audio"""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not available")
        
    try:
        audio_data = request.get("audio_data", [])
        result = await audio_service.play_audio(audio_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_audio():
    """Stop audio playback"""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not available")
        
    try:
        result = await audio_service.stop_audio()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_audio_status():
    """Get current audio status"""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not available")
        
    try:
        return audio_service.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spectrum")
async def get_frequency_spectrum():
    """Get current frequency spectrum"""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not available")
        
    try:
        return audio_service.get_spectrum()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/frequencies")
async def get_active_frequencies():
    """Get currently active frequencies"""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not available")
        
    try:
        return {"frequencies": audio_service.get_active_frequencies()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))