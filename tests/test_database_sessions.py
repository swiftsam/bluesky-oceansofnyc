"""Database tests for chat session management.

These tests require a PostgreSQL test database.
Set TEST_DATABASE_URL environment variable to run these tests.
"""

from datetime import datetime

import pytest

from chat.session import ChatSession


@pytest.mark.db
class TestChatSessionCreation:
    """Test chat session creation and retrieval."""

    def test_create_new_session(self, test_db_url, clean_db):
        """Test creating a new chat session."""
        session = ChatSession("+15551111111", test_db_url)
        data = session.get()

        assert data is not None
        assert data["phone_number"] == "+15551111111"
        assert data["state"] == ChatSession.IDLE
        assert session.is_new_session() is True

    def test_get_existing_session(self, test_db_url, clean_db):
        """Test retrieving an existing session."""
        # Create first session
        session1 = ChatSession("+15552222222", test_db_url)
        session1.get()

        # Get same session again
        session2 = ChatSession("+15552222222", test_db_url)
        data2 = session2.get()

        assert data2 is not None
        assert data2["phone_number"] == "+15552222222"
        assert session2.is_new_session() is False

    def test_multiple_sessions(self, test_db_url, clean_db):
        """Test that different phone numbers have separate sessions."""
        session1 = ChatSession("+15553333333", test_db_url)
        session2 = ChatSession("+15554444444", test_db_url)

        data1 = session1.get()
        data2 = session2.get()

        assert data1["phone_number"] != data2["phone_number"]
        assert data1["id"] != data2["id"]


@pytest.mark.db
class TestChatSessionStateTransitions:
    """Test chat session state transitions."""

    def test_idle_to_awaiting_plate(self, test_db_url, clean_db):
        """Test transitioning from IDLE to AWAITING_PLATE."""
        session = ChatSession("+15555555555", test_db_url)
        session.get()

        # Transition to AWAITING_PLATE (user sent image)
        session.update(
            state=ChatSession.AWAITING_PLATE,
            pending_image_path="/tmp/image.jpg",
            pending_latitude=40.7589,
            pending_longitude=-73.9851,
            pending_timestamp=datetime.now(),
        )

        data = session.get()
        assert data["state"] == ChatSession.AWAITING_PLATE
        assert data["pending_image_path"] == "/tmp/image.jpg"
        assert data["pending_latitude"] is not None
        assert data["pending_longitude"] is not None

    def test_awaiting_plate_to_awaiting_borough(self, test_db_url, clean_db):
        """Test transitioning from AWAITING_PLATE to AWAITING_BOROUGH."""
        session = ChatSession("+15556666666", test_db_url)
        session.get()

        # Set up as awaiting plate
        session.update(
            state=ChatSession.AWAITING_PLATE,
            pending_image_path="/tmp/image.jpg",
        )

        # User sends plate number
        session.update(state=ChatSession.AWAITING_BOROUGH, pending_plate="T123456C")

        data = session.get()
        assert data["state"] == ChatSession.AWAITING_BOROUGH
        assert data["pending_plate"] == "T123456C"
        assert data["pending_image_path"] == "/tmp/image.jpg"

    def test_awaiting_borough_to_idle(self, test_db_url, clean_db):
        """Test completing the flow and returning to IDLE."""
        session = ChatSession("+15557777777", test_db_url)
        session.get()

        # Set up complete pending data
        session.update(
            state=ChatSession.AWAITING_BOROUGH,
            pending_image_path="/tmp/image.jpg",
            pending_plate="T234567C",
        )

        # User sends borough - reset to idle
        session.reset()

        data = session.get()
        assert data["state"] == ChatSession.IDLE
        assert data["pending_image_path"] is None
        assert data["pending_plate"] is None


@pytest.mark.db
class TestChatSessionPendingData:
    """Test storing pending data in sessions."""

    def test_store_pending_image(self, test_db_url, clean_db):
        """Test storing pending image path."""
        session = ChatSession("+15558888888", test_db_url)
        session.get()

        session.update(pending_image_path="/modal/volume/image123.jpg")

        data = session.get()
        assert data["pending_image_path"] == "/modal/volume/image123.jpg"

    def test_store_pending_gps_coordinates(self, test_db_url, clean_db):
        """Test storing GPS coordinates."""
        session = ChatSession("+15559999999", test_db_url)
        session.get()

        session.update(
            state=ChatSession.AWAITING_PLATE,
            pending_latitude=40.7589,
            pending_longitude=-73.9851,
        )

        data = session.get()
        assert data["pending_latitude"] == 40.7589
        assert data["pending_longitude"] == -73.9851

    def test_store_pending_plate(self, test_db_url, clean_db):
        """Test storing pending plate number."""
        session = ChatSession("+15550000000", test_db_url)
        session.get()

        session.update(pending_plate="T345678C")

        data = session.get()
        assert data["pending_plate"] == "T345678C"

    def test_store_pending_borough(self, test_db_url, clean_db):
        """Test storing pending borough."""
        session = ChatSession("+15551111222", test_db_url)
        session.get()

        session.update(pending_borough="Brooklyn")

        data = session.get()
        assert data["pending_borough"] == "Brooklyn"

    def test_store_image_path(self, test_db_url, clean_db):
        """Test storing image path."""
        session = ChatSession("+15552222333", test_db_url)
        session.get()

        session.update(
            pending_image_path="/modal/volume/image.jpg",
        )

        data = session.get()
        assert data["pending_image_path"] == "/modal/volume/image.jpg"


@pytest.mark.db
class TestChatSessionReset:
    """Test session reset functionality."""

    def test_reset_clears_all_pending_data(self, test_db_url, clean_db):
        """Test that reset clears all pending data."""
        session = ChatSession("+15553333444", test_db_url)
        session.get()

        # Fill session with pending data
        session.update(
            state=ChatSession.AWAITING_BOROUGH,
            pending_image_path="/tmp/image.jpg",
            pending_plate="T456789C",
            pending_latitude=40.7589,
            pending_longitude=-73.9851,
            pending_borough="Queens",
        )

        # Reset
        session.reset()

        data = session.get()
        assert data["state"] == ChatSession.IDLE
        assert data["pending_image_path"] is None
        assert data["pending_plate"] is None
        assert data["pending_latitude"] is None
        assert data["pending_longitude"] is None
        assert data["pending_borough"] is None

    def test_reset_maintains_phone_number(self, test_db_url, clean_db):
        """Test that reset doesn't change phone number."""
        session = ChatSession("+15554444555", test_db_url)
        original_data = session.get()
        original_id = original_data["id"]

        session.update(state=ChatSession.AWAITING_PLATE)
        session.reset()

        data = session.get()
        assert data["phone_number"] == "+15554444555"
        assert data["id"] == original_id


@pytest.mark.db
class TestChatSessionCoordinateClearing:
    """Test special coordinate clearing behavior."""

    def test_coordinates_cleared_on_new_image(self, test_db_url, clean_db):
        """Test that old coordinates are cleared when new image arrives."""
        session = ChatSession("+15555555666", test_db_url)
        session.get()

        # First image with coordinates
        session.update(
            state=ChatSession.AWAITING_PLATE,
            pending_image_path="/tmp/image1.jpg",
            pending_latitude=40.7589,
            pending_longitude=-73.9851,
        )

        # Second image without coordinates (should clear)
        session.update(
            state=ChatSession.AWAITING_PLATE,
            pending_image_path="/tmp/image2.jpg",
            pending_latitude=None,
            pending_longitude=None,
        )

        data = session.get()
        assert data["pending_latitude"] is None
        assert data["pending_longitude"] is None

    def test_coordinates_cleared_on_idle(self, test_db_url, clean_db):
        """Test that coordinates are cleared when returning to IDLE."""
        session = ChatSession("+15556666777", test_db_url)
        session.get()

        # Set up with coordinates
        session.update(
            state=ChatSession.AWAITING_PLATE,
            pending_latitude=40.7589,
            pending_longitude=-73.9851,
        )

        # Transition to IDLE
        session.update(state=ChatSession.IDLE)

        data = session.get()
        assert data["pending_latitude"] is None
        assert data["pending_longitude"] is None
