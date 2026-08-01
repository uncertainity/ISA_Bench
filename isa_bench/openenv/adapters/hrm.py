"""HRM (Human Resource Machine) adapter."""

from typing import Any, Dict, List, Optional

from .base import ExecutionResult
from ..models import TestCaseResult

from ...games.hrm.vm.parser import parse, ParseError
from ...games.hrm.vm.emulator import run_program, ExecutionError
from ...games.hrm.puzzles.loader import load_puzzles, get_puzzle, get_playable_puzzles
from ...games.hrm.puzzles.schema import Puzzle


class HRMAdapter:
    """Adapter for Human Resource Machine puzzles."""

    @property
    def game_name(self) -> str:
        return "hrm"

    @property
    def metric_names(self) -> List[str]:
        return ["steps", "instructions"]

    def load_puzzles(self) -> List[Puzzle]:
        """Load all playable HRM puzzles (excluding cutscenes)."""
        return get_playable_puzzles()

    def get_puzzle(self, puzzle_id: str) -> Puzzle:
        """Get puzzle by ID (format: 'hrm_level_N' or just 'N')."""
        if puzzle_id.startswith("hrm_level_"):
            num = int(puzzle_id.replace("hrm_level_", ""))
        else:
            num = int(puzzle_id)
        return get_puzzle(num)

    def get_puzzle_id(self, puzzle: Puzzle) -> str:
        return f"hrm_level_{puzzle.number}"

    def get_puzzle_name(self, puzzle: Puzzle) -> str:
        return puzzle.name

    def get_commands(self, puzzle: Puzzle) -> List[str]:
        return puzzle.commands

    def get_par(self, puzzle: Puzzle) -> Optional[Dict[str, int]]:
        if puzzle.challenge is None:
            return None
        return {
            "instructions": puzzle.challenge.size,
            "steps": puzzle.challenge.speed,
        }

    def format_description(self, puzzle: Puzzle) -> str:
        """Format puzzle description with instructions and test case examples."""
        lines = [puzzle.instructions]

        if puzzle.floor:
            floor_dict = puzzle.floor.to_dict()
            if floor_dict:
                floor_items = [f"{k}={v}" for k, v in sorted(floor_dict.items())]
                lines.append(f"\nFloor tiles: {', '.join(floor_items)}")

        if puzzle.test_cases:
            tc = puzzle.test_cases[0]
            lines.append(f"\nExample:")
            lines.append(f"  Input: {tc.inbox}")
            lines.append(f"  Expected output: {tc.outbox}")

        return "\n".join(lines)

    def execute(
        self,
        code: str,
        puzzle: Puzzle,
        max_steps: int = 100_000,
    ) -> ExecutionResult:
        """Parse and execute HRM code against puzzle test cases."""
        if not puzzle.test_cases:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=0,
                runtime_error="Puzzle has no test cases; correctness cannot be verified",
            )

        # Parse the code
        try:
            program = parse(code)
        except ParseError as e:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error=str(e),
            )

        # Run against each test case
        test_results = []
        tests_passed = 0
        total_steps = 0
        runtime_error = None

        for tc in puzzle.test_cases:
            floor_dict = puzzle.floor.to_dict() if puzzle.floor else {}

            try:
                result = run_program(
                    program,
                    inbox=list(tc.inbox),
                    floor=floor_dict,
                    expected_output_count=len(tc.outbox),
                    max_steps=max_steps,
                )
                passed = result.outbox == list(tc.outbox)
                total_steps += result.steps_executed

                test_results.append(
                    TestCaseResult(
                        passed=passed,
                        input_values=list(tc.inbox),
                        expected_output=list(tc.outbox),
                        actual_output=list(result.outbox),
                    )
                )
                if passed:
                    tests_passed += 1

            except ExecutionError as e:
                runtime_error = str(e)
                test_results.append(
                    TestCaseResult(
                        passed=False,
                        input_values=list(tc.inbox),
                        expected_output=list(tc.outbox),
                        actual_output=[],
                        error=str(e),
                    )
                )

        success = runtime_error is None and tests_passed == len(puzzle.test_cases)
        metrics = {
            "steps": total_steps,
            "instructions": len(program),
        }

        return ExecutionResult(
            success=success,
            tests_passed=tests_passed,
            tests_total=len(puzzle.test_cases),
            metrics=metrics,
            test_results=test_results,
            runtime_error=runtime_error,
        )
