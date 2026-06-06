"""V1 capability-registry binding seam + exact-subset tool filtering (VTEAM-07).

The seam is comment-only — `filter_toolset_for_role` behavior is unchanged.
These tests assert (a) exact-subset filtering with net opt-in, and (b) the
greppable V1-capability seam marker is present in team.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from voss.harness.subagents import SubagentSpec
from voss.harness.tools import make_toolset
from voss.harness.team import filter_toolset_for_role

_TEAM_PY = Path(__file__).resolve().parents[2] / "voss" / "harness" / "team.py"


@pytest.fixture
def full_toolset(tmp_path: Path):
    return make_toolset(tmp_path, renderer=None, net=None)


def test_declared_subset_excludes_net(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"fs", "code"}))
    out = filter_toolset_for_role(spec, full_toolset)
    # fs+code expansion present; net tools absent (not declared).
    assert "fs_read" in out
    assert "web_fetch" not in out
    assert "web_search" not in out
    # exact-subset: returned keys are a subset of the declared expansion.
    assert set(out.keys()) <= set(full_toolset.keys())


def test_net_included_only_when_declared(full_toolset) -> None:
    with_net = filter_toolset_for_role(
        SubagentSpec("r", "d", "rp", tools=frozenset({"fs", "net"})), full_toolset
    )
    assert "web_fetch" in with_net and "web_search" in with_net

    without_net = filter_toolset_for_role(
        SubagentSpec("r", "d", "rp", tools=frozenset({"fs"})), full_toolset
    )
    assert "web_fetch" not in without_net and "web_search" not in without_net


def test_v1_capability_seam_marker_present() -> None:
    src = _TEAM_PY.read_text(encoding="utf-8")
    assert re.search(r"V1.*capabilit", src), "V1-capability seam marker missing in team.py"
