"""Versioned scenario sets: freeze.json hashes, and a run-once marker for locked sets."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import workspace
from .spec import BenchmarkSpec, Config, scenario_id
from .runner import config_ref

FREEZE = "freeze.json"
LOCKED_RUNS = "locked-runs.jsonl"


class FreezeError(Exception):
    pass


def _hashes(bench: list[tuple[Path, BenchmarkSpec]]) -> dict[str, dict]:
    return {scenario_id(t, s): {"version": s.meta.version if s.meta else 1, "sha256": workspace.scenario_hash(t)}
            for t, s in bench}


def freeze(root: Path, bench: list[tuple[Path, BenchmarkSpec]], *, locked: bool) -> Path:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
    out = root / FREEZE
    out.write_text(json.dumps({
        "frozen_at": datetime.now(timezone.utc).date().isoformat(),
        "commit": commit or None,
        "locked": locked,
        "scenarios": _hashes(bench),
    }, indent=2, sort_keys=True) + "\n")
    return out


def check(root: Path, bench: list[tuple[Path, BenchmarkSpec]]) -> dict | None:
    """The set's freeze.json, after checking every scenario still matches it. None when the set is not frozen."""
    path = root / FREEZE
    if not path.exists():
        return None
    frozen = json.loads(path.read_text())
    actual = _hashes(bench)
    changed = sorted(sid for sid in set(actual) | set(frozen["scenarios"])
                     if actual.get(sid) != frozen["scenarios"].get(sid))
    if changed:
        raise FreezeError(f"{root}: changed since {FREEZE}: {', '.join(changed)}. "
                          "Bump meta.version of each changed scenario and run `proofs freeze` again.")
    return {**frozen, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def claim_locked_run(root: Path, configs: list[Config]) -> None:
    """A locked set runs once per config. Record the claim before any run starts."""
    log = root / LOCKED_RUNS
    done = {json.loads(line)["sha256"] for line in log.read_text().splitlines() if line.strip()} if log.exists() else set()
    repeat = [c.name for c in configs if config_ref(c).sha256 in done]
    if repeat:
        raise FreezeError(f"{root} is locked and already ran under {repeat}; a locked set runs once per config")
    with log.open("a") as f:
        for c in configs:
            f.write(json.dumps({"config": c.name, "sha256": config_ref(c).sha256,
                                "started_at": datetime.now(timezone.utc).isoformat()}, sort_keys=True) + "\n")
