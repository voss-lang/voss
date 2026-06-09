"""V9 RED scaffolds for the audit renderers (VAUD-08).

Pins ``voss.harness.audit.render.render_text/render_markdown/render_json``.
Expected RED until V9-04 lands. Uses tmp_path; never writes to the real
``.voss/`` directory. No xfail masking.

Note: ``render_json`` round-trips tuples as JSON lists (dataclasses.asdict
coerces tuple -> list). Round-trip assertions check for lists, not tuples.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.harness.audit.test_o6_fixtures import build_fixture_tree


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    build_fixture_tree(tmp_path)
    return tmp_path


class TestMarkdown:
    def test_markdown_has_section_headers(self, tmp_path: Path):
        from voss.harness.audit.render import render_markdown
        from voss.harness.audit.report import build_audit_report

        # Drop run-final.json so the Goal section has no source -> _none_.
        build_fixture_tree(tmp_path)
        (tmp_path / ".voss" / "sessions" / "root_aabbcc0001" / "run-final.json").unlink()
        md = render_markdown(build_audit_report(tmp_path))
        assert md.startswith("#") or "\n#" in md  # has markdown headers
        assert "_none_" in md                       # missing section sentinel

    def test_markdown_render_stable_bytes(self, fixture_root: Path):
        from voss.harness.audit.render import render_markdown
        from voss.harness.audit.report import build_audit_report

        md = render_markdown(build_audit_report(fixture_root))

        assert md == (
            "# Audit: root_aabbcc0001\n"
            "\n"
            "## §1 Goal\n"
            "\n"
            "fixture idea\n"
            "## §2 Active Team\n"
            "\n"
            "source: default roster (not persisted)\n"
            "roster: _none_\n"
            "## §3 Principles\n"
            "\n"
            "- diff: Make the smallest diff that solves the task.\n"
            "- evidence: No factual claim without evidence.\n"
            "- tests: Tests prove behavior, not coverage theater.\n"
            "- scope: Do not edit outside assigned scope.\n"
            "- review: Review intent and correctness before style.\n"
            "- reversibility: Prefer reversible changes unless the user approves risk.\n"
            "## §4 Scope and Budget\n"
            "\n"
            "- node_ab_block1: spent 0/5000\n"
            "- node_done_0001: spent 0/5000\n"
            "- node_killed_01: spent 0/5000\n"
            "- node_misroute1: spent 0/5000\n"
            "- node_rescoped_1: spent 0/5000\n"
            "- node_successor1: spent 0/5000\n"
            "- node_timeout_1: spent 0/5000\n"
            "- root_aabbcc0001: spent 0/5000\n"
            "## §5 Board Timeline\n"
            "\n"
            "- node_ab_block1: InReview -> Done (passed)\n"
            "- node_ab_block1: Done -> Blocked (refused)\n"
            "- node_done_0001: Backlog -> Done (passed)\n"
            "- node_misroute1: InReview -> InProgress (refused)\n"
            "- node_misroute1: Backlog -> Done (passed)\n"
            "- node_successor1: Backlog -> Done (passed)\n"
            "- node_timeout_1: InProgress -> Blocked (refused)\n"
            "## §6 Work Cards\n"
            "\n"
            "- node_ab_block1 [Blocked]\n"
            "- node_done_0001 [Done]\n"
            "- node_killed_01 [Blocked]  [UNSUPPORTED CLAIM]\n"
            "- node_misroute1 [Done]\n"
            "- node_rescoped_1 [Blocked]  [UNSUPPORTED CLAIM]\n"
            "- node_successor1 [Done]  [UNSUPPORTED CLAIM]\n"
            "- node_timeout_1 [Blocked]  [UNSUPPORTED CLAIM]\n"
            "## §7 Agent Actions\n"
            "\n"
            "- node_ab_block1: em.ticket, em.routing, board.transition, board.transition\n"
            "- node_done_0001: em.ticket, em.routing, board.transition\n"
            "- node_killed_01: em.ticket, em.routing, em.kill\n"
            "- node_misroute1: em.ticket, em.routing, board.transition, board.transition\n"
            "- node_rescoped_1: em.ticket, em.routing, em.rescope\n"
            "- node_successor1: em.ticket, em.routing, board.transition\n"
            "- node_timeout_1: em.ticket, em.routing, board.transition\n"
            "- root_aabbcc0001: em.run_final, audit.leak6\n"
            "## §8 Diff Summary\n"
            "\n"
            "_none_\n"
            "## §9 Tests and Evals\n"
            "\n"
            "_none_\n"
            "## §10 Reviewer-A Verification\n"
            "\n"
            "- node_ab_block1: result=pass (test_ab)\n"
            "- node_done_0001: result=pass (test_done)\n"
            "- node_misroute1: result=pass (test_misroute)\n"
            "## §11 Reviewer-B Verdict\n"
            "\n"
            "- node_ab_block1: verdict=block conf=0.3 tier=strong\n"
            "- node_done_0001: verdict=pass conf=0.92 tier=fast\n"
            "- node_misroute1: verdict=fail conf=0.55 tier=fast\n"
            "## §12 Blocked/Killed/Rescoped Items\n"
            "\n"
            "- killed: node_killed_01 (fixture kill rationale)\n"
            "- rescoped: tk_resc -> tk_succ\n"
            "## §13 Evidence References\n"
            "\n"
            "- test_a_1\n"
            "- test_b_1\n"
            "## §14 Residual Risks\n"
            "\n"
            "Leak-6: accepted_gap — no standup-to-memory writer exists in O1-O5 substrate\n"
            "## §15 Final Human Decision\n"
            "\n"
            "decision: approve\n"
        )


class TestJson:
    def test_json_round_trips(self, fixture_root: Path):
        from voss.harness.audit.render import render_json
        from voss.harness.audit.report import build_audit_report

        data = json.loads(render_json(build_audit_report(fixture_root)))
        assert isinstance(data, dict)
        assert data["run_id"] == "root_aabbcc0001"
        assert data["idea"] == "fixture idea"
        assert "snapshot" in data
        # tuples are coerced to lists by dataclasses.asdict.
        assert isinstance(data["snapshot"]["nodes"], list)


class TestDeterminism:
    def test_determinism(self, fixture_root: Path):
        from voss.harness.audit.render import render_json
        from voss.harness.audit.report import build_audit_report

        out1 = render_json(build_audit_report(fixture_root))
        out2 = render_json(build_audit_report(fixture_root))
        assert out1 == out2

    def test_text_render_stable(self, fixture_root: Path):
        from voss.harness.audit.render import render_text
        from voss.harness.audit.report import build_audit_report

        out1 = render_text(build_audit_report(fixture_root))
        out2 = render_text(build_audit_report(fixture_root))
        assert out1 == out2
