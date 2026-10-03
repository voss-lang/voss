"""Retrieval baseline evaluation: dataset loader, ranking metrics, J3 gate, report (J2 S2.4/S2.5)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from voss.template_render import render_package_template

GRADES = {"irrelevant": 0, "contextual": 1, "directly_useful": 2, "necessary": 3}
RELEVANT_GRADE = 2
K = 5
POOL_SIZE = 15
NDCG_GAIN_MIN = 0.03
RECALL_DROP_MAX = 0.0
BOOTSTRAP_B = 10_000
BOOTSTRAP_SEED = 20261003
ALPHA = 0.05
DATASET_ROOT = Path("evals/retrieval")

SPLITS = ("dev", "test")
SOURCES = ("pool", "gold")
CONFIDENCES = ("", "high", "low")
FLAGS = ("none", "review", "reviewed", "ambiguous")


class DatasetError(ValueError):
    pass


class LockedSplitError(DatasetError):
    pass


@dataclass(frozen=True)
class Dataset:
    split: str
    corpus: dict
    queries: dict[str, dict]
    group_of: dict[str, str]
    labels: dict[str, dict[str, int]]
    pools: dict[str, list[str]]
    chunk_paths: dict[str, str]
    ambiguous: tuple[str, ...]
    adversarial: tuple[str, ...]
    scored_queries: tuple[str, ...]


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _load_queries(root: Path, split: str) -> dict[str, dict]:
    seen: set[str] = set()
    group_split: dict[str, str] = {}
    selected: dict[str, dict] = {}
    for path in sorted((root / "queries").glob("*.jsonl")):
        for row in _read_jsonl(path):
            qid = row["id"]
            if qid in seen:
                raise DatasetError(f"{path}: duplicate query id {qid}")
            seen.add(qid)
            if row["split"] == "":
                raise DatasetError(f"{path}: {qid}: dataset not frozen")
            if row["split"] not in SPLITS:
                raise DatasetError(f"{path}: {qid}: unknown split {row['split']!r}")
            if group_split.setdefault(row["group"], row["split"]) != row["split"]:
                raise DatasetError(f"{path}: {qid}: group {row['group']} spans splits")
            if row["split"] == split:
                selected[qid] = row
    return selected


def _load_pools(root: Path, queries: dict[str, dict]) -> tuple[dict[str, list[str]], dict[str, str]]:
    pools: dict[str, list[str]] = {}
    chunk_paths: dict[str, str] = {}
    for path in sorted((root / "baseline").glob("*.jsonl")):
        for row in _read_jsonl(path):
            if row["query_id"] not in queries:
                continue
            entries = sorted(row["pool"], key=lambda entry: entry["rank"])
            pools[row["query_id"]] = [entry["chunk_id"] for entry in entries]
            for entry in entries:
                chunk_paths[entry["chunk_id"]] = entry["path"]
    return pools, chunk_paths


def _check_vocab(path: Path, row: dict, field: str, allowed) -> None:
    if row[field] not in allowed:
        raise DatasetError(
            f"{path}: {row['query_id']}/{row['chunk_id']}: unknown {field} {row[field]!r}"
        )


def load_dataset(root: Path = DATASET_ROOT, *, split: str = "dev", locked_final: bool = False) -> Dataset:
    if split == "test" and not locked_final:
        raise LockedSplitError("test split is locked; pass locked_final=True only for the J3 comparison run")
    if split not in SPLITS:
        raise DatasetError(f"unknown split {split!r}")
    root = Path(root)
    corpus = json.loads((root / "corpus.json").read_text())
    queries = _load_queries(root, split)
    pools, chunk_paths = _load_pools(root, queries)
    labels: dict[str, dict[str, int]] = {qid: {} for qid in queries}
    ambiguous: set[str] = set()
    for path in sorted((root / "labels").glob("*.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                qid = row["query_id"]
                if qid not in queries:
                    continue
                _check_vocab(path, row, "source", SOURCES)
                _check_vocab(path, row, "grade", ("", *GRADES))
                _check_vocab(path, row, "confidence", CONFIDENCES)
                _check_vocab(path, row, "flag", FLAGS)
                if row["source"] == "pool" and row["chunk_id"] not in pools.get(qid, ()):
                    raise DatasetError(f"{path}: {qid}/{row['chunk_id']}: chunk not in pool or gold")
                chunk_paths.setdefault(row["chunk_id"], row["path"])
                if row["flag"] == "ambiguous":
                    ambiguous.add(qid)
                if row["grade"]:
                    labels[qid][row["chunk_id"]] = GRADES[row["grade"]]
    return Dataset(
        split=split,
        corpus=corpus,
        queries=queries,
        group_of={qid: row["group"] for qid, row in queries.items()},
        labels=labels,
        pools=pools,
        chunk_paths=chunk_paths,
        ambiguous=tuple(sorted(ambiguous)),
        adversarial=tuple(sorted(qid for qid, row in queries.items() if row["kind"] == "adversarial")),
        scored_queries=tuple(sorted(qid for qid in queries if qid not in ambiguous)),
    )


def _dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(grades, start=1))


def ndcg_at_k(ranking: list[str], grades: dict[str, int], k: int = K) -> float | None:
    idcg = _dcg(sorted(grades.values(), reverse=True)[:k])
    if idcg == 0:
        return None
    return _dcg([grades.get(chunk, 0) for chunk in ranking[:k]]) / idcg


def recall_at_k_files(
    ranking: list[str], grades: dict[str, int], chunk_paths: dict[str, str], k: int = K
) -> float | None:
    relevant = {chunk_paths[chunk] for chunk, grade in grades.items() if grade >= RELEVANT_GRADE}
    if not relevant:
        return None
    found = {chunk_paths.get(chunk) for chunk in ranking[:k]}
    return len(relevant & found) / len(relevant)


def paired_bootstrap(
    diffs: list[float], *, b: int = BOOTSTRAP_B, seed: int = BOOTSTRAP_SEED, alpha: float = ALPHA
) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(math.fsum(rng.choices(diffs, k=n)) / n for _ in range(b))
    return means[int(b * alpha / 2)], means[int(b * (1 - alpha / 2)) - 1]


def _mean(values: list[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def _scores(dataset: Dataset, qids: list[str], rankings: dict[str, list[str]]) -> dict[str, tuple]:
    scores: dict[str, tuple] = {}
    for qid in qids:
        grades = dataset.labels[qid]
        ndcg = ndcg_at_k(rankings[qid], grades)
        if ndcg is not None:
            scores[qid] = (ndcg, recall_at_k_files(rankings[qid], grades, dataset.chunk_paths))
    return scores


def _baseline_metrics(dataset: Dataset, qids: list[str], baseline: dict[str, list[str]]) -> dict | None:
    scores = _scores(dataset, qids, baseline)
    if not scores:
        return None
    return {
        "baseline_ndcg": _mean([ndcg for ndcg, _ in scores.values()]),
        "baseline_recall": _mean([recall for _, recall in scores.values() if recall is not None]),
        "n_groups": len({dataset.group_of[qid] for qid in scores}),
        "n_queries": len(scores),
        "n_excluded": len(qids) - len(scores),
    }


def _compare(
    dataset: Dataset, qids: list[str], baseline: dict[str, list[str]], candidate: dict[str, list[str]]
) -> dict | None:
    base = _scores(dataset, qids, baseline)
    if not base:
        return None
    cand = _scores(dataset, list(base), candidate)
    by_group: defaultdict[str, list[tuple[float, float]]] = defaultdict(list)
    for qid in base:
        by_group[dataset.group_of[qid]].append((base[qid][0], cand[qid][0]))
    groups = [by_group[group] for group in sorted(by_group)]
    base_means = [_mean([b for b, _ in pairs]) for pairs in groups]
    cand_means = [_mean([c for _, c in pairs]) for pairs in groups]
    diffs = [_mean([c - b for b, c in pairs]) for pairs in groups]
    ci_low, ci_high = paired_bootstrap(diffs)
    recall_pairs = [(base[qid][1], cand[qid][1]) for qid in base if base[qid][1] is not None]
    baseline_recall = _mean([b for b, _ in recall_pairs])
    candidate_recall = _mean([c for _, c in recall_pairs])
    return {
        "baseline_ndcg": _mean(base_means),
        "candidate_ndcg": _mean(cand_means),
        "mean_gain": _mean(diffs),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "baseline_recall": baseline_recall,
        "candidate_recall": candidate_recall,
        "recall_diff": None if not recall_pairs else candidate_recall - baseline_recall,
        "wins": sum(1 for qid in base if cand[qid][0] > base[qid][0]),
        "losses": sum(1 for qid in base if cand[qid][0] < base[qid][0]),
        "ties": sum(1 for qid in base if cand[qid][0] == base[qid][0]),
        "n_groups": len(groups),
        "n_queries": len(base),
        "n_excluded": len(qids) - len(base),
    }


def gate(dataset: Dataset, baseline: dict[str, list[str]], candidate: dict[str, list[str]]) -> dict:
    result = _compare(dataset, list(dataset.scored_queries), baseline, candidate)
    if result is None:
        raise DatasetError("no scored queries to compare")
    adversarial = [qid for qid in dataset.scored_queries if qid in dataset.adversarial]
    result["n_ambiguous"] = len(dataset.ambiguous)
    result["adversarial"] = _compare(dataset, adversarial, baseline, candidate)
    result["thresholds"] = {
        "ndcg_gain_min": NDCG_GAIN_MIN,
        "recall_drop_max": RECALL_DROP_MAX,
        "alpha": ALPHA,
        "b": BOOTSTRAP_B,
        "seed": BOOTSTRAP_SEED,
    }
    result["passed"] = (
        result["mean_gain"] >= NDCG_GAIN_MIN
        and result["ci_low"] > 0
        and result["recall_diff"] is not None
        and result["recall_diff"] >= -RECALL_DROP_MAX
    )
    return result


_METRIC_LABELS = (
    ("baseline_ndcg", "baseline nDCG@5"),
    ("candidate_ndcg", "candidate nDCG@5"),
    ("mean_gain", "mean nDCG@5 gain (per group)"),
    ("ci_low", "95% CI lower"),
    ("ci_high", "95% CI upper"),
    ("baseline_recall", "baseline recall@5 (files)"),
    ("candidate_recall", "candidate recall@5 (files)"),
    ("recall_diff", "recall@5 difference"),
    ("wins", "wins"),
    ("losses", "losses"),
    ("ties", "ties"),
    ("n_groups", "groups"),
    ("n_queries", "queries"),
    ("n_excluded", "excluded (no positive labels)"),
)


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metric_rows(metrics: dict | None) -> list[tuple[str, str]]:
    if metrics is None:
        return []
    return [(label, _fmt(metrics[key])) for key, label in _METRIC_LABELS if key in metrics]


def _common_value(receipts: list[dict], key: str) -> str:
    values = {receipt.get(key) for receipt in receipts}
    if len(values) == 1:
        return str(next(iter(values)))
    return "mixed"


def _receipt_context(receipts: list[dict]) -> dict:
    if not receipts:
        return {"has_receipts": False}
    latencies = [receipt["latency_ms"] for receipt in receipts]
    quantiles = statistics.quantiles(latencies, n=20) if len(latencies) >= 2 else None
    observed = [receipt["cost_usd"] for receipt in receipts if receipt["cost_usd"] is not None]
    return {
        "has_receipts": True,
        "n_receipts": len(receipts),
        "statuses": sorted(Counter(receipt["status"] for receipt in receipts).items()),
        "fallbacks": sorted(
            Counter(r["fallback_reason"] for r in receipts if r["fallback_reason"]).items()
        ),
        "cost_observed": f"${math.fsum(observed):.4f}",
        "cost_held": f"${math.fsum(receipt['held_usd'] for receipt in receipts):.4f}",
        "latency_p50": f"{quantiles[9]:.0f} ms" if quantiles else "n/a",
        "latency_p95": f"{quantiles[18]:.0f} ms" if quantiles else "n/a",
        "model": _common_value(receipts, "model_returned"),
        "rubric": _common_value(receipts, "rubric_version"),
    }


def render_report(
    dataset: Dataset,
    baseline: dict[str, list[str]],
    candidate: dict[str, list[str]] | None = None,
    receipts=(),
    *,
    title: str = "Retrieval baseline",
) -> str:
    adversarial = [qid for qid in dataset.scored_queries if qid in dataset.adversarial]
    if candidate is None:
        metrics = _baseline_metrics(dataset, list(dataset.scored_queries), baseline)
        adversarial_metrics = _baseline_metrics(dataset, adversarial, baseline)
        gate_result = None
    else:
        gate_result = gate(dataset, baseline, candidate)
        metrics = gate_result
        adversarial_metrics = gate_result["adversarial"]
    return render_package_template(
        "voss",
        "templates/eval/retrieval.md.jinja",
        {
            "title": title,
            "split": dataset.split,
            "commit": dataset.corpus.get("commit", "n/a"),
            "n_queries": len(dataset.queries),
            "n_groups": len(set(dataset.group_of.values())),
            "n_scored": len(dataset.scored_queries),
            "ranking": _metric_rows(metrics),
            "gate": gate_result,
            "adversarial": _metric_rows(adversarial_metrics),
            "n_adversarial": len(dataset.adversarial),
            "ambiguous": list(dataset.ambiguous),
            "receipts": _receipt_context(list(receipts)),
        },
    )


def _report(args: argparse.Namespace) -> int:
    if args.split == "test" and not args.locked_final:
        print("test split is locked; pass --locked-final only for the J3 comparison run", file=sys.stderr)
        return 2
    dataset = load_dataset(args.root, split=args.split, locked_final=args.locked_final)
    candidate = None
    if args.candidate:
        candidate = {row["query_id"]: row["ranking"] for row in _read_jsonl(args.candidate)}
    receipts = _read_jsonl(args.receipts) if args.receipts else []
    report = render_report(dataset, dataset.pools, candidate, receipts)
    if args.out:
        args.out.write_text(report)
    else:
        sys.stdout.write(report)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voss.eval.retrieval")
    commands = parser.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report", help="render the retrieval comparison report")
    report.add_argument("--root", type=Path, default=DATASET_ROOT)
    report.add_argument("--split", choices=SPLITS, default="dev")
    report.add_argument("--locked-final", action="store_true")
    report.add_argument("--candidate", type=Path)
    report.add_argument("--receipts", type=Path)
    report.add_argument("--out", type=Path)
    report.set_defaults(handler=_report)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
