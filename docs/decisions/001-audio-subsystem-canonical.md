# ADR 001: Audio Subsystem Canonical Selection

- **Status:** Accepted (2026-06-18)
- **Deciders:** Wave 2 remediation
- **References:** `.omo/evidence/wave0-task5-audio-matrix.md` (Wave 0 Task 5), evaluation Issue 3.4
- **Gates:** Blocks Wave 3 Task 16 (delete duplicates), Wave 4 Task 26 (audio consolidation)
- **Amendments:**
  - 2026-06-18 (Wave 4 Task 26): scope of `modules/audio.py:AudioService` clarified in
    its class docstring (LLM-tool integration only; user-facing path is
    `vajra_service.py`). New finding recorded in §"Open issue (Task 26)" —
    `RadionicsOperator.generate_audio` tool passes a `mode=` kwarg that
    `AudioService.generate_tone` does not currently accept.

## Context

A preflight enumeration (Wave 0 Task 5) discovered **four** classes named `AudioService` / audio subsystems in the codebase. Only one of them actually serves the live `/api/v1/audio/*` HTTP surface; the others are orphans or serve a different concern. Without a recorded decision, future maintenance (and Wave 3 Task 16 / Wave 4 Task 26) risks deleting the live path or conflating two distinct concerns.

The four candidates:

| # | File | Class / instance | Live? |
|---|------|------------------|-------|
| 1 | `backend/core/services/vajra_service.py` | `VajraStreamService` → module singleton `vajra_service` (@ L774) | ✅ **Canonical** |
| 2 | `modules/audio.py` | `AudioService` (instance via project-root `container.py` @ L122–129) | ✅ Live, **different concern** (LLM tool path) |
| 3 | `backend/core/services/audio_service.py` | `AudioService` orphan singleton (@ L186) | ❌ Orphan — only 2 stale test refs |
| 4 | `backend/core/services/audio_service_fixed.py` | `AudioService` orphan singleton (@ L138) | ❌ Orphan chain with `endpoints/audio_fixed.py` (unmounted) |

### Request chain (frontend → engine)

```
frontend/src/stores/audioStore.js:38    ──POST /api/v1/audio/generate──┐
frontend/src/stores/audioStore.js:98    ──POST /api/v1/audio/play──────┤
frontend/src/stores/audioStore.js:137   ──POST /api/v1/audio/stop──────┤
frontend/src/components/UI/ChakraHealing.jsx:88,95,110                  │
                                                                        ▼
  backend/app/main.py:263   app.include_router(api_router, prefix="/api/v1")
  backend/app/main.py:28    from backend.app.api.v1.api import api_router
  backend/app/api/v1/api.py:6    import audio as audio_endpoint
  backend/app/api/v1/api.py:34   include_router(audio_endpoint.router, prefix="/audio")
  backend/app/api/v1/endpoints/audio.py:43-44
      from backend.core.services.vajra_service import AudioConfig as ServiceAudioConfig
      from backend.core.services.vajra_service import vajra_service
  backend/core/services/vajra_service.py:76    class VajraStreamService:
  backend/core/services/vajra_service.py:774   vajra_service = VajraStreamService()   ← singleton
        │ internally wraps core/audio_generator.ScalarWaveGenerator
        │             + core/enhanced_audio_generator (EnhancedAudioGenerator, PrayerBowlGenerator)
        ▼
  Audio emitted.
```

**Supporting liveness:** the same `vajra_service` singleton is also imported by 3 websocket managers (`connection_manager.py:138`, `connection_manager_stable.py:220`, `connection_manager_stable_v2.py:218`) and 4 sibling endpoints (`llm.py:302`, `astrology.py:67,112,...`, `divination.py:92,147`, `sessions`) — i.e. `VajraStreamService` is a generalist "Vajra.Stream service wrapper", not a pure audio class. Audio is its surface area; the `core/*_audio_generator.py` modules are the engines.

`endpoints/audio_fixed.py` is **not** imported by `api.py` (L1–64) and **not** in `endpoints/__init__.py:9-38` — its router is never mounted, so the `audio_service_fixed.py` singleton it imports is unreachable from HTTP.

## Decision

1. **Canonical user-facing audio subsystem** = `backend/core/services/vajra_service.py:VajraStreamService` (module-level singleton `vajra_service` @ L774). All `/api/v1/audio/*` routes and all websocket audio paths resolve to this single instance.

2. **Delete the 3 dead duplicates** in Wave 3 Task 16, plus their 2 stale tests:
   - `backend/core/services/audio_service.py` (orphan; only test refs)
   - `backend/core/services/audio_service_fixed.py` (orphan; only its sibling endpoint imports it)
   - `backend/app/api/v1/endpoints/audio_fixed.py` (router declared, never mounted)
   - *(collateral)* `tests/unit/test_backend_audio_playback.py:22` (only imports `audio_service.py`)
   - *(collateral)* `tests/unit/test_audio_fix.py:21` (only imports `audio_service.py`)

3. **KEEP** `modules/audio.py:AudioService` as a **separate concern**. It is wired through the project-root DI container (`container.py:122-129`, lazy `@property` provider returning `AudioService(event_bus=self.event_bus)`) and consumed by the RadionicsOperator LLM tool path (`modules/radionics_operator.py:511` → `svc = self._container.audio`). Its constructor signature differs (`event_bus` param) and its internal delegates (`core/audio_generator.AudioGenerator`, `core/enhanced_audio_generator.EnhancedAudioGenerator`, `core/tts_engine.TTSEngine`) serve agent/LLM tool calls — not HTTP audio. The two subsystems must not be conflated.

> Note: the DI container lives at **project root** `container.py`, not `backend/app/container.py` (the latter does not exist).

## Consequences

- **Positive:** A single, unambiguous audio path for the HTTP/WS surface. Any future audio bug, feature, or test has exactly one service to touch (`vajra_service`), one endpoint to mount (`endpoints/audio.py`), and one router prefix (`/audio`).
- **Positive:** The LLM tool path (`container.audio` → `modules/audio.py`) stays isolated and independently testable; agent audio tools are not coupled to HTTP lifecycle.
- **Negative:** `VajraStreamService` remains a broad wrapper (3 websockets + 4 non-audio endpoints also import it). This ADR does **not** extract a dedicated `AudioService` from it — that is Wave 4 Task 26's concern, and is optional. Until then, audio responsibilities live as methods on the generalist service.
- **Neutral:** Wave 3 Task 16 gains a precise deletion manifest (3 files + 2 tests) with no archaeological guesswork.
- **Risk:** If a future contributor names a new class `AudioService` without reading this record, confusion may recur. Mitigated by this ADR + Task 26's consolidation (if pursued).

## Alternatives Considered

### (a) Make `modules/audio.py:AudioService` canonical and rewire endpoints to it

**Rejected.** Would force every frontend fetch (`audioStore.js:38,98,137`, `ChakraHealing.jsx:88,95,110`) and all 3 websocket managers through `container.audio`, which has a different constructor (`event_bus`), different delegates, and no `AudioConfig` surface. Rewiring `endpoints/audio.py:43-44` away from `vajra_service` breaks the live path and merges two concerns the LLM-tool design intentionally kept separate.

### (b) Merge all four subsystems into one `AudioService`

**Rejected.** The four are not duplicates — `modules/audio.py` is an LLM-tool container citizen with a distinct lifecycle and event bus dependency; `audio_service.py` / `audio_service_fixed.py` are dead code, not competing implementations. Merging would either delete dead code (already Task 16) or couple HTTP audio to the LLM event bus (a regression of (a)).

### (c) Keep all four; document instead of deleting

**Rejected.** Two of the four are fully unreachable from HTTP and referenced only by stale tests. Keeping them invites accidental imports and future "which AudioService?" confusion — exactly the problem this ADR exists to end.

## Open issue (Task 26 — observed but out of scope)

While locking the `container.audio` LLM-tool pathway in Wave 4 Task 26, an interface mismatch was observed between the LLM tool schema / dispatcher and `modules/audio.py:AudioService`:

- `core/radionics_tools.py:484-506` declares the `generate_audio` tool with three parameters: `frequency_hz`, `duration_seconds`, and `mode` (enum: `prayer_bowl | sine`).
- `modules/radionics_operator.py:510-519` dispatches it as `svc.generate_tone(frequency=..., duration=..., mode=mode)`.
- `modules/audio.py:AudioService.generate_tone(self, frequency=432.0, duration=10.0, volume=0.5)` does **not** declare a `mode` parameter. A live tool call would raise `TypeError`.

This is pre-existing behaviour and **not** in scope for Task 26 (the task explicitly forbids modifying `AudioService` logic). The new lock test (`tests/unit/test_container_audio_llm_tools.py`) asserts the **documented** working interface (`frequency=`, `duration=`); the `mode` plumbing — either adding `mode` to `AudioService.generate_tone` (with prayer_bowl/sine selection logic) or stripping it from the dispatcher / tool schema — is deferred to a future audio-focused task. Recorded here so the next maintainer of either side knows the contract is currently violated on the `mode` axis.

The two-subsystem split itself (§Decision 1 vs §Decision 3) remains correct; the mismatch is intra-subsystem (dispatcher ↔ service) and does not change the canonical-path decision.
