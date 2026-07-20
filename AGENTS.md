# AGENTS.md — Vajra.Stream

Guidance for AI agents working in this repo. Repo facts only; verify against
the listed files before relying on any command or claim.

## Stack

- **Backend:** Python 3.10–3.13, FastAPI, SQLAlchemy, Pydantic v2, `sounddevice`.
  Python 3.14+ is unsupported (some packages don't have wheels yet).
- **Frontend:** React 18 + TypeScript + Vite, Tailwind CSS + Ant Design,
  Three.js (`@react-three/fiber`/`drei`), Zustand, Recharts.
- **Storage:** SQLite at `vajra_stream.db` (mirrored to `backend/app/vajra_stream.db`).

## Canonical Entry Points

Use these — the legacy `main_*.py` variants and "deleted entrypoint" comments
were removed (see "Ghost paths" below).

| Action | Command | Notes |
|---|---|---|
| Start everything | `python run.py full` | Backend on `:8008`, frontend on `:3009`. Polls `/health` first. |
| Backend only | `python run.py serve [--port N]` | FastAPI app from `backend/app/main.py`. |
| Frontend only | `python run.py frontend` | Vite dev server on `:3009`. Requires `frontend/node_modules`. |
| Status / test / install | `python run.py {status,test,install}` | Wrapper around the items below. |
| Windows shortcut | `vajra.bat serve` etc. | Activates `.venv\Scripts\python.exe` if present, else falls back to system `python`. |

`run.py` runs pre-flight checks (deps + `npm install`) before `serve`/`frontend`/`full`.
The pre-flight is cached via `.vajra_preflight_ok` and invalidates when
`requirements.txt` or `frontend/package.json` change.

## Repository Layout

- `backend/app/main.py` — the only FastAPI app. Lifespan splits startup into a
  critical path (DB schema init) and a fire-and-forget warmup task
  (orchestrator bridge, LLM registry, health heartbeat, streaming, autonomous
  operator, practice engine pre-warm, outlook background generation). Failures
  in warmup are logged but never block the server.
- `backend/app/api/v1/api.py` — registers all 30 endpoint routers under
  `/api/v1/*`. **Add new endpoint modules here**; otherwise they are unreachable.
- `backend/app/api/v1/endpoints/*.py` — one router file per feature area
  (astrology, audio, radionics, sessions, tts, llm, ...).
- `backend/core/services/` — backend-internal services. The user-facing audio
  subsystem lives here (`vajra_service.py:VajraStreamService` singleton at
  L774 — see ADR 001).
- `modules/` — service layer exposed via the DI container (see `modules/README.md`).
  All service classes take `event_bus` as their first constructor argument.
- `core/` — processing engines (44 files; `core/audio_generator.py`,
  `core/enhanced_audio_generator.py`, `core/astrology.py`, `core/schema.py`, ...).
- `container.py` (project root) — singleton DI container. **There is no
  `backend/app/container.py`** despite what older docs may imply.
- `infrastructure/event_bus.py` — `SimpleEventBus` / `EnhancedEventBus`.
- `config/settings.py` — runtime defaults (audio sample rate, prayer-bowl mode,
  default coordinates `37.7749, -122.4194` — mirrored in `frontend/src/lib/geo.ts`).
- `tests/{unit,integration,e2e,backend,core}/` — no `test_*.py` lives at
  `tests/` root (structural rule; see `tests/unit/test_docs_no_ghost_paths.py`).

## Architecture Decisions That Matter

These are recorded as ADRs in `docs/decisions/`; respect them.

- **ADR 001 — Audio subsystem canonical.** Two distinct concerns coexist and
  must not be conflated:
  - `backend/core/services/vajra_service.py:VajraStreamService` (singleton
    `vajra_service`) — backs all `/api/v1/audio/*` HTTP routes AND all
    websocket audio paths. The generalist "service wrapper" for audio.
  - `modules/audio.py:AudioService` — separate LLM-tool path. Wired through
    `container.audio` and consumed by `RadionicsOperator` only. Different
    constructor signature, different engines.
  - Do **not** introduce a third class named `AudioService`.
- **ADR 002 — Settings canonical.** `config/settings.py` is the single source;
  `backend/app/config.py` is a shim.
- **ADR 003 — Orchestrator canonical.** `backend/core/orchestrator_bridge.py`
  is the single bridge into the legacy `container.py` DI graph.
- **ADR 004 — Frontend URL strategy.** Always proxy-relative:
  `import { apiUrl } from './utils/api'; fetch(apiUrl('/foo'))`.
  Vite dev proxy (`frontend/vite.config.ts:10-18`) forwards `/api` and `/ws`
  to `http://localhost:8008`. In production, a reverse proxy must do the same.
  The hardcoded `${API_BASE} = http://${hostname}:8008/api/v1` pattern is
  gone — adding it back reintroduces the doubled-prefix bug class
  (e.g. `/api/v1/api/v1/...`).
  - Build-time override: `VITE_API_BASE=https://api.example.com npm run build`
    (build only; no `.env*` files exist in `frontend/`).
  - One implementation detail: `apiUrl()` is defined in
    `frontend/src/utils/api.ts`. Don't create parallel `API_BASE` constants.

## Install / Run

```bash
# Backend deps — minimum that the smoke test needs
pip install -r requirements-minimal.txt

# Full stack + LLM extras
pip install -r requirements.txt

# Dev tooling (ruff, mypy, pytest plugins, pre-commit)
pip install -r requirements-dev.txt

# Astrology extras (Vedic/Chinese). Required by /api/v1/astrology/* —
# without them core/astrology.py raises ImportError and endpoints silently
# drop the western/indian/chinese keys.
pip install vajra-stream[astrology]
# or: pyswisseph>=2.10.3.2 lunar-python>=1.4.8

# DB schema (one-time)
python scripts/setup_database.py

# Frontend (one-time)
cd frontend && npm install
```

Linux CI also installs `libportaudio2`, `libsndfile1`, `ffmpeg` — required by
`sounddevice`/`soundfile`/pydub. On Windows they ship with the wheels.
On macOS: `brew install portaudio`.

## Verify

Order matters. Run from the project root unless noted.

```bash
# 1. Lint (CI gate)
ruff check .
ruff format --check .

# 2. Type check (loose; module dirs override to ignore_missing_imports)
mypy .

# 3. Tests — split because e2e needs live LM Studio / Postgres
pytest tests/ -m "not slow" --ignore=tests/e2e --tb=short -v

# 4. Frontend unit tests
cd frontend && npx vitest run

# 5. Frontend e2e (Playwright; needs `npx playwright install chromium` once)
cd frontend && npx playwright test
```

CI runs the same on `ubuntu-latest` with Python 3.11 (`.github/workflows/ci.yml`).

### Test quirks worth knowing

- `tests/conftest.py` has an **autouse** fixture that stubs
  `GeocodingService.get_coordinates_and_timezone` with a canned dict
  (London, Paris, New York, Tokyo, New Delhi, San Francisco, Beijing, Mumbai)
  plus a `(0.0, 0.0, "UTC")` fallback for unknown cities and an
  explicit "not found" for anything starting with `Xyzzy`. This avoids the
  real Nominatim rate limit. Don't remove it — chart-creation tests will
  start flaking.
- Markers: `unit`, `integration`, `e2e`, `slow`. `asyncio_mode = "auto"` —
  no need to decorate `async def test_*` with `@pytest.mark.asyncio`.
- `tests/integration/test_server.py` boots the real FastAPI app via
  `TestClient(app)`; it imports a lot, so it's the slow integration suite.
- `tests/e2e/test_*_lm_studio.py` requires a live LM Studio on localhost and
  is **skipped** (not failed) when unreachable.

## Frontend Conventions

- **Styling split** (see `docs/frontend-styling-guide.md`):
  - Tailwind: layout, spacing, color utilities, typography, animations, and
    custom primitives like `.glassmorphism`, `.vajra-button-*`.
  - Ant Design: interactive widgets (`Table`, `Modal`, `Drawer`, `Form`,
    `Select`, `DatePicker`, `Tabs`, `Popconfirm`, toasts).
  - **Brand colors** live in `frontend/src/lib/colors.js` (single source of
    truth) and are mirrored to CSS variables (`globals.css`), Tailwind tokens
    (`tailwind.config.js`), and AntD `ConfigProvider` tokens (`App.jsx`).
    Change the source, then mirror.
- **State:** Zustand stores under `frontend/src/stores/` (one per domain:
  audioStore, commandStore, crystalStore, rateStore, uiStore, practiceStorage).
- **Path alias:** `@/` → `frontend/src/` (configured in `vitest.config.ts`).
- **Vendor chunks:** `vite.config.ts` splits `react`/`antd`/`three`/`recharts`/
  `lucide-react` into separate bundles for cache hits. Keep this when adding
  deps so the initial parse cost stays bounded.
- **No orphan components:** `frontend/src/__tests__/no-orphan-components.test.ts`
  enforces no unused exports in `src/components/`. Run `npx vitest run` after
  adding components.

## Guardrails (will fail CI / tests if violated)

- **No new ruff suppressions.** `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`
  is frozen empty. `tests/unit/test_no_new_ruff_suppressions.py` snapshots at
  0/0 entries and 0/0 ignored codes. Do not add `ignore = [...]` lines.
- **No `test_*.py` at `tests/` root.** `test_docs_no_ghost_paths.py` enforces
  it. Put every test under `unit/`, `integration/`, `e2e/`, `backend/`, or `core/`.
- **No ghost documentation paths.** Several legacy `README.md`s contain
  HTML comments marking removed sections (`<!-- removed: ... ghost path per
  remediation-18 / Issue 5.8 -->`). If you add a doc link, make sure the
  target file exists.
- **No `as any` / `@ts-ignore` / `@ts-expect-error`.** TypeScript strictness
  is enforced; widen the type instead.
- **Pre-commit hooks** (`.pre-commit-config.yaml`): ruff + ruff-format on
  commit; ruff pinned to `v0.4.4` for the hook regardless of local ruff
  version.

## Smoke Test (no hardware, ~30s)

```bash
python scripts/run_blessing.py --duration 30
# Expect: a gentle multi-harmonic prayer-bowl hum through the speakers.
python scripts/run_blessing.py --intention "May all beings be happy" --duration 300
python scripts/run_blessing.py --mode healing --chakra heart --duration 600
python scripts/run_blessing.py --continuous   # until Ctrl+C
```

Other useful one-shot scripts in `scripts/`:
- `radionics_operation.py --preset world_peace --duration 3600`
- `setup_database.py` (initial DB schema)
- `scalar_wave_benchmark.py --method all --duration 3`

## PowerShell (Windows) Notes

The default shell here is `powershell` (5.1). Three things that bite:

- `&&` is **not** supported. Chain with `cmd1; if ($?) { cmd2 }`.
- `cd` inside a piped/command-block resets. Use the `workdir` parameter on
  tools instead of `Set-Location` followed by another command.
- Quote any path with spaces; prefer full cmdlet names
  (`Get-ChildItem`, `Set-Content`, `Remove-Item`) over aliases.

## When Something Goes Wrong

- **Astrology endpoint returns no `western`/`indian`/`chinese` keys** — install
  `pyswisseph` and `lunar-python`; see ADR-style note in `README.md` and
  `requirements-minimal.txt` comments.
- **Audio import errors in tests** — install system PortAudio (`libportaudio2`
  on Debian/Ubuntu, `brew install portaudio` on macOS).
- **`vajra_service.event_bus` not wired** — `backend/app/main.py` lifespan
  wires it to `container.event_bus` during warmup. If you see events not
  reaching the autonomous agent or WS broadcast, check the warmup order:
  orchestrator bridge → `vajra_service.event_bus = container.event_bus` →
  LLM registry → health heartbeat → streaming → autonomous operator.
- **Doubled-prefix 404s in the frontend** — you reintroduced an absolute
  `API_BASE`. Use `apiUrl()` from `frontend/src/utils/api.ts` (ADR 004).
- **Geocoding tests flake** — do not remove the autouse fixture in
  `tests/conftest.py`; the real Nominatim rate-limits at ~1 req/s.

## Out-of-scope / do not assume

- No `opencode.json` in this repo (no extra instruction sources to merge).
- No `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, or
  `.github/copilot-instructions.md` existed before this file.
- `.omo/`, `.kilo/`, and `.codegraph/` are tool-local scratch spaces; do not
  commit their contents.
- `ai_integration_project/`, `scratch/`, and `generated/` are excluded from
  ruff and mypy — leave them alone unless explicitly asked.
