# UI/UX Rework + Test Suite Cleanup — Design Spec

**Status**: Auto-approved by user
**Branch**: `feat/healing-dialogue` (based on main@6c89dd9)
**Date**: 2026-06-20

---

## 1. Nav Consolidation (12 → 7 routes)

### Current (12 flat routes)
```
Command Center | Sanctuary | 88 Buddhas | Operations | Cosmic Clock |
Outlook | Broadcast | Meditate | Visualizer | Grimoire | TTS | Settings
```

### Proposed (7 grouped routes)
```
1. Command Center    ← AI chat + operator dashboard (unchanged)
2. Practice          ← tabs: Sanctuary / 88 Buddhas / Meditation / Visualizer
3. Cosmic Clock      ← astrology (unchanged)
4. Outlook           ← narrative generation (unchanged)
5. Operations        ← tabs: Automation / Broadcast / Divination
6. Grimoire          ← correspondence search (unchanged)
7. Settings          ← tabs: LLM Providers / TTS / Audio
```

### Route migration map
| Old Route | New Location | How |
|---|---|---|
| `/sanctuary` | `/practice/sanctuary` | Sub-route of Practice |
| `/buddhas` | `/practice/buddhas` | Sub-route of Practice |
| `/meditation` | `/practice/meditation` | Sub-route of Practice |
| `/visualizers` | `/practice/visualizers` | Sub-route of Practice |
| `/broadcast` | `/operations` (tab) | Merge into Operations |
| `/tts` | `/settings` (tab) | Merge into Settings |
| `/command-center` | `/command-center` | Unchanged |
| `/astrology` | `/astrology` | Unchanged |
| `/outlook` | `/outlook` | Unchanged |
| `/grimoire` | `/grimoire` | Unchanged |
| `/settings` | `/settings` | Unchanged (gains TTS tab) |

### Practice page structure
```
/practice              → redirect to /practice/sanctuary (default)
/practice/sanctuary    → SanctuaryPage (healing dialogue)
/practice/buddhas      → BuddhasPage (88 Buddhas recitation)
/practice/meditation   → RothkoGenerator fullscreen
/practice/visualizers  → 3D sacred geometry
```

Sub-tab navigation via Ant Design `Tabs` or `Segmented` at the top of the Practice page.

### Operations page structure
```
/operations            → Automation tab (default)
/operations/broadcast  → Broadcast panel
/operations/divination → Tarot / I Ching / Geomancy
```

### Settings page structure
```
/settings              → LLM Providers tab (default)
/settings/tts          → TTS configuration
/settings/audio        → Audio device settings
```

---

## 2. Meditate + Visualizer Consolidation

Merge into the Practice page with sub-tabs. The current implementations stay unchanged internally — just wrapped in a tabbed container.

### Meditation tab
- Full-screen Rothko art generator with audio spectrum
- "Exit" button returns to Practice tab view (not browser back)

### Visualizer tab
- 3D sacred geometry + stars (R3F Canvas)
- Visualization selector (Sacred Geometry / Mandala / Flower of Life)

---

## 3. Test Suite Cleanup

### Current: 549 Python tests across 75 files + 26 frontend test files

### Strategy: Cut redundant, move integration to e2e, keep focused unit tests

**Cut** (testing implementation details or heavy duplication):
- `test_core_modules.py` (34 tests) — tests internal module wiring, overlaps with focused tests
- `test_integration.py` (27 tests) — overlaps with `test_operator.py` and service tests
- `test_container_modules.py` (10 tests) — tests DI container plumbing, not behavior
- `test_task_10.py` (8 tests) — legacy task verification, no longer relevant
- `test_services.py` (8 tests) — generic service smoke tests, superseded by focused tests

**Keep but trim** (trim to essential cases):
- `test_operator.py` (40 → ~15) — keep endpoint behavior, cut internal state checks
- `test_astrology.py` (35 → ~20) — keep calculation accuracy, cut duplicate API tests
- `test_ritual_engine.py` (19 → ~10) — keep core loop, cut edge cases
- `test_ritual_scheduler.py` (18 → ~8) — keep scheduling logic, cut config variations

**Move to e2e** (need full stack):
- Any test that uses `TestClient(app)` with real DB operations
- Endpoint tests that verify the full request → DB → response cycle
- Tests that require the orchestrator or WebSocket manager

**Keep as-is** (high value, well-focused):
- All `test_healing_*.py` (129 tests) — fresh, well-written
- All `test_divination.py` (15 tests) — tarot system
- All `tests/core/llm/` (71 tests) — provider registry
- All `tests/core/context/` (17 tests) — context modules
- All frontend tests (361 tests)

### Target: ~350 Python tests (from 549) + structured e2e suite

---

## 4. Implementation Order

### Phase 1: Route consolidation (frontend only)
1. Create `/practice` route with Tabs (Sanctuary / Buddhas / Meditation / Visualizer)
2. Move existing components into the tabbed layout
3. Update `routes.ts` — remove 4 old entries, add 1 "Practice" entry
4. Create `/operations` tabs (merge Broadcast)
5. Move TTS into Settings tabs
6. Update all internal links/redirects

### Phase 2: Test cleanup
1. Delete redundant test files
2. Trim oversized test files
3. Restructure `tests/e2e/` with proper fixtures
4. Verify CI still passes

### Phase 3: UI polish
1. Consistent header styling across all routes
2. Consistent dark theme tokens
3. Remove dead CSS / unused imports
4. Verify responsive layout on all pages

---

## 5. What This Is Not
- Not a backend refactor (all APIs stay the same)
- Not a new design system (staying on AntD v6 + Tailwind)
- Not a performance optimization pass (focus is UX clarity)
- Not removing any features (just reorganizing access to them)
