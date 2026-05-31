# Vajra.Stream Architecture & System Specifications

This document details the software architecture, system specifications, data models, APIs, and real-time protocol specifications for the **Vajra.Stream Sacred Technology Platform**.

---

## 1. System Overview

Vajra.Stream is structured as a modern multi-tiered application designed for offline-first, local operations:

```
┌────────────────────────────────────────────────────────┐
│               FRONTEND: Vite + React                   │
│        (Three.js, Lucide icons, Canvas, HTML5)         │
└───────┬────────────────────────────────────────┬───────┘
        │ REST API Requests                      │ WebSockets (Real-time updates)
        │ (Port 3009 -> Port 8008)               │ (Port 8008/ws)
        ▼                                        ▼
┌────────────────────────────────────────────────────────┐
│               BACKEND: FastAPI (Python)                │
│       (FastAPI, Asyncio, Sounddevice, edge-tts)        │
└───────┬────────────────────────────────────────┬───────┘
        │                                        │
        ▼ Local Filesystem Storage               ▼ Database Access (sqlite3)
┌────────────────────────────────┐       ┌────────────────────────────────┐
│   ~/.vajra-stream/             │       │   vajra_stream.db (Core data)  │
│   (populations.json, etc.)     │       │   backend/vajra_stream.db (Log)│
└────────────────────────────────┘       └────────────────────────────────┘
```

---

## 2. Core Service Directory (`backend/core/services/`)

The backend functions via a set of modular services instantiated in a dependency injection `container.py` wrapper:

*   **`VajraStreamService` (`vajra_service.py`):** The central controller orchestrating active healing sessions, loading settings, generating real-time spectrums, and running the background WebSocket broadcast loop.
*   **`RNGAttunementService` (`rng_attunement_service.py`):** Models the E-meter style psychic tuning logic. Gathers entropy, tracks baseline tone arms, manages active needle positions, and analyzes needle states.
*   **`PopulationManager` (`population_manager.py`) & `BlessingScheduler` (`blessing_scheduler.py`):** Handles Target Population lists, syncs offline photo directories, and runs the continuous async round-robin rotation scheduler.
*   **`AudioService` (`audio_service.py`):** Integrates audio generators, playing synthesizers, and controlling sound card playback via `sounddevice`.
*   **`AstrologyChartService` (`astrology_chart_service.py`) & `LocationManager` (`location_manager.py`):** Handles planetary calculations, house divisions, and Auspicious timing checking.
*   **`DivinationService` & `GrimoireService`:** Manages random drawing algorithms, ritual definitions, and narrative insights.
*   **`SigilService` (`sigil_service.py`):** Renders dynamic visual sigils from textual intention keys for anchoring.

---

## 3. SQLite Database Schema

The system maintains two SQLite database files to track user sessions, settings, history, and log telemetry:

### A. Core Database: `vajra_stream.db` (Root Folder)

Tracks the main states, user configurations, history, and target entities:

*   **`sessions`:** Logs historical sessions.
    *   `id` (INTEGER, Primary Key)
    *   `session_type` (TEXT)
    *   `start_time` (TIMESTAMP)
    *   `end_time` (TIMESTAMP)
    *   `intention` (TEXT)
    *   `focus_area` (TEXT)
    *   `settings` (TEXT)
    *   `notes` (TEXT)
*   **`intentions`:** Tracks previously entered intentions.
    *   `id` (INTEGER, Primary Key), `intention_text` (TEXT), `created_at` (TIMESTAMP), `times_used` (INTEGER), `category` (TEXT), `parent_intention_id` (INTEGER)
*   **`generated_content`:** Caches AI stories, prayers, and insights.
    *   `id` (INTEGER, Primary Key), `content_type` (TEXT), `content` (TEXT), `created_at` (TIMESTAMP), `intention_id` (INTEGER), `quality_rating` (INTEGER), `archived` (BOOLEAN)
*   **`healing_history`:** Specific logs for chakra/meridian work.
    *   `id` (INTEGER, Primary Key), `session_id` (INTEGER), `chakra` (TEXT), `meridian` (TEXT), `duration_minutes` (INTEGER), `frequencies_used` (TEXT), `subjective_result` (TEXT)
*   **`blessing_targets` & `blessing_sessions`:** Manages identity records, case numbers, locations, and cumulative counts of mantras/rotations dedicated per target.
*   **`mantra_dedications`:** Logs specific mantra counts dedicated to individual targets.
*   **`outlook_narratives`:** Caches astrological transits and daily readings.

### B. Telemetry Database: `backend/vajra_stream.db`

Contains local debugging, tool executions, and system log statistics:

*   **`failed_tool_calls`:** Tracks tools that crashed during execution.
    *   `id` (INTEGER, Primary Key), `timestamp` (TEXT), `tool_name` (TEXT), `arguments` (TEXT), `error_message` (TEXT)
*   **`intentional_paths`:** Traces pathing logic and decisions made by the LLM agent.
    *   `id` (INTEGER, Primary Key), `timestamp` (TEXT), `agent_id` (TEXT), `intention` (TEXT), `missing_tools` (TEXT), `context` (TEXT)
*   **`outlook_narratives`:** Local developer caches.

---

## 4. REST API Endpoint Specification

All REST APIs run on port **8008** under the prefix `/api/v1/`:

*   **Sessions (`/api/v1/sessions`):** `POST /create`, `POST /{id}/start`, `POST /{id}/stop`, `GET /history`.
*   **Populations (`/api/v1/populations`):** CRUD endpoints for targets, import/export JSON, category listings.
*   **Automation (`/api/v1/automation`):** Start/stop/pause/resume autonomous scheduler loops.
*   **RNG Attunement (`/api/v1/rng-attunement`):** Initialize E-meter style sessions, get live reading values, read needle state metrics.
*   **Operator Interface (`/api/v1/operator`):** Exposes `POST /analyze` for intention parsing, `POST /suggest-rates` for dial coordinates, `POST /chat` with the virtual operator, and `/stream` for Server-Sent Events (SSE) insights.
*   **88 Buddhas (`/api/v1/operator`):**
    *   `GET /buddhas/random`: Returns a random Buddha with meaning, realm, light, and narrative.
    *   `GET /buddhas/liturgy`: Returns the full repentance liturgy structure.
    *   `GET /buddhas/recitation/status`: Returns active mala counts and index.
    *   `POST /buddhas/recitation/start`: Starts the background recitation task.
    *   `POST /buddhas/recitation/stop`: Gracefully halts the background loop.
*   **Saka Dawa (`/api/v1/operator/saka-dawa`):** Checks timing window status.

---

## 5. WebSockets Protocol

Real-time data feeds stream over WebSockets at `ws://127.0.0.1:8008/ws`.

### A. Outgoing Server-to-Client Messages

The backend broadcasts event payloads to keep the Vite frontend reactive without polling:

#### 1. `RNG_READING`
Pushed at 1-3Hz during attunement or active scheduling.
```json
{
  "type": "RNG_READING",
  "data": {
    "session_id": "uuid-string",
    "coherence": 0.81,
    "entropy": 0.49,
    "floating_needle_score": 0.75,
    "tone_arm": 5.4,
    "needle_position": 12.5,
    "needle_state": "floating",
    "trend": 0.08,
    "quality": "excellent"
  },
  "timestamp": 178293021.45
}
```

#### 2. `BUDDHA_RECITATION_UPDATE`
Emitted as the 88 Buddhas recitation loop advances to a new name.
```json
{
  "type": "BUDDHA_RECITATION_UPDATE",
  "data": {
    "running": true,
    "intention": "world peace",
    "current_index": 12,
    "current_cycle": 1,
    "total_recited": 100,
    "mala_count": 12,
    "dedications": 4,
    "total_buddhas": 88,
    "current_buddha": {
      "name_chinese": "南無金剛堅强消伏坏散佛",
      "name_pinyin": "Namo Jingang Jianqiang Xiaofu Huaisan Fo",
      "category": "past"
    },
    "progress_pct": 13.6,
    "started_at": "2026-05-31T13:50:00Z"
  },
  "timestamp": 178293025.10
}
```

#### 3. `SAKA_DAWA_CHECK`
Emitted periodically during operations to indicate active merit multipliers.
```json
{
  "type": "SAKA_DAWA_CHECK",
  "data": {
    "is_saka_dawa": true,
    "multiplier": 10000,
    "is_duchen": false,
    "lunar_month": 4,
    "lunar_day": 12,
    "current_date": "2026-05-31T13:50:00Z"
  },
  "timestamp": 178293025.12
}
```

#### 4. `SCALAR_WAVE_ACTIVE` / `RADIONICS_RATE_BROADCAST`
Updates scalar frequencies and virtual rate dials (e.g. 0-100 coordinates).
```json
{
  "type": "RADIONICS_RATE_BROADCAST",
  "data": {
    "rate": 52.8,
    "session_id": "uuid",
    "frequency": 528.0
  },
  "timestamp": 178293028.00
}
```

### B. Client-to-Server Heartbeat

The frontend client must establish heartbeat loops to maintain connection stability:
- **Ping:** Client sends `{"type": "ping"}` every 30 seconds.
- **Pong:** Server responds with `{"type": "pong"}` to keep TCP sockets alive.
