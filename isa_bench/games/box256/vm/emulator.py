"""BOX-256 emulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import Program, Instruction, Operand, AddressMode, parse
from .errors import ExecutionError


@dataclass
class EmulatorResult:
    """Result from running the emulator."""

    display: bytes  # 256 bytes = 16x16 pixels
    cycles: int
    threads_used: int
    code_size: int  # Bytes used for program
    completed: bool = False


class Emulator:
    """BOX-256 emulator."""

    def __init__(self):
        self.memory = bytearray(256)
        self.threads: list[int] = []  # Thread PCs (active threads)
        self.cycles = 0
        self.program: Program | None = None
        self.halted = False

    def reset(self) -> None:
        """Reset emulator state."""
        self.memory = bytearray(256)
        self.threads = []
        self.cycles = 0
        self.halted = False

    def load(self, program: Program) -> None:
        """Load a program into memory."""
        self.program = program
        self.reset()

        if not program.instructions:
            return

        # Each instruction takes 4 bytes
        # Program loads at address 0
        addr = 0
        for instr in program.instructions:
            if addr + 4 > 256:
                raise ExecutionError("Program too large (max 64 instructions)")

            # Encode instruction as 4 bytes
            # Byte 0: opcode, Bytes 1-3: operands
            self.memory[addr] = self._encode_opcode(instr)
            for i, op in enumerate(instr.operands):
                if i < 3:
                    self.memory[addr + 1 + i] = op.value
            # Fill unused operand slots with 0
            for i in range(len(instr.operands), 3):
                self.memory[addr + 1 + i] = 0

            addr += 4

        # Main thread starts at address 0
        self.threads = [0]

    def _encode_opcode(self, instr: Instruction) -> int:
        """Encode an instruction opcode byte."""
        opcode_map = {
            "MOV": 0x01,
            "ADD": 0x13,
            "SUB": 0x1C,
            "JEQ": 0x25,
            "MUL": 0x2E,
            "DIV": 0x37,
            "JMP": 0x40,
            "JGR": 0x43,
            "PIX": 0x4C,
            "FLP": 0x55,
            "THR": 0x5E,
            "MOD": 0x60,
            "JNE": 0x69,
        }
        base = opcode_map.get(instr.opcode, 0)

        # Adjust for addressing modes
        offset = 0
        for op in instr.operands:
            offset *= 3
            if op.mode == AddressMode.CONSTANT:
                offset += 0
            elif op.mode == AddressMode.MEMORY:
                offset += 1
            else:  # POINTER
                offset += 2

        return (base + offset) & 0xFF

    def get_display(self) -> bytes:
        """Get the 16x16 pixel display as bytes."""
        return bytes(self.memory)

    def get_pixel(self, x: int, y: int) -> int:
        """Get pixel color at (x, y)."""
        if 0 <= x < 16 and 0 <= y < 16:
            return self.memory[y * 16 + x] & 0x0F
        return 0

    def set_pixel(self, x: int, y: int, color: int) -> None:
        """Set pixel color at (x, y)."""
        if 0 <= x < 16 and 0 <= y < 16:
            self.memory[y * 16 + x] = color & 0x0F

    def _get_value(self, operand: Operand) -> int:
        """Get the value of an operand."""
        if operand.mode == AddressMode.CONSTANT:
            return operand.value
        elif operand.mode == AddressMode.MEMORY:
            return self.memory[operand.value]
        else:  # POINTER
            addr = self.memory[operand.value]
            return self.memory[addr]

    def _set_value(self, operand: Operand, value: int) -> None:
        """Set the value at an operand's address."""
        value = value % 256
        if value < 0:
            value = 256 + value

        if operand.mode == AddressMode.MEMORY:
            self.memory[operand.value] = value
        elif operand.mode == AddressMode.POINTER:
            addr = self.memory[operand.value]
            self.memory[addr] = value

    def _get_address(self, operand: Operand) -> int:
        """Get the address referenced by an operand."""
        if operand.mode == AddressMode.MEMORY:
            return operand.value
        elif operand.mode == AddressMode.POINTER:
            return self.memory[operand.value]
        return operand.value

    def step(self) -> bool:
        """Execute one cycle (all threads). Returns False if halted."""
        if self.halted or not self.threads:
            return False

        new_threads: list[int] = []

        for pc in self.threads:
            # Decode instruction from memory
            instr_index = pc // 4
            if self.program is None or instr_index >= len(self.program.instructions):
                continue

            instr = self.program.instructions[instr_index]
            result = self._execute(instr)

            # Calculate next PC
            next_pc = pc + 4  # Default: next instruction

            if result:
                if "jump_offset" in result:
                    next_pc = pc + result["jump_offset"] * 4
                elif "jump_to" in result:
                    next_pc = result["jump_to"]
                if "new_thread" in result:
                    new_threads.append(result["new_thread"])

            # Sequential execution wraps to instruction 0 after the final
            # decoded instruction, as specified by BOX-256.  Explicit jumps
            # to addresses outside the decoded program remain invalid and are
            # discarded on the next cycle.
            program_size = len(self.program.instructions) * 4
            if next_pc == program_size:
                next_pc = 0
            if next_pc >= 256:
                next_pc = 0
            if next_pc < 0:
                next_pc = 0

            new_threads.append(next_pc)

        self.threads = new_threads
        self.cycles += 1

        return len(self.threads) > 0

    def _execute(self, instr: Instruction) -> dict | None:
        """Execute a single instruction. Returns control flow info."""
        ops = instr.operands

        if instr.opcode == "MOV":
            src_val = self._get_value(ops[0])
            dst_addr = self._get_address(ops[1])
            count = self._get_value(ops[2]) if len(ops) > 2 else 1

            if ops[0].mode == AddressMode.CONSTANT:
                for i in range(count):
                    self.memory[(dst_addr + i) % 256] = src_val
            else:
                src_addr = self._get_address(ops[0])
                for i in range(count):
                    self.memory[(dst_addr + i) % 256] = self.memory[
                        (src_addr + i) % 256
                    ]

        elif instr.opcode == "ADD":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            self._set_value(ops[2], (a + b) % 256)

        elif instr.opcode == "SUB":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            self._set_value(ops[2], (a - b) % 256)

        elif instr.opcode == "MUL":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            self._set_value(ops[2], (a * b) % 256)

        elif instr.opcode == "DIV":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            result = 255 if b == 0 else a // b
            self._set_value(ops[2], result)

        elif instr.opcode == "MOD":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            result = 255 if b == 0 else a % b
            self._set_value(ops[2], result)

        elif instr.opcode == "JMP":
            if ops[0].mode == AddressMode.CONSTANT:
                return {"jump_offset": ops[0].value}
            else:
                return {"jump_to": self._get_value(ops[0])}

        elif instr.opcode == "JEQ":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            if a == b:
                if ops[2].mode == AddressMode.CONSTANT:
                    return {"jump_offset": ops[2].value}
                else:
                    return {"jump_to": self._get_value(ops[2])}

        elif instr.opcode == "JNE":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            if a != b:
                if ops[2].mode == AddressMode.CONSTANT:
                    return {"jump_offset": ops[2].value}
                else:
                    return {"jump_to": self._get_value(ops[2])}

        elif instr.opcode == "JGR":
            a = self._get_value(ops[0])
            b = self._get_value(ops[1])
            if a > b:
                if ops[2].mode == AddressMode.CONSTANT:
                    return {"jump_offset": ops[2].value}
                else:
                    return {"jump_to": self._get_value(ops[2])}

        elif instr.opcode == "PIX":
            addr = self._get_value(ops[0])
            color = self._get_value(ops[1]) & 0x0F
            x = addr % 16
            y = addr // 16
            self.set_pixel(x, y, color)

        elif instr.opcode == "FLP":
            addr_a = self._get_address(ops[0])
            addr_b = self._get_address(ops[1])
            val_a = self.memory[addr_a]
            val_b = self.memory[addr_b]
            self.memory[addr_a] = val_b
            self.memory[addr_b] = val_a

        elif instr.opcode == "THR":
            addr = self._get_address(ops[0])
            return {"new_thread": addr}

        return None

    def run(self, max_cycles: int = 10000) -> EmulatorResult:
        """Run until completion or cycle limit."""
        while self.cycles < max_cycles and self.step():
            pass

        code_size = len(self.program.instructions) * 4 if self.program else 0

        return EmulatorResult(
            display=self.get_display(),
            cycles=self.cycles,
            threads_used=max(1, len(self.threads)),
            code_size=code_size,
            completed=self.cycles < max_cycles,
        )


def run_program(
    source: str,
    target: bytes | None = None,
    max_cycles: int = 10000,
) -> EmulatorResult:
    """Parse and run a BOX-256 program.

    Args:
        source: BOX-256 assembly source
        target: Optional target display for comparison
        max_cycles: Maximum cycles before timeout

    Returns:
        EmulatorResult with display and stats
    """
    program = parse(source)
    emu = Emulator()
    emu.load(program)
    return emu.run(max_cycles)
