"""O5-03: EMPlanResponse schema — LENIENT posture, Op discrimination, max_length."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from voss.harness.em.schema import (
    CreateTicketOp, DispatchCardOp, EMPlanResponse,
    KillCardOp, NoopOp, RescopeCardOp, SetACOp, SetDoDOp,
)


class TestSchemaLenient:
    def test_unknown_top_level_field_dropped(self):
        r = EMPlanResponse.model_validate({
            "ops": [], "reasoning": "", "extend_budget": 50000,
        })
        assert not hasattr(r, "extend_budget")
        assert r.ops == []

    def test_unknown_op_field_dropped(self):
        r = EMPlanResponse.model_validate({
            "ops": [{
                "op": "create_ticket", "original_idea": "x",
                "acceptance_criteria": [], "dod": [], "worker_role": "backend",
                "extend_budget": 50000,
            }],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], CreateTicketOp)
        assert not hasattr(r.ops[0], "extend_budget")


class TestDiscriminatorRouting:
    def test_create_ticket_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "create_ticket", "original_idea": "x",
                     "acceptance_criteria": [], "dod": [], "worker_role": "be"}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], CreateTicketOp)

    def test_kill_card_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "kill_card", "card_id": "c1", "rationale_text": "bad"}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], KillCardOp)

    def test_dispatch_card_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "dispatch_card", "card_id": "c1", "role_id": "be",
                     "task": "build", "rationale_text": "why",
                     "candidates_considered": ["be"]}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], DispatchCardOp)

    def test_rescope_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "rescope_card", "card_id": "c1",
                     "new_worker_role": "fe", "rationale_text": "narrow"}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], RescopeCardOp)

    def test_set_ac_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "set_ac", "card_id": "c1", "acceptance_criteria": ["a"]}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], SetACOp)

    def test_set_dod_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "set_dod", "card_id": "c1", "dod": ["d"]}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], SetDoDOp)

    def test_noop_routes(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "noop", "reason": "nothing to do"}],
            "reasoning": "",
        })
        assert isinstance(r.ops[0], NoopOp)
        assert r.ops[0].reason == "nothing to do"

    def test_noop_default_reason(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "noop"}], "reasoning": "",
        })
        assert r.ops[0].reason == ""


class TestMaxLength:
    def test_21_ops_rejected(self):
        ops = [{"op": "noop"} for _ in range(21)]
        with pytest.raises(ValidationError):
            EMPlanResponse.model_validate({"ops": ops, "reasoning": ""})

    def test_20_ops_accepted(self):
        ops = [{"op": "noop"} for _ in range(20)]
        r = EMPlanResponse.model_validate({"ops": ops, "reasoning": ""})
        assert len(r.ops) == 20


class TestConfidenceHintRange:
    def test_valid_range(self):
        r = EMPlanResponse.model_validate({
            "ops": [{"op": "dispatch_card", "card_id": "c", "role_id": "be",
                     "task": "t", "rationale_text": "r",
                     "candidates_considered": [], "confidence_hint": 0.5}],
            "reasoning": "",
        })
        assert r.ops[0].confidence_hint == 0.5

    def test_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            EMPlanResponse.model_validate({
                "ops": [{"op": "dispatch_card", "card_id": "c", "role_id": "be",
                         "task": "t", "rationale_text": "r",
                         "candidates_considered": [], "confidence_hint": 1.5}],
                "reasoning": "",
            })
