# Vajra.Stream Frontend Implementation Guide

## 🎨 React + Vite + React Three Fiber Setup

### 1. Project Initialization
```bash
# Create new React + Vite project
npm create vite@latest vajra-stream-ui -- --template react
cd vajra-stream-ui

# Install dependencies
npm install

# Install Three.js and React Three Fiber
npm install three @react-three/fiber @react-three/drei

# Install additional dependencies
npm install @react-three/postprocessing  # Post-processing effects
npm install zustand                           # State management
npm install tailwindcss postcss autoprefixer   # Styling
npm install axios                             # HTTP client
npm install socket.io-client                   # WebSocket client

# Install dev dependencies
npm install -D @types/three
```

### 2. Project Structure
```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
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
│   │   │   ├── PrayerWheel3D.jsx
│   │   │   └── AudioReactiveVisualization.jsx
│   │   ├── 2D/                    # Canvas/SVG visualizations
│   │   │   ├── FrequencyBars.jsx
│   │   │   ├── Mandala.jsx
│   │   │   ├── SpectrumAnalyzer.jsx
│   │   │   └── RothkoMeditation.jsx
│   │   ├── UI/                    # Regular React components
│   │   │   ├── Controls/
│   │   │   │   ├── AudioControls.jsx
│   │   │   │   ├── SessionControls.jsx
│   │   │   │   ├── IntentionForm.jsx
│   │   │   │   └── HardwareControls.jsx
│   │   │   ├── Panels/
│   │   │   │   ├── AstrologyPanel.jsx
│   │   │   │   ├── FrequencyPanel.jsx
│   │   │   │   ├── PrayerPanel.jsx
│   │   │   │   └── SessionPanel.jsx
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
│   ├── stores/
│   │   ├── sessionStore.js      # Session state management
│   │   ├── audioStore.js        # Audio state management
│   │   └── uiStore.js          # UI state management
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
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

### 3. Tailwind CSS Configuration
```bash
# Initialize Tailwind CSS
npx tailwindcss init -p
```

**tailwind.config.js:**
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sacred': {
          'gold': '#FFD700',
          'purple': '#6B46C1',
          'blue': '#2563EB',
          'green': '#059669',
          'red': '#DC2626',
          'white': '#F9FAFB',
          'black': '#111827',
        },
        'chakra': {
          'root': '#FF0000',
          'sacral': '#FFA500',
          'solar': '#FFFF00',
          'heart': '#00FF00',
          'throat': '#0000FF',
          'third-eye': '#4B0082',
          'crown': '#9400D3',
        }
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 20s linear infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        }
      }
    },
  },
  plugins: [],
}
```

### 4. Main Application (src/App.jsx)
```jsx
import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from './components/Common/ErrorBoundary'
import { MainLayout } from './components/Layout/MainLayout'
import { BlessingScene } from './scenes/BlessingScene'
import { HealingScene } from './scenes/HealingScene'
import { MeditationScene } from './scenes/MeditationScene'
import { PurificationScene } from './scenes/PurificationScene'
import './styles/globals.css'

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <MainLayout>
          <Routes>
            <Route path="/" element={<BlessingScene />} />
            <Route path="/healing" element={<HealingScene />} />
            <Route path="/meditation" element={<MeditationScene />} />
            <Route path="/purification" element={<PurificationScene />} />
          </Routes>
        </MainLayout>
      </Router>
    </ErrorBoundary>
  )
}

export default App
```

### 5. State Management (src/stores/sessionStore.js)
```javascript
import { create } from 'zustand'

export const useSessionStore = create((set, get) => ({
  // State
  currentSession: null,
  sessions: [],
  isRunning: false,
  elapsedTime: 0,
  
  // Actions
  setCurrentSession: (session) => set({ currentSession: session }),
  
  addSession: (session) => set((state) => ({
    sessions: [...state.sessions, session]
  })),
  
  updateSession: (sessionId, updates) => set((state) => ({
    sessions: state.sessions.map(session =>
      session.id === sessionId ? { ...session, ...updates } : session
    ),
    currentSession: state.currentSession?.id === sessionId 
      ? { ...state.currentSession, ...updates } 
      : state.currentSession
  })),
  
  setRunning: (isRunning) => set({ isRunning }),
  
  setElapsedTime: (time) => set({ elapsedTime: time }),
  
  reset: () => set({
    currentSession: null,
    sessions: [],
    isRunning: false,
    elapsedTime: 0
  })
}))
```

### 6. WebSocket Hook (src/hooks/useWebSocket.js)
```javascript
import { useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import { useSessionStore } from '../stores/sessionStore'
import { useAudioStore } from '../stores/audioStore'

export const useWebSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const socketRef = useRef(null)
  
  const updateSession = useSessionStore((state) => state.updateSession)
  const setSpectrum = useAudioStore((state) => state.setSpectrum)
  const setFrequencies = useAudioStore((state) => state.setFrequencies)
  
  useEffect(() => {
    // Initialize WebSocket connection
    socketRef.current = io(url, {
      transports: ['websocket'],
      upgrade: false
    })
    
    const socket = socketRef.current
    
    // Connection events
    socket.on('connect', () => {
      console.log('Connected to WebSocket server')
      setIsConnected(true)
    })
    
    socket.on('disconnect', () => {
      console.log('Disconnected from WebSocket server')
      setIsConnected(false)
    })
    
    // Message handling
    socket.on('message', (data) => {
      setLastMessage(data)
      
      switch (data.type) {
        case 'audio_spectrum':
          setSpectrum(data.data.amplitudes)
          setFrequencies(data.data.frequencies)
          break
          
        case 'session_update':
          updateSession(data.data.session_id, data.data)
          break
          
        case 'astrology_update':
          // Handle astrology updates
          break
          
        default:
          console.log('Unknown message type:', data.type)
      }
    })
    
    // Cleanup
    return () => {
      socket.disconnect()
    }
  }, [url])
  
  // Send message function
  const sendMessage = (type, data) => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('message', { type, ...data })
    }
  }
  
  return {
    isConnected,
    lastMessage,
    sendMessage
  }
}
```

### 7. Audio Hook (src/hooks/useAudio.js)
```javascript
import { useEffect, useRef, useState } from 'react'
import { useAudioStore } from '../stores/audioStore'

export const useAudio = () => {
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const [isInitialized, setIsInitialized] = useState(false)
  
  const {
    isPlaying,
    volume,
    frequencies,
    spectrum,
    setPlaying,
    setVolume,
    setSpectrum,
    setFrequencies
  } = useAudioStore()
  
  // Initialize Web Audio API
  useEffect(() => {
    if (typeof window !== 'undefined' && !audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 2048
      setIsInitialized(true)
    }
  }, [])
  
  // Analyze audio spectrum
  const analyzeSpectrum = () => {
    if (!analyserRef.current) return
    
    const bufferLength = analyserRef.current.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyserRef.current.getByteFrequencyData(dataArray)
    
    // Convert to normalized values
    const normalizedSpectrum = Array.from(dataArray).map(value => value / 255)
    setSpectrum(normalizedSpectrum)
    
    // Continue analysis if playing
    if (isPlaying) {
      requestAnimationFrame(analyzeSpectrum)
    }
  }
  
  // Start/stop audio analysis
  useEffect(() => {
    if (isPlaying && isInitialized) {
      analyzeSpectrum()
    }
  }, [isPlaying, isInitialized])
  
  // Play audio frequency
  const playFrequency = (frequency, duration = 5) => {
    if (!audioContextRef.current) return
    
    const oscillator = audioContextRef.current.createOscillator()
    const gainNode = audioContextRef.current.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioContextRef.current.destination)
    gainNode.connect(analyserRef.current)
    
    oscillator.frequency.value = frequency
    oscillator.type = 'sine'
    
    gainNode.gain.value = volume
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioContextRef.current.currentTime + duration)
    
    oscillator.start()
    oscillator.stop(audioContextRef.current.currentTime + duration)
    
    setPlaying(true)
  }
  
  // Stop all audio
  const stopAudio = () => {
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
      analyserRef.current = null
      setIsInitialized(false)
    }
    setPlaying(false)
  }
  
  return {
    isPlaying,
    volume,
    frequencies,
    spectrum,
    isInitialized,
    playFrequency,
    stopAudio,
    setVolume,
    setFrequencies
  }
}
```

### 8. 3D Sacred Geometry - Flower of Life (src/components/3D/SacredGeometry/FlowerOfLife.jsx)
```jsx
import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useAudioStore } from '../../../stores/audioStore'

export const FlowerOfLife = ({ 
  radius = 10, 
  audioReactive = true, 
  color = '#00ffff' 
}) => {
  const meshRef = useRef()
  const { spectrum, frequencies } = useAudioStore()
  
  // Generate flower of life geometry
  const geometry = useMemo(() => {
    const group = new THREE.Group()
    const circles = []
    
    // Center circle
    circles.push({ x: 0, y: 0, z: 0 })
    
    // First ring - 6 circles
    for (let i = 0; i < 6; i++) {
      const angle = (i * Math.PI * 2) / 6
      circles.push({
        x: Math.cos(angle) * radius,
        y: 0,
        z: Math.sin(angle) * radius
      })
    }
    
    // Second ring - 12 circles
    for (let i = 0; i < 12; i++) {
      const angle = (i * Math.PI * 2) / 12
      circles.push({
        x: Math.cos(angle) * radius * 2,
        y: 0,
        z: Math.sin(angle) * radius * 2
      })
    }
    
    // Create circle geometries
    circles.forEach((circle, index) => {
      const geometry = new THREE.RingGeometry(0, radius, 32)
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide
      })
      
      const mesh = new THREE.Mesh(geometry, material)
      mesh.position.set(circle.x, circle.y, circle.z)
      mesh.userData = { index }
      
      group.add(mesh)
    })
    
    return group
  }, [radius, color])
  
  // Audio-reactive animation
  useFrame((state) => {
    if (!meshRef.current) return
    
    const time = state.clock.getElapsedTime()
    
    // Rotate the entire structure
    meshRef.current.rotation.y = time * 0.1
    
    if (audioReactive && spectrum && spectrum.length > 0) {
      // React to audio spectrum
      const avgAmplitude = spectrum.reduce((a, b) => a + b, 0) / spectrum.length
      const scale = 1 + avgAmplitude * 0.2
      
      meshRef.current.scale.setScalar(scale)
      
      // Pulse individual circles based on frequency bands
      meshRef.current.children.forEach((child, index) => {
        const frequencyIndex = index % spectrum.length
        const amplitude = spectrum[frequencyIndex] || 0
        child.material.opacity = 0.3 + amplitude * 0.7
      })
    }
  })
  
  return <primitive ref={meshRef} object={geometry} />
}
```

### 9. Planetary System (src/components/3D/PlanetarySystem.jsx)
```jsx
import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { OrbitControls, Stars } from '@react-three/drei'
import { Planet } from './Planet'
import { Sun } from './Sun'
import { ZodiacRing } from './ZodiacRing'
import { BlessingFlow } from './BlessingFlow'

export const PlanetarySystem = ({ 
  astrologyData, 
  blessings, 
  audioReactive = true 
}) => {
  const groupRef = useRef()
  
  // Calculate planetary positions
  const planets = useMemo(() => {
    if (!astrologyData?.planets) return []
    
    return Object.entries(astrologyData.planets).map(([name, data]) => ({
      name,
      position: calculatePlanetaryPosition(data),
      data,
      blessing: blessings?.[name] || null
    }))
  }, [astrologyData, blessings])
  
  // Animation
  useFrame((state) => {
    if (!groupRef.current) return
    
    const time = state.clock.getElapsedTime()
    
    // Slow rotation of entire system
    groupRef.current.rotation.y = time * 0.05
    
    // Update planetary positions based on real-time data
    planets.forEach((planet, index) => {
      const planetMesh = groupRef.current.children.find(child => 
        child.userData.name === planet.name
      )
      
      if (planetMesh) {
        // Orbital motion
        const orbitalSpeed = 1 / (index + 1) * 0.1
        const angle = time * orbitalSpeed
        const radius = 10 + index * 5
        
        planetMesh.position.x = Math.cos(angle) * radius
        planetMesh.position.z = Math.sin(angle) * radius
        
        // Audio-reactive scaling
        if (audioReactive && planet.blessing) {
          const intensity = planet.blessing.intensity || 0.5
          const scale = 1 + Math.sin(time * 2 + index) * intensity * 0.2
          planetMesh.scale.setScalar(scale)
        }
      }
    })
  })
  
  return (
    <group ref={groupRef}>
      {/* Background stars */}
      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade />
      
      {/* Sun at center */}
      <Sun />
      
      {/* Planets */}
      {planets.map((planet) => (
        <Planet
          key={planet.name}
          name={planet.name}
          position={planet.position}
          data={planet.data}
          blessing={planet.blessing}
          audioReactive={audioReactive}
        />
      ))}
      
      {/* Zodiac ring */}
      <ZodiacRing />
      
      {/* Blessing energy flows */}
      <BlessingFlow planets={planets} />
      
      {/* Camera controls */}
      <OrbitControls 
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={20}
        maxDistance={200}
      />
    </group>
  )
}

// Helper function to calculate planetary position
function calculatePlanetaryPosition(data) {
  const longitude = data.longitude || 0
  const latitude = data.latitude || 0
  const distance = data.distance || 15
  
  const x = Math.cos(longitude * Math.PI / 180) * distance
  const y = Math.sin(latitude * Math.PI / 180) * distance
  const z = Math.sin(longitude * Math.PI / 180) * distance
  
  return [x, y, z]
}
```

### 10. Audio-Reactive Visualization (src/components/3D/AudioReactiveVisualization.jsx)
```jsx
import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useAudioStore } from '../../stores/audioStore'

export const AudioReactiveVisualization = ({ 
  type = 'spectrum', 
  color = '#00ffff' 
}) => {
  const meshRef = useRef()
  const { spectrum, frequencies } = useAudioStore()
  
  // Custom shader for audio visualization
  const fragmentShader = `
    uniform float uTime;
    uniform vec3 uFrequencies;
    uniform vec2 uResolution;
    uniform float uSpectrum[32];
    
    varying vec2 vUv;
    
    void main() {
      vec2 uv = vUv;
      
      // Create wave patterns based on frequencies
      float wave1 = sin(uv.x * 10.0 + uTime * uFrequencies.r) * 0.5 + 0.5;
      float wave2 = sin(uv.y * 8.0 + uTime * uFrequencies.g) * 0.5 + 0.5;
      float wave3 = sin((uv.x + uv.y) * 6.0 + uTime * uFrequencies.b) * 0.5 + 0.5;
      
      // Mix waves with spectrum data
      float spectrumInfluence = 0.0;
      for(int i = 0; i < 32; i++) {
        float band = float(i) / 32.0;
        float distance = length(uv - vec2(band, 0.5));
        spectrumInfluence += uSpectrum[i] * (1.0 - smoothstep(0.0, 0.5, distance));
      }
      
      vec3 finalColor = vec3(wave1, wave2, wave3) * (1.0 + spectrumInfluence);
      
      gl_FragColor = vec4(finalColor, 1.0);
    }
  `
  
  const vertexShader = `
    varying vec2 vUv;
    
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `
  
  // Create shader material
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uFrequencies: { value: new THREE.Vector3(1, 2, 3) },
        uResolution: { value: new THREE.Vector2(800, 600) },
        uSpectrum: { value: new Array(32).fill(0) }
      },
      vertexShader,
      fragmentShader,
      transparent: true
    })
  }, [])
  
  // Update shader uniforms
  useFrame((state) => {
    if (!meshRef.current) return
    
    const time = state.clock.getElapsedTime()
    
    // Update time uniform
    material.uniforms.uTime.value = time
    
    // Update frequency uniforms
    if (frequencies && frequencies.length >= 3) {
      material.uniforms.uFrequencies.value.set(
        frequencies[0] || 0,
        frequencies[1] || 0,
        frequencies[2] || 0
      )
    }
    
    // Update spectrum uniform
    if (spectrum && spectrum.length >= 32) {
      material.uniforms.uSpectrum.value = spectrum.slice(0, 32)
    }
  })
  
  return (
    <mesh ref={meshRef}>
      <planeGeometry args={[20, 20]} />
      <primitive object={material} />
    </mesh>
  )
}
```

### 11. Main Scene (src/scenes/BlessingScene.jsx)
```jsx
import React, { useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Suspense } from 'react'
import { PlanetarySystem } from '../components/3D/PlanetarySystem'
import { FlowerOfLife } from '../components/3D/SacredGeometry/FlowerOfLife'
import { AudioReactiveVisualization } from '../components/3D/AudioReactiveVisualization'
import { AudioControls } from '../components/UI/Controls/AudioControls'
import { SessionControls } from '../components/UI/Controls/SessionControls'
import { IntentionForm } from '../components/UI/Controls/IntentionForm'
import { useWebSocket } from '../hooks/useWebSocket'
import { useSessionStore } from '../stores/sessionStore'
import { Loading } from '../components/Common/Loading'

export const BlessingScene = () => {
  const [visualizationType, setVisualizationType] = useState('planetary')
  const [astrologyData, setAstrologyData] = useState(null)
  const [blessings, setBlessings] = useState({})
  
  const { sendMessage } = useWebSocket('ws://localhost:8000/ws')
  const { currentSession, isRunning } = useSessionStore()
  
  // Handle session start
  const handleStartSession = (intention) => {
    sendMessage('start_session', {
      intention,
      duration: 300,
      audio_type: 'prayer_bowl'
    })
  }
  
  // Handle audio control
  const handleAudioControl = (action, params) => {
    sendMessage('audio_control', { action, ...params })
  }
  
  return (
    <div className="w-full h-screen bg-gray-900 text-white">
      {/* 3D Visualization Canvas */}
      <div className="absolute inset-0">
        <Canvas camera={{ position: [0, 0, 50], fov: 75 }}>
          <Suspense fallback={<Loading />}>
            {visualizationType === 'planetary' && (
              <PlanetarySystem 
                astrologyData={astrologyData}
                blessings={blessings}
                audioReactive={true}
              />
            )}
            {visualizationType === 'flower_of_life' && (
              <FlowerOfLife 
                audioReactive={true}
                color="#00ffff"
              />
            )}
            {visualizationType === 'audio_spectrum' && (
              <AudioReactiveVisualization />
            )}
          </Suspense>
        </Canvas>
      </div>
      
      {/* Control Panels */}
      <div className="absolute top-4 left-4 space-y-4">
        <IntentionForm onSubmit={handleStartSession} />
        <SessionControls />
      </div>
      
      <div className="absolute top-4 right-4">
        <AudioControls onControl={handleAudioControl} />
      </div>
      
      {/* Visualization Type Selector */}
      <div className="absolute bottom-4 left-4 bg-black bg-opacity-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">Visualization</h3>
        <div className="space-y-2">
          {['planetary', 'flower_of_life', 'audio_spectrum'].map(type => (
            <button
              key={type}
              onClick={() => setVisualizationType(type)}
              className={`block w-full text-left px-3 py-2 rounded ${
                visualizationType === type 
                  ? 'bg-sacred-blue text-white' 
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>
      
      {/* Session Status */}
      {currentSession && (
        <div className="absolute bottom-4 right-4 bg-black bg-opacity-50 p-4 rounded-lg">
          <h3 className="text-lg font-semibold">Session Active</h3>
          <p>Intention: {currentSession.intention}</p>
          <p>Status: {isRunning ? 'Running' : 'Paused'}</p>
        </div>
      )}
    </div>
  )
}
```

### 12. Vite Configuration (vite.config.js)
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  optimizeDeps: {
    include: ['three'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three', '@react-three/fiber', '@react-three/drei'],
        },
      },
    },
  },
})
```

### 13. Package.json Scripts
```json
{
  "name": "vajra-stream-ui",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "@react-three/drei": "^9.88.17",
    "@react-three/fiber": "^8.15.11",
    "@react-three/postprocessing": "^2.15.11",
    "axios": "^1.6.2",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1",
    "socket.io-client": "^4.7.4",
    "three": "^0.159.0",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@types/three": "^0.159.0",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.55.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "vite": "^5.0.8"
  }
}
```

## 🚀 Running the Frontend

### Development
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables
Create `.env` file:
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

This frontend implementation provides a comprehensive foundation for the Vajra.Stream web application with advanced 3D visualizations, real-time audio reactivity, and full integration with the backend API system.