"""Focused tests for the public ISA-Bench command-line interface."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from isa_bench import cli


MAIL_ROOM_SOLUTION = """\
loop:
    INBOX
    OUTBOX
    JUMP loop
"""


def test_list_games(capsys):
    assert cli.main(["list-games"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "hrm",
        "sic1",
        "tis100",
        "box256",
        "mhrd",
    ]


def test_list_puzzles_json(capsys):
    assert cli.main(["list-puzzles", "--game", "hrm", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["game"] == "hrm"
    assert {puzzle["id"] for puzzle in payload["puzzles"]} >= {
        "hrm_level_1",
        "hrm_level_2",
    }


def test_show_puzzle(capsys):
    assert cli.main(["show", "--game", "hrm", "--puzzle", "1"]) == 0
    output = capsys.readouterr().out
    assert "Mail Room" in output
    assert "Available commands:" in output


def test_check_correct_solution_human_output(tmp_path, capsys):
    solution = tmp_path / "mail-room.hrm"
    solution.write_text(MAIL_ROOM_SOLUTION)

    status = cli.main(
        [
            "check",
            "--game",
            "hrm",
            "--puzzle",
            "hrm_level_1",
            "--solution",
            str(solution),
        ]
    )

    assert status == 0
    output = capsys.readouterr().out
    assert "PASS:" in output
    assert "Tests: 2/2" in output


def test_check_correct_solution_json(tmp_path, capsys):
    solution = tmp_path / "mail-room.hrm"
    solution.write_text(MAIL_ROOM_SOLUTION)

    status = cli.main(
        [
            "check",
            "--game",
            "hrm",
            "--puzzle",
            "1",
            "--solution",
            str(solution),
            "--json",
        ]
    )

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["success"] is True
    assert payload["tests_passed"] == payload["tests_total"] == 2
    assert len(payload["test_results"]) == 2


@pytest.mark.parametrize("code", ["INBOX", "NOT_A_COMMAND"])
def test_check_incorrect_or_invalid_solution_exits_one(tmp_path, capsys, code):
    solution = tmp_path / "bad.hrm"
    solution.write_text(code)

    status = cli.main(
        ["check", "--game", "hrm", "--puzzle", "1", "--solution", str(solution)]
    )

    assert status == 1
    assert "FAIL:" in capsys.readouterr().out


def test_check_missing_solution_exits_two(capsys):
    status = cli.main(
        ["check", "--game", "hrm", "--puzzle", "1", "--solution", "does-not-exist.hrm"]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ""
    assert "could not read solution" in captured.err


def test_unknown_puzzle_exits_two(tmp_path, capsys):
    solution = tmp_path / "solution.hrm"
    solution.write_text(MAIL_ROOM_SOLUTION)

    status = cli.main(
        ["check", "--game", "hrm", "--puzzle", "999", "--solution", str(solution)]
    )

    assert status == 2
    assert "could not load puzzle" in capsys.readouterr().err


def test_solve_uses_prompt_override_and_api_key_env(tmp_path, monkeypatch, capsys):
    prompt = tmp_path / "system.md"
    prompt.write_text("Solve this exact ISA puzzle.")
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        def chat(self, messages):
            captured["messages"] = messages
            return SimpleNamespace(
                content=f"<answer>{MAIL_ROOM_SOLUTION}</answer>",
                usage={"total_tokens": 42},
            )

    monkeypatch.setattr(cli, "LLMClient", FakeClient)
    monkeypatch.setenv("ISA_BENCH_API_KEY", "do-not-print-this-key")

    status = cli.main(
        [
            "solve",
            "--game",
            "hrm",
            "--puzzle",
            "1",
            "--model",
            "mock-model",
            "--system-prompt-file",
            str(prompt),
            "--track",
            "worked_examples",
            "--json",
        ]
    )

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["solved"] is True
    assert payload["track"] == "worked_examples"
    assert payload["custom_system_prompt"] is True
    assert len(payload["system_prompt_sha256"]) == 64
    assert len(payload["puzzle_prompt_sha256"]) == 64
    assert payload["temperature"] == 0.0
    assert captured["client_kwargs"]["api_key"] == "do-not-print-this-key"
    assert "do-not-print-this-key" not in json.dumps(payload)
    assert captured["messages"][0].content == "Solve this exact ISA puzzle."
