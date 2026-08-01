"""MHRD puzzle data schema."""

from dataclasses import dataclass, field


@dataclass
class TestCase:
    """A single test case for a puzzle."""

    inputs: dict[str, int | list[int]]  # Pin name -> value(s)
    outputs: dict[str, int | list[int]]  # Expected outputs


@dataclass
class Puzzle:
    """MHRD puzzle definition."""

    name: str  # Component name (e.g., "NOT", "AND")
    description: str
    inputs: list[tuple[str, int]]  # (name, width) pairs
    outputs: list[tuple[str, int]]  # (name, width) pairs
    test_cases: list[TestCase] = field(default_factory=list)
    available_components: list[str] = field(default_factory=list)
    index: int = 0  # Level order

    @property
    def input_pins(self) -> list[str]:
        """Get list of input pin names."""
        return [name for name, _ in self.inputs]

    @property
    def output_pins(self) -> list[str]:
        """Get list of output pin names."""
        return [name for name, _ in self.outputs]
