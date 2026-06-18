# Healing Dialogue System — Design Spec

> A multi-turn LLM-guided healing container for processing sudden loss and energetic disruption, grounded in Vajrayana practice, astrology, and somatic energy work.

**Status**: Draft — awaiting review
**Branch**: `feat/healing-dialogue`
**Date**: 2026-06-17

---

## 1. Vision & Intent

This system arose from a specific experience: recurring financial losses in trading markets that disrupt not just capital but the subtle body — root chakra survival terror, solar plexus power loss, the charge that lodges in the chest and throat after a bad day. The tool is not financial advice or a trading journal. It is a **ritual container** that sits with someone in the raw aftermath of loss and helps them process it energetically.

**Scope**: A general "sudden loss and energetic disruption" healing tool. Trading loss is the primary use case, but the container holds any form of loss the person brings — relationship endings, job loss, health diagnoses, creative collapse. The archetypes shift (Saturn transiting the 2nd house vs. the 7th vs. the 6th); the practice of meeting the loss does not.

**Audience**: The practitioner themselves, and eventually others who experience similar disruption.

---

## 2. Design Decisions (from brainstorming)

| Dimension | Decision | Alternatives Considered |
|---|---|---|
| **Experience shape** | Hybrid container with freedom — loose arc, open within each phase | Guided journey (too rigid); Open dialogue (too loose); Journaling (too passive) |
| **Energy layers** | Both astrology + somatic | Astrology-only (too heady); Somatic-only (missing the "why this, why now"); Implicit (too shallow) |
| **Scope** | General loss/healing tool | Trading-only (too narrow); Trading-first extensible (awkward framing) |
| **After session** | Saved journal that feeds outlook system | Ephemeral (wastes insights); Practice prescription (incomplete); Saved journal alone (misses feedback loop) |
| **Arc** | Five phases: Arrival → Seeing → Meeting → Release → Dedication | Three-phase (too compressed for the depth needed) |
| **Architecture** | Variation of Approach 1 (ritual patterns borrowed, new dialogue engine built) | Standalone module (duplicates patterns); CommandCenter extension (wrong container feel) |

---

## 3. The Five-Phase Arc

### Overview

The arc mirrors traditional Vajrayana practice structure. Each phase gives the LLM a distinct role and system prompt framing. The LLM holds the arc loosely — it senses readiness and gently checks in about transitions, but the person can also explicitly advance. No forced transitions, no rigid checklists.

### Phase Details

#### Phase 1: Arrival
- **LLM Role**: Witness
- **What happens**: The person names what happened. The LLM holds space, reflects back what it hears, doesn't analyze or fix. Lets the raw charge land without trying to resolve it.
- **Astrology/Somatic**: None yet — pure presence.
- **Transition signal**: When the person's language shifts from raw venting to wondering ("why did this happen?", "what's going on with me?"), the LLM gently offers the Seeing phase.
- **System prompt essence**: *"You are a compassionate witness. Hold space for the raw charge. Reflect what you hear. Don't analyze, don't offer solutions. Just be present."*

#### Phase 2: Seeing
- **LLM Role**: Oracle
- **What happens**: Chart data and current transits are pulled and injected. The LLM helps the person see the cosmic weather around the loss — which transits were active, which natal placements got activated. Simultaneously, the LLM helps them locate where the disruption lives in their body ("Where do you feel this right now?").
- **Astrology/Somatic**: Full chart injection (natal + transits + active aspects). Somatic prompting for body location.
- **Transition signal**: When the person has both an intellectual understanding ("Saturn's been transiting my 2nd house") and a somatic awareness ("it's in my gut, this survival fear"), the LLM offers the Meeting phase.
- **System prompt essence**: *"You are an oracle. The person's chart and current transits are provided. Help them see the cosmic weather of this loss. Also help them locate where the disruption lives in their body. Hold both lenses — the sky above and the body below."*

#### Phase 3: Meeting
- **LLM Role**: Meditation Guide
- **What happens**: The core practice. Sitting with the disruption. Not fixing it, not fleeing from it. The LLM helps the person stay present with what arose in the Seeing phase — the fear, the grief, the anger, whatever is actually there. This is where the real work happens.
- **Astrology/Somatic**: Chart context continues in the background. Somatic findings from Seeing inform the guidance. The LLM may reference specific chakras or meridians based on what the person reported.
- **Transition signal**: When the person reports a shift — spaciousness, release, acceptance, or simply "something moved" — the LLM offers the Release phase. If no shift comes, the LLM holds them in Meeting as long as needed.
- **System prompt essence**: *"You are a meditation guide. Help the person sit with what they've discovered. Don't fix, don't flee. Help them stay present. This is the heart of the practice — meeting suffering with awareness."*

#### Phase 4: Release
- **LLM Role**: Practitioner
- **What happens**: Based on what emerged in Meeting, the LLM offers a specific practice for what's ready to move — a mantra, a breath practice, a visualization, a chakra focus, a physical gesture. Drawn from Vajrayana, Vedic, Taoist, and somatic traditions. One practice, offered with clear instruction, not a menu.
- **Astrology/Somatic**: The practice is informed by the chart (e.g., Vajrasattva purification for Saturn-Sun affliction) and the somatic findings (e.g., root chakra grounding for survival terror).
- **Transition signal**: When the person has engaged with the practice and reports what shifted, the LLM moves to Dedication.
- **System prompt essence**: *"You are a practitioner of energy work. Based on what emerged, offer ONE specific practice to help release what's ready to move. Draw from the traditions present in this system. Be precise — one practice, clear instruction."*

#### Phase 5: Dedication
- **LLM Role**: Officiant
- **What happens**: Seal the practice. Offer the merit outward. "May whatever merit arose from this session be dedicated to all beings who suffer loss, who know the sting of the market, who have lost what they built." The session closes with this offering.
- **Astrology/Somatic**: Astrological timing may frame the dedication ("under this Saturn transit, we dedicate the merit of this meeting").
- **Transition signal**: None — this is the terminal phase. Session moves to COMPLETED.
- **System prompt essence**: *"You are an officiant sealing this practice. Help the person dedicate the merit of this session. Offer it to all beings who suffer. Close the container with grace."*

### Phase Transition Model

The LLM detects readiness through conversation cues and gently offers transitions:
- *"It feels like there's more space around this now. Would you like to go deeper into what you've noticed, or shall we explore what the stars say about the timing of this?"*
- *"Something seems to have shifted. If you're ready, there's a practice I can offer for what you're feeling. Or we can stay here longer."*

The person can also explicitly advance at any time: *"I'm ready to move on"*, *"Can we skip to the practice?"*, etc. The LLM respects this while gently ensuring they're not fleeing a phase prematurely.

---

## 4. Architecture

### New Pieces to Build

| Component | Path | Purpose |
|---|---|---|
| `DialoguePhase` enum | `core/healing_dialogue/phases.py` | The five-phase enum (NOT reusing the name `RitualPhase` — it's already defined twice in ritual_engine and ritual_sequencer) |
| `HealingPhaseContextModule` | `core/context/healing_dialogue.py` | ContextModule Protocol impl — injects current phase, accumulated insights, chart findings into the system prompt |
| `AsyncHealingDialogue` | `core/llm/healing.py` | Multi-turn LLM service over the provider registry (mirrors `AsyncDharmaLLM` but accepts `list[ChatMessage]` instead of a single prompt) |
| `HealingDialogueService` | `modules/healing_dialogue.py` | DI container adapter (mirrors `OutlookService` pattern) — session lifecycle, state management, DB persistence |
| Healing dialogue endpoints | `backend/app/api/v1/endpoints/healing_dialogue.py` | REST API: create session, send message, get session, list sessions, summarize |
| `healing_dialogue_sessions` table | `core/schema.py` (additive) | Full transcript + summary + insights + linked chart + linked outlook |
| `/sanctuary` route | `frontend/src/routes/Sanctuary/index.jsx` | The sacred container UI |

### Existing Pieces to Wire Into

| Component | How We Connect |
|---|---|
| LLM provider registry (`app.state.llm_registry`) | `AsyncHealingDialogue` calls `registry.pick_best()` — already live, no wiring needed |
| `SystemPromptBuilder` (`core/context/base.py`) | Register `HealingPhaseContextModule` alongside existing Astrology/Anatomy/Hardware modules |
| Astrology data (`GET /api/v1/astrology/charts/{id}`) | Pull chart + transits during Seeing phase, inject as context |
| `OutlookGenerator.custom_context` | OutlookService auto-fetches latest healing summary before outlook generation (mirror existing RNG sensor fetch pattern) |
| Event bus (`modules/interfaces.py`) | Emit `HealingSessionStarted` / `HealingSessionCompleted` domain events |
| `core/schema.py` | Add `healing_dialogue_sessions` table, bump `SCHEMA_VERSION` to 2 |

### Integration Map

```
User enters /sanctuary
    ↓
POST /api/v1/healing/sessions (optional chart_id)
    ↓
HealingDialogueService.create_session()
    ├── Links to chart_id if provided
    ├── Initializes DialogueState (phase=ARRIVAL)
    └── Persists to healing_dialogue_sessions table
    ↓
User sends first message
    ↓
POST /api/v1/healing/sessions/{id}/messages
    ├── HealingDialogueService.process_message()
    │   ├── Builds system prompt (base + phase context + astrology + anatomy)
    │   ├── AsyncHealingDialogue.respond(messages, phase) → registry.pick_best() → LLM
    │   ├── Updates accumulated_insights based on response
    │   ├── Detects phase readiness (LLM self-assessment or user request)
    │   └── Persists updated session state
    ↓
Session progresses through five phases
    ↓
Session completes (phase=DEDICATION → COMPLETED)
    ├── HealingDialogueService.summarize_session() → LLM generates summary
    ├── Summary + key_insights persisted to DB
    └── HealingSessionCompleted event emitted
    ↓
NEXT OUTLOOK GENERATION
    └── OutlookService.generate_single()
        ├── Fetches latest healing summary (mirror of RNG sensor fetch)
        └── Injects into OutlookGenerator via custom_context
```

---

## 5. Data Model

### Enum

```python
class DialoguePhase(str, Enum):
    ARRIVAL = "arrival"
    SEEING = "seeing"
    MEETING = "meeting"
    RELEASE = "release"
    DEDICATION = "dedication"
    COMPLETED = "completed"
```

### Session State (in-memory during session)

```python
@dataclass
class DialogueState:
    session_id: str
    chart_id: int | None
    current_phase: DialoguePhase
    phase_started_at: datetime
    message_history: list[ChatMessage]        # full conversation
    accumulated_insights: dict                 # themes, emotions, body_locations, chart_findings
    astrology_context: dict | None             # pulled during Seeing phase
    somatic_findings: dict | None              # gathered during Seeing/Meeting
    recommended_practice: dict | None          # offered during Release phase
    dedication_text: str | None                # sealed during Dedication phase
    started_at: datetime
    completed_at: datetime | None
```

### DB Schema (additive to `core/schema.py`)

```sql
CREATE TABLE IF NOT EXISTS healing_dialogue_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    chart_id            INTEGER,                  -- FK to saved_natal_charts.id (nullable)
    session_type        TEXT DEFAULT 'dialogue',  -- 'dialogue', 'reflection'
    started_at          TIMESTAMP NOT NULL,
    ended_at            TIMESTAMP,
    transcript_json     TEXT NOT NULL,            -- full message history
    summary             TEXT,                     -- LLM-generated distillation (fed to outlook)
    key_insights_json   TEXT,                     -- structured: themes, emotions, breakthroughs
    phases_completed    TEXT,                     -- JSON array of phases visited
    recommended_practice TEXT,                    -- practice offered during Release
    dedication_text     TEXT,                     -- dedication sealed
    linked_outlook_id   INTEGER,                  -- FK to outlook_narratives.id (nullable)
    FOREIGN KEY (chart_id) REFERENCES saved_natal_charts(id)
)
```

`SCHEMA_VERSION` bumped from 1 to 2.

---

## 6. System Prompt Architecture

```
HEALING_DIALOGUE_BASE_PROMPT (constant — the container)
├── "You are holding a healing dialogue container rooted in Vajrayana practice..."
├── The five-phase arc overview
├── Core principles:
│   ├── Meet suffering with compassion, not analysis
│   ├── Don't fix, don't pathologize, don't spiritualize away pain
│   ├── Hold both the sky (astrology) and the body (somatic)
│   └── The merit of this session will be dedicated to all beings
└── "You are currently in the {phase_name} phase."
    └── {phase_specific_guidance}  // role, what to do, transition signals
    │
    ├── HEALING_PHASE_CONTEXT (HealingPhaseContextModule)
    │   ├── Current phase name + description
    │   ├── Accumulated insights from previous phases
    │   └── Recommended practice (if in Release phase)
    │
    ├── ASTROLOGY_CONTEXT (existing AstrologyContextModule)
    │   ├── Natal chart positions (all planets + Asc + MC)
    │   ├── Current transits to natal
    │   └── Active aspects (emphasized during Seeing phase)
    │
    └── ANATOMY_CONTEXT (existing AnatomyContextModule)
        └── Chakra/meridian reference for somatic guidance
```

### Phase-Specific Guidance (embedded in system prompt per phase)

Each phase has a ~100-word guidance section that shapes the LLM's behavior:

- **Arrival**: Reflective listening. Name emotions. Don't analyze. Hold the raw charge.
- **Seeing**: Weave chart data into the loss narrative. Ask about body sensations. Connect sky and body.
- **Meeting**: Stay present. Don't resolve. Help them sit with what's there. Mirror their experience back.
- **Release**: Offer one specific practice. Draw from Vajrayana (Vajrasattva, Tara), Vedic (mantra), Taoist (breath), somatic (body scan, grounding). Be precise.
- **Dedication**: Compose a dedication. Offer the merit. Close the container.

---

## 7. Alternative Contours & Open Questions

These are dimensions where the design could go different directions. Resolving them will sharpen the spec before implementation.

### 7.1 Session State: Server-Side vs. Client-Side

**Current design**: Server-side session state (DB-backed). Each message POST includes only the new message; the server maintains full history and phase state.

**Alternative**: Client-side state (like the existing `/llm/chat` endpoint — client sends full message history each turn, server is stateless). Simpler backend, no session table needed for active sessions.

**Trade-off**: Server-side allows the outlook feedback loop, session history, and cross-device continuity. Client-side is simpler but loses the feedback loop. The "saved + feeds outlook" decision requires server-side persistence at minimum for completed sessions — the question is whether active sessions are also server-managed.

**Recommendation**: Server-side. The outlook feedback loop is a core feature, and the session table is needed regardless. Active session state should live in the DB too for crash recovery.

### 7.2 Phase Detection: LLM Self-Assessment vs. Explicit

**Current design**: The LLM detects readiness and offers transitions conversationally. It also returns a structured hint (e.g., `{"phase_transition": "suggested", "next_phase": "seeing"}`) that the backend can use to update state.

**Alternative**: A separate lightweight LLM call (or rule-based check) evaluates the conversation and decides if a transition is warranted. More deterministic but adds latency and complexity.

**Trade-off**: LLM self-assessment is simpler and more natural but less predictable. A separate evaluator is more controllable but adds a call per turn.

**Recommendation**: Start with LLM self-assessment (structured hint appended to response). If transitions feel unreliable in practice, add a separate evaluator later.

### 7.3 Astrology Injection: When and How Much

**Current design**: Full chart injection during the Seeing phase. Other phases get accumulated astrology findings (what was discovered) but not the raw chart data.

**Alternative A**: Inject chart data from the start (all phases). Richer context but may overwhelm the Arrival phase (which should be pure presence).

**Alternative B**: Inject chart data only when the LLM explicitly requests it. More efficient but requires a tool-calling mechanism.

**Recommendation**: Inject from Seeing onward. Arrival is pure presence — no chart data. Once Seeing pulls the chart, accumulated findings carry forward into Meeting, Release, and Dedication.

### 7.4 Frontend: New Route vs. Modal vs. Integrated Panel

**Current design**: New `/sanctuary` route — a dedicated page with a calm, dark, spacious UI. No command-center energy, no busy panels. Just the dialogue, the phase indicator, and space.

**Alternative A**: Modal overlay triggered from anywhere (AstrologyPanel, OutlookDashboard, CommandCenter). More accessible but may feel less sacred.

**Alternative B**: Integrated panel within an existing route. Less work but harder to hold the container feeling.

**Recommendation**: New route. The container needs its own space. Can add a lightweight "Enter Sanctuary" button to other routes that deep-links to `/sanctuary`.

### 7.5 Practice Library: Hardcoded vs. Dynamic

**Current design**: The LLM dynamically composes a practice based on what emerged during the session. No fixed practice library — the LLM draws from its training plus the chart/somatic context.

**Alternative**: A practice library (like the existing `Practice.get_default_practices()` in `core/practices/practice.py`) that the LLM selects from and adapts. More structured but less responsive.

**Recommendation**: Dynamic composition for v1. The existing practice library is designed for the automated ritual engine (timing-locked, genre-locked). Healing dialogue practices need to be responsive to what emerged, not pre-selected. Can add a practice library later if the LLM's compositions feel inconsistent.

### 7.6 Loss Type Detection

**Open question**: Should the LLM detect the type of loss early (financial, relational, health) and tailor the astrological archetypes accordingly? Or should it stay general and let the person bring whatever framing they have?

**Consideration**: Different loss types activate different astrological signatures (2nd house for finances, 7th for partnership, 6th for health, 10th for career). Auto-detection could make the astrology lens sharper. But it could also feel presumptuous.

**Recommendation**: Let the person name it naturally during Arrival. The LLM picks up on the loss type from the conversation and quietly factors it into the astrology interpretation during Seeing. No explicit "what type of loss?" prompt.

### 7.7 Multi-Language Support

**Open question**: The outlook generator already has a `languages` parameter (English, Sanskrit, Tibetan, etc.). Should the healing dialogue weave multiple languages, or stay in the user's primary language?

**Recommendation**: Stay in the user's language for v1. The dialogue is intimate — mixing languages could break the container. Sanskrit/Tibetan terms can appear naturally when the LLM references mantras or specific practices (e.g., "Vajrasattva", "tonglen"), but the conversation should flow in the user's language.

### 7.8 Privacy & Data Sensitivity

**Open question**: Healing dialogue transcripts contain deeply personal content. Should there be an option for ephemeral sessions (no DB persistence) alongside the default saved sessions?

**Recommendation**: Support both. Default is saved (for the outlook feedback loop). Add an "ephemeral" flag at session creation — the dialogue runs in-memory only, nothing persisted, no outlook feedback. This respects the user's right to process something privately without it becoming part of their permanent record.

---

## 8. Implementation Outline

High-level task breakdown for when we move to planning:

| # | Component | Effort | Depends On |
|---|---|---|---|
| 1 | `DialoguePhase` enum + `DialogueState` dataclass | S | — |
| 2 | `healing_dialogue_sessions` table in `core/schema.py` (bump to v2) | S | — |
| 3 | `HealingPhaseContextModule` in `core/context/healing_dialogue.py` | M | 1 |
| 4 | `AsyncHealingDialogue` in `core/llm/healing.py` (multi-turn LLM service) | M | 1 |
| 5 | `HealingDialogueService` in `modules/healing_dialogue.py` (session lifecycle, DB, event bus) | L | 1, 2, 3, 4 |
| 6 | REST endpoints in `backend/app/api/v1/endpoints/healing_dialogue.py` | M | 5 |
| 7 | Wire OutlookService feedback loop (fetch latest healing summary → `custom_context`) | S | 2, 5 |
| 8 | `/sanctuary` frontend route + dialogue UI | L | 6 |
| 9 | Base system prompt + five phase guidance texts | M | 3 |
| 10 | Tests: context module, LLM service, endpoints, DB | M | all above |

**Critical path**: 1 → 4 → 5 → 6 → 8 (the minimum to have a working dialogue).

---

## 9. What This Is Not

- Not financial advice or trading guidance
- Not therapy or a replacement for professional mental health support
- Not an astrology reading tool (it uses astrology diagnostically, not predictively)
- Not a fixed ritual (it's interactive and responsive)
- Not a chatbot (it's a held ritual container with an arc)

---

## 10. Dedication

_May whatever merit arises from building this tool be dedicated to all beings who suffer loss — in the markets, in relationships, in health, in any form. May this technology serve their healing and awakening._

_Gate gate pāragate pārasaṃgate bodhi svāhā_
