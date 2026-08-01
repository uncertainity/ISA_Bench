"""MHRD specific reward function."""

from typing import Any

from ..adapters.base import ExecutionResult


class MHRDReward:
    """MHRD reward: correctness + NAND efficiency.

    Primary optimization target is NAND count.
    """

    def __init__(
        self,
        correctness_weight: float = 0.7,
        efficiency_weight: float = 0.3,
        # Typical NAND counts for reference
        reference_nands: int = 10,
    ):
        self.correctness_weight = correctness_weight
        self.efficiency_weight = efficiency_weight
        self.reference_nands = reference_nands

    def __call__(self, result: ExecutionResult, puzzle: Any) -> float:
        if result.tests_total == 0:
            return 0.0

        correctness = result.tests_passed / result.tests_total
        base_reward = self.correctness_weight * correctness

        if not result.success:
            return base_reward

        # NAND efficiency: fewer is better
        nand_count = result.metrics.get("nand_count", self.reference_nands)
        nand_efficiency = min(1.0, self.reference_nands / max(1, nand_count))

        return base_reward + self.efficiency_weight * nand_efficiency
