"""Small public-API tests for the standalone checker."""

import pytest

from isa_bench import check_solution, get_puzzle_info, list_games, list_puzzles
from isa_bench.openenv.adapters import get_default_max_steps


def test_lists_all_five_games():
    assert list_games() == ("hrm", "sic1", "tis100", "box256", "mhrd")


def test_canonical_box_cycle_budget_matches_released_prompt():
    assert get_default_max_steps("box256") == 10_000
    assert get_default_max_steps("hrm") == 100_000


@pytest.mark.parametrize("game", list_games())
def test_every_game_has_puzzles(game):
    assert list_puzzles(game)


def test_get_puzzle_info():
    puzzle = get_puzzle_info("hrm", "hrm_level_1")
    assert puzzle.name == "Mail Room"
    assert puzzle.game == "hrm"


def test_check_known_good_hrm_solution():
    result = check_solution(
        "hrm",
        "hrm_level_1",
        "loop:\nINBOX\nOUTBOX\nJUMP loop",
    )
    assert result.success
    assert result.tests_passed == result.tests_total == 2


def test_check_parse_error_is_structured():
    result = check_solution("hrm", "hrm_level_1", "NOT_A_COMMAND")
    assert not result.success
    assert result.parse_error


def test_rejects_nonpositive_step_limit():
    with pytest.raises(ValueError, match="positive"):
        check_solution("hrm", "hrm_level_1", "INBOX", max_steps=0)
