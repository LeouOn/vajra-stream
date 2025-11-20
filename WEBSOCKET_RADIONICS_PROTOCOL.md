# WebSocket Radionics Protocol Specification

## Overview

This document defines the WebSocket message protocols for advanced radionics features in Vajra.Stream, including RNG attunement, trend padding, structural links, and digital radionics interfaces.

## Message Format

All WebSocket messages follow this JSON format:

```json
{
  "type": "message_type",
  "data": { ... },
  "timestamp": 1234567890.123,
  "session_id": "optional_session_id"
}
```

## Message Types

### 1. Unified Orchestrator Messages

#### 1.1 Create Unified Session
**Client → Server**

```json
{
  "type": "create_unified_session",
  "data": {
    "intention": "healing|liberation|empowerment|protection|peace|love|wisdom",
    "targets": [
      {
        "type": "individual|group|location|event",
        "identifier": "target_name_or_id",
        "metadata": {
          "photo": "base64_image_data",
          "description": "target_description",
          "coordinates": {"lat": 0.0, "lng": 0.0}
        }
      }
    ],
    "modalities": ["radionics", "audio", "crystal", "visual"],
    "duration": 3600,
    "advanced_options": {
      "rng_attunement": true,
      "trend_padding": {
        "enabled": true,
        "type": "exponential|linear|fibonacci|sacred",
        "carrier_wave": "schumann|earth_om|solar|lunar",
        "repetitions": 108
      },
      "structural_links": {
        "enabled": true,
        "link_type": "digital|witness|quantum|signature",
        "diagram_type": "welz_basic|cybershaman_matrix|aetherone_grid|sacred_geometry"
      }
    }
  },
  "timestamp": 1234567890.123
}
```

**Server → Client (Response)**

```json
{
  "type": "unified_session_created",
  "data": {
    "session_id": "uuid-string",
    "status": "created|initializing|ready",
    "config": { ... },
    "estimated_start_time": 1234567890.123
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 1.2 Start Unified Session
**Client → Server**

```json
{
  "type": "start_unified_session",
  "data": {
    "session_id": "uuid-string"
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "unified_session_started",
  "data": {
    "session_id": "uuid-string",
    "status": "starting|running",
    "start_time": 1234567890.123,
    "active_modalities": ["radionics", "audio"],
    "initial_parameters": {
      "frequency": 528.0,
      "intensity": 0.85,
      "structural_link_strength": 0.92
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 1.3 Unified Session Update
**Server → Client (Periodic Updates)**

```json
{
  "type": "unified_session_update",
  "data": {
    "session_id": "uuid-string",
    "status": "running|pausing|stopped|completed",
    "progress": 0.75,
    "elapsed_time": 2700,
    "remaining_time": 900,
    "active_modalities": ["radionics", "audio"],
    "current_phase": "trend_padding|intention_broadcast|integration",
    "parameters": {
      "frequency": 528.0,
      "intensity": 0.85,
      "scalar_mops": 17.73,
      "thermal_status": "optimal"
    },
    "rng_attunement": {
      "coherence": 0.82,
      "needle_state": "floating",
      "floating_needle_score": 0.91
    },
    "structural_links": [
      {
        "link_id": "uuid",
        "type": "digital",
        "strength": 0.92,
        "coherence": 0.88
      }
    ]
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 2. RNG Attunement Messages

#### 2.1 Request RNG Reading
**Client → Server**

```json
{
  "type": "request_rng_reading",
  "data": {
    "session_id": "uuid-string",
    "reading_type": "single|sequence|analysis",
    "parameters": {
      "baseline_tone_arm": 5.0,
      "sensitivity": 1.0,
      "duration": 5.0
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "rng_reading",
  "data": {
    "session_id": "uuid-string",
    "reading_id": "uuid",
    "timestamp": 1234567890.123,
    "raw_value": 0.523,
    "tone_arm": 5.1,
    "needle_position": 2.3,
    "needle_state": "floating|rising|falling|rockslam|theta_bop|stuck",
    "quality": "excellent|good|fair|poor|disrupted",
    "entropy": 0.45,
    "coherence": 0.78,
    "trend": 0.05,
    "floating_needle_score": 0.85,
    "interpretation": {
      "meaning": "Optimal attunement detected",
      "recommendation": "Proceed with broadcast",
      "intensity_adjustment": 1.2
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 2.2 RNG Sequence Analysis
**Server → Client (For sequence requests)**

```json
{
  "type": "rng_sequence_analysis",
  "data": {
    "session_id": "uuid-string",
    "sequence_id": "uuid",
    "readings": [
      {
        "timestamp": 1234567890.123,
        "needle_state": "rising",
        "coherence": 0.72,
        "floating_needle_score": 0.0
      },
      {
        "timestamp": 1234567890.623,
        "needle_state": "floating",
        "coherence": 0.85,
        "floating_needle_score": 0.92
      }
    ],
    "analysis": {
      "total_readings": 5,
      "floating_needle_count": 2,
      "avg_coherence": 0.78,
      "avg_entropy": 0.42,
      "stability_score": 0.83,
      "optimal_timing": true,
      "recommended_wait": 0,
      "confidence": 0.87
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 3. Structural Links Messages

#### 3.1 Create Structural Link
**Client → Server**

```json
{
  "type": "create_structural_link",
  "data": {
    "session_id": "uuid-string",
    "link_type": "digital|witness|quantum|signature",
    "target_data": {
      "name": "Target Name",
      "photo": "base64_image_data",
      "signature": "digital_signature_data",
      "witness_type": "hair|dna|saliva|other",
      "intention": "healing|liberation|empowerment"
    },
    "parameters": {
      "amplification": 1.0,
      "stabilization": true,
      "quantum_entanglement": true
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "structural_link_created",
  "data": {
    "session_id": "uuid-string",
    "link_id": "uuid",
    "link_type": "digital",
    "status": "created|activating|active|failed",
    "creation_time": 1234567890.123,
    "link_properties": {
      "resonance_signature": "0x5F3759DF",
      "frequency_matrix": [528.0, 1056.0, 1584.0],
      "link_strength": 0.92,
      "stability_factor": 0.88,
      "quantum_coherence": 0.85,
      "entanglement_strength": 0.78
    },
    "visualization_data": {
      "color": "#00FFFF",
      "intensity": 0.9,
      "pattern": "spiral|wave|pulse"
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 3.2 Structural Link Update
**Server → Client (Periodic Updates)**

```json
{
  "type": "structural_link_update",
  "data": {
    "session_id": "uuid-string",
    "link_id": "uuid",
    "timestamp": 1234567890.123,
    "current_strength": 0.89,
    "coherence": 0.84,
    "stability": 0.91,
    "energy_flow": 0.76,
    "resonance_drift": 0.02,
    "status": "stable|fluctuating|degrading|optimized",
    "alerts": []
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 4. Transfer Diagram Messages

#### 4.1 Request Transfer Diagram
**Client → Server**

```json
{
  "type": "request_transfer_diagram",
  "data": {
    "session_id": "uuid-string",
    "diagram_type": "welz_basic|cybershaman_matrix|aetherone_grid|sacred_geometry",
    "intention": "healing|liberation|empowerment|protection|peace|love|wisdom",
    "structural_link_id": "uuid",
    "parameters": {
      "complexity": "low|medium|high",
      "animation_speed": 1.0,
      "color_scheme": "traditional|modern|energetic"
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "transfer_diagram_data",
  "data": {
    "session_id": "uuid-string",
    "diagram_id": "uuid",
    "diagram_type": "welz_basic",
    "matrix_data": {
      "size": [64, 64],
      "values": [[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
      "metadata": {
        "frequency_components": [528.0, 1056.0, 1584.0],
        "harmonic_ratios": [1.0, 2.0, 3.0],
        "sacred_ratios": [1.618, 2.618, 4.236]
      }
    },
    "visualization_params": {
      "center_point": [32, 32],
      "rate_dials": [
        {"position": [16, 16], "rate": 25.5, "color": "#00FFFF"},
        {"position": [48, 16], "rate": 45.2, "color": "#FF00FF"}
      ],
      "energy_lines": [
        {"start": [32, 32], "end": [16, 16], "intensity": 0.8},
        {"start": [32, 32], "end": [48, 16], "intensity": 0.7}
      ]
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 5. Trend Padding Messages

#### 5.1 Apply Trend Padding
**Client → Server**

```json
{
  "type": "apply_trend_padding",
  "data": {
    "session_id": "uuid-string",
    "padding_config": {
      "type": "exponential|linear|fibonacci|sacred",
      "carrier_wave": "schumann|earth_om|solar|lunar",
      "repetitions": 108,
      "amplification_factor": 1.5,
      "noise_floor": 0.01
    },
    "intention_signal": {
      "frequency": 528.0,
      "duration": 30.0,
      "waveform": "sine|square|triangle|complex"
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "trend_padding_applied",
  "data": {
    "session_id": "uuid-string",
    "padding_id": "uuid",
    "status": "applied|processing|failed",
    "parameters": {
      "original_duration": 30.0,
      "padded_duration": 3240.0,
      "repetitions_applied": 108,
      "carrier_frequency": 136.1,
      "amplification_profile": [1.0, 1.1, 1.21, 1.331, ...]
    },
    "results": {
      "signal_amplification": 54.7,
      "frequency_harmonics": [528.0, 1056.0, 1584.0, 2112.0],
      "coherence_improvement": 0.23,
      "field_strength": 0.87
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 5.2 Trend Padding Progress
**Server → Client (Progress Updates)**

```json
{
  "type": "trend_padding_progress",
  "data": {
    "session_id": "uuid-string",
    "padding_id": "uuid",
    "progress": 0.65,
    "current_repetition": 70,
    "total_repetitions": 108,
    "current_amplification": 7.7,
    "estimated_completion": 1234567895.123,
    "performance_metrics": {
      "processing_rate": 1000.0,
      "memory_usage": 0.65,
      "cpu_usage": 0.42
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 6. Cybershaman Matrix Messages

#### 6.1 Create Cybershaman Matrix
**Client → Server**

```json
{
  "type": "create_cybershaman_matrix",
  "data": {
    "session_id": "uuid-string",
    "intention": "healing|liberation|empowerment|protection|peace|love|wisdom",
    "targets": [
      {
        "name": "Target Name",
        "symbol_encoding": "encoded_symbol_data"
      }
    ],
    "matrix_config": {
      "size": 128,
      "complexity": "medium",
      "symbol_set": "sacred|planetary|elemental|custom",
      "frequency_banks": ["solfeggio", "planetary", "schumann"]
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "cybershaman_matrix_created",
  "data": {
    "session_id": "uuid-string",
    "matrix_id": "uuid",
    "matrix_data": {
      "size": [128, 128],
      "symbol_positions": [
        {"index": 0, "position": [32, 32], "symbol": "om", "frequency": 528.0},
        {"index": 1, "position": [96, 32], "symbol": "lotus", "frequency": 396.0}
      ],
      "energy_connections": [
        {"from": 0, "to": 1, "strength": 0.8, "frequency": 462.0}
      ],
      "frequency_set": [528.0, 396.0, 741.0, 852.0, 963.0, 136.1, 126.22, 210.42]
    },
    "analysis": {
      "matrix_coherence": 0.87,
      "symbol_resonance": 0.92,
      "energy_flow_efficiency": 0.78,
      "dimensional_stability": 0.85
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 7. AetherOnePi Interface Messages

#### 7.1 Create AetherOnePi Session
**Client → Server**

```json
{
  "type": "create_aetherone_session",
  "data": {
    "session_id": "uuid-string",
    "intention": "healing|liberation|empowerment|protection|peace|love|wisdom",
    "targets": [
      {
        "name": "Target Name",
        "photo": "base64_image_data"
      }
    ],
    "initial_rates": [25.5, 45.2, 67.8, 89.3, 12.1, 34.7, 56.9, 78.4, 91.2, 23.6]
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "aetherone_session_created",
  "data": {
    "session_id": "uuid-string",
    "aetherone_id": "uuid",
    "rate_dials": [
      {"dial": 1, "position": 25.5, "frequency": 528.0, "rate_name": "DNA Repair"},
      {"dial": 2, "position": 45.2, "frequency": 396.0, "rate_name": "Liberation"}
    ],
    "led_pattern": [true, false, true, false, true, false, true, false, true, false],
    "display_output": "SESSION READY - PRESS SCAN TO BEGIN",
    "control_status": {
      "scan_available": true,
      "broadcast_available": false,
      "analyze_available": true
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 7.2 AetherOnePi Control
**Client → Server**

```json
{
  "type": "aetherone_control",
  "data": {
    "session_id": "uuid-string",
    "action": "scan|broadcast|analyze|stop|dial_change",
    "parameters": {
      "dial_index": 3,
      "dial_position": 67.8,
      "button_id": "scan|broadcast|analyze"
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

**Server → Client (Response)**

```json
{
  "type": "aetherone_status_update",
  "data": {
    "session_id": "uuid-string",
    "action": "scan",
    "result": "scanning|complete|error",
    "display_output": "SCANNING TARGET... 67% COMPLETE",
    "led_pattern": [true, true, false, true, false, true, true, false, true, false],
    "scan_results": {
      "target_resonance": 0.87,
      "optimal_rates": [25.5, 67.8, 91.2],
      "coherence": 0.82,
      "recommendations": ["Increase dial 3 to 70.2", "Activate trend padding"]
    },
    "broadcast_status": {
      "active": false,
      "intensity": 0.0,
      "frequency": 0.0,
      "duration": 0
    }
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

### 8. Error and Status Messages

#### 8.1 Error Message
**Server → Client**

```json
{
  "type": "error",
  "data": {
    "error_code": "INVALID_SESSION_ID|RNG_SERVICE_UNAVAILABLE|STRUCTURAL_LINK_FAILED",
    "error_message": "Detailed error description",
    "session_id": "uuid-string",
    "component": "unified_orchestrator|radionics_enhancer|rng_service|structural_links",
    "recoverable": true,
    "suggested_action": "Retry operation|Check session ID|Reset service"
  },
  "timestamp": 1234567890.123,
  "session_id": "uuid-string"
}
```

#### 8.2 System Status
**Server → Client (Periodic)**

```json
{
  "type": "system_status",
  "data": {
    "overall_status": "healthy|degraded|maintenance|error",
    "services": {
      "unified_orchestrator": "healthy",
      "radionics_enhancer": "healthy",
      "rng_service": "healthy",
      "structural_links": "healthy",
      "trend_padding": "healthy",
      "cybershaman_matrix": "healthy",
      "aetherone_interface": "healthy"
    },
    "performance": {
      "cpu_usage": 0.42,
      "memory_usage": 0.67,
      "active_sessions": 3,
      "websocket_connections": 5
    },
    "alerts": []
  },
  "timestamp": 1234567890.123
}
```

## Connection Management

### Connection Establishment
1. Client connects to WebSocket endpoint: `ws://localhost:8001/ws`
2. Server sends initial connection status:
```json
{
  "type": "connection_status",
  "data": {
    "status": "connected",
    "message": "Successfully connected to Vajra.Stream",
    "server_version": "1.0.0",
    "supported_features": ["unified_orchestrator", "radionics_enhancer", "rng_attunement"]
  },
  "timestamp": 1234567890.123
}
```

### Heartbeat
- Client sends heartbeat every 30 seconds:
```json
{
  "type": "ping",
  "timestamp": 1234567890.123
}
```

- Server responds:
```json
{
  "type": "pong",
  "timestamp": 1234567890.123
}
```

### Disconnection
- Server sends disconnection notice:
```json
{
  "type": "disconnection",
  "data": {
    "reason": "server_shutdown|client_timeout|error",
    "message": "Server shutting down for maintenance"
  },
  "timestamp": 1234567890.123
}
```

## Rate Limiting and Throttling

### Message Rate Limits
- RNG reading requests: Maximum 1 per second per session
- Structural link creation: Maximum 5 per minute per connection
- Trend padding requests: Maximum 1 per minute per session
- Control commands: Maximum 10 per second per connection

### Data Size Limits
- Maximum message size: 1 MB
- Maximum image data for structural links: 5 MB
- Maximum matrix data size: 10 MB

## Security Considerations

### Authentication
- WebSocket connections should include authentication token in query parameter or initial message
- Session IDs should be validated for each request
- Client-side validation for all user inputs

### Data Validation
- All numeric values should be within expected ranges
- Enum values should be validated against allowed values
- Base64 data should be validated for format and size

### Error Handling
- All errors should be logged with session context
- Sensitive information should not be included in error messages
- Graceful degradation should be implemented for service failures

## Implementation Notes

### Backend Implementation
- Use async/await patterns for WebSocket handling
- Implement proper message queuing for high-frequency updates
- Use connection pooling for database operations
- Implement proper cleanup on connection termination

### Frontend Implementation
- Use React hooks for WebSocket state management
- Implement reconnection logic with exponential backoff
- Use debouncing for high-frequency updates
- Implement proper error boundaries for WebSocket errors

### Testing
- Unit tests for message parsing and validation
- Integration tests for WebSocket communication
- Load testing for concurrent connections
- End-to-end tests for complete workflows

This protocol specification provides a comprehensive foundation for implementing advanced radionics features in Vajra.Stream with real-time WebSocket communication.