"""Command-line interface for the ISA-Bench executable harness."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

from pydantic import BaseModel

from .inference.agent import ISAAgent
from .inference.client import LLMClient
from .openenv.adapters import ADAPTERS, get_adapter, get_default_max_steps


EXIT_SUCCESS = 0
EXIT_INCORRECT = 1
EXIT_USAGE = 2
TRACKS = ("spec_only", "worked_examples")


class CLIError(Exception):
    """A user-facing input or resource-loading error."""


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def _jsonable(value: Any) -> Any:
    """Convert benchmark result objects to JSON-compatible values."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value):
        return {
            field.name: _jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _print_json(payload: Any) -> None:
    print(json.dumps(_jsonable(payload), indent=2, sort_keys=True))


def _get_adapter_and_puzzle(game: str, puzzle_id: str) -> tuple[Any, Any]:
    try:
        adapter = get_adapter(game)
        puzzle = adapter.get_puzzle(puzzle_id)
    except (KeyError, TypeError, ValueError) as exc:
        detail = exc.args[0] if len(exc.args) == 1 else str(exc)
        raise CLIError(
            f"could not load puzzle {puzzle_id!r} for {game!r}: {detail}"
        ) from exc
    return adapter, puzzle


def _read_text(path_value: str, *, label: str) -> str:
    if path_value == "-":
        return sys.stdin.read()

    path = Path(path_value)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CLIError(f"could not read {label} {str(path)!r}: {exc}") from exc


def _puzzle_summary(adapter: Any, puzzle: Any) -> dict[str, Any]:
    return {
        "game": adapter.game_name,
        "id": adapter.get_puzzle_id(puzzle),
        "name": adapter.get_puzzle_name(puzzle),
    }


def _command_list_games(args: argparse.Namespace) -> int:
    games = list(ADAPTERS)
    if args.json:
        _print_json({"games": games})
    else:
        for game in games:
            print(game)
    return EXIT_SUCCESS


def _command_list_puzzles(args: argparse.Namespace) -> int:
    try:
        adapter = get_adapter(args.game)
        puzzles = adapter.load_puzzles()
        summaries = [_puzzle_summary(adapter, puzzle) for puzzle in puzzles]
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise CLIError(f"could not load puzzles for {args.game!r}: {exc}") from exc

    if args.json:
        _print_json({"game": args.game, "puzzles": summaries})
    else:
        for puzzle in summaries:
            print(f"{puzzle['id']}\t{puzzle['name']}")
    return EXIT_SUCCESS


def _command_show(args: argparse.Namespace) -> int:
    adapter, puzzle = _get_adapter_and_puzzle(args.game, args.puzzle)
    payload = {
        **_puzzle_summary(adapter, puzzle),
        "description": adapter.format_description(puzzle),
        "available_commands": adapter.get_commands(puzzle),
        "par": adapter.get_par(puzzle),
    }

    if args.json:
        _print_json(payload)
    else:
        print(f"{payload['name']} ({payload['id']})")
        print(f"Game: {payload['game']}")
        print()
        print(payload["description"])
        if payload["available_commands"]:
            print()
            print("Available commands: " + ", ".join(payload["available_commands"]))
        if payload["par"]:
            print(
                "Par: "
                + ", ".join(f"{key}={value}" for key, value in payload["par"].items())
            )
    return EXIT_SUCCESS


def _execution_payload(adapter: Any, puzzle: Any, result: Any) -> dict[str, Any]:
    return {
        **_puzzle_summary(adapter, puzzle),
        "success": result.success,
        "tests_passed": result.tests_passed,
        "tests_total": result.tests_total,
        "parse_error": result.parse_error,
        "runtime_error": result.runtime_error,
        "metrics": result.metrics,
        "test_results": result.test_results,
    }


def _print_execution_result(payload: dict[str, Any]) -> None:
    status = "PASS" if payload["success"] else "FAIL"
    print(f"{status}: {payload['game']}/{payload['id']} ({payload['name']})")
    print(f"Tests: {payload['tests_passed']}/{payload['tests_total']}")
    if payload["parse_error"]:
        print(f"Parse error: {payload['parse_error']}")
    if payload["runtime_error"]:
        print(f"Runtime error: {payload['runtime_error']}")
    if payload["metrics"]:
        metrics = ", ".join(
            f"{key}={value}" for key, value in payload["metrics"].items()
        )
        print(f"Metrics: {metrics}")


def _command_check(args: argparse.Namespace) -> int:
    adapter, puzzle = _get_adapter_and_puzzle(args.game, args.puzzle)
    code = _read_text(args.solution, label="solution")
    max_steps = args.max_steps or get_default_max_steps(args.game)
    result = adapter.execute(code=code, puzzle=puzzle, max_steps=max_steps)
    payload = _execution_payload(adapter, puzzle, result)

    if args.json:
        _print_json(payload)
    else:
        _print_execution_result(payload)
    return EXIT_SUCCESS if result.success else EXIT_INCORRECT


def _reference_prompt(game: str, track: str) -> str:
    """Load a canonical prompt lazily so VM-only commands have no prompt dependency."""
    try:
        from .prompts import get_system_prompt
    except ImportError as exc:
        raise CLIError(
            "reference prompts are not installed; use --system-prompt-file"
        ) from exc

    try:
        return get_system_prompt(game, track)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise CLIError(
            f"could not load the {track!r} prompt for {game!r}: {exc}"
        ) from exc


def _make_agent(
    client: LLMClient,
    *,
    game: str,
    max_attempts: int,
    track: str,
    system_prompt: str,
    verbose: bool,
) -> ISAAgent:
    """Construct an agent across the legacy and track-aware agent APIs."""
    import inspect

    parameters = inspect.signature(ISAAgent).parameters
    kwargs: dict[str, Any] = {
        "game": game,
        "max_attempts": max_attempts,
        "verbose": verbose,
    }
    if "track" in parameters:
        kwargs["track"] = track
    if "system_prompt" in parameters:
        kwargs["system_prompt"] = system_prompt

    agent = ISAAgent(client, **kwargs)
    if "system_prompt" not in parameters:
        agent.system_prompt = system_prompt
    return agent


def _agent_payload(
    game: str,
    track: str,
    result: Any,
    *,
    custom_system_prompt: bool,
) -> dict[str, Any]:
    codes = list(result.codes)
    return {
        "game": game,
        "track": track,
        "custom_system_prompt": custom_system_prompt,
        "system_prompt_sha256": result.system_prompt_sha256,
        "puzzle_prompt_sha256": result.puzzle_prompt_sha256,
        "puzzle_id": result.puzzle_id,
        "puzzle_name": result.puzzle_name,
        "solved": result.solved,
        "attempts": result.attempts,
        "final_reward": result.final_reward,
        "best_reward": result.best_reward,
        "total_tokens": result.total_tokens,
        "error": result.error,
        "final_code": codes[-1] if codes else None,
        "codes": codes,
        "raw_responses": list(result.raw_responses),
        "observations": result.observations,
    }


def _print_agent_result(payload: dict[str, Any]) -> None:
    status = "SOLVED" if payload["solved"] else "FAILED"
    print(
        f"{status}: {payload['game']}/{payload['puzzle_id']} ({payload['puzzle_name']})"
    )
    print(f"Track: {payload['track']}")
    print(f"Attempts: {payload['attempts']}")
    print(f"Best reward: {payload['best_reward']:.3f}")
    print(f"Total tokens: {payload['total_tokens']}")
    if payload["error"]:
        print(f"Model error: {payload['error']}")
    if payload["final_code"] is not None:
        print("\nFinal code:\n")
        print(payload["final_code"])


def _command_solve(args: argparse.Namespace) -> int:
    # Resolve the puzzle before making a network request. The agent loads it again
    # when starting the episode, but this gives bad identifiers exit status 2.
    _get_adapter_and_puzzle(args.game, args.puzzle)

    if args.system_prompt_file:
        system_prompt = _read_text(args.system_prompt_file, label="system prompt")
    else:
        system_prompt = _reference_prompt(args.game, args.track)

    api_key = (
        args.api_key
        or os.environ.get("ISA_BENCH_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    base_url = (
        args.base_url
        or os.environ.get("ISA_BENCH_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
    )
    base_url = base_url or "http://localhost:11434/v1"

    client = LLMClient(
        base_url=base_url,
        api_key=api_key,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
    )
    agent = _make_agent(
        client,
        game=args.game,
        max_attempts=args.max_attempts,
        track=args.track,
        system_prompt=system_prompt,
        verbose=args.verbose and not args.json,
    )
    result = agent.solve(puzzle_id=args.puzzle)
    payload = _agent_payload(
        args.game,
        args.track,
        result,
        custom_system_prompt=bool(args.system_prompt_file),
    )
    payload.update(
        {
            "model": args.model,
            "max_attempts": args.max_attempts,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "timeout": args.timeout,
        }
    )

    if args.json:
        _print_json(payload)
    else:
        _print_agent_result(payload)
    return EXIT_SUCCESS if result.solved else EXIT_INCORRECT


def _add_game_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--game", required=True, choices=tuple(ADAPTERS), help="Puzzle game"
    )


def _add_json_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="isa-bench",
        description="Inspect, execute, and solve ISA-Bench puzzles.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_games = subparsers.add_parser(
        "list-games", help="List supported game identifiers"
    )
    _add_json_argument(list_games)
    list_games.set_defaults(handler=_command_list_games)

    list_puzzles = subparsers.add_parser(
        "list-puzzles", help="List puzzles for one game"
    )
    _add_game_argument(list_puzzles)
    _add_json_argument(list_puzzles)
    list_puzzles.set_defaults(handler=_command_list_puzzles)

    show = subparsers.add_parser("show", help="Show a puzzle specification")
    _add_game_argument(show)
    show.add_argument("--puzzle", required=True, help="Puzzle ID or index")
    _add_json_argument(show)
    show.set_defaults(handler=_command_show)

    check = subparsers.add_parser(
        "check", help="Check an existing game-language solution"
    )
    _add_game_argument(check)
    check.add_argument("--puzzle", required=True, help="Puzzle ID or index")
    check.add_argument(
        "--solution", required=True, help="Solution file, or '-' for standard input"
    )
    check.add_argument(
        "--max-steps",
        type=_positive_int,
        default=None,
        help="Execution step limit (default: canonical budget for the game)",
    )
    _add_json_argument(check)
    check.set_defaults(handler=_command_check)

    solve = subparsers.add_parser(
        "solve", help="Ask an OpenAI-compatible model to solve a puzzle"
    )
    _add_game_argument(solve)
    solve.add_argument("--puzzle", required=True, help="Puzzle ID or index")
    solve.add_argument(
        "--model", required=True, help="Model name at the configured endpoint"
    )
    solve.add_argument("--base-url", help="OpenAI-compatible base URL")
    solve.add_argument(
        "--api-key", help="API key (prefer ISA_BENCH_API_KEY or OPENAI_API_KEY)"
    )
    solve.add_argument(
        "--track", choices=TRACKS, default="spec_only", help="Reference prompt track"
    )
    solve.add_argument(
        "--system-prompt-file", help="Override the track's system prompt with this file"
    )
    solve.add_argument(
        "--max-attempts",
        "--retry",
        dest="max_attempts",
        type=_positive_int,
        default=5,
        help="Maximum model attempts (default: %(default)s)",
    )
    solve.add_argument(
        "--temperature",
        type=_nonnegative_float,
        default=0.0,
        help="Sampling temperature",
    )
    solve.add_argument(
        "--max-tokens",
        type=_positive_int,
        default=4096,
        help="Maximum completion tokens",
    )
    solve.add_argument(
        "--timeout", type=_positive_int, default=120, help="Request timeout in seconds"
    )
    solve.add_argument(
        "--verbose", action="store_true", help="Print progress while solving"
    )
    _add_json_argument(solve)
    solve.set_defaults(handler=_command_solve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except CLIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except (KeyError, OSError, TypeError, ValueError) as exc:
        # Keep command-line failures concise; evaluator parse/runtime failures are
        # represented in ExecutionResult and therefore do not arrive here.
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
