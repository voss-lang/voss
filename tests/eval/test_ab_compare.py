from __future__ import annotations

import pytest

from voss.eval.ab import compare, render, task_score

TASKS = [f"t{i:02d}" for i in range(30)]


def row(task_id: str, passed: bool, *, run_idx: int = 0, **extra) -> dict:
    return {"task_id": task_id, "run_idx": run_idx, "gate_pass": passed, "capped": False, **extra}


def runs(task_id: str, outcomes: list[bool]) -> list[dict]:
    return [row(task_id, passed, run_idx=i) for i, passed in enumerate(outcomes)]


def test_task_score_requires_gate_pass_and_not_capped() -> None:
    assert task_score(row("t", True)) == 1
    assert task_score(row("t", False)) == 0
    assert task_score(row("t", None)) == 0
    assert task_score({"task_id": "t", "gate_pass": True, "capped": True}) == 0
    assert task_score({"task_id": "t", "gate_pass": True}) == 1


def test_identical_outcomes_report_no_observed_difference() -> None:
    rows = [row(t, i % 3 == 0) for i, t in enumerate(TASKS)]

    result = compare(rows, list(rows))

    assert result["n_tasks"] == 30
    assert result["mean_diff"] == 0.0
    assert (result["ci_low"], result["ci_high"]) == (0.0, 0.0)
    assert result["no_difference"] is True
    assert result["regressions"] == []
    assert result["passed"] is True


def test_b_only_passes_need_no_confirmation() -> None:
    a_rows = [row(t, i >= 3) for i, t in enumerate(TASKS)]
    b_rows = [row(t, True) for t in TASKS]

    result = compare(a_rows, b_rows)

    assert result["b_only"] == TASKS[:3]
    assert result["a_only"] == []
    assert result["mean_diff"] == pytest.approx(0.1)
    assert result["ci_low"] <= 0.1 <= result["ci_high"]
    assert result["unconfirmed"] == []
    assert result["no_difference"] is False
    assert result["passed"] is True


def test_regression_requires_every_run_to_disagree() -> None:
    a_rows = runs("t1", [True, True]) + runs("t2", [True]) + runs("t3", [True, True])
    b_rows = runs("t1", [False, False]) + runs("t2", [False]) + runs("t3", [False, True])

    result = compare(a_rows, b_rows)

    assert result["regressions"] == ["t1"]
    assert result["unconfirmed"] == ["t2"]
    assert result["a_only"] == ["t1", "t2", "t3"]
    assert result["disagreements"] == ["t1", "t2", "t3"]
    assert result["passed"] is False


def test_single_run_disagreement_is_unconfirmed_and_fails() -> None:
    result = compare(runs("t2", [True]), runs("t2", [False, False]))

    assert result["unconfirmed"] == ["t2"]
    assert result["regressions"] == []
    assert result["passed"] is False


def test_paired_difference_uses_first_run_as_written() -> None:
    a_rows = [row("t1", False, run_idx=1), row("t1", True, run_idx=0)]
    b_rows = [row("t1", False, run_idx=0)]

    result = compare(a_rows, b_rows)

    assert result["mean_diff"] == 0.0
    assert result["a_pass_rate"] == 0.0


def test_task_on_one_side_only_raises() -> None:
    with pytest.raises(ValueError, match="t9"):
        compare([row("t1", True), row("t9", True)], [row("t1", True)])


def test_skipped_tasks_are_excluded() -> None:
    a_rows = [row("t1", True), row("t2", None, skipped=True)]
    b_rows = [row("t1", True), row("t2", None, skipped=True)]

    result = compare(a_rows, b_rows)

    assert result["n_tasks"] == 1
    assert result["n_skipped"] == 1


def test_zero_comparable_tasks_raises() -> None:
    skipped = [row("t1", None, skipped=True)]
    with pytest.raises(ValueError):
        compare(skipped, list(skipped))


def test_render_states_labels_numbers_and_caveat() -> None:
    rows = [row(t, True) for t in TASKS]
    text = render(compare(rows, list(rows)), a_label="off", b_label="active")

    assert "off" in text and "active" in text
    assert "1.000" in text
    assert "[+0.000, +0.000]" in text
    assert "no observed difference" in text
    assert "Reproducible regressions: none" in text
    assert "A 30-task pilot cannot establish general non-regression." in text


def test_render_lists_regressions() -> None:
    text = render(
        compare(runs("t1", [True, True]), runs("t1", [False, False])),
        a_label="off",
        b_label="active",
    )

    assert "Reproducible regressions: t1" in text
    assert "no observed difference" not in text
    assert "FAIL" in text
