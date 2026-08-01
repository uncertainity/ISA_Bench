"""Pydantic models for ISA_bench OpenEnv environments."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


GameType = Literal["hrm", "sic1", "tis100", "box256", "mhrd"]


class ISAAction(BaseModel):
    """Action for ISA puzzle environments.

    The agent submits code in the game-specific DSL.
    """

    code: str = Field(..., description="Solution code in game-specific DSL")
    max_steps: Optional[int] = Field(
        default=None,
        gt=0,
        description="Execution step limit; omit to use the canonical game budget",
    )

    model_config = {"extra": "forbid"}


class TestCaseResult(BaseModel):
    """Result of running one test case."""

    passed: bool
    input_values: List[Any] = Field(default_factory=list)
    expected_output: List[Any] = Field(default_factory=list)
    actual_output: List[Any] = Field(default_factory=list)
    error: Optional[str] = None


class ISAObservation(BaseModel):
    """Observation returned by ISA puzzle environments.

    Contains puzzle specification, execution feedback, and episode state.
    """

    # Puzzle specification
    puzzle_id: str
    puzzle_name: str
    puzzle_description: str
    game: GameType
    available_commands: List[str] = Field(default_factory=list)

    # Test results
    test_results: List[TestCaseResult] = Field(default_factory=list)
    tests_passed: int = 0
    tests_total: int = 0

    # Execution metrics (game-specific)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    # Par values (optimization targets)
    par: Optional[Dict[str, int]] = None

    # Feedback from last attempt
    last_code: Optional[str] = None
    parse_error: Optional[str] = None
    runtime_error: Optional[str] = None

    # Episode state
    attempt: int = 0
    max_attempts: int = 5

    # Standard OpenEnv fields
    done: bool = False
    reward: float = 0.0

    model_config = {"extra": "forbid"}


class ISAState(BaseModel):
    """Internal state for ISA puzzle environments."""

    episode_id: str
    step_count: int = 0

    game: GameType
    puzzle_id: str
    puzzle_index: int

    attempt_history: List[str] = Field(default_factory=list)
    best_metrics: Optional[Dict[str, Any]] = None
    solved: bool = False
    max_attempts: int = 5

    model_config = {"extra": "forbid"}
