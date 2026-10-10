from __future__ import annotations

import math
import random

import pytest

from voss.eval.retrieval import (
    NDCG_GAIN_MIN,
    Dataset,
    gate,
    ndcg_at_k,
    paired_bootstrap,
    recall_at_k_files,
)

FILLER = ["x1", "x2", "x3", "x4"]


def make_dataset(labels: dict, group_of: dict, *, adversarial=(), ambiguous=()) -> Dataset:
    paths = {chunk: f"{chunk}.py" for grades in labels.values() for chunk in grades}
    paths.update({chunk: f"{chunk}.py" for chunk in FILLER})
    return Dataset(
        split="dev",
        corpus={},
        queries={qid: {} for qid in labels},
        group_of=group_of,
        labels=labels,
        pools={},
        chunk_paths=paths,
        ambiguous=tuple(ambiguous),
        adversarial=tuple(adversarial),
        scored_queries=tuple(sorted(qid for qid in labels if qid not in ambiguous)),
    )


def test_ndcg_matches_hand_computed_value() -> None:
    expected = (7 + 3 / math.log2(4)) / (7 + 3 / math.log2(3))

    assert ndcg_at_k(["a", "b", "c"], {"a": 3, "b": 0, "c": 2}) == pytest.approx(expected)
    assert ndcg_at_k(["a", "c", "b"], {"a": 3, "b": 0, "c": 2}) == 1.0
    assert ndcg_at_k(["a", "b"], {"a": 0, "b": 0}) is None


def test_ndcg_ideal_includes_gold_chunks_missing_from_ranking() -> None:
    assert ndcg_at_k(["a", "b"], {"a": 3, "gold": 3}) < 1.0


def test_recall_counts_relevant_files_once() -> None:
    paths = {"a1": "a.py", "a2": "a.py", "b1": "b.py", "c1": "c.py"}

    assert recall_at_k_files(["a1", "a2", "c1"], {"a1": 3, "a2": 2, "b1": 2, "c1": 1}, paths) == 0.5
    assert recall_at_k_files(["a1"], {"a1": 1}, paths) is None
    assert recall_at_k_files(["c1", "b1"], {"a1": 3, "a2": 3}, paths) == 0.0


def test_paired_bootstrap_is_seeded_and_uses_percentile_indices() -> None:
    assert paired_bootstrap([0.1] * 20) == (0.1, 0.1)

    diffs = [-1.0, 1.0] * 10
    low, high = paired_bootstrap(diffs)
    assert low < 0 < high
    assert paired_bootstrap(diffs) == (low, high)

    rng = random.Random(7)
    means = sorted(sum(rng.choices(diffs, k=20)) / 20 for _ in range(40))
    assert paired_bootstrap(diffs, b=40, seed=7) == pytest.approx((means[1], means[38]))


def moved_up(n: int) -> tuple[dict, dict, dict, dict]:
    labels = {f"q{i}": {f"n{i}": 3} for i in range(n)}
    group_of = {"q0": "g0", "q1": "g0", **{f"q{i}": f"g{i}" for i in range(2, n)}}
    baseline = {qid: FILLER + [f"n{qid[1:]}"] for qid in labels}
    candidate = {qid: [f"n{qid[1:]}"] + FILLER for qid in labels}
    return labels, group_of, baseline, candidate


def test_gate_passes_when_necessary_chunk_moves_to_rank_one() -> None:
    labels, group_of, baseline, candidate = moved_up(5)

    result = gate(make_dataset(labels, group_of), baseline, candidate)

    assert result["mean_gain"] >= NDCG_GAIN_MIN
    assert result["ci_low"] > 0
    assert result["recall_diff"] >= 0
    assert result["passed"] is True
    assert (result["wins"], result["losses"], result["ties"]) == (5, 0, 0)
    assert (result["n_groups"], result["n_queries"]) == (4, 5)


def test_gate_fails_on_identical_rankings() -> None:
    labels, group_of, baseline, _ = moved_up(5)

    result = gate(make_dataset(labels, group_of), baseline, baseline)

    assert result["mean_gain"] == 0
    assert result["passed"] is False
    assert result["ties"] == 5


def test_gate_fails_when_relevant_file_drops_out_of_top_five() -> None:
    labels = {f"q{i}": {f"a{i}": 3, f"b{i}": 2} for i in range(4)}
    group_of = {qid: f"g{qid}" for qid in labels}
    baseline = {qid: [f"a{qid[1:]}", f"b{qid[1:]}"] + FILLER for qid in labels}
    candidate = {qid: [f"a{qid[1:]}"] + FILLER + [f"b{qid[1:]}"] for qid in labels}

    result = gate(make_dataset(labels, group_of), baseline, candidate)

    assert result["recall_diff"] < 0
    assert result["passed"] is False


def test_gate_averages_variant_queries_within_a_group() -> None:
    labels, group_of, baseline, candidate = moved_up(3)
    candidate["q1"] = baseline["q1"]
    gain = 1 - (7 / math.log2(6)) / 7

    result = gate(make_dataset(labels, group_of), baseline, candidate)

    assert (result["n_groups"], result["n_queries"]) == (2, 3)
    assert result["mean_gain"] == pytest.approx((gain / 2 + gain) / 2)


def test_gate_excludes_ambiguous_and_unscorable_queries_and_reports_adversarial() -> None:
    labels, group_of, baseline, candidate = moved_up(5)
    labels["q5"] = {"x1": 0}
    group_of["q5"] = "g5"
    baseline["q5"] = candidate["q5"] = FILLER
    dataset = make_dataset(labels, group_of, adversarial=["q3", "q4"], ambiguous=["q4"])

    result = gate(dataset, baseline, candidate)

    assert (result["n_queries"], result["n_excluded"], result["n_ambiguous"]) == (4, 1, 1)
    assert result["adversarial"]["n_queries"] == 1
    assert result["thresholds"] == {
        "ndcg_gain_min": 0.03, "recall_drop_max": 0.0, "alpha": 0.05, "b": 10_000, "seed": 20261003,
    }
