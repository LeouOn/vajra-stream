# Vajra.Stream Web Application Implementation Guide

## 🎯 Overview

This guide provides step-by-step instructions to transform the existing Vajra.Stream sacred technology system into a modern web application with React + Vite + React Three Fiber frontend and FastAPI backend.

## 📋 Prerequisites

### System Requirements
- Python 3.8+ (for backend)
- Node.js 16+ (for frontend)
- Git
- Existing Vajra.Stream project with all modules

### Required Dependencies
```bash
# Backend Python packages
pip install fastapi uvicorn websockets numpy scipy pydantic

# Frontend Node.js packages
npm install react react-dom @react-three/fiber @react-three/drei three vite tailwindcss zustand axios
```

## 🚀 Step-by-Step Implementation

### Step 1: Backend Setup

#### 1.1 Create Backend Directory Structure
```bash
mkdir -p backend/{app/{api/v1/endpoints,core/services,websocket},tests}
cd backend
```

#### 1.2 Create Requirements File
**File**: `backend/requirements.txt`
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
pydantic==2.5.0
numpy==1.24.3
scipy==1.11.4
python-multipart==0.0.6
```

#### 1.3 Install Dependencies
```bash
pip install -r requirements.txt
```

#### 1.4 Create Main FastAPI Application
**File**: `backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import audio, sessions, astrology
from websocket.connection_manager import ConnectionManager

app = FastAPI(title="Vajra.Stream API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audio.router, prefix="/api/v1/audio", tags=["audio"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(astrology.router, prefix="/api/v1/astrology", tags=["astrology"])

# WebSocket connection manager
connection_manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Vajra.Stream API", "status": "active"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "vajra-stream"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 1.5 Create Vajra Stream Service Wrapper
**File**: `backend/app/core/services/vajra_service.py`
```python
import asyncio
import sys
import os
from typing import Dict, List, Optional
import numpy as np

# Add parent directory to path to import existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from core.audio_generator import ScalarWaveGenerator
from core.enhanced_audio_generator import EnhancedAudioGenerator, PrayerBowlGenerator
from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3CrystalBroadcaster
from core.prayer_wheel import PrayerWheel
from core.astrology import AstrologicalCalculator
from core.llm_integration import LLMIntegration
from core.tts_engine import TTSEngine
from core.rothko_generator import RothkoGenerator
from core.visual_renderer import VisualRenderer

class VajraStreamService:
    """Service wrapper for Vajra.Stream functionality"""
    
    def __init__(self):
        # Initialize existing modules
        try:
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
            
            self.current_audio_data: Optional[np.ndarray] = None
            self.audio_spectrum: List[float] = []
            self.active_sessions: Dict[str, Dict] = {}
            
            print("Vajra.Stream service initialized successfully")
            
        except Exception as e:
            print(f"Error initializing Vajra.Stream service: {e}")
            # Fallback to basic functionality
            self.audio_generator = None
            self.prayer_bowl_generator = None
            self.level2_broadcaster = None
            self.level3_broadcaster = None
    
    async def generate_prayer_bowl_audio(self, frequency: float = 136.1, duration: float = 30.0, 
                                        volume: float = 0.8, prayer_bowl_mode: bool = True,
                                        harmonic_strength: float = 0.3, modulation_depth: float = 0.05) -> np.ndarray:
        """Generate prayer bowl audio using existing enhanced generator"""
        try:
            if self.prayer_bowl_generator:
                audio_data = await self.prayer_bowl_generator.generate_prayer_bowl_tone(
                    frequency=frequency,
                    duration=duration,
                    volume=volume,
                    harmonic_strength=harmonic_strength,
                    modulation_depth=modulation_depth
                )
            else:
                # Fallback: generate simple sine wave
                sample_rate = 44100
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                audio_data = np.sin(frequency * 2 * np.pi * t) * volume
            
            self.current_audio_data = audio_data
            self._update_audio_spectrum(audio_data)
            
            return audio_data
            
        except Exception as e:
            print(f"Error generating prayer bowl audio: {e}")
            # Return fallback audio
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            return np.sin(frequency * 2 * np.pi * t) * volume
    
    async def broadcast_audio(self, audio_data: np.ndarray, hardware_level: int = 2) -> bool:
        """Broadcast audio using existing crystal broadcasters"""
        try:
            if hardware_level == 2 and self.level2_broadcaster:
                success = await self.level2_broadcaster.generate_5_channel_blessing(audio_data)
            elif hardware_level == 3 and self.level3_broadcaster:
                success = await self.level3_broadcaster.generate_528hz_blessing(audio_data)
            else:
                # Simulate broadcasting
                print(f"Simulating audio broadcast at level {hardware_level}")
                success = True
            
            return success
            
        except Exception as e:
            print(f"Error broadcasting audio: {e}")
            return False
    
    def _update_audio_spectrum(self, audio_data: np.ndarray):
        """Update audio spectrum for real-time visualization"""
        try:
            # Simple FFT for spectrum analysis
            fft = np.fft.fft(audio_data)
            frequencies = np.abs(fft[:len(fft)//2])
            
            # Normalize and update (take first 100 frequency bins)
            max_freq = np.max(frequencies) if np.max(frequencies) > 0 else 1
            self.audio_spectrum = (frequencies[:100] / max_freq).tolist()
            
        except Exception as e:
            print(f"Error updating audio spectrum: {e}")
            self.audio_spectrum = [0.0] * 100
    
    def get_audio_spectrum(self) -> List[float]:
        """Get current audio spectrum for WebSocket streaming"""
        return self.audio_spectrum
    
    async def get_astrology_data(self) -> Dict:
        """Get current astrological data"""
        try:
            if self.astrology:
                moon_phase = self.astrology.get_moon_phase()
                planetary_positions = self.astrology.get_planetary_positions()
                auspicious_times = self.astrology.get_auspicious_times()
                
                return {
                    "moon_phase": moon_phase,
                    "planetary_positions": planetary_positions,
                    "auspicious_times": auspicious_times,
                    "timestamp": asyncio.get_event_loop().time()
                }
            else:
                # Fallback data
                return {
                    "moon_phase": "waxing",
                    "planetary_positions": {"sun": "aries", "moon": "taurus"},
                    "auspicious_times": ["morning", "evening"],
                    "timestamp": asyncio.get_event_loop().time()
                }
        except Exception as e:
            print(f"Error getting astrology data: {e}")
            return {}

# Global service instance
vajra_service = VajraStreamService()
```

#### 1.6 Create API Endpoints
**File**: `backend/app/api/v1/endpoints/audio.py`
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from ...core.services.vajra_service import vajra_service

router = APIRouter()

class AudioConfig(BaseModel):
    frequency: float = 136.1
    duration: float = 30.0
    volume: float = 0.8
    prayer_bowl_mode: bool = True
    harmonic_strength: float = 0.3
    modulation_depth: float = 0.05

class PlayRequest(BaseModel):
    hardware_level: int = 2

@router.post("/generate")
async def generate_audio(config: AudioConfig):
    """Generate prayer bowl audio"""
    try:
        audio_data = await vajra_service.generate_prayer_bowl_audio(
            frequency=config.frequency,
            duration=config.duration,
            volume=config.volume,
            prayer_bowl_mode=config.prayer_bowl_mode,
            harmonic_strength=config.harmonic_strength,
            modulation_depth=config.modulation_depth
        )
        
        return {
            "status": "success",
            "message": "Audio generated successfully",
            "duration": len(audio_data) / 44100,
            "sample_rate": 44100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/play")
async def play_audio(request: PlayRequest):
    """Play current audio through hardware"""
    try:
        if vajra_service.current_audio_data is None:
            raise HTTPException(status_code=400, detail="No audio data available")
        
        success = await vajra_service.broadcast_audio(
            vajra_service.current_audio_data, 
            request.hardware_level
        )
        
        if success:
            return {"status": "success", "message": "Audio playback started"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start audio playback")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spectrum")
async def get_audio_spectrum():
    """Get current audio spectrum"""
    try:
        spectrum = vajra_service.get_audio_spectrum()
        return {"status": "success", "spectrum": spectrum}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**File**: `backend/app/api/v1/endpoints/sessions.py`
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import uuid

from ...core.services.vajra_service import vajra_service

router = APIRouter()

class SessionConfig(BaseModel):
    name: str
    intention: str
    duration: int = 3600
    audio_frequency: float = 136.1
    astrology_enabled: bool = True
    hardware_enabled: bool = True
    visuals_enabled: bool = True

@router.post("/create")
async def create_session(config: SessionConfig):
    """Create a new blessing session"""
    try:
        session_id = str(uuid.uuid4())
        
        session_data = {
            "id": session_id,
            "name": config.name,
            "intention": config.intention,
            "duration": config.duration,
            "audio_frequency": config.audio_frequency,
            "astrology_enabled": config.astrology_enabled,
            "hardware_enabled": config.hardware_enabled,
            "visuals_enabled": config.visuals_enabled,
            "status": "created",
            "start_time": None,
            "end_time": None
        }
        
        vajra_service.active_sessions[session_id] = session_data
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/start")
async def start_session(session_id: str):
    """Start a blessing session"""
    try:
        if session_id not in vajra_service.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = vajra_service.active_sessions[session_id]
        session["status"] = "running"
        session["start_time"] = asyncio.get_event_loop().time()
        
        # Generate and play audio
        audio_data = await vajra_service.generate_prayer_bowl_audio(
            frequency=session["audio_frequency"]
        )
        
        # Broadcast if hardware enabled
        if session["hardware_enabled"]:
            await vajra_service.broadcast_audio(audio_data)
        
        return {"status": "success", "message": "Session started"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a blessing session"""
    try:
        if session_id not in vajra_service.active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = vajra_service.active_sessions[session_id]
        session["status"] = "stopped"
        session["end_time"] = asyncio.get_event_loop().time()
        
        # Move to history
        vajra_service.session_history.append(session.copy())
        del vajra_service.active_sessions[session_id]
        
        return {"status": "success", "message": "Session stopped"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_all_sessions():
    """Get all active sessions"""
    try:
        return {"status": "success", "sessions": vajra_service.active_sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**File**: `backend/app/api/v1/endpoints/astrology.py`
```python
from fastapi import APIRouter, HTTPException
from ...core.services.vajra_service import vajra_service

router = APIRouter()

@router.get("/current")
async def get_current_astrology():
    """Get current astrological data"""
    try:
        astrology_data = await vajra_service.get_astrology_data()
        return {"status": "success", "astrology": astrology_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 1.7 Create WebSocket Manager
**File**: `backend/websocket/connection_manager.py`
```python
from fastapi import WebSocket
from typing import List
import json
import time
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)
    
    async def start_realtime_streaming(self):
        """Start streaming real-time data to all clients"""
        while True:
            try:
                # Get current data
                from app.core.services.vajra_service import vajra_service
                
                spectrum = vajra_service.get_audio_spectrum()
                sessions = vajra_service.active_sessions
                
                # Send real-time data
                await self.broadcast({
                    "type": "realtime_data",
                    "timestamp": time.time(),
                    "audio_spectrum": spectrum,
                    "active_sessions": sessions
                })
                
                await asyncio.sleep(0.1)  # 10Hz update rate
                
            except Exception as e:
                print(f"Error in realtime streaming: {e}")
                await asyncio.sleep(1)

# Global connection manager
connection_manager = ConnectionManager()
```

#### 1.8 Add WebSocket Endpoint to Main App
**Add to `backend/app/main.py`:**
```python
from websocket.connection_manager import connection_manager
import asyncio

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        connection_manager.disconnect(websocket)

# Start background task for real-time streaming
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(connection_manager.start_realtime_streaming())
```

### Step 2: Frontend Setup

#### 2.1 Create Frontend Project
```bash
cd ../
npm create vite@latest frontend -- --template react
cd frontend
```

#### 2.2 Install Dependencies
```bash
npm install @react-three/fiber @react-three/drei three zustand axios tailwindcss
npm install -D postcss autoprefixer
```

#### 2.3 Configure Tailwind CSS
```bash
npx tailwindcss init -p
```

**File**: `tailwind.config.js`
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**File**: `src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### 2.4 Create Main App Component
**File**: `src/App.jsx`
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
import './index.css';

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

#### 2.5 Create WebSocket Hook
**File**: `src/hooks/useWebSocket.js`
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

#### 2.6 Create Audio Store
**File**: `src/stores/audioStore.js`
```javascript
import { create } from 'zustand';

export const useAudioStore = create((set, get) => ({
  // State
  isPlaying: false,
  frequency: 136.1,
  volume: 0.8,
  prayerBowlMode: true,
  harmonicStrength: 0.3,
  modulationDepth: 0.05,
  
  // Actions
  updateSettings: (newSettings) => {
    set((state) => ({
      ...state,
      ...newSettings
    }));
  },
  
  generateAudio: async () => {
    try {
      const { frequency, volume, prayerBowlMode, harmonicStrength, modulationDepth } = get();
      
      const response = await fetch('http://localhost:8000/api/v1/audio/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          frequency,
          volume,
          prayer_bowl_mode: prayerBowlMode,
          harmonic_strength: harmonicStrength,
          modulation_depth: modulationDepth
        }),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        console.log('Audio generated successfully');
        return true;
      } else {
        console.error('Failed to generate audio');
        return false;
      }
    } catch (error) {
      console.error('Error generating audio:', error);
      return false;
    }
  },
  
  playAudio: async (hardwareLevel = 2) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/audio/play', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          hardware_level: hardwareLevel
        }),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        set({ isPlaying: true });
        console.log('Audio playback started');
        return true;
      } else {
        console.error('Failed to start audio playback');
        return false;
      }
    } catch (error) {
      console.error('Error playing audio:', error);
      return false;
    }
  },
  
  stopAudio: () => {
    set({ isPlaying: false });
    console.log('Audio playback stopped');
  }
}));
```

#### 2.7 Create Sacred Geometry Component
**File**: `src/components/3D/SacredGeometry.jsx`
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

#### 2.8 Create Audio Spectrum Component
**File**: `src/components/2D/AudioSpectrum.jsx`
```jsx
import React, { useEffect, useRef } from 'react';

const AudioSpectrum = ({ spectrum, isPlaying }) => {
  const canvasRef = useRef();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    if (spectrum.length === 0) return;
    
    // Draw spectrum bars
    const barWidth = width / spectrum.length;
    const barSpacing = 2;
    
    spectrum.forEach((value, index) => {
      const barHeight = value * height * 0.8;
      const x = index * barWidth;
      const y = height - barHeight;
      
      // Create gradient
      const gradient = ctx.createLinearGradient(0, y, 0, height);
      gradient.addColorStop(0, `hsl(${index * 3}, 70%, 50%)`);
      gradient.addColorStop(1, `hsl(${index * 3}, 70%, 30%)`);
      
      ctx.fillStyle = gradient;
      ctx.fillRect(x + barSpacing/2, y, barWidth - barSpacing, barHeight);
    });
    
  }, [spectrum, isPlaying]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={400}
      className="border border-gray-700 rounded-lg"
    />
  );
};

export default AudioSpectrum;
```

#### 2.9 Create Control Panel Component
**File**: `src/components/UI/ControlPanel.jsx`
```jsx
import React, { useState } from 'react';

const ControlPanel = ({
  isPlaying,
  frequency,
  volume,
  prayerBowlMode,
  onSettingsChange,
  onGenerateAudio,
  onPlayAudio
}) => {
  const [localFrequency, setLocalFrequency] = useState(frequency);
  const [localVolume, setLocalVolume] = useState(volume);
  const [localPrayerBowlMode, setLocalPrayerBowlMode] = useState(prayerBowlMode);

  const handleGenerateAudio = async () => {
    onSettingsChange({
      frequency: localFrequency,
      volume: localVolume,
      prayerBowlMode: localPrayerBowlMode
    });
    
    const success = await onGenerateAudio();
    if (success) {
      console.log('Audio generated successfully');
    }
  };

  const handlePlayAudio = async () => {
    const success = await onPlayAudio();
    if (success) {
      console.log('Audio playback started');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4 text-cyan-400">Audio Controls</h2>
        
        {/* Frequency Control */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Frequency: {localFrequency.toFixed(1)} Hz
          </label>
          <input
            type="range"
            min="20"
            max="1000"
            step="0.1"
            value={localFrequency}
            onChange={(e) => setLocalFrequency(parseFloat(e.target.value))}
            className="w-full"
          />
        </div>

        {/* Volume Control */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Volume: {Math.round(localVolume * 100)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={localVolume}
            onChange={(e) => setLocalVolume(parseFloat(e.target.value))}
            className="w-full"
          />
        </div>

        {/* Prayer Bowl Mode */}
        <div className="mb-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={localPrayerBowlMode}
              onChange={(e) => setLocalPrayerBowlMode(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm font-medium">Prayer Bowl Mode</span>
          </label>
        </div>

        {/* Control Buttons */}
        <div className="space-y-2">
          <button
            onClick={handleGenerateAudio}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors"
          >
            Generate Audio
          </button>
          
          <button
            onClick={handlePlayAudio}
            disabled={isPlaying}
            className={`w-full font-medium py-2 px-4 rounded transition-colors ${
              isPlaying 
                ? 'bg-gray-600 cursor-not-allowed' 
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {isPlaying ? 'Playing...' : 'Play Audio'}
          </button>
        </div>
      </div>

      {/* Status Display */}
      <div className="bg-gray-700 p-4 rounded-lg">
        <h3 className="text-sm font-semibold mb-2 text-cyan-400">Status</h3>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span>State:</span>
            <span className={isPlaying ? 'text-green-400' : 'text-gray-400'}>
              {isPlaying ? 'Playing' : 'Stopped'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Frequency:</span>
            <span>{frequency.toFixed(1)} Hz</span>
          </div>
          <div className="flex justify-between">
            <span>Volume:</span>
            <span>{Math.round(volume * 100)}%</span>
          </div>
          <div className="flex justify-between">
            <span>Mode:</span>
            <span>{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
```

#### 2.10 Create Session Manager Component
**File**: `src/components/UI/SessionManager.jsx`
```jsx
import React, { useState } from 'react';

const SessionManager = ({ sessions, onStartSession, onStopSession }) => {
  const [sessionName, setSessionName] = useState('');
  const [sessionIntention, setSessionIntention] = useState('');

  const handleStartSession = async () => {
    if (!sessionName.trim() || !sessionIntention.trim()) {
      alert('Please enter both session name and intention');
      return;
    }

    const sessionConfig = {
      name: sessionName,
      intention: sessionIntention,
      duration: 3600, // 1 hour
      audio_frequency: 136.1, // OM frequency
      astrology_enabled: true,
      hardware_enabled: true,
      visuals_enabled: true
    };

    try {
      const result = await onStartSession(sessionConfig);
      if (result.status === 'success') {
        setSessionName('');
        setSessionIntention('');
        console.log('Session started successfully');
      }
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4 text-cyan-400">Session Manager</h2>
        
        {/* Create New Session */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Session Name
            </label>
            <input
              type="text"
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="Enter session name"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Intention
            </label>
            <textarea
              value={sessionIntention}
              onChange={(e) => setSessionIntention(e.target.value)}
              placeholder="Enter your intention for this session"
              rows={3}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          <button
            onClick={handleStartSession}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded transition-colors"
          >
            Start Session
          </button>
        </div>
      </div>

      {/* Active Sessions */}
      <div>
        <h3 className="text-lg font-semibold mb-3 text-cyan-400">Active Sessions</h3>
        
        {Object.keys(sessions).length === 0 ? (
          <p className="text-gray-400 text-sm">No active sessions</p>
        ) : (
          <div className="space-y-3">
            {Object.values(sessions).map((session) => (
              <div key={session.id} className="bg-gray-700 p-3 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="font-medium">{session.name}</h4>
                    <p className="text-sm text-gray-400">{session.intention}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded ${
                    session.status === 'running' 
                      ? 'bg-green-600 text-white' 
                      : 'bg-gray-600 text-gray-300'
                  }`}>
                    {session.status}
                  </span>
                </div>
                
                <div className="flex justify-between items-center text-sm text-gray-400">
                  <span>Frequency: {session.audio_frequency} Hz</span>
                  <button
                    onClick={() => onStopSession(session.id)}
                    className="text-red-400 hover:text-red-300 transition-colors"
                  >
                    Stop
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionManager;
```

### Step 3: Testing and Launch

#### 3.1 Start Backend Server
```bash
cd backend
python app/main.py
```

#### 3.2 Start Frontend Development Server
```bash
cd frontend
npm run dev
```

#### 3.3 Test the Application
1. Open browser to `http://localhost:3000`
2. Check WebSocket connection status (should show green)
3. Test audio generation and playback
4. Test session creation and management
5. Verify real-time visualizations respond to audio

#### 3.4 Create Integration Test Script
**File**: `test_integration.py`
```python
import asyncio
import requests
import websocket
import json
import time

async def test_integration():
    """Test backend-frontend integration"""
    
    print("🧪 Testing Vajra.Stream Web Application Integration")
    
    # Test backend health
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Backend health check passed")
        else:
            print("❌ Backend health check failed")
            return
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return
    
    # Test audio generation
    try:
        response = requests.post("http://localhost:8000/api/v1/audio/generate", 
                               json={
                                   "frequency": 136.1,
                                   "duration": 10.0,
                                   "volume": 0.8,
                                   "prayer_bowl_mode": True
                               })
        if response.status_code == 200:
            print("✅ Audio generation API working")
        else:
            print("❌ Audio generation API failed")
    except Exception as e:
        print(f"❌ Audio generation test failed: {e}")
    
    # Test session creation
    try:
        response = requests.post("http://localhost:8000/api/v1/sessions/create",
                               json={
                                   "name": "Test Session",
                                   "intention": "Testing integration",
                                   "duration": 300,
                                   "audio_frequency": 136.1
                               })
        if response.status_code == 200:
            session_id = response.json()["session_id"]
            print(f"✅ Session creation working (ID: {session_id})")
            
            # Test session start
            response = requests.post(f"http://localhost:8000/api/v1/sessions/{session_id}/start")
            if response.status_code == 200:
                print("✅ Session start working")
            else:
                print("❌ Session start failed")
        else:
            print("❌ Session creation failed")
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
    
    # Test WebSocket connection
    try:
        ws = websocket.create_connection("ws://localhost:8000/ws")
        print("✅ WebSocket connection established")
        
        # Wait for real-time data
        for i in range(5):
            result = ws.recv()
            data = json.loads(result)
            if data.get("type") == "realtime_data":
                print("✅ Real-time data streaming working")
                break
            time.sleep(0.5)
        
        ws.close()
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
    
    print("\n🎉 Integration testing completed!")

if __name__ == "__main__":
    asyncio.run(test_integration())
```

## 🎯 Success Criteria

### Backend Success
- [ ] FastAPI server starts without errors
- [ ] All API endpoints respond correctly
- [ ] WebSocket connection established
- [ ] Real-time data streaming works
- [ ] Existing Vajra.Stream modules integrated

### Frontend Success
- [ ] React application loads without errors
- [ ] WebSocket connection to backend established
- [ ] 3D sacred geometry visualization renders
- [ ] Audio spectrum visualization works
- [ ] Control panel functions correctly
- [ ] Session management works

### Integration Success
- [ ] Audio generation from frontend works
- [ ] Real-time visualizations respond to audio
- [ ] Session creation and management works
- [ ] Hardware control through web interface
- [ ] Astrology data displays correctly

## 🚀 Next Steps

1. **Enhance Visualizations**: Add more sacred geometry patterns and 3D models
2. **Hardware Integration**: Connect to actual crystal broadcasters
3. **User Authentication**: Add user accounts and session persistence
4. **Mobile Responsive**: Optimize for mobile devices
5. **Deployment**: Deploy to production server

This implementation guide provides a complete roadmap for transforming Vajra.Stream into a modern web application while preserving all existing functionality and adding powerful new capabilities for sacred technology practice.