"""O5-03: DeterministicEMStub — scripted responses, zero LLM calls."""
from __future__ import annotations

import pytest

from voss.harness.em.schema import CreateTicketOp, EMPlanResponse, NoopOp
from voss.harness.em.stub import DeterministicEMStub


class TestDeterministicEMStub:
    @pytest.mark.asyncio
    async def test_yields_scripted_in_order(self):
        ep1 = EMPlanResponse(ops=[CreateTicketOp(
            original_idea="idea1", worker_role="be",
        )], reasoning="first")
        ep2 = EMPlanResponse(ops=[NoopOp(reason="done")], reasoning="second")
        stub = DeterministicEMStub(scripted=[ep1, ep2])

        r1 = await stub.plan(idea="x", snapshot="")
        assert r1.reasoning == "first"
        r2 = await stub.plan(idea="x", snapshot="")
        assert r2.reasoning == "second"

    @pytest.mark.asyncio
    async def test_exhausted_returns_noop(self):
        stub = DeterministicEMStub(scripted=[])
        r = await stub.plan(idea="x", snapshot="")
        assert isinstance(r.ops[0], NoopOp)
        assert r.ops[0].reason == "stub_exhausted"

    @pytest.mark.asyncio
    async def test_records_calls(self):
        stub = DeterministicEMStub(scripted=[
            EMPlanResponse(ops=[], reasoning=""),
        ])
        await stub.plan(idea="Build API", snapshot="board state")
        assert len(stub.calls) == 1
        assert stub.calls[0]["idea"] == "Build API"
        assert stub.calls[0]["snapshot"] == "board state"

    @pytest.mark.asyncio
    async def test_no_provider_required(self):
        stub = DeterministicEMStub()
        r = await stub.plan(idea="x", snapshot="")
        assert isinstance(r, EMPlanResponse)

    @pytest.mark.asyncio
    async def test_third_call_after_two_scripted(self):
        stub = DeterministicEMStub(scripted=[
            EMPlanResponse(ops=[], reasoning="a"),
            EMPlanResponse(ops=[], reasoning="b"),
        ])
        await stub.plan(idea="x", snapshot="")
        await stub.plan(idea="x", snapshot="")
        r3 = await stub.plan(idea="x", snapshot="")
        assert r3.ops[0].reason == "stub_exhausted"
