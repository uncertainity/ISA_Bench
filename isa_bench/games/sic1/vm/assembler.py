# SPDX-FileCopyrightText: 2019-2024 Jared Krinke
# SPDX-FileCopyrightText: 2026 ISA-Bench authors and contributors
#
# Ported from SIC-1's lib/src/sic1asm.ts and modified for ISA Bench in 2026.
# SPDX-License-Identifier: LGPL-3.0-or-later

"""SIC-1 subleq assembler — port of sic1asm.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Union

from .errors import CompilationError

# Constants matching the original
ADDRESS_MAX = 255
ADDRESS_USER_MAX = 252
ADDRESS_INPUT = 253
ADDRESS_OUTPUT = 254
ADDRESS_HALT = 255
VALUE_MIN = -128
VALUE_MAX = 127
SUBLEQ_INSTRUCTION_BYTES = 3


@dataclass
class SourceMapEntry:
    line_number: int
    source: str


@dataclass
class VariableDefinition:
    label: str
    address: int


@dataclass
class AssembledProgram:
    bytes: list[int]
    source_map: dict[int, SourceMapEntry] = field(default_factory=dict)
    variables: list[VariableDefinition] = field(default_factory=list)


# --- Tokenizer ---


class TokenType(Enum):
    LABEL = auto()
    COMMAND = auto()
    NUMBER_LITERAL = auto()
    CHARACTER_LITERAL = auto()
    REFERENCE = auto()
    STRING_LITERAL = auto()
    COMMA = auto()
    WHITESPACE = auto()
    COMMENT = auto()


@dataclass
class Token:
    token_type: TokenType
    raw: str
    groups: dict[str, str] = field(default_factory=dict)


# Regex patterns for tokenizer (order matters — first match wins)
_IDENTIFIER = r"[^\s!@\\();:'\",+\-]+"
_NUMBER = r"[0-9]+"
_PRINTABLE_EXCEPT_APOS_BS = r"[ -&(-[\]-~]"
_PRINTABLE_EXCEPT_QUOTE_BS = r"[ !#-[\]-~]"
_PRINTABLE = r"[ -~]"

_TOKEN_RULES: list[tuple[TokenType, str, list[str], bool]] = [
    # (type, pattern, group_names, discard)
    (TokenType.WHITESPACE, r"\s+", [], False),  # kept for parser to check spacing
    (TokenType.COMMA, r",", [], False),
    (TokenType.COMMAND, r"[.]?[_a-zA-Z][_a-zA-Z0-9]*", [], False),
    (TokenType.NUMBER_LITERAL, rf"-?{_NUMBER}", [], False),
    (
        TokenType.CHARACTER_LITERAL,
        rf"-?'({_PRINTABLE_EXCEPT_APOS_BS}|\\{_PRINTABLE})'",
        ["character"],
        False,
    ),
    (
        TokenType.STRING_LITERAL,
        rf'-?"(({_PRINTABLE_EXCEPT_QUOTE_BS}|\\{_PRINTABLE})*)"',
        ["characters"],
        False,
    ),
    (TokenType.LABEL, rf"@({_IDENTIFIER}):", ["name"], False),
    (
        TokenType.REFERENCE,
        rf"(-?)@({_IDENTIFIER})([+-]{_NUMBER})?",
        ["negation", "name", "offset"],
        False,
    ),
    (TokenType.COMMENT, r";.*$", [], True),  # comments always discarded
]

_COMPILED_RULES = [
    (tt, re.compile("^" + pattern), groups, discard)
    for tt, pattern, groups, discard in _TOKEN_RULES
]


def _tokenize_line(
    line: str, line_number: int | None = None, line_text: str | None = None
) -> list[Token]:
    tokens = []
    remaining = line
    while remaining:
        matched = False
        for tt, regex, group_names, discard in _COMPILED_RULES:
            m = regex.match(remaining)
            if m:
                if not discard:
                    groups = {}
                    for i, name in enumerate(group_names):
                        val = m.group(i + 1)
                        if val is not None:
                            groups[name] = val
                    tokens.append(Token(token_type=tt, raw=m.group(0), groups=groups))
                remaining = remaining[m.end() :]
                matched = True
                break
        if not matched:
            raise CompilationError(
                f'Invalid token: "{remaining}"',
                line_number=line_number,
                line_text=line_text,
            )
    return tokens


# --- Parser types ---


class Command(Enum):
    SUBLEQ = auto()
    DATA = auto()


_COMMAND_MAP = {
    "subleq": Command.SUBLEQ,
    ".data": Command.DATA,
}


@dataclass
class LabelReference:
    label: str
    negated: bool = False
    offset: int = 0


Expression = Union[LabelReference, int]


@dataclass
class LabelDefinition:
    label: str
    offset: int
    inline: bool = False


@dataclass
class ParsedLine:
    label_definitions: list[LabelDefinition]
    command: Command | None = None
    expressions: list[Expression] = field(default_factory=list)


# --- Helpers ---


def _unsigned_to_signed(unsigned: int) -> int:
    signed = unsigned & 0x7F
    if unsigned & 0x80:
        signed -= 128
    return signed


def _signed_to_unsigned(signed: int) -> int:
    return signed & 0xFF


def _parse_escape(
    char: str, line_number: int | None = None, line_text: str | None = None
) -> str:
    if char == "0":
        return "\0"
    elif char == "n":
        return "\n"
    elif char in ("\\", "'", '"'):
        return char
    else:
        raise CompilationError(
            f'Invalid escape code: "\\{char}"',
            line_number=line_number,
            line_text=line_text,
        )


def _parse_character_token(
    token: Token, line_number: int | None = None, line_text: str | None = None
) -> int:
    char_str = token.groups.get("character", "")
    if char_str.startswith("\\"):
        value = ord(_parse_escape(char_str[1], line_number, line_text))
    else:
        value = ord(char_str)
    if token.raw.startswith("-"):
        value = _signed_to_unsigned(-value)
    return value


def _parse_string_token(
    token: Token, line_number: int | None = None, line_text: str | None = None
) -> list[int]:
    chars_str = token.groups.get("characters", "")
    output = []
    i = 0
    while i < len(chars_str):
        if chars_str[i] == "\\":
            i += 1
            output.append(ord(_parse_escape(chars_str[i], line_number, line_text)))
        else:
            output.append(ord(chars_str[i]))
        i += 1
    if token.raw.startswith("-"):
        output = [_signed_to_unsigned(-v) for v in output]
    output.append(0)  # null terminator
    return output


def _parse_reference_token(token: Token) -> LabelReference:
    name = token.groups.get("name", "")
    offset_str = token.groups.get("offset", "")
    negated = token.groups.get("negation", "") == "-"
    offset = int(offset_str) if offset_str else 0
    return LabelReference(label=name, negated=negated, offset=offset)


# --- Assembler ---


class Assembler:
    """Assembles SIC-1 subleq source code into a byte array."""

    @staticmethod
    def assemble(lines: list[str]) -> AssembledProgram:
        """Assemble source lines into an AssembledProgram."""
        labels: dict[str, int] = {
            "MAX": ADDRESS_USER_MAX,
            "IN": ADDRESS_INPUT,
            "OUT": ADDRESS_OUTPUT,
            "HALT": ADDRESS_HALT,
        }
        variables: list[VariableDefinition] = []
        source_map: dict[int, SourceMapEntry] = {}
        address = 0

        # First pass: collect expressions and labels
        all_expressions: list[Expression] = []
        expression_addresses: list[int] = []  # track address for source map

        for line_idx, line in enumerate(lines):
            if not line.strip():
                continue

            line_number = line_idx + 1
            tokens = _tokenize_line(line, line_number=line_number, line_text=line)
            parsed = _parse_line(tokens, line_number=line_number, line_text=line)

            # Register labels
            for ldef in parsed.label_definitions:
                if ldef.label in labels:
                    raise CompilationError(
                        f'Label already defined: "@{ldef.label}"',
                        line_number=line_number,
                        line_text=line,
                    )
                label_addr = address + ldef.offset
                labels[ldef.label] = label_addr

                if ldef.inline or parsed.command == Command.DATA:
                    variables.append(
                        VariableDefinition(label=f"@{ldef.label}", address=label_addr)
                    )

            if parsed.command is None:
                continue

            exprs = parsed.expressions
            start_address = address

            if parsed.command == Command.SUBLEQ:
                for e in exprs:
                    all_expressions.append(e)
                next_address = address + SUBLEQ_INSTRUCTION_BYTES
                if len(exprs) < 3:
                    all_expressions.append(next_address)  # auto-fill 3rd arg
                address = next_address
            elif parsed.command == Command.DATA:
                for e in exprs:
                    if isinstance(e, list):
                        all_expressions.extend(e)
                        address += len(e)
                    else:
                        all_expressions.append(e)
                        address += 1

            source_map[start_address] = SourceMapEntry(
                line_number=line_idx, source=line
            )

        if address - 1 > ADDRESS_USER_MAX:
            raise CompilationError(
                f"Program too large: {address} bytes (max {ADDRESS_USER_MAX + 1})"
            )

        # Second pass: resolve label references
        result_bytes = []
        for expr in all_expressions:
            if isinstance(expr, LabelReference):
                if expr.label not in labels:
                    raise CompilationError(f'Undefined reference: "@{expr.label}"')
                value = labels[expr.label]
                if expr.negated:
                    value = _signed_to_unsigned(-value)
                value += expr.offset
                if value < 0 or value > ADDRESS_MAX:
                    raise CompilationError(
                        f'Address "@{expr.label}+{expr.offset}" ({value}) out of range [0, {ADDRESS_MAX}]'
                    )
                result_bytes.append(value)
            else:
                result_bytes.append(expr)

        return AssembledProgram(
            bytes=result_bytes,
            source_map=source_map,
            variables=variables,
        )

    @staticmethod
    def assemble_source(source: str) -> AssembledProgram:
        """Convenience: assemble a multi-line source string."""
        return Assembler.assemble(source.split("\n"))


def _parse_line(
    tokens: list[Token], line_number: int | None = None, line_text: str | None = None
) -> ParsedLine:
    """Parse a list of tokens into a ParsedLine."""
    label_definitions: list[LabelDefinition] = []
    expressions: list[Expression] = []
    idx = 0
    offset = 0

    def skip_ws():
        nonlocal idx
        while idx < len(tokens) and tokens[idx].token_type == TokenType.WHITESPACE:
            idx += 1

    def collect_labels(inline: bool = False):
        nonlocal idx
        while idx < len(tokens):
            tt = tokens[idx].token_type
            if tt == TokenType.LABEL:
                label_definitions.append(
                    LabelDefinition(
                        label=tokens[idx].groups["name"],
                        offset=offset,
                        inline=inline,
                    )
                )
                idx += 1
            elif tt == TokenType.WHITESPACE:
                idx += 1
            else:
                break

    # Collect leading labels
    skip_ws()
    collect_labels()

    # Check for command
    skip_ws()
    if idx >= len(tokens):
        return ParsedLine(label_definitions=label_definitions)

    command_name = tokens[idx].raw
    command = _COMMAND_MAP.get(command_name)
    if command is None:
        raise CompilationError(
            f'Unknown command: "{command_name}" (valid: "subleq", ".data")',
            line_number=line_number,
            line_text=line_text,
        )
    idx += 1

    # Parse arguments
    arg_count = 0
    while idx < len(tokens):
        # Require whitespace or comma between args
        if arg_count == 0:
            if idx < len(tokens) and tokens[idx].token_type != TokenType.WHITESPACE:
                raise CompilationError(
                    f'Whitespace required after "{command_name}"',
                    line_number=line_number,
                    line_text=line_text,
                )
        else:
            skip_ws()
            if idx < len(tokens) and tokens[idx].token_type == TokenType.COMMA:
                idx += 1

        skip_ws()
        collect_labels(inline=True)

        if idx >= len(tokens):
            break

        tok = tokens[idx]
        if command == Command.SUBLEQ:
            # Address expression: number literal or reference
            if tok.token_type == TokenType.NUMBER_LITERAL:
                val = int(tok.raw)
                if val < 0 or val > ADDRESS_MAX:
                    raise CompilationError(
                        f"Address {val} out of range [0, {ADDRESS_MAX}]",
                        line_number=line_number,
                        line_text=line_text,
                    )
                expressions.append(val)
                offset += 1
            elif tok.token_type == TokenType.REFERENCE:
                expressions.append(_parse_reference_token(tok))
                offset += 1
            else:
                raise CompilationError(
                    f'Expected address or reference, got: "{tok.raw}"',
                    line_number=line_number,
                    line_text=line_text,
                )
        elif command == Command.DATA:
            # Value expression: number, character, string, or reference
            if tok.token_type == TokenType.NUMBER_LITERAL:
                val = int(tok.raw)
                if val < VALUE_MIN or val > VALUE_MAX:
                    raise CompilationError(
                        f"Value {val} out of range [{VALUE_MIN}, {VALUE_MAX}]",
                        line_number=line_number,
                        line_text=line_text,
                    )
                expressions.append(_signed_to_unsigned(val))
                offset += 1
            elif tok.token_type == TokenType.CHARACTER_LITERAL:
                expressions.append(_parse_character_token(tok, line_number, line_text))
                offset += 1
            elif tok.token_type == TokenType.STRING_LITERAL:
                str_bytes = _parse_string_token(tok, line_number, line_text)
                expressions.extend(str_bytes)
                offset += len(str_bytes)
            elif tok.token_type == TokenType.REFERENCE:
                expressions.append(_parse_reference_token(tok))
                offset += 1
            else:
                raise CompilationError(
                    f'Expected value, character, string, or reference, got: "{tok.raw}"',
                    line_number=line_number,
                    line_text=line_text,
                )

        arg_count += 1
        idx += 1

    # Validate argument counts
    if command == Command.SUBLEQ:
        if arg_count < 2 or arg_count > 3:
            raise CompilationError(
                f"subleq requires 2 or 3 arguments, got {arg_count}",
                line_number=line_number,
                line_text=line_text,
            )
    elif command == Command.DATA:
        if arg_count < 1:
            raise CompilationError(
                ".data requires at least 1 argument",
                line_number=line_number,
                line_text=line_text,
            )

    return ParsedLine(
        label_definitions=label_definitions,
        command=command,
        expressions=expressions,
    )
