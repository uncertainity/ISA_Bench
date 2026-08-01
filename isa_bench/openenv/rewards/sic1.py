"""SIC-1 specific reward function."""

from typing import Any

from ..adapters.base import ExecutionResult


class SIC1Reward:
    """SIC-1 reward: correctness + efficiency bonus.

    Efficiency based on cycles and program size (bytes).
    """

    def __init__(
        self,
        correctness_weight: float = 0.7,
        efficiency_weight: float = 0.3,
    ):
        self.correctness_weight = correctness_weight
        self.efficiency_weight = efficiency_weight

    def __call__(self, result: ExecutionResult, puzzle: Any) -> float:
        if result.tests_total == 0:
            return 0.0

        correctness = result.tests_passed / result.tests_total
        base_reward = self.correctness_weight * correctness

        if not result.success:
            return base_reward

        # Full efficiency bonus for correct solutions
        # (SIC-1 doesn't have par values, so we give full bonus)
        return base_reward + self.efficiency_weight
