# SPDX-FileCopyrightText: 2019-2024 Jared Krinke
# SPDX-FileCopyrightText: 2026 ISA-Bench authors and contributors
#
# Ported from SIC-1's lib/src/sic1asm.ts and modified for ISA Bench in 2026.
# SPDX-License-Identifier: LGPL-3.0-or-later

"""SIC-1 subleq emulator — port of the Emulator class from sic1asm.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .assembler import AssembledProgram
from .errors import ExecutionError

ADDRESS_MAX = 255
ADDRESS_INPUT = 253
ADDRESS_OUTPUT = 254
ADDRESS_HALT = 255
ADDRESS_INSTRUCTION_MAX = ADDRESS_MAX - 3  # 252


def _unsigned_to_signed(unsigned: int) -> int:
    signed = unsigned & 0x7F
    if unsigned & 0x80:
        signed -= 128
    return signed


@dataclass
class EmulatorResult:
    """Result returned after running the emulator."""

    outputs: list[int]
    cycles_executed: int
    memory_bytes_accessed: int


class Emulator:
    """SIC-1 subleq emulator.

    256-byte memory. One instruction: subleq a b c.
    Reads 3 bytes at IP, computes mem[a] = mem[a] - mem[b],
    branches to c if result <= 0, else advances IP.
    """

    def __init__(
        self,
        program: AssembledProgram,
        read_input: Callable[[], int] | None = None,
        write_output: Callable[[int], None] | None = None,
    ):
        self._read_input = read_input
        self._write_output = write_output

        # Initialize memory
        self._memory = [0] * (ADDRESS_MAX + 1)
        for i, b in enumerate(program.bytes):
            self._memory[i] = b

        self._initial_memory = self._memory[:]
        self._ip = 0
        self._running = True
        self._cycles_executed = 0

        # Track unique memory addresses accessed
        self._memory_accessed: set[int] = set()

    @property
    def cycles_executed(self) -> int:
        return self._cycles_executed

    @property
    def memory_bytes_accessed(self) -> int:
        return len(self._memory_accessed)

    @property
    def is_running(self) -> bool:
        return self._running and 0 <= self._ip <= ADDRESS_INSTRUCTION_MAX

    def _access_memory(self, address: int) -> None:
        self._memory_accessed.add(address)

    def _read_memory(self, address: int) -> int:
        self._access_memory(address)
        return self._memory[address]

    def _write_memory(self, address: int, value: int) -> None:
        self._access_memory(address)
        self._memory[address] = value

    def step(self) -> None:
        """Execute one subleq instruction."""
        if not self.is_running:
            return

        a = self._read_memory(self._ip)
        self._ip += 1
        b = self._read_memory(self._ip)
        self._ip += 1
        c = self._read_memory(self._ip)
        self._ip += 1

        # Read input if needed
        input_val = 0
        if a == ADDRESS_INPUT or b == ADDRESS_INPUT:
            self._access_memory(ADDRESS_INPUT)
            if self._read_input:
                input_val = self._read_input()

        av = input_val if a == ADDRESS_INPUT else self._read_memory(a)
        bv = input_val if b == ADDRESS_INPUT else self._read_memory(b)

        # Subtract (wraps around as unsigned byte)
        result = (av - bv) & 0xFF
        result_signed = _unsigned_to_signed(result)

        # Write result
        if a == ADDRESS_OUTPUT:
            self._access_memory(ADDRESS_OUTPUT)
            if self._write_output:
                self._write_output(result_signed)
        elif a != ADDRESS_INPUT and a != ADDRESS_HALT:
            self._write_memory(a, result)

        # Branch if result <= 0
        if result_signed <= 0:
            self._ip = c

        self._cycles_executed += 1
        self._running = 0 <= self._ip <= ADDRESS_INSTRUCTION_MAX

    def run(self, max_cycles: int = 100_000) -> None:
        """Run until halted or cycle limit reached."""
        while self.is_running:
            if self._cycles_executed >= max_cycles:
                raise ExecutionError(f"Cycle limit exceeded: {max_cycles} cycles")
            self.step()

    def reset(self) -> None:
        """Reset to initial state."""
        self._memory = self._initial_memory[:]
        self._ip = 0
        self._running = True
        self._cycles_executed = 0
        self._memory_accessed = set()


def run_program(
    program: AssembledProgram,
    inputs: list[int],
    expected_output_count: int | None = None,
    max_cycles: int = 100_000,
) -> EmulatorResult:
    """Run a program with given inputs, collect outputs.

    If expected_output_count is set, stops after that many outputs
    (matching the original game's verification behavior — many programs
    loop forever and are driven by the test harness).
    """
    input_iter = iter(inputs)
    outputs: list[int] = []

    def read_input() -> int:
        try:
            return next(input_iter)
        except StopIteration:
            return 0

    emu = Emulator(program, read_input=read_input, write_output=outputs.append)

    while emu.is_running:
        if emu.cycles_executed >= max_cycles:
            raise ExecutionError(f"Cycle limit exceeded: {max_cycles} cycles")
        if expected_output_count is not None and len(outputs) >= expected_output_count:
            break
        emu.step()

    return EmulatorResult(
        outputs=outputs,
        cycles_executed=emu.cycles_executed,
        memory_bytes_accessed=emu.memory_bytes_accessed,
    )
