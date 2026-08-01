"""TIS-100 program parser.

Parses TIS-100 solution format with @N node markers.

Format:
    @0
    MOV UP, ACC
    ADD ACC
    MOV ACC, DOWN
    @1
    MOV LEFT, RIGHT

Instructions: MOV, ADD, SUB, NEG, SAV, SWP, JMP, JEZ, JNZ, JGZ, JLZ, JRO, NOP
Registers: ACC, NIL
Ports: UP, DOWN, LEFT, RIGHT, ANY, LAST
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto

from .errors import ParseError


class Opcode(Enum):
    NOP = auto()
    MOV = auto()
    SWP = auto()
    SAV = auto()
    ADD = auto()
    SUB = auto()
    NEG = auto()
    JMP = auto()
    JEZ = auto()
    JNZ = auto()
    JGZ = auto()
    JLZ = auto()
    JRO = auto()


# Valid ports and registers
PORTS = {"UP", "DOWN", "LEFT", "RIGHT", "ANY", "LAST"}
REGISTERS = {"ACC", "NIL"}
ALL_SOURCES = PORTS | REGISTERS
ALL_DESTS = PORTS | REGISTERS - {"NIL"}  # Can't write to NIL... wait, you can

# Instruction argument counts
INSTRUCTION_ARGS = {
    "NOP": 0,
    "MOV": 2,
    "SWP": 0,
    "SAV": 0,
    "ADD": 1,
    "SUB": 1,
    "NEG": 0,
    "JMP": 1,
    "JEZ": 1,
    "JNZ": 1,
    "JGZ": 1,
    "JLZ": 1,
    "JRO": 1,
}


@dataclass
class Operand:
    """An instruction operand."""

    value: int | str  # int for literal, str for register/port/label
    is_literal: bool = False

    @classmethod
    def parse(cls, text: str) -> "Operand":
        text = text.strip().upper()
        try:
            return cls(value=int(text), is_literal=True)
        except ValueError:
            return cls(value=text, is_literal=False)


@dataclass
class Instruction:
    """A parsed TIS-100 instruction."""

    opcode: str
    args: list[Operand] = field(default_factory=list)
    line: int = 0


@dataclass
class NodeProgram:
    """Program for a single TIS-100 node."""

    instructions: list[Instruction] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.instructions)


# Regex patterns
COMMENT_RE = re.compile(r"#.*$")
LABEL_RE = re.compile(r"^([A-Za-z_]\w*)\s*:\s*$")
NODE_MARKER_RE = re.compile(r"^@(\d+)\s*$")


def _parse_instruction(line: str, lineno: int) -> Instruction | None:
    """Parse a single instruction line."""
    # Strip comments and whitespace
    line = COMMENT_RE.sub("", line).strip()
    if not line:
        return None

    # Check for label (handled separately)
    if LABEL_RE.match(line):
        return None

    # Split on whitespace and commas
    parts = re.split(r"[,\s]+", line)
    parts = [p for p in parts if p]

    if not parts:
        return None

    opcode = parts[0].upper()
    if opcode not in INSTRUCTION_ARGS:
        raise ParseError(f"Unknown instruction: {parts[0]}", line=lineno)

    expected_args = INSTRUCTION_ARGS[opcode]
    actual_args = len(parts) - 1

    if actual_args != expected_args:
        raise ParseError(
            f"{opcode} expects {expected_args} argument(s), got {actual_args}",
            line=lineno,
        )

    args = [Operand.parse(p) for p in parts[1:]]
    return Instruction(opcode=opcode, args=args, line=lineno)


def parse_node(source: str, node_index: int | None = None) -> NodeProgram:
    """Parse source code for a single node.

    Args:
        source: Node program text
        node_index: Node index for error messages

    Returns:
        NodeProgram with instructions and labels
    """
    program = NodeProgram()
    lines = source.splitlines()

    for lineno, line in enumerate(lines):
        # Strip comments
        line = COMMENT_RE.sub("", line).strip()
        if not line:
            continue

        # Check for label definition
        label_match = LABEL_RE.match(line)
        if label_match:
            label = label_match.group(1).upper()
            if label in program.labels:
                raise ParseError(
                    f"Duplicate label: {label}", node=node_index, line=lineno
                )
            program.labels[label] = len(program.instructions)
            continue

        # Parse instruction
        instr = _parse_instruction(line, lineno)
        if instr:
            program.instructions.append(instr)

    # Validate label references
    for instr in program.instructions:
        if instr.opcode in ("JMP", "JEZ", "JNZ", "JGZ", "JLZ"):
            if instr.args and not instr.args[0].is_literal:
                label = instr.args[0].value
                if label not in program.labels:
                    raise ParseError(
                        f"Undefined label: {label}", node=node_index, line=instr.line
                    )

    return program


def parse(source: str) -> dict[int, NodeProgram]:
    """Parse a TIS-100 solution with @N node markers.

    Args:
        source: Full solution text with @N markers

    Returns:
        Dict mapping node index to NodeProgram
    """
    programs: dict[int, NodeProgram] = {}
    current_node: int | None = None
    current_lines: list[str] = []

    for line in source.splitlines():
        # Check for node marker
        marker_match = NODE_MARKER_RE.match(line.strip())
        if marker_match:
            # Save previous node if any
            if current_node is not None and current_lines:
                node_source = "\n".join(current_lines)
                programs[current_node] = parse_node(node_source, current_node)

            current_node = int(marker_match.group(1))
            current_lines = []
        elif current_node is not None:
            current_lines.append(line)

    # Save last node
    if current_node is not None and current_lines:
        node_source = "\n".join(current_lines)
        programs[current_node] = parse_node(node_source, current_node)

    return programs
