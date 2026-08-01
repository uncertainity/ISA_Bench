"""MHRD HDL parser.

Parses HDL designs with 4 sections: Inputs, Outputs, Parts, Wires.

Example:
    Inputs: a, b;
    Outputs: out;
    Parts: n1 NAND, n2 NAND;
    Wires: a -> n1.in1, b -> n1.in2, n1.out -> out;
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import ParseError


@dataclass
class Pin:
    """A pin declaration (single or bus)."""

    name: str
    width: int = 1  # 1 for single pin, >1 for bus

    def __str__(self) -> str:
        if self.width == 1:
            return self.name
        return f"{self.name}[{self.width}]"


@dataclass
class Part:
    """A component instance."""

    instance: str  # Instance name (e.g., "n1")
    component: str  # Component type (e.g., "NAND")

    def __str__(self) -> str:
        return f"{self.instance} {self.component}"


@dataclass
class WireEnd:
    """One end of a wire connection."""

    name: str  # Pin name or "part.pin"
    index: int | None = None  # Single index [n]
    range_start: int | None = None  # Range [start:end]
    range_end: int | None = None
    is_constant: bool = False  # True for 0 or 1

    @property
    def is_indexed(self) -> bool:
        return self.index is not None

    @property
    def is_range(self) -> bool:
        return self.range_start is not None

    def __str__(self) -> str:
        if self.is_constant:
            return self.name
        if self.is_range:
            return f"{self.name}[{self.range_start}:{self.range_end}]"
        if self.is_indexed:
            return f"{self.name}[{self.index}]"
        return self.name


@dataclass
class Wire:
    """A wire connection from source to destination."""

    source: WireEnd
    dest: WireEnd

    def __str__(self) -> str:
        return f"{self.source} -> {self.dest}"


@dataclass
class HDLDesign:
    """A parsed HDL design."""

    inputs: list[Pin] = field(default_factory=list)
    outputs: list[Pin] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)


# Regex patterns
COMMENT_RE = re.compile(r"//.*$", re.MULTILINE)
SECTION_RE = re.compile(
    r"(Inputs|Outputs|Parts|Wires)\s*:\s*(.*?)\s*;", re.IGNORECASE | re.DOTALL
)
PIN_RE = re.compile(r"([a-zA-Z]\w*)(?:\[(\d+)\])?")
PART_RE = re.compile(r"([a-zA-Z]\w*)\s+([A-Z][A-Z0-9]*)")
WIRE_RE = re.compile(r"(.+?)\s*->\s*(.+)")
WIRE_END_RE = re.compile(r"([a-zA-Z]\w*(?:\.[a-zA-Z]\w*)?)(?:\[(\d+)(?::(\d+))?\])?")


def _strip_comments(source: str) -> str:
    """Remove // comments from source."""
    return COMMENT_RE.sub("", source)


def _parse_pins(content: str) -> list[Pin]:
    """Parse pin declarations like 'a, b, bus[8]'."""
    pins = []
    for item in content.split(","):
        item = item.strip()
        if not item:
            continue
        match = PIN_RE.fullmatch(item)
        if not match:
            raise ParseError(f"Invalid pin declaration: {item}")
        name, width = match.groups()
        pins.append(Pin(name=name, width=int(width) if width else 1))
    return pins


def _parse_parts(content: str) -> list[Part]:
    """Parse part declarations like 'n1 NAND, n2 NAND'."""
    parts = []
    for item in content.split(","):
        item = item.strip()
        if not item:
            continue
        match = PART_RE.fullmatch(item)
        if not match:
            raise ParseError(f"Invalid part declaration: {item}")
        instance, component = match.groups()
        parts.append(Part(instance=instance, component=component))
    return parts


def _parse_wire_end(text: str) -> WireEnd:
    """Parse a wire endpoint like 'a', 'n1.out', 'bus[3]', 'bus[1:8]'."""
    text = text.strip()

    # Check for constants
    if text == "0" or text == "1":
        return WireEnd(name=text, is_constant=True)

    match = WIRE_END_RE.fullmatch(text)
    if not match:
        raise ParseError(f"Invalid wire endpoint: {text}")

    name, idx, range_end = match.groups()

    if range_end is not None:
        # Range: bus[1:8]
        return WireEnd(name=name, range_start=int(idx), range_end=int(range_end))
    elif idx is not None:
        # Single index: bus[3]
        return WireEnd(name=name, index=int(idx))
    else:
        # Simple name: a, n1.out
        return WireEnd(name=name)


def _parse_wires(content: str) -> list[Wire]:
    """Parse wire declarations like 'a -> n1.in1, n1.out -> out'."""
    wires = []
    for item in content.split(","):
        item = item.strip()
        if not item:
            continue
        match = WIRE_RE.fullmatch(item)
        if not match:
            raise ParseError(f"Invalid wire declaration: {item}")
        src_text, dst_text = match.groups()
        source = _parse_wire_end(src_text)
        dest = _parse_wire_end(dst_text)
        wires.append(Wire(source=source, dest=dest))
    return wires


def parse(source: str) -> HDLDesign:
    """Parse HDL source code into an HDLDesign.

    Args:
        source: HDL design text

    Returns:
        HDLDesign with inputs, outputs, parts, and wires

    Raises:
        ParseError: If the source contains syntax errors
    """
    # Strip comments
    source = _strip_comments(source)

    design = HDLDesign()

    # Find and parse each section
    for match in SECTION_RE.finditer(source):
        section_name = match.group(1).lower()
        content = match.group(2).strip()

        if section_name == "inputs":
            design.inputs = _parse_pins(content)
        elif section_name == "outputs":
            design.outputs = _parse_pins(content)
        elif section_name == "parts":
            design.parts = _parse_parts(content)
        elif section_name == "wires":
            design.wires = _parse_wires(content)

    return design
