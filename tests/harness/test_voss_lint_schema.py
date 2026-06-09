import io
import json
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from voss.harness.skill_registry import default_skill_registry
from voss.harness.voss_lint_schema import (
    FINDING_FIELDS,
    LintFinding,
    parse_lint_json,
    render_lint_summary,
)


def _valid_payload() -> dict:
    return {
        "version": 1,
        "findings": [
            {
                "file": "bad.voss",
                "line": 3,
                "col": 12,
                "rule": "ANLY001",
                "severity": "warning",
                "msg": "unguarded probable returned as concrete value",
                "hint": None,
            }
        ],
    }


def test_voss_lint_valid_version_1_json_parses() -> None:
    findings = parse_lint_json(json.dumps(_valid_payload()))

    assert findings == [
        LintFinding(
            file="bad.voss",
            line=3,
            col=12,
            rule="ANLY001",
            severity="warning",
            msg="unguarded probable returned as concrete value",
            hint=None,
        )
    ]


def test_voss_lint_summary_renders_exact_template_bytes() -> None:
    findings = [
        LintFinding(
            file="bad.voss",
            line=3,
            col=12,
            rule="ANLY001",
            severity="warning",
            msg="bad probable",
            hint="guard it",
        ),
        LintFinding(
            file="ok.voss",
            line=4,
            col=2,
            rule="STYLE001",
            severity="info",
            msg="style note",
            hint=None,
        ),
    ]

    assert render_lint_summary(findings) == (
        "bad.voss:3:12: warning ANLY001: bad probable\n"
        "  hint: guard it\n"
        "ok.voss:4:2: info STYLE001: style note"
    )


def test_voss_lint_missing_field_fails() -> None:
    payload = _valid_payload()
    del payload["findings"][0]["hint"]

    with pytest.raises(ValueError, match="missing fields: hint"):
        parse_lint_json(json.dumps(payload))


def test_voss_lint_extra_field_fails() -> None:
    payload = _valid_payload()
    payload["findings"][0]["end_line"] = 4

    with pytest.raises(ValueError, match="extra fields: end_line"):
        parse_lint_json(json.dumps(payload))


def test_voss_lint_bad_version_fails() -> None:
    payload = _valid_payload()
    payload["version"] = 2

    with pytest.raises(ValueError, match="version must be 1"):
        parse_lint_json(json.dumps(payload))


def test_voss_lint_skill_registry_entry_is_read_only() -> None:
    entry = default_skill_registry().get("voss-lint-as-skill")

    assert entry is not None
    assert entry.mutating is False


def test_voss_lint_skill_output_parses_with_consumer(tmp_path: Path) -> None:
    from voss.harness.skills.voss_lint_as_skill import run

    (tmp_path / "bad.voss").write_text(
        'fn classify(text: string) -> string {\n'
        '    let intent: probable<string> = ask("Classify: " + text)\n'
        "    return intent\n"
        "}\n"
    )

    buf = io.StringIO()
    with patch("click.echo", side_effect=lambda s, **kw: buf.write(str(s) + "\n")):
        run(
            cwd=tmp_path,
            provider=None,
            history=None,
            record=types.SimpleNamespace(model="fake", id="t"),
            renderer=None,
            tools=None,
            gate=None,
            args=[str(tmp_path)],
        )

    findings = parse_lint_json(buf.getvalue())

    assert findings
    assert [field for field in FINDING_FIELDS] == [
        "file",
        "line",
        "col",
        "rule",
        "severity",
        "msg",
        "hint",
    ]
    assert any(finding.rule == "ANLY001" for finding in findings)
