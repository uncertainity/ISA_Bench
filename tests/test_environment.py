"""Tests for ISAEnvironment."""

import pytest

from isa_bench.openenv.environment import ISAEnvironment
from isa_bench.openenv.models import ISAAction, ISAObservation, ISAState


class TestISAEnvironment:
    """Tests for the main environment class."""

    @pytest.fixture
    def env(self):
        return ISAEnvironment(game="hrm", max_attempts=5)

    def test_init(self, env):
        assert env.game == "hrm"
        assert env._max_attempts == 5

    def test_reset_random(self, env):
        obs = env.reset()

        assert isinstance(obs, ISAObservation)
        assert obs.game == "hrm"
        assert obs.puzzle_id.startswith("hrm_level_")
        assert obs.attempt == 0
        assert obs.done is False
        assert obs.reward == 0.0

    def test_reset_with_puzzle_id(self, env):
        obs = env.reset(puzzle_id="hrm_level_1")

        assert obs.puzzle_id == "hrm_level_1"
        assert obs.puzzle_name == "Mail Room"

    def test_reset_with_puzzle_index(self, env):
        obs = env.reset(puzzle_index=0)

        assert obs.puzzle_id is not None

    def test_reset_with_seed(self, env):
        obs1 = env.reset(seed=42)
        obs2 = env.reset(seed=42)

        assert obs1.puzzle_id == obs2.puzzle_id

    def test_state_before_reset_raises(self):
        env = ISAEnvironment(game="hrm")
        with pytest.raises(RuntimeError, match="not reset"):
            _ = env.state

    def test_step_before_reset_raises(self):
        env = ISAEnvironment(game="hrm")
        with pytest.raises(RuntimeError, match="not reset"):
            env.step(ISAAction(code="INBOX"))

    def test_state_after_reset(self, env):
        env.reset(puzzle_id="hrm_level_1")
        state = env.state

        assert isinstance(state, ISAState)
        assert state.game == "hrm"
        assert state.puzzle_id == "hrm_level_1"
        assert state.step_count == 0
        assert state.solved is False

    def test_step_correct_solution(self, env):
        env.reset(puzzle_id="hrm_level_1")

        obs = env.step(
            ISAAction(
                code="""
a:
    INBOX
    OUTBOX
    JUMP a
"""
            )
        )

        assert isinstance(obs, ISAObservation)
        assert obs.tests_passed == obs.tests_total
        assert obs.done is True
        assert obs.reward > 0
        assert env.state.solved is True

    def test_step_wrong_solution(self, env):
        env.reset(puzzle_id="hrm_level_1")

        obs = env.step(ISAAction(code="INBOX"))

        assert obs.tests_passed < obs.tests_total
        assert obs.reward < 1.0
        assert obs.done is False  # Can still try again

    def test_step_parse_error(self, env):
        env.reset(puzzle_id="hrm_level_1")

        obs = env.step(ISAAction(code="NOT_A_COMMAND"))

        assert obs.parse_error is not None
        assert obs.tests_passed == 0
        assert obs.done is False

    def test_max_attempts_terminates(self, env):
        env = ISAEnvironment(game="hrm", max_attempts=2)
        env.reset(puzzle_id="hrm_level_1")

        obs1 = env.step(ISAAction(code="INBOX"))
        assert obs1.done is False
        assert obs1.attempt == 1

        obs2 = env.step(ISAAction(code="INBOX"))
        assert obs2.done is True
        assert obs2.attempt == 2

    def test_attempt_history_tracked(self, env):
        env.reset(puzzle_id="hrm_level_1")

        env.step(ISAAction(code="code1"))
        env.step(ISAAction(code="code2"))

        assert len(env.state.attempt_history) == 2
        assert env.state.attempt_history[0] == "code1"
        assert env.state.attempt_history[1] == "code2"

    def test_metrics_in_observation(self, env):
        env.reset(puzzle_id="hrm_level_1")

        obs = env.step(
            ISAAction(
                code="""
a:
    INBOX
    OUTBOX
    JUMP a
"""
            )
        )

        assert "steps" in obs.metrics
        assert "instructions" in obs.metrics

    def test_test_results_in_observation(self, env):
        env.reset(puzzle_id="hrm_level_1")

        obs = env.step(
            ISAAction(
                code="""
a:
    INBOX
    OUTBOX
    JUMP a
"""
            )
        )

        assert len(obs.test_results) > 0
        for tr in obs.test_results:
            assert tr.passed is True

    def test_available_commands_in_observation(self, env):
        obs = env.reset(puzzle_id="hrm_level_1")

        assert len(obs.available_commands) > 0
        assert "inbox" in obs.available_commands or "INBOX" in [
            c.upper() for c in obs.available_commands
        ]

    def test_par_in_observation(self, env):
        # Level 2 has challenges
        obs = env.reset(puzzle_id="hrm_level_2")

        # Par may or may not exist depending on puzzle
        assert obs.par is None or isinstance(obs.par, dict)


class TestMultiplePuzzles:
    """Tests for running multiple puzzles."""

    def test_reset_different_puzzles(self):
        env = ISAEnvironment(game="hrm")

        obs1 = env.reset(puzzle_index=0)
        obs2 = env.reset(puzzle_index=1)

        assert obs1.puzzle_id != obs2.puzzle_id

    def test_solve_multiple_puzzles(self):
        env = ISAEnvironment(game="hrm")
        solved = 0

        # Try first 3 puzzles with simple solution
        for i in range(3):
            env.reset(puzzle_index=i)
            obs = env.step(
                ISAAction(
                    code="""
a:
    INBOX
    OUTBOX
    JUMP a
"""
                )
            )
            if obs.tests_passed == obs.tests_total:
                solved += 1

        # At least Mail Room (level 1) should be solved
        assert solved >= 1


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_same_seed_same_result(self):
        env = ISAEnvironment(game="hrm")

        env.reset(puzzle_id="hrm_level_1", seed=42)
        obs1 = env.step(ISAAction(code="INBOX\nOUTBOX\nJUMP 0"))

        env.reset(puzzle_id="hrm_level_1", seed=42)
        obs2 = env.step(ISAAction(code="INBOX\nOUTBOX\nJUMP 0"))

        assert obs1.tests_passed == obs2.tests_passed
        assert obs1.metrics == obs2.metrics


class TestAllGames:
    """Tests for all supported games."""

    def test_sic1_environment(self):
        env = ISAEnvironment(game="sic1")
        obs = env.reset(puzzle_index=0)
        assert obs.game == "sic1"
        assert obs.puzzle_id.startswith("sic1_")

    def test_tis100_environment(self):
        env = ISAEnvironment(game="tis100")
        obs = env.reset(puzzle_index=0)
        assert obs.game == "tis100"

        # Test with a solution
        obs = env.step(
            ISAAction(
                code="""
@0
MOV UP, ACC
ADD ACC
MOV ACC, DOWN
@4
MOV UP, DOWN
"""
            )
        )
        assert obs.tests_total > 0

    def test_box256_environment(self):
        env = ISAEnvironment(game="box256")
        obs = env.reset(puzzle_index=0)
        assert obs.game == "box256"

    def test_mhrd_environment(self):
        env = ISAEnvironment(game="mhrd")
        obs = env.reset(puzzle_index=0)
        assert obs.game == "mhrd"

        # Test with NOT gate solution
        obs = env.step(
            ISAAction(
                code="""
Inputs: in;
Outputs: out;
Parts: n NAND;
Wires: in -> n.in1, in -> n.in2, n.out -> out;
"""
            )
        )
        assert obs.tests_passed == obs.tests_total
        assert obs.done

    def test_all_games_have_puzzles(self):
        """Verify all games have loadable puzzles."""
        for game in ["hrm", "sic1", "tis100", "box256", "mhrd"]:
            env = ISAEnvironment(game=game)
            obs = env.reset()
            assert len(obs.puzzle_id) > 0
            assert obs.tests_total >= 0
