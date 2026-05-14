"""M9-04 runtime-surface hash regression.

Pins voss/harness/recorder.py + voss_runtime/{probable,budget,agent}.py to
their pre-M9-04 byte content. Any change requires either revert or running
the test with `UPDATE_BASELINE=1` AND documenting the change in the M9-04
SUMMARY. subagents.py is INTENTIONALLY excluded — the SPAWN_TOOL_NAME
constant is the M9-04 W3 resolution.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = Path(__file__).resolve().parent / "baseline" / "runtime_surface.sha256"
BASELINE_FILES: tuple[str, ...] = (
    "voss/harness/recorder.py",
    "voss_runtime/probable.py",
    "voss_runtime/budget.py",
    "voss_runtime/agent.py",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_baseline() -> dict[str, str]:
    out: dict[str, str] = {}
    if not BASELINE_PATH.exists():
        return out
    for line in BASELINE_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        h, _, fname = line.partition("  ")
        out[fname.strip()] = h.strip()
    return out


def test_runtime_surface_files_unchanged() -> None:
    """Each baseline file's SHA-256 must match the committed baseline."""
    if os.environ.get("UPDATE_BASELINE") == "1":
        lines = [f"{_hash(REPO_ROOT / f)}  {f}" for f in BASELINE_FILES]
        BASELINE_PATH.write_text("\n".join(lines) + "\n")
        pytest.skip(f"baseline updated: {BASELINE_PATH}")

    baseline = _read_baseline()
    assert baseline, f"missing baseline file: {BASELINE_PATH}"
    assert set(baseline) == set(BASELINE_FILES), (
        f"baseline file list drift: {set(baseline) ^ set(BASELINE_FILES)}"
    )
    drift = []
    for fname in BASELINE_FILES:
        actual = _hash(REPO_ROOT / fname)
        if actual != baseline[fname]:
            drift.append(fname)
    assert not drift, (
        f"runtime-surface drift detected in {drift}. Revert the change "
        f"or rerun with UPDATE_BASELINE=1 and document in M9-04 summary."
    )


def test_subagents_not_in_baseline_set() -> None:
    """W3 resolution: subagents.py is OUT of baseline scope (constant-add allowed)."""
    assert "voss/harness/subagents.py" not in BASELINE_FILES


def test_spawn_tool_name_constant_present() -> None:
    from voss.harness.subagents import SPAWN_TOOL_NAME

    assert isinstance(SPAWN_TOOL_NAME, str)
    assert SPAWN_TOOL_NAME
