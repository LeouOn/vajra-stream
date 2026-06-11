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
│   ├── api/v1/endpoints/          # API endpoint modules (14 files)
│   │   ├── audio.py              # Audio generation/playback
│   │   ├── sessions.py           # Session management
│   │   ├── astrology.py          # Astrological calculations
│   │   ├── scalar_waves.py       # Scalar wave operations
│   │   ├── radionics.py          # Radionics rates
│   │   ├── anatomy.py            # Energetic anatomy
│   │   ├── blessings.py          # Blessing generation
│   │   ├── visualization.py      # Visualization generation
│   │   ├── rng_attunement.py     # RNG attunement
│   │   ├── populations.py        # Population management
│   │   ├── automation.py         # Automation workflows
│   │   └── ...
│   └── config.py                  # API configuration
├── core/
│   ├── services/                  # Business logic services (7 files)
│   │   ├── vajra_service.py
│   │   ├── audio_service.py
│   │   ├── blessing_scheduler.py
│   │   ├── rng_attunement_service.py
│   │   └── ...
│   ├── orchestrator_bridge.py     # Event bus bridge
│   └── __init__.py
├── websocket/                     # WebSocket connection management
│   ├── connection_manager_stable_v2.py  # Active WebSocket manager
│   └── ...
├── tests/                         # Backend integration tests
│   ├── test_integration.py
│   ├── conftest.py
│   └── __init__.py
└── requirements.txt               # Backend-specific dependencies
```

**Key Files:**
- **`app/main.py`**: FastAPI app initialization, CORS, routing, lifespan management
- **`api/v1/endpoints/*.py`**: RESTful API endpoints for each feature module
- **`websocket/connection_manager_stable_v2.py`**: Real-time WebSocket streaming (10Hz)

## Core (`core/`)

Core processing engines and algorithms.

```
core/
├── audio_generator.py             # Scalar wave and frequency generation
├── enhanced_audio_generator.py    # Prayer bowl synthesis
├── astrocartography.py            # Astrocartography calculations (798 lines)
├── astrology.py                   # Astrological services
├── blessing_narratives.py         # Blessing narrative generation
├── compassionate_blessings.py     # Compassionate blessing engine
├── energetic_anatomy.py           # Chakra and meridian systems
├── energetic_visualization.py     # Energy field visualization
├── healing_systems.py             # Healing protocol engine
├── intelligent_composer.py        # AI-powered audio composition
├── meridian_visualization.py      # Meridian pathway visualization
├── prayer_wheel.py                # Prayer wheel automation
├── radionics_engine.py            # Radionics rate calculations
├── rothko_generator.py            # Rothko-style visualization
├── time_cycle_broadcaster.py      # Time-based broadcasting
├── services/                      # Shared core services
│   ├── audio_service.py
│   └── vajra_service.py
└── __init__.py
```

**Key Files:**
- **`astrocartography.py`**: Planetary line calculations, parans, local space
- **`blessing_narratives.py`**: LLM-powered blessing generation
- **`radionics_engine.py`**: Radionics rate database and calculations

## Modules (`modules/`)

Feature modules and integrations.

```
modules/
├── astrology.py                   # Astrology module wrapper
├── audio.py                       # Audio module
├── blessings.py                   # Blessing module
├── healing.py                     # Healing protocols module
├── radionics.py                   # Radionics module
├── visualization.py               # Visualization module
└── __init__.py
```

## Frontend (`frontend/`)

React/Vite web application with 3D visualizations.

```
frontend/
├── src/
│   ├── components/
│   │   ├── 3D/                   # Three.js 3D components
│   │   │   ├── SacredGeometry.jsx
│   │   │   ├── Astrocartography.jsx  # NEW: 3D Earth visualization
│   │   │   ├── CrystalGrid.jsx
│   │   │   ├── SacredMandala.jsx
│   │   │   └── RadionicsVisualization.jsx
│   │   ├── 2D/                   # 2D Canvas components
│   │   │   └── AudioSpectrum.jsx
│   │   └── UI/                   # Control panel components
│   │       ├── ControlPanel.jsx
│   │       ├── SessionManager.jsx
│   │       ├── StatusIndicator.jsx
│   │       ├── VisualizationSelector.jsx
│   │       ├── RNGAttunement.jsx
│   │       ├── BlessingSlideshow.jsx
│   │       ├── PopulationManager.jsx
│   │       └── AutomationControl.jsx
│   ├── hooks/
│   │   ├── useWebSocket.js       # WebSocket connection hook
│   │   └── useWebSocketStable.js
│   ├── stores/
│   │   └── audioStore.js         # Zustand state management
│   ├── App.jsx                   # Main application component
│   ├── main.jsx                  # React entry point
│   └── index.css                 # Global styles
├── public/                        # Static assets
├── package.json                   # Frontend dependencies
├── vite.config.js                 # Vite configuration (port 3009, proxy to 8008)
├── tailwind.config.js             # Tailwind CSS configuration
├── .prettierrc                    # Prettier configuration
└── .eslintrc.json                 # ESLint configuration
```

**Key Files:**
- **`App.jsx`**: Main app structure with vertical layout (viz top, controls bottom)
- **`components/3D/Astrocartography.jsx`**: New 3D Earth with planetary lines
- **`stores/audioStore.js`**: Audio state management with API integration

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
├── settings.py                    # Core settings (audio, hardware, paths)
└── enhanced_settings.py           # Enhanced configuration management
```

## Knowledge (`knowledge/`)

Knowledge bases and reference data (JSON format).

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

Utility and orchestration scripts.

```
scripts/
├── unified_orchestrator.py        # Main orchestrator
├── vajra_orchestrator.py
├── astrocartography_analysis.py   # CLI tool for astrocartography
├── radionics_operation.py
├── visualizer.py
└── ... (25+ utility scripts)
```

## Tests (`tests/`)

**Organized test suite** (reorganized from 37 scattered files).

```
tests/
├── unit/                          # Unit tests (18 files)
│   ├── test_audio_*.py           # Audio-related tests
│   ├── test_rng_*.py             # RNG tests
│   ├── test_tts_system.py
│   ├── test_basic_functionality.py
│   └── ...
├── integration/                   # Integration tests (16 files)
│   ├── test_full_integration.py
│   ├── test_websocket_*.py       # WebSocket connection tests
│   ├── test_module_connections.py
│   └── ...
├── e2e/                           # End-to-end tests (placeholder)
├── scripts/                       # Deprecated (being migrated)
├── test_foundation.py
├── test_integration_phase2.py
├── test_api_endpoints.py
├── test_radionics_enhancer.py
└── README.md                      # Test suite documentation
```

**Test Organization:**
- **Unit tests**: Individual module/function tests
- **Integration tests**: Multi-module interaction tests
- **E2E tests**: Full user workflow tests (to be implemented)

## Documentation (`docs/`)

**Organized documentation** (reorganized from 52 scattered files).

```
docs/
├── api/                           # API documentation
│   ├── BACKEND_API_ENDPOINTS_SPECIFICATION.md
│   ├── UNIFIED_API_ARCHITECTURE.md
│   ├── WEB_ARCHITECTURE.md
│   └── WEBSOCKET_RADIONICS_PROTOCOL.md
├── architecture/                  # System architecture
│   ├── COMPREHENSIVE_IMPLEMENTATION_GUIDE.md
│   ├── UNIFIED_ARCHITECTURE.md
│   └── ...
├── features/                      # Feature specifications
│   ├── FEATURES.md
│   ├── HEALING_SYSTEMS_SUMMARY.md
│   └── VISUALIZATION_SPEC.md
├── guides/                        # User and developer guides
│   ├── USAGE_GUIDE.md
│   ├── ASTROCARTOGRAPHY_GUIDE.md
│   ├── BLESSING_NARRATIVES_GUIDE.md
│   ├── PRAYER_BOWL_AUDIO.md
│   ├── SCALAR_WAVE_THEORY.md
│   └── ...
├── implementation/                # Implementation details
│   ├── BACKEND_IMPLEMENTATION.md
│   ├── FRONTEND_IMPLEMENTATION.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   └── ...
├── radionics/                     # Radionics documentation
│   ├── RADIONICS_MASTER_GUIDE.md
│   ├── PHYSICAL_RADIONICS_SETUP.md
│   └── ...
├── DEVELOPMENT_ROADMAP.md
├── PROGRESS_TRACKER.md
└── README.md                      # Documentation index
```

## Root Directory

Essential files in project root:

```
/
├── README.md                      # ✓ Project overview (KEEP)
├── START_HERE.md                  # ✓ Quick start guide (KEEP)
├── QUICKSTART.md                  # ✓ Fast setup (KEEP)
├── API_DOCUMENTATION.md           # ✓ Comprehensive API docs (KEEP)
├── CONTRIBUTING.md                # ✓ Contribution guidelines (NEW)
├── CHANGELOG.md                   # ✓ Version history (NEW)
├── PROJECT_STRUCTURE.md           # ✓ This file (NEW)
├── pyproject.toml                 # ✓ Python package config (NEW)
├── .gitignore                     # ✓ Git ignore rules
├── .editorconfig                  # ✓ Editor settings (NEW)
├── .flake8                        # ✓ Flake8 config (NEW)
├── requirements.txt               # Python dependencies
├── requirements-minimal.txt       # Minimal dependencies
├── container.py                   # Dependency injection container
├── vajra_stream.py                # Main entry point
├── vajra_stream_v2.py
└── start_full_system.py           # System launcher
```

## File Naming Conventions

### Python Files
- **Modules**: `snake_case.py`
- **Tests**: `test_*.py`
- **Scripts**: `descriptive_name.py`

### JavaScript Files
- **Components**: `PascalCase.jsx`
- **Utilities**: `camelCase.js`
- **Tests**: `*.test.js` or `*.spec.js`

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
- Source code (`.py`, `.js`, `.jsx`)
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
- **`frontend/.prettierrc`**: JavaScript formatting
- **`frontend/.eslintrc.json`**: JavaScript linting
- **`.editorconfig`**: Editor consistency

### Build Tools
- **`frontend/vite.config.js`**: Vite build configuration
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

**Last Updated:** 2024-11-20
**Maintainer:** Vajra.Stream Development Team
