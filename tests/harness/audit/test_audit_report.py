"""V9 RED scaffolds for build_audit_report (VAUD-02/03/04/05/06/07/10).

Pins the planned ``voss.harness.audit.report.build_audit_report`` surface.
Expected RED until V9-03 lands. Uses tmp_path; never writes to the real
``.voss/`` directory. No xfail masking.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.harness.audit.test_o6_fixtures import ROOT_ID, build_fixture_tree


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    build_fixture_tree(tmp_path)
    return tmp_path


class TestPrdSections:
    def test_all_prd_sections_present(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report

        report = build_audit_report(fixture_root)
        assert report.idea == "fixture idea"
        assert len(report.principles) > 0          # non-empty tuple
        assert report.team_config is not None
        assert report.snapshot is not None
        assert report.review_sidecars is not None
        assert report.run_final is not None
        # signoff_ack / calibration / sections_missing fields exist.
        assert hasattr(report, "signoff_ack")
        assert report.calibration is not None
        assert isinstance(report.sections_missing, tuple)

    def test_missing_source_renders_none_not_crash(self, tmp_path: Path):
        from voss.harness.audit.report import build_audit_report

        # Build a tree, then delete run-final.json so the Goal source is absent.
        build_fixture_tree(tmp_path)
        (tmp_path / ".voss" / "sessions" / ROOT_ID / "run-final.json").unlink()
        report = build_audit_report(tmp_path)        # must not raise
        assert report.idea == ""
        assert any("oal" in s for s in report.sections_missing)  # "Goal"


class TestClaimsVsEvidence:
    def test_claims_vs_evidence(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report

        report = build_audit_report(fixture_root)
        # node_killed_01 has an em.ticket but NO .review.json sidecar.
        assert "node_killed_01" in report.unsupported_claims
        # node_ab_block1 HAS a sidecar — its evidence is reachable.
        assert "node_ab_block1" not in report.unsupported_claims


class TestBudgetSection:
    def test_budget_section(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report

        report = build_audit_report(fixture_root)
        for node in report.snapshot.nodes:
            assert "limit" in node.envelope
            assert "spent" in node.envelope


class TestScopeDenials:
    def test_scope_denials(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report, scope_denials

        # Inject a node carrying rejected_raises and re-run the report.
        run_dir = fixture_root / ".voss" / "sessions" / ROOT_ID
        node = {
            "id": "node_denied_1",
            "root_id": ROOT_ID,
            "parent_run_id": ROOT_ID,
            "envelope": {"limit": 5000, "spent": 0},
            "terminal_state": {"exit_reason": "done", "final": "ok"},
            "created_at": "2026-05-20T10:01:00+00:00",
            "ended_at": "2026-05-20T10:06:00+00:00",
            "rejected_raises": [
                {
                    "attempted_delta": 1000,
                    "reason": "over ceiling",
                    "attempted_at": "2026-05-20T10:05:00+00:00",
                }
            ],
            "transitions": [],
            "retry_notes": [],
        }
        (run_dir / "node_denied_1.json").write_text(json.dumps(node, indent=2))
        report = build_audit_report(fixture_root)
        # rejected_raises lives on the raw node dict (NOT on the frozen
        # AuditNode); report.py surfaces it via the scope_denials helper.
        denials = scope_denials(report.snapshot, run_dir)
        reasons = [d["reason"] for d in denials]
        assert "over ceiling" in reasons
        denied = [d for d in denials if d["node_id"] == "node_denied_1"]
        assert denied and denied[0]["attempted_delta"] == 1000


class TestReviewerSections:
    def test_reviewer_sections_separate(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report

        report = build_audit_report(fixture_root)
        sidecar = report.review_sidecars["node_ab_block1"]
        assert sidecar["a_verification"]["result"] == "pass"
        assert sidecar["b_verdict"]["verdict"] == "block"


class TestLineage:
    def test_lineage(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report

        report = build_audit_report(fixture_root)
        # Killed card reachable.
        kill_ids = {k.killed_node_id for k in report.snapshot.kills}
        assert "node_killed_01" in kill_ids
        # Rescope lineage reachable with routing rationale.
        rescopes = report.snapshot.rescopes
        assert any(
            r.predecessor_card_id == "tk_resc" and r.successor_card_id == "tk_succ"
            for r in rescopes
        )
        assert len(report.snapshot.routings) >= 1


class TestResidualRisk:
    def test_residual_risk(self, fixture_root: Path):
        from voss.harness.audit.report import build_audit_report

        report = build_audit_report(fixture_root)
        assert report.snapshot.leak6.status == "accepted_gap"
