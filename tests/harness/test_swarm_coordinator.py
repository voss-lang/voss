"""Unit tests for the swarm coordinator (R3 goal decomposition).

Uses a stub provider whose `.complete` returns a canned Decomposition on
`resp.parsed` — NO network/LLM calls. Verifies decompose returns + clamps the
subtasks, that a None `.parsed` raises, and that to_tasks builds Tasks and rejects
an overlapping decomposition via VSWARM-06 overlap validation.
"""
from __future__ import annotations

import pytest

from voss.harness.swarm_coordinator import (
    Decomposition,
    DecompositionError,
    SubtaskSpec,
    decompose,
    to_tasks,
)
from voss.harness.swarm_store import OwnershipOverlapError


class _StubResponse:
    """Minimal stand-in for ProviderResponse — only `.parsed` is read by decompose."""

    def __init__(self, parsed):
        self.parsed = parsed
        self.text = ""


class _StubProvider:
    """Provider whose `complete` returns a pre-canned Decomposition. Records the
    last call so tests can assert the forced schema was passed."""

    def __init__(self, parsed):
        self._parsed = parsed
        self.last_kwargs: dict | None = None

    async def complete(self, **kwargs):
        self.last_kwargs = kwargs
        return _StubResponse(self._parsed)


@pytest.mark.asyncio
async def test_decompose_returns_subtasks() -> None:
    canned = Decomposition(
        subtasks=[
            SubtaskSpec(goal="refactor", owned_files=["src/a.py"], agent="claude"),
            SubtaskSpec(goal="tests", owned_files=["tests/test_a.py"], agent="codex"),
        ]
    )
    provider = _StubProvider(canned)

    out = await decompose(provider, goal="do it", model="opus", cwd="/repo")

    assert [s.goal for s in out] == ["refactor", "tests"]
    assert [s.agent for s in out] == ["claude", "codex"]
    # decompose forced structured output on the Decomposition schema.
    assert provider.last_kwargs["response_format"] is Decomposition
    assert provider.last_kwargs["model"] == "opus"


@pytest.mark.asyncio
async def test_decompose_clamps_to_max() -> None:
    canned = Decomposition(
        subtasks=[SubtaskSpec(goal=f"t{i}", owned_files=[f"f{i}.py"]) for i in range(10)]
    )
    out = await decompose(provider := _StubProvider(canned), goal="g", model="m", cwd=".", max_tasks=4)
    assert len(out) == 4
    assert provider.last_kwargs is not None


@pytest.mark.asyncio
async def test_decompose_none_parsed_raises() -> None:
    with pytest.raises(DecompositionError):
        await decompose(_StubProvider(None), goal="g", model="m", cwd=".")


def test_to_tasks_builds_tasks() -> None:
    subtasks = [
        SubtaskSpec(goal="A", owned_files=["src/a.py"]),
        SubtaskSpec(goal="B", owned_files=["src/b.py"]),
    ]
    tasks = to_tasks(subtasks)

    assert [t.goal for t in tasks] == ["A", "B"]
    assert all(t.id for t in tasks)
    assert len({t.id for t in tasks}) == 2  # ids are unique


def test_to_tasks_rejects_overlap() -> None:
    # Two subtasks claim src/shared.py with no depends_on → must be rejected up front.
    subtasks = [
        SubtaskSpec(goal="A", owned_files=["src/shared.py"]),
        SubtaskSpec(goal="B", owned_files=["src/shared.py"]),
    ]
    with pytest.raises(OwnershipOverlapError):
        to_tasks(subtasks)


def test_to_tasks_allows_overlap_when_ordered() -> None:
    # depends_on ordering lets two subtasks legitimately share a file.
    def make_id(spec, idx):
        return f"task-{idx}"

    subtasks = [
        SubtaskSpec(goal="A", owned_files=["src/shared.py"]),
        SubtaskSpec(goal="B", owned_files=["src/shared.py"], depends_on=["task-0"]),
    ]
    tasks = to_tasks(subtasks, make_id=make_id)
    assert tasks[1].depends_on == ["task-0"]
