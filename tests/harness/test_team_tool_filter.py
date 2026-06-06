"""OTEAM-07: filter_toolset_for_role hybrid aliases + exact tool names."""

from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.subagents import SubagentSpec
from voss.harness.tools import make_toolset
from voss.harness.team import filter_toolset_for_role, TOOL_GROUP_ALIASES


@pytest.fixture
def full_toolset(tmp_path: Path):
    return make_toolset(tmp_path, renderer=None, net=None)


def test_filter_none_returns_full_copy(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=None)
    out = filter_toolset_for_role(spec, full_toolset)
    assert set(out.keys()) == set(full_toolset.keys())
    assert out is not full_toolset


def test_filter_fs_alias(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"fs"}))
    out = filter_toolset_for_role(spec, full_toolset)
    for n in ("fs_read", "fs_write", "fs_edit", "fs_glob", "fs_grep"):
        assert n in out
    assert "shell_run" not in out
    assert "web_fetch" not in out
    assert "web_search" not in out


def test_filter_net_alias(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"net"}))
    out = filter_toolset_for_role(spec, full_toolset)
    assert "web_fetch" in out
    assert "web_search" in out
    assert "fs_read" not in out


def test_filter_code_alias(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"code"}))
    out = filter_toolset_for_role(spec, full_toolset)
    assert set(out.keys()) == {
        "code_search",
        "find_definition",
        "find_references",
        "code_refresh",
    }


def test_filter_excludes_net_when_net_absent(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"fs", "test"}))
    out = filter_toolset_for_role(spec, full_toolset)
    assert "shell_run" in out
    assert "web_fetch" not in out
    assert "web_search" not in out


def test_filter_exact_name_hybrid(full_toolset) -> None:
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"fs_read"}))
    out = filter_toolset_for_role(spec, full_toolset)
    assert set(out.keys()) == {"fs_read"}


def test_filter_unknown_alias_silently_drops(full_toolset) -> None:
    spec = SubagentSpec(
        "r", "d", "rp", tools=frozenset({"nonexistent_alias"}),
    )
    out = filter_toolset_for_role(spec, full_toolset)
    assert out == {}


def test_filter_does_not_mutate_base(full_toolset) -> None:
    keys_before = set(full_toolset.keys())
    spec = SubagentSpec("r", "d", "rp", tools=frozenset({"fs"}))
    filter_toolset_for_role(spec, full_toolset)
    assert set(full_toolset.keys()) == keys_before


def test_tool_group_aliases_cover_expected_keys() -> None:
    assert "net" in TOOL_GROUP_ALIASES
    assert TOOL_GROUP_ALIASES["net"] == frozenset({"web_fetch", "web_search"})
    assert TOOL_GROUP_ALIASES["code"] == frozenset(
        {"code_search", "find_definition", "find_references", "code_refresh"}
    )
