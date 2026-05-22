# Vajra.Stream Deep Modernization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Vajra.Stream repo with proper Python tooling, clean test suite, CI pipeline, and git hygiene.

**Architecture:** Add pyproject.toml as the single source of truth for project metadata, dependencies, and tool config. Rewrite surviving tests as proper pytest with fixtures. Delete dead scratch tests. Add ruff/mypy/pre-commit/CI. Clean git tracking.

**Tech Stack:** Python 3.10+, ruff, mypy, pytest, pytest-asyncio, pre-commit, GitHub Actions

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `pyproject.toml` | Project metadata, deps, tool config |
| Create | `requirements-dev.txt` | Dev-only deps (backward compat) |
| Create | `.pre-commit-config.yaml` | Pre-commit hooks |
| Create | `.gitattributes` | Line ending config |
| Create | `.github/workflows/ci.yml` | CI pipeline |
| Create | `tests/conftest.py` | Shared pytest fixtures |
| Create | `modules/README.md` | Document modules/ ownership |
| Create | `core/README.md` | Document core/ ownership |
| Modify | `.gitignore` | Add missing entries |
| Modify | `container.py` | Remove sys.path hack, add type hints |
| Modify | `vajra_stream_v2.py` | Remove sys.path hack |
| Modify | `backend/app/main.py` | Remove sys.path hack |
| Rewrite | `tests/test_foundation.py` | Proper pytest with fixtures |
| Rewrite | `tests/test_monolith.py` → `tests/test_container_modules.py` | Proper pytest |
| Rewrite | `tests/test_basic_functionality.py` → `tests/test_services.py` | Proper pytest |
| Rewrite | `tests/test_rng_service.py` | Proper pytest |
| Rewrite | `tests/test_radionics_enhancer.py` | Already uses unittest, convert to pytest |
| Rewrite | `tests/test_server.py` | Proper pytest |
| Delete | 16 scratch test files | Dead tests |
| Delete | All `__pycache__/` dirs | Tracked artifacts |

---

### Task 1: Git Hygiene — Update .gitignore and remove tracked artifacts

**Files:**
- Modify: `.gitignore`
- Create: `.gitattributes`
- Delete: all `__pycache__/` dirs, `backend_server.err`, `backend_server.log`

- [ ] **Step 1: Update `.gitignore`**

Add the following missing entries to `.gitignore` after the existing `# Temporary files` section:

```
# Virtual environments (expanded)
.venv/

# AI tooling
.kilo/

# Backend server logs (runtime artifacts)
backend_server.err
backend_server.log

# Byte-compiled (explicit)
*.pyc
```

- [ ] **Step 2: Create `.gitattributes`**

Create `.gitattributes` with:

```
* text=auto
*.py text eol=lf
*.bat text eol=crlf
*.sh text eol=lf
*.json text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.toml text eol=lf
*.md text eol=lf
*.txt text eol=lf
*.css text eol=lf
*.js text eol=lf
*.ts text eol=lf
*.tsx text eol=lf
*.html text eol=lf
*.db binary
*.sqlite binary
*.png binary
*.jpg binary
*.wav binary
*.mp3 binary
```

- [ ] **Step 3: Remove tracked artifacts from git index (keep on disk)**

```bash
git rm -r --cached __pycache__ core/__pycache__ modules/__pycache__ infrastructure/__pycache__ backend/app/__pycache__ backend/app/api/__pycache__ backend/app/api/v1/__pycache__ backend/app/api/v1/endpoints/__pycache__ backend/core/__pycache__ backend/websocket/__pycache__ tests/__pycache__ backend/__pycache__ scripts/__pycache__ 2>/dev/null; git rm --cached backend_server.err backend_server.log vajra_stream.db 2>/dev/null; echo "Done"
```

Expected: Git reports files removed from tracking. Files still exist on disk.

- [ ] **Step 4: Verify .gitignore is working**

```bash
git status
```

Expected: No `__pycache__/` dirs or `.pyc` files showing as untracked.

- [ ] **Step 5: Commit**

```bash
git add .gitignore .gitattributes
git commit -m "chore: update .gitignore, add .gitattributes, remove tracked artifacts"
```

---

### Task 2: Delete scratch/debug test files

**Files:**
- Delete: 16 files from `tests/`

- [ ] **Step 1: Delete the scratch test files**

```bash
cd tests
rm -f test_fixed3_connection.py test_fixed4_connection.py test_minimal_connection.py test_module_connections.py test_implementation_simple.py test_integration_simple.py test_websocket_minimal.py test_websocket_simple.py test_new_implementation.py test_full_integration.py test_integration_phase2.py test_integration.py test_rng_api.py test_tts_system.py test_visualization.py test_api_endpoints.py
```

- [ ] **Step 2: Verify only the kept tests remain**

```bash
ls tests/
```

Expected: `__init__.py`, `conftest.py` (not yet created), `test_basic_functionality.py`, `test_foundation.py`, `test_monolith.py`, `test_radionics_enhancer.py`, `test_rng_service.py`, `test_server.py`

- [ ] **Step 3: Commit**

```bash
git add -A tests/
git commit -m "chore: remove 16 scratch/debug test files"
```

---

### Task 3: Add pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "vajra-stream"
version = "0.2.0"
description = "Digital Dharma Technology — sacred technology for continuous blessing, healing, and purification"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}

dependencies = [
    "numpy>=1.24.0",
    "scipy>=1.10.0",
    "pillow>=10.0.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "colorama>=0.4.0",
    "psutil>=5.9.0",
    "requests>=2.31.0",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
web = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "jinja2>=3.1.0",
    "websockets>=12.0",
    "python-multipart>=0.0.6",
    "aiohttp>=3.8.0",
    "aiofiles>=0.8.0",
]
audio = [
    "sounddevice>=0.4.6",
    "pydub>=0.25.0",
    "soundfile>=0.12.0",
    "pyttsx3>=2.90",
]
science = [
    "matplotlib>=3.7.0",
    "pandas>=2.0.0",
    "sqlalchemy>=2.0.0",
    "alembic",
    "astropy>=5.3.0",
    "sympy>=1.0.0",
]
astrology = [
    "pyswisseph>=2.10.3.2",
    "astroquery>=0.4.6",
]
llm = [
    "openai>=1.3.0",
    "anthropic>=0.7.0",
]
hardware = [
    "pyserial>=3.5",
]
viz = [
    "opencv-python>=4.8.0",
]
all = [
    "vajra-stream[web,audio,science,astrology,llm,hardware,viz]",
    "cryptography>=3.4.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "orjson>=3.8.0",
    "cachetools>=5.0.0",
    "tenacity>=8.0.0",
    "apscheduler>=3.10.0",
    "markdown>=3.4.0",
    "watchdog>=3.0.0",
    "click>=8.0.0",
    "tqdm>=4.64.0",
    "loguru>=0.7.0",
    "pytz>=2023.3",
    "typing-extensions>=4.0.0",
    "websocket-client>=1.6.0",
]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "coverage>=7.0.0",
    "ruff>=0.4.0",
    "mypy>=1.5.0",
    "pre-commit>=3.5.0",
]

[tool.setuptools.packages.find]
include = ["modules*", "core*", "infrastructure*", "config*", "backend*", "scripts*"]

[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D", "ANN"]
"scripts/**" = ["D", "ANN"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.10"
strict = false
warn_return_any = true
warn_unused_configs = true
exclude = [
    "frontend/",
    "generated/",
    ".venv/",
    "node_modules/",
]

[[tool.mypy.overrides]]
module = ["modules.*", "core.*", "backend.*", "infrastructure.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: fast isolated tests",
    "integration: tests that wire multiple modules together",
    "slow: tests that take more than a few seconds",
]
asyncio_mode = "auto"
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["modules", "core", "infrastructure", "config"]
omit = ["tests/*", "scripts/*", "frontend/*"]
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
-r requirements.txt

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
coverage>=7.0.0
ruff>=0.4.0
mypy>=1.5.0
pre-commit>=3.5.0
```

- [ ] **Step 3: Verify pyproject.toml parses correctly**

```bash
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml requirements-dev.txt
git commit -m "feat: add pyproject.toml with project metadata, tool config, and dep groups"
```

---

### Task 4: Add pre-commit config

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=1000"]
      - id: no-commit-to-branch
        args: ["--branch", "main"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format
```

- [ ] **Step 2: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: add pre-commit config with ruff and standard hooks"
```

---

### Task 5: Add CI pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-minimal.txt
          pip install -r requirements-dev.txt

      - name: Ruff check
        run: ruff check .

      - name: Ruff format check
        run: ruff format --check .

      - name: Run tests
        run: pytest tests/ -m "not slow" --cov --cov-report=term-missing
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI pipeline with ruff and pytest"
```

---

### Task 6: Create conftest.py with shared fixtures

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
import pytest
import tempfile
import shutil
from pathlib import Path

from infrastructure.event_bus import EnhancedEventBus


@pytest.fixture
def event_bus():
    bus = EnhancedEventBus()
    yield bus
    bus.clear()


@pytest.fixture
def fresh_container():
    from container import Container

    c = Container()
    c._initialized = False
    c.__init__()
    yield c
    c.reset()


@pytest.fixture
def tmp_output_dir(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    return out


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast isolated tests")
    config.addinivalue_line("markers", "integration: tests wiring multiple modules")
    config.addinivalue_line("markers", "slow: tests taking more than a few seconds")
```

- [ ] **Step 2: Verify conftest loads**

```bash
python -m pytest tests/conftest.py --co
```

Expected: No errors (may show 0 tests collected, which is fine).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add conftest.py with shared pytest fixtures"
```

---

### Task 7: Rewrite test_foundation.py

**Files:**
- Rewrite: `tests/test_foundation.py`

- [ ] **Step 1: Rewrite as proper pytest**

Replace entire contents of `tests/test_foundation.py`:

```python
import os
import pytest

from infrastructure.event_bus import EnhancedEventBus, DomainEvent
from config.enhanced_settings import EnhancedConfig
from modules.crystal import CrystalService, CrystalBroadcastStarted, CrystalBroadcastCompleted
from modules.blessing_router import BlessingRouter, BlessingRouted, TargetSpecification, TargetType, DeliveryMethod
from modules.enhanced_scalar_waves import EnhancedScalarWaveService, WaveSessionStarted


@pytest.mark.unit
class TestEventBusPersistence:
    def test_publish_and_subscribe(self, event_bus, tmp_path):
        path = tmp_path / "test_events.jsonl"
        bus = EnhancedEventBus(persistence_path=str(path))

        class TestEvent(DomainEvent):
            def __init__(self, message: str):
                super().__init__()
                self.message = message

        received = []
        bus.subscribe(TestEvent, lambda e: received.append(e))
        bus.publish(TestEvent("Hello World"))

        assert len(received) == 1
        assert received[0].message == "Hello World"
        assert path.exists()

        content = path.read_text()
        assert "Hello World" in content


@pytest.mark.unit
class TestCrystalService:
    def test_broadcast_intention(self, event_bus):
        service = CrystalService(event_bus)

        events = []
        event_bus.subscribe(CrystalBroadcastStarted, lambda e: events.append(e))
        event_bus.subscribe(CrystalBroadcastCompleted, lambda e: events.append(e))

        result = service.broadcast_intention("Healing Light", duration=1)

        assert result["status"] == "completed"
        assert len(events) == 2
        assert isinstance(events[0], CrystalBroadcastStarted)
        assert isinstance(events[1], CrystalBroadcastCompleted)
        assert events[0].intention == "Healing Light"


@pytest.mark.unit
class TestBlessingRouter:
    def test_route_blessing(self, event_bus):
        router = BlessingRouter(event_bus)

        events = []
        event_bus.subscribe(BlessingRouted, lambda e: events.append(e))

        target = TargetSpecification(TargetType.INDIVIDUAL, "John Doe")
        router.route_blessing("Peace", target, DeliveryMethod.DIRECT)

        assert len(events) == 1
        assert isinstance(events[0], BlessingRouted)
        assert events[0].intention == "Peace"
        assert events[0].target_spec.identifier == "John Doe"


@pytest.mark.unit
class TestEnhancedScalarWaves:
    def test_create_wave_session(self, event_bus):
        service = EnhancedScalarWaveService(event_bus)

        events = []
        event_bus.subscribe(WaveSessionStarted, lambda e: events.append(e))

        session_id = service.create_wave_session("lorenz", count=100)

        assert session_id is not None
        assert len(events) == 1
        assert isinstance(events[0], WaveSessionStarted)
        assert events[0].session_id == session_id


@pytest.mark.unit
class TestConfiguration:
    def test_default_config(self):
        config = EnhancedConfig("test")
        assert config.get("audio.sample_rate") == 44100
        assert config.get("hardware.level") in [2, 3]
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_foundation.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_foundation.py
git commit -m "test: rewrite test_foundation.py as proper pytest with fixtures"
```

---

### Task 8: Rewrite test_monolith.py → test_container_modules.py

**Files:**
- Rename: `tests/test_monolith.py` → `tests/test_container_modules.py`

- [ ] **Step 1: Create `tests/test_container_modules.py`**

```python
from pathlib import Path

import pytest


@pytest.mark.integration
class TestScalarWaves:
    def test_generate_qrng(self, fresh_container):
        scalar = fresh_container.scalar_waves
        result = scalar.generate("qrng", 1000, 1.0)
        assert result["count"] > 0
        assert result["method"] == "qrng"
        assert "mops" in result

    def test_thermal_status(self, fresh_container):
        scalar = fresh_container.scalar_waves
        thermal = scalar.get_thermal_status()
        assert "temperature" in thermal
        assert "status" in thermal


@pytest.mark.integration
class TestRadionics:
    def test_available_intentions(self, fresh_container):
        radionics = fresh_container.radionics
        intentions = radionics.get_available_intentions()
        assert len(intentions) > 0

    def test_broadcast_healing(self, fresh_container):
        radionics = fresh_container.radionics
        result = radionics.broadcast_healing("Test Target", 1, 528)
        assert "session_id" in result
        assert result["target"] == "Test Target"


@pytest.mark.integration
class TestAnatomy:
    def test_chakra_info(self, fresh_container):
        anatomy = fresh_container.anatomy
        chakras = anatomy.get_chakra_info()
        assert len(chakras) == 7

    def test_meridian_info(self, fresh_container):
        anatomy = fresh_container.anatomy
        meridians = anatomy.get_meridian_info()
        assert len(meridians) == 12

    def test_visualize_chakras(self, fresh_container, tmp_output_dir):
        anatomy = fresh_container.anatomy
        path = anatomy.visualize_chakras(width=800, height=1000, output_path=str(tmp_output_dir / "chakras.png"))
        assert Path(path).exists()


@pytest.mark.integration
class TestBlessings:
    def test_generate_blessing(self, fresh_container):
        blessings = fresh_container.blessings
        result = blessings.generate_blessing("All Beings", "peace and happiness", "universal")
        assert "blessing_text" in result
        assert len(result["blessing_text"]) > 0

    def test_available_traditions(self, fresh_container):
        blessings = fresh_container.blessings
        traditions = blessings.get_available_traditions()
        assert len(traditions) > 0


@pytest.mark.integration
class TestEventBus:
    def test_publish_and_receive(self, fresh_container):
        from modules.interfaces import ScalarWavesGenerated
        from datetime import datetime

        events = []
        fresh_container.event_bus.subscribe(ScalarWavesGenerated, lambda e: events.append(e))

        event = ScalarWavesGenerated(
            timestamp=datetime.now(),
            event_id="test-123",
            method="qrng",
            count=1000,
            mops=1.5,
        )
        fresh_container.event_bus.publish(event)

        assert len(events) == 1
        assert events[0].method == "qrng"

        fresh_container.event_bus.unsubscribe(ScalarWavesGenerated, events.append)
```

- [ ] **Step 2: Delete old test_monolith.py**

```bash
rm tests/test_monolith.py
```

- [ ] **Step 3: Run the tests**

```bash
python -m pytest tests/test_container_modules.py -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_container_modules.py
git rm tests/test_monolith.py
git commit -m "test: rewrite test_monolith.py as test_container_modules.py with proper pytest"
```

---

### Task 9: Rewrite test_basic_functionality.py → test_services.py

**Files:**
- Rename: `tests/test_basic_functionality.py` → `tests/test_services.py`

- [ ] **Step 1: Create `tests/test_services.py`**

```python
import pytest


@pytest.mark.integration
class TestContainerInit:
    def test_container_imports(self):
        from container import container
        assert container is not None

    def test_scalar_waves_accessible(self, fresh_container):
        assert fresh_container.scalar_waves is not None

    def test_radionics_accessible(self, fresh_container):
        assert fresh_container.radionics is not None

    def test_blessings_accessible(self, fresh_container):
        assert fresh_container.blessings is not None


@pytest.mark.integration
class TestVisualizationModule:
    def test_loads_and_reports_status(self):
        from modules.visualization import VisualizationService
        viz = VisualizationService()
        status = viz.get_status()
        assert "rothko_available" in status
        assert "energetic_viz_available" in status


@pytest.mark.integration
class TestAnatomyModule:
    def test_loads_with_visualization_flag(self):
        from modules.anatomy import AnatomyService
        anatomy = AnatomyService()
        assert hasattr(anatomy, "has_visualization")


@pytest.mark.integration
class TestAudioModule:
    def test_loads_and_reports_status(self):
        from modules.audio import AudioService
        audio = AudioService()
        status = audio.get_status()
        assert "audio_generator" in status
        assert "tts" in status


@pytest.mark.integration
class TestAPIImport:
    def test_fastapi_app_imports(self):
        from backend.app.main import app
        assert app is not None
```

- [ ] **Step 2: Delete old test_basic_functionality.py**

```bash
rm tests/test_basic_functionality.py
```

- [ ] **Step 3: Run the tests**

```bash
python -m pytest tests/test_services.py -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_services.py
git rm tests/test_basic_functionality.py
git commit -m "test: rewrite test_basic_functionality.py as test_services.py with proper pytest"
```

---

### Task 10: Rewrite test_rng_service.py

**Files:**
- Rewrite: `tests/test_rng_service.py`

- [ ] **Step 1: Rewrite as proper pytest**

Replace entire contents of `tests/test_rng_service.py`:

```python
import pytest

from backend.core.services.rng_attunement_service import (
    RNGAttunementService,
    NeedleState,
    ReadingQuality,
)


@pytest.fixture
def rng_service():
    return RNGAttunementService()


@pytest.fixture
def rng_session(rng_service):
    session_id = rng_service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)
    yield session_id
    rng_service.stop_session(session_id)


@pytest.mark.unit
class TestRNGServiceLifecycle:
    def test_create_session(self, rng_service):
        session_id = rng_service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)
        assert session_id is not None
        rng_service.stop_session(session_id)

    def test_stop_session(self, rng_service):
        session_id = rng_service.create_session(baseline_tone_arm=5.0, sensitivity=1.0)
        assert rng_service.stop_session(session_id) is True
        assert rng_service.get_reading(session_id) is None


@pytest.mark.unit
class TestRNGReadings:
    def test_get_reading_returns_valid_data(self, rng_service, rng_session):
        reading = rng_service.get_reading(rng_session)
        assert reading is not None
        assert 0.0 <= reading.raw_value <= 1.0
        assert 0.0 <= reading.tone_arm <= 10.0
        assert -100 <= reading.needle_position <= 100
        assert isinstance(reading.needle_state, NeedleState)
        assert isinstance(reading.quality, ReadingQuality)
        assert 0.0 <= reading.coherence <= 1.0
        assert 0.0 <= reading.entropy <= 1.0
        assert 0.0 <= reading.floating_needle_score <= 1.0

    def test_readings_vary(self, rng_service, rng_session):
        r1 = rng_service.get_reading(rng_session)
        r2 = rng_service.get_reading(rng_session)
        assert r1.raw_value != r2.raw_value


@pytest.mark.unit
class TestRNGSessionSummary:
    def test_summary_after_readings(self, rng_service, rng_session):
        for _ in range(5):
            rng_service.get_reading(rng_session)

        summary = rng_service.get_session_summary(rng_session)
        assert summary is not None
        assert summary["total_readings"] == 5
        assert summary["is_active"] is True
        assert "avg_tone_arm" in summary
        assert "avg_coherence" in summary
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_rng_service.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_rng_service.py
git commit -m "test: rewrite test_rng_service.py as proper pytest with fixtures"
```

---

### Task 11: Rewrite test_radionics_enhancer.py

**Files:**
- Rewrite: `tests/test_radionics_enhancer.py`

- [ ] **Step 1: Rewrite as pytest**

Replace entire contents:

```python
import pytest

from modules.radionics_enhancer import RadionicsEnhancer, StructuralLink


@pytest.fixture
def enhancer():
    return RadionicsEnhancer()


@pytest.mark.unit
class TestEntropy:
    def test_entropy_in_range(self, enhancer):
        entropy = enhancer.get_entropy_value()
        assert isinstance(entropy, float)
        assert 0.0 <= entropy <= 1.0

    def test_entropy_varies(self, enhancer):
        e1 = enhancer.get_entropy_value()
        e2 = enhancer.get_entropy_value()
        assert e1 != e2


@pytest.mark.unit
class TestRateAttunement:
    def test_attune_rate_in_range(self, enhancer):
        rate = enhancer.attune_rate("Healing for the World")
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 100.0


@pytest.mark.unit
class TestTrendPadding:
    def test_fibonacci_padding(self, enhancer):
        padded = enhancer.apply_trend_padding("test_signal", padding_type="fibonacci", repetitions=3)
        assert len(padded) == 6
        assert padded[0] == "test_signal"

    def test_exponential_padding(self, enhancer):
        padded = enhancer.apply_trend_padding("test_signal", padding_type="exponential", repetitions=3)
        assert len(padded) == 7


@pytest.mark.unit
class TestStructuralLink:
    def test_create_link(self, enhancer):
        link = enhancer.create_structural_link(
            link_type="digital",
            target="John Doe",
            metadata={"notes": "Test Subject"},
        )
        assert isinstance(link, StructuralLink)
        assert link.target == "John Doe"
        assert link.link_type == "digital"
        assert link.id in enhancer.active_links
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_radionics_enhancer.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_radionics_enhancer.py
git commit -m "test: rewrite test_radionics_enhancer.py as proper pytest"
```

---

### Task 12: Rewrite test_server.py

**Files:**
- Rewrite: `tests/test_server.py`

- [ ] **Step 1: Rewrite as pytest**

Replace entire contents:

```python
from fastapi.testclient import TestClient

import pytest


@pytest.fixture
def client():
    from backend.app.main import app
    return TestClient(app)


@pytest.mark.integration
class TestServerHealth:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
```

- [ ] **Step 2: Run the tests**

```bash
python -m pytest tests/test_server.py -v
```

Expected: Tests PASS (some may fail if backend deps missing, which is acceptable — mark those with `pytest.mark.skip` if needed).

- [ ] **Step 3: Commit**

```bash
git add tests/test_server.py
git commit -m "test: rewrite test_server.py as proper pytest with TestClient"
```

---

### Task 13: Remove sys.path hacks from source files

**Files:**
- Modify: `container.py` (remove lines 21-22, add type hints)
- Modify: `vajra_stream_v2.py` (remove lines 16-23)
- Modify: `backend/app/main.py` (remove line 19)

- [ ] **Step 1: Edit `container.py`**

Remove these lines:
```python
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
```

Remove the `import sys` and `from pathlib import Path` imports if no longer used (keep `sys` for the Windows encoding block on lines 16-21).

Add return type annotations to all properties. Each property should have a return type, e.g.:

```python
@property
def scalar_waves(self) -> "ScalarWaveService":
```

For modules with optional dependencies, use `Optional`:
```python
@property
def astrology(self) -> "Optional[AstrologyService]":
```

Add `from typing import Optional` to imports.

- [ ] **Step 2: Edit `vajra_stream_v2.py`**

Remove the `sys.path.insert` line (line 23):
```python
sys.path.insert(0, str(Path(__file__).parent))
```

- [ ] **Step 3: Edit `backend/app/main.py`**

Remove line 19:
```python
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
```

- [ ] **Step 4: Run tests to verify nothing broke**

```bash
python -m pytest tests/ -v
```

Expected: Same number of tests passing as before.

- [ ] **Step 5: Commit**

```bash
git add container.py vajra_stream_v2.py backend/app/main.py
git commit -m "refactor: remove sys.path.insert hacks, add type hints to container"
```

---

### Task 14: Add directory ownership docs

**Files:**
- Create: `modules/README.md`
- Create: `core/README.md`

- [ ] **Step 1: Create `modules/README.md`**

```markdown
# modules/ — Service Layer

This is the **canonical location** for all Vajra.Stream service modules. Each module exposes a service class that is instantiated by the DI container (`container.py`).

## Module Index

| Module | Service Class | Description |
|--------|--------------|-------------|
| `scalar_waves.py` | `ScalarWaveService` | Scalar wave generation (QRNG, Lorenz, etc.) |
| `radionics.py` | `RadionicsService` | Radionics broadcasting |
| `anatomy.py` | `AnatomyService` | Chakra and meridian systems |
| `blessings.py` | `BlessingService` | Blessing generation |
| `audio.py` | `AudioService` | Audio synthesis and TTS |
| `visualization.py` | `VisualizationService` | Sacred geometry and Rothko art |
| `astrology.py` | `AstrologyService` | Astrological calculations |
| `time_cycles.py` | `TimeCyclesService` | Kalachakra time-space healing |
| `prayer_wheel.py` | `PrayerWheelService` | Digital prayer wheel |
| `composer.py` | `ComposerService` | Healing music composition |
| `healing.py` | `HealingService` | Comprehensive healing systems |
| `llm.py` | `LLMService` | LLM integration |

## Convention

All service classes accept `event_bus` as their first constructor argument. They communicate through the event bus defined in `infrastructure/event_bus.py`.
```

- [ ] **Step 2: Create `core/README.md`**

```markdown
# core/ — Internal Implementations

This directory contains internal rendering engines, generators, and shared utilities used by the service modules. Code here is **not** directly wired into the DI container — it is consumed by `modules/` services.

## Contents

| File | Description |
|------|-------------|
| `audio_generator.py` | Low-level audio synthesis engine |
| `visual_display.py` | Terminal-based visual display |
| `visual_renderer_simple.py` | Simple image renderer |
| `tts_engine.py` | Text-to-speech engine |
| `radionics_engine.py` | Core radionics computation |
| `advanced_scalar_waves.py` | Advanced scalar wave algorithms |
| `energetic_anatomy.py` | Energetic anatomy data and logic |
| `blessing_narratives.py` | Narrative generation engine |
| `dharma_tales.py` | Dharma story generation |
| `rothko_generator.py` | Rothko-style art generation |
| `llm_integration.py` | LLM API integration layer |

## Guideline

If you're adding new functionality, create the service class in `modules/` and put internal helpers here.
```

- [ ] **Step 3: Commit**

```bash
git add modules/README.md core/README.md
git commit -m "docs: add directory ownership docs for modules/ and core/"
```

---

### Task 15: Run ruff and fix issues

**Files:**
- Possibly modify: multiple source files (auto-fixed by ruff)

- [ ] **Step 1: Run ruff check with auto-fix**

```bash
python -m ruff check --fix .
```

Expected: Ruff fixes import ordering, unused imports, and other auto-fixable issues.

- [ ] **Step 2: Run ruff format**

```bash
python -m ruff format .
```

Expected: All files reformatted to consistent style.

- [ ] **Step 3: Run tests to verify nothing broke**

```bash
python -m pytest tests/ -v
```

Expected: Same tests passing.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "style: apply ruff lint fixes and formatting"
```

---

### Task 16: Final verification

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass. Note the count — should be ~25 tests across 6 files.

- [ ] **Step 2: Run ruff check (no fixes)**

```bash
python -m ruff check .
```

Expected: Clean output, no errors.

- [ ] **Step 3: Verify git status is clean**

```bash
git status
```

Expected: `nothing to commit, working tree clean` (or only expected changes).

- [ ] **Step 4: Verify deleted files are gone and new files are tracked**

```bash
git log --oneline -10
```

Expected: See commits from all tasks above.
