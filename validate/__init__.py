"""Validate module - license plate validation against TLC database."""

from .matcher import get_potential_matches, validate_plate
from .tlc import TLCDatabase

__all__ = ["TLCDatabase", "validate_plate", "get_potential_matches"]
