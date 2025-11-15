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
        Include posture, breath awareness, and main practice."""
        
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
        # Clear cache
        enhanced_llm_service.cache.clear()
        
        logger.info("✅ LLM cache cleared")
        
        return {
            "status": "success",
            "message": "LLM cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))