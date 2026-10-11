from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

from tests.harness.audit.test_audit_judgments import ROOT, _receipt, build_ledger
from tests.harness.audit.test_o6_fixtures import build_fixture_tree
from tests.harness.review_fakes import choice_body, install_jev
from tests.harness.test_decision_review_packet import _git
from voss.harness import decision_review as dr
from voss.harness.audit.render import _judgments_body, render_json, render_markdown, render_text
from voss.harness.audit.report import build_audit_report
from voss.harness.session_tree import write_judgments_sidecar
from voss_runtime.judgments import JudgmentLedger

SENTINEL = "SENTINEL-j406"
ABSTAIN = {"supported": 0.05, "contradicted": 0.05, "insufficient_evidence": 0.9}
CURRENT = "AC-1  supported  P(supported)=0.90  current"
STALE = "AC-1  supported  P(supported)=0.90  stale: work changed since this was checked"


@pytest.fixture(autouse=True)
def project(monkeypatch, tmp_path) -> Path:
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "a.py").write_text("a = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    build_fixture_tree(root)
    return root


def _answering(overrides=None):
    return lambda request: httpx.Response(200, json=choice_body(request, overrides))


async def _review(project: Path, monkeypatch, criteria="adds foo", overrides=None) -> JudgmentLedger:
    install_jev(monkeypatch, _answering(overrides))
    (project / "a.py").write_text("a = 'foo'\n")
    ledger = JudgmentLedger(4, 0.01)
    await dr.assess_candidate(cwd=project, criteria=criteria, ledger=ledger)
    write_judgments_sidecar(project, ROOT, ledger)
    return ledger


def _block(out: str) -> list[str]:
    lines = out.splitlines()
    start = next(n for n, line in enumerate(lines) if "Requirement assessments (advisory)" in line)
    return lines[start:start + 2]


async def test_review_receipt_shows_current_assessments(project, monkeypatch):
    await _review(project, monkeypatch)
    report = build_audit_report(project, run_id=ROOT)
    body = _judgments_body(report)
    assert body[0].startswith("- ") and "review.requirements answered" in body[0]
    assert body[1] == "  Requirement assessments (advisory)"
    assert body[2] == "    " + CURRENT
    assert CURRENT in render_text(report)
    markdown = render_markdown(report)
    assert "Requirement assessments (advisory)" in markdown and CURRENT in markdown
    assert json.loads(render_json(report))["judgments"]["receipts"][0]["detail"]["stale"] is False
    for line in _block(render_text(report)):
        assert not any(word in line.lower() for word in ("score", "correctness", "confidence"))


@pytest.mark.parametrize("change", ["edit", "delete"])
async def test_review_receipt_goes_stale_after_the_touched_file_changes(project, monkeypatch, change):
    await _review(project, monkeypatch)
    if change == "edit":
        (project / "a.py").write_text("a = 'bar'\n")
    else:
        (project / "a.py").unlink()
    report = build_audit_report(project, run_id=ROOT)
    assert STALE in render_text(report)
    assert STALE in render_markdown(report)
    assert json.loads(render_json(report))["judgments"]["receipts"][0]["detail"]["stale"] is True
    saved = json.loads((project / ".voss" / "sessions" / ROOT / "judgments.json").read_text())
    assert "stale" not in saved["receipts"][0]["detail"]


def test_old_receipts_render_as_before(project):
    write_judgments_sidecar(project, ROOT, build_ledger())
    body = _judgments_body(build_audit_report(project, run_id=ROOT))
    assert len(body) == 3
    assert body[0].startswith("- aaaaaaaaaaaa recall.rerank unavailable")
    assert body[1].startswith("- bbbbbbbbbbbb explicit answered")
    assert "Requirement assessments" not in render_text(build_audit_report(project, run_id=ROOT))


def _review_receipt(call_id: str, **overrides):
    fields = dict(purpose=dr.PURPOSE, rubric_version=dr.RUBRIC_VERSION, cost_usd=None, answers={})
    fields.update(overrides)
    return _receipt(call_id, **fields)


def test_failed_review_shows_the_reason_never_a_number(project):
    ledger = JudgmentLedger(4, 0.01)
    detail = {"packet_id": "p", "criterion_ids": ["AC-1"], "labels": {}, "candidate": {"kind": "commit", "head": "abc"}}
    ledger.receipts.append(_review_receipt(
        "c" * 20, status="unavailable", fallback_reason="oversize", attempts=0, detail=detail,
    ))
    write_judgments_sidecar(project, ROOT, ledger)
    body = _judgments_body(build_audit_report(project, run_id=ROOT))
    assert body[1:3] == ["  Requirement assessments (advisory)", "    not available: oversize"]
    assert "P(" not in "\n".join(body)


@pytest.mark.parametrize(
    "detail",
    [
        ["not", "a", "dict"],
        {"candidate": "x"},
        {"candidate": {"kind": "working_tree", "touched_paths": "a.py", "tree_digest": 1}},
        {"criterion_ids": ["AC-1"], "labels": "bad"},
        None,
    ],
)
def test_malformed_review_detail_renders_without_raising(project, detail):
    ledger = JudgmentLedger(4, 0.01)
    ledger.receipts.append(_review_receipt("d" * 20, detail=detail))
    write_judgments_sidecar(project, ROOT, ledger)
    report = build_audit_report(project, run_id=ROOT)
    render_json(report)
    assert "not available: malformed receipt" in render_markdown(report)
    assert "not available: malformed receipt" in render_text(report)


async def test_criterion_and_diff_text_never_reach_audit_output(project, monkeypatch):
    install_jev(monkeypatch, _answering())
    (project / "a.py").write_text(f"a = '{SENTINEL}'\n")
    ledger = JudgmentLedger(4, 0.01)
    await dr.assess_candidate(cwd=project, criteria=f"{SENTINEL} adds foo", ledger=ledger)
    write_judgments_sidecar(project, ROOT, ledger)
    report = build_audit_report(project, run_id=ROOT)
    assert report.judgments["receipts"][0]["detail"]["labels"] == {"AC-1": "supported"}
    for out in (render_text(report), render_markdown(report), render_json(report)):
        assert SENTINEL not in out


def _run_files(project: Path) -> dict[str, bytes]:
    run_dir = project / ".voss" / "sessions" / ROOT
    return {p.name: p.read_bytes() for p in sorted(run_dir.iterdir()) if p.name != "judgments.json"}


def test_demo_review_then_audit_then_stale(project, monkeypatch):
    from voss.harness import judgments
    from voss.harness.cli import audit_cmd

    seen = install_jev(monkeypatch, _answering({"AC-2": ABSTAIN}))
    monkeypatch.chdir(project)
    before = _run_files(project)
    (project / "a.py").write_text("a = 'foo'\n")
    result = CliRunner().invoke(
        judgments.judge_cmd, ["review", "--criterion", "adds foo", "--criterion", "adds bar", "--run", ROOT],
    )
    assert result.exit_code == 0, result.output
    assert len(seen) == 1
    assert _run_files(project) == before

    audit = CliRunner().invoke(audit_cmd, [ROOT, "--cwd", str(project)])
    assert audit.exit_code == 0, audit.output
    assert "AC-1  supported  P(supported)=0.90  current" in audit.output
    assert "AC-2  unclear (abstained)  P(insufficient_evidence)=0.90  current" in audit.output

    (project / "a.py").write_text("a = 'foo'\nb = 2\n")
    audit = CliRunner().invoke(audit_cmd, [ROOT, "--cwd", str(project)])
    assert "AC-1  supported  P(supported)=0.90  stale: work changed since this was checked" in audit.output
    assert "AC-2  unclear (abstained)  P(insufficient_evidence)=0.90  stale: work changed since this was checked" in audit.output
    assert _run_files(project) == before
    assert len(seen) == 1

