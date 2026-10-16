# Development Roadmap

_Last revised 2026-10-14. Supersedes the "Roadmap (later)" line of
[the 2026-08-16 design spec](superpowers/specs/2026-08-16-sittings-constellation-and-world-emanation-design.md),
whose two items (night-sky chart, auspicious-timing wheel) have shipped._

## Where we are

The core loop is closed and honest: **one sitting → rates → one folio →
optional Outlook / voice / image / broadcast.** Around it sits work no generic
meditation or sound app has:

- Real topocentric astronomy (Swiss Ephemeris alt/az), Vedic nakshatras,
  Chinese BaZi and the Tibetan calendar, with Saka Dawa multipliers
  stamped onto every working.
- Unabbreviated dharani texts: the 84-phrase Great Compassion, the
  5-assembly Shurangama, Sitatapatra, Mahapratisara, Cundi.
- Epoch-gated playback (a Stop is guaranteed to stop), an idempotent
  folio ledger, and visuals that ride on real records (Sittings
  Constellation, World Emanation, Celestial Sky Dome).
- An approval-gated LLM operator with about 100 in-process tools, and
  compassion arcs drawn from real crisis feeds.

Commit velocity has fallen steeply (June 271 → September 11). The next phase
should consolidate before it expands.

## Guiding principle: the honest instrument

The 08-16 spec already sets the rule: _"Visualizations are representations of
real records and real events, never claims that a counter is a working.
Simulated/derived values stay visually and verbally labeled as what they are."_

This principle is what makes Vajra.Stream distinctive. Many tools in this
space present fabricated "energy readings" as measurements. An instrument that
is always clear about where each number comes from is more trustworthy, and it
is truer to the README's own stance: _"The computer cannot generate compassion
or wisdom; only you can do that."_

Every value the UI displays should belong to exactly one of these kinds:

| Provenance | Meaning | Example |
|---|---|---|
| **record** | A persisted fact | a sealed folio, a broadcast that started |
| **computed** | Deterministic from real inputs | planet altitude, moon phase, nakshatra |
| **draw** | Random, used as a divinatory method | GV via the stick-pad analog, I Ching casts |
| **decorative** | Animation that carries no information | scalar-wave canvas, globe rays |

A **draw** is legitimate. The radionics engine says outright that RNG stands in
for the stick pad or pendulum. What a draw must never do is pose as a
measurement, with readouts like "Coherence 88%" or "Excellent — very high
vitality".

## Phase 1: Stabilize (now)

- [x] Prayer-bowl audio really uses the prayer-bowl synthesizer. Every request
      used to fall back to a plain sine, because of an `await` on a sync call
      plus wrong kwargs (`tests/unit/test_vajra_service_generate.py`).
- [x] Fixed Outlook → Universe and TTS Settings crashing at runtime on
      undefined names (`UniverseTab` and `message` were never imported).
- [x] Added a TypeScript error ratchet to CI (`npm run typecheck`, baseline
      277, down from 304). `vite build` never type-checked, which is how those
      crashes shipped.
- [x] "Aura Field Coherence %" (`Math.sin + Math.random`, pinned to about 88%
      while audio played) became "Field Presence", which is driven only by
      audio and session state.
- [x] Burn down the tsc baseline: 304 → 153 (2026-10-15). `AstrologyPanel.tsx`
      and `AstrologyExtractionPanel.tsx` are clean. The work also fixed four
      user-visible bugs: sweep results overriding the Replay selection, an
      "explicit dates" picker that only allowed two dates, moon illumination
      under 1% shown 100× too high, and "Invalid Date" on failure.
- [x] Second tsc pass: 153 → 23 (2026-10-15). It fixed more silent runtime
      bugs:
      - the LLM usage badge always read 0;
      - recitation showed "stopped" right after starting;
      - an Outlook video poll never stopped;
      - the Astrology mandala threw on every frame while audio played;
      - "Ask the astrologer" failed on planets without a house;
      - the Scalar tab's journey never rendered.
- [x] Finish the last 23: 23 → 0 (2026-10-15), with no casts or
      suppressions. `.tsc-baseline` is 0 and the gate is a hard zero
      (`--update` can no longer raise it). Bugs fixed along the way:
      - "Strip PII" on the astrology copy buttons was inverted. The live
        copy kept the observer's location while it said "PII stripped";
      - the Astrocartography globe imported a hook that no longer exists
        and threw away the positions it fetched;
      - the scalar visualizer read a "coherence" that the status never
        carries (it was always the fallback);
      - the sadhana caption read a nonexistent field.
- [ ] Recreate `.venv` on Python 3.13. Local venvs are 3.14, but
      `.python-version` pins 3.13 and 3.14 is documented as unsupported.

## Phase 2: Provenance everywhere

Make the honest-instrument rule structural, so it no longer depends on
individual reviews catching each case.

1. **Backend:** derived values carry a `provenance` field
   (`record | computed | draw | decorative`) in API and WebSocket payloads.
2. **Frontend:** a single `<Reading value provenance>` primitive renders the
   label consistently. A draw reads as "drawn" and is never shown as a meter.
3. **Known offenders to migrate** (verified 2026-10-14):
   - ~~MOPS~~ **Done (2026-10-15).** The MOPS engine added hard-coded
     constants (17.73M ops/s whenever scalar was active, 120/s per crystal),
     exactly the "ops per second" counter the spec rules out. It is deleted
     with its routes and every `mops` field; scalar-radionics broadcasts are
     recorded in the operations ledger, and the UI shows ledger facts.
   - ~~Rate jitter, GV verdicts, e-meter, potency %, carrier nudge~~
     **Done (2026-10-15).** The rate broadcast is computed with no jitter.
     GV, potency and attunement readings carry `provenance` and read as
     draws, both in the UI ("drawn") and in what the LLM is told: "Drawn GV
     812, in the stick-pad tradition this reads as…", never a diagnosis. The
     no-analysis fallback rate is flagged as a fallback, and the carrier
     nudge follows the hand.
4. ~~**Guard test**~~ **Done (2026-10-15).**
   `tests/unit/test_no_unlabeled_randomness.py` and
   `frontend/src/__tests__/no-unlabeled-math-random.test.ts` fail on any
   randomness outside a reviewed allow-list. Each entry is labeled draw,
   content, decorative, timing or id.
5. **Operations ledger** **Done (2026-10-15).** `core/operations.py`
   (schema v7), `/api/v1/operations`, live `operation_update` events, and
   the Operations → Ledger tab. A real operation has a start, a measured
   duration and a completion record.
6. **Local render** **Done, except the live run (2026-10-15).** The Qwen-Image
   2.1 adapter runs behind ComfyUI; see
   [the spec](specs/2026-10-14-operations-and-local-render.md). Built:
   reference images, folio witness renders that return immediately and fill
   in the folio when done, sigils through the engine, and the launcher
   configured via `COMFYUI_LAUNCHER`. **Verified live on 2026-10-15** on the
   AMD Radeon 8060S (ComfyUI 0.39.0, Qwen-Image 2.1 Turbo):
   - a cold 1024² render through the engine took 77.2 s;
   - a 2432×1280 render through `POST /render/jobs` took 159.8 s, with the
     seed recorded as chosen;
   - the backend was killed mid-render, and on restart it re-attached to
     the ComfyUI prompt and collected the result;
   - the PNG's sha256 matched the ledger, and the image route served it.
   - The run showed that the ledger's elapsed time includes downtime after
     a re-attach, so each result now also stores
     `backend_execution_seconds`.
7. **Follow-ups found along the way:**
   - ~~`/radionics/broadcast` blocks the event loop~~ **Done.** Broadcasts
     run in a capped worker pool, return immediately, and can be cancelled
     from the Ledger (`POST /operations/{id}/cancel`). Each broadcast and
     session registers its own stop; render registers one per kind. See
     [Cancel registries](specs/2026-10-14-operations-and-local-render.md#cancel-registries-as-built).
   - ~~Sessions and sigil broadcasts are missing from the ledger~~ **Done.**
   - ~~Summary polling duplicated~~ **Done.** One shared poller in
     `operationsStore`.
   - ~~Sigil UI ignores the local render~~ **Done (2026-10-15).** With
     `IMAGE_PROVIDER=comfyui`, `BroadcastPanel` follows the forge's
     `ai_image_render` operation through `operation_update` events. It
     shows the status, the elapsed time, the finished image, any error and
     a Cancel button.
   - ~~The `forge_witness` LLM tool uses only the hosted path~~ **Done.**
     The route and both tool registries share
     `core.working.forge_witness`. It renders locally when the engine is
     reachable, and the tools return the queued `operation_id`. Otherwise
     it falls back to hosted and reports `witness_fallback`.
   - ~~Autonomous journey advances emit no JOURNEY_* events~~ **Done.**
     `StableConnectionManagerV2.schedule_broadcast` sends from worker
     threads onto the recorded main loop.
   - ~~The hosted witness path blocks the event loop~~ **Done.** It runs
     in a worker thread. On the loop it had also failed every time:
     `generate_image` returns a coroutine when a loop is running. The sigil
     forge's synchronous providers now run in a thread as well.

## Phase 3: Consolidate

- Merge the two LLM tool registries (`backend/core/llm_agent/tools.py`,
  `core/radionics_tools.py`, about 100 tools in total) into one.
- Break the import cycles between `core` and `backend` and between `modules`
  and `backend`, and remove the 14 production `sys.path.insert`s.
- Finish ADR 002 step 3 (retire the `backend/app/config.py` shim).
- Continue splitting monoliths: `OutlookDashboard.tsx` (about 1,980 lines,
  55 `useState`) and `CommandCenter.tsx` (about 1,500 lines).
  **Done 2026-10-16:** `OutlookDashboard.tsx` went from 1,991 to 240 lines
  (9 hooks and 10 section components under `components/UI/outlook/`) and
  `CommandCenter.tsx` from 1,478 to 171 lines (6 hooks and 6 sections under
  `components/CommandCenter/`). No new file is over 400 lines. Behavior is
  pinned by characterization tests (`OutlookDashboard.flows.test.tsx`,
  `CommandCenter.flows.test.tsx`) written before the split. Still over 400
  lines: the earlier extractions `outlook/UniverseTab.tsx` (524) and
  `CommandCenter/RenderMessageWidgets.tsx` (679).

## Phase 4: Deepen the practice

Expand only after phases 1 through 3 are done, and keep the honest-instrument
rule throughout:

- **Practice over time:** streaks, accumulation counts and dedications grounded
  in the folio ledger (records only, with no scores).
- **Calendar-aware sittings:** suggest practices from the Tibetan calendar and
  auspicious-timing wheel that already exist (Saka Dawa, Duchen days, lunar
  phases).
- **Dedication of merit as a first-class step** that closes every sitting and
  is recorded on the folio.

## Decisions

- **2026-10-14: draws stay.** RNG-based radionics remains a legitimate
  divinatory method (the stick-pad analog), always labeled as a draw and
  never presented as a measurement.
- **2026-10-14: MOPS is retired as a rate.** A magical operation takes real
  time, so a per-second throughput figure overstates what happens. Replace it
  with real operations: each one has a start, a duration and a completion
  record.

## Open decisions (owner)

- **Hardware Levels 2 and 3** (crystal grid, bass shaker). Are they still in
  scope, or should the README be descoped?
