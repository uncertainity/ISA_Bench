"""MHRD puzzle definitions and loader."""

from .schema import Puzzle, TestCase
from .loader import load_puzzles, get_puzzle

__all__ = [
    "Puzzle",
    "TestCase",
    "load_puzzles",
    "get_puzzle",
]
