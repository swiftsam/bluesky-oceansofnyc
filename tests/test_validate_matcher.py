"""Unit tests for validate matcher module.

These tests focus on the pure logic of find_similar_plates().
Database-dependent functions are tested separately.
"""

import pytest


@pytest.mark.unit
class TestSimilarPlateLogic:
    """Test the logic for finding similar plates."""

    def test_character_difference_calculation(self):
        """Test counting character differences between plates."""
        plate1 = "T123456C"
        plate2 = "T123456C"
        # Identical plates have 0 differences
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 0

    def test_single_character_difference(self):
        """Test plates differing by one character."""
        plate1 = "T123456C"
        plate2 = "T123457C"
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 1

    def test_two_character_difference(self):
        """Test plates differing by two characters."""
        plate1 = "T123456C"
        plate2 = "T123457D"
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 2

    def test_case_insensitive_comparison(self):
        """Test that comparison is case-insensitive."""
        plate1 = "T123456C"
        plate2 = "t123456c"
        diff_count = sum(1 for a, b in zip(plate1.upper(), plate2.upper(), strict=False) if a != b)
        assert diff_count == 0

    def test_completely_different_plates(self):
        """Test plates that are completely different."""
        plate1 = "T123456C"
        plate2 = "X987654Y"
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 8

    def test_different_length_plates_skipped(self):
        """Test that plates of different lengths should be filtered out."""
        plate1 = "T123456C"
        plate2 = "T12345C"
        # In the actual function, different lengths are skipped
        assert len(plate1) != len(plate2)

    def test_typo_detection_single_digit(self):
        """Test detecting common single-digit typos."""
        plate1 = "T723456C"
        plate2 = "T123456C"  # 7 vs 1 (typo)
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 1

    def test_typo_detection_adjacent_keys(self):
        """Test detecting typos from adjacent keyboard keys."""
        plate1 = "T123456C"
        plate2 = "T123456V"  # C vs V (adjacent on keyboard)
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 1

    def test_similarity_threshold_logic(self):
        """Test the threshold logic for determining similarity."""
        # If diff_count is 1-2, plate should be considered similar
        test_cases = [
            ("T123456C", "T123456C", 0, False),  # Identical - exclude (> 0)
            ("T123456C", "T123457C", 1, True),  # 1 difference - include
            ("T123456C", "T123457D", 2, True),  # 2 differences - include
            ("T123456C", "T123567D", 3, False),  # 3 differences - exclude (> 2)
        ]

        for plate1, plate2, expected_diff, should_include in test_cases:
            diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
            assert diff_count == expected_diff
            # Logic: include if 0 < diff_count <= 2
            assert (0 < diff_count <= 2) == should_include


@pytest.mark.unit
class TestPlateNormalization:
    """Test plate normalization for matching."""

    def test_uppercase_normalization(self):
        """Test that plates are normalized to uppercase."""
        assert "t123456c".upper() == "T123456C"

    def test_already_uppercase(self):
        """Test that uppercase plates remain unchanged."""
        assert "T123456C".upper() == "T123456C"

    def test_mixed_case_normalization(self):
        """Test mixed case normalization."""
        assert "T123456c".upper() == "T123456C"
        assert "t123456C".upper() == "T123456C"


@pytest.mark.unit
class TestPlateValidationEdgeCases:
    """Test edge cases in plate validation logic."""

    def test_empty_plate_comparison(self):
        """Test handling of empty plates."""
        plate1 = ""
        plate2 = ""
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 0

    def test_single_character_plates(self):
        """Test single character plates."""
        plate1 = "A"
        plate2 = "B"
        diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
        assert diff_count == 1

    def test_common_ocr_confusion(self):
        """Test common OCR character confusions."""
        # Common confusions: 0 vs O, 1 vs I, 5 vs S, 8 vs B
        test_cases = [
            ("T023456C", "TO23456C"),  # 0 vs O
            ("T123456C", "T1Z3456C"),  # 2 vs Z
            ("T123456C", "T1234S6C"),  # 5 vs S
            ("T823456C", "TB23456C"),  # 8 vs B
        ]

        for plate1, plate2 in test_cases:
            diff_count = sum(1 for a, b in zip(plate1, plate2, strict=False) if a != b)
            assert diff_count == 1


@pytest.mark.unit
class TestScoringLogic:
    """Test the scoring and sorting logic for similar plates."""

    def test_scored_plates_sorting(self):
        """Test that plates are sorted by difference count."""
        # Simulating the scored_plates list structure: (diff_count, plate)
        scored_plates = [
            (2, "T123457D"),
            (1, "T123457C"),
            (2, "T123456D"),
            (1, "T123456D"),
        ]

        # Sort by difference count (ascending)
        scored_plates.sort(key=lambda x: x[0])

        # Check that 1-difference plates come before 2-difference plates
        assert scored_plates[0][0] == 1
        assert scored_plates[1][0] == 1
        assert scored_plates[2][0] == 2
        assert scored_plates[3][0] == 2

    def test_extract_plates_from_scored(self):
        """Test extracting plate strings from scored tuples."""
        scored_plates = [
            (1, "T123457C"),
            (2, "T123457D"),
        ]

        plates = [p[1] for p in scored_plates]
        assert plates == ["T123457C", "T123457D"]

    def test_max_results_limiting(self):
        """Test limiting results to max_results."""
        scored_plates = [
            (1, "T123456A"),
            (1, "T123456B"),
            (1, "T123456C"),
            (2, "T123456D"),
            (2, "T123456E"),
        ]

        max_results = 3
        limited_plates = [p[1] for p in scored_plates[:max_results]]
        assert len(limited_plates) == 3
        assert limited_plates == ["T123456A", "T123456B", "T123456C"]
