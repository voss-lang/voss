"""Shared fixtures for skill tests (T7 seam).

`isolated_state` is autouse — every skill test gets an XDG_STATE_HOME
sandbox pointed at its own tmp_path so session JSON / permission state never
leaks into the real `~/.local/state` or the working tree.

`seed_git_repo(root)` is a module-level helper that builds a one-commit git
tree at an arbitrary `root` WITHOUT clobbering pre-seeded fixture files (it
only writes a README when none exists). The `git_repo` fixture delegates to
it with `tmp_path`, matching `tests/harness/conftest.py:34-42`.

`FakeProvider` is copied verbatim from
`tests/harness/test_agent_integration.py:30-102` (post-T1-05 contract:
`run_turn` drives `provider.stream()`, not `complete()`). It is a
module-level class, not a fixture — downstream tests construct it inline with
their own `Plan` objects. The supporting harness imports are re-exported here
so downstream test files can import them from one place.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from voss_runtime.providers.base import ProviderResponse

from voss.harness.agent import Plan, ToolCall, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset

__all__ = [
    "FakeProvider",
    "seed_git_repo",
    "Plan",
    "ToolCall",
    "run_turn",
    "PermissionGate",
    "PlainRenderer",
    "make_toolset",
    "Done",
    "ParsedPlan",
    "TextDelta",
    "Usage",
    "ProviderResponse",
]


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path


def seed_git_repo(root: Path) -> Path:
    """Build a one-commit git tree at `root` in place.

    Operates strictly inside `root` (every subprocess call uses `cwd=root`);
    never touches the real project repo. Does NOT clobber pre-seeded fixture
    files — a README is written only when one is absent.
    """
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=root, check=True, capture_output=True
    )
    if not (root / "README.md").exists():
        (root / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True
    )
    return root


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    return seed_git_repo(tmp_path)


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
