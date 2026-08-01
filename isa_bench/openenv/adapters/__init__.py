"""Game adapters for ISA_bench OpenEnv environments."""

from .base import GameAdapter, ExecutionResult
from .hrm import HRMAdapter
from .sic1 import SIC1Adapter
from .tis100 import TIS100Adapter
from .box256 import BOX256Adapter
from .mhrd import MHRDAdapter

ADAPTERS = {
    "hrm": HRMAdapter,
    "sic1": SIC1Adapter,
    "tis100": TIS100Adapter,
    "box256": BOX256Adapter,
    "mhrd": MHRDAdapter,
}

DEFAULT_MAX_STEPS = {
    "hrm": 100_000,
    "sic1": 100_000,
    "tis100": 100_000,
    "box256": 10_000,
    "mhrd": 100_000,
}


def get_adapter(game: str) -> GameAdapter:
    """Get adapter instance for a game."""
    if game not in ADAPTERS:
        raise ValueError(f"Unknown game: {game}. Available: {list(ADAPTERS.keys())}")
    return ADAPTERS[game]()


def get_default_max_steps(game: str) -> int:
    """Return the canonical execution budget for a game."""

    if game not in DEFAULT_MAX_STEPS:
        raise ValueError(
            f"Unknown game: {game}. Available: {list(DEFAULT_MAX_STEPS.keys())}"
        )
    return DEFAULT_MAX_STEPS[game]


__all__ = [
    "ADAPTERS",
    "DEFAULT_MAX_STEPS",
    "ExecutionResult",
    "GameAdapter",
    "get_adapter",
    "get_default_max_steps",
]
