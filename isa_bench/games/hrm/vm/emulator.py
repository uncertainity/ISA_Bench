"""HRM emulator — executes parsed HRM programs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .parser import Program, Address
from .errors import ExecutionError

Value = Union[int, str]


@dataclass
class EmulatorResult:
    """Result returned after running the emulator."""

    outbox: list[Value]
    steps_executed: int
    instructions_used: int


class Emulator:
    """HRM emulator.

    Executes HRM programs with inbox/outbox I/O and floor tile memory.
    Values can be integers (-999 to 999) or single uppercase characters.
    """

    def __init__(
        self,
        program: Program,
        inbox: list[Value] | None = None,
        floor: dict[int, Value] | None = None,
    ):
        self._program = program
        self._initial_inbox = list(inbox) if inbox else []
        self._initial_floor = dict(floor) if floor else {}

        self._inbox: list[Value] = []
        self._outbox: list[Value] = []
        self._floor: dict[int, Value] = {}
        self._hands: Value | None = None
        self._ip: int = 0
        self._running: bool = True
        self._steps_executed: int = 0

        self.reset()

    @property
    def hands(self) -> Value | None:
        return self._hands

    @property
    def outbox(self) -> list[Value]:
        return self._outbox

    @property
    def steps_executed(self) -> int:
        return self._steps_executed

    @property
    def is_running(self) -> bool:
        return self._running and 0 <= self._ip < len(self._program)

    def reset(self) -> None:
        """Reset emulator to initial state."""
        self._inbox = list(self._initial_inbox)
        self._outbox = []
        self._floor = dict(self._initial_floor)
        self._hands = None
        self._ip = 0
        self._running = True
        self._steps_executed = 0

    def _get_address(self, addr: Address) -> int:
        """Resolve address, handling indirect addressing."""
        if isinstance(addr, list):
            # Indirect: [n] means use floor[n] as the address
            indirect = addr[0]
            if indirect not in self._floor:
                raise ExecutionError(f"Empty tile {indirect}", self._ip)
            val = self._floor[indirect]
            if not isinstance(val, int):
                raise ExecutionError(
                    f"Cannot use character '{val}' as address", self._ip
                )
            return val
        return addr

    def _read_floor(self, addr: Address) -> Value:
        """Read value from floor tile."""
        resolved = self._get_address(addr)
        if resolved not in self._floor:
            raise ExecutionError(f"Empty tile {resolved}", self._ip)
        return self._floor[resolved]

    def _write_floor(self, addr: Address, value: Value) -> None:
        """Write value to floor tile."""
        resolved = self._get_address(addr)
        self._floor[resolved] = value

    def _require_hands(self) -> Value:
        """Ensure hands is not empty."""
        if self._hands is None:
            raise ExecutionError("Empty hands", self._ip)
        return self._hands

    def step(self) -> bool:
        """Execute one instruction. Returns True if program should continue."""
        if not self.is_running:
            return False

        instr = self._program.instructions[self._ip]
        op = instr.op
        arg = instr.arg
        self._ip += 1

        if op == "inbox":
            if not self._inbox:
                self._running = False
                return False
            self._hands = self._inbox.pop(0)

        elif op == "outbox":
            val = self._require_hands()
            self._outbox.append(val)
            self._hands = None

        elif op == "copyfrom":
            assert isinstance(arg, (int, list))
            self._hands = self._read_floor(arg)

        elif op == "copyto":
            assert isinstance(arg, (int, list))
            val = self._require_hands()
            self._write_floor(arg, val)

        elif op == "add":
            assert isinstance(arg, (int, list))
            hands = self._require_hands()
            if not isinstance(hands, int):
                raise ExecutionError(f"Cannot add to character '{hands}'", self._ip - 1)
            other = self._read_floor(arg)
            if not isinstance(other, int):
                raise ExecutionError(f"Cannot add character '{other}'", self._ip - 1)
            self._hands = hands + other

        elif op == "sub":
            assert isinstance(arg, (int, list))
            hands = self._require_hands()
            other = self._read_floor(arg)
            if isinstance(hands, int) and isinstance(other, int):
                self._hands = hands - other
            elif isinstance(hands, str) and isinstance(other, str):
                # Character subtraction yields integer (ord difference)
                self._hands = ord(hands) - ord(other)
            else:
                raise ExecutionError(
                    f"Cannot subtract {type(other).__name__} from {type(hands).__name__}",
                    self._ip - 1,
                )

        elif op == "bumpup":
            assert isinstance(arg, (int, list))
            val = self._read_floor(arg)
            if not isinstance(val, int):
                raise ExecutionError(
                    f"Cannot increment character '{val}'", self._ip - 1
                )
            val += 1
            self._write_floor(arg, val)
            self._hands = val

        elif op == "bumpdn":
            assert isinstance(arg, (int, list))
            val = self._read_floor(arg)
            if not isinstance(val, int):
                raise ExecutionError(
                    f"Cannot decrement character '{val}'", self._ip - 1
                )
            val -= 1
            self._write_floor(arg, val)
            self._hands = val

        elif op == "jump":
            assert isinstance(arg, str)
            self._ip = self._program.labels[arg]

        elif op == "jumpz":
            assert isinstance(arg, str)
            hands = self._require_hands()
            if hands == 0:
                self._ip = self._program.labels[arg]

        elif op == "jumpn":
            assert isinstance(arg, str)
            hands = self._require_hands()
            if isinstance(hands, int) and hands < 0:
                self._ip = self._program.labels[arg]

        self._steps_executed += 1
        return self.is_running

    def run(self, max_steps: int = 100_000) -> None:
        """Run until halted or step limit reached."""
        while self.is_running:
            if self._steps_executed >= max_steps:
                raise ExecutionError(f"Step limit exceeded: {max_steps} steps")
            self.step()


def run_program(
    program: Program,
    inbox: list[Value],
    floor: dict[int, Value] | None = None,
    expected_output_count: int | None = None,
    max_steps: int = 100_000,
) -> EmulatorResult:
    """Run a program with given inputs, collect outputs.

    If expected_output_count is set, stops after that many outputs.
    """
    emu = Emulator(program, inbox=inbox, floor=floor)

    while emu.is_running:
        if emu.steps_executed >= max_steps:
            raise ExecutionError(f"Step limit exceeded: {max_steps} steps")
        if (
            expected_output_count is not None
            and len(emu.outbox) >= expected_output_count
        ):
            break
        emu.step()

    return EmulatorResult(
        outbox=list(emu.outbox),
        steps_executed=emu.steps_executed,
        instructions_used=len(program),
    )
