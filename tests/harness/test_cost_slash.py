"""CACHE-04: /cost cache accounting slash command stubs for T4-05."""

from types import SimpleNamespace

import pytest


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


def test_by_model_matches_per_run_sum_to_4_decimals(fake_ctx, capsys) -> None:
    from voss.harness.cli import _build_slash_registry

    fake_ctx.record.runs = [
        {"cost_usd": 0.0123, "changed": []},
        {"cost_usd": 0.0456, "changed": []},
    ]
    fake_ctx.record.model = "claude-sonnet-4-7"
    fake_ctx.total_cost = 0.0579

    registry = _build_slash_registry()
    registry.lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")
    out = capsys.readouterr().out

    assert "$0.0579" in out
    assert "claude-sonnet-4-7" in out


def test_by_tool_placeholder_cites_t6(fake_ctx, capsys) -> None:
    from voss.harness.cli import _build_slash_registry

    registry = _build_slash_registry()
    registry.lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")
    out = capsys.readouterr().out

    assert "T6 SLASH-07" in out
