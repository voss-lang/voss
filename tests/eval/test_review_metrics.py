from __future__ import annotations

import math

import pytest

from voss.eval.review import RELEASE_BAR, receipt_summary, score, wilson

Z = 1.96


def row(gold: str, label: str | None, *, kind: str = "contradicted", flag: str = "none",
        probabilities: dict | None = None, fixture: str = "rv-001", criterion: str = "AC-1") -> dict:
    return {
        "fixture": fixture, "criterion": criterion, "kind": kind, "gold": gold,
        "flag": flag, "label": label, "probabilities": probabilities,
    }


def quadratic_roots(k: int, n: int) -> tuple[float, float]:
    p = k / n
    a = 1 + Z * Z / n
    b = -(2 * p + Z * Z / n)
    c = p * p
    root = math.sqrt(b * b - 4 * a * c)
    return ((-b - root) / (2 * a), (-b + root) / (2 * a))


def test_wilson_upper_bound_at_zero_errors_stays_above_the_bar():
    assert wilson(0, 25)[0] == 0.0
    assert round(wilson(0, 25)[1], 3) == 0.133
    assert round(wilson(0, 30)[1], 3) == 0.114
    assert wilson(0, 30)[1] > RELEASE_BAR


def test_wilson_matches_the_closed_form():
    assert wilson(5, 50) == pytest.approx(quadratic_roots(5, 50))
    assert wilson(5, 50) == pytest.approx((0.0435, 0.2136), abs=1e-4)


def test_wilson_with_no_trials_is_uninformative():
    assert wilson(0, 0) == (0.0, 1.0)


def test_ambiguous_pairs_are_excluded_from_every_rate():
    rows = [
        row("contradicted", "contradicted"),
        row("contradicted", "supported", flag="ambiguous", fixture="rv-009", criterion="AC-2"),
        row("insufficient_evidence", None, flag="ambiguous", fixture="rv-010", criterion="AC-1"),
    ]

    result = score(rows)

    assert result["false_supported"]["k"] == 0 and result["false_supported"]["n"] == 1
    assert result["contradicted_recall"]["n"] == 1
    assert result["abstention"] == {"k": 0, "n": 1, "rate": 0.0}
    assert result["failed"] == 0
    assert result["ambiguous"] == {"count": 2, "pairs": ["rv-009/AC-2", "rv-010/AC-1"]}
    assert sum(sum(cell.values()) for gold in result["by_kind"].values() for cell in gold.values()) == 1


def test_false_supported_counts_supported_labels_on_non_supported_gold():
    rows = [
        row("contradicted", "supported"),
        row("insufficient_evidence", "supported", kind="missing_criterion"),
        row("contradicted", "contradicted"),
        row("supported", "supported", kind="supported"),
    ]

    result = score(rows)

    assert result["false_supported"] == {"k": 2, "n": 3, "rate": 2 / 3, "ci": pytest.approx(list(wilson(2, 3)))}
    assert result["contradicted_recall"] == {"k": 1, "n": 2, "rate": 0.5, "ci": pytest.approx(list(wilson(1, 2)))}


def test_abstention_counts_abstained_no_answer_and_failed_calls():
    rows = [
        row("contradicted", "abstained"),
        row("contradicted", "no_answer"),
        row("insufficient_evidence", None),
        row("supported", "supported", kind="supported"),
    ]

    result = score(rows)

    assert result["abstention"] == {"k": 3, "n": 4, "rate": 0.75}
    assert result["coverage"] == pytest.approx(0.25)
    assert result["failed"] == 1


def test_brier_uses_p_supported_over_rows_with_probabilities():
    rows = [
        row("supported", "supported", kind="supported", probabilities={"supported": 0.9, "contradicted": 0.05, "insufficient_evidence": 0.05}),
        row("contradicted", "abstained", probabilities={"supported": 0.2, "contradicted": 0.7, "insufficient_evidence": 0.1}),
        row("contradicted", None),
    ]

    assert score(rows)["brier"] == pytest.approx((0.01 + 0.04) / 2)
    assert score([row("contradicted", None)])["brier"] is None


def test_by_kind_is_a_gold_by_shown_confusion_count():
    rows = [
        row("contradicted", "contradicted"),
        row("contradicted", "contradicted"),
        row("supported", "abstained"),
        row("insufficient_evidence", None, kind="no_checks"),
        row("insufficient_evidence", "supported", kind="no_checks"),
    ]

    assert score(rows)["by_kind"] == {
        "contradicted": {"contradicted": {"contradicted": 2}, "supported": {"abstained": 1}},
        "no_checks": {"insufficient_evidence": {"failed": 1, "supported": 1}},
    }


def negatives(false_supported: int, total: int) -> list[dict]:
    return [row("contradicted", "supported" if i < false_supported else "contradicted") for i in range(total)]


def test_release_bar_is_the_point_estimate():
    at_bar = score(negatives(1, 20))
    above_bar = score(negatives(2, 30))

    assert at_bar["false_supported"]["rate"] == 0.05 and at_bar["passed"] is True
    assert at_bar["false_supported"]["ci"][1] > RELEASE_BAR
    assert above_bar["passed"] is False


def test_release_bar_fails_without_non_supported_gold():
    result = score([row("supported", "supported", kind="supported")])

    assert result["false_supported"] == {"k": 0, "n": 0, "rate": None, "ci": [0.0, 1.0]}
    assert result["passed"] is False


def receipt(status: str, *, cost: float | None, latency: float, request_bytes: int, model: str | None) -> dict:
    return {
        "status": status, "cost_usd": cost, "latency_ms": latency,
        "model_returned": model, "detail": {"request_bytes": request_bytes},
    }


def test_receipt_summary_reports_calls_cost_latency_size_and_models():
    receipts = [
        receipt("answered", cost=0.002, latency=100.0, request_bytes=1000, model="jev-1.13.0"),
        receipt("answered", cost=0.004, latency=300.0, request_bytes=3000, model="jev-1.13.0"),
        receipt("answered", cost=0.003, latency=200.0, request_bytes=2000, model="jev-1.14.0"),
        receipt("timeout", cost=None, latency=5000.0, request_bytes=9000, model=None),
    ]

    summary = receipt_summary(receipts)

    assert summary["calls"] == 4
    assert summary["answered"] == 3
    assert summary["cost_usd_total"] == pytest.approx(0.009)
    assert summary["cost_usd_mean"] == pytest.approx(0.003)
    assert summary["latency_p50_ms"] == pytest.approx(200.0)
    assert summary["latency_p95_ms"] == pytest.approx(380.0)
    assert summary["request_bytes_median"] == 2000
    assert summary["request_bytes_max"] == 3000
    assert summary["models"] == ["jev-1.13.0", "jev-1.14.0"]


def test_receipt_summary_of_nothing():
    assert receipt_summary([]) == {
        "calls": 0, "answered": 0, "cost_usd_total": 0.0, "cost_usd_mean": None,
        "latency_p50_ms": None, "latency_p95_ms": None,
        "request_bytes_median": None, "request_bytes_max": None, "models": [],
    }
