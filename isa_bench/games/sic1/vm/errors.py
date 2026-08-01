# SPDX-FileCopyrightText: 2019-2024 Jared Krinke
# SPDX-FileCopyrightText: 2026 ISA-Bench authors and contributors
#
# This module forms part of the SIC-1 VM port modified for ISA Bench in 2026.
# SPDX-License-Identifier: LGPL-3.0-or-later


class CompilationError(Exception):
    """Raised when the assembler cannot compile a program."""

    def __init__(
        self, message: str, line_number: int | None = None, line_text: str | None = None
    ):
        self.line_number = line_number
        self.line_text = line_text
        super().__init__(message)


class ExecutionError(Exception):
    """Raised when the emulator encounters a runtime error (e.g., cycle limit exceeded)."""

    def __init__(self, message: str):
        super().__init__(message)
