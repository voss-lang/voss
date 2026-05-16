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
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset


class FakeProvider:
    """Returns a canned Plan via stream() on iter 0; synthetic done plan on iter 1+.

    T1-05 routes planning through provider.stream(). The first stream call
    emits the canned plan. If the canned plan is already "done"
    (steps=[] + final_when_done set), the loop exits there. Otherwise the
    canned plan's steps execute and a follow-up stream() call returns a
    synthetic "done" Plan derived from the canned one, so the loop closes
    cleanly without spinning to max-iter.

    `calls` records every messages payload (stream + complete) so existing
    assertions on provider.calls[0]["messages"] still work.
    """

    def __init__(self, plan: Plan, cost: float = 0.001):
        self.plan = plan
        self.cost = cost
        self.calls: list[dict] = []
        self._stream_index = 0

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

    def stream(self, **kwargs):
        self.calls.append(
            {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "schema": kwargs.get("response_format"),
            }
        )
        idx = self._stream_index
        self._stream_index += 1
        if idx == 0:
            plan_to_emit = self.plan
        else:
            plan_to_emit = Plan(
                rationale="(synthetic done plan from FakeProvider)",
                steps=[],
                confidence=self.plan.confidence,
                final_when_done=self.plan.final_when_done or "(stub final)",
            )

        async def _gen():
            yield TextDelta(text="…")
            yield ParsedPlan(plan=plan_to_emit)
            yield Usage(prompt_tokens=50, completion_tokens=50, cost_usd=self.cost)
            yield Done(stop_reason="end_turn")

        return _gen()

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


class FakeProviderWithSemantics(FakeProvider):
    """Returns parsed Plan first, then parsed RunSemantics on subsequent calls."""

    def __init__(self, plan, semantics, cost: float = 0.001):
        super().__init__(plan, cost=cost)
        self.semantics = semantics

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
        self.calls.append({"model": model, "messages": messages, "schema": response_format})
        # Decide which canned response to return based on the requested schema.
        from voss.harness.agent import Plan as _Plan
        from voss.harness.agent import RunSemantics as _RunSemantics

        if response_format is _Plan:
            parsed = self.plan
            text = self.plan.model_dump_json()
        elif response_format is _RunSemantics:
            parsed = self.semantics
            text = self.semantics.model_dump_json()
        else:
            parsed = None
            text = ""

        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=50,
            completion_tokens=50,
            cost_usd=self.cost,
            raw={"fake": True},
            parsed=parsed,
        )


class FakeProviderFailingSemantics(FakeProvider):
    """First call returns Plan; second call raises RuntimeError."""

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
        self.calls.append({"model": model, "schema": response_format})
        from voss.harness.agent import Plan as _Plan
        from voss.harness.agent import RunSemantics as _RunSemantics

        if response_format is _Plan:
            return ProviderResponse(
                text=self.plan.model_dump_json(),
                model=model,
                prompt_tokens=50,
                completion_tokens=50,
                cost_usd=self.cost,
                raw={"fake": True},
                parsed=self.plan,
            )
        if response_format is _RunSemantics:
            raise RuntimeError("simulated record_run provider failure")
        return ProviderResponse(
            text="", model=model, prompt_tokens=0, completion_tokens=0,
            cost_usd=0.0, raw={}, parsed=None,
        )


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
        # T1-05: placeholder substitution removed. final_when_done is no
        # longer a template — the loop calls back to the model after tools
        # run and the next iter's plan supplies the realized final string.
        plan = Plan(
            rationale="list source files",
            steps=[ToolCall(name="fs_glob", args={"pattern": "**/*.py"})],
            confidence=0.92,
            final_when_done="found python files",
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
        # Tool ran and produced src/a.py somewhere in the per-iter results.
        assert any("src/a.py" in tr for tr in result.tool_results)
        assert len(result.tool_results) == 1

    def test_low_confidence_returns_clarify(self, project: Path) -> None:
        # T1-05: confidence gate fires only on the terminating iter.
        # final_when_done must be non-empty for _is_done_plan to recognize
        # this as terminating; the open_question is what the user sees.
        plan = Plan(
            rationale="task is ambiguous",
            steps=[],
            confidence=0.30,
            open_question="which file did you mean?",
            final_when_done="(tentative)",
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
            final_when_done="attempted bogus tool",
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
            final_when_done="ran shell",
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

    def test_tool_results_surface_in_run_record(self, project: Path) -> None:
        # T1-05 replaced the pre-T1 `{{step_N}}` placeholder substitution
        # feature with the iteration loop's model-driven re-plan. Step
        # results land in the iteration record under run.iterations[0]
        # (not in final_when_done).
        plan = Plan(
            rationale="read then report",
            steps=[
                ToolCall(name="fs_read", args={"path": "README.md"}),
                ToolCall(name="fs_glob", args={"pattern": "**/*.py"}),
            ],
            confidence=0.90,
            final_when_done="reported",
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
        flat = "\n".join(result.tool_results)
        assert "# project" in flat
        assert "src/a.py" in flat
        # Step results are also visible in the structured iteration record.
        first_iter = result.run.iterations[0]
        assert len(first_iter.tool_results) == 2


class TestEditTools:
    def test_fs_write_creates_file(self, project: Path) -> None:
        plan = Plan(
            rationale="write greeting",
            steps=[ToolCall(name="fs_write", args={"path": "hi.txt", "content": "hello"})],
            confidence=0.99,
            final_when_done="step ran",
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
            final_when_done="step ran",
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
            final_when_done="step ran",
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


class TestRecordRunIntegration:
    def test_record_run_populates_semantic_fields(self, project: Path) -> None:
        from voss.harness.agent import RunSemantics

        plan = Plan(
            rationale="read the readme",
            steps=[ToolCall(name="fs_read", args={"path": "README.md"})],
            confidence=0.95,
            final_when_done="read readme",
        )
        semantics = RunSemantics(
            goal="summarize repo",
            decisions=[
                {"title": "use markdown", "body": "clear format", "confidence": 0.9}
            ],
            assumptions=["repo is small"],
            risks=[],
            follow_ups=["add tests"],
        )
        provider = FakeProviderWithSemantics(plan, semantics)
        result = _run(
            run_turn(
                "summarize",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=provider,
                permissions=PermissionGate(auto_yes=True),
                session_id="testsess1",
            )
        )
        assert result.run is not None
        assert result.run.goal == "summarize repo"
        assert result.run.decisions and result.run.decisions[0]["title"] == "use markdown"
        assert result.run.assumptions == ["repo is small"]
        assert result.run.follow_ups == ["add tests"]
        # Mechanical capture still works alongside semantics.
        assert "README.md" in result.run.inspected

    def test_record_run_failure_persists_mechanical(self, project: Path) -> None:
        plan = Plan(
            rationale="read the readme",
            steps=[ToolCall(name="fs_read", args={"path": "README.md"})],
            confidence=0.95,
            final_when_done="done",
        )
        provider = FakeProviderFailingSemantics(plan)
        result = _run(
            run_turn(
                "summarize",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=provider,
                permissions=PermissionGate(auto_yes=True),
                session_id="testsess2",
            )
        )
        assert result.run is not None
        assert result.run.goal == "(record_run failed)"
        assert "README.md" in result.run.inspected
        # plan dict still stored as fallback.
        assert result.run.plan is not None

    def test_decisions_written_to_disk(self, project: Path) -> None:
        """When decisions are present, .voss/decisions/*.md files appear."""
        from voss.harness.agent import RunSemantics

        plan = Plan(
            rationale="trivial",
            steps=[],
            confidence=0.95,
            final_when_done="ok",
        )
        semantics = RunSemantics(
            goal="trial",
            decisions=[
                {"title": "pick strict schema", "body": "fail loud", "confidence": 0.85}
            ],
        )
        provider = FakeProviderWithSemantics(plan, semantics)
        _run(
            run_turn(
                "go",
                tools=make_toolset(project),
                cwd=project,
                renderer=PlainRenderer(),
                provider=provider,
                permissions=PermissionGate(auto_yes=True),
                session_id="testsess3",
            )
        )
        decisions_dir = project / ".voss" / "decisions"
        assert decisions_dir.exists()
        files = list(decisions_dir.glob("*.md"))
        assert files, "no decision markdown files written"
        text = files[0].read_text()
        assert "related_session: testsess3" in text
        assert "pick strict schema" in text


def test_turn_injects_cognition(tmp_path: Path) -> None:
    """When cognition.load returns initialized=True, run_turn prepends
    architecture.md + constraints bullets BEFORE PLAN_SYSTEM."""
    from voss.harness import cognition as cognition_mod

    voss = tmp_path / ".voss"
    voss.mkdir()
    (voss / "architecture.md").write_text(
        "---\n"
        "git_head: abc123\n"
        "analyzed_at: 2026-05-10T00:00:00+00:00\n"
        "file_count: 1\n"
        "analyzer_version: 1\n"
        "---\n"
        "# Arch\n\nMODULE MAP HERE\n"
    )
    (voss / "constraints.yml").write_text(
        "rules:\n  - forbid: [eval]\n"
    )

    bundle = cognition_mod.load(tmp_path)
    assert bundle.initialized

    plan = Plan(
        rationale="trivial",
        steps=[],
        confidence=0.99,
        final_when_done="hello",
    )
    provider = FakeProvider(plan)
    _run(
        run_turn(
            "do thing",
            tools=make_toolset(tmp_path),
            cwd=tmp_path,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=PermissionGate(auto_yes=True),
            cognition=bundle,
        )
    )
    sys_msg = provider.calls[0]["messages"][0]
    assert sys_msg["role"] == "system"
    content = sys_msg["content"]
    arch_idx = content.find("MODULE MAP HERE")
    constraint_idx = content.find("forbid: eval")
    plan_idx = content.find("You are Voss")
    assert arch_idx != -1, "architecture body missing from system prompt"
    assert constraint_idx != -1, "constraints bullet missing from system prompt"
    assert plan_idx != -1, "PLAN_SYSTEM missing"
    assert arch_idx < plan_idx, "architecture must precede PLAN_SYSTEM"
    assert constraint_idx < plan_idx, "constraints must precede PLAN_SYSTEM"


def test_resume_injects_prior_run_context(tmp_path: Path) -> None:
    """run_turn(..., prior_context=<dict>) inlines a 'Prior context' block."""
    plan = Plan(
        rationale="trivial",
        steps=[],
        confidence=0.99,
        final_when_done="hello",
    )
    provider = FakeProvider(plan)
    prior = {
        "goal": "prev goal",
        "plan": {"rationale": "prev rationale"},
        "decisions": [
            {"title": "chose X", "body": "b", "confidence": 0.9}
        ],
        "follow_ups": ["next: y"],
        "risks": ["r1"],
    }
    _run(
        run_turn(
            "continue",
            tools=make_toolset(tmp_path),
            cwd=tmp_path,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=PermissionGate(auto_yes=True),
            prior_context=prior,
        )
    )
    sys_msg = provider.calls[0]["messages"][0]
    content = sys_msg["content"]
    assert "Prior context" in content
    assert "prev goal" in content
    assert "chose X" in content
    assert "next: y" in content
    assert "r1" in content
