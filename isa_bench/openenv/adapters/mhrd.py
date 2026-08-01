"""MHRD (Hardware Description Language) adapter."""

from typing import Any, Dict, List, Optional

from .base import ExecutionResult
from ..models import TestCaseResult

from ...games.mhrd.hdl.parser import parse, ParseError
from ...games.mhrd.hdl.simulator import (
    compile_design,
    ComponentLibrary,
    SimulationError,
)
from ...games.mhrd.puzzles.loader import load_puzzles, get_puzzle
from ...games.mhrd.puzzles.schema import Puzzle


class MHRDAdapter:
    """Adapter for MHRD puzzles."""

    def __init__(self):
        self._library = ComponentLibrary()

    @property
    def game_name(self) -> str:
        return "mhrd"

    @property
    def metric_names(self) -> List[str]:
        return ["nand_count"]

    def load_puzzles(self) -> List[Puzzle]:
        """Load all MHRD puzzles."""
        return load_puzzles()

    def get_puzzle(self, puzzle_id: str) -> Puzzle:
        """Get puzzle by ID or index."""
        if puzzle_id.startswith("mhrd_"):
            puzzle_id = puzzle_id.replace("mhrd_", "")
        try:
            return get_puzzle(int(puzzle_id))
        except (ValueError, KeyError):
            return get_puzzle(puzzle_id)

    def get_puzzle_id(self, puzzle: Puzzle) -> str:
        return f"mhrd_{puzzle.name.lower()}"

    def get_puzzle_name(self, puzzle: Puzzle) -> str:
        return puzzle.name

    def get_commands(self, puzzle: Puzzle) -> List[str]:
        return puzzle.available_components

    def get_par(self, puzzle: Puzzle) -> Optional[Dict[str, int]]:
        return None

    def format_description(self, puzzle: Puzzle) -> str:
        """Format puzzle description."""
        lines = [puzzle.description]

        # Show inputs/outputs
        inputs_str = ", ".join(
            f"{name}[{width}]" if width > 1 else name for name, width in puzzle.inputs
        )
        outputs_str = ", ".join(
            f"{name}[{width}]" if width > 1 else name for name, width in puzzle.outputs
        )
        lines.append(f"\nInputs: {inputs_str}")
        lines.append(f"Outputs: {outputs_str}")
        lines.append(f"\nAvailable parts: {', '.join(puzzle.available_components)}")

        # Show truth table example
        if puzzle.test_cases:
            tc = puzzle.test_cases[0]
            lines.append(f"\nExample: inputs={tc.inputs} -> outputs={tc.outputs}")

        return "\n".join(lines)

    def execute(
        self,
        code: str,
        puzzle: Puzzle,
        max_steps: int = 100_000,
    ) -> ExecutionResult:
        """Parse and execute MHRD HDL code against puzzle."""
        if not puzzle.test_cases:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=0,
                runtime_error="Puzzle has no test cases; correctness cannot be verified",
            )

        # Parse the HDL
        try:
            design = parse(code)
        except ParseError as e:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error=str(e),
            )

        # A submission must implement the puzzle's complete interface.  The
        # simulator supplies default-low values for missing pins, so accepting
        # a partial or additional interface here would make correctness depend
        # on implicit simulator defaults rather than on the submitted design.
        expected_inputs = dict(puzzle.inputs)
        expected_outputs = dict(puzzle.outputs)
        actual_inputs = {pin.name: pin.width for pin in design.inputs}
        actual_outputs = {pin.name: pin.width for pin in design.outputs}
        if (
            len(actual_inputs) != len(design.inputs)
            or actual_inputs != expected_inputs
            or len(actual_outputs) != len(design.outputs)
            or actual_outputs != expected_outputs
        ):
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error=(
                    "Design interface does not match puzzle interface: "
                    f"expected inputs {expected_inputs} and outputs {expected_outputs}"
                ),
            )

        part_names = [part.instance for part in design.parts]
        if len(set(part_names)) != len(part_names):
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error="Duplicate part instance name",
            )

        unavailable = sorted(
            {
                part.component
                for part in design.parts
                if part.component not in puzzle.available_components
            }
        )
        if unavailable:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error=f"Unavailable component(s): {', '.join(unavailable)}",
            )

        # Compile the design
        try:
            circuit = compile_design(design, puzzle.name, self._library)
        except SimulationError as e:
            return ExecutionResult(
                success=False,
                tests_passed=0,
                tests_total=len(puzzle.test_cases),
                parse_error=str(e),
            )

        # Run against each test case
        test_results = []
        tests_passed = 0
        runtime_error = None

        for tc in puzzle.test_cases:
            try:
                # Convert inputs to list[bool] format
                input_values = {}
                for name, val in tc.inputs.items():
                    if isinstance(val, int):
                        input_values[name] = [bool(val)]
                    else:
                        input_values[name] = [bool(v) for v in val]

                # Evaluate
                output_values = circuit.evaluate(input_values)

                # Convert outputs to int for comparison
                actual = {}
                for name, bits in output_values.items():
                    if bits is None:
                        actual[name] = None
                    elif len(bits) == 1:
                        actual[name] = int(bits[0])
                    else:
                        actual[name] = [int(b) for b in bits]

                # Require the complete output mapping to match.  Checking only
                # expected keys would allow undeclared extra outputs to pass.
                passed = actual == tc.outputs

                test_results.append(
                    TestCaseResult(
                        passed=passed,
                        input_values=list(tc.inputs.values()),
                        expected_output=list(tc.outputs.values()),
                        actual_output=[actual.get(name) for name, _ in puzzle.outputs],
                    )
                )
                if passed:
                    tests_passed += 1

            except (
                SimulationError,
                TypeError,
                KeyError,
                AttributeError,
                IndexError,
            ) as e:
                runtime_error = str(e)
                test_results.append(
                    TestCaseResult(
                        passed=False,
                        input_values=list(tc.inputs.values()),
                        expected_output=list(tc.outputs.values()),
                        actual_output=[],
                        error=str(e),
                    )
                )

        success = runtime_error is None and tests_passed == len(puzzle.test_cases)
        metrics = {
            "nand_count": circuit.nand_count,
        }

        return ExecutionResult(
            success=success,
            tests_passed=tests_passed,
            tests_total=len(puzzle.test_cases),
            metrics=metrics,
            test_results=test_results,
            runtime_error=runtime_error,
        )
