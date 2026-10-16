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
- [ ] Burn down the tsc baseline, starting with `AstrologyPanel.tsx` (90),
      `useWebSocketStable.ts` (31) and `AstrologyExtractionPanel.tsx` (31).
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
   - `backend/core/services/mops_engine.py:114-117`: MOPS adds hard-coded
     constants (17.73M ops/s whenever scalar is active, 120/s per crystal).
     This is exactly the "ops per second" counter the spec rules out.
     Retire it in favour of real operations (see Decisions).
   - `backend/core/services/vajra_service.py:638`: the broadcast "rate" is
     `freq % 100 + random.uniform(-2, 2)`, which is jitter presented as a
     reading.
   - `core/radionics_engine.py:297+`: the GV draw is legitimate as a draw.
     Label it as one, including in the LLM tool output, which currently
     attaches verdicts such as "Excellent".
   - `rng_attunement_service.py` e-meter needle, and
     `BroadcastPanel.tsx:260` random carrier-direction nudge.
4. **Guard test:** in the same spirit as `test_no_new_ruff_suppressions.py`,
   fail CI when `Math.random` / `np.random` feeds a displayed value outside
   an allow-list of decorative components.

## Phase 3: Consolidate

- Merge the two LLM tool registries (`backend/core/llm_agent/tools.py`,
  `core/radionics_tools.py`, about 100 tools in total) into one.
- Break the import cycles between `core` and `backend` and between `modules`
  and `backend`, and remove the 14 production `sys.path.insert`s.
- Finish ADR 002 step 3 (retire the `backend/app/config.py` shim).
- Continue splitting monoliths: `OutlookDashboard.tsx` (about 1,980 lines,
  55 `useState`) and `CommandCenter.tsx` (about 1,500 lines).

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
