# `scripts/` Audit — 2026-09-14 (re-evaluated 2026-09-15)

Inventory + recommendations for the contents of `scripts/`. Generated from
`git log --since="6 months ago"`, AST parsing, and grep across the repo for
references. The 2026-09-14 report recommended deletions; the re-evaluation
and implementation happened 2026-09-15 (deletions are recorded below).

> **2026-09-15 re-evaluation:** verdicts re-derived against runtime evidence
> (committed data artifacts, live endpoint callers, test dependencies).
> Changes: `generate_iching_data.py` and `tts_narrator.py` moved to KEEP,
> both Chinese-lore seeders moved to KEEP (unique curated content),
> `create_test_populations.py` moved to DELETE-recommended (superseded by
> committed `knowledge/blessing_populations/*.json` + the importer).

## Summary

After the 2026-09-15 implementation sweep, `scripts/` holds **17 files**.
**14 are keepers**; **1 is pending owner confirmation** (`blessing_manager.py`).

| Bucket | Count | Lines | Action |
|---|---|---|---|
| Documented entries (referenced in `README.md` / `AGENTS.md` / `START_HERE.md` / `OPERATIONS_GUIDE.md`) | 6 | 2,027 | KEEP |
| Live import targets (imported by code outside `scripts/`) | 4 | 1,890 | KEEP |
| Recently active (≥2 commits in last 6 months, has docstring, clear purpose) | 3 | 1,371 | KEEP, review next audit |
| Provenance / content scripts (re-evaluated 2026-09-15) | 4 | ~2,900 | KEEP |
| Feature-coupled utility (could be tied to a feature; ask before delete) | 1 | 584 | ASK before delete |

## Definite KEEP — 10 files

### Documented entry points
- `scripts/setup_database.py` — one-liner wrapper around `core.schema.init_db`. Referenced in `AGENTS.md`, `README.md`, `START_HERE.md`, `OPERATIONS_GUIDE.md`.
- `scripts/run_blessing.py` — 5-channel prayer-bowl blessing CLI. Referenced in 4 docs.
- `scripts/radionics_operation.py` — full radionics broadcasting CLI. Referenced in `README.md`; also imported by `scripts/blessing_manager.py`.
- `scripts/scalar_wave_benchmark.py` — benchmarks all scalar-wave methods. Referenced in `README.md`.
- `scripts/unified_orchestrator.py` — imported by `backend/core/orchestrator_bridge.py:10` (live).
- `scripts/vajra_orchestrator.py` — referenced in `README.md`/`AGENTS.md` as the top-level CLI.

### Live imports from outside `scripts/`
- `scripts/audit_ws_contract.py` — referenced as a **CI guard** in `docs/ARCHITECTURE.md` ("scripts/audit_ws_contract.py"). 5 commits in last 6mo (actively maintained).
- `scripts/story_generator.py` — imported by `modules/blessings.py:33` (lazy import for the outlook/blessing feature).
- `scripts/import_blessing_populations.py` — 6 commits in last 6mo (active dev), loads blessing populations from JSON files into the DB.

### Recently active
- `scripts/generate_tarot_art.py` (1044 lines) — generates SVG art for the 78-card Rider-Waite deck; 2 commits in 6mo, well-documented.
- `scripts/run_88_buddhas_3x.py` (243 lines) — runs 3 cycles of the 88-Buddha liturgy; 3 commits, ties into `core/practice_engine.py`.
- `scripts/smoke_image_generation.py` (84 lines) — image-endpoint smoke test; 2 recent commits.

## DELETE recommended — 8 files (~2,200 lines) — **REMOVED 2026-09-15**

All 8 were deleted in the implementation sweep. Their filenames are locked
out of `PROJECT_STRUCTURE.md` by `tests/unit/test_docs_no_ghost_paths.py`.

| File | Lines | Why deleted |
|---|---|---|
| `scripts/integrated_blessing.py` | 138 | Duplicates `run_blessing.py` (combined prayer bowl + visuals demo). 1 commit in last 6mo (style-only). No cross-imports. |
| `scripts/holistic_blessing_run.py` | 197 | Demo script (the docstring literally says "Demonstrates the integration of…"). 3 commits in last 6mo but all style-only. No live import. |
| `scripts/verify_narratives.py` | 39 | Confirmed on read: bare ad-hoc `requests.post` probe against a running localhost backend; no docstring, no imports of it. |
| `scripts/audit_modules.py` | 124 | Module-import check that's been superseded by pytest's collection (135-file import sweep runs in every CI pass). No live import. |
| `scripts/astrocartography_analysis.py` | 525 | CLI analysis tool, last touched May 2026 for a style pass. No live import, no docs reference. |
| `scripts/radionics_analysis.py` | 384 | CLI radionics analysis, same story as above. |
| `scripts/vajra_stream_ui.py` | 481 | Terminal UI demo. **Confirmed broken**: line 429 shells out to `scripts/time_cycle_healer.py`, deleted in the 2026-09-14 sweep — its "Time Cycle" menu item fails at runtime. Superseded by the web frontend; the `run.py ui` command and its `START_HERE.md` / `OPERATIONS_GUIDE.md` bullets were removed alongside. |
| `scripts/create_test_populations.py` | 308 | Superseded: all blessing populations are committed as `knowledge/blessing_populations/*.json` (12 files) and loaded by the kept `import_blessing_populations.py`. No test references it (verified). |

## KEEP — 4 provenance/content scripts (re-evaluated 2026-09-15)

| File | Lines | Why keep (changed verdict) |
|---|---|---|
| `scripts/generate_iching_data.py` | 1128 | Writes `knowledge/iching.json`, which is **committed and loaded at runtime** by `/api/v1/divination/iching/cast`. Deleting it removes the provenance/regeneration path for load-bearing data. Mirrors the kept `generate_tarot_art.py` pattern. Follow-up: add a module docstring (only smell). |
| `scripts/tts_narrator.py` | 362 | Not superseded — it's the CLI layer over three live core modules (`core.blessing_narratives`, `core.time_cycle_broadcaster`, `core.tts_integration`). The lib alone has no CLI entry point. |
| `scripts/seed_chinese_lore.py` | 701 | Contains **unique curated content** (Chinese mythological figures/locations) that exists nowhere else in the repo. `CharacterManager` persists to `~/.vajra-stream/characters.json`, which feeds live `/api/v1/outlook` character endpoints; the store is currently empty on a fresh install, so this seeder is the only way to populate it. |
| `scripts/direct_seed_chinese_lore.py` | 728 | Same content rationale, direct-file variant (docstring says the manager path failed to persist historically). Keep until `seed_chinese_lore.py` is proven to persist reliably; consider extracting the shared lore data into `knowledge/` JSONs and collapsing the two scripts into one. |

## ASK before delete — 1 file

| File | Lines | What it does | Last touched |
|---|---|---|---|
| `scripts/blessing_manager.py` | 584 | Compassionate Blessing Manager CLI — manages blessing targets and dedicates mantras. Not imported by anything; overlaps with the HTTP surface (`/api/v1/blessings`, `blessing_targets`/`mantra_dedications` tables), but the mantra-dedication CLI flow may be unique. Wraps the kept `radionics_operation.py`. | 2026-05-21 |

## Already-removed (2026-09-14 sweep)

30 files / 3,603 lines were deleted in the same sweep that produced this
report. Categories:

- **TEST-IN-WRONG-PLACE (20)** — `test_*.py` in `scripts/` that should have
  been in `tests/` (e.g., `test_astrology_systems.py`, `test_async_chat.py`,
  `test_debug.py`, `test_full_stack.py`, `test_live_toolcall*.py`,
  `test_llm_operations.py`, `test_narratives.py`, `test_quick.py`,
  `test_statistics_loop.py`, `test_system_status.py`,
  `test_tool_calling_e2e.py`, `test_ui_e2e.py`,
  `audio_comparison_test.py`, `quick_test.py`, etc.).
- **AD-HOC-DEV (5)** — one-off investigation leftovers: `explore_improvements.py`,
  `demo_unified_system.py`, `visual_demo.py`, `smoke_task17.py`,
  `write_task17_evidence.py`.
- **ONE-OFF-RITUAL (5)** — dated rituals with no reuse value:
  `july4_ritual.py`, `venezuela_earthquake_prayer.py`,
  `full_ritual_broadcast.py`, `time_cycle_healer.py`,
  `universal_compassion_broadcast.py`.

## Stale docs references (action item, separate from deletion)

`docs/DEVELOPMENT.md` mentions three `scripts/` files that don't exist:
- `scripts/test_timing.py`
- `scripts/test_orchestration_cmd.py`
- `scripts/test_backend_peace.py`

(README.md's `scripts/test_prayer_bowl_audio.py` reference was already
fixed in the same sweep — the test now lives at
`tests/unit/test_prayer_bowl_audio.py` and is invoked via `pytest -m slow`.)

## How this audit was produced

```python
# Last-touched + commit count
git log --since="6 months ago" --oneline -- <file> | wc -l
git log -1 --format="%ci" -- <file>

# Docstring + main()/argparse presence
python -c "import ast, pathlib; tree=ast.parse(pathlib.Path('<file>').read_text()); print(ast.get_docstring(tree))"

# Cross-reference (find live imports)
grep -rln "scripts.<name>\|from scripts import <name>" --include='*.py' --include='*.md' .
```

Run again in 3-6 months for a refresh.
