"""BOX-256 specific reward function."""

from typing import Any

from ..adapters.base import ExecutionResult


class BOX256Reward:
    """BOX-256 reward: pixel accuracy + code size bonus.

    Primary metric is pixel accuracy (partial credit for close matches).
    """

    def __init__(
        self,
        accuracy_weight: float = 0.8,
        size_weight: float = 0.2,
    ):
        self.accuracy_weight = accuracy_weight
        self.size_weight = size_weight

    def __call__(self, result: ExecutionResult, puzzle: Any) -> float:
        # BOX-256 uses pixel accuracy directly
        pixel_accuracy = result.metrics.get("pixel_accuracy", 0.0)
        base_reward = self.accuracy_weight * pixel_accuracy

        if pixel_accuracy < 1.0:
            return base_reward

        # Size bonus for perfect solutions
        # Smaller code = better
        code_size = result.metrics.get("code_size", 256)
        size_efficiency = max(0.0, 1.0 - code_size / 256)

        return base_reward + self.size_weight * size_efficiency
