"""O3-04 Task 2: 100-card deterministic stress — proves liveness invariant (SPEC L122)."""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError, BoardWIPError
from voss.harness.board.machine import _TERMINAL_COLUMNS
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.tick import FakeClock
from voss.harness.board.verdict import ReviewerVerdict
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode, mutate_envelope

from .conftest import build_test_team

_FORWARD_PATH = {
    "Backlog": "Planned",
    "Planned": "InProgress",
    "InProgress": "InReview",
    "InReview": "Done",
}


@pytest.mark.asyncio
async def test_100_card_stress(tmp_path):
    """100 cards, mixed outcomes, zero non-terminal after driver loop."""
    root = SessionTreeNode.create_root(cwd=tmp_path, limit=100_000_000)
    manager = SessionTreeManager(root, reserve=0, cwd=tmp_path)
    clock = FakeClock(0.0)
    stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
    board = Board.from_team_config(
        build_test_team(budget=100_000_000, latency_s=600),
        recorder=manager, reviewer=stub, cwd=tmp_path, clock=clock,
    )

    # --- Spawn 100 cards with mixed configs ---
    # 60 passing, 20 timeout, 10 budget-starved, 10 failing-artifact
    passing_art = SimpleNamespace(tests_passed=True, scope_violations=())
    failing_art = SimpleNamespace(tests_passed=False, eval_score=0.0, scope_violations=())

    cards = []
    for i in range(60):
        c = await board.spawn_card(risk_tier="low", deadline_override=clock() + 9999.0)
        c = dataclasses.replace(c, artifact=passing_art)
        board._cards = [c if x.node_id == c.node_id else x for x in board._cards]
        cards.append(("pass", c))
    for i in range(20):
        c = await board.spawn_card(risk_tier="low", deadline_override=clock() + 0.5)
        c = dataclasses.replace(c, artifact=passing_art)
        board._cards = [c if x.node_id == c.node_id else x for x in board._cards]
        cards.append(("timeout", c))
    for i in range(10):
        c = await board.spawn_card(risk_tier="low", per_card_budget=10,
                                   deadline_override=clock() + 9999.0)
        c = dataclasses.replace(c, artifact=passing_art)
        board._cards = [c if x.node_id == c.node_id else x for x in board._cards]
        cards.append(("budget", c))
    for i in range(10):
        c = await board.spawn_card(risk_tier="low", deadline_override=clock() + 9999.0)
        c = dataclasses.replace(c, artifact=failing_art)
        board._cards = [c if x.node_id == c.node_id else x for x in board._cards]
        cards.append(("fail", c))

    total_attempts = 0

    # --- Drain budget-starved cards ---
    for kind, c in cards:
        if kind == "budget":
            node = manager.get_node(c.node_id)
            if node:
                mutate_envelope(node, -node.envelope["limit"], tmp_path)

    # --- Driver loop (max 60 iterations to prevent infinite) ---
    fail_verdict = ReviewerVerdict(
        conf=0.99, source="B", tier="strong", verdict="fail",
        notes="failing", evidence_refs=(),
    )

    for iteration in range(60):
        clock.advance(1.0)
        board._tick_once(clock())

        all_terminal = True
        for idx, (kind, old_card) in enumerate(cards):
            # Refresh card from board.
            current = [c for c in board.cards() if c.node_id == old_card.node_id]
            if not current:
                continue
            c = current[0]
            if c.column in _TERMINAL_COLUMNS:
                continue
            all_terminal = False

            next_col = _FORWARD_PATH.get(c.column)
            if next_col is None:
                continue
            try:
                new_c = board.move(c, to=next_col)
                total_attempts += 1
                cards[idx] = (kind, new_c)
            except BoardWIPError:
                total_attempts += 1
                # WIP full — skip this card, try again next iteration.
                continue
            except BoardGateError as e:
                total_attempts += 1
                # Critic loop for failing cards refused at Done.
                if "tests" in (e.failing_clauses or []) or "eval" in (e.failing_clauses or []):
                    refreshed = [x for x in board.cards() if x.node_id == c.node_id][0]
                    new_c = board.critic_step(refreshed, fail_verdict)
                    cards[idx] = (kind, new_c)

        if all_terminal:
            break

    # --- Assertions ---
    final_cards = board.cards()
    assert len(final_cards) == 100

    done_count = sum(1 for c in final_cards if c.column == "Done")
    blocked_count = sum(1 for c in final_cards if c.column == "Blocked")
    non_terminal = sum(1 for c in final_cards if c.column not in _TERMINAL_COLUMNS)

    # Liveness: zero non-terminal.
    assert non_terminal == 0, f"{non_terminal} cards still non-terminal"
    assert done_count + blocked_count == 100

    # At least one Done.
    assert done_count >= 1

    # Check for each blocked reason.
    reasons_seen = set()
    for c in final_cards:
        if c.column == "Blocked":
            node = manager.get_node(c.node_id)
            if node:
                forced = [d for d in node.transitions if d["outcome"] == "forced"]
                for f in forced:
                    reasons_seen.add(f["reason"])
    assert "timeout" in reasons_seen, f"missing timeout in {reasons_seen}"
    assert "budget" in reasons_seen, f"missing budget in {reasons_seen}"
    assert "retry_ceiling" in reasons_seen, f"missing retry_ceiling in {reasons_seen}"

    # Transition-delta count invariant.
    for c in final_cards:
        node = manager.get_node(c.node_id)
        if node:
            assert len(node.transitions) >= 1, f"card {c.node_id} has no transitions"
