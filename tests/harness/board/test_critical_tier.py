"""V20-04 (VRES-04): critical risk tier — Done requires explicit human approval.

NO agent verdict can clear the 'human' clause: the card parks pending-human
(resumable gate refusal, not terminal) until an operator approve/reject
record exists under .voss/sessions/<root>/approvals/<card_id>.json.
"""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


def _clean_code_artifact():
    return SimpleNamespace(tests_passed=True, scope_violations=())


def _passing_board(manager, cwd):
    stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
    stub_b = DeterministicReviewerStub(conf=0.99, verdict="pass", source="B", tier="strong")
    return Board.from_team_config(
        build_test_team(), recorder=manager,
        reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
    )


async def _to_inreview(board, *, risk_tier):
    card = await board.spawn_card(risk_tier=risk_tier)
    card = board.move(card, to="Planned")
    card = board.move(card, to="InProgress")
    card = dataclasses.replace(card, artifact=_clean_code_artifact())
    board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
    card = board.move(card, to="InReview")
    return card


@pytest.mark.asyncio
async def test_critical_card_blocked_without_human(tmp_recorder):
    manager, cwd = tmp_recorder
    board = _passing_board(manager, cwd)
    card = await _to_inreview(board, risk_tier="critical")
    with pytest.raises(BoardGateError) as exc:
        board.move(card, to="Done")
    assert "human" in exc.value.failing_clauses
    assert next(c for c in board._cards if c.node_id == card.node_id).column == "InReview"


@pytest.mark.asyncio
async def test_critical_card_passes_after_approval(tmp_recorder):
    from voss.harness.board.machine import write_human_approval

    manager, cwd = tmp_recorder
    board = _passing_board(manager, cwd)
    card = await _to_inreview(board, risk_tier="critical")
    write_human_approval(
        cwd, manager._root.id, card.node_id, decision="approved", note="reviewed"
    )
    card = board.move(card, to="Done")
    assert card.column == "Done"


@pytest.mark.asyncio
async def test_critical_rejection_routes_blocked(tmp_recorder):
    from voss.harness.board.machine import write_human_approval

    manager, cwd = tmp_recorder
    board = _passing_board(manager, cwd)
    card = await _to_inreview(board, risk_tier="critical")
    write_human_approval(
        cwd, manager._root.id, card.node_id, decision="rejected", note="too risky"
    )
    card = board.move(card, to="Done")
    assert card.column == "Blocked"
    node = manager.get_node(card.node_id)
    last = [t for t in node.transitions if t.get("kind") == "board.transition"][-1]
    assert last["reason"] == "pending_human_rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", ["low", "med", "high"])
async def test_noncritical_tiers_unaffected(tmp_recorder, tier):
    manager, cwd = tmp_recorder
    board = _passing_board(manager, cwd)
    card = await _to_inreview(board, risk_tier=tier)
    # No approval record anywhere; human clause never blocks non-critical.
    passed, failing = board.dry_run_gate(card, ("InReview", "Done"))
    assert "human" not in failing
    card = board.move(card, to="Done")
    assert card.column == "Done"


@pytest.mark.asyncio
async def test_critical_pending_does_not_burn_retries(tmp_recorder):
    manager, cwd = tmp_recorder
    board = _passing_board(manager, cwd)
    card = await _to_inreview(board, risk_tier="critical")
    for _ in range(board._cfg.retry_ceiling + 2):
        with pytest.raises(BoardGateError):
            board.move(card, to="Done")
    live = next(c for c in board._cards if c.node_id == card.node_id)
    assert live.column == "InReview"  # never force-terminated
    assert live.retry_count == 0  # pending-human burns zero retries


@pytest.mark.asyncio
async def test_critical_threshold_entry_exists(tmp_recorder):
    manager, cwd = tmp_recorder
    # conf 0.985 < critical threshold 0.99 → intermediate conf gate refuses
    # (and does not KeyError on the thresholds dict).
    stub = DeterministicReviewerStub(conf=0.985, verdict="pass")
    board = Board.from_team_config(
        build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
    )
    card = await board.spawn_card(risk_tier="critical")
    card = board.move(card, to="Planned")
    card = board.move(card, to="InProgress")
    card = dataclasses.replace(card, artifact=_clean_code_artifact())
    board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
    with pytest.raises(BoardGateError) as exc:
        board.move(card, to="InReview")
    assert "conf" in exc.value.failing_clauses


@pytest.mark.asyncio
async def test_critical_pending_skips_ab_spend(tmp_recorder):
    """Gate-before-spend: pending-human refuses before paying A/B reviews."""

    class CountingStub(DeterministicReviewerStub):
        calls = 0

        def review(self, card, *, tier=None):
            type(self).calls += 1
            return super().review(card, tier=tier)

    manager, cwd = tmp_recorder
    stub_a = CountingStub(conf=0.99, verdict="pass", source="A", tier="fast")
    stub_b = CountingStub(conf=0.99, verdict="pass", source="B", tier="strong")
    board = Board.from_team_config(
        build_test_team(), recorder=manager,
        reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
    )
    card = await _to_inreview(board, risk_tier="critical")
    CountingStub.calls = 0
    with pytest.raises(BoardGateError):
        board.move(card, to="Done")
    assert CountingStub.calls == 0
