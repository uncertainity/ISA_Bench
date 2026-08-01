"""HRM-specific reward function."""

from typing import Any

from ..adapters.base import ExecutionResult
from ...games.hrm.puzzles.schema import Puzzle


class HRMReward:
    """HRM reward: correctness + efficiency bonus.

    Reward structure:
    - Base: correctness_weight * (tests_passed / tests_total)
    - Bonus (only if all tests pass): efficiency_weight * efficiency_score

    Efficiency is computed by comparing steps and instructions to par values.
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

        # Base correctness score
        correctness = result.tests_passed / result.tests_total
        base_reward = self.correctness_weight * correctness

        # Efficiency bonus only if all tests pass
        if not result.success:
            return base_reward

        efficiency = self._compute_efficiency(result, puzzle)
        return base_reward + self.efficiency_weight * efficiency

    def _compute_efficiency(self, result: ExecutionResult, puzzle: Any) -> float:
        """Compute efficiency score (0.0 to 1.0) based on par values."""
        if not isinstance(puzzle, Puzzle) or puzzle.challenge is None:
            return 1.0

        scores = []

        # Instructions efficiency
        par_size = puzzle.challenge.size
        actual_size = result.metrics.get("instructions", par_size)
        if par_size > 0:
            scores.append(min(1.0, par_size / max(1, actual_size)))

        # Steps efficiency
        par_speed = puzzle.challenge.speed
        actual_steps = result.metrics.get("steps", par_speed)
        if par_speed > 0:
            scores.append(min(1.0, par_speed / max(1, actual_steps)))

        return sum(scores) / len(scores) if scores else 1.0
