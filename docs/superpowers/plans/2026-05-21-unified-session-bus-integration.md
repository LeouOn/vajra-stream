# Unified Session Bus Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the frontend and backend together so that sessions actually work end-to-end — create session, start session runs audio + crystal broadcast, WebSocket streams live data back to frontend.

**Architecture:** Single session store in VajraService. Session lifecycle events published to EnhancedEventBus. OrchestratorBridge subscribes to events and triggers crystal/radionics side effects as background tasks. WebSocket streams from VajraService.

**Tech Stack:** FastAPI, EnhancedEventBus, sounddevice, React, Zustand, WebSocket

---

## File Map

### Existing Files Being Modified
- `infrastructure/event_bus.py` — add session event types
- `modules/interfaces.py` — add session event dataclasses
- `backend/core/services/vajra_service.py` — become single session store, publish lifecycle events
- `backend/core/orchestrator_bridge.py` — subscribe to session events, trigger crystal/radionics
- `backend/app/api/v1/endpoints/sessions.py` — use VajraService directly, wire background tasks
- `backend/websocket/connection_manager_stable_v2.py` — emit frontend-compatible message types

### Existing Files Being Fixed
- `frontend/src/stores/commandStore.js` — syntax error fix
- `frontend/src/hooks/useWebSocketStable.js` — wrong port 8007 → 8008

### New Files Created
- `backend/core/services/session_events.py` — session event type definitions (optional, can inline in interfaces)

---

## Task 1: Add Session Event Types to Event Bus

**Files:**
- Modify: `infrastructure/event_bus.py:19-25`
- Modify: `modules/interfaces.py:15-48`

- [ ] **Step 1: Add session event types to interfaces.py**

Add three new event dataclasses after `BlessingGenerated` (line 48):

```python
@dataclass
class SessionCreated(DomainEvent):
    """Event: A blessing session has been created"""
    session_id: str
    name: str
    intention: str
    duration: int
    audio_frequency: float


@dataclass
class SessionStarted(DomainEvent):
    """Event: A session has started broadcasting"""
    session_id: str
    name: str


@dataclass
class SessionStopped(DomainEvent):
    """Event: A session has been stopped"""
    session_id: str
    name: str
    runtime_seconds: float


@dataclass
class BroadcastStarted(DomainEvent):
    """Event: Crystal/radionics broadcast has started"""
    session_id: str
    hardware_level: int
    frequencies: list[float]


@dataclass
class BroadcastStopped(DomainEvent):
    """Event: Crystal/radionics broadcast has stopped"""
    session_id: str
    actual_runtime: float
```

- [ ] **Step 2: Verify interfaces.py parses without error**

Run: `python -c "from modules.interfaces import SessionCreated, SessionStarted, SessionStopped, BroadcastStarted, BroadcastStopped; print('OK')"`

---

## Task 2: Make VajraService the Single Session Store

**Files:**
- Modify: `backend/core/services/vajra_service.py:281-347`
- Modify: `backend/app/api/v1/endpoints/sessions.py:28-79`

- [ ] **Step 1: Update vajra_service.create_session to accept extended config**

Replace the `create_session` method (lines 281-303) to accept name, intention, audio_frequency, and wire in crystal service. The method should also import and use the event bus if available.

The new `create_session` signature:
```python
async def create_session(
    self,
    name: str,
    intention: str,
    audio_frequency: float = 136.1,
    duration: int = 3600,
    astrology_enabled: bool = True,
    hardware_enabled: bool = True,
    visuals_enabled: bool = True,
) -> str:
```

The method should:
1. Create session_id
2. Build `AudioConfig` from parameters
3. Build a `SessionConfig` dataclass
4. Store in `self.active_sessions`
5. Publish `SessionCreated` event to event bus if available
6. Return session_id

- [ ] **Step 2: Update vajra_service.start_session to publish SessionStarted + BroadcastStarted**

The existing `start_session` (lines 305-330) already calls `generate_prayer_bowl_audio` and `broadcast_audio`. Add:
1. `SessionStarted` event published after status is set to "running"
2. For crystal broadcast: check if hardware_enabled, call crystal service in a background thread (since broadcast_audio already threads the playback)

- [ ] **Step 3: Update vajra_service.stop_session to publish SessionStopped**

Add `SessionStopped` event after setting status to "stopped", including runtime calculation.

- [ ] **Step 4: Update sessions.py create endpoint to use VajraService directly**

Replace `orchestrator_bridge.create_session()` call (line 54) with:
```python
from backend.core.services.vajra_service import vajra_service
session_id = await vajra_service.create_session(
    name=config.name,
    intention=config.intention,
    audio_frequency=config.audio_frequency,
    duration=config.duration,
    astrology_enabled=config.astrology_enabled,
    hardware_enabled=config.hardware_enabled,
    visuals_enabled=config.visuals_enabled,
)
```

- [ ] **Step 5: Update sessions.py start endpoint to use VajraService.start_session**

Replace the orchestrator status-set-only code (lines 92-96) with:
```python
from backend.core.services.vajra_service import vajra_service
success = await vajra_service.start_session(session_id)
```

- [ ] **Step 6: Update sessions.py stop endpoint similarly**

Replace with `vajra_service.stop_session(session_id)`.

- [ ] **Step 7: Run tests**

Run: `pytest tests/ -v --tb=short` (if no tests yet, skip to Step 8)
Expected: No new failures

- [ ] **Step 8: Commit**

```bash
git add backend/core/services/vajra_service.py backend/app/api/v1/endpoints/sessions.py modules/interfaces.py
git commit -m "feat: unify session store in VajraService, add session lifecycle events"
```

---

## Task 3: Wire Background Tasks for Crystal/Radionics

**Files:**
- Modify: `backend/core/orchestrator_bridge.py`
- Modify: `backend/app/api/v1/endpoints/sessions.py`

- [ ] **Step 1: Add crystal broadcast as a background task in orchestrator_bridge**

The orchestrator bridge should subscribe to `SessionStarted` events from the event bus. When one fires, it calls crystal service in a thread (non-blocking).

Add a new method `_on_session_started`:
```python
def _on_session_started(self, event):
    """Handle session started event - trigger crystal broadcast as background task"""
    try:
        import threading
        crystal = self.orchestrator.services.get("crystal")
        if crystal and event.session_id:
            def run_broadcast():
                try:
                    crystal.broadcast_intention(
                        intention=event.name,
                        duration=3600,
                        hardware_level=2,
                    )
                except Exception as e:
                    logger.error(f"Crystal broadcast error: {e}")
            threading.Thread(target=run_broadcast, daemon=True).start()
    except Exception as e:
        logger.error(f"Error handling SessionStarted: {e}")
```

- [ ] **Step 2: Register the SessionStarted handler in _register_event_forwarding**

In `_register_event_forwarding`, add:
```python
from modules.interfaces import SessionStarted
self.orchestrator.event_bus.subscribe(SessionStarted, self._on_session_started)
```

- [ ] **Step 3: Verify the bridge initializes without error**

Run: `python -c "from backend.core.orchestrator_bridge import orchestrator_bridge; orchestrator_bridge.initialize(); print('OK')"`
Expected: "OK" or similar success message

- [ ] **Step 4: Commit**

```bash
git add backend/core/orchestrator_bridge.py
git commit -m "feat: wire crystal broadcast to session lifecycle events"
```

---

## Task 4: Add Missing WebSocket Message Types

**Files:**
- Modify: `backend/websocket/connection_manager_stable_v2.py:245-253`
- Modify: `backend/core/orchestrator_bridge.py:47-69`

- [ ] **Step 1: Add session update broadcast in connection_manager_stable_v2.py**

The `send_safe_realtime_data` method broadcasts every 100ms. After broadcasting the `realtime_data` message (lines 245-253), add a check for newly started sessions and send `session_update` messages:

```python
# Check for active sessions and send updates
for session_id, session in sessions.items():
    if session.get("status") == "running":
        await self.broadcast({
            "type": "session_update",
            "data": {
                "id": session_id,
                "status": "running",
                "name": session.get("config", {}).name if hasattr(session.get("config", {}), "name") else str(session.get("config", {})),
            }
        })
```

- [ ] **Step 2: Change domain_event forwarding to use proper message type names**

In `_forward_event_to_websocket` (orchestrator_bridge.py lines 47-69), change the message type based on event class:

```python
event_data = {
    "type": event.__class__.__name__,  # e.g. "SessionStarted", "BroadcastStarted"
    "timestamp": event.timestamp.isoformat(),
    "data": {k: v for k, v in event.__dict__.items() if not k.startswith("_")},
}
```

This makes the frontend receive `SessionStarted` instead of `domain_event`, which the frontend already has handlers for (none currently, but they could be added).

- [ ] **Step 3: Add explicit broadcast in vajra_service.start_session for BroadcastStarted**

In `vajra_service.py`, after starting audio broadcast, add to `start_session`:
```python
# Notify via WebSocket that broadcast started
try:
    from backend.websocket.connection_manager_stable_v2 import stable_connection_manager_v2
    asyncio.create_task(stable_connection_manager_v2.broadcast({
        "type": "CRYSTAL_BROADCAST_STARTED",
        "session_id": session_id,
        "timestamp": time.time(),
    }))
except Exception:
    pass  # Non-critical
```

- [ ] **Step 4: Commit**

```bash
git add backend/websocket/connection_manager_stable_v2.py backend/core/orchestrator_bridge.py
git commit -m "feat: add frontend-compatible WebSocket message types for session events"
```

---

## Task 5: Wire Frontend Stores to Backend APIs

**Files:**
- Modify: `frontend/src/stores/commandStore.js` (syntax error fix)
- Modify: `frontend/src/stores/audioStore.js`
- Modify: `frontend/src/stores/crystalStore.js`
- Modify: `frontend/src/stores/rateStore.js`
- Create: (no new files)

- [ ] **Step 1: Fix syntax error in commandStore.js line 32**

Current (broken):
```javascript
{ id: tales.generate': label: 'Generate Teaching Tale', ...
```
Fix:
```javascript
{ id: 'tales.generate', label: 'Generate Teaching Tale', ...
```

- [ ] **Step 2: Fix hardcoded localhost:8008 in commandStore.js**

Lines 133 and 158 hardcode `http://localhost:8008`. Change to relative URLs:
```javascript
fetch('/api/v1/stories/search?q=...')  // line 133
fetch('/api/v1/radionics/rates/search?query=...')  // line 158
```

- [ ] **Step 3: Add stopAudio API call in audioStore.js**

In `audioStore.js`, the `stopAudio` action (around line 135) updates local state but doesn't call the backend. Add:
```javascript
stopAudio: () => {
  try {
    axios.get('/api/v1/audio/stop');
  } catch (e) {
    console.warn('Stop audio API not available');
  }
  set({ isPlaying: false, audioData: null });
},
```

- [ ] **Step 4: Wire crystalStore to backend API**

Add API calls to `crystalStore.js`. Read the file first to understand current structure.

Key actions to add:
- `fetchCrystalGrid()` → `GET /api/v1/radionics/crystal/grid` (or similar — check existing endpoints)
- `programCrystal(intention)` → `POST /api/v1/radionics/crystal/program`
- `broadcastCrystal(duration)` → `POST /api/v1/radionics/broadcast`

If those endpoints don't exist yet, use `POST /api/v1/radionics/broadcast` for now with appropriate params.

- [ ] **Step 5: Wire rateStore to backend API**

Add API calls to `rateStore.js`:
- `searchRates(query)` → `GET /api/v1/radionics/rates/search?query=...`
- `getCategories()` → `GET /api/v1/radionics/rates/categories`

- [ ] **Step 6: Verify frontend builds**

Run: `cd frontend && npm run build` (or `npm run dev` to check dev server starts)
Expected: No build errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/stores/commandStore.js frontend/src/stores/audioStore.js frontend/src/stores/crystalStore.js frontend/src/stores/rateStore.js
git commit -m "fix: wire frontend stores to backend APIs, fix syntax error"
```

---

## Task 6: Fix Stable WebSocket Hook Port

**Files:**
- Modify: `frontend/src/hooks/useWebSocketStable.js:38`

- [ ] **Step 1: Change port 8007 to 8008**

Line 38: `return \`${wsProtocol}//${frontendHost}:8007/ws\`` → `8008`

Or remove this file if it's not referenced anywhere. Check with:
Run: `grep -r "useWebSocketStable" frontend/src/`

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useWebSocketStable.js
git commit -m "fix: useWebSocketStable wrong port 8007 -> 8008"
```

---

## Self-Review Checklist

1. **Spec coverage:** Does each design section map to a task above?
   - Unified session store → Task 2
   - Event lifecycle → Task 1 + Task 2 + Task 3
   - Real audio + crystal on start → Task 2 + Task 3
   - Missing WebSocket types → Task 4
   - Frontend stores → Task 5
   - Fixes → Task 6

2. **Placeholder scan:** No "TBD", "TODO", or "fill in later" in any step above.

3. **Type consistency:**
   - `SessionCreated` event has `session_id`, `name`, `intention`, `duration`, `audio_frequency`
   - `SessionStarted` event has `session_id`, `name`
   - `SessionStopped` event has `session_id`, `name`, `runtime_seconds`
   - All methods in `vajra_service.py` use consistent `session_id` parameter name

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?