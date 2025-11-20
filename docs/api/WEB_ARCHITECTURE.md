# Vajra.Stream Web Architecture

## 🏗️ System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │  Core System   │
│                 │    │                 │    │                 │
│ React + Vite    │◄──►│   FastAPI       │◄──►│  Audio Engine  │
│ React Three     │    │   WebSocket     │    │  Prayer Wheel  │
│ Fiber (3D)      │    │   REST APIs     │    │  Astrology     │
│                 │    │                 │    │  LLM Integration│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Backend Architecture (Python + FastAPI)

### Core API Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
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

### API Endpoints Design

#### Audio Control (`/api/v1/audio/`)
```python
# Audio Generation
POST   /api/v1/audio/generate
{
    "type": "prayer_bowl|solfeggio|binaural|schumann",
    "frequency": 432,
    "duration": 300,
    "intention": "peace and harmony",
    "prayer_bowl_mode": true
}

# Audio Control
POST   /api/v1/audio/play
POST   /api/v1/audio/stop
POST   /api/v1/audio/pause
GET    /api/v1/audio/status

# Frequency Analysis
GET    /api/v1/audio/spectrum
GET    /api/v1/audio/frequencies
```

#### Session Management (`/api/v1/sessions/`)
```python
# Session CRUD
POST   /api/v1/sessions/
GET    /api/v1/sessions/
GET    /api/v1/sessions/{session_id}
PUT    /api/v1/sessions/{session_id}
DELETE /api/v1/sessions/{session_id}

# Session Control
POST   /api/v1/sessions/{session_id}/start
POST   /api/v1/sessions/{session_id}/stop
POST   /api/v1/sessions/{session_id}/pause
GET    /api/v1/sessions/{session_id}/logs
```

#### Astrology (`/api/v1/astrology/`)
```python
# Real-time Calculations
GET    /api/v1/astrology/current
GET    /api/v1/astrology/planetary_positions
GET    /api/v1/astrology/moon_phase
GET    /api/v1/astrology/auspicious_times

# Location-based
POST   /api/v1/astrology/location_data
{
    "latitude": 37.7749,
    "longitude": -122.4194,
    "datetime": "2024-01-01T12:00:00Z"
}
```

#### Prayer Wheel (`/api/v1/prayers/`)
```python
# Prayer Generation
POST   /api/v1/prayers/generate
{
    "intention": "compassion",
    "tradition": "buddhist|universal|custom",
    "use_llm": true
}

# Prayer Wheel Control
POST   /api/v1/prayers/spin
POST   /api/v1/prayers/continuous
POST   /api/v1/prayers/mantra_accumulation
GET    /api/v1/prayers/traditional
```

#### Hardware Control (`/api/v1/hardware/`)
```python
# Crystal Broadcaster
GET    /api/v1/hardware/status
POST   /api/v1/hardware/crystal_grid
{
    "intention": "healing",
    "duration": 300,
    "frequencies": [7.83, 136.1, 528]
}

# Amplifier Control
POST   /api/v1/hardware/amplifier
POST   /api/v1/hardware/bass_shaker
```

#### Visual Generation (`/api/v1/visuals/`)
```python
# Sacred Geometry
POST   /api/v1/visuals/sacred_geometry
{
    "type": "flower_of_life|sri_yantra|metatrons_cube",
    "intention": "peace",
    "audio_reactive": true
}

# Rothko-style Meditation
POST   /api/v1/visuals/rothko
{
    "theme": "compassion|wisdom|peace",
    "chakra": "heart|third_eye"
}
```

### WebSocket Events

#### Real-time Data Streaming
```python
# Audio Analysis
{
    "type": "audio_spectrum",
    "data": {
        "frequencies": [7.83, 136.1, 528],
        "amplitudes": [0.8, 0.6, 0.4],
        "timestamp": "2024-01-01T12:00:00Z"
    }
}

# Session Updates
{
    "type": "session_update",
    "data": {
        "session_id": "uuid",
        "status": "running|paused|stopped",
        "elapsed_time": 120,
        "current_intention": "peace"
    }
}

# Astrological Updates
{
    "type": "astrology_update",
    "data": {
        "planetary_hour": "venus",
        "moon_phase": "waxing_gibbous",
        "auspicious": true
    }
}
```

## 🎨 Frontend Architecture (React + Vite + R3F)

### Project Structure
```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── 3D/                    # React Three Fiber components
│   │   │   ├── PlanetarySystem.jsx
│   │   │   ├── Earth3D.jsx
│   │   │   ├── SacredGeometry/
│   │   │   │   ├── FlowerOfLife.jsx
│   │   │   │   ├── SriYantra.jsx
│   │   │   │   └── MetatronsCube.jsx
│   │   │   ├── ChakraSystem.jsx
│   │   │   └── PrayerWheel3D.jsx
│   │   ├── 2D/                    # Canvas/SVG visualizations
│   │   │   ├── FrequencyBars.jsx
│   │   │   ├── Mandala.jsx
│   │   │   └── SpectrumAnalyzer.jsx
│   │   ├── UI/                    # Regular React components
│   │   │   ├── Controls/
│   │   │   │   ├── AudioControls.jsx
│   │   │   │   ├── SessionControls.jsx
│   │   │   │   ├── IntentionForm.jsx
│   │   │   │   └── HardwareControls.jsx
│   │   │   ├── Panels/
│   │   │   │   ├── AstrologyPanel.jsx
│   │   │   │   ├── FrequencyPanel.jsx
│   │   │   │   └── PrayerPanel.jsx
│   │   │   └── Layout/
│   │   │       ├── Header.jsx
│   │   │       ├── Sidebar.jsx
│   │   │       └── MainLayout.jsx
│   │   └── Common/
│   │       ├── Loading.jsx
│   │       ├── ErrorBoundary.jsx
│   │       └── Modal.jsx
│   ├── hooks/
│   │   ├── useWebSocket.js        # WebSocket connection
│   │   ├── useAudio.js           # Audio context and analysis
│   │   ├── useAstrology.js       # Astrological data
│   │   ├── useSession.js         # Session management
│   │   └── useThree.js           # Three.js utilities
│   ├── services/
│   │   ├── api.js               # API client
│   │   ├── websocket.js         # WebSocket client
│   │   └── audio.js             # Audio processing
│   ├── scenes/
│   │   ├── BlessingScene.jsx     # Main blessing interface
│   │   ├── HealingScene.jsx      # Healing session
│   │   ├── MeditationScene.jsx   # Meditation practice
│   │   └── PurificationScene.jsx # Purification ritual
│   ├── utils/
│   │   ├── three.js             # Three.js utilities
│   │   ├── audio.js             # Audio utilities
│   │   └── constants.js         # App constants
│   ├── styles/
│   │   ├── globals.css
│   │   └── components/
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── vite.config.js
```

### Key 3D Components Architecture

#### Planetary System
```jsx
// components/3D/PlanetarySystem.jsx
function PlanetarySystem({ astrologyData, blessings }) {
  return (
    <Canvas camera={{ position: [0, 0, 100] }}>
      <Stars />
      <Sun />
      {Object.entries(astrologyData.planets).map(([name, data]) => (
        <Planet
          key={name}
          name={name}
          position={calculatePosition(data)}
          blessing={blessings[name]}
          glowIntensity={data.influence}
        />
      ))}
      <BlessingFlow />
      <ZodiacRing />
    </Canvas>
  )
}
```

#### Sacred Geometry
```jsx
// components/3D/SacredGeometry/FlowerOfLife.jsx
function FlowerOfLife({ audioReactive, frequencies }) {
  const meshRef = useRef()
  
  useFrame(() => {
    if (audioReactive && frequencies) {
      // React to audio in real-time
      meshRef.current.scale.setScalar(
        1 + frequencies[0] * 0.1
      )
    }
  })
  
  return (
    <mesh ref={meshRef}>
      <ringGeometry args={[0, 10, 64]} />
      <meshBasicMaterial color="cyan" transparent opacity={0.6} />
    </mesh>
  )
}
```

#### Audio-Reactive Visualizations
```jsx
// components/3D/AudioReactiveVisualization.jsx
function AudioReactiveVisualization({ frequencies }) {
  const shaderRef = useRef()
  
  const fragmentShader = `
    uniform float uTime;
    uniform vec3 uFrequencies;
    
    void main() {
      vec2 uv = gl_FragCoord.xy / resolution.xy;
      float wave = sin(uv.x * 10.0 + uTime) * uFrequencies.r;
      gl_FragColor = vec4(wave, wave * 0.5, wave * 0.8, 1.0);
    }
  `
  
  return (
    <mesh>
      <planeGeometry args={[20, 20]} />
      <shaderMaterial
        ref={shaderRef}
        fragmentShader={fragmentShader}
        uniforms={{
          uTime: { value: 0 },
          uFrequencies: { value: new THREE.Vector3(...frequencies) }
        }}
      />
    </mesh>
  )
}
```

## 🔄 Real-time Data Flow

### WebSocket Communication
```javascript
// Frontend WebSocket Hook
function useWebSocket() {
  const [socket, setSocket] = useState(null)
  const [audioData, setAudioData] = useState(null)
  const [sessionData, setSessionData] = useState(null)
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      switch (data.type) {
        case 'audio_spectrum':
          setAudioData(data.data)
          break
        case 'session_update':
          setSessionData(data.data)
          break
      }
    }
    
    setSocket(ws)
    return () => ws.close()
  }, [])
  
  return { socket, audioData, sessionData }
}
```

### Audio Analysis Pipeline
```python
# Backend WebSocket Handler
async def stream_audio_data(websocket: WebSocket):
    while True:
        # Get current audio analysis
        spectrum = audio_service.get_spectrum()
        frequencies = audio_service.get_active_frequencies()
        
        await websocket.send_json({
            "type": "audio_spectrum",
            "data": {
                "frequencies": frequencies,
                "amplitudes": spectrum,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        await asyncio.sleep(0.1)  # 10 Hz update rate
```

## 🎯 User Interface Design

### Main Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Header: Vajra.Stream Logo | Session Status | Settings    │
├─────────────┬───────────────────────────┬─────────────────┤
│             │                           │                 │
│ Sidebar     │     Main 3D Canvas       │   Control Panel │
│             │                           │                 │
│ • Sessions  │   (Planetary System      │ • Audio        │
│ • Prayers   │    / Sacred Geometry)    │ • Astrology    │
│ • Hardware  │                           │ • Intentions   │
│ • Settings  │   Audio Visualizer       │ • Hardware     │
│             │                           │                 │
└─────────────┴───────────────────────────┴─────────────────┘
```

### Control Panels
- **Audio Controls**: Frequency selection, prayer bowl mode, volume
- **Astrology Panel**: Real-time planetary positions, auspicious times
- **Intention Form**: Custom intentions, traditional prayers
- **Hardware Status**: Crystal grid status, amplifier levels

## 🚀 Implementation Phases

### Phase 1: Backend Foundation
1. FastAPI application structure
2. Core API endpoints (audio, sessions)
3. WebSocket streaming
4. Database models

### Phase 2: Frontend Foundation
1. React + Vite + R3F setup
2. Basic 3D scene (sacred geometry)
3. WebSocket integration
4. UI layout components

### Phase 3: Core Features
1. Audio generation and control
2. Real-time visualization
3. Session management
4. Basic astrology integration

### Phase 4: Advanced Features
1. Planetary system visualization
2. Prayer wheel 3D
3. Chakra energy body
4. Hardware control interface

### Phase 5: Polish & Optimization
1. Performance optimization
2. Advanced shaders
3. Mobile responsiveness
4. Comprehensive testing

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance async web framework
- **WebSockets**: Real-time communication
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **React Three Fiber**: 3D graphics
- **React Three Drei**: Helper components
- **Tailwind CSS**: Styling
- **Zustand**: State management

### Audio/Visual
- **Web Audio API**: Browser audio processing
- **Three.js**: 3D graphics engine
- **GLSL Shaders**: GPU-based visual effects
- **WebRTC**: Real-time audio streaming

This architecture provides a solid foundation for building a comprehensive web-based radionics and sacred technology platform that can control all aspects of the Vajra.Stream system.