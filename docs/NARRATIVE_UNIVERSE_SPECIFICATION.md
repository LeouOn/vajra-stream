# Narrative Universe Specification: Realms, Characters, and Broadcast Loops

## Overview and Vision

Vajra.Stream uses a Narrative Generation and Outlook subsystem to weave astrological alignments, divination oracles (Tarot and I Ching), and sacred entities into sutra-style blessings and parables. To allow advanced, localized storytelling, the subsystem incorporates a **Narrative Universe** model with JSON-backed settings:
1. **Locations & Realms**: Earthly coordinates (with automatic lat/lon overrides) and Metaphysical dimensions (with frequency tunings and celestial anchors).
2. **Esoteric Characters**: Archetypes featuring distinct dialogue styles, mantras, and roles that are woven into direct dialogues in stories.
3. **Continuous Broadcast Loops**: Background loops that periodically trigger the LLM to write blessings for the active realms and populations, streaming events live to the UI dashboard.

This document details the architecture, JSON storage formats, REST APIs, and tool-calling execution patterns for developers, future agents, and automation LLMs.

---

## 1. System Architecture

```
                       ┌────────────────────────┐
                       │   React UI Dashboard   │
                       └────────────────────────┘
                                   │  (REST API calls)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend Server                          │
│                                                                        │
│  ┌───────────────────────┐            ┌─────────────────────────────┐  │
│  │   OutlookEndpoints    │───────────▶│       OutlookService        │  │
│  │   (API Controllers)   │            │   (Event Bus Coordinator)   │  │
│  └───────────────────────┘            └─────────────────────────────┘  │
│              │                                       │                 │
│              │ (CRUD)                                │ (Start / Stop)  │
│              ▼                                       ▼                 │
│  ┌───────────────────────┐            ┌─────────────────────────────┐  │
│  │   Universe Managers   │            │   Continuous Broadcast Loop │  │
│  │ (Character, Location) │            │     (Background Task)       │  │
│  └───────────────────────┘            └─────────────────────────────┘  │
│              │ (Read / Write)                        │                 │
│              ▼                                       │ (Generate)      │
│  ┌───────────────────────┐                           ▼                 │
│  │     JSON Datastores   │◀──────────────────────────┴                 │
│  │ (characters/locations)│                                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Universe Data Models

### 2.1 Character Schema (`NarrativeCharacter`)

Characters represent spiritual guides, deities, or historical figures who speak in parables and blessings.

```python
@dataclass
class NarrativeCharacter:
    # Identity
    id: str                         # Unique ID, prefix: "char_"
    name: str                       # e.g., "Zen Master Zhao"
    role: CharacterRole             # master, student, alchemist, hero, deity, guardian, custom
    description: str                # Background narrative biography
    source_type: CharacterSourceType # manual, generated, mythology, historical

    # Esoteric Settings
    dialogue_style: str = "cryptic and profound"
    associated_realms: list[str] = field(default_factory=list) # Realm IDs frequented
    mantra_preference: str | None = None
    elemental_anchor: str = "space" # earth, water, fire, air, space, aether

    # System Tracking
    priority: int = 5               # Priority 1-10
    is_active: bool = True
    added_time: float = field(default_factory=time.time)
    last_used_time: float | None = None
    total_narratives_featured: int = 0
    tags: list[str] = field(default_factory=list)
    notes: str = ""
```

#### Seeded Defaults:
- `char_zhao_master`: **Zen Master Zhao** (Enigmatic zen riddles / koans)
- `char_hermes_alchemist`: **Alchemist Hermes** (Verbose alchemical analogies about base metals)
- `char_chenrezig_deity`: **Bodhisattva Chenrezig** (Radiating white light, serene, highly compassionate)
- `char_suchandra_hero`: **King Suchandra** (Righteous Dharma King, commanding and spiritually wise)

---

### 2.2 Location & Realm Schema (`NarrativeLocation`)

Locations represent earthly sacred sites or metaphysical pure lands where transmissions originate.

```python
@dataclass
class NarrativeLocation:
    # Identity
    id: str                         # Unique ID, prefix: "loc_"
    name: str                       # e.g., "Mount Kailash"
    description: str                # Mystical geography/dimension details
    location_type: LocationType     # earthly_sacred, metaphysical_realm, cosmic_anchor, historical_academy, custom
    source_type: LocationSourceType # manual, generated, mythology, geographic
    is_metaphysical: bool = False

    # Earthly coordinates (None for metaphysical)
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "UTC"

    # Metaphysical dimensions (None for earthly)
    celestial_coordinates: str | None = None  # e.g., "Taurus 15 degrees"
    dimension_frequency: float | None = None  # e.g., 528.0 Hz (Solfeggio frequencies)

    # Esoteric settings
    realm_governor: str | None = None         # Guardian/deity ruling the realm
    astrological_anchor: str | None = None     # Primary planetary line
    elemental_affinity: str | None = None      # Fire, Water, Earth, Air, Space, Aether

    # System Tracking
    priority: int = 5
    is_active: bool = True
    added_time: float = field(default_factory=time.time)
    last_used_time: float | None = None
    total_narratives_featured: int = 0
    tags: list[str] = field(default_factory=list)
    notes: str = ""
```

#### Seeded Defaults:
- `loc_sukhavati`: **Sukhavati (Pure Land)** (Metaphysical, 528Hz, governed by Amitabha Buddha)
- `loc_shambhala`: **Shambhala Kingdom** (Metaphysical, 432Hz, governed by King Suchandra)
- `loc_kailash`: **Mount Kailash** (Earthly, 31.0667° N, 81.3125° E, governed by Shiva/Chakrasamvara)
- `loc_alexandria`: **Alexandria Hermetic Academy** (Earthly, 31.2001° N, 29.9187° E, governed by Hermes Trismegistus)

---

## 3. JSON Storage Engine

Data is stored as JSON to align with offline-first local operation:
- **Characters Store**: `~/.vajra-stream/characters.json`
- **Locations Store**: `~/.vajra-stream/locations.json`

On startup, if these files do not exist or are empty, the `CharacterManager` and `LocationManager` self-seed default records and write the files to the user's home folder directory.

---

## 4. API Reference

All routes are prefixed with `/api/v1/outlook`.

### 4.1 Character CRUD

| Method | Route | Description | Payload Schema |
|--------|-------|-------------|----------------|
| **GET** | `/characters` | List all characters | None |
| **POST** | `/characters` | Create custom character | `CharacterCreate` |
| **GET** | `/characters/{id}` | Get character details | None |
| **PUT** | `/characters/{id}` | Update character attributes | Partial JSON |
| **DELETE** | `/characters/{id}` | Delete character | None |
| **GET** | `/characters/roles/list` | List available roles | None |

### 4.2 Location CRUD

| Method | Route | Description | Payload Schema |
|--------|-------|-------------|----------------|
| **GET** | `/locations` | List all locations | None |
| **POST** | `/locations` | Create custom location | `LocationCreate` |
| **GET** | `/locations/{id}` | Get location details | None |
| **PUT** | `/locations/{id}` | Update location attributes | Partial JSON |
| **DELETE** | `/locations/{id}` | Delete location | None |
| **GET** | `/locations/types/list` | List location types | None |

### 4.3 Generation & Loop Controls

#### POST `/generate_single`
Trigger a single-pass narrative outlook based on coordinates, characters, realms, and target populations.

```json
{
  "lat": 34.0522,
  "lon": -118.2437,
  "languages": ["English", "Sanskrit"],
  "genre": "healing",
  "date": "2026-05-26T00:00:00Z",
  "custom_context": "Soothe anxiety",
  "realm_id": "loc_kailash",
  "population_ids": ["pop_123"],
  "character_ids": ["char_zhao_master"],
  "excluded_forces": ["restlessness"],
  "include_dialogue": true
}
```

#### POST `/loop/start`
Start the background transmission loop generating a narrative at set intervals.

```json
{
  "interval_minutes": 15,
  "genre": "alchemist",
  "languages": ["English", "Latin"],
  "realm_id": "loc_alexandria",
  "character_ids": ["char_hermes_alchemist"],
  "include_dialogue": true
}
```

#### POST `/loop/stop`
Stop the running background generation loop. Returns: `{"status": "success", "message": "Broadcast loop stopped successfully"}`.

#### GET `/loop/status`
Check if the loop is active, what parameters it uses, and view the last generated story.

---

## 5. Tool-Calling Automation Guidelines for LLM Operators

When programmatically automating Vajra.Stream narrative cycles, use the following operational flow:

### 5.1 Dynamic Realm & Dialogue Scripting

To orchestrate a story scene between characters in a specific setting:
1. **Select / Create Settings**: Check `/locations` to find a suitable location. If none matches the theme, write to `/locations` to establish a new earthly or metaphysical realm.
2. **Materialize Actors**: Write to `/characters` to establish character descriptions and `dialogue_style`.
3. **Execute Narrative**: Call `/generate_single` providing the `realm_id`, `character_ids`, and setting `include_dialogue` to `true`.

### 5.2 Broadcast Loop Operation
 
 To configure a continuous automated broadcast:
 1. Check the loop status via `GET /loop/status`.
 2. Stop any existing loop with `POST /loop/stop`.
 3. Select the target population IDs from `GET /api/v1/populations/`.
 4. Start the loop via `POST /loop/start` with a suitable interval (e.g. `15` to `60` minutes).
 
 ---
 
## 6. LLM Agent Tools & Local Command Fallbacks
 
To enable programmatic control by autonomous LLM operators, the narrative subsystem registers its tools in the agent registry [tools.py](file:///c:/Users/llama/OneDrive/proj/vajra-stream/backend/core/llm_agent/tools.py) and configures natural language matches in the local fallback router [llm.py](file:///c:/Users/llama/OneDrive/proj/vajra-stream/backend/app/api/v1/endpoints/llm.py).
 
### 6.1 Programmatic Agent Tool Registry
 
The following functions are exposed to LLM agents:
- `generate_single_outlook(lat, lon, languages, genre, custom_context, realm_id, population_ids, character_ids, excluded_forces, include_dialogue)`
- `generate_epic_outlook(lat, lon, languages, genre, stages, custom_context, realm_id, population_ids, character_ids, excluded_forces, include_dialogue)`
- `list_narrative_locations()`
- `create_narrative_location(name, description, location_type, ...)`
- `list_narrative_characters()`
- `create_narrative_character(name, role, description, ...)`
- `start_narrative_loop(interval_minutes, ...)`
- `stop_narrative_loop()`
- `get_narrative_loop_status()`
 
### 6.2 Local Fallback Natural Language Commands
 
When the Vajra.Stream server runs in offline or rule-based fallback mode, operators can type these commands into the AI Command Center chat:
- `generate outlook` or `write blessing narrative` -> calls `generate_single_outlook`
- `list realms` or `show settings` -> calls `list_narrative_locations`
- `list characters` or `show archetypes` -> calls `list_narrative_characters`
- `start narrative loop` or `activate broadcast loop` -> calls `start_narrative_loop`
- `check narrative loop status` or `loop status` -> calls `get_narrative_loop_status`
- `stop narrative loop` or `deactivate story loop` -> calls `stop_narrative_loop`
 
---
 
### Verification and Event Output
The generated narratives are logged directly to the SQLite `outlook_narratives` table in `vajra_stream.db`. Furthermore, each successful narrative cycle publishes a `BlessingGenerated` event to the system event bus, causing live updates to flash on the operator HUD panels.
