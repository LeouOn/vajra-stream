# Vajra Stream Refactoring Plan

## Overview

This document outlines the specific steps to refactor the Vajra Stream codebase into the unified architecture described in [`UNIFIED_ARCHITECTURE.md`](UNIFIED_ARCHITECTURE.md:1). The refactoring is organized into phases to minimize disruption while systematically improving the system.

## Phase 1: Foundation Enhancement (Week 1-2)

### 1.1 Enhance Event Bus

**Current State:** [`infrastructure/event_bus.py`](infrastructure/event_bus.py:1) provides basic in-process event communication

**Tasks:**
1. Add event persistence for replay and debugging
2. Implement event filtering and routing
3. Add event middleware for logging and metrics
4. Create event registry for type safety

**Implementation:**
```python
# Enhanced event bus in infrastructure/enhanced_event_bus.py
class EnhancedEventBus(SimpleEventBus):
    def __init__(self, persistence_path: str = None):
        super().__init__()
        self.persistence_path = persistence_path
        self.event_history = []
        self.middleware_chain = []
        self.filters = {}
    
    def persist_event(self, event: DomainEvent):
        """Persist event for replay"""
        if self.persistence_path:
            with open(self.persistence_path, 'a') as f:
                f.write(json.dumps({
                    'timestamp': event.timestamp.isoformat(),
                    'type': type(event).__name__,
                    'data': asdict(event)
                }) + '\n')
    
    def add_filter(self, event_type: type, filter_func: Callable):
        """Add filter for specific event type"""
        if event_type not in self.filters:
            self.filters[event_type] = []
        self.filters[event_type].append(filter_func)
```

### 1.2 Create Missing Service Wrappers

#### 1.2.1 Crystal Service Wrapper

**Current State:** [`hardware/crystal_broadcaster.py`](hardware/crystal_broadcaster.py:1) operates independently

**Create:** `modules/crystal.py`
```python
class CrystalService(Protocol):
    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self.level2 = Level2CrystalBroadcaster()
        self.level3 = Level3AmplifiedBroadcaster()
    
    def broadcast_intention(
        self,
        intention: str,
        frequencies: List[float] = None,
        duration: int = 300,
        hardware_level: int = 2,
        prayer_bowl_mode: bool = True
    ) -> Dict[str, Any]:
        """Broadcast intention through crystal grid"""
        
        # Publish start event
        if self.event_bus:
            self.event_bus.publish(CrystalBroadcastStarted(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                intention=intention,
                hardware_level=hardware_level
            ))
        
        # Execute broadcast
        if hardware_level == 3:
            self.level3.generate_amplified_blessing(intention, duration)
        else:
            self.level2.generate_5_channel_blessing(intention, duration)
        
        # Publish completion event
        if self.event_bus:
            self.event_bus.publish(CrystalBroadcastCompleted(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                intention=intention,
                duration=duration
            ))
        
        return {
            'intention': intention,
            'duration': duration,
            'hardware_level': hardware_level,
            'status': 'completed'
        }
```

#### 1.2.2 Enhanced Scalar Wave Service

**Current State:** [`modules/scalar_waves.py`](modules/scalar_waves.py:1) provides basic wrapper

**Enhancements needed:**
1. Session management for wave generation
2. Wave conflict resolution
3. Real-time modulation capabilities

**Create:** `modules/enhanced_scalar_waves.py`
```python
class WaveSession:
    def __init__(self, session_id: str, method: str, count: int, priority: int):
        self.session_id = session_id
        self.method = method
        self.count = count
        self.priority = priority
        self.start_time = time.time()
        self.values = []
        self.is_active = True

class EnhancedScalarWaveService(ScalarWaveGenerator):
    def __init__(self, event_bus: EventBus = None):
        super().__init__(event_bus)
        self.active_sessions = {}
        self.session_queue = []
        self.max_concurrent_sessions = 3
    
    def create_wave_session(
        self,
        method: str,
        count: int,
        priority: WavePriority = WavePriority.NORMAL,
        intensity: float = 1.0
    ) -> str:
        """Create managed wave generation session"""
        
        session_id = str(uuid.uuid4())
        session = WaveSession(session_id, method, count, priority.value)
        
        # Check for conflicts
        if self._check_conflicts(method):
            self.session_queue.append(session)
            return session_id
        
        # Start session if slot available
        if len(self.active_sessions) < self.max_concurrent_sessions:
            self._start_session(session)
        else:
            self.session_queue.append(session)
        
        return session_id
    
    def modulate_session(
        self,
        session_id: str,
        modulation: WaveModulation
    ) -> bool:
        """Modulate active wave session"""
        if session_id not in self.active_sessions:
            return False
        
        session = self.active_sessions[session_id]
        # Apply modulation to session
        session.apply_modulation(modulation)
        
        # Publish modulation event
        if self.event_bus:
            self.event_bus.publish(WaveSessionModulated(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                session_id=session_id,
                modulation=modulation
            ))
        
        return True
```

#### 1.2.3 Blessing Router Service

**Current State:** [`modules/blessings.py`](modules/blessings.py:1) provides basic blessing generation

**Create:** `modules/blessing_router.py`
```python
class TargetSpecification:
    def __init__(self, target_type: TargetType, identifier: str, metadata: Dict = None):
        self.target_type = target_type
        self.identifier = identifier
        self.metadata = metadata or {}

class BlessingRouter:
    def __init__(self, event_bus: EventBus = None):
        self.event_bus = event_bus
        self.target_resolvers = {}
        self.delivery_channels = {}
        self.blessing_service = BlessingService(event_bus)
        self._register_default_resolvers()
    
    def route_blessing(
        self,
        intention: str,
        target_spec: TargetSpecification,
        delivery_method: DeliveryMethod = DeliveryMethod.DIRECT,
        timing: TimingSpecification = None
    ) -> str:
        """Route blessing to appropriate target and channel"""
        
        blessing_id = str(uuid.uuid4())
        
        # Resolve target
        resolver = self.target_resolvers.get(target_spec.target_type)
        if not resolver:
            raise ValueError(f"No resolver for target type: {target_spec.target_type}")
        
        resolved_target = resolver.resolve(target_spec)
        
        # Generate blessing
        blessing = self.blessing_service.generate_blessing(
            target_name=resolved_target.name,
            intention=intention,
            tradition=resolved_target.tradition
        )
        
        # Route to delivery channel
        channel = self.delivery_channels.get(delivery_method)
        if not channel:
            raise ValueError(f"No channel for delivery method: {delivery_method}")
        
        # Execute delivery
        delivery_result = channel.deliver(blessing, resolved_target, timing)
        
        # Publish events
        if self.event_bus:
            self.event_bus.publish(BlessingRouted(
                timestamp=datetime.now(),
                event_id=blessing_id,
                intention=intention,
                target_spec=target_spec,
                delivery_method=delivery_method
            ))
        
        return blessing_id
```

### 1.3 Configuration Management Enhancement

**Current State:** [`config/settings.py`](config/settings.py:1) has basic configuration

**Enhancements needed:**
1. Environment-specific configurations
2. Configuration validation
3. Runtime configuration updates

**Create:** `config/enhanced_settings.py`
```python
class EnhancedConfig:
    def __init__(self, env: str = 'development'):
        self.env = env
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from multiple sources"""
        # Default config
        config = {
            'audio': {
                'sample_rate': 44100,
                'max_volume': 0.8,
                'prayer_bowl_mode': True
            },
            'hardware': {
                'level': 2,
                'amplifier_connected': False,
                'bass_shaker_connected': False
            },
            'events': {
                'persistence_enabled': True,
                'max_history': 10000
            }
        }
        
        # Environment-specific overrides
        env_file = f'config/{self.env}.yaml'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_config = yaml.safe_load(f)
                config.update(env_config)
        
        # Runtime overrides
        if os.environ.get('VAJRA_CONFIG'):
            runtime_config = json.loads(os.environ['VAJRA_CONFIG'])
            config.update(runtime_config)
        
        return config
    
    def _validate_config(self):
        """Validate configuration values"""
        if self.config['audio']['max_volume'] > 1.0:
            raise ValueError("max_volume cannot exceed 1.0")
        
        if self.config['hardware']['level'] not in [2, 3]:
            raise ValueError("hardware.level must be 2 or 3")
```

## Phase 2: Integration Layer (Week 3-4)

### 2.1 Implement Unified Orchestrator

**Current State:** [`scripts/vajra_orchestrator.py`](scripts/vajra_orchestrator.py:1) operates outside module system

**Create:** `orchestrator/unified_orchestrator.py`
```python
class UnifiedOrchestrator:
    def __init__(self, config: EnhancedConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.services = self._initialize_services()
        self.session_manager = SessionManager(event_bus)
        self.intent_router = IntentRouter(event_bus)
        self.target_resolver = TargetResolver(event_bus)
    
    def _initialize_services(self) -> Dict[str, Any]:
        """Initialize all services with dependency injection"""
        return {
            'audio': AudioService(event_bus),
            'crystal': CrystalService(event_bus),
            'scalar_waves': EnhancedScalarWaveService(event_bus),
            'blessings': BlessingService(event_bus),
            'blessing_router': BlessingRouter(event_bus),
            'astrology': AstrologyService(event_bus),
            'healing': HealingService(event_bus),
            'visualization': VisualizationService(event_bus),
            'time_cycles': TimeCyclesService(event_bus)
        }
    
    def create_session(
        self,
        intention: str,
        targets: List[TargetSpecification],
        modalities: List[Modality],
        duration: int,
        scheduling: SchedulingSpecification = None
    ) -> str:
        """Create unified healing/blessing session"""
        
        session_id = str(uuid.uuid4())
        
        # Create session
        session = HealingSession(
            session_id=session_id,
            intention=intention,
            targets=targets,
            modalities=modalities,
            duration=duration,
            scheduling=scheduling
        )
        
        # Register session
        self.session_manager.register_session(session)
        
        # Publish session created event
        self.event_bus.publish(SessionCreated(
            timestamp=datetime.now(),
            event_id=session_id,
            session=session
        ))
        
        return session_id
    
    def execute_session(self, session_id: str):
        """Execute orchestrated session"""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Execute each modality
        for modality in session.modalities:
            self._execute_modality(session, modality)
    
    def _execute_modality(self, session: HealingSession, modality: Modality):
        """Execute specific modality for session"""
        if modality == Modality.CRYSTAL:
            self._execute_crystal_modality(session)
        elif modality == Modality.SCALAR_WAVES:
            self._execute_scalar_wave_modality(session)
        elif modality == Modality.BLESSING:
            self._execute_blessing_modality(session)
        # ... other modalities
```

### 2.2 Hardware Integration Layer

**Create:** `hardware/hardware_manager.py`
```python
class HardwareManager:
    def __init__(self, event_bus: EventBus, config: EnhancedConfig):
        self.event_bus = event_bus
        self.config = config
        self.connected_devices = {}
        self.device_capabilities = {}
    
    def discover_devices(self) -> List[Device]:
        """Discover available hardware devices"""
        devices = []
        
        # Check for audio devices
        audio_devices = self._discover_audio_devices()
        devices.extend(audio_devices)
        
        # Check for crystal grid
        if self.config.config['hardware']['level'] >= 2:
            crystal_device = CrystalDevice(level=2)
            devices.append(crystal_device)
        
        # Check for amplifier
        if self.config.config['hardware']['level'] == 3:
            amplifier_device = AmplifierDevice()
            devices.append(amplifier_device)
        
        return devices
    
    def connect_device(self, device: Device) -> bool:
        """Connect to hardware device"""
        try:
            if device.connect():
                self.connected_devices[device.id] = device
                self.event_bus.publish(DeviceConnected(
                    timestamp=datetime.now(),
                    event_id=str(uuid.uuid4()),
                    device_id=device.id,
                    device_type=device.type
                ))
                return True
        except Exception as e:
            self.event_bus.publish(DeviceConnectionFailed(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                device_id=device.id,
                error=str(e)
            ))
        return False
```

### 2.3 Target Resolution System

**Create:** `targeting/target_resolver.py`
```python
class TargetResolver:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.resolvers = {}
        self._register_default_resolvers()
    
    def _register_default_resolvers(self):
        """Register default target resolvers"""
        self.resolvers[TargetType.INDIVIDUAL] = IndividualResolver()
        self.resolvers[TargetType.LOCATION] = LocationResolver()
        self.resolvers[TargetType.POPULATION] = PopulationResolver()
        self.resolvers[TargetType.TEMPORAL] = TemporalResolver()
        self.resolvers[TargetType.ENERGETIC] = EnergeticResolver()
    
    def resolve(self, target_spec: TargetSpecification) -> ResolvedTarget:
        """Resolve target specification to concrete target"""
        resolver = self.resolvers.get(target_spec.target_type)
        if not resolver:
            raise ValueError(f"No resolver for target type: {target_spec.target_type}")
        
        resolved = resolver.resolve(target_spec)
        
        # Publish resolution event
        self.event_bus.publish(TargetResolved(
            timestamp=datetime.now(),
            event_id=str(uuid.uuid4()),
            target_spec=target_spec,
            resolved_target=resolved
        ))
        
        return resolved

class IndividualResolver:
    def resolve(self, target_spec: TargetSpecification) -> ResolvedTarget:
        """Resolve individual person target"""
        # Look up in database
        # Validate information
        # Return resolved target
        pass

class LocationResolver:
    def resolve(self, target_spec: TargetSpecification) -> ResolvedTarget:
        """Resolve geographic location target"""
        # Parse coordinates
        # Get astrocartography data
        # Return resolved target
        pass
```

## Phase 3: Advanced Features (Week 5-6)

### 3.1 Wave Management System

**Create:** `waves/wave_manager.py`
```python
class WaveManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_sessions = {}
        self.wave_priorities = {}
        self.conflict_resolver = WaveConflictResolver()
    
    def create_session(
        self,
        intention: str,
        methods: List[str],
        duration: int,
        priority: WavePriority = WavePriority.NORMAL
    ) -> str:
        """Create managed wave generation session"""
        
        session_id = str(uuid.uuid4())
        
        # Check for conflicts
        conflicts = self._check_conflicts(methods)
        if conflicts:
            resolution = self.conflict_resolver.resolve(conflicts, priority)
            if resolution.action == ConflictAction.QUEUE:
                # Queue session
                pass
            elif resolution.action == ConflictAction.MODIFY:
                # Modify parameters
                methods = resolution.modified_methods
        
        # Create session
        session = WaveSession(
            session_id=session_id,
            intention=intention,
            methods=methods,
            duration=duration,
            priority=priority
        )
        
        self.active_sessions[session_id] = session
        
        # Start generation
        self._start_wave_generation(session)
        
        return session_id
    
    def _check_conflicts(self, methods: List[str]) -> List[WaveConflict]:
        """Check for potential conflicts with active sessions"""
        conflicts = []
        
        for active_id, active_session in self.active_sessions.items():
            for method in methods:
                if method in active_session.methods:
                    conflicts.append(WaveConflict(
                        session1_id=active_id,
                        session2_id=None,  # New session
                        method=method,
                        conflict_type=ConflictType.METHOD_OVERLAP
                    ))
        
        return conflicts
```

### 3.2 Blessing Routing System

**Create:** `blessings/blessing_router.py`
```python
class BlessingRouter:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.target_resolvers = {}
        self.delivery_channels = {}
        self.blessing_templates = {}
        self._initialize_components()
    
    def route_blessing(
        self,
        intention: str,
        target_spec: TargetSpecification,
        delivery_method: DeliveryMethod,
        timing: TimingSpecification = None
    ) -> str:
        """Route blessing to appropriate target and channel"""
        
        blessing_id = str(uuid.uuid4())
        
        # Resolve target
        resolver = self.target_resolvers.get(target_spec.target_type)
        resolved_target = resolver.resolve(target_spec)
        
        # Generate blessing
        blessing = self._generate_blessing(intention, resolved_target)
        
        # Select delivery channel
        channel = self.delivery_channels.get(delivery_method)
        
        # Schedule delivery
        if timing:
            self._schedule_delivery(blessing_id, blessing, channel, resolved_target, timing)
        else:
            self._deliver_blessing(blessing_id, blessing, channel, resolved_target)
        
        return blessing_id
    
    def _generate_blessing(self, intention: str, target: ResolvedTarget) -> Blessing:
        """Generate blessing based on intention and target"""
        template = self.blessing_templates.get(target.tradition)
        
        blessing_text = template.generate(
            intention=intention,
            target_name=target.name,
            target_attributes=target.attributes
        )
        
        return Blessing(
            text=blessing_text,
            intention=intention,
            target=target,
            tradition=target.tradition
        )
```

### 3.3 Web Integration Layer

**Create:** `api/vajra_api.py`
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vajra Stream API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
@app.on_event("startup")
async def startup_event():
    # Initialize orchestrator
    config = EnhancedConfig()
    event_bus = EnhancedEventBus()
    app.state.orchestrator = UnifiedOrchestrator(config, event_bus)

@app.post("/sessions")
async def create_session(request: CreateSessionRequest):
    """Create new healing/blessing session"""
    orchestrator = app.state.orchestrator
    
    session_id = orchestrator.create_session(
        intention=request.intention,
        targets=request.targets,
        modalities=request.modalities,
        duration=request.duration,
        scheduling=request.scheduling
    )
    
    return {"session_id": session_id}

@app.post("/sessions/{session_id}/execute")
async def execute_session(session_id: str):
    """Execute healing session"""
    orchestrator = app.state.orchestrator
    await orchestrator.execute_session(session_id)
    
    return {"status": "executing"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    # Subscribe to events
    event_bus = app.state.orchestrator.event_bus
    event_bus.subscribe(DomainEvent, lambda e: websocket.send_text(json.dumps(asdict(e))))
```

## Phase 4: Testing & Documentation (Week 7-8)

### 4.1 Comprehensive Testing

**Create:** `tests/test_unified_architecture.py`
```python
class TestUnifiedOrchestrator:
    def test_session_creation(self):
        """Test session creation with multiple modalities"""
        config = EnhancedConfig('test')
        event_bus = MockEventBus()
        orchestrator = UnifiedOrchestrator(config, event_bus)
        
        targets = [
            TargetSpecification(TargetType.INDIVIDUAL, "John Doe"),
            TargetSpecification(TargetType.LOCATION, "New York")
        ]
        
        session_id = orchestrator.create_session(
            intention="healing",
            targets=targets,
            modalities=[Modality.CRYSTAL, Modality.BLESSING],
            duration=300
        )
        
        assert session_id is not None
        assert len(event_bus.published_events) > 0
    
    def test_blessing_routing(self):
        """Test blessing routing to different target types"""
        config = EnhancedConfig('test')
        event_bus = MockEventBus()
        router = BlessingRouter(event_bus)
        
        # Test individual routing
        individual_target = TargetSpecification(TargetType.INDIVIDUAL, "Jane Smith")
        blessing_id = router.route_blessing(
            intention="peace",
            target_spec=individual_target,
            delivery_method=DeliveryMethod.DIRECT
        )
        
        assert blessing_id is not None
        # Verify appropriate events were published
```

### 4.2 Documentation

**Create:** `docs/API_REFERENCE.md`
```markdown
# Vajra Stream API Reference

## Overview
The Vajra Stream API provides programmatic access to all healing and blessing capabilities.

## Authentication
Currently no authentication required (will be added in production).

## Endpoints

### Sessions
#### Create Session
POST /sessions

Create a new healing/blessing session with specified modalities.

**Request Body:**
```json
{
  "intention": "healing and peace",
  "targets": [
    {
      "type": "individual",
      "identifier": "John Doe",
      "metadata": {}
    }
  ],
  "modalities": ["crystal", "blessing", "scalar_waves"],
  "duration": 300,
  "scheduling": {
    "start_time": "2024-01-01T10:00:00Z",
    "repeat": "daily"
  }
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "status": "created",
  "estimated_duration": 300
}
```
```

## Migration Strategy

### Current System Preservation

1. **Backward Compatibility Layer**
   - Create adapter for [`scripts/vajra_orchestrator.py`](scripts/vajra_orchestrator.py:1)
   - Maintain existing CLI interface
   - Map old commands to new unified system

2. **Gradual Migration**
   - Run both systems in parallel
   - Feature flag for switching between systems
   - Performance comparison and validation

3. **Data Migration**
   - Export existing blessing databases
   - Migrate configuration settings
   - Preserve session logs and history

### Testing Strategy

1. **Unit Tests**
   - Test all service implementations
   - Test event bus functionality
   - Test configuration management

2. **Integration Tests**
   - Test service interactions
   - Test orchestrator workflows
   - Test hardware integration

3. **End-to-End Tests**
   - Test complete user workflows
   - Test web API integration
   - Test real hardware operation

### Rollback Plan

1. **Feature Flags**
   - Quick rollback to legacy system
   - Preserve data integrity
   - Minimize user disruption

2. **Monitoring**
   - System health monitoring
   - Performance metrics
   - Error tracking

## Conclusion

This refactoring plan provides a systematic approach to transforming the Vajra Stream codebase into a unified, event-driven architecture. The phased approach minimizes risk while delivering incremental value.

Key benefits of the refactored system:
1. **Unified Orchestration** - Single point of control for all operations
2. **Event-Driven Communication** - Loose coupling between modules
3. **Hardware Abstraction** - Consistent interface for all hardware
4. **Target Resolution** - Flexible targeting system for all blessing types
5. **Wave Management** - Sophisticated wave generation with conflict resolution
6. **Web Integration** - Modern API and web interface

The refactored system will be more maintainable, extensible, and powerful while preserving all existing functionality.