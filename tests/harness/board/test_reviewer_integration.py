"""O4-04 Task 1: Full board lifecycle with real ReviewerA + ReviewerB (ORVW-10).

Proves the A/B split plugs into O3's Board via the frozen Reviewer Protocol:
- ReviewerB is the Board's gate reviewer (called by conf_meets_p during
  Board.move at InProgress→InReview and InReview→Done)
- ReviewerA operates outside the gate system (called by the test driver,
  standing in for the EM loop) to author verification
- Both produce ReviewerVerdict instances; both are Protocol-compatible
  with DeterministicReviewerStub

No real LLM calls — fake providers for both reviewers.
"""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board
from voss.harness.board.reviewer_a import ReviewerA
from voss.harness.board.reviewer_b import ReviewerB, _ReviewerBOutput
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.verdict import Reviewer, ReviewerVerdict
from voss.harness.permissions import PermissionGate
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode
from voss_runtime.providers.base import ProviderResponse

from .conftest import build_test_team


# --- Fake providers ----------------------------------------------------------

class _FakeProviderForA:
    """Scripts run_turn responses so ReviewerA produces a pass verdict."""
    async def complete(self, **kw):
        raise NotImplementedError("A uses run_turn_fn, not raw provider.complete")
    def count_tokens(self, **kw):
        return 1


class _FakeProviderForB:
    """Returns a canned passing verdict for ReviewerB."""
    def __init__(self, conf: float = 0.99, verdict: str = "pass"):
        self._canned = _ReviewerBOutput(
            conf=conf, verdict=verdict, notes="integration test", evidence_refs=[],
        )
        self.call_count = 0

    async def complete(self, **kw):
        self.call_count += 1
        return ProviderResponse(
            text="{}", model=kw.get("model", "test"),
            prompt_tokens=1, completion_tokens=1, cost_usd=0.0,
            parsed=self._canned,
        )

    def count_tokens(self, **kw):
        return 1


class _NullRenderer:
    def status(self, *a, **kw): pass
    def info(self, *a, **kw): pass
    def tool_call(self, *a, **kw): pass
    def tool_result(self, *a, **kw): pass
    def stream_text(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def step(self, *a, **kw): pass
    def done(self, *a, **kw): pass


def _make_review_context(**overrides):
    """Build a card-like object with all fields A and B need."""
    defaults = {
        "original_idea": "Build a REST API for user management",
        "acceptance_criteria": "Users can be created, read, updated, deleted",
        "artifact": SimpleNamespace(tests_passed=True, scope_violations=()),
        "artifact_text": "def create_user(): pass",
        "file_diff": "+def create_user(): pass",
        "a_verification_summary": "",
        "domain": "code",
        "node_id": "test-node",
        "column": "InReview",
        "risk_tier": "low",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# --- Integration test --------------------------------------------------------

class TestBoardLifecycleWithRealReviewers:
    @pytest.mark.asyncio
    async def test_board_lifecycle_with_real_reviewers(self, tmp_path):
        """ORVW-10: A+B drive a card Backlog→Done via the Board."""
        # 1. Set up reviewers.
        provider_b = _FakeProviderForB(conf=0.99, verdict="pass")
        reviewer_b = ReviewerB(
            provider=provider_b, fast_model="test-fast", strong_model="test-strong",
        )

        async def fake_run_turn(task, **kwargs):
            from voss.harness.agent import TurnResult
            plan = SimpleNamespace(
                confidence=0.9, steps=[], open_question=None,
                assumptions=[], decisions=[], risks=[],
            )
            return TurnResult(
                plan=plan, confidence=0.9, final="PASS if API works",
                tool_results=["Running tests... [exit 0]"], cost_usd=0.0, run=None,
            )

        reviewer_a = ReviewerA(
            provider=_FakeProviderForA(), model="test-model",
            cwd=tmp_path, renderer=_NullRenderer(),
            base_gate=PermissionGate(mode="edit", auto_yes=True),
            run_turn_fn=fake_run_turn,
        )

        # 2. Both implement the Reviewer Protocol.
        assert isinstance(reviewer_a, Reviewer)
        assert isinstance(reviewer_b, Reviewer)
        # Both are drop-in replacements for DeterministicReviewerStub.
        stub = DeterministicReviewerStub(conf=0.99)
        assert isinstance(stub, Reviewer)

        # 3. Call A to author verification (outside the Board gate system).
        review_ctx = _make_review_context()
        a_verdict = reviewer_a.review(review_ctx)
        assert isinstance(a_verdict, ReviewerVerdict)
        assert a_verdict.source == "A"
        assert a_verdict.verdict == "pass"

        # 4. Create a Board with B as the gate reviewer.
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1_000_000)
        manager = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=reviewer_b, cwd=tmp_path,
        )

        # 5. Spawn a card and drive it through the lifecycle.
        card = await board.spawn_card(risk_tier="low")
        # Attach passing artifact (code-card: tests_passed=True, no scope violations).
        card = dataclasses.replace(
            card,
            artifact=SimpleNamespace(tests_passed=True, scope_violations=()),
        )
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]

        # Backlog → Planned (no reviewer call — non-artifact transition).
        card = board.move(card, to="Planned")
        assert card.column == "Planned"
        assert provider_b.call_count == 0  # B not invoked yet

        # Planned → InProgress (no reviewer call — non-artifact transition).
        card = board.move(card, to="InProgress")
        assert card.column == "InProgress"
        assert provider_b.call_count == 0  # B still not invoked

        # InProgress → InReview (reviewer B IS invoked by conf_meets_p gate).
        card = board.move(card, to="InReview")
        assert card.column == "InReview"
        assert provider_b.call_count >= 1  # B invoked at this gate

        b_calls_before_done = provider_b.call_count

        # InReview → Done (reviewer B invoked again at Done gate).
        card = board.move(card, to="Done")
        assert card.column == "Done"
        assert provider_b.call_count > b_calls_before_done  # B invoked again

        # 6. Verify transition deltas on the node.
        node = manager.get_node(card.node_id)
        assert node is not None
        assert len(node.transitions) == 4  # Planned, InProgress, InReview, Done
        # Artifact transitions (InReview, Done) have verdict_snapshot.
        assert node.transitions[2]["verdict_snapshot"] is not None
        assert node.transitions[3]["verdict_snapshot"] is not None
        assert node.transitions[2]["verdict_snapshot"]["source"] == "B"
