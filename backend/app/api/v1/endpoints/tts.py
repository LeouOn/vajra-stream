"""
TTS API Endpoints — voice configuration, speaker selection, and speech generation.

Exposes:
    GET  /api/v1/tts/config            — list all backends, voices, speakers, capabilities
    POST /api/v1/tts/config            — switch backend, voice, language, model
    POST /api/v1/tts/config/role       — set/clear per-project role→speaker override
    POST /api/v1/tts/speak             — generate TTS audio from text (file path)
    POST /api/v1/tts/speak-batch       — batch TTS generation
    POST /api/v1/tts/stream            — generate TTS audio and stream bytes (audio/mpeg|wav)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter()


class TTSSpeakRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=5000)
    voice: str | None = Field(default=None, description="Voice/speaker ID override (bypasses role)")
    rate: str | None = Field(default=None, description="Speech rate (Edge TTS only, e.g. '-25%')")
    language: str | None = Field(default=None, description="Language override (Qwen3-TTS only)")
    backend: str | None = Field(default=None, description="Force backend: 'edge', 'qwen', or 'auto'")
    role: str | None = Field(default=None, description="Ritual role (auto-maps to a speaker per project)")
    project_id: str | None = Field(default=None, description="Project id for per-project speaker override")


class TTSSpeakBatchRequest(BaseModel):
    texts: list[str] = Field(..., description="List of texts to speak", min_length=1, max_length=500)
    voice: str | None = Field(default=None)
    language: str | None = Field(default=None)
    role: str | None = Field(default=None)
    project_id: str | None = Field(default=None)


class TTSStreamRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=10000)
    voice: str | None = Field(default=None)
    rate: str | None = Field(default=None)
    language: str | None = Field(default=None)
    backend: str | None = Field(default=None, description="Force backend: 'edge', 'qwen', or 'auto'")
    role: str | None = Field(default=None, description="Ritual role for auto-speaker mapping")
    project_id: str | None = Field(default=None)


class TTSConfigUpdateRequest(BaseModel):
    backend: str | None = Field(default=None, description="'edge', 'qwen', or 'auto'")
    edge_voice: str | None = Field(default=None, description="Edge TTS voice ID")
    edge_rate: str | None = Field(default=None, description="Edge TTS speech rate")
    qwen_model: str | None = Field(default=None, description="Qwen3-TTS model name")
    qwen_speaker: str | None = Field(default=None, description="Qwen3-TTS speaker ID")
    qwen_language: str | None = Field(default=None, description="Qwen3-TTS language")
    role: str | None = Field(default=None, description="Default ritual role for this session")
    project_id: str | None = Field(default=None, description="Project id for per-project overrides")


class TTSRoleOverrideRequest(BaseModel):
    project_id: str = Field(..., description="Project id (use 'default' for the global default)")
    role: str = Field(..., description="Ritual role, e.g. 'buddhist_chant', 'outlook_narrative'")
    speaker: str = Field(..., description="Speaker/voice id to use for this role within the project")
    clear: bool = Field(default=False, description="If true, remove the override instead of setting it")


@router.get("/config", summary="Get TTS configuration and capabilities")
async def get_tts_config():
    """Return full TTS catalog — available backends, voices, speakers, and current config."""
    from core.tts_provider import get_tts_provider, list_project_overrides
    provider = get_tts_provider()
    payload = provider.get_available_configs()
    payload["project_overrides"] = list_project_overrides()
    return payload


@router.post("/config", summary="Update TTS configuration")
async def update_tts_config(request: TTSConfigUpdateRequest):
    """Update TTS backend, voice, model, or language settings."""
    from core.tts_provider import get_tts_provider
    provider = get_tts_provider()

    updates = request.model_dump(exclude_none=True)
    provider.set_config(**updates)

    return {
        "status": "ok",
        "active_backend": provider.active_backend.value,
        "config": provider.config.to_dict(),
        "capabilities": provider.capabilities,
    }


@router.post("/config/role", summary="Set or clear a per-project ritual-role speaker override")
async def set_role_override(request: TTSRoleOverrideRequest):
    """
    Map a ritual role (e.g. 'buddhist_chant', 'outlook_narrative') to a specific
    speaker within a project. The override wins over the global default.

    Pass clear=true to remove an override.
    """
    from core.tts_provider import (
        clear_project_speakers,
        list_project_overrides,
        set_project_speaker,
    )
    if request.clear:
        if request.project_id == "default":
            clear_project_speakers(request.project_id)
        else:
            clear_project_speakers(request.project_id)
        return {
            "status": "ok",
            "cleared": request.project_id,
            "project_overrides": list_project_overrides(),
        }
    set_project_speaker(request.project_id, request.role, request.speaker)
    return {
        "status": "ok",
        "project_id": request.project_id,
        "role": request.role,
        "speaker": request.speaker,
        "project_overrides": list_project_overrides(),
    }


@router.post("/speak", summary="Generate TTS audio from text")
async def speak_text(request: TTSSpeakRequest):
    """Generate speech and return the audio file path."""
    from core.tts_provider import get_tts_provider
    provider = get_tts_provider()

    # Temporarily switch backend if requested
    original_backend = provider.config.backend
    if request.backend:
        provider.set_backend(request.backend)

    # Temporarily set project_id on the config (cleanly, even if unchanged)
    original_project = provider.config.project_id
    if request.project_id is not None:
        provider.config.project_id = request.project_id

    try:
        path = await provider.speak(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            language=request.language,
            role=request.role,
        )
    finally:
        provider.config.backend = original_backend
        provider.config.project_id = original_project

    if path is None:
        raise HTTPException(status_code=500, detail="TTS generation failed — check backend availability")

    return {
        "status": "ok",
        "audio_path": path,
        "backend": provider.active_backend.value,
        "text_length": len(request.text),
    }


@router.post("/speak-batch", summary="Generate TTS audio for multiple texts")
async def speak_batch(request: TTSSpeakBatchRequest):
    """Batch speech generation — faster on Qwen3-TTS (single GPU pass)."""
    from core.tts_provider import get_tts_provider
    provider = get_tts_provider()

    original_project = provider.config.project_id
    if request.project_id is not None:
        provider.config.project_id = request.project_id
    try:
        paths = await provider.speak_batch(
            texts=request.texts,
            voice=request.voice,
            language=request.language,
            role=request.role,
        )
    finally:
        provider.config.project_id = original_project

    return {
        "status": "ok",
        "audio_paths": paths,
        "count": len(paths),
        "backend": provider.active_backend.value,
    }


@router.post("/stream", summary="Generate TTS audio and stream the bytes back")
async def stream_speech(request: TTSStreamRequest):
    """
    Returns the rendered audio as a streaming Response so the browser
    <audio> element can play it directly.

    Headers:
        X-TTS-Backend   — 'edge' or 'qwen'
        X-TTS-Chars     — input text length
    """
    from core.tts_provider import get_tts_provider
    provider = get_tts_provider()

    original_backend = provider.config.backend
    original_project = provider.config.project_id
    if request.backend:
        provider.set_backend(request.backend)
    if request.project_id is not None:
        provider.config.project_id = request.project_id

    try:
        result = await provider.speak_stream(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            language=request.language,
            role=request.role,
        )
    finally:
        provider.config.backend = original_backend
        provider.config.project_id = original_project

    if result is None:
        raise HTTPException(status_code=500, detail="TTS generation failed — check backend availability")

    audio_bytes, mime_type, backend_id = result
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "X-TTS-Backend": backend_id,
            "X-TTS-Chars": str(len(request.text)),
            "Cache-Control": "no-store",
        },
    )
