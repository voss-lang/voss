"""CACHE-07: telemetry and RunRecord cache field stubs for T4-04."""
from __future__ import annotations

import dataclasses
import importlib.util
import json
from pathlib import Path


from voss.harness.session import IterationRecord


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _telemetry_module():
    path = _REPO_ROOT / "voss/harness/telemetry.py"
    spec = importlib.util.spec_from_file_location(
        "voss.harness.telemetry_cache_test_import",
        path,
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_provider_response_event_carries_cache_tokens(monkeypatch, tmp_path: Path) -> None:
    telemetry = _telemetry_module()
    logf = tmp_path / "h.ndjson"
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(logf))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()
    telemetry.emit(
        "provider.response",
        "info",
        data={
            "model": "claude-sonnet-4-5",
            "cost_usd": 0.012,
            "cache_creation_input_tokens": 1500,
            "cache_read_input_tokens": 0,
        },
    )
    telemetry.finalize_turn(True, None)
    telemetry.reset_session_sink()

    events = [
        json.loads(line)
        for line in logf.read_text().splitlines()
        if line.strip()
    ]
    provider_response = next(
        event for event in events if event.get("kind") == "provider.response"
    )
    data = provider_response["data"]
    assert data["cache_creation_input_tokens"] == 1500
    assert data["cache_read_input_tokens"] == 0
    assert "cache" not in data


def test_iteration_record_cache_fields_default_zero_for_old_fixtures() -> None:
    old_iter = {
        "index": 0,
        "plan": {"rationale": "r", "steps": []},
        "tool_results": [{"tool": "fs_read", "path": "a.py"}],
        "cost_usd": 0.012,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:00:01+00:00",
        "exit_reason": None,
    }
    rec = IterationRecord(**old_iter)
    assert rec.cache_creation_input_tokens == 0
    assert rec.cache_read_input_tokens == 0


def test_iteration_record_cache_fields_round_trip() -> None:
    rec = IterationRecord(
        index=0,
        cache_creation_input_tokens=1500,
        cache_read_input_tokens=200,
    )
    hydrated = IterationRecord(**dataclasses.asdict(rec))
    assert hydrated.cache_creation_input_tokens == 1500
    assert hydrated.cache_read_input_tokens == 200
