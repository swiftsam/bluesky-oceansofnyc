"""Mock implementation of Twilio client for testing."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MockTwilioMessage:
    """Mock Twilio message response."""

    sid: str
    status: str
    date_created: datetime
    from_: str
    to: str
    body: str

    def __init__(
        self,
        sid: str,
        from_: str,
        to: str,
        body: str,
        status: str = "sent",
    ):
        self.sid = sid
        self.from_ = from_
        self.to = to
        self.body = body
        self.status = status
        self.date_created = datetime.now()


class MockTwilioMessages:
    """Mock Twilio messages collection."""

    def __init__(self, client: "MockTwilioClient"):
        self.client = client

    def create(
        self, from_: str, to: str, body: str, media_url: list[str] | None = None
    ) -> MockTwilioMessage:
        """Mock message creation."""
        message = MockTwilioMessage(
            sid=f"SM{len(self.client.sent_messages):032x}",
            from_=from_,
            to=to,
            body=body,
        )

        # Track the message
        self.client.sent_messages.append(
            {
                "from": from_,
                "to": to,
                "body": body,
                "media_url": media_url or [],
                "message": message,
            }
        )

        return message


class MockTwilioClient:
    """Mock Twilio client that tracks sent messages."""

    def __init__(self, account_sid: str | None = "test_sid", auth_token: str | None = "test_token"):
        """Initialize mock Twilio client."""
        self.account_sid = account_sid
        self.auth_token = auth_token

        # Track sent messages
        self.sent_messages: list[dict] = []

        # Messages API
        self.messages = MockTwilioMessages(self)

    def get_sent_message_count(self) -> int:
        """Get number of sent messages (test helper)."""
        return len(self.sent_messages)

    def get_last_sent_message(self) -> dict | None:
        """Get last sent message (test helper)."""
        return self.sent_messages[-1] if self.sent_messages else None

    def get_messages_to(self, phone_number: str) -> list[dict]:
        """Get all messages sent to a specific number (test helper)."""
        return [msg for msg in self.sent_messages if msg["to"] == phone_number]

    def get_messages_from(self, phone_number: str) -> list[dict]:
        """Get all messages sent from a specific number (test helper)."""
        return [msg for msg in self.sent_messages if msg["from"] == phone_number]

    def clear(self) -> None:
        """Clear all sent messages (test helper)."""
        self.sent_messages.clear()


def mock_send_admin_notification(
    message: str,
    admin_contributor_id: int = 1,
    mock_client: MockTwilioClient | None = None,
) -> bool:
    """
    Mock version of send_admin_notification for testing.

    Instead of using environment variables and database, accepts a mock client.
    """
    if mock_client is None:
        mock_client = MockTwilioClient()

    try:
        # Mock admin phone number
        admin_phone = "+15551234567"

        # Send mock SMS
        mock_client.messages.create(
            from_="+15559999999",  # Mock Twilio number
            to=admin_phone,
            body=message,
        )

        return True

    except Exception:
        return False
