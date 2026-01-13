# Testing Strategy for Oceans of NYC

## Executive Summary

This document outlines a comprehensive testing strategy for the Oceans of NYC Python codebase, which currently has minimal test coverage (16 tests covering only text extractors). The project integrates multiple external services (Twilio, Bluesky, Cloudflare R2, Neon PostgreSQL) and runs on Modal's serverless platform.

## Current State

**Existing Tests:**
- [tests/test_extractors.py](tests/test_extractors.py) - 16 tests for plate and borough extraction
- Coverage: ~5% of codebase (extractors only)
- Framework: pytest (implicit)

**No Tests For:**
- Database operations and duplicate detection
- SMS/MMS webhook handling and chat flow
- Bluesky posting and image compression
- R2 storage operations
- TLC vehicle validation
- Image processing and hashing
- Modal endpoints
- Integration between components

## Testing Philosophy

Given the project's characteristics:
- Small team/solo maintainer
- Community-driven project (not commercial/SLA-bound)
- Heavy reliance on external services
- Serverless deployment (Modal)

**Prioritize:**
1. **Critical path testing** - Duplicate detection, chat flow, posting logic
2. **Pure function testing** - High ROI, fast to write and run
3. **Integration tests with mocks** - Validate component interactions
4. **Minimal E2E testing** - Only for critical workflows

**Avoid:**
- 100% coverage goals (diminishing returns)
- Heavy mocking that duplicates implementation logic
- Tests that are more complex than the code they test

## Testing Layers

### Layer 1: Unit Tests (Pure Functions)

**Target: Functions with no side effects or external dependencies**

Priority areas:
- ✅ `chat/extractors.py` - Already tested (maintain these)
- `geolocate/boroughs.py::get_borough_from_coords()` - Coordinate → borough mapping
- `geolocate/boroughs.py::parse_borough_input()` - User input normalization
- `utils/image_hashing.py::hamming_distance()` - Distance calculation
- `validate/matcher.py::find_similar_plates()` - Levenshtein distance logic
- `post/bluesky.py::_format_batch_text()` - Text generation (if extracted)
- `post/bluesky.py::_generate_progress_bar()` - Progress visualization

**Test Characteristics:**
- Fast (<1ms per test)
- No mocking required
- High coverage of edge cases
- Property-based testing where appropriate (e.g., hamming distance properties)

**Example Test Structure:**
```python
# tests/test_geolocate.py
def test_get_borough_from_coords_manhattan():
    assert get_borough_from_coords(40.7589, -73.9851) == "Manhattan"

def test_get_borough_from_coords_outside_nyc():
    assert get_borough_from_coords(0, 0) is None

def test_parse_borough_input_case_insensitive():
    assert parse_borough_input("BROOKLYN") == "Brooklyn"
    assert parse_borough_input("bk") == "Brooklyn"
```

### Layer 2: Unit Tests (With Database Fixtures)

**Target: Database operations that can run against test DB**

Priority areas:
- `database/models.py::SightingsDatabase.add_sighting()` - Duplicate detection
- `database/models.py::SightingsDatabase.get_unposted_sightings()` - Post queue
- `database/models.py::SightingsDatabase.mark_as_posted()` - Status updates
- `validate/matcher.py::validate_plate()` - TLC lookup
- `chat/session.py::ChatSession` - Session state management

**Strategy:**
- Use pytest fixtures for database setup/teardown
- Test against local PostgreSQL instance or SQLite (if compatible)
- Use transactions with rollback for isolation
- Seed test data for TLC vehicles, contributors

**Example Test Structure:**
```python
# tests/test_database.py
import pytest
from database.models import SightingsDatabase

@pytest.fixture
def test_db():
    """Create test database connection with clean state"""
    db = SightingsDatabase(connection_string="postgresql://test_db")
    db.setup_schema()  # Create tables
    yield db
    db.teardown()  # Clean up

@pytest.fixture
def sample_tlc_data(test_db):
    """Load sample TLC vehicle records"""
    test_db.cursor.execute("""
        INSERT INTO tlc_vehicles (plate_number, vin, vehicle_type)
        VALUES ('T123456C', 'VCF1ABCD123456789', 'FOR_HIRE')
    """)
    test_db.conn.commit()

def test_add_sighting_no_duplicates(test_db, sample_tlc_data):
    result = test_db.add_sighting(
        plate_number="T123456C",
        borough="Manhattan",
        image_path="/tmp/test.jpg",
        phone_number="+15551234567"
    )
    assert result["is_duplicate"] is False
    assert result["sighting_id"] is not None

def test_add_sighting_detects_sha256_duplicate(test_db):
    # Add first sighting
    test_db.add_sighting(..., sha256_hash="abc123")

    # Try to add duplicate
    result = test_db.add_sighting(..., sha256_hash="abc123")
    assert result["is_duplicate"] is True
    assert result["duplicate_type"] == "exact"
```

**Database Test Configuration:**
- Use `pytest.ini` to set test database URL
- Consider using Docker for PostgreSQL test instance
- Use pytest-postgresql plugin for automatic setup

### Layer 3: Unit Tests (With Mocked External Services)

**Target: Functions that call Twilio, Bluesky, R2 but have testable logic**

Priority areas:
- `chat/webhook.py::handle_incoming_sms()` - Chat flow state machine
- `post/bluesky.py::BlueskyClient.create_batch_sighting_post()` - Post generation
- `utils/image_processor.py::ImageProcessor.process_sighting_image()` - Image processing
- `notify/sms.py::send_admin_notification()` - SMS sending
- `utils/r2_storage.py::R2Storage` - Upload/download operations

**Mocking Strategy:**

**Option A: Monkey Patching (Quick Start)**
```python
# tests/test_chat_webhook.py
from unittest.mock import patch, MagicMock

@patch('chat.webhook.download_image_from_url')
@patch('chat.webhook.SightingsDatabase')
def test_handle_incoming_sms_image_upload(mock_db, mock_download):
    mock_download.return_value = b"fake_image_data"
    mock_db_instance = MagicMock()
    mock_db.return_value = mock_db_instance

    response = handle_incoming_sms(
        from_number="+15551234567",
        message_body="",
        media_urls=["https://example.com/image.jpg"]
    )

    assert "plate number" in response.lower()
    mock_download.assert_called_once()
```

**Option B: Dependency Injection (Better Long-Term)**

Refactor code to accept dependencies:
```python
# chat/webhook.py (refactored)
def handle_incoming_sms(
    from_number: str,
    message_body: str,
    media_urls: list[str],
    db: SightingsDatabase | None = None,
    image_downloader: Callable | None = None
):
    db = db or SightingsDatabase()
    downloader = image_downloader or download_image_from_url
    # ... rest of function
```

Then test with test doubles:
```python
# tests/test_chat_webhook.py
def test_handle_incoming_sms_with_test_db():
    test_db = InMemorySightingsDatabase()
    test_downloader = lambda url: b"fake_image"

    response = handle_incoming_sms(
        from_number="+15551234567",
        message_body="",
        media_urls=["https://example.com/image.jpg"],
        db=test_db,
        image_downloader=test_downloader
    )

    assert "plate number" in response.lower()
```

**Recommendation:** Start with Option A (monkey patching) for quick wins, migrate to Option B gradually as code evolves.

**Mock Service Boundaries:**

For external services, create mock implementations:

```python
# tests/mocks/mock_r2.py
class MockR2Storage:
    def __init__(self):
        self.uploaded_files = {}

    def upload_bytes(self, data: bytes, key: str) -> str:
        self.uploaded_files[key] = data
        return f"https://mock-r2.com/{key}"

    def file_exists(self, key: str) -> bool:
        return key in self.uploaded_files

# tests/mocks/mock_bluesky.py
class MockBlueskyClient:
    def __init__(self):
        self.posts = []

    def create_batch_sighting_post(self, sightings: list, dry_run: bool = False):
        self.posts.append(sightings)
        return {"uri": "at://mock/post/123", "cid": "mockCid"}
```

### Layer 4: Integration Tests (External Services)

**Target: Test real interactions with external services in controlled way**

**Test Environment Strategy:**

1. **Twilio Sandbox**
   - Use Twilio test credentials
   - Send to verified test numbers only
   - Capture webhooks with ngrok/local server

2. **Bluesky Test Account**
   - Create dedicated test account (e.g., @oceansofnyc-test.bsky.social)
   - Post to test account, verify via API
   - Clean up test posts after runs

3. **Cloudflare R2 Test Bucket**
   - Create separate `oceansofnyc-test` bucket
   - Use separate credentials
   - Lifecycle policy to auto-delete test objects after 24 hours

4. **Neon Test Database**
   - Create separate test branch in Neon
   - Reset to known state before tests
   - Use test data fixtures

**Integration Test Structure:**

```python
# tests/integration/test_r2_storage.py
import pytest
from utils.r2_storage import R2Storage
import os

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests disabled (set RUN_INTEGRATION_TESTS=1)"
)
def test_r2_upload_and_download():
    """Test actual R2 upload/download cycle"""
    r2 = R2Storage()
    test_data = b"test image data"
    key = "test/integration-test.jpg"

    # Upload
    url = r2.upload_bytes(test_data, key)
    assert url.startswith("https://")

    # Verify exists
    assert r2.file_exists(key)

    # Cleanup
    r2.delete_file(key)
    assert not r2.file_exists(key)
```

**Running Integration Tests:**
```bash
# Skip by default
pytest tests/

# Run integration tests explicitly
RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v
```

### Layer 5: Modal Endpoint Tests

**Target: Test Modal function handlers**

**Strategy:**

Modal endpoints are essentially HTTP handlers. Test them as such:

```python
# tests/test_modal_endpoints.py
from modal_app import web_submission_webhook, chat_sms_webhook
from unittest.mock import patch, MagicMock

def test_web_submission_webhook_valid_submission():
    """Test web submission with valid data"""
    with patch('modal_app.SightingsDatabase') as mock_db:
        mock_db_instance = MagicMock()
        mock_db_instance.add_sighting.return_value = {
            "sighting_id": 123,
            "is_duplicate": False
        }
        mock_db.return_value = mock_db_instance

        # Simulate Modal web request
        result = web_submission_webhook.local(
            image_data=b"fake_image",
            plate_number="T123456C",
            borough="Manhattan",
            contributor_name="Test User"
        )

        assert result["success"] is True
        assert result["sighting_id"] == 123

def test_chat_sms_webhook_twilio_format():
    """Test Twilio webhook with correct TwiML response"""
    response = chat_sms_webhook.local(
        From="+15551234567",
        Body="T123456C",
        NumMedia="0"
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers["Content-Type"]
    assert "<Response>" in response.body
    assert "<Message>" in response.body
```

**Modal Testing Limitations:**
- Cannot test scheduled functions (cron) without running locally
- Cannot test Modal-specific features (volumes, secrets) in unit tests
- Consider using `modal run` with `--dry-run` for smoke tests

### Layer 6: End-to-End Tests (Selective)

**Target: Critical user workflows**

**Recommendation:** Limit E2E tests to 3-5 critical paths:

1. **SMS Submission Flow**
   - Send SMS to Twilio number
   - Upload image via MMS
   - Respond with plate and borough
   - Verify sighting in database
   - Verify admin notification

2. **Web Submission Flow**
   - POST to /submit endpoint
   - Verify image upload to R2
   - Verify database record
   - Verify duplicate detection

3. **Posting Flow**
   - Create unposted sightings in test DB
   - Run `post_batch()` Modal function
   - Verify Bluesky post created
   - Verify database marked as posted

**Implementation:**
```python
# tests/e2e/test_sms_flow.py
import pytest
import requests
from twilio.rest import Client

@pytest.mark.e2e
def test_complete_sms_submission_flow():
    """Test full SMS submission from user to database"""
    # 1. Send SMS with image
    twilio = Client(
        os.getenv("TWILIO_TEST_ACCOUNT_SID"),
        os.getenv("TWILIO_TEST_AUTH_TOKEN")
    )
    message = twilio.messages.create(
        from_="+15551234567",  # Test number
        to=os.getenv("TWILIO_PHONE_NUMBER"),
        body="",
        media_url=["https://example.com/test-fisker.jpg"]
    )

    # 2. Wait for webhook processing
    time.sleep(2)

    # 3. Check session state
    db = SightingsDatabase()
    session = db.get_chat_session("+15551234567")
    assert session.state == "AWAITING_PLATE"

    # 4. Send plate number
    twilio.messages.create(
        from_="+15551234567",
        to=os.getenv("TWILIO_PHONE_NUMBER"),
        body="T123456C"
    )

    # 5. Verify completion
    # ... continue flow
```

**E2E Test Management:**
- Run manually or in CI on-demand (not every commit)
- Use test data that can be safely deleted
- Document cleanup procedures
- Monitor test environment costs

## Testing Infrastructure

### Required Tools

```bash
# Core testing
pip install pytest pytest-cov pytest-asyncio

# Mocking and fixtures
pip install pytest-mock responses freezegun

# Database testing
pip install pytest-postgresql

# Property-based testing (optional)
pip install hypothesis

# Coverage reporting
pip install coverage[toml]
```

### Project Configuration

**pytest.ini:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require external services)
    e2e: End-to-end tests (full workflow)
    slow: Tests that take >1s to run
env =
    DATABASE_URL=postgresql://localhost/oceansofnyc_test
    TWILIO_ACCOUNT_SID=test
    TWILIO_AUTH_TOKEN=test
    BLUESKY_HANDLE=test.bsky.social
    BLUESKY_APP_PASSWORD=test
```

**pyproject.toml additions:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=.",
    "--cov-report=term-missing",
    "--cov-report=html",
]

[tool.coverage.run]
source = ["."]
omit = [
    "tests/*",
    "scripts/*",
    "*/migrations/*",
    ".venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### CI/CD Integration

**GitHub Actions Workflow:**
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov pytest-mock

      - name: Run unit tests
        run: pytest tests/ -m "not integration and not e2e" --cov

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  integration:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-mock

      - name: Run integration tests
        env:
          RUN_INTEGRATION_TESTS: 1
          R2_ACCESS_KEY_ID: ${{ secrets.R2_TEST_ACCESS_KEY_ID }}
          R2_SECRET_ACCESS_KEY: ${{ secrets.R2_TEST_SECRET_ACCESS_KEY }}
          BLUESKY_HANDLE: ${{ secrets.BLUESKY_TEST_HANDLE }}
          BLUESKY_APP_PASSWORD: ${{ secrets.BLUESKY_TEST_PASSWORD }}
        run: pytest tests/integration/ -v
```

## Implementation Roadmap

### Phase 1: Foundation (1-2 weeks)

1. Set up pytest infrastructure
   - Install testing dependencies
   - Create pytest.ini and coverage config
   - Set up test directory structure

2. Test pure functions (high ROI)
   - Migrate existing extractor tests
   - Add geolocate tests
   - Add image hashing tests
   - Add validation tests

3. Create mock utilities
   - Mock R2 storage
   - Mock Bluesky client
   - Mock Twilio client

**Success Criteria:** 30% code coverage, all pure functions tested

### Phase 2: Database Tests (1 week)

4. Set up test database fixtures
   - PostgreSQL test instance
   - Schema creation/teardown
   - Sample data fixtures

5. Test database operations
   - Sighting creation and duplicate detection
   - TLC vehicle validation
   - Session management
   - Post queue management

**Success Criteria:** 50% code coverage, all DB operations tested

### Phase 3: Integration Tests (1 week)

6. Test Modal endpoints with mocks
   - Web submission webhook
   - SMS webhook handler
   - Scheduled functions

7. Test with real services (optional)
   - R2 upload/download
   - Bluesky posting to test account
   - Twilio SMS to test number

**Success Criteria:** 70% code coverage, critical paths tested

### Phase 4: Continuous Integration (2-3 days)

8. Set up GitHub Actions
   - Run tests on every PR
   - Generate coverage reports
   - Fail on coverage decrease (optional)

9. Pre-commit hooks
   - Run tests before commit (optional)
   - Format with ruff
   - Type check with mypy

**Success Criteria:** Automated testing in CI, coverage tracked

## Testing Best Practices

### General Guidelines

1. **Test Behavior, Not Implementation**
   - Test what functions do, not how they do it
   - Avoid testing internal details
   - Allow refactoring without breaking tests

2. **AAA Pattern (Arrange, Act, Assert)**
   ```python
   def test_calculate_hamming_distance():
       # Arrange
       hash1 = "abc123"
       hash2 = "abc456"

       # Act
       distance = hamming_distance(hash1, hash2)

       # Assert
       assert distance == 3
   ```

3. **One Assertion Per Test (Guideline, Not Rule)**
   - Keep tests focused on single behavior
   - Use multiple assertions for related checks
   - Split unrelated assertions into separate tests

4. **Test Names Should Describe Behavior**
   ```python
   # Good
   def test_add_sighting_detects_exact_duplicate_by_sha256():

   # Bad
   def test_add_sighting():
   def test_duplicate():
   ```

5. **Use Fixtures for Common Setup**
   ```python
   @pytest.fixture
   def sample_sighting_data():
       return {
           "plate_number": "T123456C",
           "borough": "Manhattan",
           "phone_number": "+15551234567"
       }

   def test_add_sighting(sample_sighting_data):
       result = db.add_sighting(**sample_sighting_data)
       assert result["sighting_id"] is not None
   ```

6. **Avoid Test Interdependence**
   - Each test should run independently
   - Don't rely on test execution order
   - Clean up after each test

### Project-Specific Guidelines

1. **Database Tests**
   - Use transactions with rollback for isolation
   - Avoid hardcoding IDs (use returned values)
   - Test both success and failure cases

2. **External Service Tests**
   - Mock by default, integrate selectively
   - Use environment variable flags for integration tests
   - Document required test credentials

3. **Image Processing Tests**
   - Use small test images (<1KB)
   - Store test images in `tests/fixtures/`
   - Test format conversion edge cases

4. **Modal Endpoint Tests**
   - Test with `.local()` for synchronous execution
   - Mock database and external services
   - Verify HTTP response formats

## Maintenance and Evolution

### Coverage Goals

**Realistic Targets:**
- **Phase 1:** 30% coverage (pure functions)
- **Phase 2:** 50% coverage (database operations)
- **Phase 3:** 70% coverage (integration)
- **Long-term:** 80% coverage (aspirational)

**Don't Test:**
- Configuration loading (environment variables)
- Simple getters/setters
- Framework code (Modal, Click CLI)
- Trivial one-liners

### Test Review Checklist

Before merging new tests:
- [ ] Test names clearly describe behavior
- [ ] Tests are isolated and independent
- [ ] Mocks are used appropriately (not over-mocked)
- [ ] Edge cases are covered
- [ ] Tests run fast (<100ms per unit test)
- [ ] Integration tests are marked with `@pytest.mark.integration`
- [ ] External service credentials are not hardcoded

### When Tests Fail

1. **Fix the test, not the code** (if behavior is correct)
2. **Update tests when requirements change**
3. **Don't comment out failing tests** (fix or delete)
4. **Use `@pytest.mark.skip` with reason if temporarily disabling**

### Refactoring for Testability

As code evolves, consider these refactorings:

1. **Extract Pure Functions**
   ```python
   # Before (hard to test)
   def handle_sms(body: str):
       plate = body.upper().strip()
       if re.match(r"T\d{6}C", plate):
           db.save(plate)

   # After (easy to test)
   def normalize_plate(body: str) -> str:
       return body.upper().strip()

   def is_valid_plate(plate: str) -> bool:
       return bool(re.match(r"T\d{6}C", plate))

   def handle_sms(body: str):
       plate = normalize_plate(body)
       if is_valid_plate(plate):
           db.save(plate)
   ```

2. **Dependency Injection**
   ```python
   # Before
   def upload_image(image_path: str):
       r2 = R2Storage()
       r2.upload_file(image_path)

   # After
   def upload_image(image_path: str, storage: R2Storage | None = None):
       storage = storage or R2Storage()
       storage.upload_file(image_path)
   ```

3. **Extract Configuration**
   ```python
   # Before
   TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")

   # After
   @dataclass
   class Config:
       twilio_sid: str
       twilio_token: str

       @classmethod
       def from_env(cls):
           return cls(
               twilio_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
               twilio_token=os.getenv("TWILIO_AUTH_TOKEN", "")
           )
   ```

## Conclusion

This testing strategy prioritizes:
1. **Quick wins** - Pure functions first
2. **High-value tests** - Critical path coverage
3. **Practical approach** - Mock external services, integrate selectively
4. **Maintainability** - Simple tests, clear patterns
5. **Incremental adoption** - Phase-based implementation

The goal is not 100% coverage, but confidence in the system's correctness and safety for refactoring.

**Next Steps:**
1. Review and approve this strategy
2. Create implementation issues in Beads
3. Set up testing infrastructure (Phase 1)
4. Begin testing pure functions
5. Iterate based on learnings

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
**Author:** Claude (via Oceans of NYC maintainer)
