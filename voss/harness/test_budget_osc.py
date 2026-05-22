"""Tests for _emit_budget_osc (F3-01 D-02/D-04)."""
from __future__ import annotations

import io
import json
import sys

import pytest

from voss.harness.recorder import _emit_budget_osc

PREFIX = "\x1b]1337;voss-budget="
BEL = "\x07"


def test_emit_budget_osc_writes_to_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    _emit_budget_osc(
        tokens_used=500,
        token_limit=10_000,
        cost_usd=0.01,
        iteration=1,
        model="claude-3",
    )
    output = buf.getvalue()
    assert output.startswith(PREFIX)
    assert output.endswith(BEL)


def test_emit_budget_osc_payload_is_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    _emit_budget_osc(
        tokens_used=1200,
        token_limit=60_000,
        cost_usd=0.0053,
        iteration=3,
        model="sonnet",
    )
    raw = buf.getvalue()
    payload = raw[len(PREFIX) : -len(BEL)]
    data = json.loads(payload)
    assert data["tokens_used"] == 1200
    assert data["token_limit"] == 60_000
    assert data["cost_usd"] == pytest.approx(0.0053)
    assert data["iteration"] == 3
    assert data["model"] == "sonnet"


def test_emit_budget_osc_unlimited_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    _emit_budget_osc(
        tokens_used=100,
        token_limit=None,
        cost_usd=0.0,
        iteration=1,
        model="m",
    )
    raw = buf.getvalue()
    payload = raw[len(PREFIX) : -len(BEL)]
    data = json.loads(payload)
    assert data["token_limit"] is None


def test_emit_budget_osc_not_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout_buf)
    monkeypatch.setattr(sys, "stderr", stderr_buf)
    _emit_budget_osc(
        tokens_used=10,
        token_limit=1000,
        cost_usd=0.001,
        iteration=1,
        model="x",
    )
    assert stdout_buf.getvalue() != ""
    assert stderr_buf.getvalue() == ""
