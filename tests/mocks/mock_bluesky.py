"""Mock implementation of BlueskyClient for testing."""

from dataclasses import dataclass


@dataclass
class MockBlueskyImage:
    """Mock Bluesky image object."""

    blob: dict
    alt: str = ""


@dataclass
class MockBlueskyPost:
    """Mock Bluesky post response."""

    uri: str
    cid: str


class MockBlueskyClient:
    """Mock Bluesky client that stores posts in memory."""

    def __init__(self, handle: str | None = "test.bsky.social", password: str | None = "test-pass"):
        """Initialize mock Bluesky client."""
        self.handle = handle
        self.password = password
        self.logged_in = False

        # Track created posts for test assertions
        self.posts: list[dict] = []

        # Track uploaded images
        self.uploaded_images: list[dict] = []

        # Auto-login
        self.login()

    def login(self) -> None:
        """Mock login."""
        self.logged_in = True

    def compress_image(self, image_path: str, max_size_kb: int = 950) -> bytes:
        """Mock image compression - returns fake bytes."""
        # In real tests, you might want to actually read and compress
        # For mocks, just return fake data
        return b"fake_compressed_image_data"

    def upload_image(self, image_path: str, alt_text: str = "") -> MockBlueskyImage:
        """Mock image upload."""
        # Track the upload
        image_info = {
            "image_path": image_path,
            "alt_text": alt_text,
        }
        self.uploaded_images.append(image_info)

        # Return mock image object
        return MockBlueskyImage(
            blob={
                "ref": f"mock_ref_{len(self.uploaded_images)}",
                "mimeType": "image/jpeg",
                "size": 100000,
            },
            alt=alt_text,
        )

    def create_post(
        self, text: str, images: list[MockBlueskyImage] | None = None, dry_run: bool = False
    ) -> MockBlueskyPost | None:
        """Mock post creation."""
        if dry_run:
            return None

        # Track the post
        post_info = {
            "text": text,
            "images": images or [],
            "image_count": len(images) if images else 0,
        }
        self.posts.append(post_info)

        # Return mock post response
        post_id = f"mock_post_{len(self.posts)}"
        return MockBlueskyPost(
            uri=f"at://test.bsky.social/app.bsky.feed.post/{post_id}", cid=post_id
        )

    def create_batch_sighting_post(
        self,
        sightings: list[dict],
        dry_run: bool = False,
    ) -> MockBlueskyPost | None:
        """
        Mock batch sighting post creation.

        This simulates the main posting function used in the app.
        """
        if dry_run:
            return None

        # Generate mock text
        text = self._generate_mock_batch_text(sightings)

        # Mock image uploads
        images = []
        for sighting in sightings:
            if "image_path" in sighting:
                images.append(self.upload_image(sighting["image_path"], "Fisker Ocean sighting"))

        return self.create_post(text, images, dry_run=False)

    def _generate_mock_batch_text(self, sightings: list[dict]) -> str:
        """Generate mock batch post text."""
        count = len(sightings)
        if count == 1:
            plate = sightings[0].get("license_plate", "T######C")
            return f"New sighting: {plate}"
        return f"New sightings: {count} Oceans spotted"

    def get_post_count(self) -> int:
        """Get number of posts created (test helper)."""
        return len(self.posts)

    def get_last_post(self) -> dict | None:
        """Get last created post (test helper)."""
        return self.posts[-1] if self.posts else None

    def get_uploaded_image_count(self) -> int:
        """Get number of images uploaded (test helper)."""
        return len(self.uploaded_images)

    def clear(self) -> None:
        """Clear all posts and images (test helper)."""
        self.posts.clear()
        self.uploaded_images.clear()
