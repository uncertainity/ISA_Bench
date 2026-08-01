"""Public API for the ISA Bench executable software release."""

from .evaluator import (
    PuzzleInfo,
    check_solution,
    get_puzzle_info,
    list_games,
    list_puzzles,
)
from .manifest import get_benchmark_manifest
from .openenv.adapters.base import ExecutionResult

__version__ = "0.1.0"

__all__ = [
    "ExecutionResult",
    "PuzzleInfo",
    "check_solution",
    "get_puzzle_info",
    "get_benchmark_manifest",
    "list_games",
    "list_puzzles",
]
