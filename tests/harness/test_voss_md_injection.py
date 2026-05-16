"""M8-01 VOSS.md injection into run_turn sys_prompt (Req 1, D-08).

Drives `run_turn` with a FakeProvider that captures the system message it
receives, then asserts the VOSS.md head block lands (or doesn't) per file
presence.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from voss_runtime.providers.base import ProviderResponse

from voss.harness.agent import Plan, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset


class CapturingProvider:
    """Records every provider call (stream or complete) so tests can inspect sys_prompt."""

    def __init__(self, plan: Plan, cost: float = 0.0):
        self.plan = plan
        self.cost = cost
        self.calls: list[dict] = []

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
    ) -> ProviderResponse:
        self.calls.append({"messages": messages, "schema": response_format})
        return ProviderResponse(
            text=self.plan.model_dump_json(),
            model=model,
            prompt_tokens=10,
            completion_tokens=10,
            cost_usd=self.cost,
            raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )

    def stream(self, **kwargs):
        self.calls.append(
            {
                "messages": kwargs.get("messages"),
                "schema": kwargs.get("response_format"),
            }
        )

        async def _gen():
            yield TextDelta(text="…")
            yield ParsedPlan(plan=self.plan)
            yield Usage(prompt_tokens=10, completion_tokens=10, cost_usd=self.cost)
            yield Done(stop_reason="end_turn")

        return _gen()

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


def _system_text(provider: CapturingProvider) -> str:
    """Concatenate every system message across recorded calls."""
    out: list[str] = []
    for call in provider.calls:
        for msg in call["messages"]:
            if msg.get("role") == "system":
                out.append(msg.get("content", ""))
    return "\n".join(out)


def _trivial_plan() -> Plan:
    return Plan(
        rationale="noop",
        steps=[],
        confidence=0.30,
        open_question="ok?",
        # T1-05: terminating-iter signal needs non-empty final_when_done.
        final_when_done="(tentative)",
    )


def test_voss_md_loaded_in_system_context(tmp_voss_repo: Path) -> None:
    (tmp_voss_repo / "VOSS.md").write_text("alpha-marker-XYZ\n")
    provider = CapturingProvider(_trivial_plan())

    asyncio.run(
        run_turn(
            "ping",
            tools=make_toolset(tmp_voss_repo),
            cwd=tmp_voss_repo,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=PermissionGate(auto_yes=True),
            voss_md_text=(tmp_voss_repo / "VOSS.md").read_text(),
        )
    )

    sys_text = _system_text(provider)
    assert "# VOSS.md\nalpha-marker-XYZ" in sys_text


def test_missing_file_degrades_silently(tmp_voss_repo: Path, capsys) -> None:
    from voss.harness import voss_md

    voss_md_text = voss_md.read_and_inject(tmp_voss_repo)
    assert voss_md_text is None

    provider = CapturingProvider(_trivial_plan())
    asyncio.run(
        run_turn(
            "ping",
            tools=make_toolset(tmp_voss_repo),
            cwd=tmp_voss_repo,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=PermissionGate(auto_yes=True),
            voss_md_text=voss_md_text,
        )
    )

    sys_text = _system_text(provider)
    assert "# VOSS.md" not in sys_text
    captured = capsys.readouterr()
    assert "VOSS.md" not in captured.err
