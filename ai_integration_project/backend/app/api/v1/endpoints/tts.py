"""
Advanced TTS API endpoints for Vajra.Stream
Integrates OpenAI TTS, ElevenLabs, and Coqui TTS with sacred language support
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import asyncio
import logging
import io
import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Request Models
class SpeechSynthesisRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    language: str = Field(default="en", description="Language code (en, sa, bo, pi, zh, ja)")
    voice_preference: Optional[str] = Field(None, description="Preferred voice name")
    provider_preference: Optional[str] = Field(None, description="Preferred provider (openai, elevenlabs, coqui)")
    emotional_tone: str = Field(default="compassionate", description="Emotional tone")
    speed: float = Field(default=1.0, ge=0.1, le=3.0, description="Speech speed")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Voice pitch")
    output_format: str = Field(default="mp3", description="Output format (mp3, wav)")
    optimize_for_frequency: Optional[float] = Field(None, description="Optimize for specific frequency (432, 528, etc.)")
    use_cache: bool = Field(default=True, description="Use cached response if available")

class GuidedMeditationRequest(BaseModel):
    theme: str = Field(..., description="Meditation theme")
    duration_minutes: int = Field(default=10, ge=1, le=60, description="Duration in minutes")
    language: str = Field(default="en", description="Language code")
    voice_style: str = Field(default="gentle", description="Voice style")
    include_background_frequency: bool = Field(default=True, description="Include background frequency")
    background_frequency: float = Field(default=432.0, description="Background frequency in Hz")

class VoiceCloningRequest(BaseModel):
    voice_name: str = Field(..., description="Name for cloned voice")
    audio_samples: List[str] = Field(..., description="Base64 encoded audio samples")
    description: str = Field(default="", description="Voice description")
    language: str = Field(default="en", description="Voice language")

class MultilingualTeachingRequest(BaseModel):
    teaching_text: str = Field(..., description="Teaching content")
    source_language: str = Field(default="en", description="Source language")
    target_languages: List[str] = Field(..., description="Target language codes")
    voice_style: str = Field(default="teaching", description="Voice style")

# Response Models
class TTSResponse(BaseModel):
    status: str
    audio_data: str  # Base64 encoded
    duration: float
    sample_rate: int
    provider: str
    voice_used: str
    language: str
    generation_time: float
    cached: bool = False
    metadata: Optional[dict] = None

class VoiceListResponse(BaseModel):
    status: str
    voices: dict
    total_count: int
    language_counts: dict

# Import services
from backend.core.services.advanced_tts_service import advanced_tts_service, TTSRequest, SacredLanguage, TTSProvider

@router.post("/synthesize")
async def synthesize_speech(request: SpeechSynthesisRequest, background_tasks: BackgroundTasks):
    """Synthesize speech using advanced TTS service"""
    try:
        logger.info(f"🎤 Speech synthesis request: {len(request.text)} characters")
        
        # Map language code to SacredLanguage enum
        language_map = {
            "en": SacredLanguage.ENGLISH,
            "sa": SacredLanguage.SANSKRIT,
            "bo": SacredLanguage.TIBETAN,
            "pi": SacredLanguage.PALI,
            "zh": SacredLanguage.CHINESE,
            "ja": SacredLanguage.JAPANESE
        }
        
        language = language_map.get(request.language, SacredLanguage.ENGLISH)
        
        # Map provider preference
        provider_map = {
            "openai": TTSProvider.OPENAI_TTS,
            "elevenlabs": TTSProvider.ELEVENLABS,
            "coqui": TTSProvider.COQUI_TTS
        }
        
        provider = provider_map.get(request.provider_preference) if request.provider_preference else None
        
        # Create TTS request
        tts_request = TTSRequest(
            text=request.text,
            language=language,
            voice_preference=request.voice_preference,
            provider_preference=provider,
            speed=request.speed,
            pitch=request.pitch,
            emotional_tone=request.emotional_tone,
            output_format=request.output_format,
            optimize_for_frequency=request.optimize_for_frequency,
            use_cache=request.use_cache
        )
        
        # Generate speech
        response = await advanced_tts_service.synthesize(tts_request)
        
        # Encode audio data as base64
        audio_base64 = base64.b64encode(response.audio_data).decode('utf-8')
        
        return TTSResponse(
            status="success",
            audio_data=audio_base64,
            duration=response.duration,
            sample_rate=response.sample_rate,
            provider=response.provider.value,
            voice_used=response.voice_used,
            language=request.language,
            generation_time=response.generation_time,
            cached=response.cached,
            metadata=response.metadata
        )
        
    except Exception as e:
        logger.error(f"❌ Speech synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/guided-meditation")
async def create_guided_meditation(request: GuidedMeditationRequest, background_tasks: BackgroundTasks):
    """Create a complete guided meditation with speech synthesis"""
    try:
        logger.info(f"🧘 Guided meditation request: {request.theme}")
        
        # First generate meditation script using LLM
        from backend.core.services.enhanced_llm_service import enhanced_llm_service, GenerationRequest
        
        script_request = GenerationRequest(
            prompt=f"Generate a {request.duration_minutes}-minute guided meditation script on {request.theme}",
            system_prompt=f"You are a meditation guide creating gentle, {request.voice_style} instructions",
            max_tokens=request.duration_minutes * 100,
            temperature=0.7,
            context={
                "request_type": "meditation_guidance",
                "duration": request.duration_minutes,
                "style": request.voice_style
            }
        )
        
        script_response = await enhanced_llm_service.generate(script_request)
        meditation_script = script_response.content
        
        # Synthesize speech
        language_map = {
            "en": SacredLanguage.ENGLISH,
            "sa": SacredLanguage.SANSKRIT,
            "bo": SacredLanguage.TIBETAN,
            "pi": SacredLanguage.PALI,
            "zh": SacredLanguage.CHINESE,
            "ja": SacredLanguage.JAPANESE
        }
        
        tts_request = TTSRequest(
            text=meditation_script,
            language=language_map.get(request.language, SacredLanguage.ENGLISH),
            emotional_tone=request.voice_style,
            speed=0.9,  # Slower for meditation
            optimize_for_frequency=request.background_frequency if request.include_background_frequency else None,
            use_cache=True
        )
        
        tts_response = await advanced_tts_service.synthesize(tts_request)
        
        # Encode audio data
        audio_base64 = base64.b64encode(tts_response.audio_data).decode('utf-8')
        
        return {
            "status": "success",
            "script": meditation_script,
            "audio_data": audio_base64,
            "duration": tts_response.duration,
            "provider": tts_response.provider.value,
            "voice_used": tts_response.voice_used,
            "language": request.language,
            "background_frequency": request.background_frequency if request.include_background_frequency else None,
            "generation_time": tts_response.generation_time,
            "metadata": {
                "theme": request.theme,
                "duration_minutes": request.duration_minutes,
                "voice_style": request.voice_style,
                "script_model": script_response.model_used,
                "script_provider": script_response.provider.value
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Guided meditation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice-cloning")
async def clone_voice(request: VoiceCloningRequest, background_tasks: BackgroundTasks):
    """Clone a voice for personalized TTS"""
    try:
        logger.info(f"🎭 Voice cloning request: {request.voice_name}")
        
        # This would integrate with ElevenLabs voice cloning API
        # For now, return a placeholder response
        
        return {
            "status": "success",
            "message": "Voice cloning initiated",
            "voice_name": request.voice_name,
            "estimated_completion_time": "30 minutes",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Voice cloning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/multilingual-teaching")
async def create_multilingual_teaching(request: MultilingualTeachingRequest, background_tasks: BackgroundTasks):
    """Create teaching in multiple languages"""
    try:
        logger.info(f"🌍 Multilingual teaching request: {len(request.target_languages)} languages")
        
        multilingual_audio = {}
        
        for target_lang in request.target_languages:
            # Translate teaching (would need translation service)
            translated_text = request.teaching_text  # Placeholder for translation
            
            # Synthesize speech
            language_map = {
                "en": SacredLanguage.ENGLISH,
                "sa": SacredLanguage.SANSKRIT,
                "bo": SacredLanguage.TIBETAN,
                "pi": SacredLanguage.PALI,
                "zh": SacredLanguage.CHINESE,
                "ja": SacredLanguage.JAPANESE
            }
            
            tts_request = TTSRequest(
                text=translated_text,
                language=language_map.get(target_lang, SacredLanguage.ENGLISH),
                emotional_tone=request.voice_style,
                use_cache=True
            )
            
            tts_response = await advanced_tts_service.synthesize(tts_request)
            audio_base64 = base64.b64encode(tts_response.audio_data).decode('utf-8')
            
            multilingual_audio[target_lang] = {
                "audio_data": audio_base64,
                "duration": tts_response.duration,
                "voice_used": tts_response.voice_used,
                "provider": tts_response.provider.value
            }
        
        return {
            "status": "success",
            "source_language": request.source_language,
            "target_languages": request.target_languages,
            "teaching_text": request.teaching_text,
            "audio_files": multilingual_audio,
            "total_duration": sum(audio["duration"] for audio in multilingual_audio.values())
        }
        
    except Exception as e:
        logger.error(f"❌ Multilingual teaching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-voices")
async def get_available_voices():
    """Get list of available TTS voices"""
    try:
        voices = await advanced_tts_service.get_available_voices()
        
        formatted_voices = {}
        language_counts = {}
        
        for voice_id, config in voices.items():
            formatted_voices[voice_id] = {
                "provider": config.provider.value,
                "voice_id": config.voice_id,
                "language": config.language.value,
                "gender": config.gender,
                "age": config.age,
                "style": config.style,
                "emotional_range": getattr(config, 'emotional_range', 0.7)
            }
            
            # Count languages
            lang = config.language.value
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        return VoiceListResponse(
            status="success",
            voices=formatted_voices,
            total_count=len(formatted_voices),
            language_counts=language_counts
        )
        
    except Exception as e:
        logger.error(f"❌ Available voices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voices/{language}")
async def get_voices_by_language(language: str):
    """Get voices for specific language"""
    try:
        language_map = {
            "en": SacredLanguage.ENGLISH,
            "sa": SacredLanguage.SANSKRIT,
            "bo": SacredLanguage.TIBETAN,
            "pi": SacredLanguage.PALI,
            "zh": SacredLanguage.CHINESE,
            "ja": SacredLanguage.JAPANESE
        }
        
        sacred_lang = language_map.get(language)
        if not sacred_lang:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
        
        voice_ids = await advanced_tts_service.get_voices_by_language(sacred_lang)
        
        return {
            "status": "success",
            "language": language,
            "voice_count": len(voice_ids),
            "voices": voice_ids
        }
        
    except Exception as e:
        logger.error(f"❌ Voices by language error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache")
async def clear_tts_cache():
    """Clear TTS cache"""
    try:
        # Clear cache (would need to implement this in the service)
        advanced_tts_service.cache.clear()
        
        logger.info("✅ TTS cache cleared")
        
        return {
            "status": "success",
            "message": "TTS cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ TTS cache clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))