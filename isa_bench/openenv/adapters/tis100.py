"""TIS-100 adapter."""

from typing import Any, Dict, List, Optional

from .base import ExecutionResult
from ..models import TestCaseResult

from ...games.tis100.vm.parser import parse as parse_multi_node, ParseError
from ...games.tis100.vm.emulator import Grid, ExecutionError
from ...games.tis100.puzzles.loader import load_puzzles, get_puzzle
from ...games.tis100.puzzles.schema import Puzzle


class TIS100Adapter:
    """Adapter for TIS-100 puzzles."""

    @property
    def game_name(self) -> str:
        return "tis100"

    @property
    def metric_names(self) -> List[str]:
        return ["cycles", "nodes", "instructions"]

    def load_puzzles(self) -> List[Puzzle]:
        """Load all TIS-100 puzzles."""
        return load_puzzles()

    def get_puzzle(self, puzzle_id: str) -> Puzzle:
        """Get puzzle by ID or index."""
        if puzzle_id.startswith("tis100_"):
            puzzle_id = puzzle_id.replace("tis100_", "")
        try:
            return get_puzzle(int(puzzle_id))
        except (ValueError, KeyError):
            return get_puzzle(puzzle_id)

    def get_puzzle_id(self, puzzle: Puzzle) -> str:
        return f"tis100_{puzzle.id}"

    def get_puzzle_name(self, puzzle: Puzzle) -> str:
        return puzzle.name

    def get_commands(self, puzzle: Puzzle) -> List[str]:
        return [
            "MOV",
            "ADD",
            "SUB",
            "NEG",
            "SAV",
            "SWP",
            "JMP",
            "JEZ",
            "JNZ",
            "JGZ",
            "JLZ",
            "JRO",
            "NOP",
        ]

    def get_par(self, puzzle: Puzzle) -> Optional[Dict[str, int]]:
        return None

    def format_description(self, puzzle: Puzzle) -> str:
        """Format puzzle description."""
        lines = [puzzle.description]
        lines.append("\nGrid: 4x3 nodes (indexed 0-11)")
        lines.append("Use @N markers to specify code per node.")
        lines.append("\nPorts: UP, DOWN, LEFT, RIGHT, ANY, LAST")
        lines.append("Registers: ACC, NIL")

        # Show input/output streams
        if puzzle.inputs:
            for stream in puzzle.inputs:
                lines.append(f"\nInput column {stream.column}: {stream.values}")
        if puzzle.outputs:
            for stream in puzzle.outputs:
                lines.append(f"Expected output column {stream.column}: {stream.values}")

        return "\n".join(lines)

    def execute(
        self,
        code: str,
        puzzle: Puzzle,
        max_steps: int = 100_000,
    ) -> ExecutionResult:
        """Parse and execute TIS-100 code against puzzle."""
        expected_value_count = sum(len(stream.values) for stream in puzzle.outputs)
        if expected_value_count == 0:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=0,
                runtime_error=(
                    "Puzzle has no expected output values; correctness cannot be verified"
                ),
            )

        # Parse multi-node code
        try:
            programs = parse_multi_node(code)
        except ParseError as e:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=1,
                parse_error=str(e),
            )

        # Set up input/output streams
        inputs = {s.column: list(s.values) for s in puzzle.inputs}
        expected = {s.column: list(s.values) for s in puzzle.outputs}

        # Run the grid
        try:
            grid = Grid(programs=programs, inputs=inputs, expected_outputs=expected)
            grid_result = grid.run(max_cycles=max_steps)

            # A TIS-100 run completes when every configured output stream has
            # produced its expected number of values.  Reaching the cycle
            # budget before that point is a timeout, not merely a wrong answer.
            timed_out = not grid_result.completed

            # Compare every physical output column.  This rejects programs
            # that produce the requested streams plus unrequested extra output.
            success = not timed_out and all(
                grid_result.outputs.get(col, []) == expected.get(col, [])
                for col in range(4)
            )

            metrics = {
                "cycles": grid_result.cycles,
                "nodes": grid_result.nodes_used,
                "instructions": grid_result.instructions,
            }

            # Flatten inputs and outputs for TestCaseResult
            input_list = [v for col in sorted(inputs.keys()) for v in inputs[col]]
            expected_list = [
                v for col in sorted(expected.keys()) for v in expected[col]
            ]
            actual_list = [
                value for col in range(4) for value in grid_result.outputs.get(col, [])
            ]

            runtime_error = (
                f"Cycle limit exceeded: {max_steps} cycles" if timed_out else None
            )

            test_results = [
                TestCaseResult(
                    passed=success,
                    input_values=input_list,
                    expected_output=expected_list,
                    actual_output=actual_list,
                    error=runtime_error,
                )
            ]

            return ExecutionResult(
                success=success,
                tests_passed=1 if success else 0,
                tests_total=1,
                metrics=metrics,
                test_results=test_results,
                runtime_error=runtime_error,
            )

        except ExecutionError as e:
            input_list = [v for col in sorted(inputs.keys()) for v in inputs[col]]
            expected_list = [
                v for col in sorted(expected.keys()) for v in expected[col]
            ]
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=1,
                runtime_error=str(e),
                test_results=[
                    TestCaseResult(
                        passed=False,
                        input_values=input_list,
                        expected_output=expected_list,
                        actual_output=[],
                        error=str(e),
                    )
                ],
            )
