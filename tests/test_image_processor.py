"""Tests for ImageProcessor class."""

import tempfile
from datetime import datetime

import pytest


@pytest.fixture
def temp_volume_path():
    """Create a temporary directory for image processing tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestGenerateFilename:
    """Test generate_filename() method."""

    def test_basic_filename_generation(self, temp_volume_path):
        """Test generating a filename with plate and timestamp."""
        from utils.image_processor import ImageProcessor

        processor = ImageProcessor(volume_path=temp_volume_path)

        # Test with a specific timestamp
        timestamp = datetime(2024, 12, 6, 18, 41, 23, 234500)
        filename = processor.generate_filename("T680368C", timestamp)

        # Expected: T680368C_20241206_184123_2345.jpg
        assert filename == "T680368C_20241206_184123_2345.jpg"

    def test_filename_with_zero_microseconds(self, temp_volume_path):
        """Test filename generation with zero microseconds."""
        from utils.image_processor import ImageProcessor

        processor = ImageProcessor(volume_path=temp_volume_path)
        timestamp = datetime(2024, 1, 15, 9, 5, 30, 0)
        filename = processor.generate_filename("T123456C", timestamp)

        # Expected: T123456C_20240115_090530_0000.jpg
        assert filename == "T123456C_20240115_090530_0000.jpg"

    def test_filename_with_max_microseconds(self, temp_volume_path):
        """Test filename generation with max microseconds (999999)."""
        from utils.image_processor import ImageProcessor

        processor = ImageProcessor(volume_path=temp_volume_path)
        timestamp = datetime(2024, 12, 31, 23, 59, 59, 999999)
        filename = processor.generate_filename("T999999C", timestamp)

        # Microseconds / 100 = 9999
        assert filename == "T999999C_20241231_235959_9999.jpg"

    def test_filename_format_consistency(self, temp_volume_path):
        """Test that filename follows {plate}_{yyyymmdd}_{hhmmss}_{ssss}.jpg format."""
        from utils.image_processor import ImageProcessor

        processor = ImageProcessor(volume_path=temp_volume_path)
        timestamp = datetime(2025, 6, 15, 14, 30, 45, 123456)
        filename = processor.generate_filename("ABC123XY", timestamp)

        # Should match pattern
        parts = filename.replace(".jpg", "").split("_")
        assert len(parts) == 4
        assert parts[0] == "ABC123XY"  # plate
        assert len(parts[1]) == 8  # yyyymmdd
        assert len(parts[2]) == 6  # hhmmss
        assert len(parts[3]) == 4  # ssss
        assert filename.endswith(".jpg")


class TestGetWebUrl:
    """Test get_web_url() method."""

    def test_url_construction(self, temp_volume_path, monkeypatch):
        """Test URL construction from base URI and filename."""
        from utils.image_processor import ImageProcessor

        monkeypatch.setenv("SIGHTING_IMAGE_BASE_URI", "https://cdn.example.com/images/")
        processor = ImageProcessor(volume_path=temp_volume_path)

        url = processor.get_web_url("T680368C_20241206_184123_2345.jpg")

        assert url == "https://cdn.example.com/images/T680368C_20241206_184123_2345.jpg"

    def test_url_construction_strips_trailing_slash(self, temp_volume_path, monkeypatch):
        """Test that trailing slash in base URI is handled."""
        from utils.image_processor import ImageProcessor

        # With trailing slash
        monkeypatch.setenv("SIGHTING_IMAGE_BASE_URI", "https://cdn.example.com/images/")
        processor = ImageProcessor(volume_path=temp_volume_path)
        url = processor.get_web_url("test.jpg")
        assert url == "https://cdn.example.com/images/test.jpg"

    def test_url_construction_without_trailing_slash(self, temp_volume_path, monkeypatch):
        """Test URL construction when base URI has no trailing slash."""
        from utils.image_processor import ImageProcessor

        monkeypatch.setenv("SIGHTING_IMAGE_BASE_URI", "https://cdn.example.com/images")
        processor = ImageProcessor(volume_path=temp_volume_path)
        url = processor.get_web_url("test.jpg")
        assert url == "https://cdn.example.com/images/test.jpg"

    def test_default_base_uri(self, temp_volume_path, monkeypatch):
        """Test default base URI when env var not set."""
        from utils.image_processor import ImageProcessor

        monkeypatch.delenv("SIGHTING_IMAGE_BASE_URI", raising=False)
        processor = ImageProcessor(volume_path=temp_volume_path)
        url = processor.get_web_url("test.jpg")

        # Should use default
        assert "oceansofnyc.com" in url or "sightings" in url
