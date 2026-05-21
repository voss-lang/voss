"""O5-05: end-to-end happy path — idea → ticket → dispatch → Done."""
from __future__ import annotations

import pytest

from voss.harness.em.loop import em_loop
from voss.harness.em.schema import CreateTicketOp, DispatchCardOp, EMPlanResponse, NoopOp
from voss.harness.em.stub import DeterministicEMStub
from voss.harness.em.tickets import RoutingRationale, RunFinal


class TestEmFullRun:
    @pytest.mark.asyncio
    async def test_idea_to_all_terminal(self, make_handle, stub_board):
        stub_board.spawn_card(node_id="c1", column="Planned")

        stub = DeterministicEMStub(scripted=[
            EMPlanResponse(ops=[
                CreateTicketOp(original_idea="ship the homepage", worker_role="backend"),
            ], reasoning="iter 1"),
            EMPlanResponse(ops=[
                DispatchCardOp(
                    card_id="c1", role_id="backend", task="build routes",
                    rationale_text="backend handles api routes",
                    candidates_considered=["backend", "frontend"],
                ),
            ], reasoning="iter 2"),
            EMPlanResponse(ops=[NoopOp(reason="waiting")], reasoning="iter 3"),
        ])

        handle = make_handle()
        rf = await em_loop(
            idea="ship the homepage", em_handle=handle, em_agent=stub,
            roster_descriptions={"backend": "API dev", "frontend": "UI dev"},
            max_iterations=3,
        )

        assert isinstance(rf, RunFinal)
        assert rf.kind == "em.run_final"
        assert rf.em_iterations == 3
        assert len(stub.calls) >= 2

        # Routing rationale emitted on dispatch.
        audits_with_rr = [
            a for a in handle._node_audit.values()
            if a.routing_rationales
        ]
        assert len(audits_with_rr) >= 1
        rr = audits_with_rr[0].routing_rationales[0]
        assert isinstance(rr, RoutingRationale)
        assert rr.chosen_role == "backend"
        assert "backend" in rr.candidates_considered
