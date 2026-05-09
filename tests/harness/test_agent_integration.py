"""End-to-end agent loop tests with a fake provider.

Verifies plan -> tool exec -> final assembly without API keys.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from voss_runtime import EpisodicMemory
from voss_runtime.providers.base import ProviderResponse

from voss.harness.agent import Plan, ToolCall, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset


class FakeProvider:
    """Returns a canned Plan once, then echoes."""

    def __init__(self, plan: Plan, cost: float = 0.001):
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
        self.calls.append({"model": model, "messages": messages, "schema": response_format})
        text = self.plan.model_dump_json()
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=50,
            completion_tokens=50,
            cost_usd=self.cost,
            raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("def hello():\n    return 'world'\n")
    (tmp_path / "README.md").write_text("# project\n")
    return tmp_path


def _run(coro):
    return asyncio.run(coro)


class TestRunTurn:
    def test_high_confidence_plan_executes_tools(self, project: Path) -> None:
        plan = Plan(
            rationale="list source files",
            steps=[ToolCall(name="fs_glob", args={"pattern": "**/*.py"})],
            confidence=0.92,
            final_when_done="found: {{step_0}}",
        )
        provider = FakeProvider(plan)
        result = _run(
            run_turn(
                "list python files",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=provider,
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert result.confidence == 0.92
        assert "src/a.py" in result.final
        assert len(result.tool_results) == 1
        assert result.cost_usd == pytest.approx(0.001)

    def test_low_confidence_returns_clarify(self, project: Path) -> None:
        plan = Plan(
            rationale="task is ambiguous",
            steps=[],
            confidence=0.30,
            open_question="which file did you mean?",
        )
        provider = FakeProvider(plan)
        result = _run(
            run_turn(
                "fix it",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=provider,
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert result.tool_results == []
        assert "which file" in result.final

    def test_unknown_tool_in_plan_surfaced_not_crashed(self, project: Path) -> None:
        plan = Plan(
            rationale="bogus call",
            steps=[ToolCall(name="does_not_exist", args={})],
            confidence=0.95,
            final_when_done="result: {{step_0}}",
        )
        provider = FakeProvider(plan)
        result = _run(
            run_turn(
                "do nothing",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=provider,
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert "unknown tool" in result.tool_results[0]

    def test_history_records_user_and_assistant(self, project: Path) -> None:
        plan = Plan(
            rationale="trivial",
            steps=[],
            confidence=0.99,
            final_when_done="hello",
        )
        history = EpisodicMemory(capacity=10)
        _run(
            run_turn(
                "say hello",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=FakeProvider(plan),
                permissions=PermissionGate(auto_yes=True),
                history=history,
            )
        )
        turns = history.last(10)
        assert any(t["role"] == "user" and "hello" in t["content"] for t in turns)
        assert any(t["role"] == "assistant" and t["content"] == "hello" for t in turns)

    def test_permission_denies_shell_in_plan_mode(self, project: Path) -> None:
        plan = Plan(
            rationale="run pytest",
            steps=[ToolCall(name="shell_run", args={"cmd": "ls"})],
            confidence=0.95,
            final_when_done="{{step_0}}",
        )
        gate = PermissionGate(mode="plan", auto_yes=False)
        # non-tty stdin in pytest -> auto-deny without prompt
        result = _run(
            run_turn(
                "list files",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=FakeProvider(plan),
                permissions=gate,
            )
        )
        assert "denied" in result.tool_results[0]

    def test_step_placeholder_substitution(self, project: Path) -> None:
        plan = Plan(
            rationale="read then report",
            steps=[
                ToolCall(name="fs_read", args={"path": "README.md"}),
                ToolCall(name="fs_glob", args={"pattern": "**/*.py"}),
            ],
            confidence=0.90,
            final_when_done="readme: {{step_0}}\nfiles: {{step_1}}",
        )
        result = _run(
            run_turn(
                "report",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=FakeProvider(plan),
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert "# project" in result.final
        assert "src/a.py" in result.final


class TestEditTools:
    def test_fs_write_creates_file(self, project: Path) -> None:
        plan = Plan(
            rationale="write greeting",
            steps=[ToolCall(name="fs_write", args={"path": "hi.txt", "content": "hello"})],
            confidence=0.99,
            final_when_done="{{step_0}}",
        )
        _run(
            run_turn(
                "write hi.txt",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=FakeProvider(plan),
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert (project / "hi.txt").read_text() == "hello"

    def test_fs_edit_replaces_unique_text(self, project: Path) -> None:
        plan = Plan(
            rationale="rename function",
            steps=[
                ToolCall(
                    name="fs_edit",
                    args={"path": "src/a.py", "old": "def hello", "new": "def greet"},
                )
            ],
            confidence=0.95,
            final_when_done="{{step_0}}",
        )
        _run(
            run_turn(
                "rename hello to greet",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=FakeProvider(plan),
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert "def greet()" in (project / "src" / "a.py").read_text()

    def test_fs_edit_rejects_non_unique(self, project: Path) -> None:
        (project / "src" / "b.py").write_text("x = 1\nx = 1\n")
        plan = Plan(
            rationale="ambiguous edit",
            steps=[
                ToolCall(
                    name="fs_edit",
                    args={"path": "src/b.py", "old": "x = 1", "new": "x = 2"},
                )
            ],
            confidence=0.9,
            final_when_done="{{step_0}}",
        )
        result = _run(
            run_turn(
                "edit",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=FakeProvider(plan),
                permissions=PermissionGate(auto_yes=True),
            )
        )
        assert "matches 2" in result.tool_results[0] or "must be unique" in result.tool_results[0]
