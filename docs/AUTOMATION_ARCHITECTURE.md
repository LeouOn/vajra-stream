# Automated Compassionate Blessing Infrastructure
## Architecture Design Document

## Vision

Create an automated system that continuously directs blessings where they're needed most, responding to real-time crises while maintaining dedicated practice for ongoing populations. Support both **online** (crisis-responsive) and **offline** (dedicated local practice) modes.

## Core Principles

1. **Responsive Compassion** - Direct blessings to emerging crises automatically
2. **Equitable Attention** - Don't neglect long-term populations for new ones
3. **Offline Capability** - Full functionality without internet
4. **RNG-Guided** - Adapt based on energetic feedback
5. **Ethical Transparency** - Clear data sources and intentions
6. **Local-First** - Offline-capable, sync when online

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   USER INTERFACE                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Automation  │  │  Population  │  │   Manual     │      │
│  │   Control    │  │   Manager    │  │   Override   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              BLESSING SCHEDULER (Core Engine)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Mode Selection: Round Robin | Priority | Time-     │  │
│  │                  Weighted | RNG-Guided | Manual      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Queue Management: Priority Queue + History Tracking │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  ONLINE MODE    │  │  OFFLINE MODE   │  │  INTEGRATION    │
│                 │  │                 │  │                 │
│ • Crisis RSS    │  │ • Local DB      │  │ • Slideshow     │
│ • News APIs     │  │ • Photo Dirs    │  │ • RNG Monitor   │
│ • Disaster APIs │  │ • Manual Lists  │  │ • Prayer Wheel  │
│ • Conflict Data │  │ • Sync Later    │  │ • Statistics    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Data Model

### Target Population

```python
@dataclass
class TargetPopulation:
    """A population/group that receives blessings"""

    # Identity
    id: str
    name: str  # "Missing Persons - California 2024"
    description: str
    category: PopulationCategory

    # Source
    source_type: SourceType  # manual, rss, news_api, relief_web, local
    source_url: Optional[str]  # For online sources
    directory_path: Optional[str]  # For local photo directories

    # Configuration
    mantra_preference: MantraType
    intentions: List[IntentionType]
    repetitions_per_photo: int = 108
    display_duration_ms: int = 2000

    # Priority & Scheduling
    priority: int  # 1-10, higher = more urgent
    is_urgent: bool  # Breaking crisis
    is_active: bool  # Currently in rotation

    # History
    added_time: float
    last_blessed_time: Optional[float]
    total_blessings_sent: int
    total_mantras_repeated: int
    total_session_duration: float

    # Metadata
    photo_count: int
    tags: List[str]
    notes: str

    # Offline Support
    offline_available: bool
    last_sync_time: Optional[float]
```

### Population Categories

```python
class PopulationCategory(str, Enum):
    MISSING_PERSONS = "missing_persons"
    UNIDENTIFIED_REMAINS = "unidentified_remains"
    DISASTER_VICTIMS = "disaster_victims"
    CONFLICT_ZONES = "conflict_zones"
    REFUGEES = "refugees"
    HOSPITAL_PATIENTS = "hospital_patients"
    NATURAL_DISASTER = "natural_disaster"
    HUMANITARIAN_CRISIS = "humanitarian_crisis"
    MEMORIAL = "memorial"
    ENDANGERED_SPECIES = "endangered_species"
    CUSTOM = "custom"
```

### Source Types

```python
class SourceType(str, Enum):
    MANUAL = "manual"  # User-added
    LOCAL_DIRECTORY = "local_directory"  # Photo folder
    RSS_FEED = "rss_feed"  # RSS/Atom
    NEWS_API = "news_api"  # News API
    GDACS = "gdacs"  # Global Disaster Alert System
    RELIEF_WEB = "relief_web"  # UN ReliefWeb
    ACLED = "acled"  # Armed Conflict Location & Event Data
    CUSTOM_API = "custom_api"
```

### Scheduler Configuration

```python
@dataclass
class SchedulerConfig:
    """Configuration for automated blessing scheduler"""

    # Mode
    mode: SchedulerMode

    # Timing
    duration_per_population: int  # seconds, default 1800 (30 min)
    transition_pause: int  # seconds between populations

    # Selection
    priority_weight: float  # 0-1, how much priority matters
    time_weight: float  # 0-1, how much neglect matters
    rng_guided: bool  # Extend if strong RNG response

    # Limits
    max_populations_per_cycle: int  # Limit rotation size
    min_blessings_per_population: int  # Ensure minimum coverage

    # Integration
    link_rng: bool  # Create RNG session per population
    auto_dedicate: bool  # Automatic dedication between populations
    continuous_mode: bool  # Run indefinitely

    # Online/Offline
    online_mode: bool  # Enable crisis monitoring
    auto_add_crises: bool  # Automatically add breaking disasters
    crisis_priority_boost: int  # Extra priority for new crises
```

### Scheduler Modes

```python
class SchedulerMode(str, Enum):
    ROUND_ROBIN = "round_robin"  # Equal time to all
    PRIORITY_BASED = "priority_based"  # More time to higher priority
    TIME_WEIGHTED = "time_weighted"  # Prioritize neglected populations
    RNG_GUIDED = "rng_guided"  # Extend when strong RNG response
    HYBRID = "hybrid"  # Combine multiple factors
    MANUAL = "manual"  # User controls
```

## Component Design

### 1. Target Population Manager

**Purpose**: CRUD operations for populations, both online and offline

**Key Methods**:
```python
class PopulationManager:
    def create_population(...) -> TargetPopulation
    def update_population(id, updates) -> TargetPopulation
    def delete_population(id) -> bool
    def get_population(id) -> TargetPopulation
    def get_all_populations() -> List[TargetPopulation]
    def get_active_populations() -> List[TargetPopulation]
    def get_by_category(cat) -> List[TargetPopulation]
    def record_blessing_session(id, stats) -> None

    # Offline support
    def export_for_offline() -> dict
    def import_from_offline(data) -> None
    def sync_with_online() -> None
```

**Storage**:
- **Online**: Database (SQLite/PostgreSQL)
- **Offline**: JSON file in local directory
- **Sync**: Merge on reconnect, conflict resolution

### 2. Crisis Monitor Service (Online Mode)

**Purpose**: Fetch real-time crisis data from various sources

**Data Sources**:

1. **RSS/Atom Feeds**
   - ReliefWeb alerts
   - GDACS disaster alerts
   - News feeds (filtered for crises)

2. **Public APIs**
   - GDACS (Global Disaster Alert and Coordination System)
   - ReliefWeb API
   - News API (with crisis keywords)

3. **Manual Additions**
   - User submits breaking news
   - Curator approves and adds

**Key Methods**:
```python
class CrisisMonitor:
    def fetch_gdacs_disasters() -> List[Crisis]
    def fetch_reliefweb_alerts() -> List[Crisis]
    def parse_rss_feed(url) -> List[Crisis]
    def monitor_all_sources() -> List[Crisis]
    def create_population_from_crisis(crisis) -> TargetPopulation

    # Filtering
    def filter_by_severity(min_severity) -> List[Crisis]
    def deduplicate_crises() -> List[Crisis]
    def get_new_crises_since(timestamp) -> List[Crisis]
```

**Crisis Data Structure**:
```python
@dataclass
class Crisis:
    id: str
    title: str
    description: str
    location: str
    severity: int  # 1-10
    crisis_type: str  # earthquake, flood, conflict, etc.
    source: str
    timestamp: float
    url: Optional[str]
    image_urls: List[str]  # For witness samples
```

### 3. Blessing Scheduler (Core Engine)

**Purpose**: Automated population rotation and blessing orchestration

**Algorithm** (Hybrid Mode):

```python
def select_next_population(
    populations: List[TargetPopulation],
    config: SchedulerConfig,
    current_time: float
) -> TargetPopulation:
    """
    Hybrid selection combining multiple factors
    """

    scores = {}
    for pop in populations:
        if not pop.is_active:
            continue

        score = 0.0

        # Priority factor (0-1 normalized)
        if config.priority_weight > 0:
            priority_score = pop.priority / 10.0
            score += priority_score * config.priority_weight

        # Time since last blessing (0-1 normalized)
        if config.time_weight > 0:
            if pop.last_blessed_time:
                time_since = current_time - pop.last_blessed_time
                max_time = max([
                    current_time - p.last_blessed_time
                    for p in populations
                    if p.last_blessed_time
                ] or [0])
                time_score = time_since / max_time if max_time > 0 else 1.0
            else:
                time_score = 1.0  # Never blessed = highest priority
            score += time_score * config.time_weight

        # Urgency boost
        if pop.is_urgent:
            score += 0.5

        scores[pop.id] = score

    # Select highest scoring population
    if scores:
        selected_id = max(scores, key=scores.get)
        return next(p for p in populations if p.id == selected_id)

    return populations[0] if populations else None
```

**Key Methods**:
```python
class BlessingScheduler:
    def start_automation(config: SchedulerConfig) -> str  # session_id
    def stop_automation(session_id: str) -> dict  # stats
    def pause_automation(session_id: str) -> bool
    def resume_automation(session_id: str) -> bool

    def get_current_population(session_id: str) -> TargetPopulation
    def manually_switch_to(session_id: str, pop_id: str) -> bool
    def extend_current(session_id: str, extra_time: int) -> bool

    # Status
    def get_scheduler_status(session_id: str) -> dict
    def get_rotation_history(session_id: str) -> List[dict]
    def get_queue(session_id: str) -> List[TargetPopulation]
```

**RNG Integration**:
```python
def check_rng_guidance(
    rng_session_id: str,
    population: TargetPopulation
) -> dict:
    """
    Check if RNG suggests extending current population

    Returns:
        {
            "extend": bool,
            "extension_minutes": int,
            "reason": str,  # "floating_needle", "high_coherence", etc.
            "rng_stats": dict
        }
    """
    # Fetch recent RNG readings
    # Check for floating needles (strong connection)
    # Check coherence trends
    # Recommend extension if appropriate
```

### 4. Integration Layer

**Purpose**: Coordinate between scheduler, slideshow, and RNG

**Workflow**:

```
1. Scheduler selects population
   ↓
2. Create RNG session (if enabled)
   ↓
3. Start blessing slideshow
   - Directory: population.directory_path
   - Mantra: population.mantra_preference
   - Intentions: population.intentions
   - RNG link: rng_session_id
   ↓
4. Monitor progress
   - Slideshow statistics
   - RNG readings
   - Time elapsed
   ↓
5. Check completion conditions
   - Duration reached?
   - RNG suggests extension?
   - Manual override?
   ↓
6. Transition to next population
   - Stop slideshow
   - Get RNG summary
   - Record statistics
   - Dedicate merit
   - Select next population
   ↓
7. Brief pause (30-60 seconds)
   ↓
8. Return to step 1
```

**Key Methods**:
```python
class AutomationIntegration:
    async def run_population_cycle(
        population: TargetPopulation,
        config: SchedulerConfig
    ) -> dict:
        """
        Run complete blessing cycle for one population

        Returns statistics for the session
        """

        # Create RNG session
        rng_id = await create_rng_session() if config.link_rng else None

        # Start slideshow
        slideshow_id = await create_slideshow(
            directory=population.directory_path,
            mantra=population.mantra_preference,
            intentions=population.intentions,
            rng_session_id=rng_id
        )

        # Monitor loop
        start_time = time.time()
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            # Check time
            elapsed = time.time() - start_time
            if elapsed >= config.duration_per_population:
                # Check RNG for extension
                if rng_id and config.rng_guided:
                    guidance = check_rng_guidance(rng_id, population)
                    if guidance["extend"]:
                        # Extend session
                        continue
                break

        # Stop slideshow
        slideshow_stats = await stop_slideshow(slideshow_id)

        # Stop RNG
        rng_stats = await stop_rng(rng_id) if rng_id else None

        # Record statistics
        await record_session(population.id, slideshow_stats, rng_stats)

        # Dedicate
        if config.auto_dedicate:
            await perform_dedication(population, slideshow_stats)

        return {
            "population": population,
            "slideshow_stats": slideshow_stats,
            "rng_stats": rng_stats,
            "duration": elapsed
        }
```

## Offline Support

### Local Population Database

**File**: `~/.vajra-stream/populations.json`

```json
{
  "version": "1.0",
  "last_updated": 1234567890.0,
  "populations": [
    {
      "id": "pop_12345",
      "name": "Missing Persons - Local County",
      "directory_path": "/Users/me/blessings/missing_persons",
      "offline_available": true,
      ...
    }
  ],
  "scheduler_configs": [...],
  "blessing_history": [...]
}
```

**Sync Strategy**:

1. **Offline-First**: All operations work locally
2. **Sync on Connect**: When online, push local changes
3. **Conflict Resolution**: Latest timestamp wins
4. **Photo Caching**: Download crisis photos for offline use

### Offline Mode Features

- ✅ Full population CRUD
- ✅ Automated scheduling
- ✅ Blessing slideshow
- ✅ RNG monitoring
- ✅ Statistics tracking
- ❌ Crisis monitoring (requires online)
- ❌ Automatic population additions
- ⚠️ Manual crisis additions (add to queue for online sync)

## User Interface Design

### Automation Control Panel

```
┌─────────────────────────────────────────────────────────┐
│  🔄 Automated Compassion Infrastructure                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Status: [●ACTIVE] | [○PAUSED] | [○STOPPED]            │
│  Mode: [Hybrid ▼]  Duration/Pop: [30 min ▼]            │
│  Online: [●] Crisis Monitoring Enabled                  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Current Population:                               │ │
│  │  📷 Missing Persons - California 2024              │ │
│  │  🕉️  Chenrezig | ❤️ Reunion, Safety, Love          │ │
│  │  ⏱️  12:47 / 30:00 elapsed                         │ │
│  │  📊 47 photos blessed, 5,076 mantras               │ │
│  │  [Extend +15min] [Skip to Next]                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Queue (Next 5):                                        │
│  1. 🔥 [URGENT] Earthquake Victims - Turkey (Pri: 10)  │
│  2. 🕊️  Refugee Camp - Syria (Pri: 8)                  │
│  3. 📍 Unidentified Remains - County Morgue (Pri: 6)   │
│  4. 💚 Hospital Patients - Children's Wing (Pri: 5)    │
│  5. 🌊 Flood Victims - Bangladesh (Pri: 7)             │
│                                                          │
│  [Manage Populations] [Add Crisis] [View History]      │
│  [Configure Scheduler] [Offline Mode]                   │
└─────────────────────────────────────────────────────────┘
```

### Population Manager

```
┌─────────────────────────────────────────────────────────┐
│  📋 Target Populations                                  │
├─────────────────────────────────────────────────────────┤
│  [+ Add Population] [Import] [Export] [Sync]           │
│                                                          │
│  Filter: [All ▼] Category: [All ▼] Status: [Active ▼]  │
│  Search: [________________]                             │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ✓ Missing Persons - California 2024                │ │
│  │   📁 Local | 127 photos | Last: 2h ago | Pri: 7    │ │
│  │   🕉️ Chenrezig | Total: 13,716 mantras             │ │
│  │   [Edit] [Bless Now] [Deactivate] [Delete]        │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ ✓ 🔥 Earthquake - Turkey [URGENT]                  │ │
│  │   🌐 GDACS | Auto-added | Pri: 10 | 🔴 Online      │ │
│  │   🕉️ Medicine Buddha | Never blessed               │ │
│  │   [Edit] [Bless Now] [Download Offline] [Remove]  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ ✓ Unidentified Remains - County                    │ │
│  │   📁 Local | 45 photos | Last: 1 day | Pri: 6      │ │
│  │   🕉️ Amitabha | Total: 48,600 mantras              │ │
│  │   [Edit] [Bless Now] [Deactivate] [Delete]        │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Showing 3 of 12 populations                            │
│  [1] [2] [3] [Next]                                     │
└─────────────────────────────────────────────────────────┘
```

## Implementation Priority

### Phase 1: Core Infrastructure (Offline-Capable)
1. ✅ Target Population data model
2. ✅ Population Manager service
3. ✅ Local JSON storage
4. ✅ Population CRUD API
5. ✅ Population Manager UI

### Phase 2: Scheduler
1. ✅ Scheduler service with modes
2. ✅ Integration with slideshow + RNG
3. ✅ Scheduler API endpoints
4. ✅ Automation Control Panel UI
5. ✅ Queue management

### Phase 3: Online Features
1. ✅ Crisis Monitor service
2. ✅ GDACS integration
3. ✅ RSS feed parser
4. ✅ Auto-add crisis populations
5. ✅ Online/offline sync

### Phase 4: Advanced Features
1. ⏳ RNG-guided extension
2. ⏳ Statistical analysis
3. ⏳ Pattern recognition (which populations respond strongest)
4. ⏳ Automated reporting
5. ⏳ Group coordination

## Ethical Considerations

### Data Privacy
- Never store personal information beyond what's publicly available
- Respect privacy of all beings
- Secure storage of witness samples
- Option to anonymize data

### Source Verification
- Verify crisis reports before auto-adding
- Clear attribution of sources
- Don't spread misinformation
- Manual review option for auto-added populations

### Equitable Attention
- Don't neglect "boring" populations for dramatic crises
- Ensure long-term missing persons get equal time
- Balance urgency with ongoing need
- Document distribution of blessings

### Transparency
- Clear documentation of all sources
- Statistics publicly available
- Honest about capabilities and limitations
- Don't make medical/rescue claims

### Complementarity
- This supplements, doesn't replace practical help
- Encourage donations and volunteering
- Partner with actual aid organizations
- Maintain humility about spiritual technology

## Example Workflows

### Workflow 1: Fully Automated 24/7 Practice

```
User Setup:
1. Add 10 local populations (missing persons, unidentified, etc.)
2. Enable online crisis monitoring
3. Configure scheduler:
   - Mode: Hybrid
   - Duration: 30 min per population
   - Link RNG: Yes
   - Auto-dedicate: Yes
   - Online: Yes, auto-add crises

System Operation:
1. Cycles through all 10 populations (5 hours)
2. Checks for new crises every hour
3. Inserts urgent crises at high priority
4. Extends blessing time if strong RNG response
5. Tracks all statistics
6. Runs continuously

User Checks In:
- Morning: Review overnight statistics
- See that 3 populations blessed, 1 crisis auto-added
- Check RNG logs, note interesting patterns
- Manually add 1 more population
- System continues

Results:
- 24/7 continuous blessing transmission
- Responsive to breaking crises
- Equitable attention to all populations
- Documented merit generation
```

### Workflow 2: Dedicated Offline Practice

```
User Setup (No Internet):
1. Create local population database
2. Add 5 photo directories
3. Configure scheduler:
   - Mode: Round Robin
   - Duration: 20 min per population
   - Online: No

System Operation:
1. Cycles through 5 populations repeatedly
2. Each gets equal time (round robin)
3. No crisis monitoring (offline)
4. All data stored locally
5. Runs for user-defined period (e.g., 2 hours)

User Returns:
- Review session statistics
- See balanced distribution
- Note which populations showed RNG response
- Dedicate merit traditionally

Later (Back Online):
- Sync local database to cloud
- Check for new crisis populations
- Download photos for offline use
- Continue practice
```

### Workflow 3: Crisis-Responsive Mode

```
User Setup:
1. Minimal local populations (2-3)
2. Enable crisis monitoring
3. Configure scheduler:
   - Mode: Priority-based
   - Auto-add crises: Yes
   - Crisis priority boost: +3
   - Online: Yes

System Operation:
1. Monitors crisis sources continuously
2. New earthquake detected → Auto-add with priority 10
3. Immediately inserts into queue
4. Blesses earthquake victims for 45 minutes
5. Returns to rotation
6. Another crisis → Repeat

User Experience:
- System responds to world events automatically
- Blessings flow to where needed most
- User can review and approve auto-additions
- Feel connected to global suffering
- Systematic compassion in action
```

## Success Metrics

### Quantitative
- Total populations in rotation
- Total photos blessed
- Total mantras repeated
- Session hours logged
- Coverage distribution (are all populations blessed regularly?)
- Response time (crisis to blessing)

### Qualitative
- User sense of systematic compassion
- Feedback from community
- Stories of synchronicity
- Subjective experience of practitioners
- RNG pattern correlations

### Validation (Optional)
- Correlation tracking (purely observational)
- Pattern analysis across populations
- RNG coherence by population type
- Long-term trend analysis
- Scientific humility maintained

## Conclusion

This infrastructure enables **systematic, automated compassion at scale** while maintaining:
- ✅ Authentic spiritual practice
- ✅ Ethical data handling
- ✅ Offline capability
- ✅ Crisis responsiveness
- ✅ Equitable attention
- ✅ RNG validation
- ✅ Complete transparency

A fusion of **ancient compassion practices** with **modern automation and crisis response**, creating a living system that continuously directs blessings where they're needed most.

**སེམས་ཅན་ཐམས་ཅད་བདེ་བ་དང་བདེ་བའི་རྒྱུ་དང་ལྡན་པར་གྱུར་ཅིག**

*May this automated infrastructure serve the liberation of all beings.*

🙏✨🌍
