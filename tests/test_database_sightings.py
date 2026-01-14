"""Database tests for sightings operations.

These tests require a PostgreSQL test database.
Set TEST_DATABASE_URL environment variable to run these tests.

Example:
    TEST_DATABASE_URL=postgresql://localhost/oceansofnyc_test pytest tests/test_database_sightings.py
"""

from datetime import datetime

import pytest

from database.models import SightingsDatabase


@pytest.mark.db
class TestAddSighting:
    """Test add_sighting() method with duplicate detection."""

    def test_add_sighting_basic(self, test_db_url, sample_contributor, temp_image):
        """Test adding a basic sighting without duplicates."""
        db = SightingsDatabase(test_db_url)

        result = db.add_sighting(
            license_plate="T123456C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
            borough="Manhattan",
        )

        assert result is not None
        assert result["id"] is not None
        assert result["duplicate_type"] is None
        assert result["duplicate_info"] is None

    def test_add_sighting_with_gps_auto_borough(self, test_db_url, sample_contributor, temp_image):
        """Test that borough is auto-populated from GPS coordinates."""
        db = SightingsDatabase(test_db_url)

        # Times Square coordinates
        result = db.add_sighting(
            license_plate="T234567C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
            # No borough provided - should auto-detect
        )

        assert result is not None
        sighting = db.get_sighting_by_id(result["id"])
        # Borough should be detected as Manhattan from coordinates
        assert sighting[9] == "Manhattan"  # borough is column 9

    def test_add_sighting_exact_duplicate_rejected(
        self, test_db_url, sample_contributor, temp_image
    ):
        """Test that exact duplicates (same SHA-256) are rejected."""
        db = SightingsDatabase(test_db_url)

        from utils.image_hashing import calculate_sha256

        sha256_hash = calculate_sha256(str(temp_image))

        # Add first sighting
        result1 = db.add_sighting(
            license_plate="T345678C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
            image_hash_sha256=sha256_hash,
        )
        assert result1 is not None

        # Try to add exact duplicate
        result2 = db.add_sighting(
            license_plate="T345678C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=f"{temp_image}_copy",  # Different path
            contributor_id=sample_contributor,
            image_hash_sha256=sha256_hash,  # Same hash
        )

        # Exact duplicates should be rejected (return None)
        assert result2 is None

    def test_add_sighting_similar_image_warning(self, test_db_url, sample_contributor, temp_images):
        """Test that similar images generate duplicate warnings."""
        db = SightingsDatabase(test_db_url)

        from utils.image_hashing import calculate_perceptual_hash

        # Add first sighting with perceptual hash
        phash1 = calculate_perceptual_hash(str(temp_images[0]))
        result1 = db.add_sighting(
            license_plate="T456789C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_images[0]),
            contributor_id=sample_contributor,
            image_hash_perceptual=phash1,
        )
        assert result1 is not None

        # Add second sighting with very similar hash
        # Modify just 1 bit to make it similar but not identical
        phash2_int = int(phash1, 16) ^ 0x1  # Flip last bit
        phash2 = format(phash2_int, "016x")

        result2 = db.add_sighting(
            license_plate="T567890C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_images[1]),
            contributor_id=sample_contributor,
            image_hash_perceptual=phash2,
        )

        # Similar images should be added but with warning
        assert result2 is not None
        assert result2["duplicate_type"] == "similar"
        assert result2["duplicate_info"] is not None
        assert result2["duplicate_info"]["distance"] <= 5

    def test_add_sighting_unique_path_constraint(self, test_db_url, sample_contributor, temp_image):
        """Test that duplicate image paths are rejected."""
        db = SightingsDatabase(test_db_url)

        # Add first sighting
        result1 = db.add_sighting(
            license_plate="T678901C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
        )
        assert result1 is not None

        # Try to add another sighting with same image path
        result2 = db.add_sighting(
            license_plate="T789012C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),  # Same path
            contributor_id=sample_contributor,
        )

        # Should be rejected due to unique constraint on image_path
        assert result2 is None

    def test_add_sighting_with_r2_urls(self, test_db_url, sample_contributor, temp_image):
        """Test adding sighting with R2 URLs."""
        db = SightingsDatabase(test_db_url)

        result = db.add_sighting(
            license_plate="T890123C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
            image_path_original=str(temp_image),
            image_url_web="https://r2.dev/web/image123.jpg",
        )

        assert result is not None
        sighting = db.get_sighting_by_id(result["id"])
        # Verify R2 URL was saved (column 11)
        assert sighting[11] == "https://r2.dev/web/image123.jpg"

    def test_add_sighting_without_gps(self, test_db_url, sample_contributor, temp_image):
        """Test adding sighting without GPS coordinates."""
        db = SightingsDatabase(test_db_url)

        result = db.add_sighting(
            license_plate="T901234C",
            timestamp=datetime.now().isoformat(),
            latitude=None,
            longitude=None,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
            borough="Brooklyn",  # Manually specified
        )

        assert result is not None
        sighting = db.get_sighting_by_id(result["id"])
        assert sighting[9] == "Brooklyn"

    def test_add_sighting_hash_calculation(self, test_db_url, sample_contributor, temp_image):
        """Test that hashes are automatically calculated if not provided."""
        db = SightingsDatabase(test_db_url)

        result = db.add_sighting(
            license_plate="T012345C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
            # No hashes provided - should be calculated
        )

        assert result is not None
        sighting = db.get_sighting_by_id(result["id"])
        # Verify hashes were calculated (columns 7 and 8)
        assert sighting[7] is not None  # SHA-256
        assert sighting[8] is not None  # Perceptual hash


@pytest.mark.db
class TestSightingQueries:
    """Test sighting query methods."""

    def test_get_sighting_count(self, test_db_url, sample_contributor, temp_image):
        """Test counting sightings for a plate."""
        db = SightingsDatabase(test_db_url)

        # Add multiple sightings for same plate
        for i in range(3):
            db.add_sighting(
                license_plate="T111111C",
                timestamp=datetime.now().isoformat(),
                latitude=40.7589,
                longitude=-73.9851,
                image_path=f"{temp_image}_{i}",
                contributor_id=sample_contributor,
            )

        count = db.get_sighting_count("T111111C")
        assert count == 3

    def test_get_unposted_sightings(self, test_db_url, sample_contributor, temp_image):
        """Test retrieving unposted sightings."""
        db = SightingsDatabase(test_db_url)

        # Add sighting
        result = db.add_sighting(
            license_plate="T222222C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
        )

        # Get unposted sightings
        unposted = db.get_unposted_sightings()
        assert len(unposted) > 0

        # Find our sighting
        found = any(s[0] == result["id"] for s in unposted)
        assert found

    def test_mark_as_posted(self, test_db_url, sample_contributor, temp_image):
        """Test marking a sighting as posted."""
        db = SightingsDatabase(test_db_url)

        # Add sighting
        result = db.add_sighting(
            license_plate="T333333C",
            timestamp=datetime.now().isoformat(),
            latitude=40.7589,
            longitude=-73.9851,
            image_path=str(temp_image),
            contributor_id=sample_contributor,
        )

        # Mark as posted
        post_uri = "at://did:plc:test/app.bsky.feed.post/abc123"
        db.mark_as_posted(result["id"], post_uri)

        # Verify it's no longer in unposted
        unposted = db.get_unposted_sightings()
        found = any(s[0] == result["id"] for s in unposted)
        assert not found


@pytest.mark.db
class TestContributorOperations:
    """Test contributor CRUD operations."""

    def test_get_or_create_contributor_new(self, test_db_url, clean_db):
        """Test creating a new contributor."""
        db = SightingsDatabase(test_db_url)

        contributor_id = db.get_or_create_contributor(
            phone_number="+15559998888",
            bluesky_handle="newuser.bsky.social",
        )

        assert contributor_id is not None
        contributor = db.get_contributor(contributor_id=contributor_id)
        assert contributor["phone_number"] == "+15559998888"

    def test_get_or_create_contributor_existing(self, test_db_url, sample_contributor):
        """Test getting an existing contributor."""
        db = SightingsDatabase(test_db_url)

        # Try to create with same phone number
        contributor_id = db.get_or_create_contributor(phone_number="+15551234567")

        # Should return existing ID
        assert contributor_id == sample_contributor

    def test_update_contributor_name(self, test_db_url, sample_contributor):
        """Test updating contributor preferred name."""
        db = SightingsDatabase(test_db_url)

        db.update_contributor_name(sample_contributor, "New Name")

        contributor = db.get_contributor(contributor_id=sample_contributor)
        assert contributor["preferred_name"] == "New Name"
