"""
Tests covering COG requirements:
COG-REPL-01, COG-REPL-02, COG-REPL-03, COG-REPL-04, COG-REPL-05
"""
from __future__ import annotations

import io
import json

import pytest
from rich.console import Console

from voss.harness.agent import (
    COGNITION_BUDGET_TOKENS,
    _compose_cognition_prompt,
)
from voss.harness.cognition import CognitionBundle
from voss.harness.cognition_schemas import ConstraintRule, ConstraintsConfig
from voss.harness.render import JsonRenderer, TtyRenderer


def test_cognition_status_line_tty() -> None:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120, highlight=False)
    r = TtyRenderer(console=console)
    r.show_cognition(architecture_tokens=1200, constraints_count=2)
    out = buf.getvalue()
    assert "cognition: architecture (1.2k) + 2 constraints" in out


def test_cognition_loaded_ndjson_event(capsys) -> None:
    r = JsonRenderer()
    r.show_cognition(
        architecture_tokens=1200,
        constraints_count=2,
        plans_loaded=0,
        decisions_loaded=0,
    )
    out = capsys.readouterr().out.strip()
    evt = json.loads(out)
    assert evt == {
        "v": 1,
        "type": "cognition_loaded",
        "architecture_tokens": 1200,
        "constraints_count": 2,
        "plans_loaded": 0,
        "decisions_loaded": 0,
    }


def test_cognition_overflow_truncates_constraints(capsys) -> None:
    # Bundle whose architecture is "large" by the stub token counter.
    bundle = CognitionBundle(
        initialized=True,
        architecture_md="ARCH BODY\n" * 200,
        architecture_tokens=8000,
        constraints=ConstraintsConfig(
            rules=[ConstraintRule(forbid=["foo"]), ConstraintRule(custom="bar")]
        ),
    )

    # Stub token counter: report 8000 unconditionally → triggers overflow.
    def stub_tok(text: str, *, model: str) -> int:
        return 8000

    r = JsonRenderer()
    text = _compose_cognition_prompt(
        bundle, model="m", token_count_fn=stub_tok, renderer=r
    )

    # Constraints dropped from prompt entirely.
    assert "## Constraints" not in text
    assert "constraints truncated due to budget" in text
    # Architecture remains.
    assert "ARCH BODY" in text

    out = capsys.readouterr().out.strip()
    evt = json.loads(out)
    assert evt["type"] == "cognition_overflow"
    assert evt["architecture_tokens"] == 8000
    assert evt["budget"] == COGNITION_BUDGET_TOKENS


@pytest.mark.skip(reason="Wave 4 — pending plan M2-06")
def test_drift_hint_printed_non_blocking() -> None:
    pass


def test_bad_yaml_loud_failure(git_repo) -> None:
    from voss.harness.cognition import load

    voss = git_repo / ".voss"
    voss.mkdir()
    (voss / "architecture.md").write_text(
        "---\ngit_head: abc\nanalyzed_at: 2026-05-10T00:00:00+00:00\n"
        "file_count: 1\nanalyzer_version: 1\n---\n# Arch\n"
    )
    (voss / "project.json").write_text(
        '{"name": "t", "primary_language": "python"}'
    )
    (voss / "constraints.yml").write_text("rules: [\n")  # malformed YAML

    b = load(git_repo)
    assert b.load_errors, "load_errors should be populated on malformed YAML"
    assert any("constraints.yml" in e for e in b.load_errors)
