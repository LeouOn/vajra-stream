# Sitting-Loop Integrity & LLM Spine — Implementation Plan (DAG)

> **For agentic workers:** REQUIRED SUB-SKILL: `subagent-driven-development` (or `executing-plans`) to implement this plan PR-by-PR. Each PR is independently mergeable; check off acceptance tests as you go.

**Goal:** Make "one sitting → one rate folio → one outlook" the default, collapse the dual LLM stacks into one generate path, and trim the surface/hygiene debt — without a rewrite.

**Architecture:** Small PRs on `origin/main`. Each PR is a DAG node; nothing here touches the audio singleton, adds a 31st router, or introduces `as any`/ruff suppressions.

**Tech Stack:** Python 3.10–3.13 + FastAPI + SQLAlchemy (backend), React 18 + TS + Vite + AntD (frontend), SQLite.

## Global Constraints (verbatim, apply to every PR)

- **No new ruff suppressions** — `pyproject.toml [tool.ruff.lint.per-file-ignores]` stays empty; `tests/unit/test_no_new_ruff_suppressions.py` snapshots 0/0.
- **No `test_*.py` at `tests/` root** — every test lives under `unit/`, `integration/`, `e2e/`, `backend/`, or `core/`.
- **No `as any` / `@ts-ignore` / `@ts-expect-error`** in frontend TS.
- **No new `API_BASE` constant** — use `apiUrl()` from `frontend/src/utils/api.ts` (ADR 004).
- **Never break** the audio singleton (`backend/core/services/vajra_service.py:774 vajra_service`, ADR 001) or `container.audio` (ADR 001 separate LLM-tool path).
- **Never add a 31st router** — prefer deleting/unifying; register new endpoints only inside existing routers in `backend/app/api/v1/api.py`.
- **Stay on `origin/main`** unless a PR genuinely needs a branch; the other machine pulls main.
- **Windows PowerShell:** no `&&`; chain with `cmd1; if ($?) { cmd2 }`.
- **Do not implement until the human approves this DAG.**

---

## A. North star

After this work, a single sitting is a **straight line**: the practitioner types one intention into the Command Center (or approves one autonomous suggestion), the LLM calls `run_working` exactly once, a **folio card** (5 dials + Saka Dawa stamp + charge) is rendered in the chat with the prose reduced to a 3–5 sentence caption, and — only if the practitioner asks — one Outlook narrative is generated against that same intention and shown as its own card. No auto-chain re-mints the working, the background 60-minute loop is explicitly a *background ambience* stream (not a sitting), and every LLM call — chat, outlook, blessing — resolves through one provider registry with truthful `model_used`/`provider_used` recorded from the call that actually ran. The radionics/Operations surface shrinks to its real job (rates, scalar, broadcast) and stops looking like a second Command Center.

---

## B. Inventory — every way to start a working / outlook / blessing today

| # | Entry point (file:line) | What it mints | Survives? |
|---|---|---|---|
| 1 | `core.working.run_working()` — `POST /operator/working` (`backend/app/api/v1/endpoints/operator.py:704`), chat tool (`backend/app/api/v1/endpoints/llm.py:586`), `TOOL_REGISTRY` (`backend/core/llm_agent/tools.py:1137`), auto-chain (`llm.py:1749`) | `wrk_*` folio + optional `broadcast_healing` | ✅ **Canonical** — add idempotency |
| 2 | `modules/radionics.py:60 broadcast_healing` (called from `core/working.py:327`, `modules/radionics_operator.py:1515`, `core/character_journey.py:452`, `backend/app/api/v1/endpoints/radionics.py:214`) | rates broadcast only (no folio) | ✅ keep as low-level primitive |
| 3 | `modules/outlook.py:231 generate_single` / `:318 generate_epic` → `core/outlook_generator.py:731/974` | `outlook_narratives` row + `BlessingGenerated` | ✅ **Canonical** |
| 4 | `POST /outlook/generate_single|epic` (`backend/app/api/v1/endpoints/outlook.py:91/180`) | same as #3 (thin HTTP wrapper, `asyncio.to_thread`) | ✅ keep |
| 5 | chat tool `generate_single_outlook`/`generate_epic_outlook` (`llm.py:595/615`, in-process `container.outlook.*`) | same as #3 | ✅ keep (renders card) |
| 6 | `TOOL_REGISTRY generate_single_outlook`/`generate_epic_outlook` (`backend/core/llm_agent/tools.py:711/762`) — `client._post("/api/v1/outlook/generate_single")` | **SELF-HTTP POST back into this process** | ❌ convert in-process (or delete) |
| 7 | background generation loop (`outlook.py:971 _background_generation_loop`; started at `main.py:213`, `/outlook/background/start`, `/outlook/loop/start`, `/outlook/idle/start`) | outlook rows on a 60-min timer | ✅ keep, but label "background", not sitting |
| 8 | `modules/outlook.py:412 start_broadcast_loop` / `:448 _run_broadcast_loop` (RitualSequencer) | outlook rows | ❌ **dead duplicate loop** — no HTTP caller; delete |
| 9 | `RadionicsOperator.start_blessing_loop` (`modules/radionics_operator.py:1100`; `operator.py:411`) | LLM blessing strings (NOT outlook rows) | ✅ keep (distinct feature) |
| 10 | `BlessingScheduler.start_automation` (`blessing_scheduler.py:148`; `automation.py:100`, `llm.py:344`) | round-robin slideshow | ✅ keep (ADR-003 G4 exempt) |
| 11 | `vajra_service._start_broadcast_loop` (`backend/core/services/vajra_service.py:433`) | audio spectrum broadcast | ✅ keep (audio, ADR-001); clarify naming only |
| 12 | chat **auto-chain** (`llm.py:1741-1809`) | re-mints `run_working` / `generate_single_outlook` | ⚠️ **stop re-minting**; render the existing card + short caption |

**Root cause of the fan-out:** the same intention can mint duplicates via the intersection of #1 (operator action button + chat tool + auto-chain) and #3/#5/#6 (chat tool + self-HTTP registry tool + auto-chain + background loop). The fix is (a) idempotent `run_working`, (b) a single in-process outlook path, (c) an auto-chain that reuses rather than re-mints, and (d) deleting the dead loop #8.

---

## C. Workstreams

### W1 — Sitting integrity

#### W1-PR1: Idempotent `run_working`
- **Title:** `fix(working): dedupe identical intentions within a sitting window`
- **Files:**
  - `core/working.py` (add `find_recent_working(intention, target, window_seconds)` + call it at the top of `run_working`; return the existing folio with `"reused": True` instead of minting a new `wrk_*`)
  - `tests/core/test_working.py` (extend existing `test_run_working_*` family)
- **Acceptance test:**
  ```python
  # tests/core/test_working.py
  def test_run_working_is_idempotent_within_window(tmp_path, monkeypatch):
      a = run_working("peace for the watershed", broadcast=False)
      b = run_working("peace for the watershed", broadcast=False)
      assert b["working_id"] == a["working_id"]
      assert b.get("reused") is True
      # different target or a different intention still mints a new folio
      c = run_working("peace for the watershed", target="the children", broadcast=False)
      assert c["working_id"] != a["working_id"]
  ```
  Run: `pytest tests/core/test_working.py -q`. Expect PASS.
- **Risk:** Low. The dedupe window must be short (≤ 60s) and keyed on normalized `(intention.lower().strip(), target.lower().strip())` so a genuinely new sitting still mints a fresh folio. Existing test `test_run_working_seals_folio_without_broadcast` (unique intentions) must keep passing.
- **Must not break:** `core.working` on-disk `wrk_*.json` schema (additive `reused` key only), `list_workings`, `delete_working`, the `/operator/working` HTTP contract.

#### W1-PR2: One outlook per request + stop the duplicate auto-chain
- **Title:** `fix(chat): auto-chain reuses the sealed result instead of re-minting`
- **Files:**
  - `backend/app/api/v1/endpoints/llm.py` (lines ~1706-1809: the tool-loop already dedups `generate_single_outlook` via `already_ran`; extend the same guard to `run_working` so the auto-chain at `:1749` skips when a `run_working` success already exists in `raw_tool_results`; change the `:1827` summary prompt from "Write a brief warm 4-8 sentence summary" to a hard cap of 3 sentences and instruct the model to *reference the card* rather than restate rates/intentions)
  - `tests/unit/test_llm_tool_parsing.py` (add a case asserting the dedup set includes `run_working`)
- **Acceptance test:**
  ```python
  # tests/unit/test_llm_tool_parsing.py  (or tests/unit/test_chat_dedup.py)
  def test_run_working_is_in_generation_dedup_set():
      from backend.app.api.v1.endpoints import llm as llm_endpoint
      # the module-level dedup guard must treat run_working as already-satisfied
      assert "run_working" in llm_endpoint._ALREADY_GENERATED  # if extracted, else assert via regex path
  ```
  Plus a manual gate: one chat message "begin a working for peace" produces exactly **one** `wrk_*` card and no second `run_working` tool-call entry.
- **Risk:** Medium — editing the tool-loop/auto-chain is the most delicate code in `llm.py`. Keep the change surgical: guard placement only, no reordering of the `_execute` calls.
- **Must not break:** chat job poll/cancel (`/llm/chat/jobs/{id}`), the `list_populations` dedup, `collapse_stutter`/`visible_text`, the 300s poll timeout.

#### W1-PR3: Command Center cards-first for folio + narrative
- **Title:** `feat(ui): working & outlook render as cards, prose reduced to caption`
- **Files:**
  - `frontend/src/components/CommandCenter/RenderMessageWidgets.tsx` (already renders `WorkingFolioCard` and the outlook card — verify both fire for `run_working` and `generate_single_outlook`; no change needed unless a tool-name alias is missing)
  - `frontend/src/components/UI/CommandCenter.tsx` (`replyText` fallback at `:897` already says "See the cards below" — keep; no code change if widgets already cover both tool names)
- **Acceptance test:** `cd frontend; npx vitest run` (existing `no-orphan-components` + component tests) green. Manual: run one sitting → folio card visible with dials/charge/witness buttons; run one outlook → outlook card visible; chat prose ≤ 3 sentences.
- **Risk:** Low — mostly verification; only edit if a tool name is missing from `RenderMessageWidgets` dispatch (`run_working`, `forge_witness`, `generate_outlook`, `generate_single_outlook`, `generate_epic_outlook`).
- **Must not break:** the `ZoomItem`/`ZoomModal` contract, `apiUrl` calls inside the cards.

---

### W2 — LLM spine

#### W2-PR1: One generate path — registry-backed facade with truthful `model_used`
- **Title:** `refactor(llm): single generate facade; record actual model/provider used`
- **Files:**
  - `core/llm/legacy_adapter.py` (add a `self.last_used: dict` populated at the end of `_generate_async` with `{model, provider}`; add a `get_active_provider()` method returning it — the name already called at `core/outlook_generator.py:954`)
  - `core/outlook_generator.py` (line ~948-958: read `model_used`/`provider_used` from the new truthful source; no signature change)
  - `tests/core/llm/test_legacy_adapter.py` (or existing `tests/core/llm/`) — assert `last_used` reflects the provider actually selected for a stub provider
- **Acceptance test:**
  ```python
  # tests/core/llm/test_legacy_adapter.py
  def test_generate_records_last_used():
      adapter = LegacyLLMIntegration(registry=stub_registry)
      adapter.generate("ping", model="stub:stub-model")
      assert adapter.get_active_provider()["model"] == "stub-model"
  ```
  Run: `pytest tests/core/llm -q`. Expect PASS.
- **Risk:** Medium — `LegacyLLMIntegration` is the sync adapter over the *same* registry the chat uses; the change is additive (`last_used`), so no routing change.
- **Must not break:** `modules/llm.py:LLMService` lazy construction, `OutlookGenerator` fallback when `self.llm is None`, the `"No LLM initialized"` sentinel.

#### W2-PR2: In-process outlook tools (kill self-HTTP)
- **Title:** `fix(tools): generate_single/epic_outlook call the container in-process, not /api/v1/...`
- **Files:**
  - `backend/core/llm_agent/tools.py` (lines ~711-790: replace `client._post("/api/v1/outlook/generate_single", ...)` with `from container import container; return container.outlook.generate_single(...)`; same for `generate_epic_outlook`)
  - `tests/unit/test_llm_tool_parsing.py` or a new `tests/unit/test_outlook_tool_inprocess.py` asserting no `_post("/api/v1/outlook` remains
- **Acceptance test:**
  ```bash
  grep -rn '_post("/api/v1/outlook' backend/core/llm_agent/tools.py
  ```
  Expect **ZERO** hits. Run: `pytest tests/unit -q`.
- **Risk:** Medium — this is the pain-point-3 fix (tools HTTP-POSTing back to self). `execute_tool_locally` in `llm.py:595/615` already bypasses these registry tools, so the registry version is only reached via `ToolDispatcher` (`modules/radionics_operator.py`) and `operator.py /dispatch`; converting them removes the deadlock/serialization hazard.
- **Must not break:** the `TOOL_REGISTRY` mapping (`tools.py:1720`), the `NEMOTRON_FREE_MODEL_ID` default, the tool JSON schema at `tools.py:2174/2216`.

#### W2-PR3: Job budget vs Ultra — outlook never blocks the chat job
- **Title:** `fix(chat): outlook generation rides to_thread and returns within poll budget`
- **Files:**
  - `backend/app/api/v1/endpoints/llm.py` (verify `generate_single_outlook`/`generate_epic_outlook` cases at `:595/615` already use `asyncio.to_thread` — they do; if the chat-job `wait_for` around the whole turn is ≤ 25s and Nemotron takes minutes, **raise the per-turn budget for generation tools only** so a completed result isn't discarded)
  - `tests/integration/test_server.py` or a focused `tests/unit/test_chat_job_budget.py`
- **Acceptance test:** a chat request that triggers `generate_single_outlook` returns `status: completed` with a non-empty `narrative` (not a discarded/timeout) when the mock generate sleeps 30s. Run: `pytest tests/integration/test_server.py -k chat -q`.
- **Risk:** Medium — touching the job-budget timing. Keep the budget change scoped to generation tools; do not shorten health/heartbeat intervals.
- **Must not break:** the 300s poll timeout in `CommandCenter.tsx:798`, the `wait_for` used for fast tools.

#### W2-PR4: `model_used` is what ran (surfaced end-to-end)
- **Title:** `feat(chat): debug_info.model/provider are the values that actually ran`
- **Files:**
  - `backend/app/api/v1/endpoints/llm.py` (ensure the chat `debug_info` `model`/`provider` are read from the registry's recorded provider, not the requested hint)
  - `frontend/src/components/UI/CommandCenter.tsx` (already reads `dbg?.model` / `dbg?.provider` at `:894/911` — no change if backend is truthful)
- **Acceptance test:** unit test asserting `debug_info["model"]` equals the provider the registry selected (stub registry), not the user-requested slug when `auto` is chosen. Run: `pytest tests/unit -q`.
- **Risk:** Low — surfacing, not routing.
- **Must not break:** the cost computation `computeCostUsd` keyed on `modelId`.

---

### W3 — Surface trim

#### W3-PR1: Primary nav per job (Operations stops being a second Command Center)
- **Title:** `ui(nav): one sitting surface (Command Center), one narrative surface (Outlook), one radionics surface (Operations)`
- **Files:**
  - `frontend/src/lib/routes.ts` (route labels/grouping)
  - `frontend/src/components/UI/OperationsPanel.tsx` (remove/rehome the `TimeCycles` embed at `:908` and any chat-like controls)
- **Acceptance test:** `cd frontend; npx vitest run` + `npx tsc --noEmit`. Manual: Operations shows rates/scalar/broadcast only; no "type an intention here" input.
- **Risk:** Medium (UI only). Needs a quick visual check via Playwright.
- **Must not break:** `/operations` route load, the `TimeCycles` component consumers (`frontend/src/components/UI/TimeCycles.tsx`), `no-orphan-components` test.

#### W3-PR2: Clock naming (Time Cycles vs Cosmic Clock)
- **Title:** `ui(naming): disambiguate "Cosmic Clock" (astrology) from "Time Cycles" (planetary-hour)`
- **Files:**
  - `frontend/src/lib/routes.ts` (`{ key: 'astrology', label: 'Cosmic Clock' }` at `:54`)
  - `frontend/src/components/UI/TimeCycles.tsx` (header copy)
- **Acceptance test:** `npx vitest run` (copy-only, no type change). Manual: two distinct labels in the nav, no duplicate "clock" confusion.
- **Risk:** Trivial — copy strings.
- **Must not break:** any test asserting route labels (`frontend/src/__tests__/`).

#### W3-PR3: `apiUrl()` sweep (ADR 004 completion)
- **Title:** `refactor(frontend): convert remaining raw /api/v1 fetches to apiUrl()`
- **Files:** the ~23 violating files found by grep (`frontend/src/stores/commandStore.ts`, `stores/audioStore.ts`, `hooks/useWebSocketStable.ts`, `App.tsx`, `components/2D/AspectChart.tsx`, `components/UI/AstrologyExtractionPanel.tsx`, `routes/Practice/ScalarTab.tsx`, `components/Settings/ProviderSettings.tsx`, `components/UI/GuidedRitualFlow.tsx`, `components/UI/GrimoirePanel.tsx`, `routes/Buddhas/index.tsx`, `components/UI/EsotericTutor.tsx`, `components/UI/DharmaTales.tsx`, `components/UI/CommandCenter.tsx`, `components/UI/TTSSettingsPanel.tsx`, `components/UI/TransitComparison.tsx`, `components/UI/SynastryViewer.tsx`, `components/UI/SessionTimeline.tsx`, `components/3D/RadionicsGlobe.tsx`, `components/UI/OutlookDashboard.tsx`, `components/3D/Astrocartography.tsx`, `components/UI/NarrativeTTSPlayer.tsx`, `components/UI/JourneyCard.tsx`)
  - Add a regression test `frontend/src/__tests__/no-raw-api-fetch.test.ts` that fails if `fetch(\`/api/v1` or `fetch('/api/v1` appears under `src/` outside `utils/api.ts`.
- **Acceptance test:** `cd frontend; npx vitest run` (new guard passes); `npx tsc --noEmit`. Manual: build + one live route fetch through the proxy.
- **Risk:** Low per-file, mechanical. Do it in one PR but one commit per file.
- **Must not break:** `apiUrl()` itself, `resolveWsUrl()`/`BACKEND_URL` (kept for the `/ready` check), `VITE_API_BASE` override.

#### W3-PR4: OutlookDashboard leftover fetches
- **Title:** `refactor(outlook): OutlookDashboard uses apiUrl() everywhere`
- **Files:** `frontend/src/components/UI/OutlookDashboard.tsx` (lines `:430-434`, `:464`, `:520`, `:535`, `:565`, `:573`, `:761`, `:849`, `:903`, `:948`, `:988`, `:999`)
- **Acceptance test:** subsumed by W3-PR3's `no-raw-api-fetch` guard; this PR is the OutlookDashboard slice. Run `npx vitest run`.
- **Risk:** Low — mechanical; keep the defensive `unwrap()` envelope handling at `:442-451`.
- **Must not break:** background loop start/stop toggling, video poll-to-file state machine.

> **Note:** W3-PR4 is a strict subset of W3-PR3. If W3-PR3 lands first, W3-PR4 is dropped. Keep W3-PR4 only if you want to ship the Outlook fix before the full sweep.

---

### W4 — Honesty + hygiene

#### W4-PR1: Label simulated sensors as models
- **Title:** `fix(honesty): GV / stick plate / scalar viz labeled as models, not measurements`
- **Files:**
  - `core/radionics_engine.py` (the GV meter at `:282-354` derives `base_gv` from `self.rng.generate(...)` — add a docstring/`source: "model"` field to the returned dict)
  - `backend/core/llm_agent/tools.py` (`measure_general_vitality` at `:1498`) and `core/radionics_tools.py:161` (tool description: prepend "**Modeled estimate**, not a physical measurement.")
  - `frontend/src/components/UI/BroadcastPanel.tsx` (`:77` "Stick Plate State", `:511` "Stick Plate Resonance" — label "simulated")
  - `docs/FEATURES_REFERENCE.md:33` (rewrite the GV bullet to say "modeled")
- **Acceptance test:** `grep -rn "General Vitality (GV)" docs/FEATURES_REFERENCE.md` shows "modeled"; `pytest tests/core/test_radionics_engine.py -q` (GV range tests still pass). Manual: BroadcastPanel visibly labels the stick plate "simulated".
- **Risk:** Low — copy + a `source` field (additive).
- **Must not break:** `tests/core/test_radionics_engine.py` GV range/interpret buckets, the `radionics_operation.py --with-gv` CLI.

#### W4-PR2: Population seed dedup
- **Title:** `fix(populations): dedupe by name on insert so repeated seeding can't duplicate`
- **Files:**
  - `backend/core/services/population_manager.py` (add an upsert-by-`(name.lower())` guard in `create_population`, or a one-time migration dedup)
  - `tests/backend/test_population_manager.py` (or existing population tests)
- **Acceptance test:**
  ```python
  def test_create_population_dedupes_by_name(pm):
      first = pm.create_population(name="California", ...)
      second = pm.create_population(name="california", ...)  # case-insensitive
      assert second.id == first.id
  ```
  Run: `pytest tests/backend -q` (or wherever population tests live). Expect PASS.
- **Risk:** Medium — read-path dedup already exists (`llm.py:269-304`); moving it to insert-time changes persistence. Confirm no caller relies on exact-duplicate creation.
- **Must not break:** `list_populations` dedup (becomes a no-op safeguard), `create_population` return shape `pop.to_dict()`.

#### W4-PR3: Doc / CI drift
- **Title:** `docs: reconcile ARCHITECTURE.md, geo defaults, and DB-path resolution`
- **Files:**
  - `docs/ARCHITECTURE.md` (router count claim "30/32" vs `api.py` actual, WS message-count claim, service table)
  - `frontend/src/lib/geo.ts` vs `config/settings.py` (both SF `37.7749/-122.4194` — confirmed in sync; instead fix the **outlook default** `34.0522/-118.2437` in `backend/app/api/v1/endpoints/outlook.py:43-44`, `modules/outlook.py`, `tools.py` to reference the canonical default or a single named constant)
  - `backend/app/api/v1/endpoints/video_generation.py:74-89` and `image_generation.py:82-89` (collapse the two SQLite-path strategies — `VAJRA_DB_PATH` env + `vajra_stream.db` + `backend/app/vajra_stream.db` mirror — into one `core.schema.get_db_path()` call)
- **Acceptance test:** `python scripts/check_ghost_paths.py` green; `ruff check .` green; `pytest tests/unit/test_docs_no_ghost_paths.py -q` green. No new path references.
- **Risk:** Low-Medium — the DB-path unification is the only behavioral change; keep it behind `core.schema.get_db_path()`.
- **Must not break:** `tests/integration/test_extraction.py` (sets `DATABASE_URL`), `tests/unit/test_settings_shim.py`.

---

## D. Sequence

```
W1-PR1 (idempotent working) ──► W1-PR2 (stop dup auto-chain) ──► W1-PR3 (cards-first)
        │
W2-PR1 (one generate path) ──► W2-PR2 (in-process tools) ──► W2-PR3 (job budget) ──► W2-PR4 (truthful model_used)
        │                              ▲
        └── both unblock "one sitting → one folio → one outlook"

W3-PR1 → W3-PR2 → W3-PR3 (→ W3-PR4 optional)        [independent, ships any time]
W4-PR1 → W4-PR2 → W4-PR3                            [independent, ships any time]
```

- **What unblocks what:** W1-PR1 (idempotency) + W2-PR2 (in-process tools) jointly unblock W1-PR2's "no duplicate auto-chain" (the auto-chain can only be reliably stopped once it can't mint dupes via two tool paths). W2-PR1 unblocks W2-PR4 (truthful model_used) and W2-PR3 (job budget needs the single path to reason about timing).
- **What ships independently to the other machine via `origin/main`:** W3 (all of it), W4-PR1, W4-PR2, W4-PR3 — none depend on W1/W2. Merge them whenever green; the other machine just pulls `main`.
- **Order within a machine:** land W1 and W2 first (the sitting loop is the product core), then fold in W3/W4 as they complete.

---

## E. Explicit non-goals

- **No idle-game / "ops-per-second swarm of purifying agents"** inside `modules/` or Operations — that is a sibling product, not a tab.
- **No third `AudioService`** — respect ADR 001 (`vajra_service` HTTP/WS vs `container.audio` LLM-tool).
- **No new `API_BASE` constant** — `apiUrl()` only (ADR 004).
- **No expanding blessing-loop LLM spend** — do not widen `start_blessing_loop`/`generate_next_blessing` frequency or model tier; the only budget work is making outlook return within the existing poll budget (W2-PR3).
- **No new router** — everything lands in existing routers or is deleted.
- **No rewriting `core/working.py` or `core/outlook_generator.py` wholesale** — additive idempotency + truthful-readback only.

---

## F. First week — 3 PRs, each mergeable alone

1. **W1-PR1 — Idempotent `run_working`** (foundation)
   - Verify: `pytest tests/core/test_working.py -q` (idempotency test added, existing pass); then live: `python run.py full`, open Command Center, send "begin a working for peace", send the *same* line again within 60s → **one** `wrk_*` card, second response shows the same `working_id`.
2. **W2-PR2 — In-process outlook tools** (kill self-HTTP)
   - Verify: `grep -rn '_post("/api/v1/outlook' backend/core/llm_agent/tools.py` → zero; `pytest tests/unit -q`; live: send "generate an outlook blessing" in Command Center → outlook card renders, no deadlock, chat job completes.
3. **W1-PR2 — Stop the duplicate auto-chain** (the actual sitting-loop fix)
   - Verify: `pytest tests/unit -q` + live sitting: one message "cast an outlook for all beings" produces **one** `generate_single_outlook` card and **zero** duplicate `run_working`/outlook re-mints; `GET /operator/workings` shows a single new folio.

**Each PR's full verify gate:** `ruff check .` → `ruff format --check .` → `pytest tests/ -m "not slow" --ignore=tests/e2e --tb=short -q` (backend) → `cd frontend; npx vitest run` (frontend, for frontend PRs) → one live Command Center sitting + one Outlook generate.
