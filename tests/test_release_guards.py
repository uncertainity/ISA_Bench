"""Compact conformance guards for release-critical evaluator behavior."""

from isa_bench.games.box256.vm.emulator import Emulator
from isa_bench.games.box256.vm.parser import parse as parse_box
from isa_bench.openenv.adapters import get_adapter


def test_known_good_sic1_solution():
    adapter = get_adapter("sic1")
    result = adapter.execute(
        "subleq @OUT, @IN", adapter.get_puzzle("0"), max_steps=1_000
    )
    assert result.success
    assert result.tests_passed == result.tests_total == 1


def test_known_good_tis100_solution():
    adapter = get_adapter("tis100")
    code = """\
@0
MOV UP, ACC
ADD ACC
MOV ACC, DOWN
@4
MOV UP, DOWN
@8
MOV UP, DOWN
"""
    result = adapter.execute(
        code, adapter.get_puzzle("signal_amplifier"), max_steps=1_000
    )
    assert result.success


def test_known_good_box256_solution_at_fixed_budget():
    adapter = get_adapter("box256")
    lines = []
    for y in range(2):
        for x in range(16):
            color = 2 if (x + y) % 2 == 0 else 3
            lines.append(f"MOV #{color} @{y * 16 + x}")
    for y in range(2, 16):
        lines.append(f"MOV @{(y % 2) * 16} @{y * 16} #16")

    result = adapter.execute(
        "\n".join(lines),
        adapter.get_puzzle("checkerboard"),
        max_steps=1_000,
    )
    assert result.success
    assert result.metrics["pixel_accuracy"] == 1.0


def test_tis100_unfinished_run_is_a_timeout():
    adapter = get_adapter("tis100")
    result = adapter.execute(
        "@0\nNOP",
        adapter.get_puzzle("signal_amplifier"),
        max_steps=2,
    )
    assert not result.success
    assert result.runtime_error == "Cycle limit exceeded: 2 cycles"


def test_box256_nonmatching_active_run_is_a_timeout():
    adapter = get_adapter("box256")
    result = adapter.execute(
        "JMP #0",
        adapter.get_puzzle("checkerboard"),
        max_steps=3,
    )
    assert not result.success
    assert result.runtime_error == "Cycle limit exceeded: 3 cycles"


def test_box256_sequential_execution_wraps_and_numbers_are_decimal_by_default():
    decimal = parse_box("MOV #10 @10")
    hexadecimal = parse_box("MOV #0x10 @0x10")
    assert decimal.instructions[0].operands[0].value == 10
    assert hexadecimal.instructions[0].operands[0].value == 16

    emulator = Emulator()
    emulator.load(parse_box("MOV #1 @20"))
    for _ in range(3):
        emulator.step()
    assert emulator.cycles == 3
    assert emulator.threads == [0]


def test_zero_test_sic1_puzzles_are_not_listed_and_fail_closed_when_requested():
    adapter = get_adapter("sic1")
    listed_ids = {adapter.get_puzzle_id(puzzle) for puzzle in adapter.load_puzzles()}
    assert "sic1_self_hosting" not in listed_ids

    puzzle = adapter.get_puzzle("self_hosting")
    result = adapter.execute("subleq 0, 0", puzzle)
    assert not result.success
    assert result.tests_total == 0
    assert "cannot be verified" in result.runtime_error


def test_mhrd_advertised_component_is_executable():
    adapter = get_adapter("mhrd")
    code = """\
Inputs: in1, in2;
Outputs: out;
Parts: n NAND, inv NOT;
Wires:
  in1 -> n.in1, in2 -> n.in2,
  n.out -> inv.in,
  inv.out -> out;
"""
    result = adapter.execute(code, adapter.get_puzzle("AND"))
    assert result.success
    assert result.metrics["nand_count"] == 2


def test_mhrd_oscillating_circuit_fails_instead_of_returning_partial_state():
    adapter = get_adapter("mhrd")
    code = """\
Inputs: in;
Outputs: out;
Parts: n NAND;
Wires: n.out -> n.in1, n.out -> n.in2, n.out -> out;
"""
    result = adapter.execute(code, adapter.get_puzzle("NOT"))
    assert not result.success
    assert "did not converge" in result.runtime_error
