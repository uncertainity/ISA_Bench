"""Base reward function protocol."""

from typing import Any, Protocol

from ..adapters.base import ExecutionResult


class RewardFunction(Protocol):
    """Protocol for reward computation.

    Reward functions take execution results and puzzle info,
    returning a float reward value.
    """

    def __call__(
        self,
        result: ExecutionResult,
        puzzle: Any,
    ) -> float:
        """Compute reward from execution result.

        Args:
            result: Execution result with success, metrics, test results
            puzzle: The puzzle being solved

        Returns:
            Reward value (typically 0.0 to 1.0)
        """
        ...
