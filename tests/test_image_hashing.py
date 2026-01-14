"""Unit tests for image hashing utilities."""

import pytest

from utils.image_hashing import hamming_distance


@pytest.mark.unit
class TestHammingDistance:
    """Test hamming_distance() function."""

    def test_identical_hashes(self):
        """Test that identical hashes have distance of 0."""
        hash1 = "abc123def456"
        hash2 = "abc123def456"
        assert hamming_distance(hash1, hash2) == 0

    def test_completely_different_hashes(self):
        """Test hashes that differ in all bits."""
        # 0000 vs ffff (all bits different)
        hash1 = "0000"
        hash2 = "ffff"
        assert hamming_distance(hash1, hash2) == 16

    def test_single_bit_difference(self):
        """Test hashes that differ by exactly one bit."""
        # 0000 vs 0001 (last bit different)
        hash1 = "0000"
        hash2 = "0001"
        assert hamming_distance(hash1, hash2) == 1

    def test_single_hex_character_difference(self):
        """Test hashes that differ by one hex character."""
        # a = 1010, b = 1011 (differ by 1 bit)
        hash1 = "aaaa"
        hash2 = "baaa"
        assert hamming_distance(hash1, hash2) == 1

    def test_multiple_bit_differences(self):
        """Test hashes with several bit differences."""
        # 0 = 0000, f = 1111 (4 bits different)
        hash1 = "0f0f"
        hash2 = "f0f0"
        # Each position: 0 vs f = 4 bits, so 4 positions * 4 bits = 16 bits different
        assert hamming_distance(hash1, hash2) == 16

    def test_typical_perceptual_hash_length(self):
        """Test with typical 16-character perceptual hashes."""
        hash1 = "a1b2c3d4e5f6a7b8"
        hash2 = "a1b2c3d4e5f6a7b9"
        # Last character: 8 = 1000, 9 = 1001 (1 bit different)
        assert hamming_distance(hash1, hash2) == 1

    def test_case_insensitive_comparison(self):
        """Test that hash comparison is case-insensitive."""
        hash1 = "ABC123"
        hash2 = "abc123"
        assert hamming_distance(hash1, hash2) == 0

    def test_uppercase_and_lowercase_mixed(self):
        """Test mixed case hashes."""
        hash1 = "AbC123"
        hash2 = "aBc123"
        assert hamming_distance(hash1, hash2) == 0

    def test_mismatched_length_raises_error(self):
        """Test that hashes of different lengths raise ValueError."""
        hash1 = "abc123"
        hash2 = "abc123def"
        with pytest.raises(ValueError, match="Hash lengths must match"):
            hamming_distance(hash1, hash2)

    def test_empty_hashes(self):
        """Test that empty hashes have distance of 0."""
        assert hamming_distance("", "") == 0

    def test_invalid_hex_raises_error(self):
        """Test that invalid hex characters raise ValueError."""
        hash1 = "abc123"
        hash2 = "xyz789"
        with pytest.raises(ValueError, match="Invalid hex hash"):
            hamming_distance(hash1, hash2)

    def test_hamming_distance_properties(self):
        """Test mathematical properties of Hamming distance."""
        hash1 = "abc123"
        hash2 = "def456"
        hash3 = "abc123"

        # Identity: d(x, x) = 0
        assert hamming_distance(hash1, hash1) == 0

        # Symmetry: d(x, y) = d(y, x)
        assert hamming_distance(hash1, hash2) == hamming_distance(hash2, hash1)

        # Non-negativity: d(x, y) >= 0
        assert hamming_distance(hash1, hash2) >= 0

        # Equal hashes have zero distance
        assert hamming_distance(hash1, hash3) == 0

    def test_specific_bit_differences(self):
        """Test specific known bit differences."""
        # Binary: 0001 vs 0010 (2 bits different)
        hash1 = "1"
        hash2 = "2"
        assert hamming_distance(hash1, hash2) == 2

        # Binary: 0001 vs 0011 (1 bit different)
        hash1 = "1"
        hash2 = "3"
        assert hamming_distance(hash1, hash2) == 1

    def test_real_world_similar_images(self):
        """Test distance typical of similar images (5-10 bits)."""
        # Simulating hashes from similar images
        # These would typically differ by 5-10 bits
        hash1 = "a1b2c3d4e5f6a7b8"
        hash2 = "a1b2c3d4e5f6a7bf"  # Last char: 8 vs f = 0111 difference = 3 bits
        distance = hamming_distance(hash1, hash2)
        assert 0 < distance < 10  # Typical range for similar images

    def test_long_hashes(self):
        """Test with longer hash strings."""
        hash1 = "0" * 32
        hash2 = "f" * 32
        # Each character differs by 4 bits, 32 chars * 4 = 128 bits
        assert hamming_distance(hash1, hash2) == 128
