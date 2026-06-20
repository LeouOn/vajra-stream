# Vajra.Stream Test Suite

This directory contains all automated tests for the Vajra.Stream project.

## Directory Structure

```
tests/
├── conftest.py            # Shared fixtures (event_bus, fresh_container, geocoding patch)
├── README.md              # This file
├── unit/                  # Unit tests — single module/function in isolation
├── integration/           # Integration tests — multiple modules / TestClient / DB
├── e2e/                   # End-to-end tests — full user workflows
├── backend/               # Tests for backend/app config & endpoints
└── core/                  # Tests for core subsystems (llm/, context/)
```

No `test_*.py` files live at the `tests/` root — every test belongs to exactly
one of the structured subdirectories above (see `Issue 5.9` / deferred Task 5).

## Running Tests

### Run All Tests
```bash
# From project root
pytest

# With coverage
pytest --cov=. --cov-report=html --cov-report=term
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_rng_service.py
```

### Run Tests with Verbose Output
```bash
pytest -v
pytest -vv  # Extra verbose
```

## Test Categories

### Unit Tests (`tests/unit/`)
Tests for individual functions, classes, and modules in isolation (no HTTP
server, no DB, no external services). Marked with `@pytest.mark.unit`.

**Includes:** foundation/event-bus, ritual engine & scheduler, prayer wheel,
radionics enhancer/operator, divination, sigils, RNG service, astrology
calculator, auspicious timing, core modules, LLM routing/tool-schemas, transit
export, endpoints init sync, and several structural guardrails
(no-dead-duplicates, no-new-ruff-suppressions, docs-no-ghost-paths, etc.).

### Integration Tests (`tests/integration/`)
Tests for interactions between multiple modules and system components, often
via `TestClient(app)` against the real FastAPI app or a SQLite DB. Marked with
`@pytest.mark.integration`.

**Includes:** server health, audio API, container modules, services, outlook
loop/import-export, LLM models & routing integration, extraction, and the
cross-module integration suite.

### End-to-End Tests (`tests/e2e/`)
Tests that simulate real user workflows across the full stack. Marked with
`@pytest.mark.e2e`. Some require a live LM Studio instance and are skipped
when unavailable.

**Includes:** full workflow, astrology e2e, extraction e2e, LLM e2e,
orchestration, autonomous agent, outlook API/generator e2e.

### Backend & Core Subdirs (`tests/backend/`, `tests/core/`)
`tests/backend/` covers `backend/app` config and endpoint smoke tests.
`tests/core/` mirrors the `core/` package layout with `core/llm/` (provider,
registry, retry, cache, health, models, base) and `core/context/` (system
prompt builder, hardware, astrology, anatomy).

## Writing Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test functions: `test_<functionality>()`
- Test classes: `Test<ClassName>`

### Example Test Structure
```python
import pytest
from your_module import your_function

def test_your_function_basic():
    """Test basic functionality"""
    result = your_function(input_data)
    assert result == expected_output

def test_your_function_error_handling():
    """Test error handling"""
    with pytest.raises(ValueError):
        your_function(invalid_input)

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality"""
    result = await async_function()
    assert result is not None
```

## Test Configuration

Tests are configured via `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["unit", "integration", "e2e", "slow"]
asyncio_mode = "auto"
```

`tests/__init__.py` and `tests/unit/__init__.py` make those directories proper
packages so that test modules sharing a basename (e.g. `test_astrology.py` in
both `tests/unit/` and `tests/core/context/`) import under distinct dotted
names (`tests.unit.test_astrology` vs bare `test_astrology`) — no collection
collisions.

## Coverage

Current coverage: To be measured
Target coverage: 80%+

View coverage report after running tests:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Nightly builds

See `.github/workflows/ci.yml` for CI configuration (to be added).

## Dependencies

Test dependencies are specified in `requirements.txt`:
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- pytest-cov>=4.1.0

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Ensure you're in project root and have PYTHONPATH set
export PYTHONPATH=/home/user/vajra-stream:$PYTHONPATH
pytest
```

**Module not found:**
```bash
# Install all dependencies
pip install -r requirements.txt
```

**Async test failures:**
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

## Contributing

When adding new features:
1. Write tests first (TDD approach recommended)
2. Ensure tests pass locally before pushing
3. Aim for >80% code coverage for new code
4. Update this README if adding new test categories

## Future Improvements

- [ ] Add frontend component tests (Vitest)
- [ ] Add E2E tests with Playwright/Cypress
- [ ] Increase test coverage to 80%+
- [ ] Add performance/load tests
- [ ] Add security tests
- [ ] Setup test fixtures and factories
- [ ] Add mutation testing
