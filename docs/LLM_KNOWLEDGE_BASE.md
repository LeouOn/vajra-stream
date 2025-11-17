# Vajra Stream LLM Knowledge Base

## Purpose

This document serves as a comprehensive knowledge base for Large Language Models to understand, use, and orchestrate the Vajra Stream radionics and blessing system. It provides detailed information about all modules, APIs, workflows, and integration patterns.

## System Overview

Vajra Stream is a radionics system combining:
1. **RNG Attunement** - Quantum-like random number generation for detecting psychic/paranormal activity
2. **Blessing Slideshow** - Rapid mantra and intention transmission to photos
3. **Population Manager** - CRUD operations for target populations
4. **Blessing Scheduler** - Automated 24/7 rotation through populations

### Core Concepts

- **Radionics**: Broadcasting intentions through witness samples (photos)
- **Floating Needle (FN)**: Indicator of release/completion from Scientology auditing
- **Witness Sample**: Photo representing a person or group
- **Mantra Pulsing**: 10Hz alpha-wave frequency for subliminal effect
- **Round Robin**: Fair time distribution across populations
- **Offline-First**: Works without internet, JSON persistence

---

## Module 1: RNG Attunement Service

### What It Does
Generates quantum-like random numbers to detect psychic or paranormal activity. Implements E-meter style needle visualization with 6 states and floating needle detection.

### When to Use
- Monitoring psychoenergetic activity during radionics
- Detecting release/completion (floating needle)
- Linking to blessing sessions for feedback
- Manual spotting/auditing practices

### Core API

#### Create Session
```python
POST /api/v1/rng/session/create
Body: {
    "baseline_tone_arm": 5.0,     # 0-10, default 5.0
    "sensitivity": 1.0             # 0.1-5.0, default 1.0
}
Response: {
    "session_id": "rng_1234567890_abcdef12"
}
```

#### Get Reading
```python
GET /api/v1/rng/session/{session_id}/reading
Response: {
    "tone_arm": 5.2,
    "needle_position": 15.3,       # -100 to +100
    "needle_state": "rising",      # still, rising, falling, floating, stick, rock_slam
    "floating_needle_score": 0.73, # 0-1, >0.6 indicates FN
    "coherence_index": 0.65,
    "entropy": 0.82,
    "timestamp": 1234567890.123
}
```

#### Get Session Summary
```python
GET /api/v1/rng/session/{session_id}/summary
Response: {
    "session_id": "...",
    "start_time": 1234567890.0,
    "duration": 3600.5,
    "total_readings": 1234,
    "floating_needle_count": 15,
    "average_tone_arm": 5.1,
    "coherence_average": 0.68,
    "entropy_average": 0.85,
    "is_active": true
}
```

#### Stop Session
```python
POST /api/v1/rng/session/{session_id}/stop
Response: {
    "session_id": "...",
    "final_duration": 3600.5,
    "total_readings": 1234
}
```

### Integration Patterns

**Pattern 1: Monitor RNG During Practice**
```
1. Create RNG session
2. Start taking readings (poll every 1-5 seconds)
3. Watch for floating_needle_score > 0.6
4. When FN detected, indicates release/completion
5. Stop session, review summary
```

**Pattern 2: Link RNG to Slideshow**
```
1. Create RNG session first
2. Pass rng_session_id when creating slideshow
3. RNG automatically monitored during blessing
4. Review RNG summary after slideshow stops
```

### Python Service Methods

```python
from backend.core.services.rng_attunement_service import get_rng_service

service = get_rng_service()

# Create session
session_id = service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)

# Get reading
reading = service.get_reading(session_id)  # Returns AttunementReading object

# Check if floating needle
if reading.floating_needle_score > 0.6:
    print("Floating Needle detected!")

# Get summary
summary = service.get_session_summary(session_id)

# Stop
service.stop_session(session_id)
```

### Needle States Explained

- **still**: Minimal movement, stable
- **rising**: Trending positive (yang energy)
- **falling**: Trending negative (release)
- **floating**: Free, rhythmic movement (indicates release/FN)
- **stick**: Stuck, no movement (resistance)
- **rock_slam**: Violent oscillation (heavy charge)

---

## Module 2: Blessing Slideshow Service

### What It Does
Displays photos with overlaid mantras and intentions at specific frequencies (10Hz mantra pulse, 2Hz intention cycle) for rapid blessing transmission.

### When to Use
- Blessing directory of photos
- Manual compassion practice
- Witnessing for radionics broadcast
- Integration with RNG monitoring

### Core Concepts

- **Mantra Pulsing**: 10Hz (100ms intervals) for alpha-wave entrainment
- **Intention Cycling**: 2Hz (500ms intervals) between intentions
- **Repetitions**: Default 108 (traditional count)
- **Display Duration**: How long each photo shows (default 2000ms)
- **Loop Mode**: Auto-restart after last photo

### Core API

#### Create Session
```python
POST /api/v1/slideshow/session/create
Body: {
    "directory_path": "/path/to/photos",
    "intention_set": {
        "primary_mantra": "chenrezig",  # or: tara, medicine_buddha, etc.
        "intentions": ["love", "healing", "peace"],
        "repetitions_per_photo": 108,
        "dedication": "May all beings benefit"
    },
    "loop_mode": true,
    "display_duration_ms": 2000,
    "recursive": false,            # Scan subdirectories
    "rng_session_id": "rng_123..."  # Optional RNG linking
}
Response: {
    "session_id": "blessing_slideshow_1234567890_abcdef12",
    "total_photos": 50
}
```

#### Get Current Slide
```python
GET /api/v1/slideshow/session/{session_id}/current
Response: {
    "photo": {
        "file_path": "/path/to/photo.jpg",
        "filename": "photo.jpg",
        "times_blessed": 3,
        "total_mantra_repetitions": 324,
        "last_blessed_time": 1234567890.0
    },
    "session": {
        "session_id": "...",
        "current_index": 5,
        "total_photos": 50,
        "is_active": true,
        "loop_mode": true,
        "rng_session_id": "rng_123..."
    },
    "overlay": {
        "mantra_text": "Om Mani Padme Hum",
        "mantra_repetitions": 108,
        "intentions": ["May you experience love", "May you be healed", ...],
        "dedication": "May all beings benefit",
        "display_duration_ms": 2000
    },
    "progress": {
        "current": 6,
        "total": 50,
        "percentage": 12.0
    }
}
```

#### Advance Slide
```python
POST /api/v1/slideshow/session/{session_id}/advance
Body: {
    "record_blessing": true  # Whether to count this as a blessing
}
Response: {
    "advanced": true,
    "new_index": 6
}
```

#### Stop Session
```python
POST /api/v1/slideshow/session/{session_id}/stop
Response: {
    "session_id": "...",
    "duration": 600.5,
    "photos_blessed": 25,
    "total_mantras_repeated": 2700,
    "unique_photos": 25,
    "loops_completed": 0
}
```

### Available Mantras

1. **chenrezig** - Om Mani Padme Hum (Compassion)
2. **tara** - Om Tare Tuttare Ture Soha (Swift compassion)
3. **medicine_buddha** - Tayata Om Bekandze... (Healing)
4. **vajrasattva** - Om Vajrasattva Hum (Purification)
5. **manjushri** - Om Ah Ra Pa Tsa Na Dhih (Wisdom)
6. **amitabha** - Om Ami Dewa Hrih (Pure Land)
7. **universal** - Om Ah Hum (Universal blessing)

### Available Intentions

1. **love** - May you experience unconditional love
2. **healing** - May you be completely healed
3. **peace** - May you find deep peace
4. **protection** - May you be protected from all harm
5. **prosperity** - May you have abundance
6. **wisdom** - May you gain clear wisdom
7. **reunion** - May you be reunited with loved ones
8. **safety** - May you be safe
9. **liberation** - May you be liberated from suffering
10. **compassion** - May you receive infinite compassion
11. **clarity** - May you have mental clarity
12. **strength** - May you have inner strength

### Python Service Methods

```python
from backend.core.services.blessing_slideshow_service import (
    get_blessing_slideshow_service,
    IntentionSet,
    MantraType,
    IntentionType
)

service = get_blessing_slideshow_service()

# Create intention set
intention_set = IntentionSet(
    primary_mantra=MantraType.CHENREZIG,
    intentions=[IntentionType.LOVE, IntentionType.HEALING, IntentionType.PEACE],
    repetitions_per_photo=108,
    dedication="May all beings benefit"
)

# Create session
session_id = service.create_session(
    directory_path="/path/to/photos",
    intention_set=intention_set,
    loop_mode=True,
    display_duration_ms=2000,
    rng_session_id="rng_123..."  # Optional
)

# Get current slide
slide = service.get_current_slide(session_id)

# Advance manually (or let auto-advance via timer)
service.advance_slide(session_id, record_blessing=True)

# Stop and get stats
stats = service.stop_session(session_id)
```

---

## Module 3: Population Manager

### What It Does
CRUD operations for managing target populations (groups of beings) that receive automated blessings. Stores data in JSON for offline operation.

### When to Use
- Creating populations for automated rotation
- Organizing different blessing targets
- Tracking blessing statistics per population
- Offline operation (local storage)

### Core API

#### Create Population
```python
POST /api/v1/populations/create
Body: {
    "name": "Missing Persons - California 2024",
    "description": "Database of missing persons from California",
    "category": "missing_persons",  # See categories below
    "source_type": "local_directory",  # See source types below
    "directory_path": "/path/to/photos",  # For local_directory
    "source_url": null,              # For online sources
    "mantra_preference": "chenrezig",
    "intentions": ["love", "reunion", "safety"],
    "repetitions_per_photo": 108,
    "display_duration_ms": 2000,
    "priority": 7,                   # 1-10, higher = more important
    "is_urgent": false,
    "tags": ["california", "2024", "namus"],
    "notes": "Updated monthly from NamUs database"
}
Response: {
    "id": "pop_1234567890_abcdef12",
    "name": "Missing Persons - California 2024",
    "category": "missing_persons",
    ...all fields...
    "added_time": 1234567890.0,
    "photo_count": 150  # Auto-detected
}
```

#### Get Population
```python
GET /api/v1/populations/{population_id}
Response: {
    "id": "pop_123...",
    "name": "...",
    ...all fields...
    "total_blessings_sent": 450,
    "total_mantras_repeated": 48600,
    "total_session_duration": 7200.5,
    "last_blessed_time": 1234567890.0
}
```

#### Get All Populations
```python
GET /api/v1/populations/?active_only=true&category=missing_persons&urgent_only=false
Response: [
    {...population 1...},
    {...population 2...}
]
```

#### Update Population
```python
PUT /api/v1/populations/{population_id}
Body: {
    "priority": 9,  # Only fields to update
    "is_urgent": true,
    "notes": "Updated notes"
}
Response: {...updated population...}
```

#### Delete Population
```python
DELETE /api/v1/populations/{population_id}
Response: {
    "message": "Population deleted successfully",
    "id": "pop_123..."
}
```

#### Get Statistics
```python
GET /api/v1/populations/statistics/overall
Response: {
    "total_populations": 25,
    "active_populations": 20,
    "urgent_populations": 3,
    "total_blessings_sent": 5000,
    "total_mantras_repeated": 540000,
    "total_session_duration": 86400.0,
    "categories": {
        "missing_persons": 8,
        "refugees": 5,
        "disaster_victims": 7,
        ...
    },
    "never_blessed": 2,
    "offline_available": 20
}
```

### Categories

1. **missing_persons** - Missing persons databases
2. **unidentified_remains** - Unidentified remains
3. **disaster_victims** - Natural disaster victims
4. **conflict_zones** - Populations in conflict zones
5. **refugees** - Refugee and displaced populations
6. **hospital_patients** - Hospital patients (with permission)
7. **natural_disaster** - Natural disaster affected areas
8. **humanitarian_crisis** - Humanitarian crises
9. **memorial** - Memorial and remembrance
10. **endangered_species** - Endangered species
11. **custom** - Custom category

### Source Types

1. **manual** - Manually added, no photos
2. **local_directory** - Photos in local folder (offline-capable)
3. **rss_feed** - RSS/Atom feed (online, Phase 3)
4. **news_api** - News API service (online, Phase 3)
5. **gdacs** - Global Disaster Alert System (online, Phase 3)
6. **relief_web** - UN ReliefWeb API (online, Phase 3)
7. **custom_api** - Custom API endpoint (online, Phase 3)

### Python Service Methods

```python
from backend.core.services.population_manager import (
    get_population_manager,
    PopulationCategory,
    SourceType
)

manager = get_population_manager()

# Create population
pop = manager.create_population(
    name="Test Population",
    description="Description",
    category=PopulationCategory.MISSING_PERSONS,
    source_type=SourceType.LOCAL_DIRECTORY,
    directory_path="/path/to/photos",
    mantra_preference="chenrezig",
    intentions=["love", "healing"],
    priority=7,
    is_urgent=False
)

# Get population
pop = manager.get_population(pop.id)

# Update
updated = manager.update_population(pop.id, priority=9, is_urgent=True)

# Delete
success = manager.delete_population(pop.id)

# Get all
all_pops = manager.get_all_populations()

# Get stats
stats = manager.get_statistics()

# Record blessing (called automatically by scheduler)
manager.record_blessing_session(
    population_id=pop.id,
    blessings_sent=50,
    mantras_repeated=5400,
    session_duration=900.0
)
```

### Storage

- Location: `~/.vajra-stream/populations.json`
- Format: JSON list of population dicts
- Auto-saves on every change
- Offline-first design

---

## Module 4: Blessing Scheduler

### What It Does
Automates 24/7 rotation through populations, managing slideshow and RNG integration for each population. Currently implements Round Robin mode for fair time distribution.

### When to Use
- 24/7 automated compassion practice
- Fair distribution of blessing time
- Hands-off operation
- Continuous operation with statistics tracking

### Core API

#### Start Automation
```python
POST /api/v1/automation/start
Body: {
    "mode": "round_robin",           # Phase 1: only this mode available
    "duration_per_population": 1800, # Seconds (30 min default)
    "transition_pause": 30,          # Seconds between populations
    "link_rng": true,                # Create RNG session per population
    "auto_dedicate": true,           # Automatic merit dedication
    "continuous_mode": true,         # Loop indefinitely
    "only_active": true,             # Only include active populations
    "min_priority": 1                # Minimum priority (1-10)
}
Response: {
    "session_id": "scheduler_1234567890_abcdef12",
    "message": "Automated blessing rotation started successfully",
    "populations_in_queue": 15
}
```

#### Get Current Status
```python
GET /api/v1/automation/{session_id}/status
Response: {
    "session_id": "...",
    "status": "running",  # running, paused, stopped, transitioning, error
    "current_population": {
        "id": "pop_123...",
        "name": "Population Name",
        "category": "missing_persons",
        "priority": 7,
        "mantra": "chenrezig",
        "intentions": ["love", "healing"],
        "photo_count": 150
    },
    "elapsed_seconds": 450.5,
    "target_duration": 1800,
    "progress_percentage": 25.0
}
```

#### Get Session Stats
```python
GET /api/v1/automation/{session_id}/stats
Response: {
    "session_id": "...",
    "status": "running",
    "mode": "round_robin",
    "start_time": 1234567890.0,
    "total_duration": 7200.5,
    "cycle_count": 2,                # Complete rotations
    "populations_in_queue": 15,
    "current_index": 5,
    "current_population_id": "pop_123...",
    "current_slideshow_id": "blessing_slideshow_123...",
    "current_rng_id": "rng_123...",
    "completed_sessions": 30,
    "total_photos_blessed": 4500,
    "total_mantras": 486000,
    "total_rng_floating_needles": 45,
    "session_history": [
        {
            "population_id": "pop_123...",
            "population_name": "Name",
            "start_time": 1234567890.0,
            "duration": 1800.5,
            "photos_blessed": 150,
            "mantras_repeated": 16200,
            "rng_floating_needles": 3
        },
        ...
    ]
}
```

#### Get Queue
```python
GET /api/v1/automation/{session_id}/queue
Response: [
    {
        "position": 0,
        "is_current": true,
        "id": "pop_123...",
        "name": "Population Name",
        "category": "missing_persons",
        "priority": 7,
        "is_urgent": false,
        "photo_count": 150,
        "last_blessed": 1234567890.0
    },
    ...
]
```

#### Stop Automation
```python
POST /api/v1/automation/{session_id}/stop
Response: {
    ...same as Get Session Stats, but final values...
}
```

#### Pause/Resume
```python
POST /api/v1/automation/{session_id}/pause
POST /api/v1/automation/{session_id}/resume
Response: {
    "message": "Automation paused/resumed",
    "session_id": "..."
}
```

### Scheduler Modes (Phase 1)

1. **round_robin** (✅ Available) - Equal time to all populations
2. **priority_based** (Phase 2) - More time to higher priority
3. **time_weighted** (Phase 2) - Prioritize neglected populations
4. **rng_guided** (Phase 2) - Extend sessions with strong RNG response
5. **hybrid** (Phase 2) - Combine multiple factors intelligently
6. **manual** (Phase 2) - User controls all transitions

### Python Service Methods

```python
from backend.core.services.blessing_scheduler import (
    get_scheduler,
    SchedulerConfig,
    SchedulerMode
)

scheduler = get_scheduler()

# Start automation
config = SchedulerConfig(
    mode=SchedulerMode.ROUND_ROBIN,
    duration_per_population=1800,  # 30 minutes
    transition_pause=30,
    link_rng=True,
    continuous_mode=True
)

session_id = scheduler.start_automation(config)

# Monitor
status = scheduler.get_current_status(session_id)
stats = scheduler.get_session_stats(session_id)
queue = scheduler.get_queue(session_id)

# Pause/Resume
scheduler.pause_automation(session_id)
scheduler.resume_automation(session_id)

# Stop
final_stats = scheduler.stop_automation(session_id)
```

### How It Works

1. **Queue Building**: Filters populations by active status and priority
2. **Round Robin**: Processes in order by added_time (FIFO)
3. **Per-Population Session**:
   - Creates RNG session (if enabled)
   - Creates blessing slideshow with population's settings
   - Runs for configured duration
   - Stops both services
   - Records statistics
4. **Transition**: Pauses between populations
5. **Loop**: Goes back to start if continuous_mode=True

---

## Integration Workflows

### Workflow 1: Manual RNG-Monitored Practice

**Use Case**: Manual radionics session with psychoenergetic feedback

```
Steps:
1. Create RNG session
   POST /api/v1/rng/session/create

2. Poll for readings every 1-5 seconds
   GET /api/v1/rng/session/{id}/reading

3. Watch floating_needle_score
   - Score > 0.6 indicates floating needle (FN)
   - FN means release/completion

4. When FN detected or practice complete:
   POST /api/v1/rng/session/{id}/stop

5. Review summary
   GET /api/v1/rng/session/{id}/summary
```

**LLM Tool Call Sequence**:
```json
[
  {"tool": "create_rng_session", "params": {"baseline_tone_arm": 5.0}},
  {"tool": "poll_readings", "params": {"interval_seconds": 2, "watch_for_fn": true}},
  {"tool": "stop_rng_session", "params": {}}
]
```

### Workflow 2: Manual Slideshow Practice

**Use Case**: Manual blessing session with specific directory

```
Steps:
1. Create slideshow
   POST /api/v1/slideshow/session/create
   {
     "directory_path": "/path/to/photos",
     "intention_set": {...},
     "display_duration_ms": 2000
   }

2. Auto-advances or manually advance
   POST /api/v1/slideshow/session/{id}/advance

3. Monitor progress
   GET /api/v1/slideshow/session/{id}/current

4. Stop when done
   POST /api/v1/slideshow/session/{id}/stop
```

**LLM Tool Call Sequence**:
```json
[
  {"tool": "create_slideshow", "params": {...}},
  {"tool": "monitor_slideshow", "params": {"auto_stop": true}},
  {"tool": "get_slideshow_stats", "params": {}}
]
```

### Workflow 3: Slideshow + RNG Integration

**Use Case**: Manual practice with psychoenergetic monitoring

```
Steps:
1. Create RNG session first
   session_id_rng = create_rng_session()

2. Create slideshow with RNG link
   create_slideshow(rng_session_id=session_id_rng)

3. Both systems operate together
   - Slideshow advances through photos
   - RNG monitors continuously

4. Stop both
   stop_slideshow()
   stop_rng()

5. Review both summaries
```

**LLM Tool Call Sequence**:
```json
[
  {"tool": "create_rng_session", "params": {}},
  {"tool": "create_slideshow", "params": {"rng_session_id": "$rng_id"}},
  {"tool": "monitor_both", "params": {"duration_seconds": 600}},
  {"tool": "stop_and_review", "params": {}}
]
```

### Workflow 4: Automated 24/7 Rotation

**Use Case**: Hands-off continuous compassion practice

```
Steps:
1. Create populations (if needed)
   POST /api/v1/populations/create (multiple times)

2. Start automation
   POST /api/v1/automation/start
   {
     "mode": "round_robin",
     "duration_per_population": 1800,  # 30 min each
     "continuous_mode": true,
     "link_rng": true
   }

3. Monitor periodically (every 5-10 seconds for UI updates)
   GET /api/v1/automation/{id}/status
   GET /api/v1/automation/{id}/stats

4. Let it run indefinitely
   (System handles everything automatically)

5. Stop when desired
   POST /api/v1/automation/{id}/stop
```

**LLM Tool Call Sequence**:
```json
[
  {"tool": "check_populations", "params": {}},
  {"tool": "start_automation", "params": {"continuous": true}},
  {"tool": "monitor_automation", "params": {"interval_minutes": 5}},
  {"tool": "provide_status_updates", "params": {}}
]
```

### Workflow 5: Population Management

**Use Case**: Organizing and maintaining blessing targets

```
Steps:
1. Create population
   POST /api/v1/populations/create

2. Get statistics overview
   GET /api/v1/populations/statistics/overall

3. Update priorities as needed
   PUT /api/v1/populations/{id}
   {"priority": 9, "is_urgent": true}

4. Export for backup
   POST /api/v1/populations/export

5. Import on another device
   POST /api/v1/populations/import
```

---

## LLM Agent Tool Calling Schemas

### Tool: create_rng_session

```json
{
  "name": "create_rng_session",
  "description": "Create a new RNG attunement session for monitoring psychoenergetic activity",
  "parameters": {
    "type": "object",
    "properties": {
      "baseline_tone_arm": {
        "type": "number",
        "description": "Baseline tone arm setting (0-10), default 5.0",
        "minimum": 0,
        "maximum": 10,
        "default": 5.0
      },
      "sensitivity": {
        "type": "number",
        "description": "Sensitivity multiplier (0.1-5.0), default 1.0",
        "minimum": 0.1,
        "maximum": 5.0,
        "default": 1.0
      }
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "session_id": {"type": "string"}
    }
  }
}
```

### Tool: get_rng_reading

```json
{
  "name": "get_rng_reading",
  "description": "Get current RNG reading including needle state and floating needle score",
  "parameters": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "RNG session ID"
      }
    },
    "required": ["session_id"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "tone_arm": {"type": "number"},
      "needle_position": {"type": "number"},
      "needle_state": {"type": "string"},
      "floating_needle_score": {"type": "number"},
      "coherence_index": {"type": "number"},
      "entropy": {"type": "number"}
    }
  }
}
```

### Tool: create_blessing_slideshow

```json
{
  "name": "create_blessing_slideshow",
  "description": "Create a blessing slideshow session for a directory of photos",
  "parameters": {
    "type": "object",
    "properties": {
      "directory_path": {
        "type": "string",
        "description": "Absolute path to directory containing photos"
      },
      "mantra": {
        "type": "string",
        "enum": ["chenrezig", "tara", "medicine_buddha", "vajrasattva", "manjushri", "amitabha", "universal"],
        "default": "chenrezig"
      },
      "intentions": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["love", "healing", "peace", "protection", "prosperity", "wisdom", "reunion", "safety", "liberation", "compassion", "clarity", "strength"]
        },
        "default": ["love", "healing", "peace"]
      },
      "repetitions_per_photo": {
        "type": "integer",
        "default": 108,
        "minimum": 1
      },
      "display_duration_ms": {
        "type": "integer",
        "default": 2000,
        "minimum": 100
      },
      "loop_mode": {
        "type": "boolean",
        "default": true
      },
      "rng_session_id": {
        "type": "string",
        "description": "Optional RNG session to link"
      }
    },
    "required": ["directory_path"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "session_id": {"type": "string"},
      "total_photos": {"type": "integer"}
    }
  }
}
```

### Tool: create_population

```json
{
  "name": "create_population",
  "description": "Create a new target population for automated blessings",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Clear, descriptive name"
      },
      "description": {
        "type": "string"
      },
      "category": {
        "type": "string",
        "enum": ["missing_persons", "unidentified_remains", "disaster_victims", "conflict_zones", "refugees", "hospital_patients", "natural_disaster", "humanitarian_crisis", "memorial", "endangered_species", "custom"]
      },
      "source_type": {
        "type": "string",
        "enum": ["manual", "local_directory", "rss_feed", "news_api", "gdacs", "relief_web", "custom_api"]
      },
      "directory_path": {
        "type": "string",
        "description": "Required for local_directory source type"
      },
      "mantra_preference": {
        "type": "string",
        "default": "chenrezig"
      },
      "intentions": {
        "type": "array",
        "items": {"type": "string"},
        "default": ["love", "healing", "peace"]
      },
      "priority": {
        "type": "integer",
        "minimum": 1,
        "maximum": 10,
        "default": 5
      },
      "is_urgent": {
        "type": "boolean",
        "default": false
      }
    },
    "required": ["name", "category", "source_type"]
  }
}
```

### Tool: start_automation

```json
{
  "name": "start_automation",
  "description": "Start automated 24/7 rotation through populations",
  "parameters": {
    "type": "object",
    "properties": {
      "mode": {
        "type": "string",
        "enum": ["round_robin"],
        "default": "round_robin",
        "description": "Phase 1: only round_robin available"
      },
      "duration_per_population": {
        "type": "integer",
        "description": "Seconds to spend on each population",
        "minimum": 60,
        "maximum": 86400,
        "default": 1800
      },
      "transition_pause": {
        "type": "integer",
        "description": "Seconds to pause between populations",
        "minimum": 0,
        "maximum": 600,
        "default": 30
      },
      "link_rng": {
        "type": "boolean",
        "default": true
      },
      "continuous_mode": {
        "type": "boolean",
        "default": true,
        "description": "Loop indefinitely if true"
      },
      "only_active": {
        "type": "boolean",
        "default": true
      },
      "min_priority": {
        "type": "integer",
        "minimum": 1,
        "maximum": 10,
        "default": 1
      }
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "session_id": {"type": "string"},
      "populations_in_queue": {"type": "integer"}
    }
  }
}
```

### Tool: get_automation_status

```json
{
  "name": "get_automation_status",
  "description": "Get current automation status (lightweight, for frequent polling)",
  "parameters": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Automation session ID"
      }
    },
    "required": ["session_id"]
  },
  "returns": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "current_population": {"type": "object"},
      "elapsed_seconds": {"type": "number"},
      "progress_percentage": {"type": "number"}
    }
  }
}
```

---

## Common LLM Agent Scenarios

### Scenario 1: User asks "Start blessing the refugees"

**Agent Response**:
```
1. Check if refugee population exists:
   GET /api/v1/populations/?category=refugees

2a. If exists:
    - Start automation focusing on refugees
    - Or create manual slideshow for refugee population

2b. If not exists:
    - Ask user for photo directory
    - Create refugee population
    - Then start blessing
```

### Scenario 2: User asks "How's the automation going?"

**Agent Response**:
```
1. Check if automation is running (check for active session)
2. GET /api/v1/automation/{session_id}/status
3. Format human-friendly response:
   "The automation is currently blessing [Population Name].
    It has completed [X] populations so far, sending [Y] mantras.
    Progress: [Z]% complete with current population."
```

### Scenario 3: User asks "Monitor the RNG for floating needle"

**Agent Response**:
```
1. Create RNG session
2. Poll readings every 2 seconds
3. Check floating_needle_score
4. When score > 0.6:
   "Floating Needle detected! This indicates a release or completion."
5. Provide summary when stopped
```

### Scenario 4: User asks "Create a population for earthquake victims"

**Agent Response**:
```
1. Ask clarifying questions:
   - "Do you have photos in a directory?"
   - "What mantra would you prefer?"
   - "How urgent is this? (priority 1-10)"

2. Create population with gathered info:
   POST /api/v1/populations/create
   {
     "name": "Earthquake Victims [Location] [Date]",
     "category": "disaster_victims",
     "source_type": "local_directory" or "manual",
     ...
   }

3. Confirm creation and offer to:
   - Start blessing immediately
   - Add to automation rotation
```

### Scenario 5: User asks "Make my own radionics journey"

**Agent Response (Full Autonomous Journey)**:
```
1. Explain radionics concepts
2. Set up RNG monitoring
3. Help create or select populations
4. Guide through manual practice:
   - Start slideshow
   - Monitor RNG
   - Recognize floating needle
5. Or set up automation for hands-off practice
6. Provide regular updates and statistics
7. Help interpret results
```

---

## Error Handling

### Common Errors

**Directory Not Found**
```json
{
  "detail": "Directory does not exist: /path/to/photos"
}
```
**Solution**: Verify path exists and has read permissions

**No Photos Found**
```json
{
  "detail": "No photos found in directory: /path/to/photos"
}
```
**Solution**: Check directory has image files (.jpg, .png, etc.)

**Session Not Found**
```json
{
  "detail": "Session not found"
}
```
**Solution**: Session was stopped or ID is incorrect

**No Populations for Automation**
```json
{
  "detail": "No populations available for automation"
}
```
**Solution**: Create populations first with appropriate filters

### Best Practices

1. **Always check if resources exist before operating on them**
2. **Use appropriate polling intervals** (not too frequent)
3. **Handle graceful degradation** (automation can run without RNG)
4. **Validate paths before creating sessions**
5. **Stop sessions when done** (releases resources)
6. **Use try/except for all API calls**
7. **Provide clear error messages to user**

---

## Performance Characteristics

### RNG Attunement
- Reading generation: < 10ms
- Recommended polling: 1-5 seconds
- Memory per session: ~100KB
- Supports: Multiple concurrent sessions

### Blessing Slideshow
- Photo loading: ~50-200ms per photo
- Display update: 60 FPS target
- Memory per session: ~5MB (cached photos)
- Deduplication: By file hash

### Population Manager
- JSON load/save: < 100ms (for 100 populations)
- Search/filter: < 10ms
- Memory: ~1KB per population
- Storage: `~/.vajra-stream/populations.json`

### Blessing Scheduler
- Queue building: < 50ms
- Transition time: Configurable (default 30s)
- Memory: Minimal (delegates to other services)
- Async task management: Non-blocking

---

## Security and Privacy

### Data Storage
- All data stored locally (offline-first)
- No telemetry or external communication
- Photos never uploaded anywhere
- JSON files human-readable

### Permissions Required
- Read access to photo directories
- Write access to `~/.vajra-stream/`

### Privacy Considerations
- Photos of vulnerable populations handled ethically
- System designed for compassionate use only
- No analytics or tracking
- Complete user control

---

## Future Enhancements (Phase 2+)

### Scheduler Modes (Phase 2)
- Priority-based allocation
- Time-weighted (prioritize neglected)
- RNG-guided (extend on strong response)
- Hybrid intelligent mode
- Manual mode with user control

### Online Integration (Phase 3)
- RSS feed monitoring
- News API integration
- GDACS disaster alerts
- ReliefWeb humanitarian data
- Auto-population creation from alerts

### Advanced Features
- Multi-device sync
- Cloud backup (optional)
- Mobile app integration
- Web dashboard
- Calendar-based scheduling
- Geolocation-based priorities

---

## Quick Reference

### Essential Endpoints

| Purpose | Method | Endpoint |
|---------|--------|----------|
| Create RNG | POST | `/api/v1/rng/session/create` |
| Get RNG Reading | GET | `/api/v1/rng/session/{id}/reading` |
| Create Slideshow | POST | `/api/v1/slideshow/session/create` |
| Get Current Slide | GET | `/api/v1/slideshow/session/{id}/current` |
| Create Population | POST | `/api/v1/populations/create` |
| List Populations | GET | `/api/v1/populations/` |
| Start Automation | POST | `/api/v1/automation/start` |
| Automation Status | GET | `/api/v1/automation/{id}/status` |

### Default Values

- Tone Arm: 5.0
- Sensitivity: 1.0
- Repetitions: 108
- Display Duration: 2000ms
- Duration Per Population: 1800s (30 min)
- Transition Pause: 30s
- Mantra: chenrezig
- Intentions: [love, healing, peace]
- Priority: 5

---

## Conclusion

This knowledge base enables LLMs to:
1. Understand all 4 subsystems completely
2. Use APIs correctly with proper parameters
3. Orchestrate complex workflows
4. Help users through their radionics journey
5. Handle errors gracefully
6. Provide intelligent guidance

The system is designed for compassionate automation of blessing practices, combining ancient wisdom (mantras, intentions) with modern technology (RNG monitoring, automation, data persistence).
