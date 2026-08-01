"""Versioned system prompts for the canonical ISA-Bench tracks."""

from __future__ import annotations

from importlib.resources import files


SUPPORTED_GAMES = ("hrm", "sic1", "tis100", "box256", "mhrd")
SUPPORTED_TRACKS = ("spec_only", "worked_examples")


def get_system_prompt(game: str, track: str) -> str:
    """Load the canonical system prompt for a game and evaluation track.

    Args:
        game: One of ``hrm``, ``sic1``, ``tis100``, ``box256``, or ``mhrd``.
        track: Exactly ``spec_only`` or ``worked_examples``.

    Raises:
        TypeError: If either argument is not a string.
        ValueError: If the game or track is not supported.
    """
    if not isinstance(game, str):
        raise TypeError(f"game must be a string, got {type(game).__name__}")
    if not isinstance(track, str):
        raise TypeError(f"track must be a string, got {type(track).__name__}")

    game = game.strip().lower()
    if game not in SUPPORTED_GAMES:
        choices = ", ".join(SUPPORTED_GAMES)
        raise ValueError(f"unknown game {game!r}; expected one of: {choices}")
    if track not in SUPPORTED_TRACKS:
        choices = ", ".join(SUPPORTED_TRACKS)
        raise ValueError(f"unknown prompt track {track!r}; expected one of: {choices}")

    prompt_file = files(__package__).joinpath(track, f"{game}.md")
    return prompt_file.read_text(encoding="utf-8")


__all__ = ["SUPPORTED_GAMES", "SUPPORTED_TRACKS", "get_system_prompt"]
