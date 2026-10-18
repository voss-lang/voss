"""Recorded task topology and worker attempts, projected into journal snapshots."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Attempt(BaseModel):
    id: str
    run_id: str | None = None
    plan_revision: str
    role: str | None = None
    harness: str | None = None
    provider: str | None = None
    model: str | None = None
    session_id: str | None = None
    state: str = "unknown"
    branch: str | None = None
    worktree: str | None = None
    base_revision: str | None = None
    candidate_revision: str | None = None
    review_state: str = "unavailable"
    blockers: list[str] = Field(default_factory=list)
    started_at: str | None = None
    ended_at: str | None = None
    output_after: int | None = None
    output_through: int | None = None


class Node(BaseModel):
    id: str
    goal: str
    depends_on: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)
    state: str = "unknown"
    harness: str | None = None
    provider: str | None = None
    model: str | None = None
    blocked_by: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    attempts: list[Attempt] = Field(default_factory=list)


class Graph(BaseModel):
    v: Literal[1] = 1
    source: str
    plan_id: str
    revision: str
    run_id: str | None = None
    owner_session_id: str
    updated_at: str = Field(default_factory=now)
    nodes: list[Node] = Field(default_factory=list)


class Output(BaseModel):
    v: Literal[1] = 1
    status: str
    message: str | None = None
    events: list[dict] = Field(default_factory=list)
    next_cursor: int = 0
    has_more: bool = False


def location(cwd):
    def git(*args):
        result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, timeout=5)
        return result.stdout.decode().strip() if result.returncode == 0 else None
    try:
        return {"worktree": str(cwd), "branch": git("symbolic-ref", "--short", "-q", "HEAD"), "base_revision": git("rev-parse", "HEAD")}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"worktree": str(cwd)}


def dependencies(graph):
    states = {node.id: node.state for node in graph.nodes}
    for node in graph.nodes:
        node.blocked_by = [key for key in node.depends_on if states.get(key) not in {"completed", "done"}]


def preview_state(snapshot):
    plan = snapshot.execution_plan
    graph = snapshot.graph
    if graph is None:
        graph = Graph(source="preview", plan_id=plan["id"], revision=plan["revision"], run_id=snapshot.run_id, owner_session_id=snapshot.session_id,
                      nodes=[Node(**{key: node[key] for key in ("id", "goal", "depends_on", "files", "criteria")},
                                  harness=plan["briefing"]["harness"], provider=plan.get("provider"), model=plan["briefing"]["model"]) for node in plan["tasks"]])
    for node in graph.nodes:
        state = snapshot.node_states.get(node.id, "unknown")
        if state == "running" and snapshot.phase == "waiting":
            state = "waiting"
        node.state = state
        if state in {"running", "waiting"} and not node.attempts:
            node.attempts.append(Attempt(id=f"{snapshot.attempt_id}:{node.id}", run_id=snapshot.run_id, plan_revision=graph.revision,
                harness=node.harness, provider=node.provider, model=node.model, role="native", session_id=snapshot.session_id,
                worktree=plan["briefing"]["cwd"], branch=plan.get("base_branch"), base_revision=plan["base_revision"],
                started_at=now(), output_after=snapshot.watermark))
        if node.attempts:
            attempt = node.attempts[-1]
            attempt.state = state
            if state in {"completed", "failed", "cancelled", "interrupted", "waiting"} and attempt.output_through is None:
                attempt.output_through = snapshot.watermark
            if state == "running":
                attempt.output_through = None
            if state in {"completed", "failed", "cancelled", "interrupted"} and attempt.ended_at is None:
                attempt.ended_at = now()
            attempt.blockers = [item.get("message") or item["kind"] for item in snapshot.pending_actions] if state == "waiting" else []
            node.blockers = list(attempt.blockers)
    dependencies(graph)
    snapshot.graph = graph


def settle(snapshot):
    graph = snapshot.graph
    if graph is None:
        return
    if snapshot.session_id == graph.owner_session_id and snapshot.phase == "waiting":
        for action in snapshot.pending_actions:
            if action.get("kind") != "authentication":
                continue
            for node in graph.nodes:
                if node.attempts and node.attempts[-1].harness == action.get("harness") and node.attempts[-1].state in {"assigned", "running", "waiting"}:
                    node.state = node.attempts[-1].state = "waiting"
                    node.blockers = node.attempts[-1].blockers = [action.get("message") or "Sign in to this harness"]
    if snapshot.session_id == graph.owner_session_id and snapshot.phase in {"cancelled", "interrupted", "failed"}:
        for node in graph.nodes:
            for attempt in node.attempts:
                if attempt.state in {"running", "assigned", "waiting"}:
                    attempt.state = snapshot.phase
                    attempt.ended_at = now()
                    attempt.blockers = [snapshot.outcome or snapshot.phase]
            if node.attempts:
                node.state = node.attempts[-1].state
                node.blockers = list(node.attempts[-1].blockers)
            if node.state in {"queued", "open"}:
                node.blockers = [f"Run {snapshot.phase}; dispatch stopped"]
    graph.updated_at = now()
    dependencies(graph)


def worker_state(owner, worker):
    if owner.graph is None:
        return False
    node = next((node for node in owner.graph.nodes if node.id == worker.swarm_task_id), None)
    attempt = next((attempt for attempt in node.attempts if attempt.id == worker.attempt_id and attempt.session_id == worker.session_id), None) if node else None
    if attempt is None or attempt.state == "candidate_ready":
        return False
    state = "running" if worker.phase == "active" else worker.phase
    blockers = [action.get("message") or action["kind"] for action in worker.pending_actions]
    if state in {"failed", "interrupted", "cancelled"}:
        blockers.append(worker.outcome or state)
    if attempt.state == state and attempt.blockers == blockers:
        return False
    attempt.state, attempt.blockers = state, blockers
    if state in {"completed", "failed", "interrupted", "cancelled"}:
        attempt.output_through, attempt.ended_at = worker.watermark, now()
    if node.attempts[-1].id == attempt.id:
        node.state, node.blockers = state, list(blockers)
    return True


def swarm_state(swarm, previous, owner, event=None):
    definitions = [{"id": node.id, "goal": node.goal, "depends_on": node.depends_on, "files": node.owned_files} for node in swarm.tasks]
    revision = hashlib.sha256(json.dumps(definitions, sort_keys=True).encode()).hexdigest()
    old = {node.id: node.model_copy(deep=True) for node in previous.nodes} if previous else {}
    graph = Graph(source="swarm", plan_id=swarm.id, revision=revision, run_id=owner.run_id, owner_session_id=owner.session_id,
                  nodes=[Node(**item, state=swarm.task(item["id"]).state, attempts=old[item["id"]].attempts if item["id"] in old else [],
                              blockers=old[item["id"]].blockers if item["id"] in old else []) for item in definitions])
    event = event or {}
    node = next((node for node in graph.nodes if node.id == event.get("task_id")), None)
    if node is not None:
        kind, attempt_id = event.get("type"), event.get("attempt_id")
        attempt = next((item for item in node.attempts if item.id == attempt_id), None)
        if attempt is None and attempt_id:
            attempt = Attempt(id=attempt_id, run_id=owner.run_id, plan_revision=revision,
                              **{key: event[key] for key in ("role", "harness", "provider", "model", "session_id", "branch", "worktree", "base_revision", "output_after") if event.get(key) is not None})
            node.attempts.append(attempt)
        if kind == "swarm.assign" and attempt and attempt.state in {"unknown", "assigned", "running"}:
            attempt.state = "running" if event.get("launched") else "assigned"
            attempt.started_at = attempt.started_at or event.get("ts") or now()
            node.blockers = []
        elif kind in {"swarm.gate", "swarm.needs_operator"}:
            detail = event.get("detail") or event.get("gate_type") or "Operator action required"
            if detail not in node.blockers:
                node.blockers.append(detail)
            if attempt:
                attempt.blockers = list(node.blockers)
                attempt.state = "failed" if event.get("gate_type") == "member_failed" else "waiting"
                if "reject" in event.get("gate_type", ""):
                    attempt.review_state = "changes_requested"
        elif kind == "swarm.candidate_ready" and attempt:
            attempt.candidate_revision = event.get("head") or None
            attempt.branch, attempt.worktree = event.get("branch"), event.get("worktree")
            attempt.state, attempt.review_state = "candidate_ready", "pending"
        elif kind == "swarm.worker_done" and attempt:
            attempt.ended_at = now()
            attempt.output_through = event.get("output_through")
            if event.get("state") in {"failed", "cancelled", "interrupted", "waiting"}:
                attempt.state = event["state"]
                attempt.blockers = [event.get("detail") or event["state"]]
            elif event.get("exit_code", 0) != 0:
                attempt.state = "failed"
                attempt.blockers.append(f"Worker exited with code {event['exit_code']}")
            elif attempt.state not in {"candidate_ready", "failed", "waiting"}:
                attempt.state = "completed"
        if attempt:
            node.state, node.harness, node.model = attempt.state, attempt.harness, attempt.model
    # Keep recorded failures/candidates when a later snapshot has only legacy store state.
    for item in graph.nodes:
        if item.attempts:
            latest = item.attempts[-1]
            item.state, item.harness, item.provider, item.model = latest.state, latest.harness, latest.provider, latest.model
            item.blockers = list(dict.fromkeys(item.blockers + latest.blockers))
    dependencies(graph)
    return graph
