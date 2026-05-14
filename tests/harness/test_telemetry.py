"""Harness NDJSON telemetry (VOSS_LOG)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _telemetry_module():
    path = _REPO_ROOT / "voss/harness/telemetry.py"
    spec = importlib.util.spec_from_file_location(
        "voss.harness.telemetry_test_import",
        path,
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_redact_tool_args_masks_content() -> None:
    telemetry = _telemetry_module()
    d = {"path": "x.py", "content": "secret body"}
    r = telemetry.redact_tool_args(d)
    assert r["path"] == "x.py"
    assert r["content"] == "<redacted>"


def test_redact_truncates_long_strings(monkeypatch) -> None:
    telemetry = _telemetry_module()
    monkeypatch.delenv("VOSS_LOG_VERBOSE", raising=False)
    d = {"note": "x" * 300}
    r = telemetry.redact_tool_args(d)
    assert len(str(r["note"])) < len(d["note"])


def test_emit_when_disabled_noop(monkeypatch) -> None:
    telemetry = _telemetry_module()
    monkeypatch.delenv("VOSS_LOG", raising=False)
    telemetry.reset_session_sink()
    telemetry.emit("x", "info", data={"k": 1})


def test_emit_writes_ndjson_file(monkeypatch, tmp_path: Path) -> None:
    telemetry = _telemetry_module()
    logf = tmp_path / "h.ndjson"
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(logf))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()
    telemetry.emit("probe", "info", data={"k": 1})
    telemetry.finalize_turn(True, None)
    telemetry.reset_session_sink()

    lines = [ln for ln in logf.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 2
    probe = None
    for ln in lines:
        o = json.loads(ln)
        if o.get("kind") == "probe":
            probe = o
            break
    assert probe is not None
    assert probe["v"] == 1
    assert "seq" in probe
    assert probe["data"]["k"] == 1


def test_finalize_turn_emits_end(monkeypatch, tmp_path: Path) -> None:
    telemetry = _telemetry_module()
    logf = tmp_path / "h.ndjson"
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(logf))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()
    telemetry.note_turn(cost_usd=0.01)
    telemetry.finalize_turn(True, None)
    telemetry.reset_session_sink()

    kinds = [json.loads(ln)["kind"] for ln in logf.read_text().splitlines() if ln.strip()]
    assert "turn.end" in kinds
