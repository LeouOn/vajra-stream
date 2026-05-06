# Frontend Integration and Advanced Radionics Specification

## Overview

This document details the integration of the Unified Backend with the Frontend and the implementation of advanced radionics features including RNG/Attunement, Trend Padding, and Welz/Cybershaman/AetherOnePi concepts.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [UnifiedOrchestrator Integration](#unifiedorchestrator-integration)
3. [RadionicsEnhancer Module](#radionicsenhancer-module)
4. [Frontend Components](#frontend-components)
5. [WebSocket Protocols](#websocket-protocols)
6. [API Endpoints](#api-endpoints)
7. [Implementation Roadmap](#implementation-roadmap)

## Architecture Overview

### Current State
- Frontend uses React with Three.js for 3D visualizations
- Backend uses FastAPI with WebSocket support
- Existing services: Audio, Radionics, RNG Attunement, Blessings
- WebSocket connection managed by [`ConnectionManager`](backend/websocket/connection_manager.py:17)

### Enhanced Architecture
```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   Frontend      │◄──────────────►│    Backend      │
│                 │                 │                 │
│ - React UI      │                 │ - FastAPI       │
│ - Three.js      │                 │ - WebSocket     │
│ - Zustand Store │                 │ - Services      │
└─────────────────┘                 └─────────────────┘
         │                                   │
         │                                   ▼
         │                          ┌─────────────────┐
         │                          │UnifiedOrchestrator│
         │                          │                 │
         │                          │ - Event Bus     │
         │                          │ - Service Mgmt  │
         │                          │ - Session Mgmt  │
         └──────────────────────────►└─────────────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │RadionicsEnhancer│
                                   │                 │
                                   │ - RNG Attunement│
                                   │ - Trend Padding │
                                   │ - Structural    │
                                   │   Links         │
                                   └─────────────────┘
```

## UnifiedOrchestrator Integration

### Backend Integration

#### 1. UnifiedOrchestrator Service Wrapper
```python
# backend/core/services/unified_orchestrator_service.py
class UnifiedOrchestratorService:
    def __init__(self):
        self.orchestrator = UnifiedOrchestrator()
        self.active_sessions = {}
        self.event_bus = self.orchestrator.event_bus
    
    async def create_unified_session(self, config: Dict) -> str:
        """Create session through UnifiedOrchestrator"""
        session_id = self.orchestrator.create_session(
            intention=config['intention'],
            targets=config['targets'],
            modalities=config['modalities'],
            duration=config['duration']
        )
        
        # Register with WebSocket manager
        await connection_manager.send_orchestrator_update({
            'session_id': session_id,
            'status': 'created',
            'config': config
        })
        
        return session_id
    
    async def start_unified_session(self, session_id: str) -> bool:
        """Start unified session"""
        success = await self.orchestrator.start_session(session_id)
        
        if success:
            await connection_manager.send_orchestrator_update({
                'session_id': session_id,
                'status': 'running',
                'start_time': time.time()
            })
        
        return success
```

#### 2. WebSocket Integration
```python
# backend/websocket/connection_manager.py (extensions)
class ConnectionManager:
    async def send_orchestrator_update(self, session_data: Dict):
        """Send UnifiedOrchestrator session updates"""
        await self.broadcast({
            "type": "orchestrator_session",
            "data": session_data,
            "timestamp": time.time()
        })
    
    async def send_radionics_update(self, radionics_data: Dict):
        """Send radionics session updates"""
        await self.broadcast({
            "type": "radionics_session",
            "data": radionics_data,
            "timestamp": time.time()
        })
    
    async def send_rng_attunement_update(self, rng_data: Dict):
        """Send RNG attunement updates"""
        await self.broadcast({
            "type": "rng_attunement",
            "data": rng_data,
            "timestamp": time.time()
        })
```

### Frontend Integration

#### 1. UnifiedOrchestrator Hook
```javascript
// frontend/src/hooks/useUnifiedOrchestrator.js
export const useUnifiedOrchestrator = () => {
  const [orchestratorSessions, setOrchestratorSessions] = useState({});
  const [radionicsSessions, setRadionicsSessions] = useState({});
  const { sendMessage, isConnected } = useWebSocket();
  
  const handleOrchestratorMessage = useCallback((data) => {
    switch (data.type) {
      case 'orchestrator_session':
        setOrchestratorSessions(prev => ({
          ...prev,
          [data.data.session_id]: data.data
        }));
        break;
      case 'radionics_session':
        setRadionicsSessions(prev => ({
          ...prev,
          [data.data.session_id]: data.data
        }));
        break;
      case 'rng_attunement':
        // Handle RNG attunement updates
        break;
    }
  }, []);
  
  const createUnifiedSession = useCallback(async (config) => {
    const response = await fetch('/api/v1/orchestrator/session/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    return response.json();
  }, []);
  
  const startUnifiedSession = useCallback(async (sessionId) => {
    const response = await fetch(`/api/v1/orchestrator/session/${sessionId}/start`, {
      method: 'POST'
    });
    
    return response.json();
  }, []);
  
  return {
    orchestratorSessions,
    radionicsSessions,
    createUnifiedSession,
    startUnifiedSession,
    handleOrchestratorMessage
  };
};
```

## RadionicsEnhancer Module

### Core Architecture

#### 1. Main Module
```python
# core/radionics_enhancer.py
class RadionicsEnhancer:
    def __init__(self):
        self.rng_service = get_rng_service()
        self.scalar_broadcaster = IntegratedScalarRadionicsBroadcaster()
        self.trend_padding_engine = TrendPaddingEngine()
        self.structural_link_processor = StructuralLinkProcessor()
        self.cybershaman_matrix = CybershamanMatrix()
        self.aetherone_interface = AetherOnePiInterface()
    
    async def create_enhanced_radionics_session(self, config: Dict) -> Dict:
        """Create comprehensive radionics session with all enhancements"""
        
        # 1. Create structural links
        structural_links = []
        for target in config.get('targets', []):
            link = await self.structural_link_processor.create_structural_link(
                config.get('link_type', 'digital'),
                target
            )
            structural_links.append(link)
        
        # 2. Apply RNG attunement if enabled
        if config.get('rng_attunement', False):
            rng_config = await self._apply_rng_attunement(config)
            config.update(rng_config)
        
        # 3. Apply trend padding
        if config.get('trend_padding', False):
            trend_config = await self.trend_padding_engine.apply_trend_padding_config(config)
            config.update(trend_config)
        
        # 4. Create transfer diagram
        diagram_type = config.get('diagram_type', 'welz_basic')
        transfer_diagram = await self.structural_link_processor.create_transfer_diagram(
            diagram_type,
            IntentionType(config.get('intention', 'healing')),
            structural_links[0] if structural_links else None
        )
        
        # 5. Create Cybershaman matrix
        cybershaman_matrix = await self.cybershaman_matrix.create_cybershaman_broadcast(
            IntentionType(config.get('intention', 'healing')),
            config.get('targets', []),
            structural_links
        )
        
        # 6. Create AetherOnePi session
        aetherone_session = await self.aetherone_interface.create_digital_radionics_session(config)
        
        return {
            'session_id': str(uuid.uuid4()),
            'config': config,
            'structural_links': structural_links,
            'transfer_diagram': transfer_diagram,
            'cybershaman_matrix': cybershaman_matrix,
            'aetherone_session': aetherone_session,
            'timestamp': time.time()
        }
```

#### 2. RNG Attunement Integration
```python
# core/rng_attunement_enhancer.py
class RNGAttunementEnhancer:
    def __init__(self):
        self.rng_service = get_rng_service()
        self.attunement_history = []
    
    async def apply_rng_attunement(self, config: Dict) -> Dict:
        """Apply RNG attunement to session configuration"""
        
        # Create RNG session
        session_id = self.rng_service.create_session(
            baseline_tone_arm=5.0,
            sensitivity=1.0
        )
        
        # Take multiple readings for stability
        readings = []
        for _ in range(5):
            reading = self.rng_service.get_reading(session_id)
            readings.append(reading)
            await asyncio.sleep(0.5)
        
        # Analyze readings
        avg_coherence = sum(r.coherence for r in readings) / len(readings)
        floating_needles = sum(1 for r in readings if r.needle_state == NeedleState.FLOATING)
        
        # Determine optimal timing
        optimal_timing = {
            'optimal': avg_coherence > 0.7 and floating_needles >= 2,
            'coherence': avg_coherence,
            'confidence': floating_needles / len(readings),
            'recommended_wait': 0 if avg_coherence > 0.8 else 60
        }
        
        # Adjust intensity based on RNG readings
        base_intensity = config.get('scalar_intensity', 0.8)
        last_reading = readings[-1]
        
        intensity_modifiers = {
            NeedleState.FLOATING: 1.2,
            NeedleState.RISING: 1.1,
            NeedleState.FALLING: 0.9,
            NeedleState.ROCKSLAM: 1.5,
            NeedleState.THETA_BOP: 1.0,
            NeedleState.STUCK: 0.8
        }
        
        modifier = intensity_modifiers.get(last_reading.needle_state, 1.0)
        adjusted_intensity = min(base_intensity * modifier, 1.0)
        
        return {
            'rng_session_id': session_id,
            'rng_readings': [r.__dict__ for r in readings],
            'rng_timing': optimal_timing,
            'adjusted_intensity': adjusted_intensity,
            'rng_attunement_applied': True
        }
```

#### 3. Trend Padding Engine
```python
# core/trend_padding.py
class TrendPaddingEngine:
    def __init__(self):
        self.padding_patterns = {
            'exponential': self._exponential_padding,
            'linear': self._linear_padding,
            'fibonacci': self._fibonacci_padding,
            'sacred': self._sacred_sequence_padding
        }
        self.carrier_frequencies = {
            'schumann': 7.83,
            'earth_om': 136.1,
            'solar': 126.22,
            'lunar': 210.42
        }
    
    async def apply_trend_padding_config(self, config: Dict) -> Dict:
        """Apply trend padding configuration"""
        
        padding_type = config.get('trend_padding_type', 'exponential')
        carrier_wave = config.get('carrier_wave', 'schumann')
        repetitions = config.get('repetitions', 108)
        
        # Get carrier frequency
        carrier_freq = self.carrier_frequencies.get(carrier_wave, 7.83)
        
        # Calculate padding parameters
        padding_params = {
            'padding_type': padding_type,
            'carrier_frequency': carrier_freq,
            'repetitions': repetitions,
            'amplification_factor': self._calculate_amplification_factor(padding_type, repetitions)
        }
        
        # Adjust duration for padding
        base_duration = config.get('duration_seconds', 600)
        padded_duration = base_duration * (1 + repetitions * 0.1)  # 10% increase per repetition
        
        return {
            **config,
            'trend_padding_params': padding_params,
            'duration_seconds': padded_duration,
            'trend_padding_applied': True
        }
```

## Frontend Components

### 1. Advanced Radionics Panel
- **Location**: [`frontend/src/components/UI/AdvancedRadionicsPanel.jsx`](frontend/src/components/UI/AdvancedRadionicsPanel.jsx)
- **Features**:
  - Intention selection with frequency mapping
  - Structural link type selection
  - RNG attunement controls with real-time readings
  - Trend padding configuration
  - Carrier wave selection

### 2. Transfer Diagram Visualization
- **Location**: [`frontend/src/components/2D/TransferDiagram.jsx`](frontend/src/components/2D/TransferDiagram.jsx)
- **Features**:
  - 3D visualization of Welz basic diagrams
  - Cybershaman matrix rendering
  - Sacred geometry patterns
  - Real-time animation based on session state

### 3. AetherOnePi Digital Interface
- **Location**: [`frontend/src/components/UI/AetherOneInterface.jsx`](frontend/src/components/UI/AetherOneInterface.jsx)
- **Features**:
  - 10 rate dials with real-time adjustment
  - LED status indicators
  - Control buttons (Scan, Broadcast, Analyze)
  - Digital display for status messages

### 4. Structural Links Manager
- **Location**: [`frontend/src/components/UI/StructuralLinksManager.jsx`](frontend/src/components/UI/StructuralLinksManager.jsx)
- **Features**:
  - Create and manage structural links
  - Link strength visualization
  - Target information display
  - Link type selection

## WebSocket Protocols

### Message Types

#### 1. Orchestrator Messages
```javascript
// Create unified session
{
  "type": "create_unified_session",
  "data": {
    "intention": "healing",
    "targets": [...],
    "modalities": ["radionics", "audio"],
    "duration": 3600
  }
}

// Session update
{
  "type": "orchestrator_session",
  "data": {
    "session_id": "uuid",
    "status": "running",
    "progress": 0.75,
    "active_modalities": ["radionics"],
    "timestamp": 1234567890
  }
}
```

#### 2. Radionics Messages
```javascript
// Start advanced radionics
{
  "type": "start_advanced_radionics",
  "data": {
    "intention": "healing",
    "targets": [...],
    "structural_links": [...],
    "trend_padding": {
      "type": "fibonacci",
      "carrier_wave": "earth_om"
    },
    "rng_attunement": true
  }
}

// Radionics session update
{
  "type": "radionics_session",
  "data": {
    "session_id": "uuid",
    "intensity": 0.85,
    "frequency": 528.0,
    "structural_link_strength": 0.92,
    "rng_coherence": 0.78,
    "trend_padding_progress": 0.65
  }
}
```

#### 3. RNG Attunement Messages
```javascript
// Request RNG reading
{
  "type": "request_rng_reading",
  "data": {
    "session_id": "uuid"
  }
}

// RNG reading update
{
  "type": "rng_attunement",
  "data": {
    "session_id": "uuid",
    "needle_state": "floating",
    "coherence": 0.82,
    "floating_needle_score": 0.91,
    "recommended_intensity": 1.2
  }
}
```

## API Endpoints

### Unified Orchestrator Endpoints

#### 1. Session Management
```python
# POST /api/v1/orchestrator/session/create
{
  "intention": "healing",
  "targets": [{"type": "individual", "identifier": "John Doe"}],
  "modalities": ["radionics", "audio", "crystal"],
  "duration": 3600
}

# POST /api/v1/orchestrator/session/{session_id}/start
# POST /api/v1/orchestrator/session/{session_id}/stop
# GET /api/v1/orchestrator/session/{session_id}/status
# GET /api/v1/orchestrator/sessions
```

### Advanced Radionics Endpoints

#### 1. Structural Links
```python
# POST /api/v1/radionics/structural-link
{
  "type": "digital",
  "target": {
    "name": "John Doe",
    "photo": "base64_image",
    "intention": "healing"
  }
}

# GET /api/v1/radionics/structural-links
# DELETE /api/v1/radionics/structural-link/{link_id}
```

#### 2. Transfer Diagrams
```python
# POST /api/v1/radionics/transfer-diagram
{
  "diagram_type": "welz_basic",
  "intention": "healing",
  "structural_link": {...}
}

# GET /api/v1/radionics/transfer-diagram/{diagram_id}
```

#### 3. Trend Padding
```python
# POST /api/v1/radionics/trend-padding/apply
{
  "intention_signal": [...],
  "padding_type": "fibonacci",
  "carrier_wave": "earth_om",
  "repetitions": 108
}

# GET /api/v1/radionics/trend-padding/patterns
```

#### 4. Cybershaman Matrix
```python
# POST /api/v1/radionics/cybershaman/create
{
  "intention": "healing",
  "targets": [...],
  "structural_links": [...]
}

# GET /api/v1/radionics/cybershaman/matrix/{matrix_id}
```

#### 5. AetherOnePi Interface
```python
# POST /api/v1/radionics/aetherone/session/create
{
  "intention": "healing",
  "targets": [...],
  "rate_dials": [25.5, 45.2, ...]
}

# POST /api/v1/radionics/aetherone/button/{button_id}/press
# GET /api/v1/radionics/aetherone/session/{session_id}
```

## Implementation Roadmap

### Phase 1: Core Integration (2 weeks)
1. **UnifiedOrchestrator Service Integration**
   - Create service wrapper
   - Integrate with WebSocket manager
   - Add basic session management

2. **Frontend Hook Development**
   - Implement useUnifiedOrchestrator hook
   - Add WebSocket message handling
   - Create basic session UI

### Phase 2: RadionicsEnhancer Module (3 weeks)
1. **Core Module Development**
   - Implement RadionicsEnhancer class
   - Add RNG attunement integration
   - Create trend padding engine

2. **API Endpoints**
   - Create structural link endpoints
   - Add transfer diagram generation
   - Implement trend padding API

### Phase 3: Advanced Features (3 weeks)
1. **Welz/Cybershaman Features**
   - Implement structural link processor
   - Create Cybershaman matrix generator
   - Add AetherOnePi interface

2. **Frontend Components**
   - Build advanced radionics panel
   - Create transfer diagram visualization
   - Implement AetherOnePi interface

### Phase 4: Integration & Testing (2 weeks)
1. **Full Integration**
   - Connect all components
   - Implement WebSocket protocols
   - Add error handling

2. **Testing & Optimization**
   - Unit tests for all modules
   - Integration testing
   - Performance optimization

### Phase 5: Documentation & Deployment (1 week)
1. **Documentation**
   - API documentation
   - User guides
   - Developer documentation

2. **Deployment**
   - Production configuration
   - Monitoring setup
   - Backup procedures

## Technical Considerations

### Performance
- Trend padding can significantly increase processing time
- Multiple RNG readings may impact performance
- WebSocket message rate limiting may be needed

### Security
- Validate all user inputs for radionics configurations
- Rate limit API calls to prevent abuse
- Secure WebSocket connections

### Scalability
- Session management should handle concurrent sessions
- RNG service should support multiple concurrent readings
- WebSocket connections should be efficiently managed

### Reliability
- Implement proper error handling for all radionics operations
- Add retry mechanisms for failed operations
- Log all radionics sessions for analysis

## Conclusion

This specification provides a comprehensive plan for integrating the Unified Backend with the Frontend and implementing advanced radionics features. The modular approach allows for incremental development and testing, ensuring a robust and scalable system.

The integration maintains compatibility with existing systems while adding powerful new capabilities for radionics practitioners, including RNG attunement, trend padding, and digital interfaces inspired by traditional radionics devices.