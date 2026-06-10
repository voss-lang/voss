"""Token-savings ledger tests (VOPT-05).

Ledger lives at `.voss/sessions/<id>/token-savings.jsonl` (RESEARCH A7 —
subdirectory of the sessions dir, NOT the flat `<id>.json` convention).

Contract pinned here:
    _append_savings_record(cwd: Path, session_id: str, record: dict) -> None
    estimate_savings_usd(saved_tokens: int, cache_read_tokens: int, model: str) -> float | None
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


def _ledger_path(tmp_path, session_id="abc123"):
    return tmp_path / ".voss" / "sessions" / session_id / "token-savings.jsonl"


def _row(**overrides) -> dict:
    base = {
        "iter": 3,
        "original_tokens_est": 1200,
        "packed_tokens_est": 700,
        "method": "tiered-K8-M20",
        "cache_read_tokens": 0,
        "saved_tokens_est": 500,
        "saved_usd_est": None,
        "model": "stub-model",
        "ts": "2026-06-10T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_ledger_packed_le_original(tmp_path) -> None:
    """VOPT-05: every ledger row satisfies packed <= original, saved >= 0."""
    from voss.harness.recorder import _append_savings_record

    _append_savings_record(cwd=tmp_path, session_id="abc123", record=_row())

    lines = _ledger_path(tmp_path).read_text().splitlines()
    row = json.loads(lines[-1])
    assert row["packed_tokens_est"] <= row["original_tokens_est"]
    assert row["saved_tokens_est"] >= 0


def test_no_pack_zero_savings(tmp_path) -> None:
    """VOPT-05: under --no-pack, original == packed and saved == 0."""
    from voss.harness.recorder import _append_savings_record

    _append_savings_record(
        cwd=tmp_path,
        session_id="abc123",
        record=_row(
            method="no-pack",
            original_tokens_est=900,
            packed_tokens_est=900,
            saved_tokens_est=0,
        ),
    )

    row = json.loads(_ledger_path(tmp_path).read_text().splitlines()[-1])
    assert row["method"] == "no-pack"
    assert row["original_tokens_est"] == row["packed_tokens_est"]
    assert row["saved_tokens_est"] == 0


@pytest.fixture
def fake_ctx(tmp_path):
    record = SimpleNamespace(
        id="abc123",
        name="fake-session",
        cwd=str(tmp_path),
        model="claude-sonnet-4-7",
        total_cost_usd=0.0,
        turns=[],
        runs=[
            {"cost_usd": 0.008, "model": "claude-sonnet-4-7", "changed": []},
            {"cost_usd": 0.012, "model": "claude-sonnet-4-7", "changed": []},
        ],
    )
    return SimpleNamespace(
        cwd=tmp_path,
        record=record,
        history=None,
        last_plan=None,
        total_cost=0.020,
        budget_usd=None,
        prior_context=None,
    )


def test_cost_slash_prints_savings_line(fake_ctx, tmp_path, capsys) -> None:
    """VOPT-05: /cost prints a `context packed:` savings line from the ledger."""
    from voss.harness.cli import _build_slash_registry

    ledger = _ledger_path(tmp_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(_row(original_tokens_est=8000, packed_tokens_est=3000, saved_tokens_est=5000))
        + "\n"
        + json.dumps(
            _row(iter=4, original_tokens_est=6200, packed_tokens_est=3800, saved_tokens_est=2400)
        )
        + "\n"
    )

    registry = _build_slash_registry()
    registry.lookup("/cost").handler(fake_ctx, [], "/cost")
    out = capsys.readouterr().out

    assert "context packed:" in out


def test_saved_usd_nets_cache_reads() -> None:
    """VOPT-05 / D-04: dollar estimate nets cache-read billing; unknown model -> None."""
    from voss.harness.recorder import estimate_savings_usd

    gross = estimate_savings_usd(saved_tokens=1000, cache_read_tokens=0, model="claude-opus-4-8")
    netted = estimate_savings_usd(saved_tokens=1000, cache_read_tokens=400, model="claude-opus-4-8")

    assert gross is not None and netted is not None
    # Cache reads already billed at the reduced rate: netting strictly
    # shrinks the estimate below naive saved_tokens * input_rate (== gross).
    assert 0.0 <= netted < gross
    assert estimate_savings_usd(saved_tokens=10, cache_read_tokens=0, model="not-a-real-model-xyz") is None
