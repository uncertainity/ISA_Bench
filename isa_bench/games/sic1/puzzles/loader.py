"""Load SIC-1 puzzles from puzzles.json."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Puzzle, TestCase

_PUZZLES_FILE = Path(__file__).parent / "puzzles.json"


def load_puzzles() -> list[Puzzle]:
    """Load all puzzles from the JSON file."""
    with open(_PUZZLES_FILE) as f:
        data = json.load(f)

    puzzles = []
    for entry in data:
        test_cases = [
            TestCase(input=tc["input"], output=tc["output"])
            for tc in entry["test_cases"]
        ]
        puzzles.append(
            Puzzle(
                id=entry["id"],
                title=entry["title"],
                index=entry["index"],
                test_cases=test_cases,
            )
        )
    return puzzles


def get_puzzle(id_or_index: str | int) -> Puzzle:
    """Get a puzzle by id string or index number."""
    puzzles = load_puzzles()
    if isinstance(id_or_index, int):
        for p in puzzles:
            if p.index == id_or_index:
                return p
        raise KeyError(f"No puzzle with index {id_or_index}")
    else:
        for p in puzzles:
            if p.id == id_or_index:
                return p
        raise KeyError(f"No puzzle with id '{id_or_index}'")
