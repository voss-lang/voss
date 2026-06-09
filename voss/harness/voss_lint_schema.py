"""Consumer for the frozen `voss-lint-as-skill` JSON schema."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from voss.template_render import render_package_template


FINDING_FIELDS = ("file", "line", "col", "rule", "severity", "msg", "hint")


@dataclass(frozen=True)
class LintFinding:
    file: str
    line: int
    col: int
    rule: str
    severity: str
    msg: str
    hint: str | None


def parse_lint_json(text: str) -> list[LintFinding]:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("lint JSON must be an object")
    if payload.get("version") != 1:
        raise ValueError("lint JSON version must be 1")

    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ValueError("lint JSON findings must be a list")

    parsed: list[LintFinding] = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValueError(f"finding {index} must be an object")

        keys = tuple(finding)
        expected = set(FINDING_FIELDS)
        actual = set(keys)
        missing = expected - actual
        extra = actual - expected
        if missing:
            raise ValueError(
                f"finding {index} is missing fields: {', '.join(sorted(missing))}"
            )
        if extra:
            raise ValueError(
                f"finding {index} has extra fields: {', '.join(sorted(extra))}"
            )
        if keys != FINDING_FIELDS:
            raise ValueError(
                f"finding {index} fields must be in order: {', '.join(FINDING_FIELDS)}"
            )

        parsed.append(_lint_finding_from_dict(finding))

    return parsed


def render_lint_summary(findings: list[LintFinding]) -> str:
    if not findings:
        return "No lint findings."

    return render_package_template(
        "voss",
        "templates/lint/summary.txt.jinja",
        {"findings": findings},
    ).removesuffix("\n")


def _lint_finding_from_dict(finding: dict[str, Any]) -> LintFinding:
    return LintFinding(
        file=finding["file"],
        line=finding["line"],
        col=finding["col"],
        rule=finding["rule"],
        severity=finding["severity"],
        msg=finding["msg"],
        hint=finding["hint"],
    )
