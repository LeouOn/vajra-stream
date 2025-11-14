"""
Enhanced LLM Service for Vajra.Stream
Integrates Z AI GLM 4.6 with LM Studio and intelligent routing
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
except ImportError as e:
    logging.warning(f"Some dependencies not available: {e}")

class ModelProvider(Enum):
    Z_AI_GLM = "z_ai_glm"
    LM_STUDIO = "lm_studio"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

@dataclass
class LMStudioConfig:
    base_url: str = "http://127.0.0.1:1234"
    api_key: str = "not-required"
    timeout: int = 30
    max_retries: int = 3

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
    preferred_provider: Optional[ModelProvider] = None

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
    Enhanced LLM service with LM Studio integration
    Supports Z AI GLM 4.6 (cloud) + LM Studio (local) + fallback APIs
    """
    
    def __init__(self, config_path: str = "config/ai_models.yaml"):
        self.config_path = config_path
        self.models: Dict[str, ModelConfig] = {}
        self.active_model: Optional[str] = None
        self.cache: Dict[str, GenerationResponse] = {}
        self.cache_ttl = 3600  # 1 hour
        self.request_queue = asyncio.Queue()
        self.rate_limits: Dict[str, Dict] = {}
        
        # LM Studio configuration
        self.lm_studio_config = LMStudioConfig()
        self.lm_studio_client = None
        
        # Initialize clients
        self.z_ai_client = None
        self.openai_client = None
        self.anthropic_client = None
        
        # Load configuration
        self._load_configuration()
        self._initialize_clients()
        
        # Start LM Studio health check
        asyncio.create_task(self._monitor_lm_studio())
        
        logging.info("Enhanced LLM Service with LM Studio initialized")
    
    def _load_configuration(self):
        """Load model configurations from YAML file"""
        try:
            config_path = Path(self.config_path)
            if not config_path.exists():
                # Create default config if doesn't exist
                self._create_default_config(config_path)
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load Z AI GLM 4.6 as primary cloud model
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
            
            # Load LM Studio configuration
            if 'lm_studio' in config:
                lm_config = config['lm_studio']
                self.lm_studio_config = LMStudioConfig(
                    base_url=lm_config.get('base_url', 'http://127.0.0.1:1234'),
                    timeout=lm_config.get('timeout', 30),
                    max_retries=lm_config.get('max_retries', 3)
                )
                
                # Add available LM Studio models
                preferred_models = lm_config.get('preferred_models', [])
                for model_name in preferred_models:
                    self.models[f"lm_studio_{model_name}"] = ModelConfig(
                        provider=ModelProvider.LM_STUDIO,
                        model_name=model_name,
                        api_endpoint=f"{self.lm_studio_config.base_url}/v1",
                        max_tokens=lm_config.get('max_tokens', 4096),
                        temperature=lm_config.get('temperature', 0.7)
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
            
            # Set default active model (prefer local, then cloud)
            lm_studio_models = [k for k in self.models.keys() if k.startswith('lm_studio_')]
            if lm_studio_models:
                self.active_model = lm_studio_models[0]  # Use first available local model
            elif 'z_ai_glm_4.6' in self.models:
                self.active_model = 'z_ai_glm_4.6'
            else:
                self.active_model = list(self.models.keys())[0]
            
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            # Fallback to basic configuration
            self.models['fallback'] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name='gpt-4o-mini',
                api_key=os.getenv('OPENAI_API_KEY')
            )
            self.active_model = 'fallback'
    
    def _create_default_config(self, config_path: Path):
        """Create default configuration file"""
        default_config = {
            'z_ai_glm': {
                'model_name': 'glm-4.6',
                'api_endpoint': 'https://api.z-ai.com/v1/chat/completions',
                'max_tokens': 4096,
                'temperature': 0.7,
                'system_prompt': '''You are a wise dharma teacher versed in Buddhist philosophy, 
meditation practices, and contemplative traditions. You speak with clarity, compassion, and depth. 
Your teachings are rooted in the Buddhadharma but accessible to all beings.
You draw from Theravada, Mahayana, and Vajrayana traditions as appropriate.'''
            },
            'lm_studio': {
                'base_url': 'http://127.0.0.1:1234',
                'timeout': 30,
                'max_retries': 3,
                'max_tokens': 4096,
                'temperature': 0.7,
                'preferred_models': [
                    'openai_gpt-oss-120b-neo-imatrix',
                    'aquif-3.5-max-42b-a3b-i1',
                    'nvidia_qwen3-nemotron-32b-rlbff'
                ]
            },
            'fallback_models': [
                {
                    'provider': 'openai',
                    'model': 'gpt-4o-mini',
                    'api_key': '${OPENAI_API_KEY}',
                    'max_tokens': 4096,
                    'temperature': 0.7
                },
                {
                    'provider': 'anthropic',
                    'model': 'claude-3-5-haiku-20241022',
                    'api_key': '${ANTHROPIC_API_KEY}',
                    'max_tokens': 4096,
                    'temperature': 0.7
                }
            ]
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        logging.info(f"Created default configuration at {config_path}")
    
    def _initialize_clients(self):
        """Initialize API clients for all configured models"""
        for model_id, config in self.models.items():
            try:
                if config.provider == ModelProvider.Z_AI_GLM and config.api_key:
                    self.z_ai_client = aiohttp.ClientSession()
                elif config.provider == ModelProvider.LM_STUDIO:
                    # Initialize LM Studio client (OpenAI-compatible)
                    self.lm_studio_client = AsyncOpenAI(
                        api_key=self.lm_studio_config.api_key,
                        base_url=self.lm_studio_config.base_url
                    )
                elif config.provider == ModelProvider.OPENAI and config.api_key:
                    self.openai_client = AsyncOpenAI(api_key=config.api_key)
                elif config.provider == ModelProvider.ANTHROPIC and config.api_key:
                    self.anthropic_client = AsyncAnthropic(api_key=config.api_key)
            except Exception as e:
                logging.error(f"Failed to initialize client for {model_id}: {e}")
    
    async def _monitor_lm_studio(self):
        """Monitor LM Studio availability"""
        while True:
            try:
                available_models = await self._check_lm_studio_health()
                if not available_models:
                    logging.warning("LM Studio not available, switching to cloud models")
                    if self.active_model and self.active_model.startswith('lm_studio_'):
                        # Switch to cloud model
                        if 'z_ai_glm_4.6' in self.models:
                            self.active_model = 'z_ai_glm_4.6'
                        else:
                            self.active_model = list(self.models.keys())[0]
                else:
                    # Update available models
                    self._update_lm_studio_models(available_models)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logging.error(f"LM Studio monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_lm_studio_health(self) -> List[str]:
        """Check if LM Studio is available and get available models"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.lm_studio_config.base_url}/v1/models",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['id'] for model in data.get('data', [])]
        except Exception as e:
            logging.debug(f"LM Studio health check failed: {e}")
        return []
    
    def _update_lm_studio_models(self, available_models: List[str]):
        """Update available LM Studio models"""
        # Remove old LM Studio models
        old_lm_models = [k for k in self.models.keys() if k.startswith('lm_studio_')]
        for old_model in old_lm_models:
            if old_model not in [f"lm_studio_{model}" for model in available_models]:
                del self.models[old_model]
        
        # Add new LM Studio models
        for model_name in available_models:
            model_id = f"lm_studio_{model_name}"
            if model_id not in self.models:
                self.models[model_id] = ModelConfig(
                    provider=ModelProvider.LM_STUDIO,
                    model_name=model_name,
                    api_endpoint=f"{self.lm_studio_config.base_url}/v1",
                    max_tokens=4096,
                    temperature=0.7
                )
    
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate text using enhanced LLM service with LM Studio
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
            elif model_config.provider == ModelProvider.LM_STUDIO:
                response = await self._generate_lm_studio(request, model_config)
            elif model_config.provider == ModelProvider.OPENAI:
                response = await self._generate_openai(request, model_config)
            elif model_config.provider == ModelProvider.ANTHROPIC:
                response = await self._generate_anthropic(request, model_config)
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
        
        # Use preferred provider if specified
        if request.preferred_provider:
            provider_models = [k for k, v in self.models.items() 
                              if v.provider == request.preferred_provider]
            if provider_models:
                return provider_models[0]
        
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
    
    async def _generate_lm_studio(self, request: GenerationRequest, config: ModelConfig) -> GenerationResponse:
        """Generate using LM Studio (OpenAI-compatible API)"""
        messages = []
        if request.system_prompt or config.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt or config.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        response = await self.lm_studio_client.chat.completions.create(
            model=config.model_name,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        return GenerationResponse(
            content=response.choices[0].message.content,
            model_used=config.model_name,
            provider=ModelProvider.LM_STUDIO,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            metadata={"response_id": response.id, "local_model": True}
        )
    
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
        lm_studio_available = await self._check_lm_studio_health()
        
        status = {
            "active_model": self.active_model,
            "total_models": len(self.models),
            "cache_size": len(self.cache),
            "lm_studio_available": len(lm_studio_available) > 0,
            "lm_studio_models": lm_studio_available,
            "models": {}
        }
        
        for model_id, config in self.models.items():
            status["models"][model_id] = {
                "provider": config.provider.value,
                "model_name": config.model_name,
                "available": True,
                "rate_limited": self._is_rate_limited(model_id),
                "is_local": config.provider == ModelProvider.LM_STUDIO
            }
        
        return status

# Global instance
enhanced_llm_service = EnhancedLLMService()