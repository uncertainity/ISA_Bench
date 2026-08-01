"""TIS-100 specific reward function."""

from typing import Any

from ..adapters.base import ExecutionResult


class TIS100Reward:
    """TIS-100 reward: correctness + efficiency bonus.

    Efficiency based on cycles, nodes used, and total instructions.
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

        # Efficiency bonus based on node usage
        # Fewer nodes = more efficient
        nodes = result.metrics.get("nodes", 12)
        node_efficiency = max(
            0.0, 1.0 - (nodes - 1) / 11
        )  # 1 node = 1.0, 12 nodes = 0.0

        return base_reward + self.efficiency_weight * node_efficiency
