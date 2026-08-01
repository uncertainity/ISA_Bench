"""MHRD HDL error types."""


class HDLError(Exception):
    """Base error for MHRD HDL operations."""

    pass


class ParseError(HDLError):
    """Error during HDL parsing."""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        if line is not None:
            super().__init__(f"Line {line}: {message}")
        else:
            super().__init__(message)


class SimulationError(HDLError):
    """Error during circuit simulation."""

    pass
