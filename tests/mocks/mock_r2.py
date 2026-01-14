"""Mock implementation of R2Storage for testing."""

from typing import BinaryIO


class MockR2Storage:
    """Mock R2 storage client that stores files in memory."""

    def __init__(
        self,
        account_id: str | None = "test-account",
        access_key_id: str | None = "test-key",
        secret_access_key: str | None = "test-secret",
        bucket_name: str | None = "test-bucket",
        public_url_base: str | None = "https://test-r2.dev",
    ):
        """Initialize mock R2 storage with test credentials."""
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.public_url_base = public_url_base

        # In-memory storage: {object_key: bytes}
        self.uploaded_files: dict[str, bytes] = {}

        # Track upload metadata for assertions
        self.upload_metadata: dict[str, dict] = {}

    def upload_file(self, file_path: str, object_key: str, content_type: str = "image/jpeg") -> str:
        """Mock file upload from path."""
        # In real tests, you'd read the file, but for mocks we just track the call
        # Read file contents
        with open(file_path, "rb") as f:
            data = f.read()

        return self.upload_bytes(data, object_key, content_type)

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        object_key: str,
        content_type: str = "image/jpeg",
        cache_control: str | None = None,
    ) -> str:
        """Mock file object upload."""
        data = fileobj.read()
        return self.upload_bytes(data, object_key, content_type, cache_control)

    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        content_type: str = "image/jpeg",
        cache_control: str | None = None,
    ) -> str:
        """Mock bytes upload."""
        # Store the file data
        self.uploaded_files[object_key] = data

        # Store metadata for test assertions
        self.upload_metadata[object_key] = {
            "content_type": content_type,
            "cache_control": cache_control or "public, max-age=31536000",
            "size": len(data),
        }

        # Return mock public URL
        return f"{self.public_url_base}/{object_key}"

    def delete_file(self, object_key: str) -> None:
        """Mock file deletion."""
        if object_key in self.uploaded_files:
            del self.uploaded_files[object_key]
            del self.upload_metadata[object_key]

    def file_exists(self, object_key: str) -> bool:
        """Check if file exists in mock storage."""
        return object_key in self.uploaded_files

    def get_file_data(self, object_key: str) -> bytes | None:
        """Get file data from mock storage (test helper method)."""
        return self.uploaded_files.get(object_key)

    def get_file_metadata(self, object_key: str) -> dict | None:
        """Get file metadata from mock storage (test helper method)."""
        return self.upload_metadata.get(object_key)

    def clear(self) -> None:
        """Clear all stored files (test helper method)."""
        self.uploaded_files.clear()
        self.upload_metadata.clear()

    def list_files(self) -> list[str]:
        """List all uploaded file keys (test helper method)."""
        return list(self.uploaded_files.keys())
