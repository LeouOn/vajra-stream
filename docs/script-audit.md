# `scripts/` Audit — 2026-09-14

Inventory + recommendations for the contents of `scripts/`. Generated from
`git log --since="6 months ago"`, AST parsing, and grep across the repo for
references. **No files were deleted by this audit** — it is a report only,
to be acted on later.

## Summary

After the 2026-09-14 sweep, `scripts/` holds 25 files (~9,200 lines).
**10 are live dependencies or have clear keepers status**; the other **15
are candidates for deletion**, accounting for ~5,800 lines (~63% of
`scripts/`).

| Bucket | Count | Lines | Action |
|---|---|---|---|
| Documented entries (referenced in `README.md` / `AGENTS.md` / `START_HERE.md` / `OPERATIONS_GUIDE.md`) | 6 | 2,027 | KEEP |
| Live import targets (imported by code outside `scripts/`) | 4 | 1,890 | KEEP |
| Recently active (≥2 commits in last 6 months, has docstring, clear purpose) | 3 | 1,371 | KEEP, review next audit |
| Suspicious cruft (no live use, stale, duplicates, missing docstrings) | 8 | ~3,300 | **DELETE (recommended)** |
| Feature-coupled utilities (could be tied to a feature; ask before delete) | 5 | ~2,683 | ASK before delete |

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

## DELETE recommended — 8 files (~3,300 lines)

| File | Lines | Why delete |
|---|---|---|
| `scripts/integrated_blessing.py` | 138 | Duplicates `run_blessing.py` (combined prayer bowl + visuals demo). 1 commit in last 6mo (style-only). |
| `scripts/holistic_blessing_run.py` | 197 | Demo script (the docstring literally says "Demonstrates the integration of…"). 3 commits in last 6mo but all style-only. No live import. |
| `scripts/verify_narratives.py` | 39 | No docstring, no live import. 1 commit 4mo ago. |
| `scripts/audit_modules.py` | 124 | Module-import check that's been superseded by pytest's collection. No live import. 1 commit 4mo ago. |
| `scripts/astrocartography_analysis.py` | 525 | CLI analysis tool, last touched May 2026 for a style pass. No live import, no docs reference. |
| `scripts/radionics_analysis.py` | 384 | CLI radionics analysis, same story as above. |
| `scripts/vajra_stream_ui.py` | 481 | Terminal UI demo (`rich` + `questionary`). No live import, no docs reference. 2 style-only commits in 6mo. |
| `scripts/generate_iching_data.py` | 1128 | **1128-line file with no module docstring** — code smell. Generates iching (易經) test data, no live import. Last touched July 2026. |

## ASK before delete — 5 files (~2,700 lines)

These could be tied to a feature I don't know about. Ask the user/feature
owner before removing.

| File | Lines | What it does | Last touched |
|---|---|---|---|
| `scripts/blessing_manager.py` | 584 | Compassionate Blessing Manager CLI — manages blessing targets and dedicates mantras. Imported by no one now (was previously imported by `radionics_operation.py`). | 2026-05-21 |
| `scripts/tts_narrator.py` | 362 | TTS narrator CLI for blessing stories/mantras/meditations. May be superseded by `core/tts_integration.py`. | 2026-05-30 |
| `scripts/seed_chinese_lore.py` | 701 | Populates `CharacterManager` + `LocationManager` with Chinese mythological figures. Uses the proper API. | 2026-05-26 |
| `scripts/create_test_populations.py` | 308 | Creates test populations (California, Myanmar, Congo) for the data-loading test. Likely a one-off dev utility. | 2026-05-26 |
| `scripts/direct_seed_chinese_lore.py` | 728 | **Bypasses `CharacterManager`/`LocationManager`** ("bypasses the CharacterManager/LocationManager entirely to guarantee persistence") — looks like a workaround. Duplicates what `seed_chinese_lore.py` does, but via direct file I/O. | 2026-05-26 |

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
