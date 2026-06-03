"""H5.4 — custom agents from .voss/agents/*.md."""

from __future__ import annotations

from voss.harness.subagents import (
    SubagentRegistry,
    load_agent_specs,
    register_agent_files,
)


def _write_agent(tmp_path, name, text):
    d = tmp_path / ".voss" / "agents"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text)


def test_load_full_frontmatter(tmp_path):
    _write_agent(
        tmp_path,
        "explore.md",
        """---
description: read-only explorer
mode: plan
model: claude-sonnet-4-5
tools: [fs_read, fs_grep]
confidence_threshold: 0.8
budget: 5000
net: false
---
You are a careful explorer. Do not edit files.
""",
    )
    specs = load_agent_specs(tmp_path)
    assert len(specs) == 1
    s = specs[0]
    assert s.id == "explore"
    assert s.description == "read-only explorer"
    assert s.mode == "plan"
    assert s.model == "claude-sonnet-4-5"
    assert s.tools == frozenset({"fs_read", "fs_grep"})
    assert s.confidence_threshold == 0.8
    assert s.budget == 5000
    assert s.net is False
    assert "careful explorer" in s.role_prompt


def test_invalid_mode_falls_back_to_none(tmp_path):
    _write_agent(tmp_path, "x.md", "---\ndescription: d\nmode: bogus\n---\nbody")
    s = load_agent_specs(tmp_path)[0]
    assert s.mode is None


def test_no_agents_dir_is_empty(tmp_path):
    assert load_agent_specs(tmp_path) == []


def test_register_agent_files(tmp_path):
    _write_agent(tmp_path, "a.md", "---\ndescription: x\n---\nbody")
    reg = SubagentRegistry()
    n = register_agent_files(reg, tmp_path)
    assert n == 1
    assert reg.get("a") is not None
