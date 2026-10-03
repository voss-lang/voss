"""
Judgments sidecar (judgments.json): writer, tolerant loader, and the §16
audit section (J2 D-13b, D-14).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

import httpx
from click.testing import CliRunner

from tests.harness.audit.test_o6_fixtures import build_fixture_tree
from voss.harness.audit.render import render_json, render_markdown, render_text
from voss.harness.audit.report import build_audit_report
from voss.harness.session_tree import write_judgments_sidecar
from voss_runtime import judgments as j

ROOT = "root_aabbcc0001"
SENTINEL = "SENTINEL-c41d"


def _receipt(call_id: str, **overrides) -> j.JudgmentReceipt:
    fields = dict(
        call_id=call_id,
        purpose="explicit",
        rubric_version=None,
        model_requested="jev-1.13.0",
        model_returned="jev-1.13.1",
        mode="explicit",
        status="answered",
        fallback_reason=None,
        attempts=1,
        input_tokens=10,
        output_tokens=2,
        cost_usd=0.0012,
        held_usd=0.0,
        latency_ms=812.4,
        answers={"pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 1.0}}},
        artifact_revision=None,
    )
    fields.update(overrides)
    return j.JudgmentReceipt(**fields)


def build_ledger() -> j.JudgmentLedger:
    ledger = j.JudgmentLedger(max_calls=4, max_cost_usd=0.01)
    ledger.entries += [
        j.LedgerEntry("bbbbbbbbbbbbbbbbbbbb", 0.004, "settled", cost_usd=0.0012),
        j.LedgerEntry("aaaaaaaaaaaaaaaaaaaa", 0.004, "unknown"),
    ]
    ledger.receipts += [
        _receipt("bbbbbbbbbbbbbbbbbbbb"),
        _receipt(
            "aaaaaaaaaaaaaaaaaaaa",
            purpose="recall.rerank",
            model_returned=None,
            status="unavailable",
            fallback_reason="timeout",
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
            held_usd=0.004,
            latency_ms=5000.0,
            answers={},
        ),
    ]
    return ledger


def test_empty_ledger_writes_nothing(tmp_path: Path):
    ledger = j.JudgmentLedger(max_calls=4, max_cost_usd=0.01)
    assert write_judgments_sidecar(tmp_path, ROOT, ledger) is None
    assert not (tmp_path / ".voss" / "sessions" / ROOT / "judgments.json").exists()


def test_sidecar_written_private_with_receipts(tmp_path: Path):
    ledger = build_ledger()
    path = write_judgments_sidecar(tmp_path, ROOT, ledger)
    assert path == tmp_path / ".voss" / "sessions" / ROOT / "judgments.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text()) == {
        "schema_version": 1,
        "judgments_cost_usd": 0.0012,
        "held_usd": 0.004,
        "receipts": [asdict(r) for r in ledger.receipts],
    }


def test_audit_report_loads_sidecar_without_breaking_node_glob(tmp_path: Path):
    build_fixture_tree(tmp_path)
    assert build_audit_report(tmp_path).judgments is None
    path = write_judgments_sidecar(tmp_path, ROOT, build_ledger())
    report = build_audit_report(tmp_path, run_id=ROOT)
    assert report.judgments == json.loads(path.read_text())
    assert len(report.snapshot.nodes) == 8


def test_malformed_sidecar_loads_as_none(tmp_path: Path):
    build_fixture_tree(tmp_path)
    path = tmp_path / ".voss" / "sessions" / ROOT / "judgments.json"
    for content in ("{not json", "[1, 2]"):
        path.write_text(content)
        report = build_audit_report(tmp_path, run_id=ROOT)
        assert report.judgments is None
        assert "Judgments" not in render_markdown(report)


def test_render_json_carries_judgments(tmp_path: Path):
    build_fixture_tree(tmp_path)
    assert json.loads(render_json(build_audit_report(tmp_path)))["judgments"] is None
    path = write_judgments_sidecar(tmp_path, ROOT, build_ledger())
    out = render_json(build_audit_report(tmp_path))
    assert json.loads(out)["judgments"] == json.loads(path.read_text())
    assert out == render_json(build_audit_report(tmp_path))


async def test_request_content_never_reaches_audit_output(tmp_path: Path):
    build_fixture_tree(tmp_path)
    body = {
        "model": "jev-1.13.1",
        "answers": {"pick": {"type": "choice", "choice": "billing", "probabilities": {"billing": 0.9, "technical": 0.1}, "confidence": 0.8}},
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }
    responses = iter([httpx.Response(200, json=body), httpx.Response(500)])
    questions = {"pick": j.ChoiceQuestion(f"{SENTINEL} pick", {"billing": f"{SENTINEL} desc", "technical": None})}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: next(responses))) as http:
        client = j.JevClient(
            "test-key", client=http, model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000,
            max_calls=2, max_cost_usd=0.01, sleep=lambda s: asyncio.sleep(0),
        )
        await client.evaluate({"secret": SENTINEL}, questions)
        try:
            await client.evaluate({"secret": SENTINEL}, questions)
        except j.JudgmentError:
            pass
    write_judgments_sidecar(tmp_path, ROOT, client.ledger)
    report = build_audit_report(tmp_path)
    assert len(report.judgments["receipts"]) == 2
    for out in (render_markdown(report), render_text(report), render_json(report)):
        assert "judgments" in out.lower()
        assert SENTINEL not in out and "test-key" not in out


def test_audit_cli_prints_judgments_section(tmp_path: Path):
    from voss.harness.cli import audit_cmd

    build_fixture_tree(tmp_path)
    write_judgments_sidecar(tmp_path, ROOT, build_ledger())
    result = CliRunner().invoke(audit_cmd, [ROOT, "--cwd", str(tmp_path)])
    assert result.exit_code == 0
    assert "[16] Judgments" in result.output
    assert "- total observed $0.001200, held $0.004000, calls 2" in result.output
