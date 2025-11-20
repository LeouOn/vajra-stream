"""
Audio API endpoints for Vajra.Stream
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class AudioConfig(BaseModel):
    frequency: float = 136.1
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05

class PlayRequest(BaseModel):
    hardware_level: int = 2

@router.post("/generate")
async def generate_audio(config: AudioConfig, background_tasks: BackgroundTasks):
    """Generate prayer bowl audio"""
    try:
        logger.info(f"🎵 Audio generation request: {config.frequency}Hz, {config.duration}s")
        
        # Import service here to avoid circular imports
        from backend.core.services.vajra_service import vajra_service
        from backend.core.services.vajra_service import AudioConfig as ServiceAudioConfig
        
        # Check current audio data state
        logger.info(f"🔍 Current audio data state: {vajra_service.current_audio_data is not None}")
        
        # Convert Pydantic model to service config
        service_config = ServiceAudioConfig(
            frequency=config.frequency,
            duration=config.duration,
            volume=config.volume,
            prayer_bowl_mode=config.prayer_bowl_mode,
            harmonic_strength=config.harmonic_strength,
            modulation_depth=config.modulation_depth
        )
        
        # Generate audio synchronously to ensure it completes before returning
        logger.info("🔄 Starting audio generation...")
        try:
            audio_data = await vajra_service.generate_prayer_bowl_audio(service_config)
            logger.info(f"✅ Audio generation completed successfully: {len(audio_data) if audio_data is not None else 0} samples")
            logger.info(f"🔍 Audio data state after generation: {vajra_service.current_audio_data is not None}")
        except Exception as e:
            logger.error(f"❌ Audio generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")
        
        return {
            "status": "success",
            "message": "Audio generation completed",
            "config": {
                "frequency": config.frequency,
                "duration": config.duration,
                "volume": config.volume,
                "prayer_bowl_mode": config.prayer_bowl_mode,
                "harmonic_strength": config.harmonic_strength,
                "modulation_depth": config.modulation_depth
            },
            "audio_generated": True,
            "samples": len(vajra_service.current_audio_data) if vajra_service.current_audio_data is not None else 0
        }
        
    except Exception as e:
        logger.error(f"❌ Audio generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/play")
async def play_audio(request: PlayRequest, background_tasks: BackgroundTasks):
    """Play current audio through hardware"""
    try:
        logger.info(f"🔊 Audio playback request: hardware level {request.hardware_level}")
        
        from backend.core.services.vajra_service import vajra_service
        
        # Check audio data state
        audio_data_exists = vajra_service.current_audio_data is not None
        logger.info(f"🔍 Audio data check - exists: {audio_data_exists}")
        
        if not audio_data_exists:
            logger.error("❌ No audio data available for playback")
            raise HTTPException(status_code=400, detail="No audio data available. Please generate audio first.")
        
        audio_length = len(vajra_service.current_audio_data) if vajra_service.current_audio_data is not None else 0
        logger.info(f"🔍 Audio data length: {audio_length} samples")
        
        # Play audio in background
        async def play_background():
            try:
                success = await vajra_service.broadcast_audio(
                    vajra_service.current_audio_data,
                    request.hardware_level
                )
                if success:
                    logger.info("✅ Audio playback completed successfully")
                else:
                    logger.error("❌ Audio playback failed")
            except Exception as e:
                logger.error(f"❌ Background audio playback failed: {e}")
        
        background_tasks.add_task(play_background)
        
        return {
            "status": "success",
            "message": "Audio playback started",
            "hardware_level": request.hardware_level,
            "audio_duration": audio_length / 44100,
            "audio_samples": audio_length
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Audio playback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_audio():
    """Stop audio playback"""
    try:
        logger.info("🛑 Audio stop request")
        
        from backend.core.services.vajra_service import vajra_service
        
        # Note: This would need to be implemented in the actual hardware interface
        # For now, we'll just log the request
        logger.info("✅ Audio stop request processed")
        
        return {
            "status": "success",
            "message": "Audio stop request processed"
        }
            
    except Exception as e:
        logger.error(f"❌ Audio stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spectrum")
async def get_audio_spectrum():
    """Get current audio spectrum"""
    try:
        from backend.core.services.vajra_service import vajra_service
        
        spectrum = vajra_service.get_audio_spectrum()
        
        return {
            "status": "success",
            "spectrum": spectrum,
            "length": len(spectrum),
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"❌ Spectrum retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_audio_status():
    """Get current audio status"""
    try:
        from backend.core.services.vajra_service import vajra_service
        
        has_audio = vajra_service.current_audio_data is not None
        audio_length = len(vajra_service.current_audio_data) / 44100 if has_audio else 0
        
        return {
            "status": "success",
            "has_audio": has_audio,
            "audio_duration": audio_length,
            "spectrum_available": len(vajra_service.get_audio_spectrum()) > 0,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"❌ Audio status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presets")
async def get_audio_presets():
    """Get available audio presets"""
    try:
        presets = {
            "om-frequency": {
                "name": "OM Frequency",
                "frequency": 136.1,
                "description": "Sacred OM frequency for meditation and spiritual practices",
                "prayer_bowl_mode": True,
                "harmonic_strength": 0.3,
                "modulation_depth": 0.05,
                "volume": 0.8
            },
            "heart-chakra": {
                "name": "Heart Chakra",
                "frequency": 528.0,
                "description": "Love frequency for heart opening and emotional healing",
                "prayer_bowl_mode": True,
                "harmonic_strength": 0.4,
                "modulation_depth": 0.1,
                "volume": 0.7
            },
            "earth-resonance": {
                "name": "Earth Resonance",
                "frequency": 7.83,
                "description": "Schumann resonance for grounding and connection to Earth",
                "prayer_bowl_mode": True,
                "harmonic_strength": 0.2,
                "modulation_depth": 0.02,
                "volume": 0.6
            },
            "pure-sine": {
                "name": "Pure Sine Wave",
                "frequency": 440.0,
                "description": "Standard tuning frequency for precise audio work",
                "prayer_bowl_mode": False,
                "harmonic_strength": 0.0,
                "modulation_depth": 0.0,
                "volume": 0.8
            }
        }
        
        return {
            "status": "success",
            "presets": presets,
            "count": len(presets)
        }
    except Exception as e:
        logger.error(f"❌ Presets retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/frequencies/range")
async def get_frequency_ranges():
    """Get recommended frequency ranges"""
    try:
        ranges = {
            "earth_resonance": {
                "name": "Earth Resonance",
                "min": 7.0,
                "max": 10.0,
                "description": "Schumann resonance frequencies"
            },
            "healing": {
                "name": "Healing Frequencies",
                "min": 100.0,
                "max": 1000.0,
                "description": "Common healing and meditation frequencies"
            },
            "solfeggio": {
                "name": "Solfeggio Frequencies",
                "frequencies": [396.0, 417.0, 444.0, 528.0, 639.0, 741.0, 852.0],
                "description": "Ancient Solfeggio scale"
            },
            "chakra": {
                "name": "Chakra Frequencies",
                "frequencies": {
                    "root": 256.0,
                    "sacral": 288.0,
                    "solar": 320.0,
                    "heart": 341.3,
                    "throat": 384.0,
                    "third_eye": 448.0,
                    "crown": 480.0
                },
                "description": "Traditional chakra tuning frequencies"
            }
        }
        
        return {
            "status": "success",
            "ranges": ranges
        }
    except Exception as e:
        logger.error(f"❌ Frequency ranges error: {e}")
        raise HTTPException(status_code=500, detail=str(e))