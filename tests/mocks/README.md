# Mock Services

This directory contains mock implementations of external services for testing without requiring actual API credentials or network calls.

## Available Mocks

### MockR2Storage

Mock implementation of Cloudflare R2 storage that stores files in memory.

```python
from tests.mocks import MockR2Storage

def test_image_upload():
    r2 = MockR2Storage()

    # Upload a file
    url = r2.upload_bytes(b"test data", "test/image.jpg")

    # Assertions
    assert r2.file_exists("test/image.jpg")
    assert url == "https://test-r2.dev/test/image.jpg"
    assert r2.get_file_data("test/image.jpg") == b"test data"
```

**Features:**
- In-memory file storage
- Tracks upload metadata (content type, cache control, size)
- Helper methods: `get_file_data()`, `list_files()`, `clear()`

### MockBlueskyClient

Mock implementation of the Bluesky social media client.

```python
from tests.mocks import MockBlueskyClient

def test_post_creation():
    client = MockBlueskyClient()

    # Create a post
    post = client.create_post("Test post", images=[])

    # Assertions
    assert client.get_post_count() == 1
    assert post.uri.startswith("at://test.bsky.social")

    last_post = client.get_last_post()
    assert last_post["text"] == "Test post"
```

**Features:**
- Tracks all created posts
- Tracks uploaded images
- Supports dry-run mode
- Helper methods: `get_post_count()`, `get_last_post()`, `clear()`

### MockTwilioClient

Mock implementation of Twilio SMS client.

```python
from tests.mocks import MockTwilioClient

def test_sms_sending():
    client = MockTwilioClient()

    # Send a message
    message = client.messages.create(
        from_="+15559999999",
        to="+15551234567",
        body="Test message"
    )

    # Assertions
    assert client.get_sent_message_count() == 1
    assert message.status == "sent"

    last_msg = client.get_last_sent_message()
    assert last_msg["body"] == "Test message"
```

**Features:**
- Tracks all sent messages
- Filter messages by sender or recipient
- Helper methods: `get_messages_to()`, `get_messages_from()`, `clear()`

### MockSightingsDatabase

Mock implementation of the sightings database with duplicate detection.

```python
from tests.mocks import MockSightingsDatabase

def test_duplicate_detection():
    db = MockSightingsDatabase()

    # Add first sighting
    result1 = db.add_sighting(
        plate_number="T123456C",
        borough="Manhattan",
        sha256_hash="abc123"
    )
    assert result1["is_duplicate"] is False

    # Try to add duplicate
    result2 = db.add_sighting(
        plate_number="T123456C",
        borough="Manhattan",
        sha256_hash="abc123"
    )
    assert result2["is_duplicate"] is True
    assert result2["duplicate_type"] == "exact"
```

**Features:**
- In-memory data storage
- SHA-256 and perceptual hash duplicate detection
- Chat session management
- TLC vehicle database
- Contributor management
- Helper methods: `get_sighting_count()`, `clear()`

## Usage Patterns

### Basic Test Structure

```python
import pytest
from tests.mocks import MockR2Storage, MockBlueskyClient, MockSightingsDatabase

@pytest.fixture
def mock_r2():
    """Provide a clean R2 mock for each test."""
    storage = MockR2Storage()
    yield storage
    storage.clear()

def test_with_mocks(mock_r2):
    """Test using mock services."""
    # Test code here
    pass
```

### Patching Production Code

```python
from unittest.mock import patch
from tests.mocks import MockR2Storage

@patch('utils.r2_storage.R2Storage')
def test_image_upload(mock_r2_class):
    """Test with patched R2 storage."""
    mock_r2_class.return_value = MockR2Storage()

    # Code that uses R2Storage will now use the mock
    # ...
```

### Dependency Injection (Preferred)

If functions accept optional dependencies, pass mocks directly:

```python
from tests.mocks import MockSightingsDatabase

def test_with_injected_mock():
    """Test using dependency injection."""
    mock_db = MockSightingsDatabase()

    # Pass mock to function that accepts db parameter
    result = my_function(db=mock_db)

    # Verify interactions
    assert mock_db.get_sighting_count() == 1
```

## Benefits

1. **Fast:** No network calls or actual I/O
2. **Reliable:** No external dependencies or flaky API calls
3. **Inspectable:** Track all interactions for assertions
4. **Flexible:** Customize behavior for edge cases
5. **Cost-free:** No API usage charges

## When to Use Real Services

Consider integration tests with real services for:
- Critical workflows (e.g., actual posting to Bluesky)
- Testing edge cases specific to the service
- Validating API assumptions

See [../integration/](../integration/) for integration test examples.
