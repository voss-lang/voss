"""T1-05 Task 1: pure helpers for the iteration loop.

Constants + four functions land in agent.py before _run_turn_exec is
rewritten. Behavior is unit-testable in isolation — no provider, no IO.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from voss.harness.agent import (
    HALTED_BUDGET_FINAL,
    HALTED_MAX_ITER_FINAL,
    PLAN_LOOP_SYSTEM,
    _build_iter_rider,
    _compose_loop_system,
    _is_done_plan,
    _serialize_iter_for_replay,
)
from voss.harness.session import IterationRecord


class TestConstants:
    def test_halted_max_iter_exact_string(self) -> None:
        assert HALTED_MAX_ITER_FINAL == "halted: max-iter"

    def test_halted_budget_exact_string(self) -> None:
        assert HALTED_BUDGET_FINAL == "halted: budget"

    def test_plan_loop_system_carries_placeholder(self) -> None:
        assert "{max_iterations}" in PLAN_LOOP_SYSTEM
        # Verbatim signposts the prompt promises.
        assert "iteration N" not in PLAN_LOOP_SYSTEM  # uses placeholder, not literal
        assert "steps: []" in PLAN_LOOP_SYSTEM
        assert "final_when_done" in PLAN_LOOP_SYSTEM


class TestComposeLoopSystem:
    def test_fills_placeholder(self) -> None:
        out = _compose_loop_system(8)
        assert "{max_iterations}" not in out
        assert "at most 8 iterations" in out

    def test_uses_str_replace_not_fstring(self) -> None:
        # If we did f-string the {{step_0}} curly-escapes would explode.
        out = _compose_loop_system(8)
        assert "{step_0}" in out  # double-curly survives as single in output


class TestBuildIterRider:
    def test_first_iter_no_priors(self) -> None:
        rider = _build_iter_rider(
            index=0,
            max_iterations=8,
            tokens_used=0,
            token_budget=60_000,
            prior_iters=[],
        )
        assert "Iteration 1 of 8" in rider
        assert "0/60000 used" in rider
        assert "Prior iterations" not in rider

    def test_third_iter_with_two_priors(self) -> None:
        priors = [
            IterationRecord(
                index=0,
                plan={"rationale": "look at code", "steps": [{"name": "fs_read"}]},
                tool_results=[{"name": "fs_read", "result": "ok"}],
            ),
            IterationRecord(
                index=1,
                plan={"rationale": "edit", "steps": [{"name": "fs_edit"}]},
                tool_results=[{"name": "fs_edit", "result": "ok"}],
            ),
        ]
        rider = _build_iter_rider(
            index=2,
            max_iterations=8,
            tokens_used=1234,
            token_budget=60_000,
            prior_iters=priors,
        )
        assert "Iteration 3 of 8" in rider
        assert "- Iter 0:" in rider
        assert "- Iter 1:" in rider
        assert "1 steps, 1 tools" in rider

    def test_prefers_final_when_done_for_snippet(self) -> None:
        priors = [
            IterationRecord(
                index=0,
                plan={
                    "rationale": "rat-line",
                    "final_when_done": "the actual final answer",
                    "steps": [],
                },
                tool_results=[],
            )
        ]
        rider = _build_iter_rider(
            index=1,
            max_iterations=8,
            tokens_used=0,
            token_budget=60_000,
            prior_iters=priors,
        )
        assert "the actual final answer" in rider
        assert "rat-line" not in rider


class TestSerializeIterForReplay:
    def test_returns_assistant_and_user_pair(self) -> None:
        ir = IterationRecord(
            index=0,
            plan={
                "rationale": "do the thing",
                "steps": [{"name": "fs_read", "args": {"path": "a.py"}}],
                "final_when_done": "",
            },
            tool_results=[
                {"name": "fs_read", "args": {"path": "a.py"}, "result": "contents"}
            ],
        )
        assistant, user = _serialize_iter_for_replay(ir)
        assert assistant["role"] == "assistant"
        payload = json.loads(assistant["content"])
        assert payload["rationale"] == "do the thing"
        assert payload["steps"][0]["name"] == "fs_read"

        assert user["role"] == "user"
        assert user["content"].startswith("Tool results for iteration 0:")
        assert "fs_read" in user["content"]
        assert "contents" in user["content"]

    def test_redacts_sensitive_args(self) -> None:
        ir = IterationRecord(
            index=1,
            plan={"rationale": "x", "steps": [], "final_when_done": ""},
            tool_results=[
                {
                    "name": "shell_run",
                    "args": {"api_key": "sk-secret"},
                    "result": "ok",
                }
            ],
        )
        _, user = _serialize_iter_for_replay(ir)
        assert "sk-secret" not in user["content"]


class TestIsDonePlan:
    def test_done_when_steps_empty_and_final_set(self) -> None:
        p = SimpleNamespace(steps=[], final_when_done="the answer", confidence=0.9)
        assert _is_done_plan(p) is True

    def test_not_done_when_steps_non_empty(self) -> None:
        p = SimpleNamespace(
            steps=[SimpleNamespace(name="x")],
            final_when_done="the answer",
            confidence=0.9,
        )
        assert _is_done_plan(p) is False

    def test_not_done_when_final_empty(self) -> None:
        assert _is_done_plan(
            SimpleNamespace(steps=[], final_when_done="", confidence=0.9)
        ) is False
        assert _is_done_plan(
            SimpleNamespace(steps=[], final_when_done="   ", confidence=0.9)
        ) is False
