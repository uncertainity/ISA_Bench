"""HRM puzzle data schema."""

from dataclasses import dataclass, field
from typing import Union

Value = Union[int, str]


@dataclass
class FloorLayout:
    """Floor tile layout for a puzzle."""

    columns: int
    rows: int
    tiles: list[Value | None] = field(default_factory=list)

    def to_dict(self) -> dict[int, Value]:
        """Convert to address -> value dict for emulator."""
        return {i: v for i, v in enumerate(self.tiles) if v is not None}


@dataclass
class TestCase:
    """A single test case for a puzzle."""

    inbox: list[Value]
    outbox: list[Value]


@dataclass
class Challenge:
    """Optimization targets for a puzzle."""

    size: int  # Target instruction count
    speed: int  # Target step count


@dataclass
class Puzzle:
    """HRM puzzle definition."""

    number: int
    name: str
    instructions: str
    commands: list[str]
    test_cases: list[TestCase] = field(default_factory=list)
    floor: FloorLayout | None = None
    challenge: Challenge | None = None
    is_cutscene: bool = False
