from __future__ import annotations

import pytest

from voss.harness.session import IterationRecord, RunRecord
from voss.harness.voss_inspect import (
    BudgetFrame,
    DecisionView,
    budget_timeline,
    decision_sequence,
    load_run,
    render_budget_timeline,
    render_decision_sequence,
)


def _decision(title: str, body: str, confidence: float) -> dict:
    return {"title": title, "body": body, "confidence": confidence}


def test_two_decisions_render_in_order_with_confidence_values() -> None:
    run = {
        "decisions": [
            _decision("choose parser", "decision-body-alpha", 0.82),
            _decision("emit tests", "decision-body-beta", 0.47),
        ]
    }

    views = decision_sequence(run)
    assert all(isinstance(view, DecisionView) for view in views)
    assert [view.index for view in views] == [0, 1]

    text = render_decision_sequence(run)
    assert text.index("choose parser") < text.index("emit tests")
    assert "0.82" in text
    assert "0.47" in text


def test_selected_decision_renders_only_that_decision_with_context_labels() -> None:
    run = {
        "decisions": [
            _decision("previous decision", "decision-body-alpha", 0.31),
            _decision("selected decision", "decision-body-beta", 0.66),
            _decision("next decision", "decision-body-gamma", 0.93),
        ]
    }

    text = render_decision_sequence(run, decision_index=1)
    lower = text.lower()

    assert "selected decision" in text
    assert "decision-body-beta" in text
    assert "0.66" in text
    assert "previous" in lower
    assert "next" in lower
    assert "decision-body-alpha" not in text
    assert "decision-body-gamma" not in text


def test_no_decisions_returns_clear_no_data_message() -> None:
    text = render_decision_sequence({"decisions": []})

    lower = text.lower()
    assert "no" in lower
    assert "decision" in lower


def test_budget_timeline_counts_frame_and_cumulative_tokens_for_json_dict_run() -> None:
    run = {
        "iterations": [
            {
                "index": 0,
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cache_creation_input_tokens": 3,
                "cache_read_input_tokens": 2,
                "cost_usd": 0.001,
                "exit_reason": None,
            },
            {
                "index": 1,
                "prompt_tokens": 7,
                "completion_tokens": 11,
                "cache_creation_input_tokens": 13,
                "cache_read_input_tokens": 17,
                "cost_usd": 0.002,
                "exit_reason": "budget",
            },
        ]
    }

    frames = budget_timeline(run)

    assert all(isinstance(frame, BudgetFrame) for frame in frames)
    assert [frame.index for frame in frames] == [0, 1]
    assert frames[0].prompt_tokens == 10
    assert frames[0].completion_tokens == 5
    assert frames[0].cache_creation_input_tokens == 3
    assert frames[0].cache_read_input_tokens == 2
    assert frames[0].total_tokens == 20
    assert frames[0].cumulative_tokens == 20
    assert frames[1].total_tokens == 48
    assert frames[1].cumulative_tokens == 68
    assert frames[1].exit_reason == "budget"

    rendered = render_budget_timeline(run)
    for expected in ("20", "48", "68", "3", "17"):
        assert expected in rendered
    assert "budget" in rendered.lower()


def test_dataclass_shaped_run_supports_decisions_and_budget_iterations() -> None:
    run = RunRecord(
        id="run-1",
        started_at="2026-05-18T00:00:00+00:00",
        ended_at="2026-05-18T00:00:01+00:00",
        decisions=[_decision("dataclass decision", "decision-body-delta", 0.91)],
        iterations=[
            IterationRecord(
                index=0,
                prompt_tokens=4,
                completion_tokens=6,
                cache_creation_input_tokens=8,
                cache_read_input_tokens=10,
                cost_usd=0.004,
                exit_reason="done",
            )
        ],
    )

    decision_views = decision_sequence(run)
    budget_frames = budget_timeline(run)

    assert decision_views[0].title == "dataclass decision"
    assert decision_views[0].body == "decision-body-delta"
    assert decision_views[0].confidence == pytest.approx(0.91)
    assert budget_frames[0].total_tokens == 28
    assert budget_frames[0].cumulative_tokens == 28
    assert render_decision_sequence(run).count("dataclass decision") == 1


def test_expected_public_api_exports_load_run() -> None:
    assert callable(load_run)
