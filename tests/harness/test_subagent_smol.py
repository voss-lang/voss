"""smol-role wiring for subagents: subagent_run uses the smol chain when
configured, else the parent provider/model."""
from __future__ import annotations

import asyncio
from pathlib import Path

from voss.harness import roles, subagents
from voss.harness.subagents import attach_subagent_tool


def _attach(tools: dict) -> None:
    attach_subagent_tool(
        tools,
        registry=object(),
        cwd=Path("."),
        renderer=object(),
        provider="parent-provider",
        model=lambda: "default-model",
        gate=object(),
        cognition=None,
    )


def test_subagent_uses_smol_when_configured(monkeypatch) -> None:
    captured: dict = {}

    async def fake_run_subagent(**kw):
        captured.update(kw)
        return "ok"

    monkeypatch.setattr(subagents, "run_subagent", fake_run_subagent)
    monkeypatch.setattr(
        roles,
        "build_role_provider",
        lambda role, **kw: ("smol-provider", "smol-model") if role == "smol" else None,
    )
    tools: dict = {}
    _attach(tools)
    asyncio.run(tools["subagent_run"].invoke(agent="x", task="t"))
    assert captured["provider"] == "smol-provider"
    assert captured["model"] == "smol-model"


def test_subagent_falls_back_to_parent_when_no_smol(monkeypatch) -> None:
    captured: dict = {}

    async def fake_run_subagent(**kw):
        captured.update(kw)
        return "ok"

    monkeypatch.setattr(subagents, "run_subagent", fake_run_subagent)
    monkeypatch.setattr(roles, "build_role_provider", lambda role, **kw: None)
    tools: dict = {}
    _attach(tools)
    asyncio.run(tools["subagent_run"].invoke(agent="x", task="t"))
    assert captured["provider"] == "parent-provider"
    assert captured["model"] == "default-model"
