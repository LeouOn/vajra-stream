# Vajra.Stream API Documentation

**Version:** 1.0.0-stable-v2
**Base URL:** `http://localhost:8008`
**WebSocket URL:** `ws://localhost:8008/ws`

## Table of Contents

1. [Authentication](#authentication)
2. [Core Endpoints](#core-endpoints)
3. [Audio API](#audio-api)
4. [Session Management](#session-management)
5. [Astrology & Astrocartography](#astrology--astrocartography)
6. [Scalar Waves](#scalar-waves)
7. [Radionics](#radionics)
8. [Blessings](#blessings)
9. [Visualization](#visualization)
10. [RNG Attunement](#rng-attunement)
11. [Population Management](#population-management)
12. [Automation](#automation)
13. [WebSocket API](#websocket-api)
14. [Error Handling](#error-handling)
15. [Rate Limiting](#rate-limiting)

---

## Authentication

Currently, the API does not require authentication for local development. For production deployments, implement JWT tokens or API keys.

**CORS Configuration:**
- Allowed Origins: `localhost:3009`, `localhost:3010`, `localhost:3001`, `localhost:5173`

---

## Core Endpoints

### Health Check

Check the API health and connection status.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "vajra-stream",
  "version": "1.0.0-stable-v2",
  "timestamp": 1234.567,
  "websocket_connections": 2,
  "streaming_active": true
}
```

### API Root

Get basic API information.

**Endpoint:** `GET /`

**Response:**
```json
{
  "message": "Vajra.Stream API",
  "status": "active",
  "version": "1.0.0-stable-v2",
  "description": "Sacred Technology Web Interface - Stable WebSocket Version v2",
  "websocket_stats": {
    "total_connections": 2,
    "active_connections": 2,
    "total_messages_sent": 1234,
    "uptime_seconds": 3600.5
  }
}
```

### WebSocket Statistics

Get real-time WebSocket connection statistics.

**Endpoint:** `GET /ws-stats`

**Response:**
```json
{
  "total_connections": 5,
  "active_connections": 3,
  "total_messages_sent": 15000,
  "total_messages_received": 2500,
  "uptime_seconds": 7200.3,
  "broadcast_rate_hz": 10,
  "last_broadcast_time": 1234567890.123
}
```

---

## Audio API

**Base Path:** `/api/v1/audio`

### Generate Audio

Generate prayer bowl audio with harmonic synthesis.

**Endpoint:** `POST /api/v1/audio/generate`

**Request Body:**
```json
{
  "frequency": 136.1,
  "duration": 30.0,
  "volume": 0.8,
  "prayer_bowl_mode": true,
  "harmonic_strength": 0.3,
  "modulation_depth": 0.05
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Audio generation completed",
  "config": {
    "frequency": 136.1,
    "duration": 30.0,
    "volume": 0.8,
    "prayer_bowl_mode": true,
    "harmonic_strength": 0.3,
    "modulation_depth": 0.05
  },
  "audio_generated": true,
  "samples": 1323000
}
```

### Play Audio

Start audio playback through hardware.

**Endpoint:** `POST /api/v1/audio/play`

**Request Body:**
```json
{
  "hardware_level": 2
}
```

**Parameters:**
- `hardware_level` (int): Hardware level (2=passive crystal, 3=amplified)

**Response:**
```json
{
  "status": "success",
  "message": "Audio playback started",
  "hardware_level": 2,
  "audio_duration": 30.0,
  "audio_samples": 1323000
}
```

### Stop Audio

Stop current audio playback.

**Endpoint:** `POST /api/v1/audio/stop`

**Response:**
```json
{
  "status": "success",
  "message": "Audio stop request processed"
}
```

### Get Audio Status

Check audio generation status.

**Endpoint:** `GET /api/v1/audio/status`

**Response:**
```json
{
  "status": "success",
  "has_audio": true,
  "audio_duration": 30.0,
  "spectrum_available": true,
  "timestamp": 1234567890.123
}
```

### Get Audio Spectrum

Retrieve current audio frequency spectrum.

**Endpoint:** `GET /api/v1/audio/spectrum`

**Response:**
```json
{
  "status": "success",
  "spectrum": [0.1, 0.3, 0.5, 0.7, ...],
  "length": 64,
  "timestamp": 1234567890.123
}
```

### Get Audio Presets

Get available audio frequency presets.

**Endpoint:** `GET /api/v1/audio/presets`

**Response:**
```json
{
  "status": "success",
  "presets": {
    "om-frequency": {
      "name": "OM Frequency",
      "frequency": 136.1,
      "description": "Sacred OM frequency for meditation",
      "prayer_bowl_mode": true,
      "harmonic_strength": 0.3,
      "modulation_depth": 0.05,
      "volume": 0.8
    },
    "heart-chakra": {
      "name": "Heart Chakra",
      "frequency": 528.0,
      "description": "Love frequency for heart opening",
      "prayer_bowl_mode": true,
      "harmonic_strength": 0.4,
      "modulation_depth": 0.1,
      "volume": 0.7
    },
    "earth-resonance": {
      "name": "Earth Resonance",
      "frequency": 7.83,
      "description": "Schumann resonance",
      "prayer_bowl_mode": true,
      "harmonic_strength": 0.2,
      "modulation_depth": 0.02,
      "volume": 0.6
    }
  },
  "count": 4
}
```

### Get Frequency Ranges

Get recommended frequency ranges.

**Endpoint:** `GET /api/v1/audio/frequencies/range`

**Response:**
```json
{
  "status": "success",
  "ranges": {
    "earth_resonance": {
      "name": "Earth Resonance",
      "min": 7.0,
      "max": 10.0,
      "description": "Schumann resonance frequencies"
    },
    "healing": {
      "name": "Healing Frequencies",
      "min": 100.0,
      "max": 1000.0,
      "description": "Common healing frequencies"
    },
    "solfeggio": {
      "name": "Solfeggio Frequencies",
      "frequencies": [396.0, 417.0, 444.0, 528.0, 639.0, 741.0, 852.0],
      "description": "Ancient Solfeggio scale"
    },
    "chakra": {
      "name": "Chakra Frequencies",
      "frequencies": {
        "root": 256.0,
        "sacral": 288.0,
        "solar": 320.0,
        "heart": 341.3,
        "throat": 384.0,
        "third_eye": 448.0,
        "crown": 480.0
      }
    }
  }
}
```

---

## Session Management

**Base Path:** `/api/v1/sessions`

### Create Session

Create a new healing/blessing session.

**Endpoint:** `POST /api/v1/sessions/create`

**Request Body:**
```json
{
  "name": "Morning Meditation",
  "duration": 1800,
  "intention": "Peace and healing for all beings",
  "frequency": 136.1,
  "modalities": ["scalar_waves", "radionics", "blessing"]
}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "sess_abc123",
  "name": "Morning Meditation",
  "created_at": "2024-01-15T10:30:00Z",
  "duration": 1800
}
```

### Start Session

Start a created session.

**Endpoint:** `POST /api/v1/sessions/{session_id}/start`

**Response:**
```json
{
  "status": "success",
  "message": "Session started",
  "session_id": "sess_abc123",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Stop Session

Stop a running session.

**Endpoint:** `POST /api/v1/sessions/{session_id}/stop`

**Response:**
```json
{
  "status": "success",
  "message": "Session stopped",
  "session_id": "sess_abc123",
  "stopped_at": "2024-01-15T11:00:00Z",
  "duration_actual": 1800
}
```

### Get Session Status

Get current session status.

**Endpoint:** `GET /api/v1/sessions/{session_id}/status`

**Response:**
```json
{
  "status": "success",
  "session": {
    "id": "sess_abc123",
    "name": "Morning Meditation",
    "status": "running",
    "started_at": "2024-01-15T10:30:00Z",
    "duration": 1800,
    "elapsed": 600,
    "remaining": 1200
  }
}
```

---

## Astrology & Astrocartography

**Base Path:** `/api/v1/astrology`

### Get Current Astrological Data

Get current planetary positions and aspects.

**Endpoint:** `GET /api/v1/astrology/current`

**Response:**
```json
{
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z",
  "planets": {
    "Sun": {"longitude": 294.5, "sign": "Capricorn", "degree": 24.5},
    "Moon": {"longitude": 45.2, "sign": "Taurus", "degree": 15.2},
    "Mercury": {"longitude": 280.1, "sign": "Capricorn", "degree": 10.1}
  },
  "aspects": [
    {"planet1": "Sun", "planet2": "Moon", "aspect": "trine", "orb": 1.2}
  ]
}
```

### Get Planetary Positions

Get detailed planetary positions.

**Endpoint:** `GET /api/v1/astrology/planetary-positions`

**Query Parameters:**
- `date` (optional): ISO 8601 date string
- `location` (optional): "lat,lon" format

**Response:**
```json
{
  "status": "success",
  "date": "2024-01-15T10:30:00Z",
  "positions": [
    {
      "planet": "Sun",
      "longitude": 294.5,
      "latitude": 0.0,
      "distance": 0.983,
      "speed": 1.019,
      "retrograde": false,
      "sign": "Capricorn",
      "degree": 24.5
    }
  ]
}
```

### Get Moon Phase

Get current moon phase information.

**Endpoint:** `GET /api/v1/astrology/moon-phase`

**Response:**
```json
{
  "status": "success",
  "phase": "Waxing Gibbous",
  "illumination": 0.73,
  "age_days": 10.2,
  "distance_km": 384400,
  "next_new_moon": "2024-01-20T15:30:00Z",
  "next_full_moon": "2024-02-05T12:15:00Z"
}
```

### Calculate Astrocartography Lines

Calculate planetary lines for a birth chart.

**Endpoint:** `POST /api/v1/astrology/astrocartography`

**Request Body:**
```json
{
  "birth_date": "1990-01-15T14:30:00Z",
  "birth_location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "name": "San Francisco"
  },
  "planets": ["Sun", "Moon", "Venus", "Jupiter", "Saturn"]
}
```

**Response:**
```json
{
  "status": "success",
  "lines": [
    {
      "planet": "Sun",
      "angle": "MC",
      "longitude": -122.4,
      "strength": 0.85,
      "quality": "benefic"
    },
    {
      "planet": "Venus",
      "angle": "ASC",
      "longitude": 45.2,
      "strength": 0.92,
      "quality": "benefic"
    }
  ],
  "parans": [
    {
      "planet1": "Sun",
      "planet2": "Jupiter",
      "location": {"lat": 51.5074, "lon": -0.1278},
      "strength": 0.78
    }
  ]
}
```

### Get Auspicious Times

Get optimal times for spiritual practices.

**Endpoint:** `GET /api/v1/astrology/auspicious-times`

**Query Parameters:**
- `activity`: Type of activity (meditation, healing, blessing, manifestation)
- `date`: Target date (optional, defaults to today)

**Response:**
```json
{
  "status": "success",
  "date": "2024-01-15",
  "activity": "meditation",
  "times": [
    {
      "start": "2024-01-15T06:00:00Z",
      "end": "2024-01-15T07:30:00Z",
      "quality": "excellent",
      "planetary_hour": "Jupiter",
      "moon_phase": "Waxing",
      "aspects": ["Sun trine Moon", "Venus sextile Mars"]
    }
  ]
}
```

### Get Planetary Hours

Get current planetary hour.

**Endpoint:** `GET /api/v1/astrology/planetary-hours`

**Query Parameters:**
- `location`: "lat,lon" format
- `date`: Date/time (optional)

**Response:**
```json
{
  "status": "success",
  "current_hour": {
    "planet": "Jupiter",
    "quality": "benefic",
    "start": "2024-01-15T10:00:00Z",
    "end": "2024-01-15T11:00:00Z",
    "attributes": ["expansion", "wisdom", "prosperity"]
  },
  "next_hours": [
    {"planet": "Mars", "start": "2024-01-15T11:00:00Z"},
    {"planet": "Sun", "start": "2024-01-15T12:00:00Z"}
  ]
}
```

---

## Scalar Waves

**Base Path:** `/api/v1/scalar`

### Generate Scalar Waves

Generate Terra MOPS scalar wave patterns.

**Endpoint:** `POST /api/v1/scalar/generate`

**Request Body:**
```json
{
  "frequency": 7.83,
  "duration": 60,
  "amplitude": 0.8,
  "pattern": "schumann",
  "intention": "Healing and balance"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Scalar wave generation started",
  "wave_id": "sw_xyz789",
  "frequency": 7.83,
  "duration": 60,
  "pattern": "schumann"
}
```

### Scalar Wave Breathing Cycle

Generate breathing rhythm scalar waves.

**Endpoint:** `POST /api/v1/scalar/breathing-cycle`

**Request Body:**
```json
{
  "inhale_seconds": 4,
  "hold_seconds": 7,
  "exhale_seconds": 8,
  "cycles": 10
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Breathing cycle initiated",
  "total_duration": 190,
  "cycles": 10
}
```

### Benchmark Scalar Waves

Run scalar wave performance benchmark.

**Endpoint:** `POST /api/v1/scalar/benchmark`

**Response:**
```json
{
  "status": "success",
  "benchmark_results": {
    "generation_time_ms": 45.2,
    "samples_per_second": 44100,
    "efficiency": 0.95
  }
}
```

---

## Radionics

**Base Path:** `/api/v1/radionics`

### Calculate Radionics Rate

Calculate radionics rate for intention.

**Endpoint:** `POST /api/v1/radionics/calculate-rate`

**Request Body:**
```json
{
  "intention": "Physical healing and vitality",
  "target_name": "John Doe",
  "method": "gematria"
}
```

**Response:**
```json
{
  "status": "success",
  "rate": 47.5,
  "intention": "Physical healing and vitality",
  "method": "gematria",
  "confidence": 0.87
}
```

### Broadcast Radionics Rate

Broadcast radionics rate through crystal hardware.

**Endpoint:** `POST /api/v1/radionics/broadcast`

**Request Body:**
```json
{
  "rate": 47.5,
  "duration": 300,
  "intention": "Healing",
  "hardware_level": 2
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Radionics broadcast started",
  "rate": 47.5,
  "duration": 300,
  "broadcast_id": "bcast_123"
}
```

### Get Radionics Database

Search radionics rate database.

**Endpoint:** `GET /api/v1/radionics/rates`

**Query Parameters:**
- `category`: Category filter (health, prosperity, protection, etc.)
- `search`: Search term

**Response:**
```json
{
  "status": "success",
  "rates": [
    {
      "rate": 47.5,
      "name": "General Vitality",
      "category": "health",
      "description": "Enhances overall physical vitality",
      "applications": ["energy", "healing", "wellness"]
    }
  ],
  "count": 150
}
```

---

## Blessings

**Base Path:** `/api/v1/blessings`

### Generate Blessing Narrative

Generate AI-powered blessing narrative.

**Endpoint:** `POST /api/v1/blessings/generate-narrative`

**Request Body:**
```json
{
  "intention": "healing",
  "target": "all sentient beings",
  "style": "compassionate",
  "length": "medium"
}
```

**Response:**
```json
{
  "status": "success",
  "narrative": "May all sentient beings be free from suffering...",
  "word_count": 250,
  "estimated_duration_seconds": 90
}
```

### Compassionate Blessing

Generate compassionate blessing for specific intention.

**Endpoint:** `POST /api/v1/blessings/compassionate-blessing`

**Request Body:**
```json
{
  "recipient": "Earth and all its inhabitants",
  "qualities": ["love", "peace", "healing"],
  "duration": 60
}
```

**Response:**
```json
{
  "status": "success",
  "blessing": {
    "text": "May Earth and all its inhabitants...",
    "qualities": ["love", "peace", "healing"],
    "energy_signature": "compassion_high"
  }
}
```

### Mass Liberation Blessing

Generate mass liberation blessing (Phowa practice).

**Endpoint:** `POST /api/v1/blessings/mass-liberation`

**Request Body:**
```json
{
  "scope": "global",
  "lineage": "Tibetan",
  "duration": 300
}
```

**Response:**
```json
{
  "status": "success",
  "blessing": {
    "type": "mass_liberation",
    "scope": "global",
    "mantra": "OM MANI PADME HUM",
    "dedication": "May all beings attain liberation..."
  }
}
```

---

## Visualization

**Base Path:** `/api/v1/visualization`

### Generate Rothko Visualization

Generate Mark Rothko-inspired color field visualization.

**Endpoint:** `POST /api/v1/visualization/rothko`

**Request Body:**
```json
{
  "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1"],
  "width": 1920,
  "height": 1080,
  "blur_amount": 50
}
```

**Response:**
```json
{
  "status": "success",
  "image_data": "base64_encoded_png...",
  "dimensions": {"width": 1920, "height": 1080},
  "format": "PNG"
}
```

### Generate Sacred Geometry

Generate sacred geometry pattern.

**Endpoint:** `POST /api/v1/visualization/sacred-geometry`

**Request Body:**
```json
{
  "pattern": "flower-of-life",
  "size": 1024,
  "color_scheme": "chakra",
  "complexity": "high"
}
```

**Response:**
```json
{
  "status": "success",
  "image_data": "base64_encoded_svg...",
  "pattern": "flower-of-life",
  "format": "SVG"
}
```

---

## RNG Attunement

**Base Path:** `/api/v1`

### Create RNG Session

Create quantum randomness attunement session.

**Endpoint:** `POST /api/v1/rng-attunement/session/create`

**Request Body:**
```json
{
  "intention": "Manifestation of highest good",
  "duration": 600,
  "source": "quantum",
  "target_deviation": 0.05
}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "rng_abc123",
  "intention": "Manifestation of highest good",
  "started_at": "2024-01-15T10:30:00Z",
  "expected_end": "2024-01-15T10:40:00Z"
}
```

### Get RNG Reading

Get randomness reading and statistical analysis.

**Endpoint:** `GET /api/v1/rng-attunement/reading/{session_id}`

**Response:**
```json
{
  "status": "success",
  "session_id": "rng_abc123",
  "reading": {
    "deviation_from_expected": 0.037,
    "p_value": 0.024,
    "significance": "moderately_significant",
    "samples_analyzed": 10000,
    "trend": "positive"
  },
  "interpretation": "The data shows moderate evidence of consciousness-RNG interaction"
}
```

---

## Population Management

**Base Path:** `/api/v1`

### Create Population

Create a target population for blessings.

**Endpoint:** `POST /api/v1/populations/create`

**Request Body:**
```json
{
  "name": "Global Humanity",
  "description": "All humans on Earth",
  "size_estimate": 8000000000,
  "categories": ["human", "global"],
  "intention": "Peace and prosperity for all"
}
```

**Response:**
```json
{
  "status": "success",
  "population_id": "pop_xyz789",
  "name": "Global Humanity",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Population

Get population details.

**Endpoint:** `GET /api/v1/populations/{population_id}`

**Response:**
```json
{
  "status": "success",
  "population": {
    "id": "pop_xyz789",
    "name": "Global Humanity",
    "description": "All humans on Earth",
    "size_estimate": 8000000000,
    "active_blessings": 5,
    "total_blessing_hours": 1250.5
  }
}
```

### List Populations

List all populations.

**Endpoint:** `GET /api/v1/populations/`

**Query Parameters:**
- `category`: Filter by category
- `limit`: Max results (default: 50)
- `offset`: Pagination offset

**Response:**
```json
{
  "status": "success",
  "populations": [
    {
      "id": "pop_xyz789",
      "name": "Global Humanity",
      "size_estimate": 8000000000
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

---

## Automation

**Base Path:** `/api/v1`

### Create Automation Workflow

Create automated blessing/healing workflow.

**Endpoint:** `POST /api/v1/automation/create`

**Request Body:**
```json
{
  "name": "Daily Healing Session",
  "schedule": "0 6 * * *",
  "actions": [
    {
      "type": "generate_audio",
      "params": {"frequency": 528.0, "duration": 1800}
    },
    {
      "type": "start_session",
      "params": {"intention": "Global healing"}
    },
    {
      "type": "broadcast_blessing",
      "params": {"population_id": "pop_xyz789"}
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "workflow_id": "wf_abc123",
  "name": "Daily Healing Session",
  "schedule": "0 6 * * *",
  "next_run": "2024-01-16T06:00:00Z"
}
```

### List Workflows

Get all automation workflows.

**Endpoint:** `GET /api/v1/automation/workflows`

**Response:**
```json
{
  "status": "success",
  "workflows": [
    {
      "id": "wf_abc123",
      "name": "Daily Healing Session",
      "status": "active",
      "last_run": "2024-01-15T06:00:00Z",
      "next_run": "2024-01-16T06:00:00Z"
    }
  ]
}
```

---

## WebSocket API

**Endpoint:** `ws://localhost:8008/ws`

### Connection

Connect to WebSocket for real-time data streaming.

```javascript
const ws = new WebSocket('ws://localhost:8008/ws');

ws.onopen = () => {
  console.log('Connected to Vajra.Stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Message Types

#### 1. Real-time Data (10Hz broadcast)

```json
{
  "type": "realtime_data",
  "timestamp": 1234567890.123,
  "audio_spectrum": [0.1, 0.3, 0.5, ...],
  "sessions": {
    "sess_abc123": {
      "id": "sess_abc123",
      "name": "Morning Meditation",
      "status": "running",
      "elapsed": 600
    }
  },
  "system_status": {
    "cpu_usage": 25.5,
    "memory_usage": 42.3,
    "websocket_connections": 3
  }
}
```

#### 2. Heartbeat

```json
{
  "type": "heartbeat",
  "timestamp": 1234567890.123,
  "connection_count": 3,
  "uptime": 7200.5
}
```

#### 3. Connection Status

```json
{
  "type": "connection_status",
  "status": "connected",
  "connection_id": "conn_xyz789",
  "server_time": 1234567890.123
}
```

#### 4. Domain Events

```json
{
  "type": "domain_event",
  "event_name": "BLESSING_STARTED",
  "payload": {
    "session_id": "sess_abc123",
    "intention": "Global peace",
    "started_at": "2024-01-15T10:30:00Z"
  }
}
```

### Client Commands

#### Start Session

```json
{
  "type": "START_SESSION",
  "session_name": "Evening Meditation",
  "duration": 1800,
  "intention": "Peace and clarity"
}
```

#### Update Settings

```json
{
  "type": "UPDATE_SETTINGS",
  "settings": {
    "frequency": 432.0,
    "volume": 0.7,
    "prayer_bowl_mode": true
  }
}
```

#### Ping

```json
{
  "type": "ping",
  "timestamp": 1234567890.123
}
```

**Response:**
```json
{
  "type": "pong",
  "timestamp": 1234567890.456
}
```

---

## Error Handling

All API endpoints return errors in a consistent format:

```json
{
  "status": "error",
  "error_code": "INVALID_FREQUENCY",
  "message": "Frequency must be between 0.1 and 20000 Hz",
  "details": {
    "provided_value": -5.0,
    "min_value": 0.1,
    "max_value": 20000.0
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_PARAMETER` | Parameter validation failed |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `AUDIO_GENERATION_FAILED` | Audio generation error |
| `SESSION_NOT_FOUND` | Session ID invalid |
| `WEBSOCKET_ERROR` | WebSocket connection issue |
| `HARDWARE_ERROR` | Crystal broadcaster hardware error |
| `DATABASE_ERROR` | Database operation failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

---

## Rate Limiting

**Current Limits:**
- Audio generation: 10 requests/minute per IP
- WebSocket connections: 5 concurrent per IP
- General API: 100 requests/minute per IP

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## Example Integration

### Python Client Example

```python
import requests
import websocket
import json

# API Base URL
BASE_URL = "http://localhost:8008"

# 1. Generate Audio
response = requests.post(f"{BASE_URL}/api/v1/audio/generate", json={
    "frequency": 136.1,
    "duration": 30.0,
    "volume": 0.8,
    "prayer_bowl_mode": True
})
print("Audio generated:", response.json())

# 2. Create Session
response = requests.post(f"{BASE_URL}/api/v1/sessions/create", json={
    "name": "Healing Session",
    "duration": 1800,
    "intention": "Universal healing"
})
session_id = response.json()["session_id"]

# 3. Start Session
response = requests.post(f"{BASE_URL}/api/v1/sessions/{session_id}/start")
print("Session started:", response.json())

# 4. WebSocket Connection
def on_message(ws, message):
    data = json.loads(message)
    if data["type"] == "realtime_data":
        print("Audio spectrum:", data["audio_spectrum"][:5])

ws = websocket.WebSocketApp("ws://localhost:8008/ws",
                             on_message=on_message)
ws.run_forever()
```

### JavaScript/Node.js Client Example

```javascript
const axios = require('axios');
const WebSocket = require('ws');

const BASE_URL = 'http://localhost:8008';

// 1. Generate Audio
async function generateAudio() {
  const response = await axios.post(`${BASE_URL}/api/v1/audio/generate`, {
    frequency: 528.0,
    duration: 30.0,
    volume: 0.8,
    prayer_bowl_mode: true
  });
  console.log('Audio generated:', response.data);
}

// 2. WebSocket Connection
const ws = new WebSocket('ws://localhost:8008/ws');

ws.on('open', () => {
  console.log('Connected to Vajra.Stream');
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  if (message.type === 'realtime_data') {
    console.log('Audio spectrum:', message.audio_spectrum.slice(0, 5));
  }
});

generateAudio();
```

---

## OpenAPI/Swagger Documentation

Interactive API documentation is available at:

- **Swagger UI:** http://localhost:8008/docs
- **ReDoc:** http://localhost:8008/redoc
- **OpenAPI JSON:** http://localhost:8008/openapi.json

---

## Support & Community

- **GitHub Issues:** https://github.com/LeouOn/vajra-stream/issues
- **Documentation:** https://docs.vajra.stream
- **Email:** support@vajra.stream

---

**Last Updated:** 2024-01-15
**API Version:** 1.0.0-stable-v2
**License:** MIT
