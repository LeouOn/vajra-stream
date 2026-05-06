# Vajra.Stream Backend Implementation Guide

## 🏗️ FastAPI Backend Setup

### 1. Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection and models
│   └── api/
│       ├── __init__.py
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── endpoints/
│       │   │   ├── __init__.py
│       │   │   ├── audio.py          # Audio generation control
│       │   │   ├── sessions.py       # Session management
│       │   │   ├── astrology.py      # Astrological calculations
│       │   │   ├── prayers.py        # Prayer wheel control
│       │   │   ├── llm.py           # LLM content generation
│       │   │   ├── hardware.py       # Hardware control
│       │   │   ├── visuals.py        # Visual generation
│       │   │   └── websocket.py     # Real-time streaming
│       │   └── api.py              # API router aggregation
│       └── deps.py                # Dependencies (auth, db, etc.)
├── core/
│   ├── __init__.py
│   ├── services/
│   │   ├── audio_service.py     # Audio generation wrapper
│   │   ├── session_service.py    # Session management
│   │   ├── astrology_service.py  # Astrological calculations
│   │   ├── prayer_service.py     # Prayer wheel logic
│   │   ├── llm_service.py       # LLM integration
│   │   ├── hardware_service.py   # Hardware control
│   │   └── visual_service.py    # Visual generation
│   └── models/
│       ├── __init__.py
│       ├── session.py           # Session data models
│       ├── user.py              # User configuration
│       ├── audio.py             # Audio configuration
│       └── hardware.py          # Hardware status
├── websocket/
│   ├── __init__.py
│   ├── connection_manager.py   # WebSocket connection handling
│   └── streaming.py          # Real-time data streaming
└── requirements.txt
```

### 2. Dependencies (requirements.txt)
```txt
# Web Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0

# Database
sqlalchemy>=2.0.0
alembic
sqlite3

# Data Validation
pydantic>=2.5.0
pydantic-settings

# WebSocket
websockets>=12.0

# Audio Processing
numpy>=1.24.0
scipy>=1.10.0
sounddevice>=0.4.6

# Image Processing
pillow>=10.0.0
opencv-python>=4.8.0

# LLM Integration
openai>=1.3.0
anthropic>=0.7.0
llama-cpp-python>=0.2.0

# Astrology
astropy>=5.3.0
astroquery>=0.4.6

# Utilities
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-dotenv>=1.0.0
```

### 3. Main Application (app/main.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.config import settings
from websocket.connection_manager import connection_manager

app = FastAPI(
    title="Vajra.Stream API",
    description="Sacred Technology Platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages
            await connection_manager.handle_message(websocket, data)
    except:
        connection_manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"message": "Vajra.Stream API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### 4. Audio Service (core/services/audio_service.py)
```python
import asyncio
from typing import List, Optional
import numpy as np
from core.audio_generator import ScalarWaveGenerator
from core.enhanced_audio_generator import EnhancedAudioGenerator

class AudioService:
    def __init__(self):
        self.generator = EnhancedAudioGenerator()
        self.current_session = None
        self.is_playing = False
        
    async def generate_audio(self, config: dict):
        """Generate audio based on configuration"""
        audio_type = config.get("type", "prayer_bowl")
        frequency = config.get("frequency", 432)
        duration = config.get("duration", 300)
        intention = config.get("intention", "peace")
        
        if audio_type == "prayer_bowl":
            return self.generator.generate_prayer_bowl_tone(
                frequency=frequency,
                duration=duration,
                pure_sine=config.get("pure_sine", False)
            )
        elif audio_type == "solfeggio":
            return self.generator.generate_solfeggio_tone(frequency, duration)
        elif audio_type == "binaural":
            base_freq = config.get("base_frequency", 432)
            beat_freq = config.get("beat_frequency", 7.83)
            return self.generator.generate_binaural_beat(base_freq, beat_freq, duration)
        
    async def play_audio(self, audio_data):
        """Play audio data"""
        self.is_playing = True
        # Implementation for audio playback
        # This would integrate with sounddevice or similar
        
    async def stop_audio(self):
        """Stop current audio playback"""
        self.is_playing = False
        
    def get_spectrum(self):
        """Get current frequency spectrum"""
        # Implementation for real-time spectrum analysis
        return {"frequencies": [7.83, 136.1, 528], "amplitudes": [0.8, 0.6, 0.4]}
        
    def get_active_frequencies(self):
        """Get currently active frequencies"""
        return [7.83, 136.1, 528]

# Global audio service instance
audio_service = AudioService()
```

### 5. Session Service (core/services/session_service.py)
```python
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from core.models.session import Session, SessionCreate, SessionUpdate

class SessionService:
    def __init__(self):
        self.active_sessions: Dict[str, Session] = {}
        
    async def create_session(self, session_data: SessionCreate) -> Session:
        """Create new session"""
        session = Session(
            id=str(uuid.uuid4()),
            created_at=datetime.now(),
            **session_data.dict()
        )
        self.active_sessions[session.id] = session
        return session
        
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
        
    async def update_session(self, session_id: str, update_data: SessionUpdate) -> Optional[Session]:
        """Update session"""
        session = self.active_sessions.get(session_id)
        if session:
            for key, value in update_data.dict(exclude_unset=True).items():
                setattr(session, key, value)
            session.updated_at = datetime.now()
        return session
        
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False
        
    async def start_session(self, session_id: str) -> Optional[Session]:
        """Start session"""
        session = self.active_sessions.get(session_id)
        if session:
            session.status = "running"
            session.started_at = datetime.now()
        return session
        
    async def stop_session(self, session_id: str) -> Optional[Session]:
        """Stop session"""
        session = self.active_sessions.get(session_id)
        if session:
            session.status = "stopped"
            session.stopped_at = datetime.now()
        return session

# Global session service instance
session_service = SessionService()
```

### 6. WebSocket Manager (websocket/connection_manager.py)
```python
import json
import asyncio
from typing import List, Dict
from fastapi import WebSocket
from core.services.audio_service import audio_service
from core.services.session_service import session_service

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, dict] = {}
        
    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {"session_id": None}
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_data:
            del self.connection_data[websocket]
            
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        await websocket.send_text(json.dumps(message))
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSockets"""
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Connection closed, remove it
                self.disconnect(connection)
                
    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe_audio":
                # Subscribe to audio data updates
                await self.start_audio_streaming(websocket)
            elif message_type == "start_session":
                # Start a session
                session_id = data.get("session_id")
                await session_service.start_session(session_id)
            elif message_type == "stop_session":
                # Stop a session
                session_id = data.get("session_id")
                await session_service.stop_session(session_id)
                
        except json.JSONDecodeError:
            await self.send_personal_message(
                {"error": "Invalid JSON message"}, websocket
            )
            
    async def start_audio_streaming(self, websocket: WebSocket):
        """Start streaming audio data to WebSocket"""
        while websocket in self.active_connections:
            try:
                # Get current audio spectrum
                spectrum = audio_service.get_spectrum()
                frequencies = audio_service.get_active_frequencies()
                
                await self.send_personal_message({
                    "type": "audio_spectrum",
                    "data": {
                        "frequencies": frequencies,
                        "amplitudes": spectrum.get("amplitudes", []),
                        "timestamp": datetime.now().isoformat()
                    }
                }, websocket)
                
                await asyncio.sleep(0.1)  # 10 Hz update rate
                
            except Exception as e:
                print(f"Error streaming audio data: {e}")
                break

# Global connection manager instance
connection_manager = ConnectionManager()
```

### 7. Audio Endpoints (app/api/v1/endpoints/audio.py)
```python
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from core.services.audio_service import audio_service
from core.models.audio import AudioGenerationRequest, AudioControlRequest

router = APIRouter(prefix="/audio", tags=["audio"])

@router.post("/generate")
async def generate_audio(request: AudioGenerationRequest):
    """Generate audio based on configuration"""
    try:
        audio_data = await audio_service.generate_audio(request.dict())
        return {
            "status": "success",
            "audio_data": audio_data.tolist() if hasattr(audio_data, 'tolist') else audio_data,
            "sample_rate": 44100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/play")
async def play_audio(request: AudioControlRequest):
    """Play audio"""
    try:
        await audio_service.play_audio(request.audio_data)
        return {"status": "playing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_audio():
    """Stop audio playback"""
    try:
        await audio_service.stop_audio()
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_audio_status():
    """Get current audio status"""
    return {
        "is_playing": audio_service.is_playing,
        "current_session": audio_service.current_session,
        "spectrum": audio_service.get_spectrum(),
        "frequencies": audio_service.get_active_frequencies()
    }

@router.get("/spectrum")
async def get_frequency_spectrum():
    """Get current frequency spectrum"""
    return audio_service.get_spectrum()

@router.get("/frequencies")
async def get_active_frequencies():
    """Get currently active frequencies"""
    return {"frequencies": audio_service.get_active_frequencies()}
```

### 8. Session Endpoints (app/api/v1/endpoints/sessions.py)
```python
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from core.services.session_service import session_service
from core.models.session import Session, SessionCreate, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/", response_model=Session)
async def create_session(session_data: SessionCreate):
    """Create new session"""
    try:
        session = await session_service.create_session(session_data)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Session])
async def get_sessions():
    """Get all active sessions"""
    return list(session_service.active_sessions.values())

@router.get("/{session_id}", response_model=Optional[Session])
async def get_session(session_id: str):
    """Get session by ID"""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.put("/{session_id}", response_model=Optional[Session])
async def update_session(session_id: str, update_data: SessionUpdate):
    """Update session"""
    session = await session_service.update_session(session_id, update_data)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete session"""
    success = await session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}

@router.post("/{session_id}/start")
async def start_session(session_id: str):
    """Start session"""
    session = await session_service.start_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop session"""
    session = await session_service.stop_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
```

### 9. Data Models (core/models/session.py)
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"

class SessionBase(BaseModel):
    intention: str
    duration: int
    audio_type: str = "prayer_bowl"
    frequencies: list = []
    prayer_bowl_mode: bool = True
    metadata: Dict[str, Any] = {}

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    intention: Optional[str] = None
    duration: Optional[int] = None
    status: Optional[SessionStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class Session(SessionBase):
    id: str
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    elapsed_time: Optional[int] = None

    class Config:
        from_attributes = True
```

### 10. Configuration (app/config.py)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vajra.Stream API"
    
    # Database
    DATABASE_URL: str = "sqlite:///./vajra_stream.db"
    
    # Audio Settings
    SAMPLE_RATE: int = 44100
    AUDIO_DEVICE: str = "default"
    MAX_VOLUME: float = 0.8
    
    # Prayer Bowl Settings
    PRAYER_BOWL_MODE: bool = True
    PRAYER_BOWL_HARMONICS: bool = True
    PRAYER_BOWL_ENVELOPES: bool = True
    
    # Hardware
    HARDWARE_LEVEL: int = 2
    AMPLIFIER_CONNECTED: bool = False
    
    # Default Frequencies
    BLESSING_FREQUENCIES: list = [7.83, 136.1, 528, 639, 741]
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 11. API Router (app/api/v1/api.py)
```python
from fastapi import APIRouter
from app.api.v1.endpoints import (
    audio,
    sessions,
    astrology,
    prayers,
    llm,
    hardware,
    visuals,
    websocket
)

api_router = APIRouter()

api_router.include_router(audio.router, prefix="/audio")
api_router.include_router(sessions.router, prefix="/sessions")
api_router.include_router(astrology.router, prefix="/astrology")
api_router.include_router(prayers.router, prefix="/prayers")
api_router.include_router(llm.router, prefix="/llm")
api_router.include_router(hardware.router, prefix="/hardware")
api_router.include_router(visuals.router, prefix="/visuals")
```

## 🚀 Running the Backend

### Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or with specific settings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --env-file .env
```

### Production Setup
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### API Documentation
Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

This backend provides a solid foundation for controlling all aspects of the Vajra.Stream system through a modern REST API with real-time WebSocket streaming capabilities.