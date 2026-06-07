"""O3-03 Task 2: DeterministicReviewerStub + production-import guard."""
from __future__ import annotations

import subprocess

from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.verdict import Reviewer, ReviewerVerdict


class TestDeterministicReviewerStub:
    def test_satisfies_reviewer_protocol(self):
        stub = DeterministicReviewerStub()
        assert isinstance(stub, Reviewer)

    def test_returns_configured_verdict(self):
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        v = stub.review(None)
        assert isinstance(v, ReviewerVerdict)
        assert v.conf == 0.99
        assert v.verdict == "pass"
        assert v.tier == "strong"
        assert v.source == "B"
        assert v.notes == "(deterministic stub)"
        assert v.evidence_refs == ()

    def test_custom_conf_and_verdict(self):
        stub = DeterministicReviewerStub(conf=0.5, verdict="fail", tier="fast", source="A")
        v = stub.review("any card")
        assert v.conf == 0.5
        assert v.verdict == "fail"
        assert v.tier == "fast"
        assert v.source == "A"


class TestProductionImportGuard:
    def test_no_production_file_imports_stub(self):
        """Grep voss/ (excluding stub.py itself) for stub imports.

        Allowlist: voss/harness/cli.py wires the stub reviewers into the
        `voss team run` stub smoke-run (V7-02, SPEC "exits 0 on stub provider").
        That command is an intentional stub-backed composition entrypoint, not a
        real review path; every OTHER production file must stay stub-free so the
        always-pass stub can never silently back a genuine review decision.
        """
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py",
             "voss.harness.board.stub", "voss/"],
            capture_output=True, text=True,
        )
        _ALLOWLIST = ("voss/harness/board/stub.py", "voss/harness/cli.py")
        lines = [
            l for l in result.stdout.strip().split("\n")
            if l and not any(allowed in l for allowed in _ALLOWLIST)
        ]
        assert lines == [], f"production files import stub: {lines}"
