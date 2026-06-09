"""T1-01: IterationRecord + additive RunRecord fields.

Locks the additive-only schema substrate that the iteration loop writes to.
No behavior here — purely schema shape, defaults, and old-fixture round-trip.
"""
from __future__ import annotations

import dataclasses

import pytest

from voss.harness.session import EXIT_REASONS, IterationRecord, RunRecord


class TestIterationRecord:
    def test_constructs_with_all_defaults_except_index(self) -> None:
        rec = IterationRecord(index=0)
        assert rec.index == 0
        assert rec.plan == {}
        assert rec.tool_results == []
        assert rec.cost_usd == 0.0
        assert rec.prompt_tokens == 0
        assert rec.completion_tokens == 0
        assert rec.started_at == ""
        assert rec.ended_at == ""
        assert rec.exit_reason is None

    def test_constructs_with_full_payload(self) -> None:
        rec = IterationRecord(
            index=0,
            plan={"rationale": "r", "steps": []},
            tool_results=[{"tool": "fs_read", "path": "a.py"}],
            cost_usd=0.012,
            prompt_tokens=100,
            completion_tokens=50,
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:00:01+00:00",
            exit_reason=None,
        )
        assert rec.index == 0
        assert rec.tool_results[0]["tool"] == "fs_read"

    def test_asdict_produces_json_safe_nested_dict(self) -> None:
        rec = IterationRecord(index=0, plan={"k": "v"})
        d = dataclasses.asdict(rec)
        assert isinstance(d, dict)
        assert d["plan"] == {"k": "v"}


class TestRunRecordAdditive:
    def test_existing_constructor_signature_still_works(self) -> None:
        rec = RunRecord(id="x", started_at="t0", ended_at="t1")
        assert rec.iterations == []
        assert rec.iteration_count == 0
        assert rec.exit_reason is None
        assert rec.iteration_total_prompt_tokens == 0
        assert rec.iteration_total_completion_tokens == 0

    def test_iterations_round_trip_through_asdict(self) -> None:
        it = IterationRecord(index=0, plan={"r": "x"})
        rec = RunRecord(id="x", started_at="t0", ended_at="t1", iterations=[it])
        d = dataclasses.asdict(rec)
        assert isinstance(d["iterations"], list)
        # nested IterationRecord serialized to plain dict, not the dataclass.
        assert isinstance(d["iterations"][0], dict)
        assert d["iterations"][0]["plan"] == {"r": "x"}

    def test_all_four_exit_reasons_accepted(self) -> None:
        for reason in ("done", "max-iter", "budget", "interrupt"):
            rec = RunRecord(id="x", started_at="a", ended_at="b", exit_reason=reason)
            assert rec.exit_reason == reason

    def test_exit_reasons_constant_is_authoritative(self) -> None:
        # Additive history: T2-03 "batch-invariant"; 74a328f "timeout"
        # (session timeout support); 6361c51 "error"; a666646 "killed".
        assert EXIT_REASONS == frozenset(
            {
                "done",
                "max-iter",
                "budget",
                "interrupt",
                "batch-invariant",
                "timeout",
                "killed",
                "error",
            }
        )


class TestRunRecordRejectsInvalidExitReason:
    def test_runrecord_rejects_invalid_exit_reason(self) -> None:
        with pytest.raises(ValueError) as exc:
            RunRecord(id="x", started_at="a", ended_at="b", exit_reason="quit")
        msg = str(exc.value)
        for reason in ("done", "max-iter", "budget", "interrupt"):
            assert reason in msg


class TestPreT1FixtureRoundTrip:
    def test_runrecord_old_fixture_roundtrip(self) -> None:
        old_dict = {
            "id": "abc123",
            "started_at": "2025-12-01T00:00:00+00:00",
            "ended_at": "2025-12-01T00:00:10+00:00",
            "goal": "do the thing",
            "plan": {"rationale": "r", "steps": []},
            "inspected": ["a.py"],
            "changed": ["b.py"],
            "cost_usd": 0.05,
        }
        rec = RunRecord(**old_dict)
        assert rec.iterations == []
        assert rec.iteration_count == 0
        assert rec.exit_reason is None
        assert rec.iteration_total_prompt_tokens == 0
        assert rec.iteration_total_completion_tokens == 0
        # Pre-T1 fields preserved.
        assert rec.goal == "do the thing"
        assert rec.inspected == ["a.py"]
        assert rec.cost_usd == 0.05
