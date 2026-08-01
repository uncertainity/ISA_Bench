"""MHRD circuit simulator.

Evaluates HDL designs by propagating signals through NAND gates.
Supports component composition - built components become reusable parts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .parser import HDLDesign, Pin, Wire, WireEnd
from .errors import SimulationError


@dataclass
class Circuit:
    """A compiled circuit that can be evaluated."""

    name: str
    inputs: list[Pin]
    outputs: list[Pin]
    evaluate_fn: Callable[[dict[str, list[bool]]], dict[str, list[bool]]]
    nand_count: int = 0

    def evaluate(self, input_values: dict[str, list[bool]]) -> dict[str, list[bool]]:
        """Evaluate the circuit with given input values.

        Args:
            input_values: Dict mapping input pin names to lists of bool values.
                         For single pins, use a list of one element.

        Returns:
            Dict mapping output pin names to lists of bool values.
        """
        return self.evaluate_fn(input_values)

    def __call__(self, **kwargs: int | list[int]) -> dict[str, list[bool]]:
        """Convenience method to evaluate with keyword arguments.

        Accepts int (0/1) or list[int] for bus values.
        """
        input_values: dict[str, list[bool]] = {}
        for name, value in kwargs.items():
            if isinstance(value, int):
                input_values[name] = [bool(value)]
            else:
                input_values[name] = [bool(v) for v in value]
        return self.evaluate(input_values)


def NAND(a: bool, b: bool) -> bool:
    """The fundamental NAND gate."""
    return not (a and b)


class ComponentLibrary:
    """Library of available components for circuit building."""

    def __init__(self):
        self._components: dict[str, Circuit] = {}
        self._register_nand()
        self._register_builtins()

    def _register_nand(self):
        """Register the fundamental NAND gate."""

        def nand_eval(inputs: dict[str, list[bool]]) -> dict[str, list[bool]]:
            a = inputs.get("in1", [False])[0]
            b = inputs.get("in2", [False])[0]
            return {"out": [NAND(a, b)]}

        self._components["NAND"] = Circuit(
            name="NAND",
            inputs=[Pin("in1"), Pin("in2")],
            outputs=[Pin("out")],
            evaluate_fn=nand_eval,
            nand_count=1,
        )

    def _register_builtins(self) -> None:
        """Register the canonical components unlocked by earlier puzzles.

        These components expose the same pin names as their corresponding
        puzzle interfaces.  Their NAND counts reflect the canonical compact
        constructions used by the benchmark and are included recursively when
        a submitted design uses a built component.
        """

        def bit(inputs: dict[str, list[bool]], name: str) -> bool:
            return inputs.get(name, [False])[0]

        self._components["NOT"] = Circuit(
            name="NOT",
            inputs=[Pin("in")],
            outputs=[Pin("out")],
            evaluate_fn=lambda inputs: {
                "out": [not bit(inputs, "in")],
            },
            nand_count=1,
        )
        self._components["AND"] = Circuit(
            name="AND",
            inputs=[Pin("in1"), Pin("in2")],
            outputs=[Pin("out")],
            evaluate_fn=lambda inputs: {
                "out": [bit(inputs, "in1") and bit(inputs, "in2")],
            },
            nand_count=2,
        )
        self._components["OR"] = Circuit(
            name="OR",
            inputs=[Pin("in1"), Pin("in2")],
            outputs=[Pin("out")],
            evaluate_fn=lambda inputs: {
                "out": [bit(inputs, "in1") or bit(inputs, "in2")],
            },
            nand_count=3,
        )
        self._components["XOR"] = Circuit(
            name="XOR",
            inputs=[Pin("in1"), Pin("in2")],
            outputs=[Pin("out")],
            evaluate_fn=lambda inputs: {
                "out": [bit(inputs, "in1") != bit(inputs, "in2")],
            },
            nand_count=4,
        )
        self._components["MUX"] = Circuit(
            name="MUX",
            inputs=[Pin("in1"), Pin("in2"), Pin("sel")],
            outputs=[Pin("out")],
            evaluate_fn=lambda inputs: {
                "out": [
                    bit(inputs, "in2") if bit(inputs, "sel") else bit(inputs, "in1")
                ],
            },
            nand_count=4,
        )
        self._components["DEMUX"] = Circuit(
            name="DEMUX",
            inputs=[Pin("in"), Pin("sel")],
            outputs=[Pin("out1"), Pin("out2")],
            evaluate_fn=lambda inputs: {
                "out1": [bit(inputs, "in") and not bit(inputs, "sel")],
                "out2": [bit(inputs, "in") and bit(inputs, "sel")],
            },
            nand_count=5,
        )
        self._components["HALFADDER"] = Circuit(
            name="HALFADDER",
            inputs=[Pin("a"), Pin("b")],
            outputs=[Pin("sum"), Pin("carry")],
            evaluate_fn=lambda inputs: {
                "sum": [bit(inputs, "a") != bit(inputs, "b")],
                "carry": [bit(inputs, "a") and bit(inputs, "b")],
            },
            nand_count=5,
        )

    def get(self, name: str) -> Circuit:
        """Get a component by name."""
        if name not in self._components:
            raise SimulationError(f"Unknown component: {name}")
        return self._components[name]

    def has(self, name: str) -> bool:
        """Check if a component exists."""
        return name in self._components

    def register(self, circuit: Circuit):
        """Register a new component."""
        self._components[circuit.name] = circuit

    def list_components(self) -> list[str]:
        """List all available component names."""
        return list(self._components.keys())


def _resolve_wire_source(
    wire_end: WireEnd,
    design_inputs: dict[str, list[bool]],
    part_outputs: dict[str, dict[str, list[bool]]],
) -> list[bool] | None:
    """Resolve the value(s) from a wire source.

    Returns None if the source is a part output that hasn't been evaluated yet.
    """
    if wire_end.is_constant:
        val = wire_end.name == "1"
        return [val]

    if "." in wire_end.name:
        # Part output: n1.out
        part_name, pin_name = wire_end.name.split(".", 1)
        if part_name not in part_outputs:
            return None  # Not evaluated yet
        values = part_outputs[part_name].get(pin_name, [False])
    else:
        # Design input
        values = design_inputs.get(wire_end.name, [False])

    # Handle indexing
    if wire_end.is_range:
        start, end = wire_end.range_start, wire_end.range_end
        return values[start - 1 : end]  # 1-indexed
    elif wire_end.is_indexed:
        idx = wire_end.index
        return [values[idx - 1]]  # 1-indexed
    else:
        return values


def _apply_wire_dest(
    wire_end: WireEnd,
    values: list[bool],
    target: dict[str, list[bool]],
    width_hints: dict[str, int],
):
    """Apply values to a wire destination."""
    name = wire_end.name
    if "." in name:
        # Will be handled separately for part inputs
        return

    # Ensure target exists with correct width
    if name not in target:
        width = width_hints.get(name, len(values))
        target[name] = [False] * width

    if wire_end.is_range:
        start, end = wire_end.range_start, wire_end.range_end
        for i, v in enumerate(values):
            if start - 1 + i < len(target[name]):
                target[name][start - 1 + i] = v
    elif wire_end.is_indexed:
        idx = wire_end.index
        if idx - 1 < len(target[name]):
            target[name][idx - 1] = values[0] if values else False
    else:
        # Whole bus or single pin
        if len(values) == 1 and len(target[name]) > 1:
            # Broadcast single value to whole bus
            target[name] = [values[0]] * len(target[name])
        else:
            target[name] = values[:]


def compile_design(
    design: HDLDesign,
    name: str,
    library: ComponentLibrary,
) -> Circuit:
    """Compile an HDL design into an evaluatable circuit.

    Args:
        design: Parsed HDL design
        name: Name for this component
        library: Available components

    Returns:
        Compiled Circuit that can be evaluated
    """
    # Calculate NAND count
    total_nands = 0
    for part in design.parts:
        component = library.get(part.component)
        total_nands += component.nand_count

    # Build evaluation function
    def evaluate(input_values: dict[str, list[bool]]) -> dict[str, list[bool]]:
        # Initialize input values with defaults
        inputs: dict[str, list[bool]] = {}
        for pin in design.inputs:
            default = [False] * pin.width
            inputs[pin.name] = input_values.get(pin.name, default)

        # Track part outputs
        part_outputs: dict[str, dict[str, list[bool]]] = {}

        # Build width hints for outputs
        output_widths = {pin.name: pin.width for pin in design.outputs}

        # Collect wires by destination part
        part_inputs: dict[str, dict[str, list[bool]]] = {
            part.instance: {} for part in design.parts
        }

        # Initialize part inputs with correct widths
        for part in design.parts:
            component = library.get(part.component)
            for pin in component.inputs:
                part_inputs[part.instance][pin.name] = [False] * pin.width

        # Helper to apply wire values to part inputs
        def apply_to_part_input(wire, values):
            if "." not in wire.dest.name:
                return
            part_name, pin_name = wire.dest.name.split(".", 1)
            if part_name not in part_inputs:
                return

            target = part_inputs[part_name]
            dest = wire.dest

            # Get pin width from component
            component = library.get(
                next(p.component for p in design.parts if p.instance == part_name)
            )
            pin_width = next(
                (p.width for p in component.inputs if p.name == pin_name), 1
            )

            if pin_name not in target:
                target[pin_name] = [False] * pin_width

            if dest.is_range:
                start, end = dest.range_start, dest.range_end
                for i, v in enumerate(values):
                    if start - 1 + i < len(target[pin_name]):
                        target[pin_name][start - 1 + i] = v
            elif dest.is_indexed:
                idx = dest.index
                if idx - 1 < len(target[pin_name]):
                    target[pin_name][idx - 1] = values[0] if values else False
            else:
                if len(values) == 1 and len(target[pin_name]) > 1:
                    target[pin_name] = [values[0]] * len(target[pin_name])
                else:
                    target[pin_name] = values[:]

        # First pass: wire design inputs and constants to part inputs
        for wire in design.wires:
            if "." in wire.dest.name:
                # Only process wires from design inputs or constants
                if "." not in wire.source.name:
                    values = _resolve_wire_source(wire.source, inputs, part_outputs)
                    if values is not None:
                        apply_to_part_input(wire, values)

        # Evaluate parts iteratively until stable
        max_iterations = len(design.parts) * 2 + 1
        for _ in range(max_iterations):
            changed = False
            for part in design.parts:
                component = library.get(part.component)
                old_outputs = part_outputs.get(part.instance, {})
                new_outputs = component.evaluate(part_inputs[part.instance])
                if new_outputs != old_outputs:
                    changed = True
                    part_outputs[part.instance] = new_outputs

            # Propagate part outputs to other part inputs
            for wire in design.wires:
                if "." in wire.source.name and "." in wire.dest.name:
                    values = _resolve_wire_source(wire.source, inputs, part_outputs)
                    if values is not None:
                        apply_to_part_input(wire, values)

            if not changed:
                break
        else:
            raise SimulationError(
                f"Circuit did not converge after {max_iterations} propagation iterations"
            )

        # Collect outputs
        outputs: dict[str, list[bool]] = {}
        for pin in design.outputs:
            outputs[pin.name] = [False] * pin.width

        for wire in design.wires:
            if wire.dest.name in output_widths or (
                not wire.dest.is_constant and "." not in wire.dest.name
            ):
                values = _resolve_wire_source(wire.source, inputs, part_outputs)
                _apply_wire_dest(wire.dest, values, outputs, output_widths)

        return outputs

    return Circuit(
        name=name,
        inputs=design.inputs,
        outputs=design.outputs,
        evaluate_fn=evaluate,
        nand_count=total_nands,
    )


def simulate(
    design: HDLDesign,
    inputs: dict[str, int | list[int]],
    library: ComponentLibrary | None = None,
) -> dict[str, list[bool]]:
    """Simulate an HDL design with given inputs.

    Args:
        design: Parsed HDL design
        inputs: Input values (int for single pin, list for bus)
        library: Component library (uses default if None)

    Returns:
        Output values as dict of bool lists
    """
    if library is None:
        library = ComponentLibrary()

    circuit = compile_design(design, "temp", library)

    # Convert inputs
    input_values: dict[str, list[bool]] = {}
    for name, value in inputs.items():
        if isinstance(value, int):
            input_values[name] = [bool(value)]
        else:
            input_values[name] = [bool(v) for v in value]

    return circuit.evaluate(input_values)
