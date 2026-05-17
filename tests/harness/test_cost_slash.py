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


def test_by_model_matches_per_run_sum_to_4_decimals(fake_ctx) -> None:
    pytest.fail("T4-05 lands /cost --by-model verification and D-09 update")


def test_by_tool_placeholder_cites_t6(fake_ctx) -> None:
    pytest.fail("T4-05 lands /cost --by-model verification and D-09 update")
