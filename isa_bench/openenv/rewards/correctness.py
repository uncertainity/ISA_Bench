"""Correctness-based reward (test pass rate)."""

from typing import Any

from ..adapters.base import ExecutionResult


class CorrectnessReward:
    """Reward based on test pass rate.

    Returns tests_passed / tests_total, giving partial credit
    for partially correct solutions.
    """

    def __call__(self, result: ExecutionResult, puzzle: Any) -> float:
        if result.tests_total == 0:
            return 0.0
        return result.tests_passed / result.tests_total
