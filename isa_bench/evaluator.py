"""Stable, LLM-independent interface for checking ISA Bench solutions."""

from __future__ import annotations

from dataclasses import dataclass

from .openenv.adapters import ADAPTERS, get_adapter, get_default_max_steps
from .openenv.adapters.base import ExecutionResult


@dataclass(frozen=True)
class PuzzleInfo:
    """Public metadata for a benchmark puzzle."""

    game: str
    puzzle_id: str
    name: str
    description: str
    available_commands: tuple[str, ...]


def list_games() -> tuple[str, ...]:
    """Return the canonical game identifiers in release order."""

    return tuple(ADAPTERS)


def list_puzzles(game: str) -> tuple[PuzzleInfo, ...]:
    """Return metadata for every released puzzle in ``game``."""

    adapter = get_adapter(game)
    return tuple(_to_info(adapter, puzzle) for puzzle in adapter.load_puzzles())


def get_puzzle_info(game: str, puzzle_id: str) -> PuzzleInfo:
    """Return public metadata for one puzzle."""

    adapter = get_adapter(game)
    return _to_info(adapter, adapter.get_puzzle(puzzle_id))


def check_solution(
    game: str,
    puzzle_id: str,
    code: str,
    *,
    max_steps: int | None = None,
) -> ExecutionResult:
    """Parse and execute ``code`` and compare it with the puzzle oracle.

    This function performs no LLM call and applies no reward shaping. A solution
    is correct only when the returned ``ExecutionResult.success`` is true.
    Parse and runtime failures are returned as structured fields rather than
    raised to the caller.
    """

    if not isinstance(code, str):
        raise TypeError("code must be a string")
    if max_steps is not None and max_steps <= 0:
        raise ValueError("max_steps must be positive")

    adapter = get_adapter(game)
    puzzle = adapter.get_puzzle(puzzle_id)
    execution_budget = max_steps or get_default_max_steps(game)
    return adapter.execute(code=code, puzzle=puzzle, max_steps=execution_budget)


def _to_info(adapter, puzzle) -> PuzzleInfo:
    return PuzzleInfo(
        game=adapter.game_name,
        puzzle_id=adapter.get_puzzle_id(puzzle),
        name=adapter.get_puzzle_name(puzzle),
        description=adapter.format_description(puzzle),
        available_commands=tuple(adapter.get_commands(puzzle)),
    )
