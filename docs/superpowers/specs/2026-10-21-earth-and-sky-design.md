# Earth & Sky — Design

- **Date:** 2026-10-21
- **Status:** **Approved 2026-10-21** by dev-lead, on the learner's instruction ("approve the spec and start wave 0 and continue working and iterating"). The learner's own decisions are under *Decisions*. Waves are built and committed locally; **nothing is pushed without the learner's explicit go.**
- **Author:** dev-lead
- **Builds on:** [2026-08-16 Sittings Constellation & World Emanation](2026-08-16-sittings-constellation-and-world-emanation-design.md) (its "literal night-sky chart" shipped as `CelestialSkyDome`), and the corrected sunrise / planetary-hour code pushed on 2026-10-21 (`bcafb3e`).
- **Build order:** Waves 0 → 4 below. Anything past Wave 4 gets its own spec.

## Context

The practice already has a globe (`WorldEmanation`, `RadionicsGlobe`, `3D/Astrocartography`) and a sky (`CelestialSkyDome`). Both are honest about *what* they show but crude in *how*:

- The Earth is eight ellipses painted on a canvas (`createEarthTexture`, `worldEmanationHelpers.ts`). No coastlines, no day/night, no sense of where dawn is.
- The sky shows the Sun, Moon, eight planets and ten hand-keyed "sacred" stars. No star field, no constellations, no ecliptic, and no way to look at another place or time.
- The two never talk to each other: choosing a place on one does nothing to the other.

This spec gives the practice a true Earth and a true sky, linked by one observer and one clock, so that "where is dawn right now, and what stands overhead there" is something you can see.

### Facts verified in the code (2026-10-21)

| Fact | Where |
|---|---|
| `/astrology/night-sky` returns Sun, Moon, 8 planets, 10 sacred stars with alt/az, plus observer LST; provenance-labelled | `backend/app/api/v1/endpoints/astrology.py:96`, `core/celestial_sky.py` |
| A malformed `datetime_str` silently becomes *now* (`except Exception: dt = None`) | `astrology.py:108-119` |
| Without the ephemeris `celestial_sky` returns deterministic placeholder positions (labelled decorative) | `core/celestial_sky.py`, `docs/DEVELOPMENT_ROADMAP.md:127` |
| Dome polls every 60 s and runs a continuous `requestAnimationFrame` loop | `CelestialSkyDome.tsx:117, 284` |
| `WorldEmanation` polls every 120 s; its `<Canvas>` sets no `frameloop` and no `dpr`, so it redraws continuously whenever visible, even with nothing moving (same for `RadionicsGlobe`); its poll timer keeps running in a hidden tab (browsers throttle timers, they do not stop them) |
| Today's Earth texture is 512×256 (≈0.5 MB, ≈0.7 MB with mipmaps); the proposed 2048×1024 is 16× larger | `worldEmanationHelpers.ts:217-221` | `WorldEmanation.tsx:473, 511` |
| The Broadcast tab renders `WorldEmanation variant="full"` and, beside it, `BroadcastPanel`, which renders `MiniGlobe` unconditionally (200 px, its own `<Canvas>`, 800 drei stars) — **two WebGL canvases at once**, each building its own Earth texture with `useMemo(() => createEarthTexture())` | `routes/Operations/index.tsx:74`, `BroadcastPanel.tsx:353`, `RadionicsGlobe.tsx:394, 470`, `WorldEmanation.tsx:318` |
| The installed stack is three 0.157, @react-three/fiber 8.18, @react-three/drei 9.122 (which ships `View`); no globe library, no geography data | `frontend/node_modules` |
| The globes place planets on Earth with a stylised rule (`lon = ecliptic longitude − 180`, `lat = 23.44·sin λ`), not their real sub-points | `worldEmanationHelpers.ts:138` |
| A Vitest guard forbids unreviewed `Math.random` in `frontend/src` | `__tests__/no-unlabeled-math-random.test.ts` |
| Provenance kinds are exactly `record · computed · draw · decorative` | `frontend/src/lib/provenance.ts`, `core/provenance.py` |
| `vendor-three` is already a separate build chunk; CI builds the frontend | `frontend/vite.config.ts` |

**Not verified:** real-GPU frame times and memory, whether the Earth textures are ever disposed, and the star and constellation-line licences (the land licence is verified — see *Wave 0 results*).

## Product frame

- **Representation of computed truth.** The Earth shows where the Sun and Moon are; the sky shows what is overhead. Both come from the ephemeris, not from art.
- **Honest-instrument rule applies unchanged.** Positions are `computed`. Constellation figures are a human convention drawn between computed positions, so they are `decorative` and labelled. Twinkle and ambient motion are `decorative`. When the ephemeris is missing the view says so and labels placeholders decorative, exactly as `/night-sky` does today. **No fifth provenance kind is added.**
- **Practice first.** The views serve a sitting — where dawn is, what stands overhead for this working — not a dashboard of widgets. No scores, counters, or modelled "prayer waves" in this spec.
- **No claim about effect on any being.** The software shows geometry and time. What a dedication does is the tradition's claim, not the instrument's.

## Goals / non-goals

**Goals**
1. A real Earth: coastlines, day/night, the dawn line, sub-solar / sub-lunar / sub-planetary points.
2. A real sky: star field, constellations, ecliptic, planets, precessed to the date.
3. One observer + one clock shared by globe and sky.
4. Fits the resource budget below; works offline; additive to every existing API and component.

**Non-goals**
Tile/street maps or any runtime network fetch; modelled populations; sky cultures beyond the IAU figures; epochs far from today; VR; new auth or database tables.

## Design

### A. Earth

- **Land.** Natural Earth land polygons bundled as one static JSON, loaded with a dynamic `import()` the first time a globe mounts. `createEarthTexture()` keeps its name and return type and now paints real land with an equirectangular projection onto a 2048×1024 canvas; if the chunk fails it falls back to today's blobs, so no caller changes. The same data later feeds the flat strip and the mini globe (Wave 3).
  **Resolution caveat.** A 2048-px-wide texture is ≈19.6 km per texel at the equator, so finer land data alone does not make small atolls visible; 4096 px is ≈9.8 km but costs ≈43 MB with mipmaps (2048: ≈11 MB). Wave 0 therefore measures 110 m / 50 m × 2048 / 4096, plus a thin vector coastline overlay (crisp at any size, no texture cost), before choosing.
  **Decision rule (the learner's):** prefer the higher-fidelity option unless it measurably costs performance. Proposed thresholds for "measurably": more than +100 ms on first globe mount, more than +50 MB GPU memory, or more than +1 ms steady-state frame time.
- **Light.** A directional light at the sub-solar direction plus a low ambient floor. The night side reads dark with no custom shader and no texture regeneration.
- **Dawn line.** A thin line computed from the sub-solar point: the set of points where the Sun's centre is at altitude **−0.8793°**, the altitude at which the app's own sunrise code (`swe.rise_trans`, default flags) fires. This is *not* the textbook −0.8333°: the lead measured it over 78 events (astropy geometric altitude at swisseph's own rise/set instants, sd 0.0036°; −0.8746° in June to −0.8833° in December from the solar semi-diameter). Using −0.8333° would put the line 12–24 s off at normal latitudes and 55–80 s off near 64°N. The sunrise half and the sunset half are drawn in different colours; the sunrise half is the dawn line from the earlier discussion.
- **Sub-points.** Backend returns the geographic point under the Sun, the Moon and each planet (latitude = declination, longitude = right ascension − Greenwich sidereal time). Today `planetToLatLon` (`worldEmanationHelpers.ts:138`) places a planet at `lon = ecliptic longitude − 180`, `lat = 23.44·sin(ecliptic longitude)` — a stylised mapping, not where the planet is overhead. Wave 1 switches every use to the computed sub-point; any use that stays is labelled decorative.
- **Small places.** 110 m land omits many small islands, and this app cares about places like Kiritimati. The known locations (`data/astrology_locations.json`, `COUNTRY_COORDS`) are drawn as points regardless of the land resolution.

### B. Sky

- **Star field.** Every naked-eye star to magnitude ≤ 6.5 — the Yale Bright Star Catalogue (**8,404 stars** at V ≤ 6.5, out of 9,110 entries) — as compact arrays `[id, ra°, dec°, vmag, b−v]` for J2000, plus a separate small file of named stars, plus constellation line segments as pairs of star ids for the 88 IAU constellations. All lazy-loaded when the dome mounts. Stars in the last half-magnitude before the limit fade out instead of clipping.
  **Why 6.5, not 5.** Several traditional lunar-mansion stars are fainter than 5: the Revati yogatara ζ Piscium is ≈5.2–5.3 ([Wikipedia](https://en.wikipedia.org/wiki/Zeta_Piscium): 5.28 combined, 5.19 for the brighter component) and θ Cancri, determinative star of the Chinese Ghost mansion 鬼宿, is 5.32 ([Wikipedia](https://en.wikipedia.org/wiki/Theta_Cancri)). A magnitude-5 cut would silently drop members of the nakshatra and xiù systems this practice draws on.
  **IDs.** Wave 0 picks one ID system (Yale HR or Hipparcos HIP). Constellation-line data is usually keyed to HIP; if the catalogue is HR, the crosswalk is part of the dataset record.
- **Precession** J2000 → date as a pure TypeScript function. Proper motion, nutation and aberration are ignored (each below about 0.02° today; stated in the code and the UI footer).
- **Projection.** The dome's existing zenith-centred horizon projection. The backend keeps supplying planets and the Moon, plus the local sidereal time the observer block already returns; stars need only sidereal time and latitude, so the client rotates them.
- **Layers** behind `Switch`es the dome already uses: stars, constellation lines, constellation names, ecliptic line (computed from the obliquity), planets and Moon (existing), sacred stars (existing).
- **Colour and size** come from magnitude and b−v. Deterministic, so no `Math.random`. Twinkle stays the existing sine, stays `decorative`, and respects `prefers-reduced-motion`.

### C. Linking

- **`skyStore`** (new small zustand store beside the existing ones): `{ lat, lng, label?, at: ISO | null }`, `at = null` meaning live; defaults to `DEFAULT_LAT / DEFAULT_LNG`. Both views read it. Props passed explicitly to `CelestialSkyDome` still win, so existing callers and tests are unaffected.
- **Pick.** Clicking the globe raycasts to a latitude/longitude and sets the observer. The sky then shows what that place sees.
- **Time.** Live · pause · scrub ±24 h · "next sunrise here". Sunrise and sunset come from the solar-day bounds the planetary-hour code already computes — one source of truth, no new sun-event math.
- **Planetary hour** (ruler, time left) is shown on the dome from `calculate_exact_planetary_hours`.
- **Flat strip.** An equirectangular "world clock" strip with the dawn line sweeping across it; easier than a globe for reading a 24-hour wave.

### D. Backend

- **New:** `GET /astrology/earth-state?datetime_str=` → sub-solar and sub-lunar points, planet sub-points, Greenwich sidereal time, Sun declination, `provenance` map. Pure ephemeris maths in a new `core/earth_sky.py`; no DB, no network. Malformed or out-of-range time returns **422**. Naive times are UTC, documented.
- **New (Wave 3):** `GET /astrology/earth-state/series?start&end&step`, capped at 288 points, so scrubbing interpolates on the client instead of making a request per frame.
- **Existing `/night-sky`:** every current key keeps its name and type. A pinned contract test locks this. Additive fields only. The silent "bad time → now" fallback becomes a 422; the dome never sends `datetime_str` today, so nothing breaks.
- **Supported time range** is whatever the ephemeris in use actually supports; the builder states it and enforces it with 422.

### E. MiniGlobe

Today the Broadcast tab runs two WebGL canvases and builds two Earth textures. Browsers cap live WebGL contexts at about 16, so two is nowhere near the cap; the cost is the duplicated texture and geometry and the second render loop. WebGL textures cannot be shared across contexts, so a "shared" mini globe means one of:

1. **One canvas, two viewports.** In this stack that is drei's `<View>` (shipped in the installed 9.122): several scenes drawn into one `<Canvas>` with scissor + viewport, sharing texture and geometry, the mini globe staying live. Cost: a page-level canvas with each globe tracking a DOM element, so `WorldEmanation` and `MiniGlobe` (separate components in separate files) are restructured and their tests' `Canvas` mocks change. Best if the mini globe must keep its 3D look.
2. **A 2D orthographic canvas (recommended).** Land from the same data, the dawn line and a live dot, drawn with the ~10-line orthographic projection: no WebGL context, no texture, no new dependency (`d3-geo` is not installed and not needed). Today's `MiniGlobe` is an auto-rotating globe plus, when any session is active, a placeholder `'Active'` target with no location, so little is lost. `WorldEmanation` and its tests stay untouched.
3. **Static snapshot.** Rejected: it goes stale the moment anything dynamic is added, and it is a second code path.

## Resource budget

| Resource | Budget | How it is held |
|---|---|---|
| **Initial JS bundle** | +0 KB | All new data behind dynamic `import()`; `vendor-three` already split |
| **Lazy data** | land: **50 m chosen, 688 KB raw (≈141 KB brotli)**, inside the 800 KB cap (110 m would be 69 KB; the coastline overlay is drawn from the land rings, so there is no second 651 KB file); stars + names + lines ≤ 400 KB raw (**measured: 8,404 stars = 298 KB compact JSON, names 14 KB, lines 5 KB, 317 KB in all**; a quantised binary form is 84 KB and is the fallback if parse time matters; the budget test counts raw bytes, not gzip, because gzip output differs between Python builds) | A Vitest test asserts the data files' byte sizes; the chosen land budget is fixed after Wave 0 |
| **GPU memory** | one shared Earth texture: 2048×1024 ≈ 11 MB with mipmaps, 4096×2048 ≈ 43 MB (size chosen in Wave 0); today the Broadcast tab holds two separate 512×256 textures (≈1.4 MB in all), so the resolution decision is a real step up in GPU memory and is measured, not assumed | Cached at module level, shared by every globe, disposed when the last one unmounts (three.js does not free textures itself — a classic leak on remount); `dpr` capped at `[1, 1.5]` |
| **WebGL contexts** | one WebGL canvas per tab (two today on Broadcast) | `MiniGlobe` stops being a second WebGL canvas — see *E. MiniGlobe* |
| **CPU / frame** | idle ≈ 0 | r3f `frameloop="demand"` unless something animates; render loops pause when offscreen (hidden tabs are already throttled by the browser), poll timers pause on `visibilitychange`; dome twinkle throttled to 30 fps, static view redraws at 1 Hz; star projection (8,404 points) recomputed at ≤1 Hz live and per frame only while scrubbing; only the above-horizon half is drawn, into one `ImageData` buffer with a single `putImageData` per redraw (measured 0.61 ms for 9,100 synthetic stars against 1.45 ms for one arc + fill per star; the sprite-per-magnitude-bucket strategy measured 14 ms and is rejected) |
| **Network** | no new polling interval | Earth-state rides the existing 60 s / 120 s cadences; polling pauses when the tab is hidden |
| **Backend** | ≤15 ms p95 locally (measured today: `/night-sky` computation p95 0.10 ms; Sun + Moon + sidereal time p95 0.017 ms) | Ephemeris maths only; small LRU keyed by minute; series capped |
| **CI** | ≤ +15 s per job per wave | New Python tests are pure maths; new Vitest tests mock WebGL as `WorldEmanation.test.tsx` does; one Playwright smoke, in Wave 3 only |
| **Dev machine** | serialise heavy runs when available RAM < 8 GiB | Vite + Vitest ≈ 1–2 GB, headless Chromium ≈ 0.5 GB, Python suite ≈ 1 GB (estimates, not measurements) |

## Waves

Each wave is a separate commit chain, additive, revertible on its own, and leaves the full CI-style suite green. Existing tests stay unmodified: `tests/core/test_celestial_sky.py`, `tests/unit/test_sky.py`, `CelestialSkyDome.test.tsx`, `AstrologyPanel.sky.test.tsx`, `WorldEmanation.test.tsx`, `no-unlabeled-math-random.test.ts`.

### Wave 0 — Baseline and sources (read-only)

Measure, do not build. Output a short report under `docs/notes/`:
- chunk sizes from `vite build`; GPU memory and frame cost of the two canvases on the Broadcast tab (the co-mounting itself is already confirmed in the code); dome frame cost headless with 9,100 synthetic stars drawn;
- `earth-state`-equivalent ephemeris timings;
- for every dataset: source URL, version, **licence**, sha256 — land (Natural Earth, believed public domain), star catalogue (Yale Bright Star or Hipparcos), constellation lines (**licence unknown; stop and ask if the only usable source is share-alike**);
- land at 110 m and 50 m × texture 2048 and 4096, plus the vector-outline overlay: file size, parse + paint time on first mount, GPU memory, frame time, and whether Kiritimati, French Polynesia and the Maldives are visible; the decision rule in *A. Earth* then picks.

**Gate:** dev-lead confirms the data sources when every dataset is public domain or attribution-only. Any share-alike, non-commercial or unclear licence goes to the learner before a byte of it is committed.

#### Wave 0 results (updated as rows are accepted)

- **W0-1 land — accepted.** Natural Earth, public domain (live terms page and the data repo's own `LICENSE.md` both say so). 110 m: 127 polygons, 69 KB; 50 m: 1,421 polygons, 688 KB; converter deterministic. 110 m keeps 4 of 15 small-island probes, 50 m keeps 14 (Midway missing). The texture, not the data, limits small islands: Kiritimati is ≈2.3 texels across at 2048 and ≈4.6 at 4096. The separate coastline file duplicates the land outlines and is dropped.
- **W0-3 baseline — accepted** (chunk hashes and timings independently reproduced; headless software GL, relative only).
  - The Broadcast tab holds **two WebGL2 canvases and two 512×256 Earth textures** (≈1.05 MB uploaded).
  - Idle redraw is **60 callbacks/s** with nothing moving (≈11 ms task time each in software GL).
  - Initial JS is **3.73 MB raw / 1.13 MB gzip**: vendor-antd 1.48 MB, vendor-three 856 KB, and the app chunk 795 KB, which already contains both globes because `App.tsx` imports the Operations route statically. `CelestialSkyDome` is its own 8.5 KB lazy chunk.
  - After three away-and-back trips the heap after GC is 4.7 MB higher and the DOM-node count 783 vs 687: it does not all come back, which supports the explicit-disposal requirement in Wave 1.
  - Star drawing, 9,100 synthetic stars: `ImageData` 0.61 ms, arc + fill 1.45 ms, sprite buckets 14.2 ms.
  - Backend: `/night-sky` computation p95 0.10 ms; Sun + Moon + sidereal time p95 0.017 ms.
- **W0-2 stars — accepted, with one licence question open.** Catalogue: **Yale Bright Star Catalogue 5th rev. (CDS V/50)**, `attribution-only` (CDS terms; ReadMe has no copyright marker; cite Hoffleit & Warren 1991 and the VizieR acknowledgement); Hipparcos kept only as an independent check. Counts: 1,630 stars at V ≤ 5.0, 2,887 ≤ 5.5, 5,080 ≤ 6.0, **8,404 ≤ 6.5**. Eight non-stellar entries (novae, M31's S And) excluded. ζ Psc is V 5.24 and θ Cnc V 5.35 in this catalogue, both present at the limit. Max quantisation error 0.042″ over every star. IAU Catalogue of Star Names: CC BY, 338 of 452 names map onto the catalogue (14 KB). Independently re-checked: converter reproduced on Python 3.13 (all uncompressed outputs byte-identical to dev-d's 3.14 run; only gzip bytes differ), and 18 well-known stars land within 19″ of the catalogue values (almost all under 3″) with the southern hemisphere correct (4,323 of 8,404 stars have negative declination). **Parse hazard recorded:** the V/50 declination sign sits in column 84, outside the documented field; naive parsing silently mirrors the southern sky.
  - **Constellation lines — decided by the learner (2026-10-22): option A, use d3-celestial's figures with attribution.** Stellarium's modern figures are GPL-2.0+ (share-alike): counted only, **not** used. d3-celestial's `constellations.lines.json` is BSD-3-Clause (attribution-only) but its README says the lines come from the IAU constellation page "with some line modifications by me"; those figures were designed at Sky & Telescope (MacRobert, Sinnott, Fienberg) for the IAU, and I could only find third-party reports (not a first-party statement) that they are CC BY 3.0. Wikimedia Commons' metadata for the IAU/S&T chart reads CC BY 3.0, artist "IAU and Sky & Telescope magazine (Roger Sinnott & Rick Fienberg)", attribution required; the IAU's own page has moved, so this is third-party evidence. Residual risk accepted by the learner; undoing it means deleting one 5 KB file and one credits line.
  - **Credits to ship** (UI footer + a credits file): Natural Earth (no credit required, courtesy line); Bright Star Catalogue 5th rev. via CDS VizieR; IAU Catalogue of Star Names (CC BY, IAU); constellation figures: "IAU and Sky & Telescope magazine (Sinnott and Fienberg), CC BY 3.0, via d3-celestial (BSD-3)".
- **W0-5 mansion-star table — accepted as a presence test, not as an authority.** 56 rows (27 nakshatras + Abhijit, 28 xiù), every star resolved through SIMBAD. All 80 star references are present in the V ≤ 6.5 catalogue (checked independently against dev-d's data): the faintest are θ Cnc 5.35, ζ Psc 5.24, then 35 Ari 4.66; none is fainter than 5.35. **Honest consequence:** a limit of 5.5 would already keep every mansion star; 6.5 stays because it is the complete naked-eye sky and costs almost nothing (298 KB), not because the mansions need it. Six entries are `DISPUTED` between sources (xiù 心, 尾, 奎, 觜, 参, and nakshatra Shatabhisha), e.g. 心's determinative star is σ Sco, with Antares the asterism's second star. **Limit:** only 9 of 28 nakshatra yogataras are actually sourced to a named star; for the other 19 the table holds the brightest asterism member as a placeholder. Do not present those 19 as yogataras in the UI; a classical source table is needed first (Wave 5).
- **W0-4 texture size and disposal — accepted** (software GL, relative evidence; medians recomputed by the lead from `raw/runs.jsonl`, all matching). Against today's 512×256 blob texture: **50 m at 2048** costs +56 ms mount, +40 MB, +0.0 ms frame (passes every threshold); 50 m at 4096 costs +223 ms and +110 MB (fails two); the full 50 m outline adds +3.9 ms per frame and +13 MB (fails frame time); a 110 m outline adds +0.4 ms. Sharing one texture between two globes saves ≈36 MiB at 2048, and the 2D mini globe removes the second texture altogether (110 m rings redraw in 0.6 ms median, 50 m in 3.0 ms, and the two look the same at 200 px, so the mini globe uses 110 m). **No Earth-texture leak across 10 mount/unmount cycles** (≈0.3 MiB per cycle with or without explicit disposal; r3f's unmount already forces context loss), so W0-3's heap residue was not the texture; we still dispose explicitly because it is free. **Tiny-island overlay:** polygons under 0.5° across number 913 and total ≈9,150 outline segments (the full outline is 60,254); they include Kiritimati, Tahiti, Easter Island, Guam, Bermuda and Mauritius. Expected cost ≈+0.6 ms, to be measured in Wave 1.
- **Wave 0 is complete.**

### Wave 1 — Earth truth

Write set: `core/earth_sky.py` (new), additive endpoint in `astrology.py`, `frontend/src/lib/earth.ts` (new), the land data file, `createEarthTexture`, light + dawn line + sub-points in `WorldEmanation` / `RadionicsGlobe`, texture cache and disposal.

Acceptance:
- Dawn line passes through each of 12 cities (including Kiritimati, Fairbanks, Auckland, Sao Paulo) at that city's computed sunrise, ±10 s up to 55° latitude and ±20 s up to 65° (the residual is the seasonal semi-diameter) — checked against the sun-event code verified in the 2026-10 batch **and** a second, independently written solar-position oracle owned by the reviewer.
- Sub-solar point within 0.01° of the ephemeris.
- Land chunk lazy; blob fallback works when it fails; texture disposed on unmount (test).
- Data byte-size budget test.

### Wave 2 — Sky truth

Write set: star / constellation data files, `frontend/src/lib/sky.ts` (precession + projection, new), layers in `CelestialSkyDome`, the `/night-sky` malformed-time 422 and contract test.

Acceptance:
- Reviewer-owned offline oracle (an astronomy library run once under `docs/notes/`, **never a repo dependency**) agrees within 0.05° over ≥200 star / place / time combinations.
- Polaris altitude ≈ latitude (± the known offset); Sirius culminates at the expected sidereal time.
- Every constellation segment resolves to a catalogue star (data-integrity test).
- All 27 nakshatra yogataras (plus Abhijit) and the 28 xiù determinative stars resolve to catalogue entries, checked against a reviewer-owned table cross-checked from two sources.
- Faint-edge fade: alpha is monotone in magnitude over the last 0.5 mag and the catalogue is never clipped abruptly.
- Dome draw time with all 8,404 stars stays within the CPU/frame budget (measured, not assumed).
- Dome renders under a mocked 2D context; no `Math.random`.

#### Wave 2 results (accepted 2026-10-24, updated as rows are accepted)

- **Stars and figures:** 8,404 stars to V 6.5 (BSC5, CDS V/50), 338 IAU names, 88 constellations / 150 polylines / 893 vertices (d3-celestial, with attribution), all lazy chunks. Licences and acknowledgements are quoted in `frontend/src/data/README-sky.md`.
- **Accuracy (independent astropy oracle, 6,160 star/place/time rows, 1800-2199):** the shipped `sky.ts` is 0.0002 degrees from the precession-only reference and at most 0.010 degrees from the full chain (nutation + aberration, not modelled); `gmstDeg` matches an independent IAU 1982 reference. Proper motion is not modelled (Arcturus about 0.017 degrees in 26 years).
- **Defects found by review and fixed, worth remembering:** (1) precession added radians to degrees (57x too small, 2.5 degrees at the ends) and the test meant to catch it was a `skipIf` around `expect(true)`; (2) the Wave 0 conversion of the figures keyed a dict by constellation id and dropped half of Serpens (the raw file has two `Ser` features) and nobody counted the output; (3) the backend's sacred stars were never precessed (0.15-0.37 degrees today, 2.8 at 1800/2199; now within 0.016 of astropy); (4) `/night-sky` silently answered "now" for a bad time, 500 for years past 5400 and 200 for year 0001: it is now strict like `/earth-state` (1800-2200, 422/503); (5) `gmstDeg` had a T^4 term where the polynomial has T^2.
- **Dome:** layer cache keyed on size, flags, sidereal time, latitude and epoch; draws at most every 33 ms while something twinkles, once a second otherwise, pauses in a hidden tab, honours reduced motion; star and figure chunks load independently; labels say what is computed and what is decorative. Production build in headless Chromium: 30 of 30 brightest stars within 2 px of an independent prediction at San Francisco and Sydney, worst oracle separation 0.00006 degrees.
- **Budget:** initial JS for the Earth & Sky feature +2.4 KB gzip against the 10 KB budget, as measured when Wave 2 was accepted (the figure for the whole feature is under *Wave 3 results*); star data, lines and the dome are lazy chunks.
- **Known residuals:** the live Sun, Moon and planets in `/night-sky` are **geocentric** although the module docstrings say topocentric (the Moon can differ by up to about 1 degree from where it appears at a place); the dome has no sky-brightness layer, so stars are drawn in daylight; labels clip at the right edge of the canvas and overlap near the centre.

### Wave 3 — Link, time, flat strip

Write set: `skyStore`, globe pick, time controls, series endpoint, planetary-hour readout, flat strip, an "Earth & Sky" layout on the Operations → Broadcast tab, and `MiniGlobe` per *E. MiniGlobe* (Decision 5).

Acceptance:
- Picking a place moves the dome; scrubbing moves both consistently.
- "Next sunrise here" lands on the verified sunrise (±1 s).
- Series cap enforced.
- One serial Playwright smoke; exactly one WebGL canvas on the Broadcast tab.

#### Wave 3 results (updated as rows are accepted)

- **Decisions that differ from the text above:** the store the spec calls `skyStore` did not exist (Wave 1 built only the live `earthStateStore`), so Wave 3 created it: `{lat, lng, label?, at}` with `at: null` meaning live, strict zone-explicit ISO instants only (a naive time is local time in JavaScript, so the same string was 10:00Z, 17:00Z or 01:00Z depending on the browser's timezone), scrub clamped to +-24 h. **The series cap fencepost:** both ends included, a 48 h window at 600 s is 289 samples, one over the cap of 288; the cap stays and the client asks for `step_seconds = 603` (287 x 603 s = 48 h 04 min). `/astrology/planetary-hours` takes no place or time, so the readout needs another route (see W3-J). The existing full 3D globe on the Broadcast tab is the tab's one WebGL canvas; the new card adds none.
- **Built and verified:** `GET /astrology/earth-state/series` (<= 288 samples, apparent sidereal time, sub-points: RA = lon + GAST) and `GET /astrology/sun-events` (the engine's own solar-day code, `null` for polar day/night, 503 instead of the 6 AM estimate), checked against swisseph/astropy/NOAA oracles (series 1,080 of 1,080 samples, sun events 126 cases); validated clients with stale-answer guards and 15 s timeouts, run against the real routes (118 seam cases, none wrongly accepted or rejected); the series maths (interpolation error at the 603 s step at most 0.000013 degrees); the dome follows the store and has a scrub mode (one series request, banner says which values are computed for the instant and which are as of now); the flat strip with an exact per-pixel night mask (every pixel checked against an analytic altitude); time controls (Live, Pause, +-24 h, "Next sunrise here" -- which returned the same sunrise forever until the real route exposed it); click-to-pick on the globe (a real raycast under software WebGL picked on every click and the atmosphere shell does not intercept it); the Earth & Sky card on the Broadcast tab; one real-browser smoke (3 of 3 runs green).
- **Committed since the first version of this section:** the shared source for the shown instant (`b79c8ce`): one series window is fetched once and the globe, the strip, the mini globe and the dome all scrub from it, frozen at the chosen instant, with the live poll paused while scrubbed; the scrub path loads on demand so the initial bundle keeps its budget (`b97068d`); and the planetary-hour readout (`0aa05bd`), directly under the dome (beside it, not inside it), from a new strict route `GET /astrology/planetary-hour`: ruler, day or night hour, exact time left, `null` with a reason at polar day or night, 503 instead of an estimate. It does not use `/timing-wheel`, which answers "now" for a malformed date and, at a polar place, substitutes a 06:00 / 18:00 estimate that its provenance still labels `computed`.
- **Initial JS:** the whole Earth & Sky feature (Waves 0-3, with the readout) is +3,246 B gzip against the 10 KB budget (the committed measurement taken by the lead on 2026-10-24).
- **"One instant everywhere", honestly:** it is exact for the scrubbed (frozen) state. While LIVE the views extrapolate from different anchors (the globe from fetch receipt on `Date.now`, the strip and the mini globe from the payload instant, the dome from `performance.now`, the dome's planets sampled every 60 s), so they agree to about a second of Earth rotation plus the response age, not exactly.
- **Honest labelling on the card:** its caption names the selected mode only (live, or scrubbed to a UTC instant) and does not claim that anything was computed; the strip, the dome, the readout and the controls each carry their own status and provenance. A cold scrubbed dome still needs a successful live `/night-sky` for names and sacred-star metadata, even when the shared series arrived.
- **Being finalised:** the browser smoke for the card, including the scrub assertion for the strip and the globe; its spec is not yet committed.

### Wave 4 — Practice integration

Show the sky and Earth state at a sitting's phases (preparation, invocation, broadcast, dedication) using the existing broadcast events; the dedication phase can pulse the dawn line. **Gate:** needs a look at the ritual engine's event stream; if larger than a day's work it becomes its own spec.

### Not in this spec

Sky cultures (nakshatra boundaries, Chinese and other star lore), archaeoastronomy replay, calendar-convergence finder, the collective mala, modelled populations.

## Verification (how this repo works)

- Independent oracles built by someone other than the builder; reviewer-owned fixtures.
- Exact bytes frozen at acceptance and hash-checked.
- A clean clone, CI-style suite on the CI Python (3.13) and the CI frontend commands, before each local commit.
- Data fetched once with its checksum recorded; never at test time.
- No live-database access, no network, no paid or audio calls in tests.
- No push without the learner's explicit go.

## Risks

| Risk | Mitigation |
|---|---|
| Constellation-line licence | Wave 0 gate; fall back to deriving lines ourselves from catalogue ids |
| 110 m land loses small islands | Location points always drawn; 50 m measured in Wave 0 |
| three.js texture / geometry leaks on remount | Shared cache, explicit disposal, a test |
| No WebGL in test environments | All logic in pure functions; renderers mocked as today |
| Precession approximation drifts far from today | Time range enforced with 422; stated in the UI footer |
| Existing decorative starfield (drei `<Stars>`) uses randomness internally | Stays labelled decorative; may be replaced by catalogue stars in Wave 2 |
| ≈8,400 stars cost too much to redraw while scrubbing | `ImageData` path (0.61 ms synthetic); re-measured with the real, faint-heavy catalogue in Wave 2; lower the magnitude limit only if measurement says so |
| Finer land data still invisible at 2048 px (≈19.6 km/texel) | Wave 0 (W0-4) measures 2048 vs 4096 and the vector overlay drawn from the land rings; known locations are always drawn as points |

## Decisions

| # | Decision | Status |
|---|---|---|
| 1 | Placement: an "Earth & Sky" panel on Operations → Broadcast | **Decided** (learner, 2026-10-21) |
| 2 | Land resolution | **Decided by the rule:** land data **50 m**, texture **2048×1024**. W0-4 (recomputed by the lead from the raw runs): 4096 fails mount (+223 ms) and memory (+110 MB); the full 50 m outline fails frame time (+3.9 ms) and memory (+53 MB). Tiny islands get a thin outline instead (see *A. Earth*), accepted only if Wave 1 measures it inside the thresholds |
| 3 | Star limit | **Decided:** V ≤ 6.5 with a faded edge (learner, 2026-10-21; reasons in *B. Sky*) |
| 4 | Default figures: IAU western constellations first, other traditions later | Proposed, unchallenged |
| 5 | `MiniGlobe` | **Decided by dev-lead (learner did not choose): a 2D orthographic canvas.** Reversible: if the learner prefers the mini globe to stay 3D, use a second `View` on one shared canvas instead (*E. MiniGlobe*). Wave 0 and Waves 1–2 do not depend on this |
