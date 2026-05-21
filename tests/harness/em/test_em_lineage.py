"""O5-01 TDD: KillRecord / RescopeRecord / RunFinal lineage invariants + L-04."""
from __future__ import annotations

import dataclasses

import pytest

from voss.harness.em.tickets import (
    KillRecord,
    RescopeRecord,
    RunFinal,
    Ticket,
)


class TestKillRecord:
    def test_construction(self):
        kr = KillRecord(
            killed_node_id="n1", rationale_text="scope too wide",
            evidence_refs=("file.py:10",), killed_at="2026-05-20T00:00:00Z",
        )
        assert kr.kind == "em.kill"
        assert kr.lineage_parent_id is None
        assert kr.successor_card_id is None

    def test_frozen(self):
        kr = KillRecord(
            killed_node_id="n1", rationale_text="x",
            evidence_refs=(), killed_at="now",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            kr.rationale_text = "tampered"  # type: ignore[misc]

    def test_self_parent_rejected(self):
        with pytest.raises(ValueError, match="self-parented"):
            KillRecord(
                killed_node_id="n1", lineage_parent_id="n1",
                rationale_text="x", evidence_refs=(), killed_at="now",
            )


class TestRescopeRecord:
    def test_construction(self):
        rr = RescopeRecord(
            predecessor_card_id="c1", successor_card_id="c2",
            diff_summary="narrowed scope", rationale_text="too wide",
            rescoped_at="2026-05-20T00:00:00Z",
        )
        assert rr.kind == "em.rescope"

    def test_self_rescope_rejected(self):
        with pytest.raises(ValueError, match="self-rescope"):
            RescopeRecord(
                predecessor_card_id="c1", successor_card_id="c1",
                diff_summary="x", rationale_text="x", rescoped_at="now",
            )


class TestBidirectionalPointers:
    def test_kill_then_rescope_pointers(self):
        kr = KillRecord(
            killed_node_id="n_old", successor_card_id="c_new",
            rationale_text="replaced", evidence_refs=(), killed_at="now",
        )
        rr = RescopeRecord(
            predecessor_card_id="c_old", successor_card_id="c_new",
            diff_summary="narrowed", rationale_text="too wide",
            rescoped_at="now",
        )
        # Bidirectional: kill points to successor, rescope points to predecessor.
        assert kr.successor_card_id == rr.successor_card_id
        assert rr.predecessor_card_id == "c_old"


class TestAppendNotDelete:
    """L-04: building kill/rescope records does NOT mutate the original Ticket."""
    def test_original_ticket_unchanged(self):
        original = Ticket(
            id="t1", card_node_id="n1", original_idea="Build API",
            acceptance="CRUD", dod="Tests pass", worker_role="be",
            routing_rationale_id="rr1", created_at="now",
        )
        snapshot = dataclasses.replace(original)  # copy

        # Build a kill record referencing the ticket.
        KillRecord(
            killed_node_id=original.card_node_id,
            successor_card_id="c_new",
            rationale_text="killed", evidence_refs=(), killed_at="now",
        )
        # Build a rescope record.
        RescopeRecord(
            predecessor_card_id=original.id, successor_card_id="t2",
            diff_summary="narrowed", rationale_text="too wide",
            rescoped_at="now",
        )
        # Original ticket is unchanged (frozen + no side-effects).
        assert original == snapshot


class TestRunFinal:
    def test_construction(self):
        rf = RunFinal(
            root_id="root1", idea="Build API", total_cards=10,
            done_count=7, blocked_count=2, killed_count=1,
            rescope_count=0, em_iterations=5, ts="now",
        )
        assert rf.kind == "em.run_final"
        assert rf.total_cards == 10

    def test_negative_counts_rejected(self):
        with pytest.raises(ValueError):
            RunFinal(
                root_id="r", idea="x", total_cards=-1,
                done_count=0, blocked_count=0, killed_count=0,
                rescope_count=0, em_iterations=0, ts="now",
            )

    def test_kind_is_em(self):
        rf = RunFinal(
            root_id="r", idea="x", total_cards=0,
            done_count=0, blocked_count=0, killed_count=0,
            rescope_count=0, em_iterations=0, ts="now",
        )
        assert rf.kind.startswith("em.")
