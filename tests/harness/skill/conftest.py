"""Shared fixtures for skill tests in the harness package.

Exposes FakeProvider, seed_git_repo, Plan, PermissionGate, PlainRenderer, and make_toolset.
Sets up XDG_STATE_HOME and XDG_CONFIG_HOME isolation fixtures.
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
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return tmp_path


def seed_git_repo(root: Path) -> Path:
    """Build a one-commit git tree at `root` in place."""
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


@pytest.fixture
def signed_fixture_bundle() -> Path:
    # Repo-relative: tests/harness/skill/conftest.py -> repo root is parents[3].
    return Path(__file__).resolve().parents[3] / "examples" / "skills" / "voss-git-summary"


class FakeProvider:
    """Returns a canned Plan via stream() on iter 0; synthetic done plan on iter 1+."""

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
