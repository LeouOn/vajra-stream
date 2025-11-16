# Unified API Architecture for Vajra Stream

## Overview
This document describes the complete microservices architecture that connects all 22 core modules through a unified FastAPI backend.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│              Cross-Platform Launchers                    │
│         (vajra.sh / vajra.bat / vajra.py)               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                        │
│              (backend/app/main.py)                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │          API Routes (RESTful + WebSocket)        │  │
│  ├──────────────────────────────────────────────────┤  │
│  │  - Scalar Waves      - Radionics                 │  │
│  │  - Meridians         - Blessings                 │  │
│  │  - TTS/Audio         - Visualizations            │  │
│  │  - Time Cycles       - Astrology                 │  │
│  │  - LLM Integration   - Prayer Wheel              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                Service Layer                            │
│          (backend/core/services/)                       │
│                                                         │
│  Wraps each core module with async methods             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Core Modules (22)                       │
│                  (core/*.py)                            │
│                                                         │
│  12,915 lines of healing technology                    │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints Structure

### 1. Scalar Waves API (`/api/v1/scalar`)
**File**: `backend/app/api/v1/endpoints/scalar_waves.py`

**Endpoints**:
- `POST /api/v1/scalar/benchmark` - Run scalar wave benchmarks
- `POST /api/v1/scalar/generate` - Generate scalar wave stream
- `POST /api/v1/scalar/breathing-cycle` - Sacred breathing cycle
- `GET /api/v1/scalar/thermal-status` - Get thermal monitoring status
- `GET /api/v1/scalar/mops-metrics` - Get current MOPS performance

### 2. Radionics API (`/api/v1/radionics`)
**File**: `backend/app/api/v1/endpoints/radionics.py`

**Endpoints**:
- `POST /api/v1/radionics/broadcast` - Start radionics broadcast
- `POST /api/v1/radionics/healing-protocol` - Healing protocol
- `POST /api/v1/radionics/liberation-protocol` - Liberation protocol
- `GET /api/v1/radionics/intentions` - List available intentions
- `GET /api/v1/radionics/frequencies` - List sacred frequencies

### 3. Meridians & Anatomy API (`/api/v1/anatomy`)
**File**: `backend/app/api/v1/endpoints/anatomy.py`

**Endpoints**:
- `POST /api/v1/anatomy/visualize/chakras` - Generate chakra diagram
- `POST /api/v1/anatomy/visualize/meridians` - Generate meridian map
- `POST /api/v1/anatomy/visualize/central-channel` - Central channel diagram
- `GET /api/v1/anatomy/traditions` - List traditions (Taoist, Tibetan, Yogic)
- `GET /api/v1/anatomy/points` - Get acupuncture/chakra points

### 4. Blessings API (`/api/v1/blessings`)
**File**: `backend/app/api/v1/endpoints/blessings.py`

**Endpoints**:
- `POST /api/v1/blessings/generate-narrative` - Generate blessing narrative
- `POST /api/v1/blessings/compassionate` - Compassionate blessing
- `GET /api/v1/blessings/templates` - List blessing templates
- `GET /api/v1/blessings/traditions` - List spiritual traditions

### 5. TTS & Audio API (`/api/v1/tts`)
**File**: `backend/app/api/v1/endpoints/tts.py`

**Endpoints**:
- `POST /api/v1/tts/synthesize` - Text to speech synthesis
- `POST /api/v1/tts/mantra` - Mantra audio generation
- `POST /api/v1/tts/prayer-bowl` - Prayer bowl audio
- `GET /api/v1/tts/voices` - List available voices
- `GET /api/v1/tts/languages` - List supported languages

### 6. LLM Integration API (`/api/v1/llm`)
**File**: `backend/app/api/v1/endpoints/llm.py`

**Endpoints**:
- `POST /api/v1/llm/generate-prayer` - Generate prayer
- `POST /api/v1/llm/generate-teaching` - Generate dharma teaching
- `POST /api/v1/llm/meditation-guide` - Generate meditation instructions
- `GET /api/v1/llm/models` - List available LLM models
- `POST /api/v1/llm/switch-model` - Switch active model

### 7. Time Cycles API (`/api/v1/time-cycles`)
**File**: `backend/app/api/v1/endpoints/time_cycles.py`

**Endpoints**:
- `POST /api/v1/time-cycles/broadcast` - Start time cycle healing
- `GET /api/v1/time-cycles/current` - Get current time cycle info
- `GET /api/v1/time-cycles/planetary` - Get planetary positions
- `POST /api/v1/time-cycles/schedule` - Schedule healing session

### 8. Visualization API (`/api/v1/visualize`)
**File**: `backend/app/api/v1/endpoints/visualizations.py`

**Endpoints**:
- `POST /api/v1/visualize/rothko` - Generate Rothko-style art
- `POST /api/v1/visualize/sacred-geometry` - Generate sacred geometry
- `POST /api/v1/visualize/energy-field` - Visualize energy field
- `GET /api/v1/visualize/gallery` - List generated visualizations

### 9. Prayer Wheel API (`/api/v1/prayer-wheel`)
**File**: `backend/app/api/v1/endpoints/prayer_wheel.py`

**Endpoints**:
- `POST /api/v1/prayer-wheel/start` - Start prayer wheel
- `POST /api/v1/prayer-wheel/add-mantra` - Add mantra
- `GET /api/v1/prayer-wheel/status` - Get wheel status
- `POST /api/v1/prayer-wheel/stop` - Stop prayer wheel

### 10. Intelligent Composer API (`/api/v1/compose`)
**File**: `backend/app/api/v1/endpoints/composer.py`

**Endpoints**:
- `POST /api/v1/compose/generate` - Generate sacred music
- `POST /api/v1/compose/frequency-based` - Frequency-based composition
- `GET /api/v1/compose/scales` - List available scales
- `GET /api/v1/compose/instruments` - List available instruments

### 11. Healing Systems API (`/api/v1/healing`)
**File**: `backend/app/api/v1/endpoints/healing.py`

**Endpoints**:
- `POST /api/v1/healing/session` - Complete healing session
- `POST /api/v1/healing/custom` - Custom healing protocol
- `GET /api/v1/healing/systems` - List healing systems
- `POST /api/v1/healing/analyze` - Analyze healing needs

## WebSocket Endpoints

### Real-Time Streaming (`/ws/*`)
**File**: `backend/websocket/connection_manager.py`

**Channels**:
- `/ws/scalar-stream` - Real-time scalar wave data
- `/ws/audio-stream` - Real-time audio streaming
- `/ws/visualization-stream` - Real-time visualization updates
- `/ws/session-updates` - Healing session updates

## Cross-Platform Launchers

### 1. Unix/Linux/Mac: `vajra.sh`
```bash
#!/bin/bash
# Unified launcher for Unix systems
# Usage: ./vajra.sh [command] [options]
```

### 2. Windows: `vajra.bat`
```batch
@echo off
REM Unified launcher for Windows
REM Usage: vajra.bat [command] [options]
```

### 3. Python Universal: `vajra.py`
```python
#!/usr/bin/env python3
# Cross-platform Python launcher
# Usage: python vajra.py [command] [options]
```

## Service Layer

Each core module gets a service wrapper in `backend/core/services/`:

- `scalar_waves_service.py` - Wraps advanced_scalar_waves
- `radionics_service.py` - Wraps radionics_engine + integrated_scalar_radionics
- `anatomy_service.py` - Wraps energetic_anatomy + meridian_visualization
- `blessing_service.py` - Wraps blessing_narratives + compassionate_blessings
- `tts_service.py` - Wraps tts_engine + enhanced_tts + tts_integration
- `llm_service.py` - Wraps llm_integration
- `time_cycle_service.py` - Wraps time_cycle_broadcaster
- `visualization_service.py` - Wraps rothko_generator + energetic_visualization
- `prayer_wheel_service.py` - Wraps prayer_wheel
- `composer_service.py` - Wraps intelligent_composer
- `healing_service.py` - Wraps healing_systems
- `astrology_service.py` - Wraps astrology + astrocartography
- `audio_service.py` - Wraps audio_generator + enhanced_audio_generator

## Integration Tests

Comprehensive test suite in `tests/`:

- `test_api_endpoints.py` - Test all API endpoints
- `test_services.py` - Test all services
- `test_integration.py` - Test module integration
- `test_websockets.py` - Test WebSocket functionality
- `test_cross_platform.py` - Test launcher scripts

## Configuration

Unified configuration in `config/`:

- `config.yaml` - Main configuration
- `services.yaml` - Service configurations
- `.env.example` - Environment variables template

## Documentation Updates

- `API_REFERENCE.md` - Complete API documentation
- `QUICKSTART.md` - Quick start guide
- `DEPLOYMENT.md` - Deployment instructions
- `DEVELOPMENT.md` - Development guide

## Benefits

1. **Unified Access** - Single entry point for all 22 modules
2. **Cross-Platform** - Works on Windows, Mac, Linux
3. **Standardized** - RESTful API + WebSocket for real-time
4. **Testable** - Comprehensive test coverage
5. **Documented** - Complete API documentation
6. **Scalable** - Microservices architecture
7. **Maintainable** - Clean separation of concerns

## Next Steps

1. Implement all API endpoints
2. Create service wrappers
3. Build cross-platform launchers
4. Write comprehensive tests
5. Update all documentation
6. Deploy and validate

---

**May all beings benefit from this unified architecture!** 🙏
