# Comprehensive Implementation Guide for Z AI GLM 4.6 Integration

## 🎯 Overview

This guide provides step-by-step instructions for implementing the complete Z AI GLM 4.6 integration with LM Studio, advanced TTS, and AI-powered features in Vajra.Stream.

## 🚀 Quick Start Setup

### Phase 1: Environment Setup (15 minutes)

#### 1.1 Install LM Studio
```bash
# Download LM Studio from https://lmstudio.ai/
# Install for your operating system
# Launch LM Studio
```

#### 1.2 Load Models in LM Studio
1. Open LM Studio → Click search icon (🔍)
2. Search and download these models:
   - `OpenAI GPT-OSS-120B-Neo-Imatrix`
   - `Aquif-3.5-Max-42B-A3B-I1`
   - `NVIDIA Qwen3-Nemotron-32B-RLBFF`

3. Go to chat tab (💬) → Load your preferred model
4. Start server (ensure running on `http://127.0.0.1:1234`)

#### 1.3 Environment Configuration
```bash
# Create .env file in project root
cat > .env << EOF
# Z AI GLM 4.6 Configuration
Z_AI_API_KEY=your_z_ai_api_key_here

# OpenAI Fallback
OPENAI_API_KEY=your_openai_api_key_here

# ElevenLabs TTS
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Anthropic Fallback
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# LM Studio Settings
LM_STUDIO_BASE_URL=http://127.0.0.1:1234
EOF
```

#### 1.4 Python Dependencies
```bash
# Update requirements.txt with new dependencies
cat >> requirements.txt << EOF

# Enhanced LLM & TTS Dependencies
aiohttp>=3.8.0
pyyaml>=6.0
openai>=1.3.0
anthropic>=0.7.0
soundfile>=0.12.0
TTS>=0.22.0
librosa>=0.9.0
base64
EOF

# Install dependencies
pip install -r requirements.txt
```

### Phase 2: Configuration Files (10 minutes)

#### 2.1 Create AI Models Configuration
```bash
# Create config directory if not exists
mkdir -p config

# Create ai_models.yaml
cat > config/ai_models.yaml << 'EOF'
# Z AI GLM 4.6 Configuration (Primary Cloud Model)
z_ai_glm:
  model_name: "glm-4.6"
  api_endpoint: "https://api.z-ai.com/v1/chat/completions"
  api_key: "${Z_AI_API_KEY}"
  max_tokens: 4096
  temperature: 0.7
  system_prompt: |
    You are a wise dharma teacher versed in Buddhist philosophy, meditation practices, 
    and contemplative traditions. You speak with clarity, compassion, and depth. 
    Your teachings are rooted in the Buddhadharma but accessible to all beings.
    You draw from Theravada, Mahayana, and Vajrayana traditions as appropriate.

# LM Studio Configuration (Primary Local Models)
lm_studio:
  base_url: "http://127.0.0.1:1234"
  timeout: 30
  max_retries: 3
  max_tokens: 4096
  temperature: 0.7
  
  preferred_models:
    - "openai_gpt-oss-120b-neo-imatrix"
    - "aquif-3.5-max-42b-a3b-i1"
    - "nvidia_qwen3-nemotron-32b-rlbff"

# Fallback Cloud Models
fallback_models:
  - provider: "openai"
    model: "gpt-4o-mini"
    api_key: "${OPENAI_API_KEY}"
    max_tokens: 4096
    temperature: 0.7
  - provider: "anthropic"
    model: "claude-3-5-haiku-20241022"
    api_key: "${ANTHROPIC_API_KEY}"
    max_tokens: 4096
    temperature: 0.7

# Model Selection Strategy
model_selection:
  strategy: "prefer_local"
  request_priorities:
    prayer_generation: ["lm_studio", "z_ai_glm", "openai", "anthropic"]
    teaching_generation: ["z_ai_glm", "lm_studio", "anthropic", "openai"]
    meditation_guidance: ["lm_studio", "z_ai_glm", "anthropic", "openai"]

# Performance Settings
performance:
  cache_enabled: true
  cache_ttl_seconds: 3600
  max_cache_size: 1000
  request_timeout: 30
  max_concurrent_requests: 5
EOF
```

#### 2.2 Create TTS Voices Configuration
```bash
# Create tts_voices.yaml
cat > config/tts_voices.yaml << 'EOF'
# OpenAI TTS Configuration
openai_tts:
  api_key: "${OPENAI_API_KEY}"
  model: "tts-1-hd"
  default_speed: 1.0
  output_format: "mp3"
  
  voices:
    compassionate_male:
      voice_id: "onyx"
      language: "en"
      gender: "male"
      age: "adult"
      style: "compassionate"
    compassionate_female:
      voice_id: "nova"
      language: "en"
      gender: "female"
      age: "adult"
      style: "compassionate"

# ElevenLabs Configuration
elevenlabs:
  api_key: "${ELEVENLABS_API_KEY}"
  model: "eleven_multilingual_v2"
  output_format: "mp3"
  default_emotional_range: 0.7
  
  voices:
    rachel:
      voice_id: "rachel"
      language: "en"
      gender: "female"
      age: "adult"
      style: "compassionate"
      emotional_range: 0.8
    adam:
      voice_id: "adam"
      language: "en"
      gender: "male"
      age: "adult"
      style: "gentle"
      emotional_range: 0.7

# pyttsx3 Fallback Configuration
pyttsx3:
  enabled: true
  rate: 150
  volume: 0.9
  voice_index: 0

# Audio Processing Settings
audio_processing:
  sample_rate: 22050
  bit_depth: 16
  channels: 1
  format: "wav"
  
  frequency_optimization:
    enabled: true
    target_frequencies:
      - 432
      - 528
      - 741
      - 963
    optimization_strength: 0.05

# Caching Settings
cache:
  enabled: true
  ttl_seconds: 86400
  max_size: 500
  storage_path: "./cache/tts"

# Quality Settings
quality:
  default_emotional_tone: "compassionate"
  default_speed: 1.0
  default_pitch: 1.0
  
  language_settings:
    en:
      preferred_provider: "elevenlabs"
      emotional_range: 0.7
    sa:
      preferred_provider: "coqui_tts"
      emotional_range: 0.3
    bo:
      preferred_provider: "coqui_tts"
      emotional_range: 0.2
EOF
```

### Phase 3: Backend Implementation (30 minutes)

#### 3.1 Create Enhanced Services
```bash
# Create service files
mkdir -p backend/core/services
mkdir -p backend/app/api/v1/endpoints

# Create enhanced LLM service
# (Copy from ENHANCED_LLM_SERVICE_SPECIFICATION.md)

# Create advanced TTS service  
# (Copy from ADVANCED_TTS_INTEGRATION_SPECIFICATION.md)

# Create AI audio analyzer
# (Copy from AI_AUDIO_ANALYZER_SPECIFICATION.md)

# Create intelligent session manager
# (Copy from INTELLIGENT_SESSION_MANAGER_SPECIFICATION.md)
```

#### 3.2 Create API Endpoints
```bash
# Create API endpoint files
# (Copy from BACKEND_API_ENDPOINTS_SPECIFICATION.md)

# Update main.py to include new routers
cat >> backend/app/main.py << 'EOF'

# Include new AI routers
from app.api.v1.endpoints import llm, tts, ai_analysis

app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])
app.include_router(tts.router, prefix="/api/v1/tts", tags=["tts"])
app.include_router(ai_analysis.router, prefix="/api/v1/ai", tags=["ai_analysis"])
EOF
```

#### 3.3 Update Vajra Service
```python
# Update backend/core/services/vajra_service.py
# Add imports:
from .enhanced_llm_service import enhanced_llm_service
from .advanced_tts_service import advanced_tts_service

# Update __init__ method:
class VajraStreamService:
    def __init__(self):
        # ... existing code ...
        self.llm_service = enhanced_llm_service
        self.tts_service = advanced_tts_service
        
        # Add AI-powered methods
    async def generate_ai_prayer(self, intention: str, tradition: str = "universal") -> str:
        """Generate prayer using enhanced LLM service"""
        from .enhanced_llm_service import GenerationRequest
        
        request = GenerationRequest(
            prompt=f"Generate a prayer for {intention}",
            system_prompt=f"Create {tradition} style prayers",
            context={"request_type": "prayer_generation"},
            max_tokens=300,
            temperature=0.8
        )
        
        response = await self.llm_service.generate(request)
        return response.content
    
    async def synthesize_guided_meditation(self, theme: str, duration: int = 10) -> bytes:
        """Create guided meditation with speech synthesis"""
        # Generate script
        script = await self.generate_ai_prayer(f"guided meditation on {theme}", "meditation")
        
        # Synthesize speech
        from .advanced_tts_service import TTSRequest, SacredLanguage
        tts_request = TTSRequest(
            text=script,
            language=SacredLanguage.ENGLISH,
            emotional_tone="gentle",
            speed=0.9,
            optimize_for_frequency=432
        )
        
        response = await self.tts_service.synthesize(tts_request)
        return response.audio_data
```

### Phase 4: Frontend Integration (20 minutes)

#### 4.1 Create AI Service Client
```javascript
// frontend/src/services/aiService.js
export class AIService {
  constructor() {
    this.baseURL = '/api/v1';
  }

  async generatePrayer(intention, tradition = 'universal', options = {}) {
    const response = await fetch(`${this.baseURL}/llm/generate-prayer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        intention,
        tradition,
        emotional_tone: options.emotionalTone || 'compassionate',
        length: options.length || 'short',
        use_local_model: options.useLocalModel !== false
      })
    });
    
    const result = await response.json();
    return {
      content: result.content,
      model: result.model_used,
      provider: result.provider,
      isLocal: result.metadata?.is_local || false,
      cached: result.cached
    };
  }

  async synthesizeSpeech(text, options = {}) {
    const response = await fetch(`${this.baseURL}/tts/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        language: options.language || 'en',
        emotional_tone: options.emotionalTone || 'compassionate',
        provider_preference: options.provider || 'elevenlabs',
        optimize_for_frequency: options.optimizeForFrequency,
        output_format: options.format || 'mp3'
      })
    });
    
    const result = await response.json();
    return {
      audioData: result.audio_data,
      duration: result.duration,
      voice: result.voice_used,
      provider: result.provider,
      sampleRate: result.sample_rate
    };
  }

  async createGuidedMeditation(theme, duration = 10, options = {}) {
    const response = await fetch(`${this.baseURL}/tts/guided-meditation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        theme,
        duration_minutes: duration,
        language: options.language || 'en',
        voice_style: options.voiceStyle || 'gentle',
        include_background_frequency: options.includeBackgroundFrequency !== false,
        background_frequency: options.backgroundFrequency || 432
      })
    });
    
    return await response.json();
  }

  async getModelStatus() {
    const response = await fetch(`${this.baseURL}/llm/model-status`);
    return await response.json();
  }

  async switchModel(modelId) {
    const response = await fetch(`${this.baseURL}/llm/switch-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId })
    });
    
    return await response.json();
  }
}

export const aiService = new AIService();
```

#### 4.2 Create AI Control Panel Component
```jsx
// frontend/src/components/UI/AIControlPanel.jsx
import React, { useState, useEffect } from 'react';
import { Brain, Settings, Volume2, Globe } from 'lucide-react';
import { aiService } from '../../services/aiService';

const AIControlPanel = () => {
  const [modelStatus, setModelStatus] = useState(null);
  const [selectedModel, setSelectedModel] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [prayerIntention, setPrayerIntention] = useState('');
  const [generatedPrayer, setGeneratedPrayer] = useState('');

  useEffect(() => {
    loadModelStatus();
  }, []);

  const loadModelStatus = async () => {
    try {
      const status = await aiService.getModelStatus();
      setModelStatus(status);
      setSelectedModel(status.active_model);
    } catch (error) {
      console.error('Failed to load model status:', error);
    }
  };

  const handleGeneratePrayer = async () => {
    if (!prayerIntention.trim()) return;
    
    setIsGenerating(true);
    try {
      const result = await aiService.generatePrayer(prayerIntention, 'buddhist', {
        emotionalTone: 'compassionate',
        length: 'short',
        useLocalModel: true
      });
      
      setGeneratedPrayer(result.content);
      console.log('Generated with:', result.model, result.provider);
    } catch (error) {
      console.error('Prayer generation failed:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSwitchModel = async (modelId) => {
    try {
      await aiService.switchModel(modelId);
      setSelectedModel(modelId);
      await loadModelStatus(); // Refresh status
    } catch (error) {
      console.error('Model switch failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Brain className="w-5 h-5 mr-2 text-vajra-cyan" />
          AI Model Control
        </h3>
        
        {/* Model Status */}
        {modelStatus && (
          <div className="mb-4 p-4 bg-gray-700 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">Active Model:</span>
              <span className="text-sm text-vajra-cyan font-mono">
                {selectedModel}
              </span>
            </div>
            
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">LM Studio:</span>
              <span className={`text-sm ${modelStatus.lm_studio_available ? 'text-green-400' : 'text-red-400'}`}>
                {modelStatus.lm_studio_available ? 'Available' : 'Unavailable'}
              </span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Total Models:</span>
              <span className="text-sm text-gray-300">{modelStatus.total_models}</span>
            </div>
          </div>
        )}

        {/* Model Selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Available Models:</label>
          <select 
            value={selectedModel}
            onChange={(e) => handleSwitchModel(e.target.value)}
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-vajra-cyan focus:border-transparent"
          >
            {modelStatus?.available_models && Object.entries(modelStatus.available_models).map(([id, config]) => (
              <option key={id} value={id}>
                {config.model_name} ({config.provider}) {config.is_local ? '🏠' : '☁️'}
              </option>
            ))}
          </select>
        </div>

        {/* Prayer Generation */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Prayer Intention:</label>
            <input
              type="text"
              value={prayerIntention}
              onChange={(e) => setPrayerIntention(e.target.value)}
              placeholder="e.g., healing, peace, compassion"
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-vajra-cyan focus:border-transparent"
            />
          </div>
          
          <button
            onClick={handleGeneratePrayer}
            disabled={isGenerating || !prayerIntention.trim()}
            className="w-full vajra-button vajra-button-primary flex items-center justify-center"
          >
            {isGenerating ? (
              <>
                <div className="spinner w-4 h-4 mr-2" />
                Generating...
              </>
            ) : (
              <>
                <Brain className="w-4 h-4 mr-2" />
                Generate Prayer
              </>
            )}
          </button>
        </div>

        {/* Generated Prayer Display */}
        {generatedPrayer && (
          <div className="mt-4 p-4 bg-gray-700 rounded-lg">
            <h4 className="text-sm font-semibold mb-2 text-vajra-cyan">Generated Prayer:</h4>
            <p className="text-gray-200 leading-relaxed">{generatedPrayer}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIControlPanel;
```

#### 4.3 Update Main App Component
```jsx
// Update frontend/src/App.jsx
import AIControlPanel from './components/UI/AIControlPanel';

// Add to existing imports and include in sidebar
<div className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-gray-800 border-r border-gray-700 transition-all duration-300 overflow-hidden flex flex-col`}>
  <div className="flex-1 overflow-y-auto p-6 space-y-6">
    {/* Existing components */}
    <ControlPanel ... />
    <SessionManager ... />
    
    {/* New AI Control Panel */}
    <AIControlPanel />
  </div>
</div>
```

### Phase 5: Testing & Validation (15 minutes)

#### 5.1 Backend Testing
```bash
# Test LM Studio connection
curl -X GET "http://127.0.0.1:1234/v1/models"

# Test enhanced LLM service
curl -X POST "http://localhost:8000/api/v1/llm/generate-prayer" \
  -H "Content-Type: application/json" \
  -d '{
    "intention": "peace and healing",
    "tradition": "buddhist",
    "use_local_model": true
  }'

# Test TTS service
curl -X POST "http://localhost:8000/api/v1/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "May all beings be happy",
    "language": "en",
    "provider_preference": "elevenlabs"
  }'
```

#### 5.2 Frontend Testing
```javascript
// Test in browser console
import { aiService } from './src/services/aiService.js';

// Test prayer generation
aiService.generatePrayer('compassion', 'buddhist')
  .then(result => console.log('Prayer:', result))
  .catch(error => console.error('Error:', error));

// Test speech synthesis
aiService.synthesizeSpeech('Hello world', { provider: 'openai' })
  .then(result => {
    const audio = new Audio(`data:audio/mp3;base64,${result.audioData}`);
    audio.play();
  });
```

## 🔧 Advanced Configuration Options

### Performance Optimization
```yaml
# config/ai_models.yaml - Performance section
performance:
  # Concurrent requests
  max_concurrent_requests: 5
  
  # Request batching
  batch_size: 3
  batch_timeout: 10
  
  # Memory management
  max_memory_usage: "2GB"
  gc_threshold: 1000
  
  # Rate limiting
  rate_limits:
    z_ai_glm: { max_requests: 100, window: 60 }
    lm_studio: { max_requests: 50, window: 60 }
    openai: { max_requests: 60, window: 60 }
```

### Cost Management
```yaml
# config/ai_models.yaml - Cost optimization
cost_optimization:
  # Budget limits
  daily_budget_limit: 10.0  # USD
  monthly_budget_limit: 200.0
  
  # Cost tracking
  cost_tracking: true
  budget_alert_threshold: 0.8
  
  # Provider costs (per 1K tokens)
  cloud_model_costs:
    z_ai_glm: 0.001
    openai: 0.002
    anthropic: 0.003
  
  # Optimization strategy
  prefer_local_models: true
  cost_vs_quality_balance: 0.7  # 0.0 = cost only, 1.0 = quality only
```

### Sacred Language Support
```yaml
# config/tts_voices.yaml - Sacred languages
sacred_languages:
  sanskrit:
    provider: "coqui_tts"
    model: "sanskrit-mantra-v1"
    pronunciation_guide: "Classical Sanskrit pronunciation"
    
  tibetan:
    provider: "elevenlabs"
    voice: "tibetan-monk"
    chanting_style: "Traditional Tibetan chanting"
    
  pali:
    provider: "coqui_tts"
    model: "pali-sutra-v1"
    translation_source: "Theravada tradition"
```

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

#### LM Studio Connection Issues
```bash
# Check if LM Studio is running
curl -X GET "http://127.0.0.1:1234/v1/models"

# If connection fails:
1. Verify LM Studio server is running
2. Check port 1234 is not blocked
3. Restart LM Studio server
4. Verify model is loaded in chat tab
```

#### API Key Issues
```bash
# Test API keys
python -c "
import os
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

# Test OpenAI
try:
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    print('✅ OpenAI API key valid')
except Exception as e:
    print(f'❌ OpenAI API key error: {e}')

# Test Anthropic
try:
    client = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    print('✅ Anthropic API key valid')
except Exception as e:
    print(f'❌ Anthropic API key error: {e}')
"
```

#### Audio Quality Issues
```bash
# Test audio synthesis
python -c "
import asyncio
from backend.core.services.advanced_tts_service import advanced_tts_service, TTSRequest, SacredLanguage

async def test_tts():
    request = TTSRequest(
        text='Test audio synthesis',
        language=SacredLanguage.ENGLISH,
        provider_preference='pyttsx3'  # Test fallback first
    )
    
    response = await advanced_tts_service.synthesize(request)
    print(f'✅ Audio generated: {len(response.audio_data)} bytes')
    print(f'Duration: {response.duration}s')
    print(f'Provider: {response.provider.value}')

asyncio.run(test_tts())
"
```

#### Performance Issues
```yaml
# Optimize for lower-end systems
performance:
  max_concurrent_requests: 2  # Reduce from 5
  cache_ttl_seconds: 7200      # Increase caching
  request_timeout: 60           # Increase timeout
  
# Use lighter models
model_selection:
  strategy: "cost_optimized"
  preferred_local_models:
    - "aquif-3.5-max-42b-a3b-i1"  # Smaller than 120B
```

## 📊 Monitoring & Analytics

### System Health Monitoring
```python
# backend/core/services/health_monitor.py
class HealthMonitor:
    async def check_lm_studio_health(self):
        """Monitor LM Studio availability"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://127.0.0.1:1234/v1/models', timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    async def check_api_key_health(self):
        """Validate API keys"""
        # Check each provider API key
        pass
    
    async def monitor_performance(self):
        """Track response times and success rates"""
        # Log performance metrics
        pass
```

### Usage Analytics
```python
# backend/core/services/usage_analytics.py
class UsageAnalytics:
    def track_llm_usage(self, provider, model, tokens, response_time):
        """Track LLM usage for analytics"""
        pass
    
    def track_tts_usage(self, provider, voice, duration, characters):
        """Track TTS usage for analytics"""
        pass
    
    def generate_cost_report(self, period='daily'):
        """Generate cost and usage reports"""
        pass
```

## 🎯 Success Metrics

### Implementation Checklist
- [ ] LM Studio installed and models loaded
- [ ] Environment variables configured
- [ ] Configuration files created
- [ ] Backend services implemented
- [ ] API endpoints created
- [ ] Frontend components updated
- [ ] Basic testing completed
- [ ] Integration testing passed
- [ ] Performance optimization applied
- [ ] Error handling implemented
- [ ] Documentation updated

### Performance Targets
- **Prayer Generation**: < 3 seconds
- **Speech Synthesis**: < 5 seconds
- **Model Switching**: < 1 second
- **API Response Time**: < 200ms
- **Memory Usage**: < 2GB
- **Cost Efficiency**: > 80% local model usage

### Quality Targets
- **Prayer Relevance**: > 90% user satisfaction
- **Voice Naturalness**: > 4.5/5 user rating
- **Language Accuracy**: > 95% correct pronunciation
- **System Reliability**: > 99% uptime
- **Error Recovery**: < 5 seconds to fallback

## 🚀 Next Steps

### Immediate Actions
1. **Complete Implementation**: Follow this guide step-by-step
2. **Test Integration**: Verify all components work together
3. **Performance Tune**: Optimize for your hardware
4. **User Testing**: Get feedback from real users
5. **Monitor Usage**: Track costs and performance

### Future Enhancements
1. **Voice Cloning**: Implement personalized voice models
2. **Real-time Translation**: Add multi-language support
3. **Advanced Analytics**: ML-powered usage optimization
4. **Mobile Support**: Extend to React Native app
5. **Cloud Deployment**: Scale for multiple users

---

**Implementation Guide Complete** 🚀

This comprehensive guide provides everything needed to successfully integrate Z AI GLM 4.6 with LM Studio and advanced TTS into Vajra.Stream, creating a powerful, intelligent sacred technology platform.