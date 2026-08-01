"""Ensure every shipped example remains a successful submission."""

from pathlib import Path

import pytest

from isa_bench import check_solution


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("game", "puzzle_id", "example_path"),
    [
        ("hrm", "hrm_level_1", "examples/hrm_mail_room.hrm"),
        (
            "sic1",
            "sic1_subleq_instruction_and_output",
            "examples/sic1_subleq_instruction_and_output.sic",
        ),
        (
            "tis100",
            "tis100_signal_amplifier",
            "examples/tis100_signal_amplifier.tis",
        ),
        (
            "box256",
            "box256_checkerboard",
            "examples/box256_checkerboard.box",
        ),
        ("mhrd", "mhrd_not", "examples/mhrd_not.hdl"),
    ],
)
def test_example_solution_passes(game, puzzle_id, example_path):
    code = (REPOSITORY_ROOT / example_path).read_text(encoding="utf-8")

    result = check_solution(game, puzzle_id, code)

    assert result.success, result
