# Vajra.Stream Web Application Technical Specification

## 🎯 Overview

This technical specification provides detailed implementation guidance for creating a modern web application that fully leverages the existing Vajra.Stream sacred technology system. The approach focuses on **integration rather than rebuilding** - using the sophisticated existing modules as the foundation and adding web interfaces.

## 🏗️ System Architecture

### Core Principle: Wrapper Pattern
```
Existing Vajra.Stream Core → Web Service Wrapper → Frontend Interface
```

Instead of rebuilding functionality, we create **service wrappers** that expose existing modules through web APIs and WebSocket connections.

### Technology Stack
- **Backend**: FastAPI (Python) + existing Vajra.Stream modules
- **Frontend**: React + Vite + React Three Fiber
- **Communication**: WebSocket for real-time data, REST APIs for control
- **Database**: SQLite for session management
- **Styling**: Tailwind CSS

## 📋 Implementation Details

### Phase 1: Backend Service Layer

#### 1.1 Core Service Wrapper
**File**: `backend/core/services/vajra_service.py`

```python
"""
Vajra.Stream Service Wrapper
Exposes existing Vajra.Stream functionality through web APIs
"""

import asyncio
from typing import Dict, List, Optional
import numpy as np
from dataclasses import dataclass

# Import existing Vajra.Stream modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from core.audio_generator import ScalarWaveGenerator
from core.enhanced_audio_generator import EnhancedAudioGenerator, PrayerBowlGenerator
from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3CrystalBroadcaster
from core.prayer_wheel import PrayerWheel
from core.astrology import AstrologicalCalculator
from core.llm_integration import LLMIntegration
from core.tts_engine import TTSEngine
from core.rothko_generator import RothkoGenerator
from core.visual_renderer import VisualRenderer
from config.settings import Settings

@dataclass
class AudioConfig:
    """Audio configuration for prayer bowl generation"""
    frequency: float = 136.1  # OM frequency
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05
    envelope_type: str = "prayer_bowl"

@dataclass
class SessionConfig:
    """Session configuration"""
    name: str
    intention: str
    duration: int = 3600  # 1 hour
    audio_config: AudioConfig
    astrology_enabled: bool = True
    hardware_enabled: bool = True
    visuals_enabled: bool = True

class VajraStreamService:
    """Main service wrapper for Vajra.Stream functionality"""
    
    def __init__(self):
        self.settings = Settings()
        
        # Initialize existing modules
        self.audio_generator = EnhancedAudioGenerator()
        self.prayer_bowl_generator = PrayerBowlGenerator()
        self.level2_broadcaster = Level2CrystalBroadcaster()
        self.level3_broadcaster = Level3CrystalBroadcaster()
        self.prayer_wheel = PrayerWheel()
        self.astrology = AstrologicalCalculator()
        self.llm_integration = LLMIntegration()
        self.tts_engine = TTSEngine()
        self.rothko_generator = RothkoGenerator()
        self.visual_renderer = VisualRenderer()
        
        # Session state
        self.active_sessions: Dict[str, Dict] = {}
        self.current_audio_data: Optional[np.ndarray] = None
        self.audio_spectrum: List[float] = []
        self.session_history: List[Dict] = []
    
    async def generate_prayer_bowl_audio(self, config: AudioConfig) -> np.ndarray:
        """Generate prayer bowl audio using existing enhanced generator"""
        try:
            # Use existing PrayerBowlGenerator
            audio_data = await self.prayer_bowl_generator.generate_prayer_bowl_tone(
                frequency=config.frequency,
                duration=config.duration,
                volume=config.volume,
                harmonic_strength=config.harmonic_strength,
                modulation_depth=config.modulation_depth,
                envelope_type=config.envelope_type
            )
            
            self.current_audio_data = audio_data
            self._update_audio_spectrum(audio_data)
            
            return audio_data
            
        except Exception as e:
            print(f"Error generating prayer bowl audio: {e}")
            raise
    
    async def broadcast_audio(self, audio_data: np.ndarray, hardware_level: int = 2) -> bool:
        """Broadcast audio using existing crystal broadcasters"""
        try:
            if hardware_level == 2:
                success = await self.level2_broadcaster.generate_5_channel_blessing(audio_data)
            elif hardware_level == 3:
                success = await self.level3_broadcaster.generate_528hz_blessing(audio_data)
            else:
                raise ValueError("Hardware level must be 2 or 3")
            
            return success
            
        except Exception as e:
            print(f"Error broadcasting audio: {e}")
            return False
    
    async def create_session(self, config: SessionConfig) -> str:
        """Create a new blessing session"""
        session_id = f"session_{len(self.active_sessions) + 1}"
        
        session_data = {
            "id": session_id,
            "config": config,
            "status": "created",
            "start_time": None,
            "end_time": None,
            "astrology_data": None,
            "audio_data": None,
            "visual_data": None
        }
        
        self.active_sessions[session_id] = session_data
        
        # Generate astrology data if enabled
        if config.astrology_enabled:
            session_data["astrology_data"] = await self._get_astrology_data()
        
        return session_id
    
    async def start_session(self, session_id: str) -> bool:
        """Start a blessing session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session["status"] = "running"
        session["start_time"] = asyncio.get_event_loop().time()
        
        # Generate and play audio
        audio_data = await self.generate_prayer_bowl_audio(session["config"].audio_config)
        session["audio_data"] = audio_data
        
        # Broadcast if hardware enabled
        if session["config"].hardware_enabled:
            await self.broadcast_audio(audio_data)
        
        # Generate visuals if enabled
        if session["config"].visuals_enabled:
            session["visual_data"] = await self._generate_visuals(audio_data)
        
        return True
    
    async def stop_session(self, session_id: str) -> bool:
        """Stop a blessing session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        session["status"] = "stopped"
        session["end_time"] = asyncio.get_event_loop().time()
        
        # Move to history
        self.session_history.append(session.copy())
        del self.active_sessions[session_id]
        
        return True
    
    async def _get_astrology_data(self) -> Dict:
        """Get current astrological data"""
        try:
            # Use existing AstrologicalCalculator
            moon_phase = self.astrology.get_moon_phase()
            planetary_positions = self.astrology.get_planetary_positions()
            auspicious_times = self.astrology.get_auspicious_times()
            
            return {
                "moon_phase": moon_phase,
                "planetary_positions": planetary_positions,
                "auspicious_times": auspicious_times,
                "timestamp": asyncio.get_event_loop().time()
            }
        except Exception as e:
            print(f"Error getting astrology data: {e}")
            return {}
    
    async def _generate_visuals(self, audio_data: np.ndarray) -> Dict:
        """Generate visual data based on audio"""
        try:
            # Use existing VisualRenderer
            visual_data = await self.visual_renderer.generate_sacred_geometry(audio_data)
            
            # Generate Rothko-style art
            rothko_data = await self.rothko_generator.generate_contemplation_art(audio_data)
            
            return {
                "sacred_geometry": visual_data,
                "rothko_art": rothko_data,
                "timestamp": asyncio.get_event_loop().time()
            }
        except Exception as e:
            print(f"Error generating visuals: {e}")
            return {}
    
    def _update_audio_spectrum(self, audio_data: np.ndarray):
        """Update audio spectrum for real-time visualization"""
        try:
            # Simple FFT for spectrum analysis
            fft = np.fft.fft(audio_data)
            frequencies = np.abs(fft[:len(fft)//2])
            
            # Normalize and update
            self.audio_spectrum = frequencies.tolist()[:100]  # First 100 frequency bins
            
        except Exception as e:
            print(f"Error updating audio spectrum: {e}")
            self.audio_spectrum = []
    
    def get_audio_spectrum(self) -> List[float]:
        """Get current audio spectrum for WebSocket streaming"""
        return self.audio_spectrum
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get status of a specific session"""
        return self.active_sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict:
        """Get all active sessions"""
        return self.active_sessions
    
    def get_session_history(self) -> List[Dict]:
        """Get session history"""
        return self.session_history
```

#### 1.2 FastAPI Application
**File**: `backend/app/main.py`

```python
"""
FastAPI Application for Vajra.Stream Web Interface
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import asyncio

from core.services.vajra_service import VajraStreamService, AudioConfig, SessionConfig
from websocket.connection_manager import ConnectionManager

# Initialize FastAPI app
app = FastAPI(
    title="Vajra.Stream API",
    description="Sacred Technology Web Interface",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
vajra_service = VajraStreamService()
connection_manager = ConnectionManager()

# Pydantic models for API
class AudioConfigModel(BaseModel):
    frequency: float = 136.1
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05
    envelope_type: str = "prayer_bowl"

class SessionConfigModel(BaseModel):
    name: str
    intention: str
    duration: int = 3600
    audio_config: AudioConfigModel
    astrology_enabled: bool = True
    hardware_enabled: bool = True
    visuals_enabled: bool = True

# API Routes
@app.get("/")
async def root():
    return {"message": "Vajra.Stream API", "status": "active"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "vajra-stream"}

@app.post("/api/v1/audio/generate")
async def generate_audio(config: AudioConfigModel):
    """Generate prayer bowl audio"""
    try:
        audio_config = AudioConfig(**config.dict())
        audio_data = await vajra_service.generate_prayer_bowl_audio(audio_config)
        
        return {
            "status": "success",
            "message": "Audio generated successfully",
            "duration": len(audio_data) / 44100,  # Assuming 44.1kHz sample rate
            "sample_rate": 44100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/audio/play")
async def play_audio(hardware_level: int = 2):
    """Play current audio through hardware"""
    try:
        if vajra_service.current_audio_data is None:
            raise HTTPException(status_code=400, detail="No audio data available")
        
        success = await vajra_service.broadcast_audio(
            vajra_service.current_audio_data, 
            hardware_level
        )
        
        if success:
            return {"status": "success", "message": "Audio playback started"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start audio playback")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sessions/create")
async def create_session(config: SessionConfigModel):
    """Create a new blessing session"""
    try:
        audio_config = AudioConfig(**config.audio_config.dict())
        session_config = SessionConfig(
            name=config.name,
            intention=config.intention,
            duration=config.duration,
            audio_config=audio_config,
            astrology_enabled=config.astrology_enabled,
            hardware_enabled=config.hardware_enabled,
            visuals_enabled=config.visuals_enabled
        )
        
        session_id = await vajra_service.create_session(session_config)
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start a blessing session"""
    try:
        success = await vajra_service.start_session(session_id)
        
        if success:
            return {"status": "success", "message": "Session started"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a blessing session"""
    try:
        success = await vajra_service.stop_session(session_id)
        
        if success:
            return {"status": "success", "message": "Session stopped"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status"""
    try:
        session = vajra_service.get_session_status(session_id)
        
        if session:
            return {"status": "success", "session": session}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sessions")
async def get_all_sessions():
    """Get all active sessions"""
    try:
        sessions = vajra_service.get_all_sessions()
        return {"status": "success", "sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sessions/history")
async def get_session_history():
    """Get session history"""
    try:
        history = vajra_service.get_session_history()
        return {"status": "success", "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/astrology/current")
async def get_current_astrology():
    """Get current astrological data"""
    try:
        astrology_data = await vajra_service._get_astrology_data()
        return {"status": "success", "astrology": astrology_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time data
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            # Get current audio spectrum
            spectrum = vajra_service.get_audio_spectrum()
            
            # Get active sessions status
            sessions = vajra_service.get_all_sessions()
            
            # Send real-time data
            await websocket.send_json({
                "type": "realtime_data",
                "timestamp": asyncio.get_event_loop().time(),
                "audio_spectrum": spectrum,
                "active_sessions": sessions
            })
            
            await asyncio.sleep(0.1)  # 10Hz update rate
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 1.3 WebSocket Connection Manager
**File**: `backend/websocket/connection_manager.py`

```python
"""
WebSocket Connection Manager for Vajra.Stream
Handles real-time data streaming to frontend
"""

from fastapi import WebSocket
from typing import List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)
    
    async def send_audio_spectrum(self, spectrum: List[float]):
        """Send audio spectrum data to all clients"""
        await self.broadcast({
            "type": "audio_spectrum",
            "data": spectrum,
            "timestamp": time.time()
        })
    
    async def send_session_update(self, session_data: dict):
        """Send session status update to all clients"""
        await self.broadcast({
            "type": "session_update",
            "data": session_data,
            "timestamp": time.time()
        })
```

### Phase 2: Frontend Implementation

#### 2.1 React Project Setup
**File**: `frontend/package.json`

```json
{
  "name": "vajra-stream-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.88.0",
    "three": "^0.157.0",
    "zustand": "^4.4.0",
    "axios": "^1.5.0",
    "tailwindcss": "^3.3.0",
    "lucide-react": "^0.290.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

#### 2.2 Main Application Component
**File**: `frontend/src/App.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudioStore } from './stores/audioStore';
import SacredGeometry from './components/3D/SacredGeometry';
import AudioSpectrum from './components/2D/AudioSpectrum';
import ControlPanel from './components/UI/ControlPanel';
import SessionManager from './components/UI/SessionManager';
import './styles/globals.css';

function App() {
  const [visualizationType, setVisualizationType] = useState('sacred-geometry');
  const { 
    audioSpectrum, 
    isConnected, 
    sessions, 
    startSession, 
    stopSession 
  } = useWebSocket();
  
  const { 
    isPlaying, 
    frequency, 
    volume, 
    prayerBowlMode,
    updateSettings,
    generateAudio,
    playAudio 
  } = useAudioStore();

  useEffect(() => {
    // Initialize with default settings
    updateSettings({
      frequency: 136.1,
      volume: 0.8,
      prayerBowlMode: true
    });
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold text-cyan-400">Vajra.Stream</h1>
          <div className="flex items-center space-x-4">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex h-screen">
        {/* Left Panel - Controls */}
        <div className="w-80 bg-gray-800 p-6 overflow-y-auto">
          <ControlPanel
            isPlaying={isPlaying}
            frequency={frequency}
            volume={volume}
            prayerBowlMode={prayerBowlMode}
            onSettingsChange={updateSettings}
            onGenerateAudio={generateAudio}
            onPlayAudio={playAudio}
          />
          
          <div className="mt-8">
            <SessionManager
              sessions={sessions}
              onStartSession={startSession}
              onStopSession={stopSession}
            />
          </div>
        </div>

        {/* Center - Visualization */}
        <div className="flex-1 relative">
          {visualizationType === 'sacred-geometry' ? (
            <Canvas camera={{ position: [0, 0, 20], fov: 60 }}>
              <ambientLight intensity={0.5} />
              <pointLight position={[10, 10, 10]} />
              <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade />
              <SacredGeometry 
                audioSpectrum={audioSpectrum}
                isPlaying={isPlaying}
              />
              <OrbitControls enableZoom={false} />
            </Canvas>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <AudioSpectrum 
                spectrum={audioSpectrum}
                isPlaying={isPlaying}
              />
            </div>
          )}
          
          {/* Visualization Selector */}
          <div className="absolute top-4 right-4 bg-gray-800 p-2 rounded-lg">
            <select
              value={visualizationType}
              onChange={(e) => setVisualizationType(e.target.value)}
              className="bg-gray-700 text-white px-3 py-1 rounded"
            >
              <option value="sacred-geometry">Sacred Geometry</option>
              <option value="audio-spectrum">Audio Spectrum</option>
            </select>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
```

#### 2.3 WebSocket Hook
**File**: `frontend/src/hooks/useWebSocket.js`

```javascript
import { useState, useEffect, useRef } from 'react';

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [audioSpectrum, setAudioSpectrum] = useState([]);
  const [sessions, setSessions] = useState({});
  const ws = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    ws.current = new WebSocket('ws://localhost:8000/ws');

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'realtime_data':
          setAudioSpectrum(data.audio_spectrum || []);
          setSessions(data.active_sessions || {});
          break;
        case 'audio_spectrum':
          setAudioSpectrum(data.data || []);
          break;
        case 'session_update':
          setSessions(prev => ({
            ...prev,
            [data.data.id]: data.data
          }));
          break;
      }
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const startSession = async (sessionConfig) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/sessions/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sessionConfig),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        // Start the session
        await fetch(`http://localhost:8000/api/v1/sessions/${result.session_id}/start`, {
          method: 'POST',
        });
      }
      
      return result;
    } catch (error) {
      console.error('Error starting session:', error);
      throw error;
    }
  };

  const stopSession = async (sessionId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/v1/sessions/${sessionId}/stop`, {
        method: 'POST',
      });
      
      return await response.json();
    } catch (error) {
      console.error('Error stopping session:', error);
      throw error;
    }
  };

  return {
    isConnected,
    audioSpectrum,
    sessions,
    startSession,
    stopSession,
  };
};
```

#### 2.4 Sacred Geometry Component
**File**: `frontend/src/components/3D/SacredGeometry.jsx`

```jsx
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const SacredGeometry = ({ audioSpectrum, isPlaying }) => {
  const meshRef = useRef();
  const groupRef = useRef();

  // Create sacred geometry pattern
  const geometry = useMemo(() => {
    const group = new THREE.Group();
    
    // Create Flower of Life pattern
    const radius = 5;
    const circles = 19; // Center + 6 + 12
    
    for (let i = 0; i < circles; i++) {
      const geometry = new THREE.RingGeometry(0, radius, 32);
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color().setHSL(i / circles, 0.7, 0.5),
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide
      });
      
      const circle = new THREE.Mesh(geometry, material);
      
      if (i === 0) {
        // Center circle
        circle.position.set(0, 0, 0);
      } else if (i <= 6) {
        // First ring
        const angle = (i - 1) * (Math.PI * 2) / 6;
        circle.position.set(
          Math.cos(angle) * radius,
          Math.sin(angle) * radius,
          0
        );
      } else {
        // Second ring
        const angle = (i - 7) * (Math.PI * 2) / 12;
        circle.position.set(
          Math.cos(angle) * radius * 2,
          Math.sin(angle) * radius * 2,
          0
        );
      }
      
      group.add(circle);
    }
    
    return group;
  }, []);

  // Animation loop
  useFrame((state, delta) => {
    if (meshRef.current) {
      // Rotate based on audio data
      const rotationSpeed = isPlaying ? 
        0.1 + (audioSpectrum[0] || 0) * 0.5 : 0.1;
      
      meshRef.current.rotation.z += rotationSpeed * delta;
      meshRef.current.rotation.x += rotationSpeed * delta * 0.5;
      
      // Scale based on audio
      if (isPlaying && audioSpectrum.length > 0) {
        const avgFrequency = audioSpectrum.slice(0, 10).reduce((a, b) => a + b, 0) / 10;
        const scale = 1 + avgFrequency * 0.2;
        meshRef.current.scale.setScalar(scale);
      }
    }
  });

  return (
    <group ref={groupRef}>
      <primitive 
        ref={meshRef} 
        object={geometry.clone()} 
      />
    </group>
  );
};

export default SacredGeometry;
```

## 🚀 Implementation Steps

### Step 1: Backend Setup
1. Create backend directory structure
2. Install dependencies: `pip install fastapi uvicorn websockets`
3. Copy existing Vajra.Stream modules to backend
4. Implement service wrapper classes
5. Create FastAPI application with WebSocket support

### Step 2: Frontend Setup
1. Create React project with Vite
2. Install dependencies: `npm install @react-three/fiber @react-three/drei three zustand axios`
3. Set up Tailwind CSS
4. Create component structure
5. Implement WebSocket connection

### Step 3: Integration Testing
1. Test backend API endpoints
2. Test WebSocket connection
3. Test audio generation and playback
4. Test real-time visualization
5. Test session management

### Step 4: Deployment
1. Configure production settings
2. Set up reverse proxy (nginx)
3. Configure SSL certificates
4. Deploy to production server

## 🎯 Key Benefits

### For Existing Vajra.Stream Users
- **Web Interface**: Modern, intuitive control of all existing features
- **Real-time Visualization**: Advanced 3D sacred geometry responding to prayer bowl audio
- **Session Management**: Track and manage blessing sessions
- **Remote Access**: Control system from any device with web browser

### For Developers
- **Extensible Architecture**: Easy to add new features and modules
- **API-First Design**: Clean separation between frontend and backend
- **Modern Development Stack**: React, FastAPI, WebSocket, Three.js
- **Comprehensive Documentation**: Full API and user guides

This technical specification provides a complete roadmap for transforming Vajra.Stream into a modern web application while preserving all existing functionality and adding powerful new capabilities for sacred technology practice.