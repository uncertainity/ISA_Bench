"""Load BOX-256 puzzles."""

from __future__ import annotations

from .schema import Puzzle


def _hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string to bytes (one hex char per pixel)."""
    return bytes(int(c, 16) for c in hex_str)


def _generate_rectangle_frame() -> bytes:
    """Level 1: Rectangle frame."""
    grid = [[0] * 16 for _ in range(16)]
    for x in range(2, 14):
        grid[2][x] = 1
        grid[13][x] = 1
    for y in range(3, 13):
        grid[y][2] = 1
        grid[y][13] = 1
    return bytes(grid[y][x] for y in range(16) for x in range(16))


def _generate_thick_frame() -> bytes:
    """Level 2: Thick rectangle frame."""
    grid = [[0] * 16 for _ in range(16)]
    for y in range(2, 4):
        for x in range(2, 14):
            grid[y][x] = 0xE
    for y in range(12, 14):
        for x in range(2, 14):
            grid[y][x] = 0xE
    for y in range(4, 12):
        grid[y][2] = 0xE
        grid[y][3] = 0xE
        grid[y][12] = 0xE
        grid[y][13] = 0xE
    return bytes(grid[y][x] for y in range(16) for x in range(16))


def _generate_checkerboard() -> bytes:
    """Level 3: Checkerboard pattern."""
    pixels = []
    for y in range(16):
        for x in range(16):
            pixels.append(2 if (x + y) % 2 == 0 else 3)
    return bytes(pixels)


def _generate_big_checkerboard() -> bytes:
    """Level 4: 2x2 checkerboard pattern."""
    pixels = []
    for y in range(16):
        for x in range(16):
            pixels.append(1 if ((x // 2) + (y // 2)) % 2 == 0 else 0xC)
    return bytes(pixels)


def _generate_squares() -> bytes:
    """Level 5: Four 4x4 squares in corners."""
    grid = [[0] * 16 for _ in range(16)]
    colors = [8, 9, 0xA, 0xB]
    for i in range(4):
        color = colors[i]
        base_x = (i % 2) * 4
        base_y = (i // 2) * 4
        for dy in range(4):
            for dx in range(4):
                if dx == 0 or dx == 3 or dy == 0 or dy == 3:
                    grid[base_y + dy][base_x + dx] = color
    return bytes(grid[y][x] for y in range(16) for x in range(16))


def _generate_triangle() -> bytes:
    """Level 6: Triangle pattern in top-left."""
    grid = [[0] * 16 for _ in range(16)]
    for y in range(8):
        for x in range(8):
            grid[y][x] = 8
    for y in range(8, 12):
        for x in range(4):
            grid[y][x] = 9
    for y in range(12, 14):
        grid[y][0] = 0xA
        grid[y][1] = 0xA
    grid[14][0] = 0xB
    return bytes(grid[y][x] for y in range(16) for x in range(16))


def _generate_diagonals() -> bytes:
    """Level 7: Diagonal stripes."""
    grid = [[1] * 16 for _ in range(16)]

    def diagonal(x_start: int, color: int):
        x = x_start
        for y in range(16):
            if 0 <= x < 16:
                grid[y][x] = color
                grid[15 - y][15 - x] = color
            x -= 1

    diagonal(0, 2)
    diagonal(2, 3)
    diagonal(3, 4)
    diagonal(6, 4)
    diagonal(7, 3)
    diagonal(9, 4)
    diagonal(12, 4)
    diagonal(15, 2)

    return bytes(grid[y][x] for y in range(16) for x in range(16))


def _generate_spiral() -> bytes:
    """Level 8: Spiral pattern."""
    pattern = "3BBB" + "3B333B3BBB" * 25 + "3B"
    return _hex_to_bytes(pattern)


def _generate_sierpinski() -> bytes:
    """Level 9: Sierpinski triangle."""
    rows = [
        "8000000000000000",
        "8800000000000000",
        "8080000000000000",
        "8888000000000000",
        "8000800000000000",
        "8800880000000000",
        "8080808000000000",
        "8888888800000000",
        "8000000080000000",
        "8800000088000000",
        "8080000080800000",
        "8888000088880000",
        "8000800080008000",
        "8800880088008800",
        "8080808080808080",
        "8888888888888888",
    ]
    return _hex_to_bytes("".join(rows))


def _generate_colored_sierpinski() -> bytes:
    """Level 10: Colored Sierpinski triangle."""
    rows = [
        "1000000000000000",
        "1100000000000000",
        "1C10000000000000",
        "1111000000000000",
        "1CCC100000000000",
        "11CC110000000000",
        "1C1C1C1000000000",
        "1111111100000000",
        "1CCCCCCC10000000",
        "11CCCCCC11000000",
        "1C1CCCCC1C100000",
        "1111CCCC11110000",
        "1CCC1CCC1CCC1000",
        "11CC11CC11CC1100",
        "1C1C1C1C1C1C1C10",
        "1111111111111111",
    ]
    return _hex_to_bytes("".join(rows))


PUZZLES = [
    Puzzle(
        id="rectangle_frame",
        name="Rectangle Frame",
        description="Draw a thin rectangle frame",
        target=_generate_rectangle_frame(),
        index=1,
    ),
    Puzzle(
        id="thick_frame",
        name="Thick Frame",
        description="Draw a thick rectangle frame",
        target=_generate_thick_frame(),
        index=2,
    ),
    Puzzle(
        id="checkerboard",
        name="Checkerboard",
        description="Draw a 1x1 checkerboard pattern",
        target=_generate_checkerboard(),
        index=3,
    ),
    Puzzle(
        id="big_checkerboard",
        name="Big Checkerboard",
        description="Draw a 2x2 checkerboard pattern",
        target=_generate_big_checkerboard(),
        index=4,
    ),
    Puzzle(
        id="corner_squares",
        name="Corner Squares",
        description="Draw four hollow squares in corners",
        target=_generate_squares(),
        index=5,
    ),
    Puzzle(
        id="triangle",
        name="Triangle",
        description="Draw a stepped triangle",
        target=_generate_triangle(),
        index=6,
    ),
    Puzzle(
        id="diagonals",
        name="Diagonals",
        description="Draw diagonal stripes",
        target=_generate_diagonals(),
        index=7,
    ),
    Puzzle(
        id="spiral",
        name="Spiral",
        description="Draw a spiral pattern",
        target=_generate_spiral(),
        index=8,
    ),
    Puzzle(
        id="sierpinski",
        name="Sierpinski Triangle",
        description="Draw a Sierpinski triangle",
        target=_generate_sierpinski(),
        index=9,
    ),
    Puzzle(
        id="colored_sierpinski",
        name="Colored Sierpinski",
        description="Draw a colored Sierpinski triangle",
        target=_generate_colored_sierpinski(),
        index=10,
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
