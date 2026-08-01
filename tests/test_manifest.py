"""Keep the installed protocol manifest synchronized with released assets."""

import hashlib
import json
from pathlib import Path

from isa_bench import __version__, get_benchmark_manifest, list_games, list_puzzles
from isa_bench.openenv.adapters import get_default_max_steps
from isa_bench.prompts import get_system_prompt


ROOT = Path(__file__).parents[1]


def test_root_and_installed_manifests_match():
    root_manifest = json.loads((ROOT / "benchmark_manifest.json").read_text())
    assert get_benchmark_manifest() == root_manifest


def test_manifest_counts_and_prompt_hashes_match_release():
    manifest = get_benchmark_manifest()
    assert manifest["software_version"] == __version__
    assert tuple(manifest["games"]) == list_games()

    for game in list_games():
        assert manifest["games"][game]["puzzle_count"] == len(list_puzzles(game))
        assert manifest["canonical_execution_budgets"][game] == get_default_max_steps(
            game
        )
        for track in manifest["prompt_tracks"]:
            prompt = get_system_prompt(game, track)
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            assert digest == manifest["prompt_tracks"][track]["sha256"][game]
