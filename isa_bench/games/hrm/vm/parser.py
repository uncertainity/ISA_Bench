"""HRM program parser.

Parses HRM clipboard format into executable instructions.

Format:
    -- HUMAN RESOURCE MACHINE PROGRAM --
    INBOX
    COPYTO   0
    INBOX
    ADD      0
    OUTBOX
    JUMP     0

Labels can be defined with `name:` syntax or referenced by line number.
Indirect addressing uses `[n]` syntax.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

from .errors import ParseError

# Value type: integer or single character
Value = Union[int, str]

# Address type: direct (int) or indirect ([int])
Address = Union[int, list[int]]


@dataclass
class Instruction:
    """A parsed HRM instruction."""

    op: str
    arg: Address | str | None = None


@dataclass
class Program:
    """A parsed HRM program."""

    instructions: list[Instruction]
    labels: dict[str, int]

    def __len__(self) -> int:
        return len(self.instructions)


# Instructions and their argument types
# None = no arg, int = address, str = label
OPS: dict[str, type | None] = {
    "inbox": None,
    "outbox": None,
    "copyfrom": int,
    "copyto": int,
    "add": int,
    "sub": int,
    "bumpup": int,
    "bumpdn": int,
    "jump": str,
    "jumpz": str,
    "jumpn": str,
}

# Regex patterns
COMMENT_RE = re.compile(r"--.*$")
LABEL_DEF_RE = re.compile(r"^([a-zA-Z_]\w*)\s*:\s*$")
INDIRECT_RE = re.compile(r"^\[(\d+)\]$")
WORD_RE = re.compile(r"\S+")


def _parse_line(line: str, lineno: int) -> tuple[str | None, Instruction | None]:
    """Parse a single line, returning (label_def, instruction) or (None, None)."""
    # Strip comments
    line = COMMENT_RE.sub("", line).strip()
    if not line:
        return None, None

    # Check for label definition
    label_match = LABEL_DEF_RE.match(line)
    if label_match:
        return label_match.group(1).lower(), None

    # Parse instruction
    tokens = WORD_RE.findall(line)
    if not tokens:
        return None, None

    op = tokens[0].lower()
    if op not in OPS:
        raise ParseError(f"Unknown instruction: {tokens[0]}", lineno)

    expected_arg = OPS[op]

    if expected_arg is None:
        if len(tokens) > 1:
            raise ParseError(f"{op.upper()} takes no arguments", lineno)
        return None, Instruction(op=op)

    if len(tokens) < 2:
        raise ParseError(f"{op.upper()} requires an argument", lineno)
    if len(tokens) > 2:
        raise ParseError(f"{op.upper()} takes only one argument", lineno)

    arg_str = tokens[1]

    if expected_arg is str:
        # Label reference - keep as string
        return None, Instruction(op=op, arg=arg_str.lower())

    # Address argument (int or indirect)
    indirect_match = INDIRECT_RE.match(arg_str)
    if indirect_match:
        addr = int(indirect_match.group(1))
        return None, Instruction(op=op, arg=[addr])
    elif arg_str.isdigit():
        return None, Instruction(op=op, arg=int(arg_str))
    else:
        raise ParseError(f"Invalid address: {arg_str}", lineno)


def parse(source: str) -> Program:
    """Parse HRM source code into a Program.

    Args:
        source: HRM program text (clipboard format)

    Returns:
        Program with instructions and labels

    Raises:
        ParseError: If the source contains syntax errors
    """
    instructions: list[Instruction] = []
    labels: dict[str, int] = {}
    pending_labels: list[str] = []

    for lineno, line in enumerate(source.splitlines(), start=1):
        label_def, instr = _parse_line(line, lineno)

        if label_def:
            if label_def in labels:
                raise ParseError(f"Duplicate label: {label_def}", lineno)
            pending_labels.append(label_def)

        if instr:
            # Assign any pending labels to this instruction
            for lbl in pending_labels:
                labels[lbl] = len(instructions)
            pending_labels.clear()
            instructions.append(instr)

    # Labels at end of program point past last instruction
    for lbl in pending_labels:
        labels[lbl] = len(instructions)

    # In HRM clipboard format, JUMP targets are often line numbers (0-indexed)
    # Add numeric labels for each instruction position
    for i in range(len(instructions)):
        labels[str(i)] = i

    # Validate all label references exist
    for i, instr in enumerate(instructions):
        if instr.op in ("jump", "jumpz", "jumpn"):
            if isinstance(instr.arg, str) and instr.arg not in labels:
                raise ParseError(f"Undefined label: {instr.arg}", None)

    return Program(instructions=instructions, labels=labels)
