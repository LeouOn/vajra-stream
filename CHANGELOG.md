# Changelog

All notable changes to Vajra.Stream will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Astrocartography 3D visualization component with planetary line mapping
- Comprehensive API documentation (800+ lines) covering all 12 modules
- Reorganized UI layout with visualizations on top and controls at bottom
- Code quality tools configuration (Black, Flake8, isort, Prettier, ESLint)
- Project documentation index with organized subdirectories
- Test suite organization into unit/integration/e2e structure
- Contributing guidelines (CONTRIBUTING.md)
- Project structure documentation (PROJECT_STRUCTURE.md)
- EditorConfig for consistent editor settings
- pyproject.toml for Python package configuration

### Changed
- Frontend-backend port configuration (8003 → 8008)
- Moved all test files from root to organized tests/ directory
- Moved 48 documentation files from root to docs/ subdirectories
- Updated docs/README.md with complete documentation index
- Reorganized frontend layout: vertical instead of horizontal
- Control panels now in responsive grid at bottom of screen

### Fixed
- Frontend-backend communication issues (port mismatch)
- stopAudio() now properly calls backend API endpoint
- Made sounddevice dependency optional for systems without PortAudio
- WebSocket connectivity between frontend and backend

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
