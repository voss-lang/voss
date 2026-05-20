"""O5-01 TDD: EXIT_REASONS additive extension with 'killed'."""
from __future__ import annotations

from voss.harness.session import EXIT_REASONS, RunRecord


class TestExitReasonsKilled:
    def test_killed_is_member(self):
        assert "killed" in EXIT_REASONS

    def test_existing_members_preserved(self):
        for m in ("done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout"):
            assert m in EXIT_REASONS, f"missing: {m}"

    def test_is_frozenset(self):
        assert isinstance(EXIT_REASONS, frozenset)

    def test_run_record_accepts_killed(self):
        rec = RunRecord(id="x", started_at="", ended_at="", exit_reason="killed")
        assert rec.exit_reason == "killed"
