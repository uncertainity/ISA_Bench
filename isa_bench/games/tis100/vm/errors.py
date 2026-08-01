"""TIS-100 error types."""


class TISError(Exception):
    """Base error for TIS-100 operations."""

    pass


class ParseError(TISError):
    """Error during program parsing."""

    def __init__(self, message: str, node: int | None = None, line: int | None = None):
        self.node = node
        self.line = line
        prefix = ""
        if node is not None:
            prefix = f"Node {node}: "
        if line is not None:
            prefix += f"Line {line}: "
        super().__init__(f"{prefix}{message}")


class ExecutionError(TISError):
    """Error during program execution."""

    pass
