"""VBUS-08 coherence guard — enforceable NOW, not xfail.

V17 adds no parallel substrate. These assertions pass on the pre-V17
baseline and must keep passing through phase end; a violation (new swarm
file, fs-watcher dependency, V17-named Solid component) turns them RED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_DIR = REPO_ROOT / "apps" / "voss-app" / "src" / "swarm"

# A13 swarm file set at V17 start. V17 must not add or remove files here.
KNOWN_SWARM_FILES = {"swarmTypes.ts"}

# Watcher packages V17 must not introduce. `watchdog` pre-dates V17 in the
# root pyproject (one runtime + one dev pin) — that baseline is allowed.
WATCHER_TOKENS = ("chokidar", "watchdog", "watchfiles", "fs-watcher", "fsevents")
PYPROJECT_WATCHDOG_BASELINE = 2


def test_swarm_dir_file_set_unchanged() -> None:
    files = {p.name for p in SWARM_DIR.iterdir() if p.is_file()}
    assert files == KNOWN_SWARM_FILES, (
        f"VBUS-08 violated: apps/voss-app/src/swarm/ file set changed to "
        f"{sorted(files)} (baseline {sorted(KNOWN_SWARM_FILES)}); "
        f"A13 swarm code must stay untouched in V17"
    )
    # Runtime baseline: every known file present, readable, non-empty.
    baseline = {
        name: hashlib.sha256((SWARM_DIR / name).read_bytes()).hexdigest()
        for name in KNOWN_SWARM_FILES
    }
    assert all(baseline.values()), baseline


def test_no_fs_watcher_dependency_added() -> None:
    # pyproject: filter comment lines BEFORE matching — never count raw text.
    pyproject_lines = [
        line
        for line in (REPO_ROOT / "pyproject.toml").read_text().splitlines()
        if not line.strip().startswith("#")
    ]
    watchdog_hits = [l for l in pyproject_lines if "watchdog" in l]
    assert len(watchdog_hits) == PYPROJECT_WATCHDOG_BASELINE, (
        f"watchdog mentions in pyproject changed from the pre-V17 baseline "
        f"({PYPROJECT_WATCHDOG_BASELINE}): {watchdog_hits!r}"
    )
    for token in WATCHER_TOKENS:
        if token == "watchdog":
            continue
        hits = [l for l in pyproject_lines if token in l]
        assert not hits, f"fs-watcher dep {token!r} added to pyproject: {hits!r}"

    # apps/voss-app/package.json: no watcher in any dependency block.
    pkg = json.loads(
        (REPO_ROOT / "apps" / "voss-app" / "package.json").read_text()
    )
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        deps.update(pkg.get(key, {}))
    hits = sorted(
        d for d in deps if any(t in d.lower() for t in WATCHER_TOKENS)
    )
    assert not hits, f"fs-watcher dep added to apps/voss-app/package.json: {hits}"


def test_no_new_v17_solid_components() -> None:
    # Documented allowlist check, not a blanket count: concurrent A-track
    # work may add unrelated components. V17 ships CLI + events only — no
    # Solid component named for the coordination surface may exist.
    forbidden_prefixes = ("claims", "bus", "coordination")
    src = REPO_ROOT / "apps" / "voss-app" / "src"
    offenders = sorted(
        str(p.relative_to(REPO_ROOT))
        for p in src.rglob("*")
        if p.suffix in (".tsx", ".jsx")
        and p.name.lower().startswith(forbidden_prefixes)
    )
    assert not offenders, (
        f"VBUS-08 violated: V17-named Solid components found: {offenders}"
    )
