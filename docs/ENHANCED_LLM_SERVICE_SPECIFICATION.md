# Enhanced LLM Service Implementation Specification

## 🎯 Overview

This specification details the implementation of the Enhanced LLM Service that integrates Z AI GLM 4.6 as the default model with support for local models and intelligent routing.

## 📁 File: `backend/core/services/enhanced_llm_service.py`

### Class Structure

```python
"""
Enhanced LLM Service for Vajra.Stream
Integrates Z AI GLM 4.6 with local model support and intelligent routing
"""

import os
import json
import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import glob
import logging
from enum import Enum

try:
    import aiohttp
    import yaml
    from openai import AsyncOpenAI
    from anthropic import AsyncAnthropic
    from llama_cpp import Llama
except ImportError as e:
    logging.warning(f"Some dependencies not available: {e}")

class ModelProvider(Enum):
    Z_AI_GLM = "z_ai_glm"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    local_path: Optional[str] = None

@dataclass
class GenerationRequest:
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    context: Optional[Dict[str, Any]] = None
    use_cache: bool = True
    priority: str = "normal"  # normal, high, low

@dataclass
class GenerationResponse:
    content: str
    model_used: str
    provider: ModelProvider
    tokens_used: int
    generation_time: float
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None

class EnhancedLLMService:
    """
    Enhanced LLM service with Z AI GLM 4.6 integration
    Supports multiple providers with intelligent routing and caching
    """
    
    def __init__(self, config_path: str = "config/ai_models.yaml"):
        self.config_path = config_path
        self.models: Dict[str, ModelConfig] = {}
        self.active_model: Optional[str] = None
        self.cache: Dict[str, GenerationResponse] = {}
        self.cache_ttl = 3600  # 1 hour
        self.request_queue = asyncio.Queue()
        self.rate_limits: Dict[str, Dict] = {}
        
        # Initialize clients
        self.z_ai_client = None
        self.openai_client = None
        self.anthropic_client = None
        self.local_models: Dict[str, Llama] = {}
        
        # Load configuration
        self._load_configuration()
        self._initialize_clients()
        
        logging.info("Enhanced LLM Service initialized")
    
    def _load_configuration(self):
        """Load model configurations from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load Z AI GLM 4.6 as primary
            if 'z_ai_glm' in config:
                glm_config = config['z_ai_glm']
                self.models['z_ai_glm_4.6'] = ModelConfig(
                    provider=ModelProvider.Z_AI_GLM,
                    model_name=glm_config.get('model_name', 'glm-4.6'),
                    api_key=glm_config.get('api_key') or os.getenv('Z_AI_API_KEY'),
                    api_endpoint=glm_config.get('api_endpoint'),
                    max_tokens=glm_config.get('max_tokens', 4096),
                    temperature=glm_config.get('temperature', 0.7),
                    system_prompt=glm_config.get('system_prompt')
                )
            
            # Load local models
            if 'local_models' in config:
                local_config = config['local_models']
                models_dir = Path(local_config.get('directory', './models/local'))
                
                for gguf_file in models_dir.rglob("*.gguf"):
                    model_name = gguf_file.stem
                    self.models[f"local_{model_name}"] = ModelConfig(
                        provider=ModelProvider.LOCAL,
                        model_name=model_name,
                        local_path=str(gguf_file),
                        max_tokens=2048,
                        temperature=0.7
                    )
            
            # Load fallback models
            if 'fallback_models' in config:
                for i, fallback in enumerate(config['fallback_models']):
                    provider_name = fallback.get('provider')
                    if provider_name == 'openai':
                        self.models[f'openai_{i}'] = ModelConfig(
                            provider=ModelProvider.OPENAI,
                            model_name=fallback.get('model', 'gpt-4o-mini'),
                            api_key=fallback.get('api_key') or os.getenv('OPENAI_API_KEY'),
                            max_tokens=fallback.get('max_tokens', 4096),
                            temperature=fallback.get('temperature', 0.7)
                        )
                    elif provider_name == 'anthropic':
                        self.models[f'anthropic_{i}'] = ModelConfig(
                            provider=ModelProvider.ANTHROPIC,
                            model_name=fallback.get('model', 'claude-3-5-haiku'),
                            api_key=fallback.get('api_key') or os.getenv('ANTHROPIC_API_KEY'),
                            max_tokens=fallback.get('max_tokens', 4096),
                            temperature=fallback.get('temperature', 0.7)
                        )
            
            # Set default active model
            self.active_model = 'z_ai_glm_4.6' if 'z_ai_glm_4.6' in self.models else list(self.models.keys())[0]
            
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            # Fallback to basic configuration
            self.models['fallback'] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name='gpt-4o-mini',
                api_key=os.getenv('OPENAI_API_KEY')
            )
            self.active_model = 'fallback'
    
    def _initialize_clients(self):
        """Initialize API clients for all configured models"""
        for model_id, config in self.models.items():
            try:
                if config.provider == ModelProvider.Z_AI_GLM and config.api_key:
                    self.z_ai_client = aiohttp.ClientSession()
                elif config.provider == ModelProvider.OPENAI and config.api_key:
                    self.openai_client = AsyncOpenAI(api_key=config.api_key)
                elif config.provider == ModelProvider.ANTHROPIC and config.api_key:
                    self.anthropic_client = AsyncAnthropic(api_key=config.api_key)
                elif config.provider == ModelProvider.LOCAL and config.local_path:
                    # Initialize local model (lazy loading)
                    pass
            except Exception as e:
                logging.error(f"Failed to initialize client for {model_id}: {e}")
    
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate text using the enhanced LLM service
        """
        start_time = time.time()
        
        # Check cache first
        if request.use_cache:
            cached_response = self._get_from_cache(request)
            if cached_response:
                cached_response.cached = True
                return cached_response
        
        # Get model to use
        model_id = await self._select_model(request)
        model_config = self.models[model_id]
        
        try:
            # Generate response based on provider
            if model_config.provider == ModelProvider.Z_AI_GLM:
                response = await self._generate_z_ai_glm(request, model_config)
            elif model_config.provider == ModelProvider.OPENAI:
                response = await self._generate_openai(request, model_config)
            elif model_config.provider == ModelProvider.ANTHROPIC:
                response = await self._generate_anthropic(request, model_config)
            elif model_config.provider == ModelProvider.LOCAL:
                response = await self._generate_local(request, model_config)
            else:
                raise ValueError(f"Unsupported provider: {model_config.provider}")
            
            # Update cache
            if request.use_cache:
                self._add_to_cache(request, response)
            
            generation_time = time.time() - start_time
            response.generation_time = generation_time
            
            return response
            
        except Exception as e:
            logging.error(f"Generation failed with {model_id}: {e}")
            # Try fallback model
            if model_id != self.active_model:
                fallback_model = self.active_model
                logging.info(f"Falling back to {fallback_model}")
                return await self.generate(request)
            else:
                # Return error response
                return GenerationResponse(
                    content=f"Error generating response: {str(e)}",
                    model_used="error",
                    provider=ModelProvider.Z_AI_GLM,
                    tokens_used=0,
                    generation_time=time.time() - start_time,
                    metadata={"error": str(e)}
                )
    
    async def _select_model(self, request: GenerationRequest) -> str:
        """
        Intelligent model selection based on request characteristics
        """
        # Priority requests use primary model
        if request.priority == "high" and self.active_model:
            return self.active_model
        
        # Check rate limits
        for model_id in self.models.keys():
            if not self._is_rate_limited(model_id):
                return model_id
        
        # Default to active model
        return self.active_model
    
    async def _generate_z_ai_glm(self, request: GenerationRequest, config: ModelConfig) -> GenerationResponse:
        """Generate using Z AI GLM 4.6 API"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": request.system_prompt or config.system_prompt or "You are a wise dharma teacher."},
                {"role": "user", "content": request.prompt}
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }
        
        async with self.z_ai_client.post(
            config.api_endpoint or "https://api.z-ai.com/v1/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                
                return GenerationResponse(
                    content=content,
                    model_used=config.model_name,
                    provider=ModelProvider.Z_AI_GLM,
                    tokens_used=tokens_used,
                    metadata={"response_data": data}
                )
            else:
                raise Exception(f"Z AI GLM API error: {response.status}")
    
    async def _generate_openai(self, request: GenerationRequest, config: ModelConfig) -> GenerationResponse:
        """Generate using OpenAI API"""
        messages = []
        if request.system_prompt or config.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt or config.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        response = await self.openai_client.chat.completions.create(
            model=config.model_name,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return GenerationResponse(
            content=response.choices[0].message.content,
            model_used=config.model_name,
            provider=ModelProvider.OPENAI,
            tokens_used=response.usage.total_tokens,
            metadata={"response_id": response.id}
        )
    
    async def _generate_anthropic(self, request: GenerationRequest, config: ModelConfig) -> GenerationResponse:
        """Generate using Anthropic API"""
        kwargs = {
            "model": config.model_name,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [{"role": "user", "content": request.prompt}]
        }
        
        if request.system_prompt or config.system_prompt:
            kwargs["system"] = request.system_prompt or config.system_prompt
        
        response = await self.anthropic_client.messages.create(**kwargs)
        
        return GenerationResponse(
            content=response.content[0].text,
            model_used=config.model_name,
            provider=ModelProvider.ANTHROPIC,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            metadata={"response_id": response.id}
        )
    
    async def _generate_local(self, request: GenerationRequest, config: ModelConfig) -> GenerationResponse:
        """Generate using local GGUF model"""
        if config.model_name not in self.local_models:
            # Lazy load local model
            try:
                self.local_models[config.model_name] = Llama(
                    model_path=config.local_path,
                    n_ctx=2048,
                    n_threads=4,
                    n_gpu_layers=0,
                    verbose=False
                )
            except Exception as e:
                raise Exception(f"Failed to load local model {config.model_name}: {e}")
        
        model = self.local_models[config.model_name]
        
        # Format prompt
        if request.system_prompt or config.system_prompt:
            formatted_prompt = f"### System:\n{request.system_prompt or config.system_prompt}\n\n### User:\n{request.prompt}\n\n### Assistant:\n"
        else:
            formatted_prompt = request.prompt
        
        # Generate
        response = model(
            formatted_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=["###", "\n\n\n"],
            echo=False
        )
        
        return GenerationResponse(
            content=response['choices'][0]['text'].strip(),
            model_used=config.model_name,
            provider=ModelProvider.LOCAL,
            tokens_used=len(response['choices'][0]['text'].split()),
            metadata={"local_model": True}
        )
    
    def _get_from_cache(self, request: GenerationRequest) -> Optional[GenerationResponse]:
        """Get cached response if available and not expired"""
        cache_key = self._generate_cache_key(request)
        
        if cache_key in self.cache:
            cached_response = self.cache[cache_key]
            if time.time() - cached_response.metadata.get('cached_at', 0) < self.cache_ttl:
                return cached_response
            else:
                del self.cache[cache_key]
        
        return None
    
    def _add_to_cache(self, request: GenerationRequest, response: GenerationResponse):
        """Add response to cache"""
        cache_key = self._generate_cache_key(request)
        response.metadata = response.metadata or {}
        response.metadata['cached_at'] = time.time()
        self.cache[cache_key] = response
    
    def _generate_cache_key(self, request: GenerationRequest) -> str:
        """Generate cache key for request"""
        key_data = f"{request.prompt}_{request.system_prompt}_{request.max_tokens}_{request.temperature}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_rate_limited(self, model_id: str) -> bool:
        """Check if model is rate limited"""
        if model_id not in self.rate_limits:
            return False
        
        rate_limit = self.rate_limits[model_id]
        current_time = time.time()
        
        # Reset if window expired
        if current_time - rate_limit['window_start'] > rate_limit['window']:
            rate_limit['requests'] = 0
            rate_limit['window_start'] = current_time
            return False
        
        return rate_limit['requests'] >= rate_limit['max_requests']
    
    async def get_available_models(self) -> Dict[str, ModelConfig]:
        """Get list of available models"""
        return self.models.copy()
    
    async def switch_model(self, model_id: str) -> bool:
        """Switch active model"""
        if model_id in self.models:
            self.active_model = model_id
            logging.info(f"Switched to model: {model_id}")
            return True
        return False
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        status = {
            "active_model": self.active_model,
            "total_models": len(self.models),
            "cache_size": len(self.cache),
            "models": {}
        }
        
        for model_id, config in self.models.items():
            status["models"][model_id] = {
                "provider": config.provider.value,
                "model_name": config.model_name,
                "available": True,  # Could implement health checks
                "rate_limited": self._is_rate_limited(model_id)
            }
        
        return status

# Global instance
enhanced_llm_service = EnhancedLLMService()
```

## 🎛️ Configuration File: `config/ai_models.yaml`

```yaml
# Z AI GLM 4.6 Configuration
z_ai_glm:
  model_name: "glm-4.6"
  api_endpoint: "https://api.z-ai.com/v1/chat/completions"
  api_key: "${Z_AI_API_KEY}"  # Set environment variable
  max_tokens: 4096
  temperature: 0.7
  system_prompt: |
    You are a wise dharma teacher versed in Buddhist philosophy, meditation practices, 
    and contemplative traditions. You speak with clarity, compassion, and depth. 
    Your teachings are rooted in the Buddhadharma but accessible to all beings.
    You draw from Theravada, Mahayana, and Vajrayana traditions as appropriate.

# Local Models Configuration
local_models:
  directory: "./models/local"
  auto_detect: true
  preferred_models:
    - "llama-3-8b-instruct.gguf"
    - "mistral-7b-instruct.gguf"
    - "qwen-7b-chat.gguf"
  
  # Local model settings
  n_ctx: 2048
  n_threads: 4
  n_gpu_layers: 0  # Set > 0 if you have GPU
  verbose: false

# Fallback Models (Cloud APIs)
fallback_models:
  - provider: "openai"
    model: "gpt-4o-mini"
    api_key: "${OPENAI_API_KEY}"
    max_tokens: 4096
    temperature: 0.7
    system_prompt: |
      You are a wise dharma teacher providing spiritual guidance and teachings.
      
  - provider: "anthropic"
    model: "claude-3-5-haiku-20241022"
    api_key: "${ANTHROPIC_API_KEY}"
    max_tokens: 4096
    temperature: 0.7
    system_prompt: |
      You are a compassionate dharma teacher offering wisdom and guidance.

# Caching Configuration
cache:
  enabled: true
  ttl_seconds: 3600  # 1 hour
  max_size: 1000  # Maximum cached responses

# Rate Limiting
rate_limits:
  z_ai_glm:
    max_requests: 100
    window: 60  # seconds
  openai:
    max_requests: 60
    window: 60
  anthropic:
    max_requests: 50
    window: 60

# Performance Settings
performance:
  request_timeout: 30  # seconds
  max_retries: 3
  retry_delay: 1  # seconds
  concurrent_requests: 5
```

## 🔧 Usage Examples

### Basic Prayer Generation
```python
from backend.core.services.enhanced_llm_service import enhanced_llm_service

request = GenerationRequest(
    prompt="Generate a prayer for healing and compassion",
    system_prompt="You are a Buddhist teacher creating heartfelt prayers.",
    max_tokens=200,
    temperature=0.8
)

response = await enhanced_llm_service.generate(request)
print(f"Generated prayer: {response.content}")
print(f"Model used: {response.model_used}")
print(f"Generation time: {response.generation_time:.2f}s")
```

### Teaching Generation with Context
```python
request = GenerationRequest(
    prompt="Explain the concept of impermanence (anicca)",
    context={
        "tradition": "theravada",
        "audience": "beginners",
        "length": "short"
    },
    max_tokens=500,
    temperature=0.6
)

response = await enhanced_llm_service.generate(request)
```

### Model Switching
```python
# Switch to local model
await enhanced_llm_service.switch_model("local_llama-3-8b-instruct")

# Check model status
status = await enhanced_llm_service.get_model_status()
print(f"Active model: {status['active_model']}")
print(f"Available models: {list(status['models'].keys())}")
```

## 🚀 Integration Points

### 1. Vajra Service Integration
Update `backend/core/services/vajra_service.py` to use the enhanced LLM service:

```python
from .enhanced_llm_service import enhanced_llm_service

class VajraStreamService:
    def __init__(self):
        # ... existing initialization ...
        self.llm_service = enhanced_llm_service
    
    async def generate_ai_prayer(self, intention: str, tradition: str = "universal") -> str:
        request = GenerationRequest(
            prompt=f"Generate a prayer for {intention}",
            system_prompt=f"Create a {tradition} style prayer",
            max_tokens=300,
            temperature=0.8
        )
        response = await self.llm_service.generate(request)
        return response.content
```

### 2. API Endpoint Integration
Create `backend/app/api/v1/endpoints/llm.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.services.enhanced_llm_service import enhanced_llm_service, GenerationRequest

router = APIRouter()

class PrayerRequest(BaseModel):
    intention: str
    tradition: str = "universal"
    length: str = "short"

@router.post("/generate-prayer")
async def generate_prayer(request: PrayerRequest):
    try:
        llm_request = GenerationRequest(
            prompt=f"Generate a {request.length} prayer for {request.intention}",
            system_prompt=f"Create {request.tradition} style prayers",
            max_tokens=500,
            temperature=0.8
        )
        
        response = await enhanced_llm_service.generate(llm_request)
        
        return {
            "status": "success",
            "prayer": response.content,
            "model_used": response.model_used,
            "generation_time": response.generation_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 📊 Performance Considerations

### Caching Strategy
- Cache common prayers and teachings
- TTL-based expiration
- LRU eviction for cache size management
- Context-aware caching (different system prompts)

### Rate Limiting
- Per-provider rate limits
- Intelligent request routing
- Automatic fallback on rate limit exceeded
- Exponential backoff for retries

### Model Selection Logic
- Priority-based routing for important requests
- Load balancing across available models
- Cost optimization (prefer local models)
- Quality vs speed trade-offs

## 🔒 Security & Privacy

### API Key Management
- Environment variable storage
- Key rotation support
- Secure key transmission
- Audit logging

### Content Filtering
- Input sanitization
- Output content validation
- Inappropriate content detection
- Safety layer integration

### Data Privacy
- Local processing for sensitive content
- No data retention for local models
- GDPR compliance
- User consent management

---

**Enhanced LLM Service Specification Complete** 🚀

This specification provides a comprehensive foundation for implementing the enhanced LLM service with Z AI GLM 4.6 integration, supporting multiple providers, intelligent routing, caching, and performance optimization.