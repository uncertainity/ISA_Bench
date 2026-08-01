"""HRM error types."""


class HRMError(Exception):
    """Base error for HRM operations."""

    pass


class ParseError(HRMError):
    """Error during program parsing."""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        if line is not None:
            super().__init__(f"Line {line}: {message}")
        else:
            super().__init__(message)


class ExecutionError(HRMError):
    """Error during program execution."""

    def __init__(self, message: str, ip: int | None = None):
        self.ip = ip
        if ip is not None:
            super().__init__(f"At IP {ip}: {message}")
        else:
            super().__init__(message)
