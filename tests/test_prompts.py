"""Tests for the two frozen prompt tracks."""

import pytest

from isa_bench.prompts import SUPPORTED_GAMES, SUPPORTED_TRACKS, get_system_prompt


@pytest.mark.parametrize("track", SUPPORTED_TRACKS)
@pytest.mark.parametrize("game", SUPPORTED_GAMES)
def test_all_canonical_prompts_load(game, track):
    prompt = get_system_prompt(game, track)
    assert len(prompt) > 100
    assert "RESPONSE FORMAT" in prompt


@pytest.mark.parametrize("game", SUPPORTED_GAMES)
def test_tracks_are_distinct(game):
    spec_only = get_system_prompt(game, "spec_only")
    worked = get_system_prompt(game, "worked_examples")
    assert spec_only != worked
    assert "WORKED EXAMPLES" not in spec_only


def test_unknown_track_fails_clearly():
    with pytest.raises(ValueError, match="unknown prompt track"):
        get_system_prompt("hrm", "legacy")
