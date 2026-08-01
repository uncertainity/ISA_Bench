"""TIS-100 Grid emulator.

Coordinates a 4x3 grid of 12 nodes with blocking port communication.
Handles input/output streams at the top and bottom of the grid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .parser import NodeProgram, parse
from .node import Node, Port, NodeState
from .errors import ExecutionError

# Grid dimensions
GRID_WIDTH = 4
GRID_HEIGHT = 3
TOTAL_NODES = GRID_WIDTH * GRID_HEIGHT

# ANY port priority
ANY_PRIORITY = [Port.UP, Port.LEFT, Port.RIGHT, Port.DOWN]


def _opposite_port(port: Port) -> Port:
    """Get the opposite direction port."""
    return {
        Port.UP: Port.DOWN,
        Port.DOWN: Port.UP,
        Port.LEFT: Port.RIGHT,
        Port.RIGHT: Port.LEFT,
    }.get(port, port)


@dataclass
class GridResult:
    """Result from running the grid."""

    outputs: dict[int, list[int]]  # Column -> output values
    cycles: int
    nodes_used: int
    instructions: int
    completed: bool = False


class Grid:
    """TIS-100 grid of compute nodes."""

    def __init__(
        self,
        programs: dict[int, NodeProgram] | None = None,
        inputs: dict[int, list[int]] | None = None,
        expected_outputs: dict[int, list[int]] | None = None,
    ):
        """Initialize the grid.

        Args:
            programs: Dict mapping node index (0-11) to NodeProgram
            inputs: Dict mapping column (0-3) to input values
            expected_outputs: Dict mapping column (0-3) to expected output values
        """
        self.programs = programs or {}
        self.input_streams = inputs or {}
        self.expected_outputs = expected_outputs or {}

        # Create nodes
        self.nodes: list[Node] = []
        for i in range(TOTAL_NODES):
            program = self.programs.get(i)
            self.nodes.append(Node(i, program))

        # Set up adjacencies
        self._setup_adjacencies()

        # Input/output state
        self.input_positions: dict[int, int] = {col: 0 for col in range(GRID_WIDTH)}
        self.outputs: dict[int, list[int]] = {col: [] for col in range(GRID_WIDTH)}

        # Cycle counter
        self.cycles = 0

    def _setup_adjacencies(self) -> None:
        """Set up neighbor pointers between nodes."""
        for i, node in enumerate(self.nodes):
            col = i % GRID_WIDTH
            row = i // GRID_WIDTH

            # UP neighbor
            if row > 0:
                node.neighbors[Port.UP] = self.nodes[i - GRID_WIDTH]
            # DOWN neighbor
            if row < GRID_HEIGHT - 1:
                node.neighbors[Port.DOWN] = self.nodes[i + GRID_WIDTH]
            # LEFT neighbor
            if col > 0:
                node.neighbors[Port.LEFT] = self.nodes[i - 1]
            # RIGHT neighbor
            if col < GRID_WIDTH - 1:
                node.neighbors[Port.RIGHT] = self.nodes[i + 1]

    def reset(self) -> None:
        """Reset all nodes and state."""
        for node in self.nodes:
            node.reset()
        self.input_positions = {col: 0 for col in range(GRID_WIDTH)}
        self.outputs = {col: [] for col in range(GRID_WIDTH)}
        self.cycles = 0

    def _resolve_any_port(self, node: Node, for_write: bool) -> Port | None:
        """Resolve ANY to a specific port based on priority and availability."""
        for port in ANY_PRIORITY:
            neighbor = node.neighbors.get(port)
            if neighbor is None:
                continue

            if for_write:
                # For write, check if neighbor is reading from us
                if neighbor.state == NodeState.READ and neighbor.pending is not None:
                    neighbor_port = neighbor.pending.port
                    if neighbor_port == Port.ANY:
                        # Neighbor using ANY - check if we're in their priority
                        continue  # Complex case, skip for now
                    elif neighbor_port == Port.LAST:
                        if (
                            neighbor.last_port
                            and _opposite_port(neighbor.last_port) == port
                        ):
                            return port
                    elif _opposite_port(neighbor_port) == port:
                        return port
            else:
                # For read, check if neighbor is writing to us
                if neighbor.state == NodeState.WRITE and neighbor.pending is not None:
                    neighbor_port = neighbor.pending.port
                    if neighbor_port == Port.ANY:
                        continue
                    elif neighbor_port == Port.LAST:
                        if (
                            neighbor.last_port
                            and _opposite_port(neighbor.last_port) == port
                        ):
                            return port
                    elif _opposite_port(neighbor_port) == port:
                        return port

        return None

    def _try_complete_io(self) -> bool:
        """Try to complete pending I/O operations. Returns True if any completed."""
        completed_any = False

        # Handle top row reading from inputs
        for col in range(GRID_WIDTH):
            node = self.nodes[col]  # Top row
            if (
                node.state == NodeState.READ
                and node.pending is not None
                and node.pending.port == Port.UP
            ):
                # Reading from input stream
                stream = self.input_streams.get(col, [])
                pos = self.input_positions[col]
                if pos < len(stream):
                    value = stream[pos]
                    self.input_positions[col] = pos + 1
                    node.complete_read(value, Port.UP)
                    completed_any = True

        # Handle bottom row writing to outputs
        for col in range(GRID_WIDTH):
            node = self.nodes[col + GRID_WIDTH * (GRID_HEIGHT - 1)]  # Bottom row
            if (
                node.state == NodeState.WRITE
                and node.pending is not None
                and node.pending.port == Port.DOWN
            ):
                # Writing to output stream
                value = node.pending.value
                self.outputs[col].append(value)
                node.complete_write(Port.DOWN)
                completed_any = True

        # Handle inter-node communication
        for node in self.nodes:
            if node.pending is None:
                continue

            port = node.pending.port

            # Resolve ANY/LAST
            actual_port = port
            if port == Port.ANY:
                resolved = self._resolve_any_port(node, node.pending.is_write)
                if resolved is None:
                    continue
                actual_port = resolved
            elif port == Port.LAST:
                if node.last_port is None:
                    continue
                actual_port = node.last_port

            neighbor = node.neighbors.get(actual_port)
            if neighbor is None:
                continue

            opposite = _opposite_port(actual_port)

            if node.pending.is_write:
                # We want to write, check if neighbor is reading from us
                if neighbor.state == NodeState.READ and neighbor.pending is not None:
                    neighbor_port = neighbor.pending.port
                    # Resolve neighbor's port
                    if neighbor_port == Port.ANY:
                        neighbor_resolved = self._resolve_any_port(neighbor, False)
                        if neighbor_resolved != opposite:
                            continue
                    elif neighbor_port == Port.LAST:
                        if neighbor.last_port != opposite:
                            continue
                    elif neighbor_port != opposite:
                        continue

                    # Transfer value
                    value = node.pending.value
                    neighbor.complete_read(value, opposite)
                    node.complete_write(actual_port)
                    completed_any = True

            else:
                # We want to read, check if neighbor is writing to us
                if neighbor.state == NodeState.WRITE and neighbor.pending is not None:
                    neighbor_port = neighbor.pending.port
                    # Resolve neighbor's port
                    if neighbor_port == Port.ANY:
                        neighbor_resolved = self._resolve_any_port(neighbor, True)
                        if neighbor_resolved != opposite:
                            continue
                    elif neighbor_port == Port.LAST:
                        if neighbor.last_port != opposite:
                            continue
                    elif neighbor_port != opposite:
                        continue

                    # Transfer value
                    value = neighbor.pending.value
                    node.complete_read(value, actual_port)
                    neighbor.complete_write(opposite)
                    completed_any = True

        return completed_any

    def _is_finished(self) -> bool:
        """Check if all expected outputs have been produced."""
        if not self.expected_outputs:
            # No expected outputs defined - run until inputs exhausted
            return all(
                self.input_positions.get(col, 0) >= len(self.input_streams.get(col, []))
                for col in range(GRID_WIDTH)
            )

        for col, expected in self.expected_outputs.items():
            actual = self.outputs.get(col, [])
            if len(actual) < len(expected):
                return False
        return True

    def step(self) -> bool:
        """Execute one cycle. Returns True if grid should continue."""
        # Step all non-blocked nodes
        for node in self.nodes:
            node.step()

        # Try to complete I/O operations
        self._try_complete_io()

        self.cycles += 1

        return not self._is_finished()

    def run(self, max_cycles: int = 100_000) -> GridResult:
        """Run until completion or cycle limit."""
        while self.cycles < max_cycles:
            if not self.step():
                break

        # Calculate stats
        nodes_used = sum(1 for n in self.nodes if not n.is_empty)
        instructions = sum(len(n.program.instructions) for n in self.nodes)

        return GridResult(
            outputs=dict(self.outputs),
            cycles=self.cycles,
            nodes_used=nodes_used,
            instructions=instructions,
            completed=self._is_finished(),
        )


def run_program(
    source: str,
    inputs: dict[int, list[int]],
    expected_outputs: dict[int, list[int]] | None = None,
    max_cycles: int = 100_000,
) -> GridResult:
    """Parse and run a TIS-100 program.

    Args:
        source: TIS-100 solution with @N markers
        inputs: Dict mapping column (0-3) to input values
        expected_outputs: Optional expected outputs for completion check
        max_cycles: Maximum cycles before timeout

    Returns:
        GridResult with outputs and stats
    """
    programs = parse(source)
    grid = Grid(programs, inputs, expected_outputs)
    return grid.run(max_cycles)
