# Notepad: astrology-extraction-sweep

> Inherited wisdom for subagents working on this plan.

## Project Conventions

- **Python style**: 3.10+ syntax allowed (the project uses 3.10-3.13 per README). Use rom __future__ import annotations if helpful.
- **Imports**: grouped (stdlib, third-party, local). Absolute imports throughout.
- **Logging**: use the logger = logging.getLogger(__name__) pattern, not print().
- **Pydantic models**: used for API request/response shapes. Use Field(...) for constraints.
- **Tests**: pytest with markers. Reference fixtures in 	ests/test_astrology.py:11-19.
- **Frontend**: React + Ant Design. Use lazy() for big components (pattern in AstrologyPanel.jsx:20-32).
- **Commits**: Conventional Commits. One commit per task.

## Architectural Constraints (from Metis + Prometheus)

- **DO NOT** extend the per-endpoint init_db() pattern. New tables go through core/schema.py only.
- **DO NOT** add new top-level routes or sidebar entries. The Extraction panel lives inside AstrologyPanel.jsx.
- **DO NOT** call narrative-generation LLMs in the batch path. The batch tool computes structured data only.
- **DO NOT** break SavedChart CRUD � new tables are additive.
- **DO NOT** add authentication in this iteration.

## Pre-existing Code to Reuse

- core/astrology.py � AstrologicalCalculator with reusable methods (get_planetary_positions, get_moon_phase, get_julian_day, etc.)
- core/astrology.py:11 � import swisseph as swe � Swiss Ephemeris is the ephemeris library.
- ackend/app/api/v1/endpoints/astrology.py � pydantic request model pattern + SavedChart CRUD pattern.
- rontend/src/components/UI/NarrativeTTSPlayer.jsx � modern Ant Design + state pattern.
- rontend/src/components/UI/AstrologyPanel.jsx:20-32 � lazy() import pattern.

## Evidence File Convention

For every task, save QA scenario outputs to .omo/evidence/task-N-{scenario-slug}.txt:
- .omo/evidence/task-1-fresh-db-tables.txt
- .omo/evidence/task-2-imports.txt
- .omo/evidence/task-15-batch.txt

## Append Findings

When a subagent discovers a non-obvious gotcha, an unexpected constraint, or a better-than-planned approach, append a dated entry to this file (never overwrite):
\\\
## [2026-06-02] Task 5: discovered
...finding...
\\\

## Issues (blockers, broken assumptions)

See issues.md � append if you hit a blocker.

## [2026-06-02] Task 1: discovered

- **`init_db()` exists in 3 endpoint files, not just `astrology.py` and `outlook.py`**: `agent_suggestions.py` uses a function called `init_tables()` (not `init_db()`) for `failed_tool_calls` + `intentional_paths`. Same anti-pattern, same fix — refactored to delegate to `core.schema.init_db()`.
- **`core/compassionate_blessings.py:_initialize_database()`** is a fourth location that creates tables (`blessing_targets`, `blessing_sessions`, `mantra_dedications`) on every `CompassionateBlessingsSystem()` constructor call. Not an endpoint file, so out of scope for Task 1's "refactor endpoint init_db" requirement, but flagging it for a follow-up to also route through `core.schema.init_db()`. Leaving it alone to avoid expanding Task 1's scope.
- **`init_db()` for the project root DB lives at the project root** (`vajra_stream.db`), not in `backend/`. The pre-existing `get_db_path()` helpers in endpoint files all do `Path(__file__).parent.parent.parent.parent.parent` walks to find it. `core/schema.py: get_db_path()` does the same project-root walk via `get_project_root()`. The two paths agree, so the delegation is safe.
- **`_schema_version` row is recorded ONLY on a fresh DB or when the version bumps.** Re-running `init_db()` does not insert a duplicate row. The QA "idempotent" scenario verifies exactly 1 row in `_schema_version` after 3 consecutive runs.
- **Pre-existing `outlook_narratives` had 37 rows, `blessing_targets` had 7, `user_preferences` had 4** in the project's live DB before the migration. All survived untouched. Other pre-existing tables had 0 rows.
