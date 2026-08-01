"""Load MHRD puzzles."""

from __future__ import annotations

from .schema import Puzzle, TestCase


# Generate truth tables for common gates
def _truth_table_1bit(func) -> list[TestCase]:
    """Generate truth table for 1-input 1-output gate."""
    cases = []
    for a in [0, 1]:
        cases.append(TestCase(inputs={"in": a}, outputs={"out": func(a)}))
    return cases


def _truth_table_2bit(func) -> list[TestCase]:
    """Generate truth table for 2-input 1-output gate."""
    cases = []
    for a in [0, 1]:
        for b in [0, 1]:
            cases.append(
                TestCase(inputs={"in1": a, "in2": b}, outputs={"out": func(a, b)})
            )
    return cases


def _truth_table_mux() -> list[TestCase]:
    """Generate truth table for MUX (in1, in2, sel -> out)."""
    cases = []
    for in1 in [0, 1]:
        for in2 in [0, 1]:
            for sel in [0, 1]:
                out = in2 if sel else in1
                cases.append(
                    TestCase(
                        inputs={"in1": in1, "in2": in2, "sel": sel},
                        outputs={"out": out},
                    )
                )
    return cases


def _truth_table_demux() -> list[TestCase]:
    """Generate truth table for DEMUX (in, sel -> out1, out2)."""
    cases = []
    for inp in [0, 1]:
        for sel in [0, 1]:
            out1 = inp if sel == 0 else 0
            out2 = inp if sel == 1 else 0
            cases.append(
                TestCase(
                    inputs={"in": inp, "sel": sel}, outputs={"out1": out1, "out2": out2}
                )
            )
    return cases


def _truth_table_halfadder() -> list[TestCase]:
    """Generate truth table for half adder."""
    cases = []
    for a in [0, 1]:
        for b in [0, 1]:
            s = a ^ b
            c = a & b
            cases.append(
                TestCase(inputs={"a": a, "b": b}, outputs={"sum": s, "carry": c})
            )
    return cases


def _truth_table_fulladder() -> list[TestCase]:
    """Generate truth table for full adder."""
    cases = []
    for a in [0, 1]:
        for b in [0, 1]:
            for cin in [0, 1]:
                total = a + b + cin
                s = total % 2
                cout = total // 2
                cases.append(
                    TestCase(
                        inputs={"a": a, "b": b, "cin": cin},
                        outputs={"sum": s, "cout": cout},
                    )
                )
    return cases


# Define all puzzles
PUZZLES = [
    Puzzle(
        name="NOT",
        description="Invert the input signal.",
        inputs=[("in", 1)],
        outputs=[("out", 1)],
        test_cases=_truth_table_1bit(lambda a: 1 - a),
        available_components=["NAND"],
        index=1,
    ),
    Puzzle(
        name="AND",
        description="Output 1 only when both inputs are 1.",
        inputs=[("in1", 1), ("in2", 1)],
        outputs=[("out", 1)],
        test_cases=_truth_table_2bit(lambda a, b: a & b),
        available_components=["NAND", "NOT"],
        index=2,
    ),
    Puzzle(
        name="OR",
        description="Output 1 when at least one input is 1.",
        inputs=[("in1", 1), ("in2", 1)],
        outputs=[("out", 1)],
        test_cases=_truth_table_2bit(lambda a, b: a | b),
        available_components=["NAND", "NOT", "AND"],
        index=3,
    ),
    Puzzle(
        name="XOR",
        description="Output 1 when inputs are different.",
        inputs=[("in1", 1), ("in2", 1)],
        outputs=[("out", 1)],
        test_cases=_truth_table_2bit(lambda a, b: a ^ b),
        available_components=["NAND", "NOT", "AND", "OR"],
        index=4,
    ),
    Puzzle(
        name="MUX",
        description="Select in1 when sel=0, in2 when sel=1.",
        inputs=[("in1", 1), ("in2", 1), ("sel", 1)],
        outputs=[("out", 1)],
        test_cases=_truth_table_mux(),
        available_components=["NAND", "NOT", "AND", "OR", "XOR"],
        index=5,
    ),
    Puzzle(
        name="DEMUX",
        description="Route input to out1 when sel=0, out2 when sel=1.",
        inputs=[("in", 1), ("sel", 1)],
        outputs=[("out1", 1), ("out2", 1)],
        test_cases=_truth_table_demux(),
        available_components=["NAND", "NOT", "AND", "OR", "XOR", "MUX"],
        index=6,
    ),
    Puzzle(
        name="HALFADDER",
        description="Add two 1-bit numbers, produce sum and carry.",
        inputs=[("a", 1), ("b", 1)],
        outputs=[("sum", 1), ("carry", 1)],
        test_cases=_truth_table_halfadder(),
        available_components=["NAND", "NOT", "AND", "OR", "XOR", "MUX", "DEMUX"],
        index=7,
    ),
    Puzzle(
        name="FULLADDER",
        description="Add two 1-bit numbers with carry in, produce sum and carry out.",
        inputs=[("a", 1), ("b", 1), ("cin", 1)],
        outputs=[("sum", 1), ("cout", 1)],
        test_cases=_truth_table_fulladder(),
        available_components=[
            "NAND",
            "NOT",
            "AND",
            "OR",
            "XOR",
            "MUX",
            "DEMUX",
            "HALFADDER",
        ],
        index=8,
    ),
]

_puzzles_by_name: dict[str, Puzzle] = {p.name: p for p in PUZZLES}
_puzzles_by_index: dict[int, Puzzle] = {p.index: p for p in PUZZLES}


def load_puzzles() -> list[Puzzle]:
    """Load all puzzles."""
    return PUZZLES[:]


def get_puzzle(name_or_index: str | int) -> Puzzle:
    """Get a puzzle by name or index."""
    if isinstance(name_or_index, int):
        if name_or_index not in _puzzles_by_index:
            raise KeyError(f"No puzzle with index {name_or_index}")
        return _puzzles_by_index[name_or_index]
    else:
        name = name_or_index.upper()
        if name not in _puzzles_by_name:
            raise KeyError(f"No puzzle named '{name}'")
        return _puzzles_by_name[name]
