# Sittings Constellation & World Emanation — Design

- **Date:** 2026-08-16
- **Status:** Approved direction, spec pending user review
- **Build order (user-selected):** Sittings Constellation first, then World Emanation (Command Center mount), then World Emanation (Operations mount)
- **Roadmap (later, separate specs):** literal night-sky chart; auspicious-timing wheel

## Context

The sitting loop is now closed and honest: one sitting → one folio, duplicates collapsed and stamped `duplicate_of` (commit `d72f2a8`), all tools in-process, apiUrl sweep complete. What the instrument still lacks is *sight* — nothing shows a sitting going out into the world, and the Workings ledger is a flat list with no sense of practice over time. This spec adds two visualizations that ride entirely on existing data and events:

1. **Sittings Constellation** — the practice history as a night sky.
2. **World Emanation** — a broadcast, seen from orbit, at the moment it seals.

## Product frame (applies to both features)

- The instrument is: one sitting → rates → one folio → optional Outlook / voice / image / broadcast.
- Visualizations are **representations of real records and real events**, never claims that a counter is a working.
- Simulated/derived values stay visually and verbally labeled as what they are.
- No idle-game "ops per second" swarm. A star is a sealed folio; an arc is a broadcast that actually started. Nothing accumulates a score.

---

## Feature A — Sittings Constellation (build first)

### What it is

A 2D-canvas night sky mounted as the hero of the Workings page (above the existing ledger list — the list stays as the honest inventory). Each sealed working is a star; sibling workings (same sitting, pre-idempotency retries) are linked as a constellation; collapsed duplicates appear as faint ghost stars tethered to their keeper.

### Data source

`GET /operator/workings?limit=50&include_hidden=true` — a dedicated fetch owned by the constellation component, decoupled from the page's "Show hidden" toggle so the sky always renders the full truth while the list keeps its current filter behavior.

**Backend change (one, additive):** `core/working.py:list_workings()` summaries additionally return four fields already present on the folio JSON:

```python
"planetary_hour": (data.get("hour_stamp") or {}).get("planetary_hour"),
"moon_phase": (data.get("hour_stamp") or {}).get("moon_phase"),
"saka_dawa_multiplier": saka.get("multiplier", 1),
"duplicate_of": data.get("duplicate_of"),
```

No schema change, no new endpoint, no new router. `frontend/src/routes/Workings/index.tsx:WorkingSummary` gains the same four optional fields.

### Star mapping (pure function, unit-tested)

`summaryToStar(summary, index, all)` → `{ x, y, size, hue, alpha, ghost }`

- **x (time):** `sealed_at` normalized across the fetched set, oldest → left, newest → right. Single-sitting edge case: center.
- **y (moon band):** the folio's own `moon_phase` string matched (case-insensitive `includes`) against the canonical 8 phases — `new, waxing crescent, first quarter, waxing gibbous, full, waning gibbous, last quarter, waning crescent` — mapping to one of 8 horizontal bands. Unknown or missing stamp → a neutral mid band. Categorical, derived from the record — no invented astronomy.
- **size/brightness:** `saka_dawa_multiplier` — ordinary nights are small stars; Duchen-scale merit (×100,000) is the brightest star in the sky.
- **hue:** `source` (command-center / ritual-composer / operator / unknown) → fixed palette assignment.
- **ghost:** `hidden === true` renders at 25% alpha.

### Constellation lines

- Group key = the same identity `collapse_duplicate_workings` uses: normalized intention + target + rate signature.
- Members of a group are joined left→right (chronological) by a thin line at low alpha.
- Ghost stars additionally tether to their `duplicate_of` keeper with a fainter dotted line.

### Times ribbon

A thin vertical strip along the left edge of the canvas showing the 8 moon-phase glyphs in band order, each aligned with its band — the legend for the y-axis. No live astronomy.

### Interaction

- **Hover:** tooltip — intention, dials joined `·`, relative seal time, multiplier if > 1.
- **Click:** calls the page's existing `setOpenId(working_id)` so the folio opens in the existing right-panel `WorkingFolioCard`. No new detail surface.
- Ghost stars are clickable too (they load like any hidden folio).

### Rendering

Plain `<canvas>` 2D (devicePixelRatio-aware), ~280px tall, full width, inside the existing amber Workings styling (`border-amber-500/20 bg-amber-950/20`). Twinkle = per-star sinusoidal alpha phase from a stable seed (star index), not RNG per frame. Redraw on prop change + rAF loop only while mounted.

### Files

- Create: `frontend/src/components/Workings/SittingsConstellation.tsx` (canvas component) and `frontend/src/components/Workings/star.ts` (pure mapping helpers, unit-tested without a canvas)
- Modify: `frontend/src/routes/Workings/index.tsx` (mount hero, extend `WorkingSummary`)
- Modify: `core/working.py` (`list_workings` additive fields)
- Test: `tests/core/test_working.py` (summary fields), `frontend/src/__tests__/components/star.test.ts` (pure mapping), `frontend/src/__tests__/components/SittingsConstellation.test.tsx` (render + empty state), `frontend/src/__tests__/components/Workings.sky.test.tsx` (page mount + hidden-inclusive fetch)

---

## Feature B — World Emanation

### What it is

When a sitting seals and its broadcast starts, the world *answers visually*: ripple rings emanate from the practitioner's coordinates and cyan arcs fly to resolvable targets — in the Command Center (compact) and on Operations (full-size hero).

### Event source (no backend changes)

`HEALING_BROADCAST_STARTED` is already emitted by `modules/radionics.py:123` on every `broadcast_healing`, already in the locked WS contract (`ws-contract.test.ts:84`), and already reaches `useWebSocketStable.ts:392` — where it currently only raises a toast. Payload: `{target, frequency_hz, frequencies, duration_minutes, audio_muted}`.

### Store

`frontend/src/stores/broadcastStore.ts` (Zustand, matching existing store conventions):

- `recentBroadcasts: BroadcastEvent[]` — push on event, each stamped `receivedAt` and `expiresAt = receivedAt + duration_minutes*60_000`.
- Prune on read and on a 30s interval; cap 20 entries.
- `useWebSocketStable` case body extended (after the existing toast) with `useBroadcastStore.getState().push(evt)`. No contract change — same message type, same case.

### Component

`frontend/src/components/3D/WorldEmanation.tsx` — the reusable scene core extracted from `RadionicsGlobe.tsx` internals (globe mesh + procedural texture, `latLonToVec3`, markers, `QuadraticBezierCurve3` arcs, `BlessingRays`, `resolveCoords` + country table). Props: `recentBroadcasts`, `variant: 'compact' | 'full'`, `practitionerCoords`.

- `RadionicsGlobe.tsx` keeps both existing exports (default + `MiniGlobe`) and delegates its scene to the shared core — `no-orphan-components` stays green and BroadcastPanel is untouched.
- The practitioner origin: browser geolocation if already granted, else `DEFAULT_LAT/LNG` (37.7749, −122.4194 — canonical, matches `geo.ts`/`config/settings.py`).

### Visual behavior (honesty rules)

- **Ripple rings** from the practitioner origin, paced across the broadcast duration — the emanation itself.
- **Arcs** only to *resolvable* targets: target/population text matched via the existing country table, plus earthly realm coordinates when realms are involved. One arc per resolvable target, cyan, ~4s flight, repeating softly while the broadcast is live.
- **"All beings" / unresolvable targets:** no fake pin — the global ripple brightens and slows instead.
- **Need-glows:** amber pulses at world-context sites the globe already fetches (2-min poll), visually and spatially distinct from cyan blessing arcs. Label: "where the need is".
- **Automation glow (full variant only):** 30s poll of scheduler status lights the current population's resolvable location + name; unresolvable populations join the global ripple.

### Mounts

1. **Command Center** — compact (~240px) in the right column above `SystemMonitorsCard`; the payoff beside the chat where the sitting sealed.
2. **Operations** — full-size hero; finally homes the currently-orphaned full globe.

### Files

- Create: `frontend/src/stores/broadcastStore.ts`, `frontend/src/components/3D/WorldEmanation.tsx`
- Modify: `frontend/src/hooks/useWebSocketStable.ts` (extend existing case), `frontend/src/components/UI/CommandCenter.tsx` (compact mount), `frontend/src/routes/Operations/index.tsx` (full mount), `frontend/src/components/3D/RadionicsGlobe.tsx` (delegate to shared core)
- Test: `broadcastStore` TTL/cap test, resolver pure-function test (matched / unmatched / realm coords), render tests for both variants, `ws-contract` + `no-orphan-components` suites stay green

---

## Error handling

- All fetches best-effort with silent degrade (existing pattern): constellation with no data renders an empty sky + "No sittings yet" caption; emanation with no broadcasts renders the calm globe.
- Geolocation is only *read* if permission was already granted — never prompted from these components.
- Store pruning never throws into the WS handler.

## Testing summary

- **Backend:** `pytest tests/core/test_working.py` — summary carries the four new fields; existing tests untouched.
- **Frontend:** `npx vitest run` — new unit/render tests + the three regression locks (`no-orphan-components`, `ws-contract`, `no-raw-api-fetch`).
- **Live gate (per feature):** constellation — seal one sitting, see its star appear and its siblings link; emanation — seal + broadcast one working, see ripple + arc in Command Center at seal time.

## Non-goals

- No WS contract additions or removals.
- No backend changes beyond the four additive summary fields.
- No new audio paths (ADR 001 untouched); no new `AudioService`.
- No literal-astronomy rendering in these two features (roadmap item, separate spec).
- No counters, scores, or "purification points" anywhere.

## Roadmap (explicitly out of this build)

1. **Night-sky chart** — real constellations + planets overhead, rotating with real time.
2. **Auspicious-timing wheel** — 24h planetary-hour mandala, moon ring, Saka Dawa windows: when to sit next.
