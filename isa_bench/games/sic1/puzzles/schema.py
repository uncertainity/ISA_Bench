"""SIC-1 puzzle data schema."""

from dataclasses import dataclass, field


@dataclass
class TestCase:
    input: list[int]
    output: list[int]


@dataclass
class Puzzle:
    id: str
    title: str
    index: int
    test_cases: list[TestCase] = field(default_factory=list)
