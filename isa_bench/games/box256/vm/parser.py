"""BOX-256 assembly parser."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from .errors import ParseError


class AddressMode(Enum):
    """Addressing mode for operands."""

    CONSTANT = "c"  # Immediate value: 42 or #42
    MEMORY = "m"  # Direct memory: @42
    POINTER = "p"  # Indirect/pointer: *42


@dataclass
class Operand:
    """An instruction operand."""

    mode: AddressMode
    value: int  # 0-255

    def __repr__(self) -> str:
        if self.mode == AddressMode.CONSTANT:
            return f"#{self.value:02X}"
        elif self.mode == AddressMode.MEMORY:
            return f"@{self.value:02X}"
        else:
            return f"*{self.value:02X}"


INSTRUCTIONS = {
    "MOV": {"args": "rwr", "required": 2, "defaults": [1]},
    "ADD": {"args": "rrw", "required": 3},
    "SUB": {"args": "rrw", "required": 3},
    "MUL": {"args": "rrw", "required": 3},
    "DIV": {"args": "rrw", "required": 3},
    "MOD": {"args": "rrw", "required": 3},
    "JMP": {"args": "r", "required": 1},
    "JEQ": {"args": "rrr", "required": 3},
    "JNE": {"args": "rrr", "required": 3},
    "JGR": {"args": "rrr", "required": 3},
    "PIX": {"args": "rr", "required": 2},
    "FLP": {"args": "wwr", "required": 2, "defaults": [1]},
    "THR": {"args": "w", "required": 1},
}


@dataclass
class Instruction:
    """A parsed instruction."""

    opcode: str
    operands: list[Operand] = field(default_factory=list)
    label: str | None = None  # Label for jump targets
    line: int = 0


@dataclass
class Program:
    """A parsed BOX-256 program."""

    instructions: list[Instruction] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.instructions)


def _parse_operand(
    text: str, labels: dict[str, int], allow_label: bool = True
) -> Operand:
    """Parse a single operand."""
    text = text.strip().upper()

    # Label reference (for jumps)
    if allow_label and text in labels:
        return Operand(AddressMode.CONSTANT, labels[text])

    # Pointer mode: *42 or *0x2A
    if text.startswith("*"):
        value = _parse_number(text[1:])
        return Operand(AddressMode.POINTER, value)

    # Memory mode: @42 or @0x2A
    if text.startswith("@"):
        value = _parse_number(text[1:])
        return Operand(AddressMode.MEMORY, value)

    # Constant mode: 42, #42, 0x2A, #0x2A
    if text.startswith("#"):
        text = text[1:]

    # Check if it's an unresolved label (labels must start with letter, not be valid hex)
    if allow_label and re.match(r"^[A-Z_][A-Z0-9_]*$", text):
        # Don't treat valid hex numbers as labels
        if not re.match(r"^[0-9A-F]+$", text):
            raise ParseError(f"Undefined label: {text}")

    value = _parse_number(text)
    return Operand(AddressMode.CONSTANT, value)


def _parse_number(text: str) -> int:
    """Parse a number (decimal by default, hex with 0x prefix)."""
    text = text.strip().upper()
    try:
        if text.startswith("0X"):
            value = int(text, 16)
        else:
            value = int(text)
    except ValueError:
        raise ParseError(f"Invalid number: {text}")

    if value < 0 or value > 255:
        raise ParseError(f"Value out of range (0-255): {value}")

    return value


def parse(source: str) -> Program:
    """Parse BOX-256 assembly source code."""
    lines = source.strip().split("\n")

    # First pass: collect labels
    labels: dict[str, int] = {}
    instruction_index = 0

    for line in lines:
        line = line.split(";")[0].strip()  # Remove comments
        if not line:
            continue

        # Check for label definition
        if ":" in line:
            label_part, rest = line.split(":", 1)
            label = label_part.strip().upper()
            if label in labels:
                raise ParseError(f"Duplicate label: {label}")
            labels[label] = instruction_index
            line = rest.strip()
            if not line:
                continue

        instruction_index += 1

    # Second pass: parse instructions
    instructions: list[Instruction] = []
    instruction_index = 0

    for line_num, line in enumerate(lines, 1):
        line = line.split(";")[0].strip()  # Remove comments
        if not line:
            continue

        current_label = None

        # Check for label definition
        if ":" in line:
            label_part, rest = line.split(":", 1)
            current_label = label_part.strip().upper()
            line = rest.strip()
            if not line:
                continue

        # Parse instruction
        parts = line.replace(",", " ").split()
        if not parts:
            continue

        opcode = parts[0].upper()
        if opcode not in INSTRUCTIONS:
            raise ParseError(f"Unknown instruction: {opcode} (line {line_num})")

        info = INSTRUCTIONS[opcode]
        arg_types = info["args"]
        required = info["required"]
        defaults = info.get("defaults", [])

        operand_texts = parts[1:]

        # Check argument count
        if len(operand_texts) < required:
            raise ParseError(
                f"{opcode} requires at least {required} arguments, "
                f"got {len(operand_texts)} (line {line_num})"
            )

        if len(operand_texts) > len(arg_types):
            raise ParseError(
                f"{opcode} takes at most {len(arg_types)} arguments, "
                f"got {len(operand_texts)} (line {line_num})"
            )

        # Parse operands
        operands: list[Operand] = []
        for i, arg_type in enumerate(arg_types):
            if i < len(operand_texts):
                op = _parse_operand(operand_texts[i], labels)
            elif i - required < len(defaults):
                op = Operand(AddressMode.CONSTANT, defaults[i - required])
            else:
                raise ParseError(
                    f"Missing argument {i+1} for {opcode} (line {line_num})"
                )

            # Validate writable operands
            if arg_type == "w" and op.mode == AddressMode.CONSTANT:
                raise ParseError(
                    f"Argument {i+1} of {opcode} must be writable (@addr or *addr), "
                    f"not a constant (line {line_num})"
                )

            operands.append(op)

        instructions.append(
            Instruction(
                opcode=opcode,
                operands=operands,
                label=current_label,
                line=line_num,
            )
        )
        instruction_index += 1

    return Program(instructions=instructions, labels=labels)
