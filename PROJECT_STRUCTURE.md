# Vajra.Stream Project Structure

This document describes the organization of the Vajra.Stream repository.

## Directory Overview

```
vajra-stream/
├── backend/              # FastAPI backend application
├── core/                 # Core processing engines
├── modules/              # Feature modules
├── frontend/             # React frontend application
├── hardware/             # Hardware device interfaces
├── infrastructure/       # Event bus and utilities
├── config/               # Configuration files
├── knowledge/            # Knowledge bases and reference data
├── scripts/              # Utility and orchestration scripts
├── tests/                # Test suite (organized)
├── docs/                 # Documentation (organized)
├── data/                 # Runtime data files
├── templates/            # HTML templates
├── example/              # Example JSON files
├── examples/             # Example Python scripts
└── [Root config files]   # pyproject.toml, .gitignore, etc.
```

## Backend (`backend/`)

FastAPI web application and API server.

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── api/v1/endpoints/          # API endpoint modules (30 files)
│   │   ├── agent_suggestions.py  # Agent suggestion endpoints
│   │   ├── anatomy.py            # Energetic anatomy
│   │   ├── astrology.py          # Astrological calculations
│   │   ├── audio.py              # Audio generation/playback
│   │   ├── automation.py         # Automation workflows
│   │   ├── blessing_slideshow.py # Blessing slideshow
│   │   ├── blessings.py          # Blessing generation
│   │   ├── dharma_tales.py       # Dharma tale generation
│   │   ├── divination.py         # Divination endpoints
│   │   ├── extraction.py         # Astrology extraction pipeline
│   │   ├── healing_dialogue.py   # Healing dialogue system (NEW)
│   │   ├── llm.py                # LLM provider endpoints
│   │   ├── locations.py          # Astrology locations CRUD
│   │   ├── mops.py               # MOPS (Multi-Operator System)
│   │   ├── operator.py           # Operator tools (Saka Dawa, etc.)
│   │   ├── outlook.py            # Outlook generation
│   │   ├── personal_healing.py   # Personal healing
│   │   ├── populations.py        # Population management
│   │   ├── prayer_wheel.py       # Prayer wheel automation
│   │   ├── radionics.py          # Radionics rates
│   │   ├── radionics_narratives.py # Radionics narratives
│   │   ├── ritual_engine.py      # Ritual engine
│   │   ├── rng_attunement.py     # RNG attunement
│   │   ├── scalar_waves.py       # Scalar wave operations
│   │   ├── sessions.py           # Session management
│   │   ├── sigils.py             # Sigil generation
│   │   ├── time_cycles.py        # Time cycle operations
│   │   ├── tts.py                # Text-to-speech
│   │   └── visualization.py      # Visualization generation
│   └── config.py                  # API configuration (shim for config/settings.py)
├── websocket/                     # WebSocket connection management
│   └── connection_manager_stable_v2.py  # Canonical WebSocket manager
├── tests/                         # Backend integration tests
└── requirements.txt               # Backend-specific dependencies
```

**Key Files:**
- **`app/main.py`**: FastAPI app initialization, CORS, routing, lifespan management
- **`api/v1/endpoints/*.py`**: 30 RESTful API endpoint modules covering all feature areas
- **`websocket/connection_manager_stable_v2.py`**: Real-time WebSocket streaming (10Hz)

## Core (`core/`)

Core processing engines and algorithms (44 Python files).

```
core/
├── astrology.py                   # Astrological services (111 KB — largest core file)
├── energetic_anatomy.py           # Chakra and meridian systems (56 KB)
├── blessing_narratives.py         # Blessing narrative generation (40 KB)
├── radionics_tools.py             # Radionics tool functions (40 KB)
├── outlook_generator.py           # Outlook generation (39 KB)
├── extraction.py                  # Astrology extraction pipeline (28 KB)
├── ritual_engine.py               # Autonomous ritual scheduler (28 KB)
├── astrocartography.py            # Astrocartography calculations (28 KB)
├── compassionate_blessings.py     # Compassionate blessing engine (27 KB)
├── radionics_engine.py            # Radionics rate calculations (26 KB)
├── enhanced_tts.py                # Enhanced TTS (25 KB)
├── energetic_visualization.py     # Energy field visualization (25 KB)
├── healing_systems.py             # Healing protocol engine (24 KB)
├── auspicious_timing.py           # Auspicious timing calculations (24 KB)
├── advanced_scalar_waves.py       # Advanced scalar wave generation (21 KB)
├── tts_provider.py                # Unified TTS provider (20 KB)
├── tts_integration.py             # TTS integration layer (20 KB)
├── character_generator.py         # Character generation (20 KB)
├── time_cycle_broadcaster.py      # Time-based broadcasting (20 KB)
├── integrated_scalar_radionics.py # Integrated scalar-radionics (19 KB)
├── schema.py                      # Centralized schema + migration runner (19 KB)
├── buddha_recitation_loop.py      # 88-Buddha recitation loop (19 KB)
├── meridian_visualization.py      # Meridian pathway visualization (18 KB)
├── intelligent_composer.py        # AI-powered audio composition (18 KB)
├── audio_generator.py             # Scalar wave and frequency generation (18 KB)
├── context_builder.py             # Context assembly for LLM prompts (18 KB)
├── assessment.py                  # Assessment engine (17 KB)
├── prayer_wheel.py                # Prayer wheel automation (17 KB)
├── qwen_tts.py                    # Qwen3-TTS backend (16 KB)
├── eighty_eight_buddhas.py        # 88-Buddha practice data (15 KB)
├── healing_session.py             # Healing session management (15 KB)
├── dharma_tales.py                # Dharma tale generation (14 KB)
├── character_journey.py           # Character journey engine (13 KB)
├── ritual_sequencer.py            # Ritual sequencing (12 KB)
├── rothko_generator.py            # Rothko-style visualization (12 KB)
├── enhanced_audio_generator.py    # Prayer bowl synthesis (11 KB)
├── internet_context.py            # Internet context retrieval (11 KB)
├── tts_engine.py                  # TTS engine base (10 KB)
├── knowledge_index.py             # Knowledge indexing (10 KB)
├── protocol_selector.py           # Protocol selection (8 KB)
├── buddha_tts.py                  # Buddha-specific TTS (8 KB)
├── chinese_invocations.py         # Chinese invocation data (7 KB)
├── visual_renderer_simple.py      # Simple visual renderer (6 KB)
└── __init__.py                    # Package init
```

**Key Files:**
- **`astrology.py`**: Comprehensive astrological calculations (111 KB)
- **`blessing_narratives.py`**: LLM-powered blessing generation
- **`radionics_engine.py`**: Radionics rate database and calculations
- **`buddha_recitation_loop.py`**: 88-Buddha recitation with TTS playback
- **`schema.py`**: Centralized database schema and migration runner

## Modules (`modules/`)

Feature modules and integrations (25 Python files).

```
modules/
├── radionics_operator.py          # Radionics operator (75 KB — largest module)
├── healing_dialogue.py            # Healing dialogue system (33 KB — NEW)
├── outlook.py                     # Outlook module (22 KB)
├── personal_healing.py            # Personal healing (15 KB)
├── blessings.py                   # Blessing module (14 KB)
├── llm.py                         # LLM integration (9 KB)
├── interfaces.py                  # Module interfaces (8 KB)
├── audio.py                       # Audio module (7 KB)
├── anatomy.py                     # Anatomy module (6 KB)
├── healing.py                     # Healing protocols (6 KB)
├── visualization.py               # Visualization module (5 KB)
├── astrology.py                   # Astrology module wrapper (5 KB)
├── blessing_router.py             # Blessing routing (5 KB)
├── wave_manager.py                # Wave management (5 KB)
├── composer.py                    # Audio composition (5 KB)
├── scalar_waves.py                # Scalar wave module (5 KB)
├── enhanced_scalar_waves.py       # Enhanced scalar waves (4 KB)
├── radionics_enhancer.py          # Radionics enhancement (4 KB)
├── time_cycles.py                 # Time cycle module (4 KB)
├── prayer_wheel.py                # Prayer wheel module (4 KB)
├── radionics.py                   # Radionics module (4 KB)
├── crystal.py                     # Crystal grid module (3 KB)
├── tts_integration.py             # TTS integration (3 KB)
├── dharma_tales.py                # Dharma tales module (2 KB)
└── __init__.py                    # Package init
```

**Key Files:**
- **`radionics_operator.py`**: Full radionics broadcasting system (75 KB)
- **`healing_dialogue.py`**: 5-phase healing dialogue container with DB persistence (33 KB)

## Frontend (`frontend/`)

React/Vite web application with 3D visualizations (126 TypeScript/TSX files, 2 legacy JSX files).

```
frontend/
├── src/
│   ├── components/
│   │   ├── 3D/                   # Three.js 3D components
│   │   │   ├── SacredGeometry.tsx
│   │   │   ├── Astrocartography.tsx
│   │   │   ├── CrystalGrid.tsx
│   │   │   ├── SacredMandala.tsx
│   │   │   └── RadionicsVisualization.tsx
│   │   ├── 2D/                   # 2D Canvas components (.tsx)
│   │   │   └── AudioSpectrum.tsx
│   │   └── UI/                   # Control panel components (50 .tsx files)
│   │       ├── ControlPanel.tsx
│   │       ├── SessionManager.tsx
│   │       ├── StatusIndicator.tsx
│   │       ├── RNGAttunement.tsx
│   │       ├── BlessingSlideshow.tsx
│   │       ├── PopulationManager.tsx
│   │       ├── AutomationControl.tsx
│   │       ├── BodhicittaBanner.tsx
│   │       ├── RitualMonitor.tsx
│   │       ├── AstrologyExtractionPanel.tsx
│   │       ├── NatalChartWheel.tsx
│   │       ├── SynastryViewer.tsx
│   │       ├── ExportPanel.tsx
│   │       ├── OutlookDashboard.tsx
│   │       ├── TTSPlayer.tsx
│   │       └── ... (50 total)
│   ├── routes/                   # Route-level page components
│   │   ├── Practice/             # Practice-related routes
│   │   ├── Sanctuary/            # Healing dialogue sanctuary
│   │   ├── Buddhas/              # 88-Buddha practice
│   │   ├── Operations/           # Radionics, scalar waves, etc.
│   │   └── Settings/             # Configuration and settings
│   ├── hooks/
│   │   ├── useWebSocket.ts       # WebSocket connection hook
│   │   └── useWebSocketStable.ts
│   ├── stores/
│   │   ├── audioStore.ts         # Audio state (Zustand)
│   │   └── commandStore.ts       # Command state
│   ├── lib/
│   │   └── colors.js             # Brand color single source of truth
│   ├── utils/
│   │   └── api.ts                # Proxy-relative URL helper
│   ├── App.tsx                   # Main application component
│   ├── main.tsx                  # React entry point
│   └── index.css                 # Global styles (Tailwind + CSS variables)
├── public/                        # Static assets
├── package.json                   # Frontend dependencies
├── vite.config.ts                 # Vite configuration (port 3009, proxy to 8008)
├── tailwind.config.js             # Tailwind CSS configuration
├── .prettierrc                    # Prettier configuration
└── .eslintrc.json                 # ESLint configuration
```

**Key Files:**
- **`App.tsx`**: Main app structure with vertical layout (viz top, controls bottom)
- **`components/UI/`**: 50 TypeScript control panel components
- **`routes/`**: 7 grouped routes (Command Center, Practice, Cosmic Clock, Outlook, Operations, Grimoire, Settings); 5 route subdirectories on disk (Practice, Operations, Settings + tab-content dirs Sanctuary, Buddhas)
- **`stores/audioStore.ts`**: Audio state management with API integration

## Routes (`frontend/src/routes/`)

Route-level page components organized by feature area (consolidated from 12 routes).

```
frontend/src/routes/
├── Practice/          # Core practice routes (blessings, healing, astrology, visualization)
├── Sanctuary/         # Healing dialogue sanctuary with 5-phase container UI
├── Buddhas/           # 88-Buddha recitation practice
├── Operations/        # Radionics, scalar waves, MOPS, ritual engine
└── Settings/          # Configuration, TTS settings, provider management
```

## Async LLM Layer (`core/llm/`, `core/context/`)

Provider-agnostic LLM integration with structured context assembly.

```
core/llm/                          # LLM provider layer (12 files)
├── registry.py                    # 7-provider registry (OpenAI, Anthropic, DeepSeek, MiniMax, Groq, OpenRouter, local)
├── health.py                      # Health-check heartbeat with provider availability
├── base.py                        # Base provider interface
├── models.py                      # Provider model definitions
├── cache.py                       # Response caching
├── retry.py                        # Retry logic with backoff
├── usage.py                       # Usage tracking and quotas
├── bootstrap.py                   # Provider initialization
├── legacy_adapter.py              # Legacy LLM adapter
├── dharma.py                      # Dharma-specific LLM prompts
├── healing.py                     # Healing-specific LLM prompts
└── __init__.py

core/context/                      # Context assembly layer (8 files)
├── base.py                        # Base context module
├── models.py                      # Context data models
├── anatomy.py                     # Energetic anatomy context
├── astrology.py                   # Astrological context
├── buddha_recitation.py           # Buddha recitation context
├── hardware.py                    # Hardware state context
├── healing_dialogue.py            # Healing dialogue context
└── __init__.py
```

## Hardware (`hardware/`)

Hardware device interfaces.

```
hardware/
├── crystal_broadcaster.py         # Level 2 (passive) and Level 3 (amplified)
└── __init__.py
```

## Infrastructure (`infrastructure/`)

Event bus and utility services.

```
infrastructure/
├── event_bus.py                   # Event-driven architecture
└── __init__.py
```

## Configuration (`config/`)

Application configuration files.

```
config/
└── settings.py                    # Core settings (audio, hardware, paths)
```

## Knowledge (`knowledge/`)

Knowledge bases and reference data (25 files, JSON format).

```
knowledge/
├── blessing_populations/          # Target populations for blessings
│   ├── earth_population.json
│   ├── suffering_beings.json
│   └── ... (7 files)
├── example_stories/               # Example narratives (markdown)
│   └── ... (4 files)
├── radionics_rates/               # Radionics rate databases
│   ├── complete_rates_database.json
│   ├── health_conditions.json
│   ├── chakra_rates.json
│   └── ... (5 files)
├── frequencies.json               # Frequency reference data
├── healing_knowledge.json         # Healing protocols and knowledge
└── historical_suffering_events.json
```

## Scripts (`scripts/`)

Utility and orchestration scripts (35 Python files).

```
scripts/
├── unified_orchestrator.py        # Main orchestrator
├── vajra_orchestrator.py
├── astrocartography_analysis.py   # CLI tool for astrocartography
├── radionics_operation.py
└── ... (35 total utility scripts)
```

## Tests (`tests/`)

**Organized test suite** (~350 Python tests after deduplication).

```
tests/
├── unit/                          # Unit tests
│   ├── test_audio_*.py           # Audio-related tests
│   ├── test_rng_*.py             # RNG tests
│   ├── test_tts_system.py
│   └── ...
├── integration/                   # Integration tests
│   ├── test_full_integration.py
│   ├── test_websocket_*.py       # WebSocket connection tests
│   └── ...
├── backend/                       # Backend-specific tests
│   ├── test_saka_dawa_endpoint.py
│   └── ...
├── core/                          # Core module tests
│   ├── test_buddha_recitation_loop_tts.py
│   └── ...
├── e2e/                           # End-to-end tests
├── conftest.py                    # Shared pytest fixtures
└── README.md                      # Test suite documentation
```

**Test Organization:**
- **Unit tests**: Individual module/function tests
- **Integration tests**: Multi-module interaction tests
- **Backend tests**: API endpoint tests
- **Core tests**: Core engine tests
- **E2E tests**: Full user workflow tests

## Documentation (`docs/`)

**Organized documentation** (reorganized from 52 scattered files).

```
docs/
├── _archive/                      # Deprecated/stale docs (deliberate one-time archive)
├── decisions/                     # Architecture Decision Records (ADRs)
├── pr-reviews/                    # Pull-request review notes
├── specs/                         # Specifications
├── superpowers/                   # Superpowers skill documentation
├── ARCHITECTURE.md                # System architecture overview
├── DEVELOPMENT.md                 # Development guide
├── FEATURES_REFERENCE.md          # Feature reference
├── OPERATIONS_GUIDE.md            # Operations guide
└── README.md                      # Documentation index
```

## Root Directory

Essential files in project root:

```
/
├── README.md                      # Project overview
├── START_HERE.md                  # Quick start guide
├── QUICKSTART.md                  # Fast setup
├── API_DOCUMENTATION.md           # Comprehensive API docs
├── CONTRIBUTING.md                # Contribution guidelines
├── CHANGELOG.md                   # Version history
├── PROJECT_STRUCTURE.md           # This file
├── pyproject.toml                 # Python package config
├── .gitignore                     # Git ignore rules
├── .editorconfig                  # Editor settings
├── .flake8                        # Flake8 config
├── requirements.txt               # Python dependencies
├── requirements-minimal.txt       # Minimal dependencies
└── container.py                   # Dependency injection container
```

## File Naming Conventions

### Python Files
- **Modules**: `snake_case.py`
- **Tests**: `test_*.py`
- **Scripts**: `descriptive_name.py`

### TypeScript Files
- **Components**: `PascalCase.tsx`
- **Utilities**: `camelCase.ts`
- **Tests**: `*.test.ts` or `*.spec.ts`

### Documentation
- **Main docs**: `UPPERCASE_WITH_UNDERSCORES.md`
- **Subdirectory docs**: Can use either case
- **Always include** `.md` extension

### JSON Files
- **Config**: `kebab-case.json` or `snake_case.json`
- **Data**: `descriptive_name.json`

## Module Organization Principles

1. **Separation of Concerns**: Backend, frontend, core, modules clearly separated
2. **Feature-Based**: Related functionality grouped together
3. **Layered Architecture**: API → Services → Core → Hardware/Infrastructure
4. **Test Co-location**: Tests mirror source structure
5. **Documentation First**: Comprehensive docs for all features

## Best Practices

### Adding New Features

1. **Backend**: Add endpoint in `backend/app/api/v1/endpoints/`
2. **Core Logic**: Implement in `core/` or `modules/`
3. **Frontend**: Add component in `frontend/src/components/`
4. **Tests**: Add to `tests/unit/` or `tests/integration/`
5. **Docs**: Update relevant docs in `docs/`
6. **Knowledge**: Add reference data to `knowledge/`

### File Placement Guide

**Where should I put...?**

- **API endpoint**: `backend/app/api/v1/endpoints/`
- **Business logic**: `core/` or `modules/`
- **React component**: `frontend/src/components/`
- **Utility function**: `core/` (Python) or `frontend/src/utils/` (JS)
- **Test file**: `tests/unit/` or `tests/integration/`
- **Documentation**: `docs/` (appropriate subdirectory)
- **Configuration**: `config/` (Python) or root (project-wide)
- **Reference data**: `knowledge/`

## Version Control

### What's Tracked
- Source code (`.py`, `.ts`, `.tsx`)
- Configuration files
- Documentation (`.md`)
- Knowledge bases (`.json`)
- Tests

### What's Ignored (.gitignore)
- `__pycache__/`, `*.pyc`
- `node_modules/`
- `.venv/`, `venv/`
- `*.db`
- `.env`, `*.log`
- `dist/`, `build/`
- IDE-specific files

## Dependency Management

### Python
- **Main**: `requirements.txt`
- **Minimal**: `requirements-minimal.txt`
- **Visualization**: `requirements_visualization.txt`
- **Backend**: `backend/requirements.txt`
- **Dev**: `pyproject.toml` [tool.project.optional-dependencies]

### JavaScript
- **Frontend**: `frontend/package.json`
- Lock file: `frontend/package-lock.json`

## Configuration Files

### Code Quality
- **`pyproject.toml`**: Black, isort, pytest, mypy, coverage config
- **`.flake8`**: Python linting rules
- **`frontend/.prettierrc`**: TypeScript formatting
- **`frontend/.eslintrc.json`**: TypeScript linting
- **`.editorconfig`**: Editor consistency

### Build Tools
- **`frontend/vite.config.ts`**: Vite build configuration
- **`frontend/tailwind.config.js`**: Tailwind CSS configuration

### Runtime
- **`config/settings.py`**: Application settings
- **`backend/app/main.py`**: FastAPI app configuration

## Next Steps

See:
- [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- [docs/README.md](docs/README.md) for documentation index
- [tests/README.md](tests/README.md) for testing guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API reference

---

**Last Updated:** 2026-06-20
**Maintainer:** Vajra.Stream Development Team