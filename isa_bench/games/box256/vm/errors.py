"""BOX-256 error types."""


class ParseError(Exception):
    """Error parsing BOX-256 source code."""

    pass


class ExecutionError(Exception):
    """Error during BOX-256 program execution."""

    pass
