"""T1-01: RunRecorder.begin_iteration / end_iteration + finalize wiring.

Locks the per-iteration capture API. Tests cover behavior, validation, and
finalize forwarding to RunRecord.iterations / iteration_count / exit_reason
/ iteration_total_*_tokens.

No provider, no git. Plan stub is a SimpleNamespace with model_dump.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.recorder import RunRecorder


def _plan_stub() -> SimpleNamespace:
    return SimpleNamespace(
        model_dump=lambda: {
            "rationale": "r",
            "steps": [],
            "confidence": 0.9,
            "final_when_done": "f",
        }
    )


class TestBeginIteration:
    def test_first_call_returns_index_zero_with_started_at(self) -> None:
        rec = RunRecorder.start()
        it = rec.begin_iteration()
        assert it.index == 0
        assert it.started_at != ""
        assert it.ended_at == ""

    def test_two_calls_yield_sequential_indices(self) -> None:
        rec = RunRecorder.start()
        a = rec.begin_iteration()
        b = rec.begin_iteration()
        assert a.index == 0
        assert b.index == 1


class TestEndIteration:
    def test_populates_open_iteration(self) -> None:
        rec = RunRecorder.start()
        rec.begin_iteration()
        rec.end_iteration(
            plan=_plan_stub(),
            tool_results=[{"tool": "fs_read", "path": "a.py"}],
            cost_usd=0.012,
            prompt_tokens=100,
            completion_tokens=50,
            exit_reason=None,
        )
        it = rec._iterations[0]
        assert it.plan == {
            "rationale": "r",
            "steps": [],
            "confidence": 0.9,
            "final_when_done": "f",
        }
        assert it.tool_results[0]["tool"] == "fs_read"
        assert it.cost_usd == 0.012
        assert it.prompt_tokens == 100
        assert it.completion_tokens == 50
        assert it.ended_at != ""
        assert it.exit_reason is None

    def test_invalid_exit_reason_raises(self) -> None:
        rec = RunRecorder.start()
        rec.begin_iteration()
        with pytest.raises(ValueError):
            rec.end_iteration(
                plan=_plan_stub(),
                tool_results=[],
                cost_usd=0.0,
                prompt_tokens=0,
                completion_tokens=0,
                exit_reason="quit",
            )


class TestFinalizeForwarding:
    def test_finalize_forwards_iterations_and_count(self, tmp_path: Path) -> None:
        rec = RunRecorder.start()
        rec.begin_iteration()
        rec.end_iteration(
            plan=_plan_stub(),
            tool_results=[],
            cost_usd=0.012,
            prompt_tokens=100,
            completion_tokens=50,
        )
        out = rec.finalize(tmp_path, cost_usd=0.012)
        assert len(out.iterations) == 1
        assert out.iteration_count == 1
        assert out.iteration_total_prompt_tokens == 100
        assert out.iteration_total_completion_tokens == 50

    def test_finalize_propagates_exit_reason(self, tmp_path: Path) -> None:
        rec = RunRecorder.start()
        rec.begin_iteration()
        rec.end_iteration(
            plan=_plan_stub(),
            tool_results=[],
            cost_usd=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            exit_reason="done",
        )
        out = rec.finalize(tmp_path, cost_usd=0.0, exit_reason="done")
        assert out.exit_reason == "done"

    def test_finalize_rejects_invalid_exit_reason(self, tmp_path: Path) -> None:
        rec = RunRecorder.start()
        with pytest.raises(ValueError):
            rec.finalize(tmp_path, cost_usd=0.0, exit_reason="quit")

    def test_finalize_defaults_preserve_pre_t1_callers(self, tmp_path: Path) -> None:
        # No iterations opened, no exit_reason — matches pre-T1 caller shape.
        rec = RunRecorder.start()
        out = rec.finalize(tmp_path, cost_usd=0.05)
        assert out.iterations == []
        assert out.iteration_count == 0
        assert out.exit_reason is None
        assert out.iteration_total_prompt_tokens == 0
        assert out.iteration_total_completion_tokens == 0
