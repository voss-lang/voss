"""Swarm coordinator — server-side goal decomposition (R3 / A13 D-03, D-16).

Under R3 the coordinator is a SINGLE server-side LLM call (not a long-lived
agent): given a natural-language goal it returns 2–6 parallelizable subtasks, each
with a DISJOINT `owned_files` set and a per-task agent choice (D-16: "coordinator
picks the CLI per subtask"). The host then writes one task file per subtask
(`swarm_filebus.write_task_file`) and seeds SwarmStore.

Disjoint ownership is what makes the rest of R3 work: it is the a-priori guard
(VSWARM-06 overlap validation) AND what guarantees the fan-in worktree merge is
conflict-free. So `to_tasks` re-runs `validate_no_overlap` across the whole
decomposition and rejects an overlapping plan up front — the LLM is asked for
disjoint files, but we never trust it to be correct.

This module depends only on the provider Protocol (structured output via
`response_format` → `resp.parsed`) and the pure pieces of swarm_store/swarm_agents,
so it has no server/web/fs coupling and is unit-testable with a stub provider.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable

from pydantic import BaseModel, Field

from .swarm_agents import NATIVE, known_agents
from .swarm_store import Task, validate_no_overlap


# ---------------------------------------------------------------------------
# Structured-output schema — what the coordinator LLM must return.
# ---------------------------------------------------------------------------
class SubtaskSpec(BaseModel):
    """One decomposed subtask: a goal, the files it exclusively owns, and the
    CLI agent that should execute it (D-16). `agent` defaults to the native loop
    so an LLM that omits it stays backward compatible; `depends_on` lets the
    coordinator order subtasks that legitimately share a file."""

    goal: str
    owned_files: list[str] = Field(default_factory=list)
    agent: str = NATIVE
    depends_on: list[str] = Field(default_factory=list)


class Decomposition(BaseModel):
    """Top-level structured response — the list of subtasks."""

    subtasks: list[SubtaskSpec] = Field(default_factory=list)


class DecompositionError(RuntimeError):
    """The provider returned no parsed structured output (forced-tool path failed)."""


def _system_prompt(known: list[str], min_tasks: int, max_tasks: int) -> str:
    """Why a dedicated builder: the disjoint-ownership + agent-choice rules are the
    coordinator's entire contract, so they live in one place rather than inline."""
    agents = ", ".join(known)
    return (
        "You are the coordinator of a coding agent swarm. Decompose the user's "
        f"goal into between {min_tasks} and {max_tasks} subtasks that can run IN "
        "PARALLEL.\n\n"
        "HARD RULES:\n"
        "1. Each subtask's `owned_files` MUST be DISJOINT from every other "
        "subtask's — no two subtasks may list the same file. This is required so "
        "the agents never collide on writes.\n"
        "2. If two units of work genuinely must touch the same file, make one "
        "`depends_on` the other instead of overlapping their files.\n"
        f"3. Pick one `agent` per subtask from exactly this set: {agents}.\n"
        "4. Keep `owned_files` to concrete repo-relative paths the subtask will "
        "edit."
    )


async def decompose(
    provider: Any,
    *,
    goal: str,
    model: str,
    cwd: str,
    project_context: str = "",
    min_tasks: int = 2,
    max_tasks: int = 6,
) -> list[SubtaskSpec]:
    """Call the provider once to split `goal` into 2–6 parallel subtasks.

    Uses forced structured output (`response_format=Decomposition`) so the result
    arrives as a validated pydantic object on `resp.parsed`; if that is None the
    forced-tool path failed and we raise rather than silently returning an empty
    plan. The returned list is clamped to [min_tasks, max_tasks] because the LLM
    can ignore the count instruction — the clamp is the real guard.
    """
    messages = [
        {"role": "system", "content": _system_prompt(known_agents(), min_tasks, max_tasks)},
        {
            "role": "user",
            "content": (
                f"Working directory: {cwd}\n"
                f"Project context: {project_context or '(none provided)'}\n\n"
                f"GOAL:\n{goal}"
            ),
        },
    ]
    resp = await provider.complete(
        messages=messages,
        model=model,
        response_format=Decomposition,
    )
    parsed = resp.parsed
    if parsed is None:
        raise DecompositionError(
            "coordinator provider returned no structured Decomposition "
            "(resp.parsed is None) — model did not honor the forced schema"
        )
    subtasks = list(parsed.subtasks)
    # Clamp: drop anything past max_tasks; a too-short plan is left as-is (we can't
    # fabricate subtasks) but never trimmed below what the model returned.
    return subtasks[:max_tasks]


def to_tasks(
    subtasks: list[SubtaskSpec],
    *,
    make_id: Callable[[SubtaskSpec, int], str] | None = None,
) -> list[Task]:
    """Convert SubtaskSpecs into SwarmStore Tasks, rejecting overlapping plans.

    Ids are generated (8-hex, matching SwarmStore.add_task) unless `make_id` is
    supplied — tests inject deterministic ids to assert depends_on ordering.
    `validate_no_overlap` runs as each Task joins the active set, so a decomposition
    that violates disjoint-ownership raises OwnershipOverlapError here — BEFORE any
    task file is written or any CLI is spawned.
    """
    tasks: list[Task] = []
    for idx, spec in enumerate(subtasks):
        tid = make_id(spec, idx) if make_id else uuid.uuid4().hex[:8]
        task = Task(
            id=tid,
            goal=spec.goal,
            owned_files=list(spec.owned_files),
            depends_on=list(spec.depends_on),
        )
        validate_no_overlap(task, tasks)
        tasks.append(task)
    return tasks
