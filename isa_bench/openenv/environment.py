"""Main ISA Environment for OpenEnv."""

from typing import Any, List, Optional
from uuid import uuid4

from .models import ISAAction, ISAObservation, ISAState
from .adapters import GameAdapter, get_adapter, get_default_max_steps
from .rewards import get_reward_fn, RewardFunction


class ISAEnvironment:
    """OpenEnv environment for ISA puzzle games.

    Supports multi-turn episodes with feedback across HRM, SIC-1,
    TIS-100, BOX-256, and MHRD puzzle games.

    Example:
        env = ISAEnvironment(game="hrm")
        obs = env.reset(puzzle_id="hrm_level_1")
        obs = env.step(ISAAction(code="INBOX\\nOUTBOX\\nJUMP 0"))
        print(f"Reward: {obs.reward}, Done: {obs.done}")
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(
        self,
        game: str = "hrm",
        max_attempts: int = 5,
        reward_fn: Optional[RewardFunction] = None,
    ):
        """Initialize environment.

        Args:
            game: Game identifier ('hrm', 'sic1', 'tis100', 'box256', 'mhrd')
            max_attempts: Maximum code submissions per episode
            reward_fn: Custom reward function (default: game-specific)
        """
        self._adapter: GameAdapter = get_adapter(game)
        self._reward_fn: RewardFunction = reward_fn or get_reward_fn(game)
        self._max_attempts = max_attempts

        self._state: Optional[ISAState] = None
        self._puzzle: Any = None
        self._puzzles: Optional[List[Any]] = None

    @property
    def game(self) -> str:
        """Current game identifier."""
        return self._adapter.game_name

    @property
    def state(self) -> ISAState:
        """Current environment state."""
        if self._state is None:
            raise RuntimeError("Environment not reset. Call reset() first.")
        return self._state

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        puzzle_id: Optional[str] = None,
        puzzle_index: Optional[int] = None,
        **kwargs,
    ) -> ISAObservation:
        """Reset environment for a new episode.

        Puzzle selection (priority order):
        1. puzzle_id - specific puzzle by ID
        2. puzzle_index - specific puzzle by index
        3. seed - deterministic random selection
        4. Random selection

        Args:
            seed: Random seed for puzzle selection
            episode_id: Optional episode identifier
            puzzle_id: Specific puzzle ID
            puzzle_index: Specific puzzle index

        Returns:
            Initial observation for the episode
        """
        if self._puzzles is None:
            self._puzzles = self._adapter.load_puzzles()

        # Select puzzle
        if puzzle_id is not None:
            self._puzzle = self._adapter.get_puzzle(puzzle_id)
            idx = (
                self._puzzles.index(self._puzzle)
                if self._puzzle in self._puzzles
                else 0
            )
        elif puzzle_index is not None:
            idx = puzzle_index % len(self._puzzles)
            self._puzzle = self._puzzles[idx]
        else:
            import random

            if seed is not None:
                random.seed(seed)
            idx = random.randrange(len(self._puzzles))
            self._puzzle = self._puzzles[idx]

        # Initialize state
        self._state = ISAState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            game=self._adapter.game_name,
            puzzle_id=self._adapter.get_puzzle_id(self._puzzle),
            puzzle_index=idx,
            max_attempts=self._max_attempts,
            attempt_history=[],
            solved=False,
        )

        return self._make_observation(first=True)

    def step(self, action: ISAAction, **kwargs) -> ISAObservation:
        """Execute code submission and return feedback.

        Args:
            action: Action containing code to execute

        Returns:
            Observation with execution results and feedback
        """
        if self._state is None:
            raise RuntimeError("Environment not reset. Call reset() first.")

        self._state.step_count += 1
        self._state.attempt_history.append(action.code)

        # Execute code against puzzle
        result = self._adapter.execute(
            code=action.code,
            puzzle=self._puzzle,
            max_steps=(
                action.max_steps
                if action.max_steps is not None
                else get_default_max_steps(self.game)
            ),
        )

        # Compute reward
        reward = self._reward_fn(result, self._puzzle)

        # Track best solution
        if result.success:
            self._state.solved = True
            if self._state.best_metrics is None:
                self._state.best_metrics = result.metrics.copy()

        # Check termination
        done = (
            self._state.solved or len(self._state.attempt_history) >= self._max_attempts
        )

        # Build observation
        return ISAObservation(
            puzzle_id=self._adapter.get_puzzle_id(self._puzzle),
            puzzle_name=self._adapter.get_puzzle_name(self._puzzle),
            puzzle_description=self._adapter.format_description(self._puzzle),
            game=self._adapter.game_name,
            available_commands=self._adapter.get_commands(self._puzzle),
            par=self._adapter.get_par(self._puzzle),
            test_results=result.test_results,
            tests_passed=result.tests_passed,
            tests_total=result.tests_total,
            metrics=result.metrics,
            last_code=action.code,
            parse_error=result.parse_error,
            runtime_error=result.runtime_error,
            attempt=len(self._state.attempt_history),
            max_attempts=self._max_attempts,
            done=done,
            reward=reward,
        )

    def _make_observation(self, first: bool = False) -> ISAObservation:
        """Construct initial observation."""
        # HRM, SIC-1, and MHRD expose explicit test-case lists. TIS-100
        # evaluates one set of streams and BOX-256 evaluates one target image.
        # Report those evaluator units consistently before the first attempt.
        if hasattr(self._puzzle, "test_cases"):
            tests_total = len(self._puzzle.test_cases)
        else:
            tests_total = 1

        return ISAObservation(
            puzzle_id=self._adapter.get_puzzle_id(self._puzzle),
            puzzle_name=self._adapter.get_puzzle_name(self._puzzle),
            puzzle_description=self._adapter.format_description(self._puzzle),
            game=self._adapter.game_name,
            available_commands=self._adapter.get_commands(self._puzzle),
            par=self._adapter.get_par(self._puzzle),
            tests_total=tests_total,
            attempt=0,
            max_attempts=self._max_attempts,
            done=False,
            reward=0.0,
        )
