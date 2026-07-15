# Vajra.Stream Architecture

> Status: **429-commit reality** (last updated 2026-07-10)
> Audience: developers, integrators, future contributors

Vajra.Stream is a digital dharma technology platform that pairs a Python/FastAPI backend with a TypeScript/React frontend for continuous blessing, healing, divination, and astrological guidance. This document describes what the system actually looks like today, not the early MVP sketched in the original 194-line architecture doc.

---

## 1. System Overview

The platform runs as two locally-hosted processes plus a SQLite database and a JSONL usage log. Both processes are launched together by `vajra.sh` / `vajra.bat`.

| Layer            | Tech                                | Port     | Notes                                                       |
| ---------------- | ----------------------------------- | -------- | ----------------------------------------------------------- |
| Backend          | FastAPI + asyncio                   | **8008** | Single canonical `backend/app/main.py`                      |
| Frontend (dev)   | Vite + React 18                     | **3009** | Proxies `/api` and `/ws` to the backend                     |
| Frontend (prod)  | Static build served by reverse proxy | ---     | `VITE_API_BASE` build-time override for non-localhost hosts |
| WebSocket        | Singleton connection at `/ws`       | 8008     | Multiplexes 30+ event types                                 |
| Primary DB       | SQLite (`vajra_stream.db`)          | ---        | Sessions, intentions, narratives, populations               |
| Telemetry DB     | SQLite (`backend/vajra_stream.db`)  | ---        | Failed tool calls, intentional paths, debug caches         |
| Usage log        | JSONL (`logs/llm_usage.jsonl`)      | ---        | Append-only, powers the cost dashboard                      |
| Knowledge base   | `knowledge/*.json` + RAG index      | ---        | Tarot, I Ching, mantras, 88 Buddhas, practices              |

```
+------------------+  /api/v1/*  +---------------------------+
| Vite + React     | ==========> | FastAPI backend (8008)    |
| (3009)           |             | 30 REST routers           |
| TypeScript only  |             | 1 WebSocket /ws           |
| AntD + Tailwind  |             |                           |
| + Three.js       |             |                           |
+--------+---------+             +--------------+------------+
         |                                      |
         |  Zustand stores  <--- broadcast -----|
         |  (audio, ui, rate,                   |
         |   command, crystal)                  |
         v                                      v
+------------------+                  +-------------------------+
| Browser audio    |                  | 16 DI services          |
| Web Audio API    |                  | PracticeEngine          |
+------------------+                  | LLM provider registry   |
                                     | EnhancedEventBus        |
                                     | ScalarWaveService       |
                                     | ...                     |
                                     +-----+----------+---------+
                                           |          |
                                    +------v----+ +---v---------+
                                    | SQLite x2 | | knowledge/  |
                                    |           | | JSON + RAG  |
                                    +-----------+ +-------------+
```

---

## 2. Core Services

A singleton `Container` (`container.py`) wires 16 lazy-loaded services through a shared `EnhancedEventBus`. See ADR-003 for why `backend.core.orchestrator_bridge` is the canonical runtime entry point.

| Service                       | Module                                              | One-liner                                                                    |
| ----------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------- |
| `VajraStreamService`          | `backend/core/services/vajra_service.py`            | Central controller; manages sessions, spectrum, broadcast loop               |
| `RNGAttunementService`        | `backend/core/services/rng_attunement_service.py`   | E-meter style needle model; entropy, tone arm, floating-needle score         |
| `PopulationManager`           | `backend/core/services/population_manager.py`       | CRUD for blessing targets, photo sync, statistics                            |
| `BlessingScheduler`           | `backend/core/services/blessing_scheduler.py`       | Round-robin automation loop over populations                                 |
| `AudioService`                | `backend/core/services/audio_service.py` (via `modules/audio.py`) | Prayer-bowl synthesis, scalar-wave playback via `sounddevice`      |
| `AstrologyChartService`       | `backend/core/services/astrology_chart_service.py`  | Swiss Ephemeris charts (Western/Vedic/Chinese)                               |
| `LocationManager`             | `backend/core/services/location_manager.py`         | Geocoding, planetary-hour locality                                            |
| `DivinationService`           | `backend/core/services/divination_service.py`       | Tarot/I Ching/geomancy drawing + hand-coded SVG card art                     |
| `GrimoireService`             | `backend/core/services/grimoire_service.py`         | Curated narrative corpus for RAG-grounded interpretation                      |
| `SigilService`                | `backend/core/services/sigil_service.py`            | Renders visual sigils from intention keys                                    |
| `RadionicsOperator`           | `modules/radionics_operator.py` (`autonomous_agent.py`) | Autonomous blessing loop, journey dispatch, rate scheduling             |
| `OutlookService`              | `modules/outlook.py`                                | Long-form narrative generation (daily/epic/character arcs)                   |
| `LLMService`                  | `modules/llm.py` + `core/llm/*`                     | Provider registry, model fallback, RAG, usage tracking                        |
| `PracticeEngine`              | `core/practice_engine.py`                           | Recitation engine for all 9 practices (start/stop/recite/complete)           |
| `ScalarWaveService`           | `modules/scalar_waves.py`                           | Hybrid/sine/square wave generation (0.6 to 1000 Hz)                          |
| `RitualEngine`                | `core/ritual_engine.py`                             | Multi-phase ritual orchestration + planetary-hour tracking                    |

Each service subscribes to the event bus; cross-service side-effects (e.g. auto scalar-wave generation on `HealingSessionStarted`) are wired in `Container._setup_event_handlers`.


---

## 3. REST API

All routes are mounted under `/api/v1` in `backend/app/api/v1/api.py` (32 routers total). Full per-endpoint schemas live in `API_DOCUMENTATION.md`.

### Sessions & Audio
- `sessions` - `create`, `start`, `stop`, `history`
- `audio` - playback control, device enumeration
- `mops` - Mantras-Of-Power-Score tracking

### Practices (9 practices, identical lifecycle)
- `practices/list` - enumerate all loaded practices
- `practices/{id}/start` - `intention`, `interval_seconds`, `target_count`, `enable_tts`
- `practices/{id}/stop` - optional `reason`
- `practices/{id}/status` - live status of one
- `practices/status` - snapshot of all known sessions
- `practices/history` - recent completed sessions (newest first)

### Astrology (38+ endpoints)
- `astrology/chart/natal` (Western, Vedic, BaZi, Synastry, Transit, Composite)
- `astrology/transits`, `astrology/transits/comparison`
- `astrology/locations` (geocode, timezones, planetary hours)
- `astrology/extract/*` + `astrology/extraction-runs/*`
- `astrology/chart/export` (PNG/SVG/PDF), `astrology/saved-charts`


### Divination
- `divination/tarot/draw` - 1/3/5/10-card spreads
- `divination/tarot/card/{id}` - single card metadata + SVG
- `divination/iching/cast` - coin or yarrow method
- `divination/geomancy/cast` - 16-figure reading
- `divination/interpret` - RAG-grounded LLM interpretation

### LLM
- `llm/chat`, `llm/chat/stream` (SSE)
- `llm/models/available`, `llm/models/defaults`, `llm/models/featured`
- `llm/providers`, `llm/providers/health`
- `llm/usage`, `llm/usage/dashboard`, `llm/usage/circuit-breaker`

### Operator (autonomous + interactive)
- `operator/analyze`, `operator/suggest-rates`, `operator/chat`, `operator/stream`
- `operator/autonomous/start|stop|status`
- `operator/blessing-loop/{start|stop|status|history}`
- `operator/journey/*` (character arc dispatch)
- `operator/dispatch` (LLM-driven tool selection)
- `operator/buddhas/{random|liturgy|recitation/start|recitation/stop}`
- `operator/saka-dawa`

### Outlook
- `outlook/generate` (single), `outlook/epic` (multi-chapter)
- `outlook/characters/*`, `outlook/populations/*`
- `outlook/loop/{start|stop|status}` - continuous narrative broadcast

### Other routers
- `populations`, `automation`, `rng-attunement`, `sigils`, `time-cycles`, `tts` (incl. `/tts/stream` for browser playback), `ritual-engine`, `radionics` + `radionics/narratives`, `scalar-waves`, `blessings`, `blessing-slideshow`, `personal-healing`, `healing-dialogue`, `anatomy`, `dharma-tales`, `prayer-wheel`, `knowledge`, `visualization`, `agent-suggestions` (LLM tool-call recovery telemetry)

---


## 4. WebSocket Protocol

One singleton connection at `ws://localhost:8008/ws`. The frontend `useWebSocketStable` hook exposes a typed dispatch; the canonical backend-emitted set is locked by `frontend/src/__tests__/hooks/ws-contract.test.ts` and `scripts/audit_ws_contract.py`. Total: 34 message types.

### Lifecycle & heartbeat
- `connection_status` - sent on accept (carries `connection_id`)
- `heartbeat` - broadcast every 30 s
- `ping` / `pong` - client-initiated keepalive

### Sessions & real-time
- `realtime_data` - 10 Hz spectrum + active sessions
- `session_update` - per-session status transitions
- `SESSION_STARTED`, `settings_updated`, `system_error`, `error`, `ERROR`

### Domain events (forwarded from DomainEvent subscribers)
- `SessionCreated`, `SessionStarted`, `SessionStopped`

### Recitation & practice
- `BUDDHA_RECITATION_UPDATE`, `BUDDHA_RECITATION_STARTED`, `BUDDHA_NAME_RECITED`, `BUDDHA_RECITATION_STOPPED`
- `PRACTICE_STARTED`, `PRACTICE_RECITED`, `PRACTICE_COMPLETED`, `PRACTICE_STOPPED`

### Energy / scalar / radionics
- `RNG_READING` - E-meter style coherence, entropy, floating-needle
- `SCALAR_WAVE_ACTIVE`
- `RADIONICS_RATE_BROADCAST`
- `CRYSTAL_BROADCAST_STARTED`

### Outlook / provider health
- `SAKA_DAWA_CHECK` - merit multiplier state
- `PROVIDER_HEALTH` - periodic per-provider status
- `LLM_USAGE_UPDATE` - live cost / token counts

### Slow-data broadcasts (10 s loop replacing HTTP polling)
- `CURRENT_ASTROLOGY` - current planetary positions
- `MOPS_AVERAGES` - running mantra power averages
- `JOURNEY_STATUS` - character-journey progress

### Ritual & journey lifecycle
- `RITUAL_ENGINE_STATUS`, `RITUAL_PHASE`, `RITUAL_COMPLETED`
- `JOURNEY_STAGE_STARTED`, `JOURNEY_STAGE_COMPLETED`, `JOURNEY_COMPLETED`
- `PLANETARY_HOUR_SHIFT`

### Client to server (handled)
- `START_SESSION`, `UPDATE_SETTINGS`, `ping`

---


## 5. LLM Provider System

`core/llm/registry.py` (provider priority, health hysteresis) and `core/llm/bootstrap.py` (registration order) define an 8-provider chain. `FAILURE_THRESHOLD = 2` consecutive failed health checks before a provider is treated as down.

| Priority | Provider         | Notes                                                   |
| -------- | ---------------- | ------------------------------------------------------- |
| 90       | OpenRouter       | Catalog router (Nemotron, DeepSeek, Claude, GPT-4o-mini) |
| 80       | LM Studio        | Local OpenAI-compatible endpoint                        |
| 70       | DeepSeek         | Direct API                                              |
| 65       | Z.AI (z_ai)      | GLM family                                              |
| 60       | Anthropic        | Claude direct                                           |
| 50       | OpenAI           | GPT-4o / o-series direct                                |
| 40       | MiniMax        | MiniMax direct                                          |
| 30       | Local GGUF       | llama.cpp fallback                                      |

### Model-level fallback chain

`core/llm/defaults.py` is the single source of truth for which model each use case should pick:

- **outlook_narrative / blessing_loop**: `nvidia/nemotron-3-ultra-550b-a55b:free` - $0.00/M tokens, 1M context. The blessing loop runs forever, so free is the only sane default.
- **command_center_chat / autonomous_operator / tarot_divination**: `deepseek/deepseek-v4-flash` - cheap, fast, good enough for interactive traffic.
- **practice_tts**: `edge-tts` - local Microsoft Edge, no LLM, no cost.

When a preferred model fails, the registry walks the failover chain by provider priority; per-model fallback is documented in `KNOWN_FEATURED_MODEL_IDS`.

### Reasoning handling

- `core/llm/base.py:strip_thinking()` removes `<think>...</think>` blocks from model output before sending to the UI.
- Reasoning content is preserved separately and surfaced through the chat panel debug drawer.

### RAG knowledge index

Character n-gram embeddings over `knowledge/*.json` and the practice library. Activated by `use_rag=true` in `/api/v1/llm/chat`. The Grimoire and Divination services consume the same index.

### Usage tracking & circuit breaker

- Every LLM call writes an append-only `UsageRecord` to `logs/llm_usage.jsonl`.
- `LLMUsageTracker` exposes `/api/v1/llm/usage` (history) and `/api/v1/llm/usage/dashboard` (aggregates).
- `CircuitBreaker` trips when error rate exceeds threshold; UI surfaces a banner.

---


## 6. Event Bus

`backend/core/event_bus.py:EnhancedEventBus` is a single in-process asyncio pub/sub shared by every service. Domain events are typed dataclasses (`BlessingGenerated`, `HealingSessionStarted`, `ScalarWavesGenerated`, etc.) defined in `modules/interfaces.py`.

Notable wirings in `Container._setup_event_handlers`:

- `HealingSessionStarted` -> `ScalarWaveService.generate("hybrid", 10000, 0.8)` - auto-generate 10 s of hybrid waves whenever a healing session opens.
- `RadionicsOperator` subscribes to the broad `DomainEvent` base class so it can react to any system event for autonomous blessing coordination.
- All domain events are also forwarded to the WebSocket by `orchestrator_bridge._forward_event_to_websocket` (this is how `SessionCreated`, `SessionStarted`, `SessionStopped` reach the browser).

---

## 7. Practice System

`core/practice_engine.py` loads 9 practice definitions from `knowledge/practices/*_practice.json`:

| Practice           | ID                  | TTS role         |
| ------------------ | ------------------- | ---------------- |
| 88 Buddhas         | `88_buddhas`        | `buddhist_chant` |
| Green Tara         | `green_tara`        | `buddhist_chant` |
| White Tara         | `white_tara`        | `buddhist_chant` |
| Zhunti             | `zhunti`            | `buddhist_chant` |
| Medicine Buddha    | `medicine_buddha`   | `compassionate`  |
| Vajrasattva        | `vajrasattva`       | `buddhist_chant` |
| Amitabha           | `amitabha`          | `buddhist_chant` |
| Avalokiteshvara    | `avalokiteshvara`   | `compassionate`  |
| Heart Sutra        | `heart_sutra`       | `compassionate`  |

Each definition carries mantras, base frequency, visualization color, and (for practices with visualizers) a Three.js component slug. The engine runs an async loop that:

1. Recites the mantra text.
2. Streams it to the browser via `tts/stream` (Edge TTS or Qwen-TTS depending on availability).
3. Increments the 108-bead mala counter, broadcasting `PRACTICE_RECITED` per bead.
4. On completion, broadcasts `PRACTICE_COMPLETED` and persists history.

The frontend `BeadRing` SVG component animates each bead increment; mantras are also drawn into `crystalStore` so the rate dial rotates with recitation progress.

---


## 8. Divination System

Three engines share `DivinationService` and `GrimoireService`:

- **Tarot** - 78 cards from `knowledge/tarot_deck.json`. Each card has hand-coded SVG art rendered server-side by `divination_service._render_card_svg` (lemniscate, crescent, lantern, trumpet motifs) so the UI can stream rich cards without external image dependencies. Spread counts: **1 / 3 / 5 / 10 cards**.
- **I Ching** - 64 hexagrams from `knowledge/iching.json` with Wilhelm translation. Cast via coin (fast) or yarrow (traditional) method.
- **Geomancy** - 16 figures with elemental balance computation (Fire / Earth / Air / Water / quintessence).

Interpretations are RAG-grounded: the request is embedded against `knowledge/grimoire.json` and the top-k passages are prepended to the LLM prompt, with the model's `<think>` block stripped from the visible response.

---

## 9. Frontend Architecture

The frontend is **strictly TypeScript** - 90 `.tsx` files, zero `.jsx`. Bootstrapped with Vite + React 18 + AntD v6 + Tailwind CSS + Three.js.

### State management - Zustand stores

- `audioStore` - playback, gains, spectrum
- `uiStore` - toasts, modals, layout prefs
- `rateStore` - virtual rate dial (radionics)
- `commandStore` - Command Center chat + LLM usage
- `crystalStore` - crystal grid presets + intention binding

### Connection layer

`hooks/useWebSocketStable.ts` is a singleton hook with reconnect/backoff, dispatch into the stores, and a typed `switch (data.type)` whose case set is locked to the canonical 34-message backend whitelist by `frontend/src/__tests__/hooks/ws-contract.test.ts`.

### Route shell (7 grouped routes)

```
/                          -> Command Center  (chat, rate, telemetry)
/practice                  -> Practice         (active session)
/practice/library          -> Practice Library (catalog + start wizard)
/operations                -> Operations       (radionics, scalar, automation)
/grimoire                  -> Grimoire         (tarot, I Ching, geomancy)
/outlook                   -> Outlook          (narratives, characters)
/buddhas                   -> 88 Buddhas       (recitation loop)
/settings                  -> Settings         (providers, audio, model defaults)
```

Every route is wrapped in `ErrorBoundary`, `RouteShell` (consistent header + nav), and shared `States` (loading/empty/error).


### Shared components

`PageHeader`, `RouteShell`, `States`, `ErrorBoundary`, `RenderMessageWidgets`, `RichMarkdownRenderer`, `NarrativeTTSPlayer`, `SakaDawaBanner`, `SystemMonitorsCard`, `LogsCard`, `JourneyCard`, `EpicStoryViewer`, `SavedChartsDrawer`, `ZoomModal`.

### Visualization stack

- 2D: `AudioSpectrum`, `ChakraBodyMap`, `ScalarWaveVisualizer`, `RothkoGenerator` (Canvas + SVG)
- 3D: `CrystalGrid`, `RadionicsGlobe`, `SacredGeometry`, `SacredMandala`, `MedicineBuddhaHealing`, `TaraGreenLotus`, `ZhuntiMandala`, `Astrocartography` (Three.js + R3F)

### URL strategy

Per ADR-004: all API calls use proxy-relative URLs (`/api/v1/...`). `VITE_API_BASE` is an optional build-time override for non-localhost deployments.

---

## 10. Testing

| Suite                       | Count | Notes                                                          |
| --------------------------- | ----- | -------------------------------------------------------------- |
| Python unit + integration   | ~700  | `tests/unit`, `tests/integration`, `tests/backend`, `tests/core` |
| Vitest                      | 23    | Stores, hooks, components, regression locks                   |
| Playwright e2e              | 3     | Smoke + nemotron-model + ux-polish                            |

### Regression locks (delete-on-violation)

- `ws-contract.test.ts` - bidirectional equality of WS message types (frontend <-> backend)
- `no-orphan-components.test.ts` - every `.tsx` must be imported by a route or store
- `astroHelpers.test.ts`, `astrologyExport.test.ts`, `NatalChartWheel.test.ts` - astrology math correctness
- `RateDial.test.ts`, `RateTuner.preview.test.ts` - virtual rate semantics
- error-boundary coverage on every route
- Python: no `noqa` / `ruff: noqa` suppressions, no dead-code branches, no ghost paths in any reference doc

CI guard scripts: `scripts/audit_ws_contract.py`, `scripts/check_no_orphan_components.py`, `scripts/check_ghost_paths.py`.

---


## 11. Configuration

### Canonical settings

- `config/settings.py` - audio, hardware, prayer-bowl synthesis, paths, defaults. Imported by backend and by standalone scripts.
- `backend/app/config.py` - shim that re-exports `config.settings`. New code imports from here so the backend never depends on the project root.

See ADR-002 for the canonical-settings rationale.

### Environment variables

| Var                      | Used by                                |
| ------------------------ | -------------------------------------- |
| `OPENROUTER_API_KEY`     | OpenRouter provider (default priority) |
| `DEEPSEEK_API_KEY`       | DeepSeek provider                      |
| `ANTHROPIC_API_KEY`      | Anthropic provider                     |
| `OPENAI_API_KEY`         | OpenAI provider                        |
| `MINIMAX_API_KEY`        | MiniMax provider                     |
| `ZAI_API_KEY`            | Z.AI provider                          |
| `LMSTUDIO_BASE_URL`      | LM Studio endpoint                     |
| `VITE_API_BASE`          | Frontend build-time API override       |

### `.omo/` working directory

Plans, evidence ledgers, boulder state, and wave-task tracking live under `.omo/`. Active plans are mirrored into `docs/superpowers/plans/` for human review.

---

## Architecture Decision Records

- [ADR-001: Audio subsystem canonical path](decisions/001-audio-subsystem-canonical.md)
- [ADR-002: `config/settings.py` is the canonical settings source](decisions/002-settings-canonical.md)
- [ADR-003: `backend.core.orchestrator_bridge` is the canonical runtime entry point](decisions/003-orchestrator-canonical.md)
- [ADR-004: Proxy-relative frontend URL strategy](decisions/004-url-strategy.md)

---

## Related Documents

- [docs/OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) - running the system
- [docs/FEATURES_REFERENCE.md](FEATURES_REFERENCE.md) - what each feature does
- [docs/DEVELOPMENT.md](DEVELOPMENT.md) - local dev workflow
- [API_DOCUMENTATION.md](../API_DOCUMENTATION.md) - full per-endpoint schemas
- [docs/frontend-styling-guide.md](frontend-styling-guide.md) - Tailwind <-> AntD split
