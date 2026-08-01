"""TIS-100 T21 Basic Execution Node.

Each node has:
- ACC: Accumulator register
- BAK: Backup register (only accessible via SAV/SWP)
- Program counter
- Port interface for communication with neighbors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from .parser import NodeProgram, Operand
from .errors import ExecutionError

if TYPE_CHECKING:
    from .emulator import Grid

# Value bounds
MIN_VALUE = -999
MAX_VALUE = 999


class Port(Enum):
    """Port directions."""

    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    ANY = auto()
    LAST = auto()
    NIL = auto()


class NodeState(Enum):
    """Node execution state."""

    IDLE = auto()
    RUN = auto()
    READ = auto()  # Blocked waiting to read
    WRITE = auto()  # Blocked waiting to write


@dataclass
class PortRequest:
    """A pending port read or write request."""

    port: Port
    value: int | None = None  # None for read, value for write
    is_write: bool = False


def _clamp(value: int) -> int:
    """Clamp value to valid range."""
    return max(MIN_VALUE, min(MAX_VALUE, value))


class Node:
    """TIS-100 T21 Basic Execution Node."""

    # ANY port priority order
    ANY_PRIORITY = [Port.UP, Port.LEFT, Port.RIGHT, Port.DOWN]

    def __init__(self, index: int, program: NodeProgram | None = None):
        self.index = index
        self.program = program or NodeProgram()

        # Registers
        self.acc = 0
        self.bak = 0

        # Program counter
        self.pc = 0

        # Last port used by ANY
        self.last_port: Port | None = None

        # Current state
        self.state = NodeState.IDLE if not self.program.instructions else NodeState.RUN

        # Pending port operation
        self.pending: PortRequest | None = None

        # Neighbors (set by Grid)
        self.neighbors: dict[Port, Node | None] = {
            Port.UP: None,
            Port.DOWN: None,
            Port.LEFT: None,
            Port.RIGHT: None,
        }

    @property
    def is_blocked(self) -> bool:
        return self.state in (NodeState.READ, NodeState.WRITE)

    @property
    def is_empty(self) -> bool:
        return len(self.program.instructions) == 0

    def reset(self) -> None:
        """Reset node to initial state."""
        self.acc = 0
        self.bak = 0
        self.pc = 0
        self.last_port = None
        self.state = NodeState.IDLE if self.is_empty else NodeState.RUN
        self.pending = None

    def _resolve_source(self, operand: Operand) -> int | Port:
        """Resolve a source operand to a value or port."""
        if operand.is_literal:
            return operand.value

        name = operand.value
        if name == "ACC":
            return self.acc
        elif name == "NIL":
            return 0
        elif name in ("UP", "DOWN", "LEFT", "RIGHT", "ANY", "LAST"):
            return Port[name]
        else:
            raise ExecutionError(f"Invalid source: {name}")

    def _resolve_dest(self, operand: Operand) -> str | Port:
        """Resolve a destination operand to a register name or port."""
        if operand.is_literal:
            raise ExecutionError("Cannot write to literal value")

        name = operand.value
        if name == "ACC":
            return "ACC"
        elif name == "NIL":
            return "NIL"
        elif name in ("UP", "DOWN", "LEFT", "RIGHT", "ANY", "LAST"):
            return Port[name]
        else:
            raise ExecutionError(f"Invalid destination: {name}")

    def _write_dest(self, dest: str, value: int) -> None:
        """Write value to a register destination."""
        if dest == "ACC":
            self.acc = _clamp(value)
        elif dest == "NIL":
            pass  # Discard

    def _advance_pc(self) -> None:
        """Advance program counter, wrapping at end."""
        if self.program.instructions:
            self.pc = (self.pc + 1) % len(self.program.instructions)

    def step(self) -> None:
        """Execute one step of the node.

        If the node is blocked on I/O, this does nothing.
        The Grid handles unblocking nodes when communication completes.
        """
        if self.state == NodeState.IDLE or self.is_empty:
            return

        if self.is_blocked:
            return  # Waiting for I/O

        if self.pc >= len(self.program.instructions):
            self.pc = 0
        instr = self.program.instructions[self.pc]
        op = instr.opcode

        if op == "NOP":
            self._advance_pc()

        elif op == "MOV":
            src = self._resolve_source(instr.args[0])
            dst = self._resolve_dest(instr.args[1])

            if isinstance(src, Port):
                # Need to read from port first
                self.state = NodeState.READ
                self.pending = PortRequest(port=src, is_write=False)
                # Store dest for when read completes
                self._mov_dest = dst
                return

            if isinstance(dst, Port):
                # Need to write to port
                self.state = NodeState.WRITE
                self.pending = PortRequest(port=dst, value=src, is_write=True)
                return

            # Register to register
            self._write_dest(dst, src)
            self._advance_pc()

        elif op == "SWP":
            self.acc, self.bak = self.bak, self.acc
            self._advance_pc()

        elif op == "SAV":
            self.bak = self.acc
            self._advance_pc()

        elif op == "ADD":
            src = self._resolve_source(instr.args[0])
            if isinstance(src, Port):
                self.state = NodeState.READ
                self.pending = PortRequest(port=src, is_write=False)
                self._pending_op = "ADD"
                return
            self.acc = _clamp(self.acc + src)
            self._advance_pc()

        elif op == "SUB":
            src = self._resolve_source(instr.args[0])
            if isinstance(src, Port):
                self.state = NodeState.READ
                self.pending = PortRequest(port=src, is_write=False)
                self._pending_op = "SUB"
                return
            self.acc = _clamp(self.acc - src)
            self._advance_pc()

        elif op == "NEG":
            self.acc = _clamp(-self.acc)
            self._advance_pc()

        elif op == "JMP":
            label = instr.args[0].value
            self.pc = self.program.labels[label]

        elif op == "JEZ":
            label = instr.args[0].value
            if self.acc == 0:
                self.pc = self.program.labels[label]
            else:
                self._advance_pc()

        elif op == "JNZ":
            label = instr.args[0].value
            if self.acc != 0:
                self.pc = self.program.labels[label]
            else:
                self._advance_pc()

        elif op == "JGZ":
            label = instr.args[0].value
            if self.acc > 0:
                self.pc = self.program.labels[label]
            else:
                self._advance_pc()

        elif op == "JLZ":
            label = instr.args[0].value
            if self.acc < 0:
                self.pc = self.program.labels[label]
            else:
                self._advance_pc()

        elif op == "JRO":
            src = self._resolve_source(instr.args[0])
            if isinstance(src, Port):
                self.state = NodeState.READ
                self.pending = PortRequest(port=src, is_write=False)
                self._pending_op = "JRO"
                return
            # Jump relative
            new_pc = self.pc + src
            if self.program.instructions:
                # Clamp to valid range
                new_pc = max(0, min(len(self.program.instructions) - 1, new_pc))
            self.pc = new_pc

    def complete_read(self, value: int, port: Port) -> None:
        """Called by Grid when a read operation completes."""
        self.last_port = port
        instr = self.program.instructions[self.pc]

        if instr.opcode == "MOV":
            dst = self._mov_dest
            if isinstance(dst, Port):
                # Read into port (forward)
                self.state = NodeState.WRITE
                self.pending = PortRequest(port=dst, value=value, is_write=True)
                return
            self._write_dest(dst, value)

        elif hasattr(self, "_pending_op"):
            op = self._pending_op
            if op == "ADD":
                self.acc = _clamp(self.acc + value)
            elif op == "SUB":
                self.acc = _clamp(self.acc - value)
            elif op == "JRO":
                new_pc = self.pc + value
                if self.program.instructions:
                    new_pc = max(0, min(len(self.program.instructions) - 1, new_pc))
                self.pc = new_pc
                self.state = NodeState.RUN
                self.pending = None
                return
            delattr(self, "_pending_op")

        self.state = NodeState.RUN
        self.pending = None
        self._advance_pc()

    def complete_write(self, port: Port) -> None:
        """Called by Grid when a write operation completes."""
        self.last_port = port
        self.state = NodeState.RUN
        self.pending = None
        self._advance_pc()
