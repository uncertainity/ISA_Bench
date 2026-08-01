"""SIC-1 (Single Instruction Computer) adapter."""

from typing import Any, Dict, List, Optional

from .base import ExecutionResult
from ..models import TestCaseResult

from ...games.sic1.vm.assembler import Assembler, CompilationError
from ...games.sic1.vm.emulator import run_program, ExecutionError
from ...games.sic1.puzzles.loader import load_puzzles, get_puzzle
from ...games.sic1.puzzles.schema import Puzzle


class SIC1Adapter:
    """Adapter for SIC-1 puzzles."""

    @property
    def game_name(self) -> str:
        return "sic1"

    @property
    def metric_names(self) -> List[str]:
        return ["cycles", "bytes"]

    def load_puzzles(self) -> List[Puzzle]:
        """Load SIC-1 puzzles that have executable correctness tests."""
        return [puzzle for puzzle in load_puzzles() if puzzle.test_cases]

    def get_puzzle(self, puzzle_id: str) -> Puzzle:
        """Get puzzle by ID or index."""
        if puzzle_id.startswith("sic1_"):
            puzzle_id = puzzle_id.replace("sic1_", "")
        # Try as index first, then as ID
        try:
            return get_puzzle(int(puzzle_id))
        except (ValueError, KeyError):
            return get_puzzle(puzzle_id)

    def get_puzzle_id(self, puzzle: Puzzle) -> str:
        return f"sic1_{puzzle.id}"

    def get_puzzle_name(self, puzzle: Puzzle) -> str:
        return puzzle.title

    def get_commands(self, puzzle: Puzzle) -> List[str]:
        return ["subleq", ".data"]

    def get_par(self, puzzle: Puzzle) -> Optional[Dict[str, int]]:
        # SIC-1 doesn't have par values in the puzzle schema
        return None

    def format_description(self, puzzle: Puzzle) -> str:
        """Format puzzle description."""
        lines = [f"Puzzle: {puzzle.title}"]
        lines.append("\nInstruction: subleq a b [c]")
        lines.append("  mem[a] = mem[a] - mem[b]")
        lines.append("  if result <= 0: jump to c (default: next instruction)")
        lines.append("\nSpecial addresses: @IN=253, @OUT=254, @MAX=252")

        if puzzle.test_cases:
            tc = puzzle.test_cases[0]
            lines.append(f"\nExample:")
            lines.append(f"  Input: {tc.input}")
            lines.append(f"  Expected output: {tc.output}")

        return "\n".join(lines)

    def execute(
        self,
        code: str,
        puzzle: Puzzle,
        max_steps: int = 100_000,
    ) -> ExecutionResult:
        """Parse and execute SIC-1 code against puzzle test cases."""
        if not puzzle.test_cases:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=0,
                runtime_error="Puzzle has no test cases; correctness cannot be verified",
            )

        # Assemble the code
        try:
            program = Assembler.assemble_source(code)
        except CompilationError as e:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error=str(e),
            )

        # Run against each test case
        test_results = []
        tests_passed = 0
        total_cycles = 0
        runtime_error = None

        for tc in puzzle.test_cases:
            try:
                result = run_program(
                    program,
                    inputs=list(tc.input),
                    expected_output_count=len(tc.output),
                    max_cycles=max_steps,
                )
                passed = result.outputs == list(tc.output)
                total_cycles += result.cycles_executed

                test_results.append(
                    TestCaseResult(
                        passed=passed,
                        input_values=list(tc.input),
                        expected_output=list(tc.output),
                        actual_output=list(result.outputs),
                    )
                )
                if passed:
                    tests_passed += 1

            except ExecutionError as e:
                runtime_error = str(e)
                test_results.append(
                    TestCaseResult(
                        passed=False,
                        input_values=list(tc.input),
                        expected_output=list(tc.output),
                        actual_output=[],
                        error=str(e),
                    )
                )

        success = runtime_error is None and tests_passed == len(puzzle.test_cases)
        metrics = {
            "cycles": total_cycles,
            "bytes": len(program.bytes),
        }

        return ExecutionResult(
            success=success,
            tests_passed=tests_passed,
            tests_total=len(puzzle.test_cases),
            metrics=metrics,
            test_results=test_results,
            runtime_error=runtime_error,
        )
