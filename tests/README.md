# Vajra.Stream Test Suite

This directory contains all automated tests for the Vajra.Stream project.

## Directory Structure

```
tests/
├── unit/                  # Unit tests for individual modules
├── integration/           # Integration tests for module interactions
├── e2e/                   # End-to-end tests (future)
├── scripts/               # Utility test scripts (deprecated - being migrated)
├── test_foundation.py     # Core foundation tests
├── test_integration_phase2.py
├── test_api_endpoints.py  # API endpoint tests
├── test_radionics_enhancer.py
└── README.md             # This file
```

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
Tests for individual functions, classes, and modules in isolation.

**Currently includes:**
- Audio generation and playback tests
- RNG API and service tests
- TTS system tests
- Basic functionality tests
- Visualization tests
- Server tests

### Integration Tests (`tests/integration/`)
Tests for interactions between multiple modules and system components.

**Currently includes:**
- Full system integration tests
- WebSocket connection tests
- Module connection tests
- Session creation tests
- Full stack simulation tests
- Data loading tests

### End-to-End Tests (`tests/e2e/`)
Tests that simulate real user workflows (to be implemented).

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

Tests are configured via `pyproject.toml` (to be added):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=. --cov-report=html --cov-report=term"
```

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
