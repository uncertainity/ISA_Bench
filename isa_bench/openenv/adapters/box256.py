"""BOX-256 adapter."""

from typing import Any, Dict, List, Optional

from .base import ExecutionResult
from ..models import TestCaseResult

from ...games.box256.vm.parser import parse, ParseError
from ...games.box256.vm.emulator import Emulator, ExecutionError
from ...games.box256.puzzles.loader import load_puzzles, get_puzzle
from ...games.box256.puzzles.schema import Puzzle


class BOX256Adapter:
    """Adapter for BOX-256 puzzles."""

    @property
    def game_name(self) -> str:
        return "box256"

    @property
    def metric_names(self) -> List[str]:
        return ["cycles", "pixel_accuracy", "code_size"]

    def load_puzzles(self) -> List[Puzzle]:
        """Load all BOX-256 puzzles."""
        return load_puzzles()

    def get_puzzle(self, puzzle_id: str | int) -> Puzzle:
        """Get puzzle by ID or index."""
        if isinstance(puzzle_id, int):
            return get_puzzle(puzzle_id)
        if puzzle_id.startswith("box256_"):
            puzzle_id = puzzle_id.replace("box256_", "")
        try:
            return get_puzzle(int(puzzle_id))
        except (ValueError, KeyError):
            return get_puzzle(puzzle_id)

    def get_puzzle_id(self, puzzle: Puzzle) -> str:
        return f"box256_{puzzle.id}"

    def get_puzzle_name(self, puzzle: Puzzle) -> str:
        return puzzle.name

    def get_commands(self, puzzle: Puzzle) -> List[str]:
        return [
            "MOV",
            "ADD",
            "SUB",
            "MUL",
            "DIV",
            "MOD",
            "JMP",
            "JEQ",
            "JNE",
            "JGR",
            "PIX",
            "FLP",
            "THR",
        ]

    def get_par(self, puzzle: Puzzle) -> Optional[Dict[str, int]]:
        return None

    def format_description(self, puzzle: Puzzle) -> str:
        """Format puzzle description."""
        lines = [puzzle.description]
        lines.append("\nMemory: 256 bytes = 16x16 pixel display")
        lines.append("Addressing: #N (constant), @N (memory), *N (pointer)")
        lines.append("\nGoal: Draw the target pattern using assembly instructions.")

        return "\n".join(lines)

    def execute(
        self,
        code: str,
        puzzle: Puzzle,
        max_steps: int = 10_000,
    ) -> ExecutionResult:
        """Parse and execute BOX-256 code against puzzle."""
        if len(puzzle.target) != 256:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=0,
                runtime_error=(
                    "Puzzle target must contain exactly 256 pixels; "
                    "correctness cannot be verified"
                ),
            )

        if not code.strip():
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=1,
                parse_error="Empty program",
            )

        # Parse the code
        try:
            program = parse(code)
        except ParseError as e:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=1,
                parse_error=str(e),
            )

        if not program.instructions:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=1,
                parse_error="Empty program",
            )

        # Run the emulator
        try:
            emu = Emulator()
            emu.load(program)

            for _ in range(max_steps):
                if emu.halted or not emu.threads:
                    break
                emu.step()

            # Compare display to target
            display = bytes(emu.memory)
            target = puzzle.target
            pixel_accuracy = puzzle.score(display)
            success = puzzle.matches(display)

            # BOX-256 has no HALT instruction and is evaluated at a fixed
            # cycle budget.  An exact target at the budget is therefore a
            # valid completion.  A non-exact active program at the budget is
            # reported as a timeout rather than as an ordinary wrong answer.
            budget_exhausted = (
                emu.cycles >= max_steps and not emu.halted and bool(emu.threads)
            )
            runtime_error = (
                f"Cycle limit exceeded: {max_steps} cycles"
                if budget_exhausted and not success
                else None
            )

            code_size = len(program.instructions) * 4  # 4 bytes per instruction

            metrics = {
                "cycles": emu.cycles,
                "pixel_accuracy": pixel_accuracy,
                "code_size": code_size,
            }

            test_results = [
                TestCaseResult(
                    passed=success,
                    input_values=[],
                    expected_output=list(target),
                    actual_output=list(display),
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
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=1,
                runtime_error=str(e),
                test_results=[
                    TestCaseResult(
                        passed=False,
                        input_values=[],
                        expected_output=list(puzzle.target),
                        actual_output=[],
                        error=str(e),
                    )
                ],
            )
