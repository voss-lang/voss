"""O5-01 TDD: Ticket + RoutingRationale frozen invariants + L-02/L-03 guards."""
from __future__ import annotations

import dataclasses

import pytest

from voss.harness.em.tickets import Ticket, RoutingRationale
from voss.harness.em.errors import EMCageViolation


class TestTicketFrozen:
    def test_ticket_construction(self):
        t = Ticket(
            id="t1", card_node_id="n1", original_idea="Build API",
            acceptance="CRUD works", dod="Tests pass",
            worker_role="backend", routing_rationale_id="rr1",
            created_at="2026-05-20T00:00:00Z",
        )
        assert t.id == "t1"
        assert t.domain == "code"
        assert t.risk_tier == "med"
        assert t.kind == "em.ticket"

    def test_ticket_frozen(self):
        t = Ticket(
            id="t1", card_node_id="n1", original_idea="x",
            acceptance="x", dod="x", worker_role="be",
            routing_rationale_id="rr1", created_at="now",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.original_idea = "tampered"  # type: ignore[misc]


class TestRoutingRationale:
    def test_construction(self):
        rr = RoutingRationale(
            id="rr1", card_id="c1", chosen_role="backend",
            candidates_considered=("backend", "frontend"),
            rationale_text="Backend owns API layer",
            ts="2026-05-20T00:00:00Z",
        )
        assert rr.kind == "em.routing"
        assert rr.confidence_hint is None

    def test_confidence_hint_valid(self):
        rr = RoutingRationale(
            id="rr1", card_id="c1", chosen_role="be",
            candidates_considered=(), rationale_text="ok",
            ts="now", confidence_hint=0.8,
        )
        assert rr.confidence_hint == 0.8

    def test_confidence_hint_out_of_range(self):
        with pytest.raises(ValueError):
            RoutingRationale(
                id="rr1", card_id="c1", chosen_role="be",
                candidates_considered=(), rationale_text="ok",
                ts="now", confidence_hint=1.5,
            )
        with pytest.raises(ValueError):
            RoutingRationale(
                id="rr1", card_id="c1", chosen_role="be",
                candidates_considered=(), rationale_text="ok",
                ts="now", confidence_hint=-0.1,
            )


class TestKindDiscriminator:
    """L-02: every EM record's kind starts with 'em.'"""
    def test_ticket_kind_is_em(self):
        t = Ticket(
            id="t1", card_node_id="n1", original_idea="x",
            acceptance="x", dod="x", worker_role="be",
            routing_rationale_id="rr1", created_at="now",
        )
        assert t.kind.startswith("em.")

    def test_routing_kind_is_em(self):
        rr = RoutingRationale(
            id="rr1", card_id="c1", chosen_role="be",
            candidates_considered=(), rationale_text="ok", ts="now",
        )
        assert rr.kind.startswith("em.")


class TestNoL2Vocab:
    """L-03: audit copy never contains model/cost/token/provider."""
    _FORBIDDEN = {"model", "cost", "token", "provider"}

    def _scan_str_fields(self, obj):
        for f in dataclasses.fields(obj):
            val = getattr(obj, f.name)
            if isinstance(val, str):
                for word in self._FORBIDDEN:
                    assert word not in val.lower(), (
                        f"L2 vocab '{word}' found in field {f.name}={val!r}"
                    )

    def test_ticket_no_l2_vocab(self):
        t = Ticket(
            id="t1", card_node_id="n1",
            original_idea="Build a REST API for user management",
            acceptance="Users can CRUD", dod="Tests pass",
            worker_role="backend", routing_rationale_id="rr1",
            created_at="2026-05-20T00:00:00Z",
        )
        self._scan_str_fields(t)

    def test_routing_no_l2_vocab(self):
        rr = RoutingRationale(
            id="rr1", card_id="c1", chosen_role="backend",
            candidates_considered=("backend", "frontend"),
            rationale_text="Backend owns API layer",
            ts="2026-05-20T00:00:00Z",
        )
        self._scan_str_fields(rr)


class TestEMCageViolation:
    def test_structured_attrs(self):
        e = EMCageViolation(op="dispatch", reason="unknown role 'phantom'")
        assert e.op == "dispatch"
        assert e.reason == "unknown role 'phantom'"
        assert "dispatch" in str(e)
        assert "phantom" in str(e)
