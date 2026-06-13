"""V20-03 mission brief tests (VRES-03) — workers stop dispatching blind."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from voss.harness.claims import atomic_stake, new_claim_id, open_claims_db
from voss.harness.em.handle import EMBoardHandle
from voss.harness.permissions import PermissionGate
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode
from voss.harness.subagents import (
    MissionBrief,
    ScopeLine,
    SiblingLine,
    SubagentRegistry,
    SubagentSpec,
    agent_task,
)
from voss.harness.team import (
    BoardSpec,
    TeamCeiling,
    TeamConfig,
    TeamPolicy,
    TeamRoleScope,
)


# --- agent_task rendering -----------------------------------------------------

SPEC = SubagentSpec(id="x", description="d", role_prompt="RP")


def test_agent_task_no_brief_unchanged():
    # Byte-identical to today's output — existing callers and prompt pins.
    assert agent_task(SPEC, "do it") == "Subagent role:\nRP\n\nTask:\ndo it"


def test_agent_task_with_brief_sections():
    brief = MissionBrief(
        outcome="ship feature X",
        siblings=(
            SiblingLine(role_id="frontend", task_summary="build UI"),
            SiblingLine(role_id="backend", task_summary="build API"),
        ),
        claimed_scopes=(
            ScopeLine(owner_agent="agent-b", patterns=("src/ui/**",)),
            ScopeLine(owner_agent="agent-a", patterns=("src/api/**", "src/db/**")),
        ),
    )
    out = agent_task(SPEC, "do it", brief=brief)
    assert out.startswith("Subagent role:\nRP\n\nTask:\ndo it")
    assert "## Outcome" in out
    assert "ship feature X" in out
    assert "## Siblings (do not duplicate their work)" in out
    assert "- backend: build API" in out
    assert "- frontend: build UI" in out
    assert "## Claimed scopes (do not touch)" in out
    assert "- agent-a: src/api/**, src/db/**" in out
    assert "- agent-b: src/ui/**" in out
    # Deterministic: sorted sections, stable across calls.
    assert out == agent_task(SPEC, "do it", brief=brief)
    assert out.index("- backend:") < out.index("- frontend:")
    assert out.index("- agent-a:") < out.index("- agent-b:")


def test_agent_task_empty_brief_unchanged():
    assert agent_task(SPEC, "do it", brief=MissionBrief()) == agent_task(SPEC, "do it")


# --- dispatch assembly (EMBoardHandle) ----------------------------------------
# Stub fixtures mirror tests/harness/em/conftest.py.


@dataclass(frozen=True, slots=True)
class StubCard:
    node_id: str
    column: str = "Backlog"
    risk_tier: str = "med"
    retry_count: int = 0
    deadline: float = 9999.0
    scope: Optional[TeamRoleScope] = None
    artifact: object = None
    eval_threshold: float = 1.0


class StubBoard:
    def __init__(self) -> None:
        self._cards: list[StubCard] = []

    def spawn_card(self, node_id: str, **kw) -> StubCard:
        card = StubCard(node_id=node_id, **kw)
        self._cards.append(card)
        return card

    def cards(self) -> list:
        return list(self._cards)

    def move(self, card: object, to: str) -> object:
        node_id = getattr(card, "node_id", "")
        new_card = dataclasses.replace(card, column=to)  # type: ignore[type-var]
        self._cards = [new_card if c.node_id == node_id else c for c in self._cards]
        return new_card

    def _tick_once(self, now: float) -> None:
        pass


@pytest.fixture
def board():
    return StubBoard()


@pytest.fixture
def handle(board, tmp_path: Path):
    root = SessionTreeNode.create_root(cwd=tmp_path, limit=1_000_000)
    manager = SessionTreeManager(root, reserve=0, cwd=tmp_path)
    registry = SubagentRegistry()
    for role in ("backend", "frontend", "ai"):
        registry.register(
            SubagentSpec(id=role, description=f"Test {role}", role_prompt=f"You are {role}")
        )
    config = TeamConfig(
        name="TestTeam",
        ceiling=TeamCeiling(
            budget_tokens=1_000_000,
            scope=TeamRoleScope(globs=("src/**",)),
            latency_seconds=600,
        ),
        policy=TeamPolicy(p=None),
        em_agent_id="em",
        roster_ids=frozenset({"backend", "frontend", "ai"}),
        board=BoardSpec(raw_items=()),
        rituals=(),
    )
    return EMBoardHandle(
        board=board,
        registry=registry,
        team_config=config,
        manager=manager,
        base_gate=PermissionGate(mode="auto", auto_yes=True),
        cwd=tmp_path,
    )


def _ticket_on_board(handle, board, *, idea: str, role: str, node_id: str, column: str):
    t = handle.create_ticket(
        original_idea=idea,
        acceptance_criteria="works",
        dod="tests green",
        worker_role=role,
    )
    t = dataclasses.replace(t, card_node_id=node_id)
    handle._tickets[t.id] = t
    board.spawn_card(node_id=node_id, column=column)
    return t


def test_dispatch_prompt_contains_siblings(handle, board, tmp_path: Path):
    t1 = _ticket_on_board(handle, board, idea="build API", role="backend", node_id="n1", column="InProgress")
    _ticket_on_board(handle, board, idea="build UI", role="frontend", node_id="n2", column="InProgress")
    _ticket_on_board(handle, board, idea="wire AI", role="ai", node_id="n3", column="Done")

    conn = open_claims_db(tmp_path)
    won, _ = atomic_stake(conn, "agent-zed", new_claim_id(), ["src/db/**", "src/models/**"])
    conn.close()
    assert won

    handle.dispatch_card(
        card_id=t1.id,
        role_id="backend",
        task="build the API endpoints",
        rationale_text="backend owns API",
        candidates_considered=("backend",),
    )
    prompt = handle._node_audit["n1"].dispatched_prompt
    assert prompt is not None
    assert "build the API endpoints" in prompt
    assert "build API" in prompt  # outcome from ticket.original_idea
    assert "- frontend: build UI" in prompt  # in-flight sibling
    assert "wire AI" not in prompt  # Done card is not a sibling
    assert "agent-zed" in prompt
    assert "src/db/**" in prompt
    assert "src/models/**" in prompt


def test_dispatch_no_claims_no_siblings(handle, board):
    t1 = _ticket_on_board(handle, board, idea="build API", role="backend", node_id="n1", column="InProgress")
    handle.dispatch_card(
        card_id=t1.id,
        role_id="backend",
        task="build the API endpoints",
        rationale_text="backend owns API",
        candidates_considered=("backend",),
    )
    prompt = handle._node_audit["n1"].dispatched_prompt
    assert prompt is not None
    assert "## Outcome" in prompt
    assert "build API" in prompt
    # Degrades cleanly: no empty header noise.
    assert "Siblings" not in prompt
    assert "Claimed scopes" not in prompt
