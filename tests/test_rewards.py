"""Tests for reward functions."""

import pytest

from isa_bench.openenv.rewards import get_reward_fn, CorrectnessReward
from isa_bench.openenv.rewards.hrm import HRMReward
from isa_bench.openenv.adapters.base import ExecutionResult
from isa_bench.games.hrm.puzzles.schema import Puzzle, Challenge


class TestCorrectnessReward:
    """Tests for correctness-based reward."""

    @pytest.fixture
    def reward_fn(self):
        return CorrectnessReward()

    def test_all_pass(self, reward_fn):
        result = ExecutionResult(
            success=True,
            tests_passed=5,
            tests_total=5,
        )
        assert reward_fn(result, None) == 1.0

    def test_partial_pass(self, reward_fn):
        result = ExecutionResult(
            success=False,
            tests_passed=3,
            tests_total=5,
        )
        assert reward_fn(result, None) == 0.6

    def test_no_pass(self, reward_fn):
        result = ExecutionResult(
            success=False,
            tests_passed=0,
            tests_total=5,
        )
        assert reward_fn(result, None) == 0.0

    def test_no_tests(self, reward_fn):
        result = ExecutionResult(
            success=False,
            tests_passed=0,
            tests_total=0,
        )
        assert reward_fn(result, None) == 0.0


class TestHRMReward:
    """Tests for HRM-specific reward."""

    @pytest.fixture
    def reward_fn(self):
        return HRMReward(correctness_weight=0.7, efficiency_weight=0.3)

    @pytest.fixture
    def puzzle_with_challenge(self):
        return Puzzle(
            number=1,
            name="Test",
            instructions="Test puzzle",
            commands=["inbox", "outbox"],
            challenge=Challenge(size=10, speed=100),
        )

    def test_partial_correct_no_efficiency(self, reward_fn, puzzle_with_challenge):
        """Partial correctness gives only base reward."""
        result = ExecutionResult(
            success=False,
            tests_passed=3,
            tests_total=5,
            metrics={"instructions": 5, "steps": 50},
        )
        # Only correctness: 0.7 * 0.6 = 0.42
        assert reward_fn(result, puzzle_with_challenge) == pytest.approx(0.42)

    def test_all_correct_with_efficiency(self, reward_fn, puzzle_with_challenge):
        """Full correctness gets efficiency bonus."""
        result = ExecutionResult(
            success=True,
            tests_passed=5,
            tests_total=5,
            metrics={"instructions": 10, "steps": 100},  # At par
        )
        # Correctness: 0.7, efficiency at par: 0.3 * 1.0 = 0.3
        assert reward_fn(result, puzzle_with_challenge) == pytest.approx(1.0)

    def test_all_correct_above_par(self, reward_fn, puzzle_with_challenge):
        """Full correctness but over par."""
        result = ExecutionResult(
            success=True,
            tests_passed=5,
            tests_total=5,
            metrics={"instructions": 20, "steps": 200},  # 2x par
        )
        # Correctness: 0.7, efficiency: 0.3 * 0.5 = 0.15
        assert reward_fn(result, puzzle_with_challenge) == pytest.approx(0.85)

    def test_all_correct_below_par(self, reward_fn, puzzle_with_challenge):
        """Full correctness and under par (capped at 1.0)."""
        result = ExecutionResult(
            success=True,
            tests_passed=5,
            tests_total=5,
            metrics={"instructions": 5, "steps": 50},  # Half of par
        )
        # Efficiency capped at 1.0
        assert reward_fn(result, puzzle_with_challenge) == pytest.approx(1.0)

    def test_no_challenge_full_efficiency(self, reward_fn):
        """Puzzle without challenge gets full efficiency bonus."""
        puzzle = Puzzle(
            number=1,
            name="Test",
            instructions="Test",
            commands=[],
            challenge=None,
        )
        result = ExecutionResult(
            success=True,
            tests_passed=1,
            tests_total=1,
            metrics={"instructions": 100, "steps": 1000},
        )
        # Full reward without challenge
        assert reward_fn(result, puzzle) == pytest.approx(1.0)


class TestGetRewardFn:
    """Tests for reward function factory."""

    def test_hrm_reward(self):
        fn = get_reward_fn("hrm")
        assert isinstance(fn, HRMReward)

    def test_unknown_game_fallback(self):
        fn = get_reward_fn("unknown")
        assert isinstance(fn, CorrectnessReward)
