"""Load TIS-100 puzzles."""

from __future__ import annotations

from .schema import Puzzle, Stream


# Define puzzles based on common TIS-100 challenges
PUZZLES = [
    Puzzle(
        id="signal_amplifier",
        name="Signal Amplifier",
        description="Read values from IN.A, double them, and write to OUT.A",
        inputs=[Stream(column=0, values=[5, 10, -3, 7, 0, 15, -8])],
        outputs=[Stream(column=0, values=[10, 20, -6, 14, 0, 30, -16])],
        index=1,
    ),
    Puzzle(
        id="differential_converter",
        name="Differential Converter",
        description="Read values from IN.A and IN.B, compute A-B and B-A, write to OUT.A and OUT.B",
        inputs=[
            Stream(column=0, values=[5, 10, 3]),
            Stream(column=1, values=[2, 7, 8]),
        ],
        outputs=[
            Stream(column=0, values=[3, 3, -5]),  # A - B
            Stream(column=1, values=[-3, -3, 5]),  # B - A
        ],
        index=2,
    ),
    Puzzle(
        id="signal_comparator",
        name="Signal Comparator",
        description="Read from IN.A. Output 1 to OUT.G if >0, 1 to OUT.L if <0, 1 to OUT.E if =0",
        inputs=[Stream(column=1, values=[5, -3, 0, 10, -7, 0])],
        outputs=[
            Stream(column=0, values=[1, 0, 0, 1, 0, 0]),  # Greater
            Stream(column=2, values=[0, 0, 1, 0, 0, 1]),  # Equal
            Stream(column=3, values=[0, 1, 0, 0, 1, 0]),  # Less
        ],
        index=3,
    ),
    Puzzle(
        id="sequence_counter",
        name="Sequence Counter",
        description="Read value N from IN.A, output 1, 2, 3, ..., N to OUT.A",
        inputs=[Stream(column=0, values=[3, 2, 4])],
        outputs=[Stream(column=0, values=[1, 2, 3, 1, 2, 1, 2, 3, 4])],
        index=4,
    ),
    Puzzle(
        id="signal_edge_detector",
        name="Signal Edge Detector",
        description="Read IN.A. Output 1 when value increases, -1 when decreases, 0 otherwise",
        inputs=[Stream(column=0, values=[0, 5, 5, 3, 10, 10, 2])],
        outputs=[Stream(column=0, values=[1, 0, -1, 1, 0, -1])],
        index=5,
    ),
    Puzzle(
        id="sequence_reverser",
        name="Sequence Reverser",
        description="Read two values, output them in reverse order",
        inputs=[Stream(column=0, values=[1, 2, 3, 4, 5, 6])],
        outputs=[Stream(column=0, values=[2, 1, 4, 3, 6, 5])],
        index=6,
    ),
    Puzzle(
        id="signal_multiplier",
        name="Signal Multiplier",
        description="Read A and B, output A*B (using repeated addition)",
        inputs=[
            Stream(column=0, values=[3, 5, 2]),
            Stream(column=1, values=[4, 2, 7]),
        ],
        outputs=[Stream(column=0, values=[12, 10, 14])],
        index=7,
    ),
]

_puzzles_by_id: dict[str, Puzzle] = {p.id: p for p in PUZZLES}
_puzzles_by_index: dict[int, Puzzle] = {p.index: p for p in PUZZLES}


def load_puzzles() -> list[Puzzle]:
    """Load all puzzles."""
    return PUZZLES[:]


def get_puzzle(id_or_index: str | int) -> Puzzle:
    """Get a puzzle by id or index."""
    if isinstance(id_or_index, int):
        if id_or_index not in _puzzles_by_index:
            raise KeyError(f"No puzzle with index {id_or_index}")
        return _puzzles_by_index[id_or_index]
    else:
        if id_or_index not in _puzzles_by_id:
            raise KeyError(f"No puzzle with id '{id_or_index}'")
        return _puzzles_by_id[id_or_index]
