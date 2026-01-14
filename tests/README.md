# Tests

This directory contains the test suite for the Oceans of NYC project.

## Structure

```
tests/
├── test_*.py           # Unit tests for pure functions
├── mocks/              # Mock implementations of external services
├── fixtures/           # Test data fixtures (images, data files)
└── integration/        # Integration tests (require external services)
```

## Running Tests

### Install Test Dependencies

```bash
pip install -e ".[test]"
```

### Run All Tests

```bash
pytest
```

### Run Only Unit Tests (Fast)

```bash
pytest -m unit
```

### Run with Coverage Report

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Run Specific Test File

```bash
pytest tests/test_geolocate.py -v
```

### Run Integration Tests (Requires External Services)

```bash
RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v
```

## Test Markers

Tests are marked with pytest markers to categorize them:

- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.integration` - Tests that require external services (R2, Bluesky, Twilio)
- `@pytest.mark.e2e` - End-to-end tests (full workflow)
- `@pytest.mark.slow` - Tests that take >1s to run

## Test Coverage Goals

- **Current:** ~5% (extractors only)
- **Phase 1 Target:** 30% (pure functions)
- **Phase 2 Target:** 50% (database operations)
- **Phase 3 Target:** 70% (integration)
- **Long-term Target:** 80%

## Writing Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test functions: `test_<specific_behavior>`

### Example Test Structure

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    """Test suite for my feature."""

    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Arrange
        input_data = "test"

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected_output
```

## Current Test Coverage

### Unit Tests (Pure Functions)

- ✅ `test_extractors.py` - License plate and borough extraction (16 tests)
- ✅ `test_geolocate.py` - Borough detection from coordinates (28 tests)
- ✅ `test_image_hashing.py` - Hamming distance calculations (18 tests)
- ✅ `test_validate_matcher.py` - Plate similarity logic (20 tests)

### Database Tests

- 🚧 Coming in Phase 2

### Integration Tests

- 🚧 Coming in Phase 3

## Resources

- Full testing strategy: [TESTING_STRATEGY.md](../TESTING_STRATEGY.md)
- pytest documentation: https://docs.pytest.org/
- Coverage documentation: https://coverage.readthedocs.io/
