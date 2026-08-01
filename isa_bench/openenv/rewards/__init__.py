"""Modular reward functions for ISA_bench environments."""

from .base import RewardFunction
from .correctness import CorrectnessReward
from .hrm import HRMReward
from .sic1 import SIC1Reward
from .tis100 import TIS100Reward
from .box256 import BOX256Reward
from .mhrd import MHRDReward

REWARDS = {
    "hrm": HRMReward,
    "sic1": SIC1Reward,
    "tis100": TIS100Reward,
    "box256": BOX256Reward,
    "mhrd": MHRDReward,
}


def get_reward_fn(game: str) -> RewardFunction:
    """Get default reward function for a game."""
    if game not in REWARDS:
        return CorrectnessReward()
    return REWARDS[game]()


__all__ = ["RewardFunction", "CorrectnessReward", "get_reward_fn", "REWARDS"]
