"""
Blessing Slideshow API Endpoints

REST API for compassionate blessing slideshow that cycles through
photographs with overlaid mantras and positive intentions.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path

from backend.core.services.blessing_slideshow_service import (
    get_blessing_slideshow_service,
    IntentionType,
    MantraType,
    IntentionSet,
    MANTRA_TEXTS
)

router = APIRouter(prefix="/blessing-slideshow", tags=["blessing-slideshow"])


# Request/Response Models
class IntentionSetRequest(BaseModel):
    """Request model for intention set"""
    primary_mantra: MantraType
    custom_mantra: Optional[str] = None
    intentions: List[IntentionType] = Field(default_factory=list)
    dedication: str = "May all beings benefit"
    repetitions_per_photo: int = Field(108, ge=1, le=10000)

    class Config:
        json_schema_extra = {
            "example": {
                "primary_mantra": "chenrezig",
                "intentions": ["love", "healing", "peace"],
                "dedication": "May all beings find peace and happiness",
                "repetitions_per_photo": 108
            }
        }


class CreateSessionRequest(BaseModel):
    """Request to create new slideshow session"""
    directory_path: str = Field(..., description="Path to directory containing photos")
    intention_set: IntentionSetRequest
    loop_mode: bool = Field(True, description="Loop back to start when reaching end")
    display_duration_ms: int = Field(2000, ge=100, le=60000, description="Display duration per photo (ms)")
    recursive: bool = Field(False, description="Scan subdirectories")
    rng_session_id: Optional[str] = Field(None, description="Optional RNG session ID for monitoring")

    class Config:
        json_schema_extra = {
            "example": {
                "directory_path": "/path/to/missing_persons_photos",
                "intention_set": {
                    "primary_mantra": "chenrezig",
                    "intentions": ["reunion", "safety", "love"],
                    "repetitions_per_photo": 108
                },
                "loop_mode": True,
                "display_duration_ms": 2000
            }
        }


class SessionResponse(BaseModel):
    """Response with session info"""
    session_id: str
    message: str
    total_photos: int


class CurrentSlideResponse(BaseModel):
    """Current slide information"""
    photo: dict
    session: dict
    overlay: dict
    progress: dict


class StatsResponse(BaseModel):
    """Session statistics"""
    session_id: str
    directory: str
    is_active: bool
    total_photos: int
    photos_blessed: int
    total_blessings_sent: int
    total_mantras_repeated: int
    session_duration: float
    average_time_per_photo: float
    intentions_used: List[str]
    mantra_used: str
    current_progress: dict
    rng_session_id: Optional[str]


class MantraInfo(BaseModel):
    """Information about a mantra"""
    type: str
    name: str
    text: str
    description: str


class IntentionInfo(BaseModel):
    """Information about an intention type"""
    type: str
    name: str
    description: str


# Endpoints

@router.post("/session/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new blessing slideshow session

    This scans a directory for photos and prepares to cycle through them
    with overlaid mantras and positive intentions.

    **Use Cases**:
    - Missing persons databases
    - Unidentified remains directories
    - Refugee/displaced persons photos
    - Hospital patient photos (with permission)
    - Memorial/remembrance collections

    **Process**:
    1. Scans directory for image files
    2. Creates blessing queue
    3. Prepares mantra and intention overlays
    4. Links with optional RNG monitoring

    **Mantras**: Sacred sounds that carry blessing power
    **Intentions**: Positive wishes directed to beings
    **Repetitions**: Each photo receives mantras repeated N times (default 108)
    """
    service = get_blessing_slideshow_service()

    # Convert request to IntentionSet
    intention_set = IntentionSet(
        primary_mantra=request.intention_set.primary_mantra,
        custom_mantra=request.intention_set.custom_mantra,
        intentions=request.intention_set.intentions,
        dedication=request.intention_set.dedication,
        repetitions_per_photo=request.intention_set.repetitions_per_photo
    )

    try:
        session_id = service.create_session(
            directory_path=request.directory_path,
            intention_set=intention_set,
            loop_mode=request.loop_mode,
            display_duration_ms=request.display_duration_ms,
            recursive=request.recursive,
            rng_session_id=request.rng_session_id
        )

        # Get photo count
        stats = service.get_session_stats(session_id)

        return SessionResponse(
            session_id=session_id,
            message="Blessing slideshow session created successfully",
            total_photos=stats["total_photos"]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")


@router.get("/slide/current/{session_id}", response_model=CurrentSlideResponse)
async def get_current_slide(session_id: str):
    """
    Get current slide information

    Returns:
    - Photo details (path, filename, blessing count)
    - Session info (progress, status)
    - Overlay data (mantra text, intentions, repetitions)
    - Progress (current position, percentage)

    **Frontend should**:
    1. Display the photo
    2. Overlay mantra text (large, semi-transparent)
    3. Flash intentions rapidly (subliminal effect)
    4. Repeat mantras N times visually/mentally
    5. Track blessing completion
    """
    service = get_blessing_slideshow_service()

    slide = service.get_current_slide(session_id)

    if slide is None:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    return CurrentSlideResponse(**slide)


@router.post("/slide/advance/{session_id}")
async def advance_slide(
    session_id: str,
    record_blessing: bool = Query(True, description="Record blessing for current photo")
):
    """
    Advance to next slide

    **Call this after**:
    - Display duration has elapsed
    - Mantras have been repeated required times
    - User manually advances

    Args:
        record_blessing: Whether to count current photo as blessed

    Returns:
        Success status and new current slide info
    """
    service = get_blessing_slideshow_service()

    success = service.advance_slide(session_id, record_blessing=record_blessing)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Session not found, inactive, or reached end (non-looping)"
        )

    # Return new current slide
    slide = service.get_current_slide(session_id)

    return {
        "success": True,
        "message": "Advanced to next slide",
        "current_slide": slide
    }


@router.post("/session/{session_id}/pause")
async def pause_session(session_id: str):
    """
    Pause the slideshow session

    Stops advancement, preserves state.
    Good for taking a break or focusing longer on one photo.
    """
    service = get_blessing_slideshow_service()

    success = service.pause_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session paused", "session_id": session_id}


@router.post("/session/{session_id}/resume")
async def resume_session(session_id: str):
    """Resume a paused session"""
    service = get_blessing_slideshow_service()

    success = service.resume_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session resumed", "session_id": session_id}


@router.post("/session/{session_id}/stop", response_model=StatsResponse)
async def stop_session(session_id: str):
    """
    Stop the session and get final statistics

    Returns complete statistics:
    - Total photos blessed
    - Total mantras repeated
    - Session duration
    - Average time per photo
    """
    service = get_blessing_slideshow_service()

    stats = service.stop_session(session_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")

    return StatsResponse(**stats)


@router.get("/session/{session_id}/stats", response_model=StatsResponse)
async def get_session_stats(session_id: str):
    """
    Get current session statistics

    Can be called while session is active to monitor progress.
    """
    service = get_blessing_slideshow_service()

    stats = service.get_session_stats(session_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")

    return StatsResponse(**stats)


@router.get("/session/{session_id}/photos")
async def get_photo_list(session_id: str):
    """
    Get list of all photos in session

    Includes blessing count for each photo.
    Useful for tracking which beings have received more blessings.
    """
    service = get_blessing_slideshow_service()

    photos = service.get_photo_list(session_id)

    if photos is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "photos": photos,
        "total": len(photos)
    }


@router.post("/session/{session_id}/jump/{index}")
async def jump_to_photo(session_id: str, index: int):
    """
    Jump to specific photo by index

    Useful for:
    - Returning to a specific being
    - Sending extra blessings to one person
    - Manual navigation
    """
    service = get_blessing_slideshow_service()

    success = service.jump_to_photo(session_id, index)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid index or session not found"
        )

    # Return new current slide
    slide = service.get_current_slide(session_id)

    return {
        "success": True,
        "message": f"Jumped to photo {index}",
        "current_slide": slide
    }


@router.get("/sessions")
async def get_all_sessions():
    """Get list of all session IDs"""
    service = get_blessing_slideshow_service()
    return {
        "sessions": service.get_all_sessions(),
        "total": len(service.get_all_sessions())
    }


@router.get("/photo/{session_id}/{index}")
async def serve_photo(session_id: str, index: int):
    """
    Serve a specific photo from a session

    Returns the actual image file for display.
    """
    service = get_blessing_slideshow_service()

    photos = service.get_photo_list(session_id)

    if not photos or index < 0 or index >= len(photos):
        raise HTTPException(status_code=404, detail="Photo not found")

    photo_path = photos[index]["file_path"]

    if not Path(photo_path).exists():
        raise HTTPException(status_code=404, detail="Photo file not found on disk")

    return FileResponse(photo_path)


@router.get("/info/mantras", response_model=List[MantraInfo])
async def get_mantras_info():
    """
    Get information about all available mantras

    Returns descriptions and texts for each mantra type.
    """
    mantra_descriptions = {
        MantraType.CHENREZIG: "Om Mani Padme Hum - Chenrezig (Avalokiteshvara) mantra of compassion. Most universal blessing.",
        MantraType.MEDICINE_BUDDHA: "Medicine Buddha mantra - For healing physical and mental illness.",
        MantraType.TARA: "Green Tara mantra - Swift action, protection, removing obstacles.",
        MantraType.VAJRASATTVA: "Vajrasattva mantra - Purification of negativity and karma.",
        MantraType.AMITABHA: "Amitabha mantra - Peaceful passing, liberation, Pure Land.",
        MantraType.MANJUSHRI: "Manjushri mantra - Wisdom, clarity, understanding.",
        MantraType.METTA: "Metta phrases - Loving-kindness, universal well-wishing.",
    }

    return [
        MantraInfo(
            type=mantra.value,
            name=mantra.value.replace("_", " ").title(),
            text=MANTRA_TEXTS.get(mantra, ""),
            description=mantra_descriptions.get(mantra, "")
        )
        for mantra in MantraType
        if mantra != MantraType.CUSTOM
    ]


@router.get("/info/intentions", response_model=List[IntentionInfo])
async def get_intentions_info():
    """
    Get information about all intention types

    Returns descriptions for each intention.
    """
    intention_descriptions = {
        IntentionType.LOVE: "May they be surrounded by love and feel deeply cared for",
        IntentionType.HEALING: "May they be healed in body, mind, and spirit",
        IntentionType.PEACE: "May they find peace, calm, and tranquility",
        IntentionType.PROTECTION: "May they be protected from all harm and danger",
        IntentionType.REUNION: "May they be reunited with their loved ones and families",
        IntentionType.IDENTIFICATION: "May they be known, recognized, and identified",
        IntentionType.LIBERATION: "May they be free from all suffering and limitation",
        IntentionType.WISDOM: "May they have clarity, understanding, and wisdom",
        IntentionType.COMPASSION: "May they receive compassion from all beings",
        IntentionType.SAFETY: "May they be safe, secure, and out of danger",
        IntentionType.COMFORT: "May they find comfort, rest, and ease",
        IntentionType.BLESSING: "May they receive blessings from all sources",
    }

    return [
        IntentionInfo(
            type=intention.value,
            name=intention.value.title(),
            description=intention_descriptions.get(intention, "")
        )
        for intention in IntentionType
    ]


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    service = get_blessing_slideshow_service()
    sessions = service.get_all_sessions()

    return {
        "status": "healthy",
        "service": "blessing_slideshow",
        "active_sessions": len(sessions)
    }
