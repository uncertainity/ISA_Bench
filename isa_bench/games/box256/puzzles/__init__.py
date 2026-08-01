"""BOX-256 puzzle definitions."""

from .schema import Puzzle
from .loader import load_puzzles, get_puzzle

__all__ = ["Puzzle", "load_puzzles", "get_puzzle"]
