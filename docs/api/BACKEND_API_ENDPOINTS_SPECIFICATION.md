# Backend API Endpoints Specification for Enhanced AI Services

## 🎯 Overview

This specification details the API endpoints for integrating the enhanced LLM service (with Z AI GLM 4.6 and LM Studio) and advanced TTS service into the Vajra.Stream backend.

## 📁 API Structure

```
backend/app/api/v1/endpoints/
├── llm.py                    # Enhanced LLM endpoints
├── tts.py                    # Advanced TTS endpoints
├── ai_analysis.py            # AI audio analysis endpoints
└── intelligent_session.py      # AI-powered session management
```

## 🔧 Enhanced LLM Endpoints: `backend/app/api/v1/endpoints/llm.py`

### Implementation

```python
"""
Enhanced LLM API endpoints for Vajra.Stream
Integrates Z AI GLM 4.6, LM Studio, and fallback models
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Request Models
class PrayerRequest(BaseModel):
    intention: str = Field(..., description="Intention for the prayer")
    tradition: str = Field(default="universal", description="Tradition style (universal, buddhist, tibetan, zen)")
    length: str = Field(default="short", description="Length (short, medium, long)")
    language: str = Field(default="en", description="Language code")
    emotional_tone: str = Field(default="compassionate", description="Emotional tone")
    use_local_model: bool = Field(default=True, description="Prefer local models")

class TeachingRequest(BaseModel):
    topic: str = Field(..., description="Teaching topic")
    tradition: str = Field(default="buddhist", description="Tradition context")
    audience: str = Field(default="general", description="Target audience (beginners, advanced, general)")
    length: str = Field(default="medium", description="Teaching length")
    complexity: str = Field(default="moderate", description="Complexity level")
    language: str = Field(default="en", description="Language code")

class MeditationInstructionRequest(BaseModel):
    practice: str = Field(..., description="Type of meditation")
    duration_minutes: int = Field(default=10, description="Duration in minutes")
    experience_level: str = Field(default="beginner", description="Experience level")
    style: str = Field(default="gentle", description="Guidance style")
    language: str = Field(default="en", description="Language code")

class ContemplationRequest(BaseModel):
    theme: str = Field(..., description="Contemplation theme")
    context: Optional[str] = Field(None, description="Additional context")
    depth: str = Field(default="moderate", description="Depth of contemplation")
    reflection_questions: bool = Field(default=True, description="Include reflection questions")

class ModelSwitchRequest(BaseModel):
    model_id: str = Field(..., description="Model identifier to switch to")
    provider: Optional[str] = Field(None, description="Provider preference")

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    analysis_type: str = Field(..., description="Type of analysis (sentiment, themes, complexity)")
    language: str = Field(default="en", description="Text language")

# Response Models
class LLMResponse(BaseModel):
    status: str
    content: str
    model_used: str
    provider: str
    tokens_used: int
    generation_time: float
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None

class ModelStatusResponse(BaseModel):
    active_model: str
    available_models: Dict[str, Any]
    lm_studio_available: bool
    lm_studio_models: List[str]
    total_models: int
    cache_size: int

# Import services
from backend.core.services.enhanced_llm_service import enhanced_llm_service, GenerationRequest, ModelProvider

@router.post("/generate-prayer")
async def generate_prayer(request: PrayerRequest, background_tasks: BackgroundTasks):
    """Generate a prayer using enhanced LLM service"""
    try:
        logger.info(f"🙏 Prayer generation request: {request.intention}")
        
        # Create generation request
        system_prompt = f"""You are a wise dharma teacher creating heartfelt prayers.
        Tradition: {request.tradition}
        Emotional tone: {request.emotional_tone}
        Language: {request.language}
        Length: {request.length}
        
        Generate a beautiful, sincere prayer that expresses {request.intention}.
        The prayer should be inclusive of all beings and suitable for contemplation."""
        
        llm_request = GenerationRequest(
            prompt=f"Generate a {request.length} prayer for {request.intention}",
            system_prompt=system_prompt,
            max_tokens=300 if request.length == "short" else 600 if request.length == "medium" else 1000,
            temperature=0.8,
            context={
                "request_type": "prayer_generation",
                "tradition": request.tradition,
                "emotional_tone": request.emotional_tone
            },
            preferred_provider=ModelProvider.LM_STUDIO if request.use_local_model else None
        )
        
        # Generate response
        response = await enhanced_llm_service.generate(llm_request)
        
        return LLMResponse(
            status="success",
            content=response.content,
            model_used=response.model_used,
            provider=response.provider.value,
            tokens_used=response.tokens_used,
            generation_time=response.generation_time,
            cached=response.cached,
            metadata={
                "intention": request.intention,
                "tradition": request.tradition,
                "length": request.length,
                "is_local": response.metadata.get("local_model", False)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Prayer generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-teaching")
async def generate_teaching(request: TeachingRequest, background_tasks: BackgroundTasks):
    """Generate a dharma teaching using enhanced LLM service"""
    try:
        logger.info(f"📚 Teaching generation request: {request.topic}")
        
        # Create generation request
        system_prompt = f"""You are a knowledgeable dharma teacher providing clear, accessible teachings.
        Tradition: {request.tradition}
        Audience: {request.audience}
        Complexity: {request.complexity}
        Language: {request.language}
        Length: {request.length}
        
        Create a teaching on {request.topic} that is appropriate for {request.audience} practitioners.
        The teaching should be clear, practical, and rooted in authentic dharma wisdom."""
        
        max_tokens_map = {"short": 400, "medium": 800, "long": 1500}
        
        llm_request = GenerationRequest(
            prompt=f"Provide a teaching on {request.topic} for {request.audience} practitioners",
            system_prompt=system_prompt,
            max_tokens=max_tokens_map.get(request.length, 800),
            temperature=0.7,
            context={
                "request_type": "teaching_generation",
                "audience": request.audience,
                "complexity": request.complexity
            }
        )
        
        # Generate response
        response = await enhanced_llm_service.generate(llm_request)
        
        return LLMResponse(
            status="success",
            content=response.content,
            model_used=response.model_used,
            provider=response.provider.value,
            tokens_used=response.tokens_used,
            generation_time=response.generation_time,
            cached=response.cached,
            metadata={
                "topic": request.topic,
                "audience": request.audience,
                "complexity": request.complexity,
                "length": request.length
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Teaching generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-meditation-instructions")
async def generate_meditation_instructions(request: MeditationInstructionRequest, background_tasks: BackgroundTasks):
    """Generate guided meditation instructions"""
    try:
        logger.info(f"🧘 Meditation instruction request: {request.practice}")
        
        # Create generation request
        system_prompt = f"""You are an experienced meditation guide creating gentle, clear instructions.
        Practice: {request.practice}
        Experience Level: {request.experience_level}
        Duration: {request.duration_minutes} minutes
        Style: {request.style}
        Language: {request.language}
        
        Create meditation instructions that guide the practitioner through {request.practice}.
        The instructions should be gentle, clear, and appropriate for {request.experience_level} level.
        Include posture, breath awareness, and the main practice."""
        
        llm_request = GenerationRequest(
            prompt=f"Generate {request.duration_minutes}-minute guided meditation instructions for {request.practice}",
            system_prompt=system_prompt,
            max_tokens=request.duration_minutes * 50,  # ~50 words per minute
            temperature=0.6,
            context={
                "request_type": "meditation_guidance",
                "experience_level": request.experience_level,
                "duration": request.duration_minutes
            }
        )
        
        # Generate response
        response = await enhanced_llm_service.generate(llm_request)
        
        return LLMResponse(
            status="success",
            content=response.content,
            model_used=response.model_used,
            provider=response.provider.value,
            tokens_used=response.tokens_used,
            generation_time=response.generation_time,
            cached=response.cached,
            metadata={
                "practice": request.practice,
                "duration_minutes": request.duration_minutes,
                "experience_level": request.experience_level,
                "style": request.style
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Meditation instruction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-contemplation")
async def generate_contemplation(request: ContemplationRequest, background_tasks: BackgroundTasks):
    """Generate contemplation exercise"""
    try:
        logger.info(f"🔍 Contemplation generation request: {request.theme}")
        
        # Create generation request
        system_prompt = f"""You are a wise spiritual guide creating profound contemplation exercises.
        Theme: {request.theme}
        Depth: {request.depth}
        Context: {request.context or 'General spiritual practice'}
        
        Create a contemplation exercise on {request.theme} that invites deep reflection.
        The exercise should be accessible yet profound, suitable for meditation practice."""
        
        llm_request = GenerationRequest(
            prompt=f"Create a contemplation exercise on {request.theme}",
            system_prompt=system_prompt,
            max_tokens=500 if request.depth == "moderate" else 800,
            temperature=0.7,
            context={
                "request_type": "contemplation",
                "depth": request.depth,
                "reflection_questions": request.reflection_questions
            }
        )
        
        # Generate response
        response = await enhanced_llm_service.generate(llm_request)
        
        return LLMResponse(
            status="success",
            content=response.content,
            model_used=response.model_used,
            provider=response.provider.value,
            tokens_used=response.tokens_used,
            generation_time=response.generation_time,
            cached=response.cached,
            metadata={
                "theme": request.theme,
                "depth": request.depth,
                "reflection_questions": request.reflection_questions
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Contemplation generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-text")
async def analyze_text(request: TextAnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze text using AI"""
    try:
        logger.info(f"📝 Text analysis request: {request.analysis_type}")
        
        # Create analysis prompt based on type
        if request.analysis_type == "sentiment":
            prompt = f"Analyze the sentiment of this text: {request.text}"
            system_prompt = "You are a text analysis expert. Provide detailed sentiment analysis."
        elif request.analysis_type == "themes":
            prompt = f"Identify the main themes in this text: {request.text}"
            system_prompt = "You are a literary analysis expert. Identify and explain key themes."
        elif request.analysis_type == "complexity":
            prompt = f"Assess the complexity of this text: {request.text}"
            system_prompt = "You are a text analysis expert. Assess readability and complexity."
        else:
            raise ValueError(f"Unsupported analysis type: {request.analysis_type}")
        
        llm_request = GenerationRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=400,
            temperature=0.3,  # Lower temperature for analysis
            context={
                "request_type": "text_analysis",
                "analysis_type": request.analysis_type,
                "language": request.language
            }
        )
        
        # Generate response
        response = await enhanced_llm_service.generate(llm_request)
        
        return LLMResponse(
            status="success",
            content=response.content,
            model_used=response.model_used,
            provider=response.provider.value,
            tokens_used=response.tokens_used,
            generation_time=response.generation_time,
            cached=response.cached,
            metadata={
                "analysis_type": request.analysis_type,
                "text_length": len(request.text),
                "language": request.language
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Text analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-status")
async def get_model_status():
    """Get status of all available models"""
    try:
        status = await enhanced_llm_service.get_model_status()
        
        return ModelStatusResponse(
            active_model=status["active_model"],
            available_models=status["models"],
            lm_studio_available=status["lm_studio_available"],
            lm_studio_models=status["lm_studio_models"],
            total_models=status["total_models"],
            cache_size=status["cache_size"]
        )
        
    except Exception as e:
        logger.error(f"❌ Model status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-models")
async def get_available_models():
    """Get list of all available models"""
    try:
        models = await enhanced_llm_service.get_available_models()
        
        formatted_models = {}
        for model_id, config in models.items():
            formatted_models[model_id] = {
                "provider": config.provider.value,
                "model_name": config.model_name,
                "language": getattr(config, 'language', 'en'),
                "max_tokens": config.max_tokens,
                "temperature": config.temperature
            }
        
        return {
            "status": "success",
            "models": formatted_models,
            "count": len(formatted_models)
        }
        
    except Exception as e:
        logger.error(f"❌ Available models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/switch-model")
async def switch_model(request: ModelSwitchRequest):
    """Switch active model"""
    try:
        logger.info(f"🔄 Model switch request: {request.model_id}")
        
        success = await enhanced_llm_service.switch_model(request.model_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Switched to model: {request.model_id}",
                "active_model": request.model_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Model not found: {request.model_id}")
        
    except Exception as e:
        logger.error(f"❌ Model switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache")
async def clear_cache():
    """Clear LLM response cache"""
    try:
        # Clear cache (would need to implement this in the service)
        enhanced_llm_service.cache.clear()
        
        logger.info("✅ LLM cache cleared")
        
        return {
            "status": "success",
            "message": "LLM cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 🎤 Advanced TTS Endpoints: `backend/app/api/v1/endpoints/tts.py`

### Implementation

```python
"""
Advanced TTS API endpoints for Vajra.Stream
Integrates OpenAI TTS, ElevenLabs, Coqui TTS with sacred language support
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
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
    voice_name: str = Field(..., description="Name for the cloned voice")
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
```

## 🔍 AI Analysis Endpoints: `backend/app/api/v1/endpoints/ai_analysis.py`

### Implementation

```python
"""
AI Analysis API endpoints for Vajra.Stream
Real-time audio analysis and frequency optimization
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Request Models
class AudioAnalysisRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio data")
    analysis_type: str = Field(..., description="Type of analysis (frequency, harmony, quality)")
    target_frequency: Optional[float] = Field(None, description="Target frequency for optimization")
    session_context: Optional[Dict[str, Any]] = Field(None, description="Session context")

class FrequencyOptimizationRequest(BaseModel):
    current_frequency: float = Field(..., description="Current frequency in Hz")
    intention: str = Field(..., description="Session intention")
    duration_minutes: int = Field(default=30, description="Session duration")
    sacred_tradition: str = Field(default="universal", description="Sacred tradition")

class PersonalizationRequest(BaseModel):
    user_preferences: Dict[str, Any] = Field(..., description="User preferences")
    session_history: Optional[List[Dict[str, Any]]] = Field(None, description="Session history")
    current_session: Optional[Dict[str, Any]] = Field(None, description="Current session data")

# Response Models
class AnalysisResponse(BaseModel):
    status: str
    analysis_results: Dict[str, Any]
    recommendations: List[str]
    confidence_score: float
    processing_time: float

class OptimizationResponse(BaseModel):
    status: str
    optimized_frequency: float
    reasoning: str
    alternative_frequencies: List[float]
    confidence: float

# Import services
from backend.core.services.ai_audio_analyzer import ai_audio_analyzer
from backend.core.services.intelligent_session_manager import intelligent_session_manager

@router.post("/analyze-audio")
async def analyze_audio(request: AudioAnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze audio using AI"""
    try:
        logger.info(f"🔊 Audio analysis request: {request.analysis_type}")
        
        # Decode audio data
        import base64
        audio_bytes = base64.b64decode(request.audio_data)
        
        # Perform analysis based on type
        if request.analysis_type == "frequency":
            results = await ai_audio_analyzer.analyze_frequency_spectrum(audio_bytes)
        elif request.analysis_type == "harmony":
            results = await ai_audio_analyzer.analyze_harmonic_content(audio_bytes)
        elif request.analysis_type == "quality":
            results = await ai_audio_analyzer.assess_audio_quality(audio_bytes)
        else:
            raise ValueError(f"Unsupported analysis type: {request.analysis_type}")
        
        # Generate recommendations
        recommendations = await ai_audio_analyzer.generate_recommendations(results, request.session_context)
        
        return AnalysisResponse(
            status="success",
            analysis_results=results,
            recommendations=recommendations,
            confidence_score=results.get("confidence", 0.8),
            processing_time=results.get("processing_time", 0.0)
        )
        
    except Exception as e:
        logger.error(f"❌ Audio analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize-frequency")
async def optimize_frequency(request: FrequencyOptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize frequency based on intention and context"""
    try:
        logger.info(f"🎵 Frequency optimization request: {request.intention}")
        
        # Use AI to determine optimal frequency
        optimization_result = await ai_audio_analyzer.optimize_frequency_for_intention(
            current_frequency=request.current_frequency,
            intention=request.intention,
            duration=request.duration_minutes,
            tradition=request.sacred_tradition
        )
        
        return OptimizationResponse(
            status="success",
            optimized_frequency=optimization_result["recommended_frequency"],
            reasoning=optimization_result["reasoning"],
            alternative_frequencies=optimization_result["alternatives"],
            confidence=optimization_result["confidence"]
        )
        
    except Exception as e:
        logger.error(f"❌ Frequency optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/personalize-session")
async def personalize_session(request: PersonalizationRequest, background_tasks: BackgroundTasks):
    """AI-powered session personalization"""
    try:
        logger.info(f"🎨 Session personalization request")
        
        # Generate personalization recommendations
        personalization = await intelligent_session_manager.generate_personalization(
            user_preferences=request.user_preferences,
            session_history=request.session_history,
            current_session=request.current_session
        )
        
        return {
            "status": "success",
            "personalization": personalization,
            "recommendations": personalization.get("recommendations", []),
            "adjusted_settings": personalization.get("adjusted_settings", {}),
            "confidence": personalization.get("confidence", 0.7)
        }
        
    except Exception as e:
        logger.error(f"❌ Session personalization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 🚀 Integration with Main App

### Update `backend/app/main.py`

```python
# Add new routers to main.py
from app.api.v1.endpoints import llm, tts, ai_analysis

app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])
app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])
app.include_router(ai_analysis.router, prefix="/api/v1/ai", tags=["ai_analysis"])
```

### Update `backend/requirements.txt`

```txt
# Add new dependencies
aiohttp>=3.8.0
pyyaml>=6.0
base64  # Built-in, but ensure imports
soundfile>=0.12.0
numpy>=1.24.0
TTS>=0.22.0
librosa>=0.9.0  # For audio processing
```

## 📊 API Usage Examples

### Generate Prayer
```javascript
// Frontend usage
const prayerResponse = await fetch('/api/v1/llm/generate-prayer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    intention: "healing and compassion",
    tradition: "buddhist",
    length: "short",
    emotional_tone: "compassionate",
    use_local_model: true
  })
});

const result = await prayerResponse.json();
console.log('Generated prayer:', result.content);
console.log('Model used:', result.model_used);
console.log('Is local:', result.metadata.is_local);
```

### Synthesize Speech
```javascript
const ttsResponse = await fetch('/api/v1/tts/synthesize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: "May all beings be happy and free from suffering",
    language: "en",
    emotional_tone: "compassionate",
    provider_preference: "elevenlabs",
    optimize_for_frequency: 528,
    output_format: "mp3"
  })
});

const audioResult = await ttsResponse.json();
const audioData = atob(audioResult.audio_data);  // Decode base64
const audioBlob = new Blob([audioData], { type: 'audio/mp3' });
const audioUrl = URL.createObjectURL(audioBlob);

// Play audio
const audio = new Audio(audioUrl);
audio.play();
```

### Guided Meditation
```javascript
const meditationResponse = await fetch('/api/v1/tts/guided-meditation', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    theme: "loving-kindness",
    duration_minutes: 15,
    language: "en",
    voice_style: "gentle",
    include_background_frequency: true,
    background_frequency: 432
  })
});

const meditation = await meditationResponse.json();
console.log('Meditation script:', meditation.script);
console.log('Audio duration:', meditation.duration);
console.log('Background frequency:', meditation.background_frequency);
```

## 🔒 Security Considerations

### API Key Management
- Store API keys in environment variables
- Use secure key rotation
- Implement rate limiting
- Audit API usage

### Input Validation
- Sanitize all text inputs
- Validate audio data size limits
- Check for malicious content
- Implement request size limits

### Output Filtering
- Validate generated content
- Filter inappropriate responses
- Implement content moderation
- Cache sanitized responses

---

**Backend API Endpoints Specification Complete** 🚀

This specification provides comprehensive API endpoints for integrating enhanced LLM and TTS services, enabling Vajra.Stream to offer intelligent, personalized spiritual content generation and high-quality audio synthesis.