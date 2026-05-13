from __future__ import annotations

import asyncio
from pathlib import Path

from click.testing import CliRunner

from voss_runtime.providers.base import ProviderResponse

from voss.harness.agent import Plan
from voss.harness.cli import main
from voss.harness.permissions import PermissionGate
from voss.harness.plugins import load_plugins, set_plugin_enabled
from voss.harness.render import PlainRenderer
from voss.harness.subagents import (
    attach_subagent_tool,
    default_subagent_registry,
    run_subagent,
)
from voss.harness.tools import make_toolset


class FakeProvider:
    async def complete(
        self,
        *,
        messages,
        model,
        response_format=None,
        tools=None,
        temperature=1.0,
        max_tokens=None,
        timeout=None,
    ):
        from voss.harness.agent import Plan as _Plan

        if response_format is _Plan:
            plan = Plan(
                rationale="subagent done",
                steps=[],
                confidence=0.99,
                final_when_done="child final",
            )
            return ProviderResponse(
                text=plan.model_dump_json(),
                model=model,
                prompt_tokens=1,
                completion_tokens=1,
                cost_usd=0.0,
                raw={},
                parsed=plan,
            )
        return ProviderResponse(
            text="{}",
            model=model,
            prompt_tokens=1,
            completion_tokens=1,
            cost_usd=0.0,
            raw={},
            parsed=None,
        )


def test_plugin_manifest_filters_unknown_refs_and_enablement(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    plugin_dir = tmp_path / ".voss" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "demo.toml").write_text(
        "\n".join(
            [
                'id = "demo"',
                'name = "Demo"',
                "enabled = false",
                'commands = ["/skills", "/nope"]',
                'skills = ["analyze", "missing"]',
                'agents = ["explorer", "ghost"]',
            ]
        )
    )

    set_plugin_enabled("demo", True)
    plugins = load_plugins(
        tmp_path,
        command_ids={"/skills"},
        skill_ids={"analyze"},
        agent_ids={"explorer"},
    )

    assert len(plugins) == 1
    plugin = plugins[0]
    assert plugin.enabled is True
    assert plugin.commands == ("/skills",)
    assert plugin.skills == ("analyze",)
    assert plugin.agents == ("explorer",)
    assert "unknown command: /nope" in plugin.warnings
    assert "unknown skill: missing" in plugin.warnings
    assert "unknown agent: ghost" in plugin.warnings


def test_extension_cli_lists_builtins() -> None:
    runner = CliRunner()
    skills = runner.invoke(main, ["skills"])
    agents = runner.invoke(main, ["agents"])

    assert skills.exit_code == 0
    assert "analyze" in skills.output
    assert agents.exit_code == 0
    assert "explorer" in agents.output
    assert "worker" in agents.output
    assert "reviewer" in agents.output


def test_subagent_tool_is_mutating_and_plan_denies(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path)
    gate = PermissionGate(mode="plan", auto_yes=True)
    attach_subagent_tool(
        tools,
        registry=default_subagent_registry(),
        cwd=tmp_path,
        renderer=PlainRenderer(),
        provider=FakeProvider(),
        model="test-model",
        gate=gate,
    )

    assert tools["subagent_run"].is_mutating is True
    allowed, reason = gate.check("subagent_run", {"agent": "explorer", "task": "x"}, is_mutating=True)
    assert allowed is False
    assert "plan" in reason


def test_run_subagent_with_fake_provider(tmp_path: Path) -> None:
    out = asyncio.run(
        run_subagent(
            agent_id="explorer",
            task="inspect",
            registry=default_subagent_registry(),
            cwd=tmp_path,
            renderer=PlainRenderer(),
            provider=FakeProvider(),
            model="test-model",
            gate=PermissionGate(auto_yes=True),
        )
    )
    assert out == "child final"
