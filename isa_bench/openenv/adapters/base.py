"""Base adapter protocol for ISA games."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from ..models import TestCaseResult


@dataclass
class ExecutionResult:
    """Result from executing code against a puzzle."""

    success: bool
    tests_passed: int
    tests_total: int
    metrics: Dict[str, Any] = field(default_factory=dict)
    test_results: List[TestCaseResult] = field(default_factory=list)
    parse_error: Optional[str] = None
    runtime_error: Optional[str] = None


@runtime_checkable
class GameAdapter(Protocol):
    """Protocol for game-specific adapters.

    Each game implements this interface to connect the OpenEnv
    environment to its VM/emulator.
    """

    @property
    def game_name(self) -> str:
        """Return game identifier (e.g., 'hrm')."""
        ...

    @property
    def metric_names(self) -> List[str]:
        """Return list of metric names tracked by this game."""
        ...

    def load_puzzles(self) -> List[Any]:
        """Load all puzzles for this game."""
        ...

    def get_puzzle(self, puzzle_id: str) -> Any:
        """Get a specific puzzle by ID."""
        ...

    def get_puzzle_id(self, puzzle: Any) -> str:
        """Get the ID of a puzzle."""
        ...

    def get_puzzle_name(self, puzzle: Any) -> str:
        """Get the display name of a puzzle."""
        ...

    def get_commands(self, puzzle: Any) -> List[str]:
        """Get available commands/instructions for a puzzle."""
        ...

    def get_par(self, puzzle: Any) -> Optional[Dict[str, int]]:
        """Get optimization targets (par values) for a puzzle."""
        ...

    def format_description(self, puzzle: Any) -> str:
        """Format puzzle description for display."""
        ...

    def execute(
        self,
        code: str,
        puzzle: Any,
        max_steps: int = 100_000,
    ) -> ExecutionResult:
        """Parse and execute code against puzzle test cases."""
        ...
