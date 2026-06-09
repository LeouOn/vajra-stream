<think>
The user wants a PR review for the Vajra Stream project. Let me analyze the commits to understand what's in this PR:

Key themes I see:
1. **TTS (Text-to-Speech) feature** - Multiple commits adding TTS provider, endpoints, settings panel, player, and wiring into widgets
2. **UI features** - OutlookDashboard improvements, TrendsChart optimization, NatalChartWheel, ExportPanel, SynastryViewer, TransitComparison upgrade, BodhicittaBanner, RitualMonitor
3. **Backend features** - core/ritual_engine.py, Hellenistic lots, extraction features (TimeGrid, LLM-friendly formatter), TTS endpoints
4. **Bug fixes** - geocoding NameError, missing exports, docstring language, transit/comparison bugs
5. **Tests** - Lots of test additions: backend (ritual_engine, Bodhicitta, endpoints), frontend (Playwright E2E, happy-dom, vitest tests)
6. **Build/Performance** - Vendor chunk splitting, recharts removal

This is a massive PR with 38 commits. Let me craft a review.

For the title - it's a mix of features, but the most prominent seem to be the TTS feature, UI upgrades, and ritual engine. Given the variety, I should use a title that captures the major scope. Something like:

"feat(tts,ui,ritual): add TTS pipeline, UI components, and ritual engine"

But that's awkward. Let me think... The PR has too many things to have a single tight title. I'll focus on the most significant additions.

Actually, looking more carefully, this seems to be a large feature PR that includes:
- TTS system (major)
- Ritual engine (major)
- Multiple UI components (charts, export, dashboard)
- Extraction improvements
- Bug fixes

Title ideas:
- `feat: TTS pipeline, ritual engine, and UI upgrades` (51 chars)
- `feat(tts,ui,ritual): unified TTS, ritual engine, chart components` (62 chars)
- `feat: TTS system, ritual scheduler, and UI overhaul` (54 chars)

I'll go with something like: `feat: TTS pipeline, ritual engine, and chart UI components` (57 chars)

Top 3 things to verify:
1. The TTS pipeline is a new external dependency integration - verify Edge/Qwen3-TTS backends work, streaming endpoints behave correctly
2. The 393-line vajra_stream_v2.py deletion - make sure nothing else imported from it
3. The big frontend build/perf changes (recharts removal, vendor chunk splitting) - verify the UI still renders correctly

Let me also consider the test coverage claim:
- 17 ritual scheduler tests
- 12 BodhicittaBanner tests
- 8 ritual_engine endpoint tests
- 19 ritual_engine tests
- 13 Bodhicitta tests
- 117 vitest tests
- Playwright E2E
- happy-dom component tests

So testing is solid.

Risks:
- 38 commits in one PR is a lot - hard to review
- TTS is a new external dependency
- Frontend perf changes (recharts removal) could break visuals
- The -17194/43728 stats with the v2 deletion could mask regressions

Let me write this up concisely.
</think>
```markdown
# feat(tts,ui,ritual): unified TTS pipeline, ritual engine, and chart UI

## Summary

- **TTS system (end-to-end):** new unified provider with Edge/Qwen3-TTS backends, REST endpoints with role overrides and streaming, wired into the recitation loop, operator tools, and existing widgets; includes a settings panel and narrative player.
- **Ritual engine:** new `core/ritual_engine.py` autonomous scheduler with `RitualConfigUpdate` endpoint, a UI `RitualMonitor`, and a `BodhicittaBanner` for surfacing state.
- **Astrology/extraction depth:** Hellenistic lots (Fortune, Spirit, Eros, Necessity, Courage, Victory, Nemesis), `get_comprehensive_astrology` extended with houses + Chiron, `TransitComparison` upgraded for 4-pillar Bazi + house cusp aspects, plus new `ExtractionConfig/Run/Result`, `TimeGrid` generator, and an LLM-friendly chart formatter.
- **UI work:** `NatalChartWheel` (SVG + houses/planets), `ExportPanel` (selection/format/preview/download), `SynastryViewer` counts + distribution chart, `OutlookDashboard` Affirmation tab + Difficulty + Global Intentions, `VisualizationSelector` recreated, `TrendsChart` rewritten without recharts and memoized.
- **Quality:** ~190 new tests across vitest/happy-dom/Playwright + backend (`ritual_engine`, Bodhicitta transmutations, endpoint coverage), vendor-chunk split (85% smaller main bundle), and four bug fixes (geocode 400-as-500, missing API exports, Python-in-JS docstring, transit/comparison bugs).

## Test plan

- Backend: `pytest` covers `core/ritual_engine.py` (19), endpoint (8), Bodhicitta transmutations (13), and prior coverage. Verify `RitualConfigUpdate` round-trips and the scheduler's pure methods are pure.
- Frontend: `vitest` (incl. 117 new + BodhicittaBanner/astroHelpers), `happy-dom` component tests, and Playwright E2E smoke for the TTS player, ExportPanel download, and OutlookDashboard Affirmation tab.
- Manual: stream a TTS narrative with role override, render a Natal chart with houses populated, confirm TrendsChart refresh path still triggers after recharts removal, and run a full `pnpm build` to confirm the smaller main bundle and no missing chunk references.
- Migration: run the centralized migration runner against a fresh DB and an existing one to validate the new extraction/location tables.

## Risks / concerns

- **Scope:** 38 commits, 196 files, +17k/-43k lines. The deletion is dominated by `vajra_stream_v2.py`; confirm no remaining imports reference it and that the new modules it duplicated are fully drop-in.
- **TTS external dependency:** Edge + Qwen3-TTS backends, model cache dirs, streaming, and role overrides are all new surfaces — provider failures, chunked-encoding behavior, and audio mime type on the player need real-environment validation, not just unit tests.
- **Frontend regressions:** removing recharts and changing chart internals (`TrendsChart`, `SynastryViewer`, `NatalChartWheel`) is a visual risk; happy-dom tests don't catch SVG layout regressions — needs screenshot diffs or manual visual review.
- **Migration safety:** centralizing the migration runner and adding new tables in one PR means a failed migration on an existing DB could block startup; verify down-migration / idempotency story.
- **API surface drift:** the `fix(api): sync endpoints/__init__.py` commit implies exports had drifted from `api.py`; worth a grep to confirm no other `__init__.py` re-exports are similarly stale.

## Top 3 things to verify before merging

1. **`vajra_stream_v2.py` deletion is clean** — grep the repo for any remaining references (imports, docs, configs, fixtures) and confirm the replacement modules cover every symbol the old file exposed.
2. **TTS end-to-end in a real browser** — exercise the settings panel → narrative player path with both Edge and Qwen3-TTS backends, including streaming playback and role overrides, since this is the largest new user-facing surface.
3. **Frontend build + visual regression** — run the production build to validate the vendor-chunk split, then visually compare `TrendsChart`, `SynastryViewer`, `NatalChartWheel`, and `OutlookDashboard` against the pre-PR UI, since the recharts removal and multiple new chart components are the highest-risk rendering changes.
```