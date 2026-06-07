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
