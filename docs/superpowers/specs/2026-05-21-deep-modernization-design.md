# Vajra.Stream Deep Modernization

**Date**: 2026-05-21
**Scope**: Test suite, project tooling, git hygiene, CI, code quality

## Problem

The repository has grown organically and shows several issues:
- 23 test files, most are scratch/debug scripts using `print()` + `assert` instead of proper pytest
- No `pyproject.toml` — just a flat `requirements.txt` with 80+ undifferentiated dependencies
- No linter, formatter, or type checker configured
- `__pycache__/` dirs and other artifacts tracked in git
- No CI pipeline
- `sys.path.insert()` hacks throughout codebase
- Overlap between `core/` and `modules/` directories with unclear ownership

## Design

### 1. pyproject.toml

Add a `pyproject.toml` at project root with:

- `[project]` metadata (name, version, requires-python, dependencies grouped as core/web/audio/science/dev)
- `[tool.ruff]` configuration (line-length=120, select=E/F/W/I/UP, per-file ignores for tests)
- `[tool.mypy]` configuration (python_version="3.10", strict=False, per-module overrides)
- `[tool.pytest.ini_options]` configuration (testpaths, markers, asyncio_mode)
- `[tool.coverage.run]` configuration (source dirs, omit patterns)

Keep `requirements.txt` as a backward-compat export. Add `requirements-dev.txt` for dev tooling.

### 2. Ruff (lint + format)

Replace `black` and `flake8` with `ruff`. Configuration:
- Line length: 120
- Rule selection: E, F, W, I (isort), UP (pyupgrade)
- Per-file ignores for test files (D, ANN)
- Exclude: `frontend/`, `generated/`, `.venv/`, `node_modules/`

### 3. mypy

- `python_version = "3.10"`
- `strict = False` globally
- Per-module overrides for dynamic modules (`modules/*.py`, `core/*.py`)
- Exclude generated files and frontend

### 4. pytest Configuration

**Markers**: `unit`, `integration`, `slow`

**conftest.py** fixtures:
- `event_bus()` — fresh `SimpleEventBus` per test
- `fresh_container()` — container with reset after test
- `tmp_output_dir()` — temporary directory for generated files, cleaned up after test

### 5. Test Suite Overhaul

**Keep and rewrite as proper pytest** (6 files):

| Original File | New Name | Key Tests |
|---|---|---|
| `test_monolith.py` | `test_container_modules.py` | Container loads all modules, scalar waves generate, radionics broadcasts, anatomy loads, blessings generate |
| `test_foundation.py` | `test_event_bus.py` | Event bus subscribe/publish/persist, crystal service, blessing router, enhanced scalar waves, config |
| `test_basic_functionality.py` | `test_services.py` | Container init, visualization, anatomy, audio, API imports |
| `test_rng_service.py` | `test_rng_service.py` | RNG session lifecycle, reading validation, session summary |
| `test_radionics_enhancer.py` | `test_radionics_enhancer.py` | Radionics enhancer functionality |
| `test_server.py` | `test_server.py` | FastAPI app creation and basic routes |

**Delete** (16 scratch/debug files):
- `test_fixed3_connection.py`, `test_fixed4_connection.py`
- `test_minimal_connection.py`, `test_module_connections.py`
- `test_implementation_simple.py`, `test_integration_simple.py`
- `test_websocket_minimal.py`, `test_websocket_simple.py`
- `test_new_implementation.py`, `test_full_integration.py`
- `test_integration_phase2.py`, `test_integration.py`
- `test_rng_api.py`, `test_tts_system.py`, `test_visualization.py`
- `test_api_endpoints.py`

### 6. Git Hygiene

**Update `.gitignore`**:
- Add `.venv/` (missing — only `venv/` was there)
- Add `.kilo/`
- Add `backend_server.err`, `backend_server.log`
- Ensure `__pycache__/` is covered (already there)
- Add `*.pyc` explicitly (only `*.py[cod]` pattern currently)

**Remove from git tracking** (not from disk):
- All `__pycache__/` directories
- `backend_server.err`, `backend_server.log`
- `vajra_stream.db` (already gitignored but may be tracked from before)

**Add `.gitattributes`**:
- `* text=auto` for consistent line endings
- `*.py text eol=lf`
- `*.bat text eol=crlf`

### 7. CI — GitHub Actions

`.github/workflows/ci.yml`:
- **Trigger**: push to main, PRs to main
- **Matrix**: Python 3.10, 3.11, 3.12
- **Steps**:
  1. Checkout
  2. Set up Python (from matrix)
  3. Install dependencies (`pip install -e ".[dev]"`)
  4. Ruff check
  5. Ruff format --check
  6. mypy
  7. pytest with coverage
- **Caching**: pip cache keyed on requirements hash

### 8. pre-commit

`.pre-commit-config.yaml`:
- ruff (lint + format)
- trailing whitespace fixer
- end-of-file fixer
- yaml/toml check
- no-commit-to-branch (protect main)

### 9. Code Quality Pass

**Remove `sys.path.insert()` hacks** from:
- All test files
- `container.py`
- `backend/app/main.py`
- `vajra_stream_v2.py`

Instead, rely on `pip install -e .` from pyproject.toml which puts the project on the path properly.

**Document `core/` vs `modules/` ownership**:
- `modules/` is the canonical location for service modules (used by container.py)
- `core/` contains internal implementations, rendering engines, and shared utilities
- Add `modules/README.md` and `core/README.md` documenting this

**Type hints on container.py** — add return type annotations to all properties

## Out of Scope

- Moving to `src/` layout (too disruptive to imports)
- Rewriting module logic
- Refactoring module interfaces or event system
- Frontend changes
