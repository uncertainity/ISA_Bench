"""Access to the versioned benchmark protocol manifest."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def get_benchmark_manifest() -> dict[str, Any]:
    """Return a fresh dictionary containing the installed release manifest."""

    resource = files("isa_bench").joinpath("benchmark_manifest.json")
    return json.loads(resource.read_text(encoding="utf-8"))


__all__ = ["get_benchmark_manifest"]
