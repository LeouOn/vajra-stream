# Interactive Radionics UI — Design Specification

**Date:** 2026-05-21
**Project:** Vajra.Stream Frontend-Backend Integration

---

## 1. Concept & Vision

The UI should feel like a **live instrument panel** — every control has visual feedback, every broadcast has moving data. Not a static dashboard but a responsive radionics workstation where the sine waves animate, the rate dials glow, and the chakra alignment pulses with the broadcast. Server-side audio and scalar data stream in at 10Hz and the frontend renders them at 60fps with client-side interpolation.

---

## 2. Design Language

**Aesthetic:** Dark mystical glassmorphism — deep purple/cyan/gold on near-black backgrounds. Glowing borders, frosted glass panels, subtle pulse animations on active elements.

**Colors:**
- Background: `#0f0f23` (near black with purple tint)
- Primary accent: `#22d3ee` (vajra-cyan, glowing cyan)
- Secondary accent: `#a855f7` (vajra-purple)
- Active/live: `#22c55e` (green glow for running state)
- Warning: `#eab308` (yellow)
- Chakra colors: Root `#ff4444`, Sacral `#ff8c00`, Solar `#ffdd00`, Heart `#00ff88`, Throat `#00ccff`, ThirdEye `#9966ff`, Crown `#cc66ff`

**Motion:**
- Audio-reactive elements pulse at 60fps via `requestAnimationFrame`
- Chakra circles pulse with `scale(1.0 → 1.08)` at ~0.5Hz when active
- Rate bars slide smoothly (CSS transitions, 200ms ease-out)
- Waveform scrolls continuously left at speed proportional to frequency

**Typography:** Existing system — `font-mono` for frequency readouts, `font-sans` for labels

---

## 3. Layout & Structure

### 3.1 VisualizationSelector Additions (5 new options)

Add these to the existing `visualizations` array in `VisualizationSelector.jsx`:

| ID | Name | Description |
|---|---|---|
| `live-wave` | Live Wave | Animated sine/scalar wave canvas, audio-reactive |
| `scalar-wave` | Scalar Wave | PRNG-driven noise wave visualization |
| `radionics-panel` | Radionics Panel | Full radionics broadcast control panel (center view) |
| `trends` | Trends | History charts (session duration bar, rate line) |
| `chakra-trend` | Chakra Trends | Live chakra alignment + frequency trending |

### 3.2 Center Canvas Switcher (in App.jsx)

The main canvas (`<Canvas>` from react-three-fiber) currently shows one of 4 Three.js visualizations based on `visualizationType`. After the change, `visualizationType` also includes the new Canvas-based visualizers (live-wave, scalar-wave) which render via a plain HTML `<canvas>` element layered where the 3D Canvas normally sits.

When `visualizationType` is one of the new visualizers:
- Three.js canvas gets `display: none`
- Canvas element shown in same position
- VisualizationSelector stays visible so user can switch back

### 3.3 RadionicsBroadcastPanel (Sidebar)

A collapsible panel in the sidebar that shows when a session is running. Lives in the "Radionics & Healing" section of the sidebar, replacing the current ChakraHealing section or alongside it.

Contains:
- 3 rate bars (R1/R2/R3) — animated fill bars showing rate values
- Intention display — glowing text with the session intention
- Progress bar — elapsed/remaining time
- 5 frequency indicator circles (Schumann, OM, Love, Connection, Awakening) — lit up when active
- Start / Pause / Stop buttons
- Real-time WebSocket message handling for `session_update`, `CRYSTAL_BROADCAST_STARTED`, `RADIONICS_RATE_BROADCAST`

### 3.4 ChakraAlignmentStrip

A fixed-height strip (48px) at the bottom of the main content area (above footer), always visible. Shows 7 chakra circles with:
- Color fill intensity based on current session config
- Frequency value below each circle
- Pulse animation when the chakra is being broadcast to

---

## 4. Features & Interactions

### 4.1 LiveWaveVisualizer

**Rendering:** HTML `<canvas>` element, 60fps `requestAnimationFrame` loop
**Data input:**
- `audioSpectrum` array (100 floats, 0-1 normalized) from WebSocket `realtime_data` at 10Hz
- `frequency` from `useAudioStore` for the sine wave base frequency

**Visuals:**
- Scrolling sine wave — amplitude from audioSpectrum bars, color: cyan
- Overlay: frequency readout in top-left corner
- Wave type toggle button (Sine / Sawtooth / Scalar / Combined) — small pill in corner
- When `isPlaying` from audioStore is true, wave animates; when false, wave is static

### 4.2 ScalarWaveVisualizer

**Rendering:** Same canvas, same 60fps loop
**Data input:** `scalarStatus.rate` and PRNG seed from `scalarStatus`
**Visuals:**
- Noise-like waveform generated client-side using a seeded PRNG
- Color: purple/cyan gradient
- Updates whenever `scalarStatus` changes (e.g., new rate attunement)

### 4.3 RadionicsBroadcastPanel

**State:** Managed locally in the component. Reads from `useWebSocket()` for `sessions`, `scalarStatus`, `crystalStatus`.

**Behavior:**
- Shows only when `runningSessionCount > 0` (via `useWebSocket().sessions`)
- Animates rate bars to match the attuned rate from `scalarStatus.rate` (or defaults to [50, 50, 50])
- Shows intention from the active session
- Progress bar updates every 100ms based on session start time + duration
- `CRYSTAL_BROADCAST_STARTED` WebSocket message triggers a glow pulse animation on the panel border
- Pause/Resume calls `stopSession` / `startSession` on the session

### 4.4 TrendsDashboard

**Chart library:** `recharts` (already has `chart.js` peer dep in package.json)

**Charts (all in Dashboard view as new cards):**
- **Session Duration Bar Chart** — last 10 sessions, x=session name, y=duration in minutes
- **Rate History Line Chart** — last 20 rate attunements, x=time, y=rate value, colored by category
- **Frequency Usage Heatmap** — 7 chakra columns × sessions rows, cell color intensity = frequency usage

**Data sources:**
- Session history: `GET /api/v1/sessions/history`
- Rate history: stored in `rateStore.rateHistory` (persisted)
- Frequency data: from `scalarStatus` or `GET /api/v1/radionics/rates/search`

**Interaction:** Hover shows tooltip with exact values. Click on a session bar navigates to session detail (future).

### 4.5 ChakraAlignmentStrip

**Always rendered** — sits in `App.jsx` between `<main>` and `<footer>`. Hidden when `currentView === dashboard`.

**Data:** Reads `sessions` from `useWebSocket()`. For active session, reads `config` to know which frequencies/chakras are enabled.

**Visuals:** 7 circles in a row, chakra colors, with frequency label below. Pulse animation on the active chakra(s).

---

## 5. Component Inventory

### New Components

| Component | File | Description |
|---|---|---|
| `RadionicsBroadcastPanel` | `frontend/src/components/UI/RadionicsBroadcastPanel.jsx` | Sidebar radionics broadcast control panel |
| `LiveWaveVisualizer` | `frontend/src/components/2D/LiveWaveVisualizer.jsx` | Canvas sine wave + audio-reactive visualization |
| `ScalarWaveVisualizer` | `frontend/src/components/2D/ScalarWaveVisualizer.jsx` | Canvas PRNG scalar wave visualization |
| `TrendsChart` | `frontend/src/components/UI/TrendsChart.jsx` | Recharts-based history charts for Dashboard |
| `ChakraAlignmentStrip` | `frontend/src/components/UI/ChakraAlignmentStrip.jsx` | Bottom-of-screen chakra status strip |

### Modified Components

| Component | File | Changes |
|---|---|---|
| `VisualizationSelector` | `frontend/src/components/UI/VisualizationSelector.jsx` | Add 5 new visualization options |
| `App.jsx` | `frontend/src/App.jsx` | Render ChakraAlignmentStrip, conditionally show Canvas vs canvas visualizers, add RadionicsBroadcastPanel to sidebar |
| `Dashboard` | `frontend/src/components/UI/Dashboard.jsx` | Add TrendsChart cards |
| `SidebarSection` | `frontend/src/components/UI/SidebarSection.jsx` | Add RadionicsBroadcastPanel section |

---

## 6. Technical Approach

### Frontend Architecture

- **State:** All real-time data comes through `useWebSocket()` hook → Zustand stores
- **Animation loop:** Each canvas visualizer manages its own `requestAnimationFrame` loop, started in `useEffect` when mounted
- **Charting:** `recharts` library (already in package.json as dependency of `react-chartjs-2`)
- **Styling:** Tailwind CSS classes (existing patterns) + inline styles for canvas

### WebSocket Message Handling

The frontend already handles these message types in `useWebSocket.js`:
- `realtime_data` → `audioSpectrum`, `sessions`
- `session_update` → already handled (just updates state)
- `CRYSTAL_BROADCAST_STARTED` → needs a handler that RadionicsBroadcastPanel can subscribe to

For RadionicsBroadcastPanel to get notified of broadcasts: it reads from the WebSocket hook's state (`sessions`, `scalarStatus`, `crystalStatus`). No new message types needed.

### API Endpoints Used

| Endpoint | Method | Used By |
|---|---|---|
| `/api/v1/sessions/history` | GET | TrendsChart |
| `/api/v1/sessions/{id}/status` | GET | RadionicsBroadcastPanel (for progress) |
| `/api/v1/radionics/rates/search` | GET | TrendsChart (rate history) |

### File Structure

```
frontend/src/
  components/
    2D/
      AudioSpectrum.jsx        (existing)
      LiveWaveVisualizer.jsx   (NEW)
      ScalarWaveVisualizer.jsx (NEW)
    UI/
      RadionicsBroadcastPanel.jsx (NEW)
      TrendsChart.jsx            (NEW)
      ChakraAlignmentStrip.jsx   (NEW)
      Dashboard.jsx              (modified)
      VisualizationSelector.jsx (modified)
      SidebarSection.jsx         (modified)
  hooks/
    useWebSocket.js           (modify: add crystalStatus/scalarStatus to handler)
  App.jsx                     (modified)
```

---

## 7. Implementation Order

1. **ChakraAlignmentStrip** — simplest, always visible, no data fetching
2. **LiveWaveVisualizer + ScalarWaveVisualizer** — canvas components, add to selector
3. **RadionicsBroadcastPanel** — sidebar panel with WebSocket state + progress
4. **TrendsChart + Dashboard integration** — charts with history data
5. **VisualizationSelector updates** — wire all new options
6. **App.jsx wiring** — conditional rendering between 3D canvas and new visualizers

---

## 8. Open Questions

1. **Scalar wave data source:** The backend doesn't currently stream scalar wave data per-session. `scalarStatus` in `useWebSocket.js` comes from the WebSocket `realtime_data` which has a static fallback. We may need to wire `scalarStatus` to real session data from vajra_service — this is a backend task.
2. **Trends data persistence:** Rate history is in `rateStore` (localStorage). Session history requires a backend endpoint that now works (verified in integration work). Charts can use both.
3. **Canvas performance:** 60fps canvas on top of Three.js may cause performance issues on lower-end hardware. The 3D canvas should `pauseRaycast()` and stop rendering when hidden (Three.js already does this when `display: none`).