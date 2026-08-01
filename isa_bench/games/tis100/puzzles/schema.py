"""TIS-100 puzzle data schema."""

from dataclasses import dataclass, field


@dataclass
class Stream:
    """An input or output stream."""

    column: int  # 0-3 for the 4 columns
    values: list[int] = field(default_factory=list)


@dataclass
class Puzzle:
    """TIS-100 puzzle definition."""

    id: str
    name: str
    description: str
    inputs: list[Stream] = field(default_factory=list)
    outputs: list[Stream] = field(default_factory=list)
    disabled_nodes: list[int] = field(default_factory=list)  # Damaged nodes
    stack_nodes: list[int] = field(default_factory=list)  # T30 stack memory nodes
    index: int = 0

    def get_input_dict(self) -> dict[int, list[int]]:
        """Get inputs as column -> values dict."""
        return {s.column: s.values for s in self.inputs}

    def get_output_dict(self) -> dict[int, list[int]]:
        """Get expected outputs as column -> values dict."""
        return {s.column: s.values for s in self.outputs}
