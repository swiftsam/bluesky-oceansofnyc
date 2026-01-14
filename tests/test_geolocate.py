"""Unit tests for geolocate module."""

import pytest

from geolocate.boroughs import get_borough_from_coords, parse_borough_input


@pytest.mark.unit
class TestGetBoroughFromCoords:
    """Test get_borough_from_coords() function."""

    def test_manhattan_times_square(self):
        """Test recognizing Times Square as Manhattan."""
        assert get_borough_from_coords(40.7589, -73.9851) == "Manhattan"

    def test_manhattan_central_park(self):
        """Test recognizing Central Park as Manhattan."""
        assert get_borough_from_coords(40.785, -73.968) == "Manhattan"

    def test_brooklyn_downtown(self):
        """Test recognizing Downtown Brooklyn."""
        assert get_borough_from_coords(40.693, -73.987) == "Brooklyn"

    def test_queens_flushing(self):
        """Test recognizing Flushing, Queens."""
        assert get_borough_from_coords(40.767, -73.833) == "Queens"

    def test_bronx_yankee_stadium(self):
        """Test recognizing Yankee Stadium area in Bronx."""
        assert get_borough_from_coords(40.829, -73.926) == "Bronx"

    def test_staten_island_ferry_terminal(self):
        """Test recognizing Staten Island Ferry area."""
        assert get_borough_from_coords(40.643, -74.074) == "Staten Island"

    def test_outside_nyc_returns_none(self):
        """Test that coordinates outside NYC return None."""
        # Somewhere in New Jersey
        assert get_borough_from_coords(40.730, -74.200) is None

    def test_far_outside_nyc_returns_none(self):
        """Test coordinates far from NYC return None."""
        # Somewhere random
        assert get_borough_from_coords(0, 0) is None

    def test_manhattan_south_boundary(self):
        """Test coordinates near Manhattan's southern boundary."""
        assert get_borough_from_coords(40.701, -74.015) == "Manhattan"

    def test_brooklyn_north_boundary(self):
        """Test coordinates near Brooklyn's northern boundary."""
        assert get_borough_from_coords(40.738, -73.95) == "Brooklyn"


@pytest.mark.unit
class TestParseBoroughInput:
    """Test parse_borough_input() function."""

    def test_manhattan_full_name(self):
        """Test parsing full 'Manhattan' string."""
        assert parse_borough_input("Manhattan") == "Manhattan"

    def test_manhattan_lowercase(self):
        """Test parsing lowercase 'manhattan'."""
        assert parse_borough_input("manhattan") == "Manhattan"

    def test_manhattan_uppercase(self):
        """Test parsing uppercase 'MANHATTAN'."""
        assert parse_borough_input("MANHATTAN") == "Manhattan"

    def test_manhattan_single_letter(self):
        """Test parsing 'M' for Manhattan."""
        assert parse_borough_input("M") == "Manhattan"

    def test_manhattan_single_letter_lowercase(self):
        """Test parsing 'm' for Manhattan."""
        assert parse_borough_input("m") == "Manhattan"

    def test_brooklyn_full_name(self):
        """Test parsing 'Brooklyn'."""
        assert parse_borough_input("Brooklyn") == "Brooklyn"

    def test_brooklyn_single_letter(self):
        """Test parsing 'B' for Brooklyn."""
        assert parse_borough_input("B") == "Brooklyn"

    def test_queens_full_name(self):
        """Test parsing 'Queens'."""
        assert parse_borough_input("Queens") == "Queens"

    def test_queens_single_letter(self):
        """Test parsing 'Q' for Queens."""
        assert parse_borough_input("Q") == "Queens"

    def test_bronx_full_name(self):
        """Test parsing 'Bronx'."""
        assert parse_borough_input("Bronx") == "Bronx"

    def test_bronx_single_letter(self):
        """Test parsing 'X' for Bronx."""
        assert parse_borough_input("X") == "Bronx"

    def test_staten_island_full_name(self):
        """Test parsing 'Staten Island'."""
        assert parse_borough_input("Staten Island") == "Staten Island"

    def test_staten_island_abbreviation(self):
        """Test parsing 'SI' for Staten Island."""
        assert parse_borough_input("SI") == "Staten Island"

    def test_staten_island_single_letter(self):
        """Test parsing 'S' for Staten Island."""
        assert parse_borough_input("S") == "Staten Island"

    def test_whitespace_trimmed(self):
        """Test that leading/trailing whitespace is handled."""
        assert parse_borough_input("  Manhattan  ") == "Manhattan"
        assert parse_borough_input(" B ") == "Brooklyn"

    def test_mixed_case(self):
        """Test mixed case input."""
        assert parse_borough_input("BrOoKlYn") == "Brooklyn"
        assert parse_borough_input("mAnHaTtAn") == "Manhattan"

    def test_invalid_input_returns_none(self):
        """Test that invalid borough names return None."""
        assert parse_borough_input("Newark") is None
        assert parse_borough_input("Z") is None
        assert parse_borough_input("NYC") is None
        assert parse_borough_input("") is None

    def test_partial_names_not_recognized(self):
        """Test that partial borough names are not recognized."""
        assert parse_borough_input("Man") is None
        assert parse_borough_input("Bro") is None
        assert parse_borough_input("Queen") is None
