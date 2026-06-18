# ADR 003: Canonical Runtime Orchestrator + Event Bus Injection

- **Status:** Accepted (2026-06-18)
- **Deciders:** Wave 2 remediation
- **References:** evaluation Issue 3.1 (orchestrator proliferation), Issue 3.2 (event bus split); ADR 001 (audio canonical); Wave 0 enumeration
- **Gates:** Blocks Wave 3 Task 16 (delete dead code), Wave 4 Task 23 (event bus rewire)
- **Guardrails:** G1 (`scripts/` untouchable), G4 (`BlessingScheduler` untouchable)

## Context

Pre-remediation, four "orchestrators" coexist in the repo. Two are CLI entrypoints, one is dead, and one is the live DI-managed runtime. Without an explicit canonical record, Task 16 (delete `orchestrator_service.py`) and Task 23 (rewire event bus) risk deleting the wrong artifact or rewiring the wrong path.

The four candidates:

| # | File:line | Class | Status |
|---|-----------|-------|--------|
| 1 | `modules/radionics_operator.py:666` | `RadionicsOperator` | ✅ **Canonical** — DI-registered (`container.py:192-199`), lifespan-started (`backend/app/main.py:159`) |
| 2 | `scripts/unified_orchestrator.py:62` | `UnifiedOrchestrator` | ✅ **KEEP** — CLI-isolated, owns its own `EnhancedEventBus` (@ L69); G1 |
| 3 | `scripts/vajra_orchestrator.py:25` | `VajraOrchestrator` | ✅ **KEEP** — README-documented CLI tool, no event bus; G1 |
| 4 | `backend/core/services/orchestrator_service.py:13` | `OrchestratorService` | ❌ **DEAD** — no DI, no lifespan, only `scratch/search_orchestrator_service.py` mentions it |

The lifespan wiring (evaluation Issue 3.1):

```
backend/app/main.py:159              container.operator.start_autonomous_mode(interval_seconds=60)
                                     ↑ resolves via container.py:192 @property provider
container.py:43                      self.event_bus = SimpleEventBus()   ← canonical bus singleton
container.py:198                     RadionicsOperator(container=self, event_bus=self.event_bus)
modules/radionics_operator.py:1274   start_autonomous_mode()
modules/radionics_operator.py:1291   loop = asyncio.get_running_loop()
modules/radionics_operator.py:1292   self._autonomous_task = loop.create_task(self._run_autonomous_loop())
modules/radionics_operator.py:1337   self._autonomous_task.cancel()  (stop_autonomous_mode)
```

## Decision

1. **Canonical runtime orchestrator = `modules/radionics_operator.py:RadionicsOperator` (class @ L666).** All production daemon loops — autonomous radionics, blessing loops, character journeys — must resolve through `container.operator`. Single source of truth: `container.py:192-199` `@property` provider + `backend/app/main.py:159` lifespan start.

2. **KEEP (Guardrail G1 — `scripts/` are CLI-isolated and out of remediation scope):**
   - `scripts/unified_orchestrator.py:62 UnifiedOrchestrator` — CLI entrypoint, owns its own `EnhancedEventBus(persistence_path="data/events.jsonl")` (@ L69), never imported by `backend/`.
   - `scripts/vajra_orchestrator.py:25 VajraOrchestrator` — README-documented CLI tool, no event bus, never imported by `backend/`.

   These are **not duplicates** of the runtime orchestrator; they are user-facing CLI wrappers with isolated state. Unifying them would couple argv parsing into the daemon lifecycle and force two different bus configurations (persisted CLI bus vs. in-memory runtime bus) through one class.

3. **DELETE (Wave 3 Task 16):**
   - `backend/core/services/orchestrator_service.py` (entire file, 136 lines)
   - The only mention outside the file itself is `scratch/search_orchestrator_service.py` (a discovery scratch file, not production).
   - No DI registration, no `start()` caller, no `stop()`, never imported by `backend/app/main.py` or `container.py`.

## Event Bus Injection Plan (Wave 4 Task 23)

**Defect.** `modules/radionics_operator.py:684`:

```python
def __init__(self, container=None, event_bus: EventBus | None = None, llm=None):
    self.event_bus = event_bus or EnhancedEventBus()   # ← fallback creates a SECOND bus
```

The `or EnhancedEventBus()` branch silently mints a *different* bus instance (and a *different type* — `EnhancedEventBus`, not the `SimpleEventBus` produced at `container.py:43`) any time the argument is `None`. Today `container.py:198` always supplies `self.event_bus`, so production has been spared — but the fallback is a latent pub/sub fracture. Any future caller (test fixture, refactor, ad-hoc instantiation) that forgets the argument silently gets a private bus: publishes invisible, subscriptions orphaned.

**Fix (executed in Task 23):**

1. Replace L684 with `self.event_bus = event_bus` (required injection — `None` becomes a hard error on first publish/subscribe, not a silent split).
2. Update the type hint to `event_bus: EventBus` (drop `| None`).
3. Verify `container.py:198` is the sole production constructor call and already passes `event_bus=self.event_bus`. ✓ confirmed.
4. **Behavior-lock test FIRST** (Metis EC1 mitigation): before the edit, add a regression test asserting (a) `Container().operator.event_bus is Container().event_bus` identity, and (b) a publish on `operator.event_bus` is observed by a service wired with `container.event_bus`.

**Acceptance grep (post-Task 23):**

```bash
grep -rn "EnhancedEventBus(" backend/ modules/
```

must return **ZERO** hits. Permitted hits remain in `tests/` (test fixtures: `tests/conftest.py:8`, `tests/e2e/test_orchestration.py:17`, `tests/e2e/test_autonomous_agent.py:25`, `tests/test_foundation.py:14`) and `scripts/unified_orchestrator.py:69` (G1-exempt CLI).

## BlessingScheduler Exemption (Guardrail G4)

`backend/core/services/blessing_scheduler.py:BlessingScheduler` is **explicitly exempt** from any "merge into RadionicsOperator" unification. It is a *leaf component* with a correctly-implemented asyncio task lifecycle:

- `blessing_scheduler.py:184` — `task = asyncio.create_task(self._run_automation_loop(session_id))` (task stored on session)
- `blessing_scheduler.py:372` — `task.cancel()` (graceful stop in `stop_automation`)
- Owns its session queue and slideshow bookkeeping; **consumes** services, does not orchestrate peer daemons.

Merging `BlessingScheduler` into `RadionicsOperator` would (a) violate the single-responsibility split between the long-running *autonomous radionics* daemon and the *rotating blessing slideshow* scheduler, and (b) couple two independent `asyncio.Task` lifecycles into one — multiplying shutdown race conditions instead of reducing them. **G4 holds: `BlessingScheduler` stays a leaf service.**

## Consequences

- **Positive:** One unambiguous runtime orchestrator path (`container.operator`). Future daemon work, debugging, and metrics have exactly one place to instrument.
- **Positive:** Event bus pub/sub integrity restored — single bus instance, single type, no silent fallbacks. Cross-service events (blessing → audio → radionics) cannot be silently split by a missed constructor arg.
- **Positive:** CLI tools (`scripts/*_orchestrator.py`) retain independent event buses and argv surfaces — CLI users see no behavior change.
- **Negative:** Tests that construct `RadionicsOperator()` with no args must be updated to inject a bus (Task 23 scope). Low cost: test fixtures already construct `EnhancedEventBus()` directly — they simply need to pass it through.
- **Risk (EC1 — autonomous operator timing/race):** Removing the `or` fallback and rewiring the bus changes the order in which the autonomous daemon (started at `main.py:159`) first sees bus events. If a subscriber is registered *after* `start_autonomous_mode` runs its first `_autonomous_cycle()` (`radionics_operator.py:1287`), the first cycle's events can be missed. **Mitigation:** Task 23 lands the behavior-lock test first; the edit is only merged once the test asserts both (a) identity of bus instances and (b) in-order subscription before the first cycle fires.
- **Neutral:** `OrchestratorService` deletion (Task 16) is a runtime no-op — nothing imports it. The scratch file (`scratch/search_orchestrator_service.py`) is left for Task 16's deletion manifest to reap.

## Alternatives Considered

### (a) Merge `scripts/unified_orchestrator.py` into the canonical path

**Rejected (G1).** `UnifiedOrchestrator` owns its own `EnhancedEventBus(persistence_path="data/events.jsonl")` (@ L69) and is invoked from CLI argv, not from the FastAPI lifespan. Unifying it into `RadionicsOperator` would couple CLI argument parsing to the runtime daemon and force two different bus configurations through one class.

### (b) Keep `OrchestratorService` as a "future" celestial-timing orchestrator

**Rejected.** The file has no DI registration, no lifespan hook, no caller, and no `stop()`. Its `_tick()` 60-second planetary-hour loop (`orchestrator_service.py:35-58`) is conceptually adjacent to `RadionicsOperator.start_autonomous_mode()`, which already checks astrological transits at `radionics_operator.py:1324-1326`. Reviving it would re-introduce exactly the duplicate-daemon problem this ADR closes.

### (c) Unify `BlessingScheduler` into `RadionicsOperator`

**Rejected (G4).** Different schedule semantics (rotating blessing slideshow vs. continuous radionics monitoring), different task-tracking state, independent `asyncio.Task` instances. Merging them couples two unrelated shutdown paths. See *BlessingScheduler Exemption* above.
