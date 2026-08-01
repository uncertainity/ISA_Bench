"""Load HRM puzzles from puzzles.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import Puzzle, TestCase, FloorLayout, Challenge, Value

_PUZZLES_FILE = Path(__file__).parent / "puzzles.json"

_puzzles_cache: list[Puzzle] | None = None


def _parse_value(v: Any) -> Value | None:
    """Parse a value from JSON (int or single character string)."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and len(v) == 1:
        return v
    raise ValueError(f"Invalid value: {v!r}")


def _parse_floor(data: dict[str, Any] | None) -> FloorLayout | None:
    """Parse floor layout from JSON."""
    if data is None:
        return None

    columns = data.get("columns", 1)
    rows = data.get("rows", 1)
    raw_tiles = data.get("tiles", [])

    # Tiles can be a list or a dict
    if isinstance(raw_tiles, dict):
        # Dict format: {"4": 0, "5": 1} means tile 4 has value 0, etc.
        total = columns * rows
        tiles: list[Value | None] = [None] * total
        for k, v in raw_tiles.items():
            idx = int(k)
            if 0 <= idx < total:
                tiles[idx] = _parse_value(v)
    else:
        # List format: ["U", "J", "X", ...] in order
        tiles = [_parse_value(t) for t in raw_tiles]

    return FloorLayout(
        columns=columns,
        rows=rows,
        tiles=tiles,
    )


def _parse_test_case(data: dict[str, Any]) -> TestCase:
    """Parse a test case from JSON."""
    return TestCase(
        inbox=[_parse_value(v) for v in data["inbox"]],
        outbox=[_parse_value(v) for v in data["outbox"]],
    )


def _parse_puzzle(data: dict[str, Any]) -> Puzzle:
    """Parse a puzzle from JSON."""
    # Check for cutscene (no gameplay)
    if data.get("cutscene", False):
        return Puzzle(
            number=data["number"],
            name=data["name"],
            instructions="",
            commands=[],
            is_cutscene=True,
        )

    challenge = None
    if "challenge" in data:
        challenge = Challenge(
            size=data["challenge"]["size"],
            speed=data["challenge"]["speed"],
        )

    return Puzzle(
        number=data["number"],
        name=data["name"],
        instructions=data.get("instructions", ""),
        commands=data.get("commands", []),
        test_cases=[_parse_test_case(ex) for ex in data.get("examples", [])],
        floor=_parse_floor(data.get("floor")),
        challenge=challenge,
    )


def load_puzzles() -> list[Puzzle]:
    """Load all puzzles from the JSON file."""
    global _puzzles_cache
    if _puzzles_cache is not None:
        return _puzzles_cache

    with open(_PUZZLES_FILE) as f:
        data = json.load(f)

    _puzzles_cache = [_parse_puzzle(entry) for entry in data]
    return _puzzles_cache


def get_puzzle(number: int) -> Puzzle:
    """Get a puzzle by level number (1-41)."""
    puzzles = load_puzzles()
    for p in puzzles:
        if p.number == number:
            return p
    raise KeyError(f"No puzzle with number {number}")


def get_playable_puzzles() -> list[Puzzle]:
    """Get all puzzles that are not cutscenes."""
    return [p for p in load_puzzles() if not p.is_cutscene]
