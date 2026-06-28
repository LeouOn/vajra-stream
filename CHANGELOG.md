# Changelog

All notable changes to Vajra.Stream will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2026-06-20

### Added
- Route consolidation: 12 flat routes merged into 7 grouped routes (Command Center, Practice, Cosmic Clock, Outlook, Operations, Grimoire, Settings)
- UI/UX rework + test cleanup design spec (`docs/specs/`)

### Changed
- Deferred-7 sweep: migrated remaining UI components (N–R), 2D visualizers, App.jsx, main.jsx, and stores to TypeScript
- Deferred-6: documented Tailwind/Ant Design styling boundary (`docs/frontend-styling-guide.md`)
- Deferred-5: reorganized test suite — moved root-level tests to structured subdirectories
- Deferred-4: unified WebSocket connection managers into single canonical implementation
- Deferred-3: internal cleanup of 88-Buddha recitation loop
- Deferred-2: consolidated on lucide-react, removed @ant-design/icons
- Deferred-1: removed ruff suppressions, fixed all latent lint errors
- Removed dead VisualizationSelector from MainLayout after route consolidation

### Fixed
- 6 critical bugs: MOPS 500 error, provider registry drift, 6 LLM provider selection disconnects
- Restored 10 WebSocket handlers with dynamic LLM selection and random toggle
- `ruff` compliance: migrated `collections.Callable` to `collections.abc.Callable`
- Deleted dead/phantom tests, fixed false-pass tests, moved misfiled tests, extracted shared fixtures
- Test suite: 549 → ~350 Python tests (removed duplicates and false passes)

## [0.6.0] - 2026-06-17

### Added
- Healing Dialogue System: 5-phase Vajrayana container (Arrival → Seeing → Meeting → Release → Dedication)
- DB persistence for healing dialogue sessions with domain events
- Outlook feedback loop: healing summaries injected into outlook generation
- `/sanctuary` route with dialogue UI and phase indicator
- BuddhaRecitationContextModule for LLM prompt enrichment
- 88-Buddha practice deep-linked from Release phase
- Comprehensive test suite for healing dialogue system

### Changed
- Phase advancement is now user-triggered, not automatic
- WebSocket direct-to-backend for Sanctuary session creation
- Documented duplicate Buddha endpoints with `linked_outlook_id` back-reference

### Fixed
- Sanctuary SessionList Drawer: hardcoded palette for portal rendering outside CSS variable scope

## [0.5.0] - 2026-06-12

### Added
- 7-provider LLM registry: OpenAI, Anthropic, DeepSeek, MiniMax, Groq, OpenRouter, local (llama-cpp)
- Health-check heartbeat with provider availability monitoring
- ContextModule system for structured LLM prompt assembly
- BodhicittaBanner + RitualMonitor UI components
- `core/ritual_engine.py`: autonomous ritual scheduler
- Ritual engine REST endpoint with RitualConfigUpdate
- 117 new vitest frontend tests + shared astroHelpers module
- 13 backend tests for Bodhicitta transmutations + 3 new LLM tool schemas
- Playwright E2E infrastructure + happy-dom component test infrastructure
- Frontend build optimization: split vendor chunks, 85% smaller main bundle

### Changed
- Route consolidation: 12 routes → 7 grouped routes
- Migrated 6 Pydantic v1 `class Config` blocks to v2 `ConfigDict`
- Routed `compassionate_blessings` init through `core.schema`
- Stub Nominatim geocoding so rate-limited OSM API never breaks CI

### Fixed
- `commandStore.performSearch` called `getScore` as free function (now method)
- Astrology extraction: stopped hanging on tuple 3 by removing `asyncio.to_thread`
- `NameError` in geocode error handler (masked 400 as 500)
- API `endpoints/__init__.py` synced with `api.py` (was missing 23 exports)

## [0.4.0] - 2026-06-02

### Added
- TypeScript migration: 50 components converted to `.tsx`, 0 `.jsx` remaining in active code
- 8 new astrological calculation systems: Hellenistic lots, midpoints/antiscia, fixed stars, year-ahead transit timeline, secondary progressions, solar arc directions, solar returns, annual profections
- Astrocartography planetary lines (AC/DC/MC/IC per planet, coarse 5° step)
- Astrology extraction pipeline: ExtractionConfig/Run/Result dataclasses, TimeGrid generator, LLM-friendly chart formatter
- AstrologyExtractionPanel UI: Setup, Replay, Sweep, and Results tabs
- Batch extraction endpoint with async background processing
- Run management endpoints (list, get, results, export, delete, recompute)
- Astrology locations CRUD with seed loader (10 sacred sites + 5 astrocartography anchors)
- Unified TTS provider with Edge/Qwen3-TTS backends + REST endpoints with role overrides and streaming
- TTS settings panel and narrative player UI components
- NatalChartWheel: circular SVG chart with houses and planets
- SynastryViewer: real counts, distribution chart, energy bars
- ExportPanel: selection, format, fields, preview, download
- TransitComparison upgraded for 4-pillar Bazi + house cusp aspects
- OutlookDashboard: Affirmation tab + Difficulty + Global Intentions
- Centralized schema migration runner with extraction/location tables
- 17 tests for RitualScheduler pure methods, 8 tests for ritual_engine endpoint, 19 tests for core/ritual_engine
- 12 tests for BodhicittaBanner data arrays

### Changed
- `get_comprehensive_astrology` extended with houses + Chiron
- TrendsChart: dropped recharts, memoized, manual refresh

### Fixed
- Three transit/comparison bugs in astrology engine
- Missing `Statistic` and `Progress` antd imports in AstrologyExtractionPanel
- Recreated missing VisualizationSelector dropdown
- GeneratedContentGallery docstring converted from Python to JS syntax

## [0.3.0] - 2026-05-30

### Added
- Ant Design component library integration for UI refactor
- Orchestration improvements for multi-system coordination
- Time cycles and automation workflows
- Saka Dawa sacred day integration

### Changed
- 33+ remediation items: ghost paths removed, dead code deleted, hardcoded values extracted, duplicate files consolidated
- Astrology refinements across multiple subsystems
- Minor model and work for outlook dashboard
- Cleanup of old files and stale work artifacts

### Fixed
- Various "unknowns" resolved across the codebase
- Model fixes for outlook dashboard

## [0.2.0] - 2026-05-21

### Added
- 8 new astrology systems and calculation categories
- Astrology extraction pipeline foundation
- TTS (Text-to-Speech) integration with multiple backends
- `pyproject.toml` with project metadata, tool config (Black, isort, pytest, mypy, coverage), and dependency groups
- GitHub Actions CI pipeline with `ruff` and `pytest`
- Pre-commit config with `ruff` and standard hooks
- Session lifecycle events and unified session store in VajraService
- Frontend-compatible WebSocket message types for session events
- Crystal broadcast wired to session lifecycle
- 6 new visualization components: TrendsChart, RadionicsBroadcastPanel, ScalarWaveVisualizer, LiveWaveVisualizer, ChakraAlignmentStrip, remaining visualization options
- Interactive radionics UI design spec and implementation plan
- Directory ownership documentation for `modules/` and `core/`
- Shared pytest fixtures (`conftest.py`)
- Rewritten test suite: 6 test files converted to proper pytest with fixtures

### Changed
- Modernized tooling: `ruff` for linting (replaced flake8), `mypy` for type checking, `pytest` for testing
- Removed `sys.path.insert` hacks from container; added type hints
- Applied `ruff` lint fixes and formatting across codebase
- Frontend stores wired to backend APIs
- `useWebSocketStable` port corrected: 8007 → 8008
- SessionConfig duplication resolved; `delete_session` encapsulated

### Fixed
- 16 scratch/debug test files removed
- Tracked build artifacts cleaned from repository
- `.gitignore` and `.gitattributes` updated

## [0.1.0] - 2024-11-20

### Added
- FastAPI backend with stable WebSocket v2 implementation
- React/Vite frontend with 3D visualizations
- 7 visualization types:
  - Sacred Geometry (Flower of Life)
  - Astrocartography (3D Earth globe)
  - Radionics visualization
  - Crystal Grid
  - Sacred Mandala (Sri Yantra, Metatron's Cube)
  - Audio Spectrum
  - Planetary System (in development)
- Audio generation with prayer bowl synthesis
- Real-time WebSocket streaming at 10Hz
- Session management system
- Astrology and astrocartography calculations
- Scalar wave generation
- Radionics rate calculations
- Blessing narrative generation
- RNG attunement system
- Population management
- Automation workflows
- Comprehensive knowledge base (JSON files)
- Test suite with pytest and pytest-asyncio
- Documentation (52 markdown files)

### Technical Stack
- **Backend:** Python 3.10+, FastAPI, uvicorn, SQLAlchemy, WebSockets
- **Frontend:** React 18, Vite, Three.js, React Three Fiber, Zustand, Tailwind CSS
- **Audio:** NumPy, SciPy, sounddevice, pydub
- **Astrology:** Swiss Ephemeris, astropy, astroquery, pyswisseph
- **AI/LLM:** OpenAI, Anthropic, llama-cpp-python

## Release Types

### Major (X.0.0)
- Breaking API changes
- Major feature additions
- Architecture changes

### Minor (0.X.0)
- New features (backwards compatible)
- Significant enhancements
- New visualizations or modules

### Patch (0.0.X)
- Bug fixes
- Documentation updates
- Performance improvements
- Minor enhancements

## Types of Changes
- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security improvements

---

**Note:** This project is in active development. Version numbers and release dates will be updated as the project matures.