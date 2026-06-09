# Contributing to Vajra.Stream

Thank you for your interest in contributing to Vajra.Stream! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Harassment, trolling, or discriminatory comments
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, Node version)
- **Error messages or logs**
- **Screenshots** (if applicable)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When suggesting enhancements:

- **Use a clear title**
- **Provide detailed description** of the proposed functionality
- **Explain why this enhancement would be useful**
- **List examples** of how the feature would be used

### Contributing Code

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test your changes**
5. **Commit with descriptive messages**
6. **Push to your fork**
7. **Open a Pull Request**

## Development Setup

### Prerequisites

**Backend:**
- Python 3.10+ (< 3.14)
- pip
- Virtual environment tool (venv, conda, etc.)

**Frontend:**
- Node.js 16+
- npm or yarn

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/LeouOn/vajra-stream.git
cd vajra-stream

# Backend setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"  # Install with dev dependencies

# Frontend setup
cd frontend
npm install
cd ..
```

### Running the Application

**Start Backend:**
```bash
cd /path/to/vajra-stream
PYTHONPATH=/path/to/vajra-stream:$PYTHONPATH uvicorn backend.app.main:app --host 0.0.0.0 --port 8008 --reload
```

**Start Frontend:**
```bash
cd frontend
npm run dev
```

Access the application:
- Frontend: http://localhost:3009
- Backend API: http://localhost:8008
- API Docs: http://localhost:8008/docs

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed project organization.

```
vajra-stream/
├── backend/          # FastAPI backend application
├── frontend/         # React/Vite frontend application
├── core/             # Core processing engines
├── modules/          # Feature modules
├── hardware/         # Hardware interfaces
├── tests/            # Test suite
├── docs/             # Documentation
├── knowledge/        # Reference data and knowledge bases
├── scripts/          # Utility scripts
└── config/           # Configuration files
```

## Coding Standards

### Python

**Style Guide:**
- Follow PEP 8
- Use Black for formatting (max line length: 100)
- Use isort for import sorting
- Use type hints where possible
- Write docstrings for all public functions/classes

**Linting:**
```bash
# Format code
black .

# Sort imports
isort .

# Check style
flake8 .

# Type checking (when ready)
mypy .
```

**Example:**
```python
from typing import Optional

def calculate_frequency(
    base_freq: float,
    harmonic: int = 1,
    modulation: Optional[float] = None
) -> float:
    """
    Calculate harmonic frequency with optional modulation.

    Args:
        base_freq: Base frequency in Hz
        harmonic: Harmonic multiplier (default: 1)
        modulation: Optional modulation depth (0.0-1.0)

    Returns:
        Calculated frequency in Hz

    Raises:
        ValueError: If parameters are out of valid range
    """
    if base_freq <= 0:
        raise ValueError("Base frequency must be positive")

    freq = base_freq * harmonic

    if modulation is not None:
        freq *= (1 + modulation)

    return freq
```

### JavaScript/React

**Style Guide:**
- Use Prettier for formatting
- Follow ESLint recommendations
- Use functional components with hooks
- Prop-types or TypeScript for type checking
- Clear component naming (PascalCase)

**Linting:**
```bash
cd frontend

# Format code
npm run format

# Check linting
npm run lint
```

**Example:**
```javascript
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

/**
 * FrequencyControl - Component for controlling audio frequency
 */
const FrequencyControl = ({ frequency, onChange, min = 0, max = 20000 }) => {
  const [value, setValue] = useState(frequency);

  useEffect(() => {
    setValue(frequency);
  }, [frequency]);

  const handleChange = (e) => {
    const newValue = parseFloat(e.target.value);
    setValue(newValue);
    onChange(newValue);
  };

  return (
    <div className="frequency-control">
      <label>Frequency: {value} Hz</label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={handleChange}
      />
    </div>
  );
};

FrequencyControl.propTypes = {
  frequency: PropTypes.number.isRequired,
  onChange: PropTypes.func.isRequired,
  min: PropTypes.number,
  max: PropTypes.number,
};

export default FrequencyControl;
```

## Testing

### Writing Tests

**Python Tests (pytest):**
```python
import pytest
from core.audio_generator import generate_prayer_bowl

def test_audio_generation():
    """Test basic audio generation"""
    audio = generate_prayer_bowl(frequency=136.1, duration=1.0)
    assert audio is not None
    assert len(audio) > 0

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality"""
    result = await async_function()
    assert result is not None

def test_error_handling():
    """Test error handling"""
    with pytest.raises(ValueError):
        generate_prayer_bowl(frequency=-1)
```

**JavaScript Tests (Vitest):**
```javascript
import { describe, it, expect } from 'vitest';
import { calculateHarmonic } from './utils';

describe('calculateHarmonic', () => {
  it('should calculate first harmonic correctly', () => {
    expect(calculateHarmonic(440, 1)).toBe(440);
  });

  it('should handle octaves', () => {
    expect(calculateHarmonic(440, 2)).toBe(880);
  });

  it('should throw error for invalid input', () => {
    expect(() => calculateHarmonic(-1, 1)).toThrow();
  });
});
```

### Running Tests

```bash
# Run all Python tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_audio_service.py

# Run frontend tests
cd frontend
npm test
```

### Coverage Requirements

- Aim for **80%+ coverage** for new code
- All public APIs should have tests
- Critical paths must be tested
- Edge cases and error handling required

## Pull Request Process

### Before Submitting

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Run linters** and fix issues
4. **Run test suite** and ensure all pass
5. **Update CHANGELOG.md** with changes
6. **Ensure commits are clear** and descriptive

### PR Guidelines

**Title Format:**
```
[Type] Brief description

Examples:
[Feature] Add astrocartography visualization
[Fix] Resolve WebSocket connection issue
[Docs] Update API documentation
[Refactor] Reorganize test structure
[Performance] Optimize audio generation
```

**Description Should Include:**
- Summary of changes
- Motivation and context
- Related issues (closes #123)
- Breaking changes (if any)
- Screenshots (for UI changes)

**Example PR Description:**
```markdown
## Summary
Add astrocartography 3D globe visualization with planetary lines.

## Motivation
Enables users to visualize astrological influences across geographic locations.

## Changes
- Created Astrocartography.jsx component
- Integrated with astrology backend API
- Added to visualization selector
- Updated documentation

## Related Issues
Closes #45

## Screenshots
[Include screenshots]

## Testing
- Tested on Chrome, Firefox, Safari
- Verified API integration
- Added unit tests for planetary line calculations
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **At least one review** required
3. **Address feedback** from reviewers
4. **Squash commits** if requested
5. **Maintainer merges** approved PRs

## Documentation

### When to Update Documentation

**Always update docs when:**
- Adding new features
- Changing APIs
- Modifying configuration
- Updating dependencies
- Changing project structure

### Documentation Locations

- **API changes** → `API_DOCUMENTATION.md`
- **User guides** → `docs/guides/`
- **Implementation details** → `docs/implementation/`
- **Architecture changes** → `docs/architecture/`
- **Code documentation** → Inline docstrings and comments

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams when helpful
- Keep links up to date
- Use proper markdown formatting

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Create an issue with bug template
- **Features:** Create an issue with feature template
- **Chat:** (Add Discord/Slack link if available)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

**Thank you for contributing to Vajra.Stream!** 🙏

_May your code bring healing to all beings._
