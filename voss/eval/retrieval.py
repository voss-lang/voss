"""Retrieval baseline evaluation: dataset loader, ranking metrics, J3 gate, report (J2 S2.4/S2.5)."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from voss.harness import config, judgments
from voss.harness.code.index import build_index
from voss.harness.code.rerank import RUBRIC_VERSION, rerank
from voss.harness.code.semantic_index import Candidate, CodeIndex, _effective_embedding_model
from voss.harness.memory_store import Hit
from voss.template_render import render_package_template
from voss_runtime._config import configure, get_config
from voss_runtime.judgments import JudgmentLedger, is_killed

GRADES = {"irrelevant": 0, "contextual": 1, "directly_useful": 2, "necessary": 3}
RELEVANT_GRADE = 2
K = 5
POOL_SIZE = 15
NDCG_GAIN_MIN = 0.03
RECALL_DROP_MAX = 0.0
BOOTSTRAP_B = 10_000
BOOTSTRAP_SEED = 20261003
ALPHA = 0.05
LATENCY_P95_MAX_MS = 1000
LATENCY_MIN_SAMPLES = 100
DATASET_ROOT = Path("evals/retrieval")
PINNED_COMMIT = "c1a27046aef3096e460b1c24b59d8066e5c2f792"
EXCLUDED_PATHS = ("tests/code_recall/test_golden_queries.py",)
LABEL_FIELDS = (
    "query_id", "chunk_id", "path", "line_start", "line_end", "text_sha",
    "source", "grade", "confidence", "flag", "note",
)
PREVIEW_LINES = 8
PREVIEW_WIDTH = 100

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


def materialize(commit: str = PINNED_COMMIT) -> Path:
    repo = Path(__file__).resolve().parents[2]
    probe = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True
    )
    if probe.returncode:
        raise DatasetError("pinned commit not available; fetch origin/master")
    dest = Path(tempfile.gettempdir()) / f"voss-retrieval-{commit[:12]}"
    if (dest / ".complete").exists():
        return dest
    staging = Path(tempfile.mkdtemp(prefix=f"{dest.name}.", dir=dest.parent))
    try:
        proc = subprocess.Popen(
            ["git", "-C", str(repo), "archive", "--format=tar", commit], stdout=subprocess.PIPE
        )
        with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
            archive.extractall(staging, filter=_data_or_skip)
        if proc.wait():
            raise DatasetError(f"git archive {commit} failed")
        (staging / ".complete").touch()
        shutil.rmtree(dest, ignore_errors=True)
        staging.rename(dest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return dest


def _data_or_skip(member: tarfile.TarInfo, dest: str) -> tarfile.TarInfo | None:
    try:
        return tarfile.data_filter(member, dest)
    except tarfile.FilterError:
        return None


@contextlib.contextmanager
def _local_embedding_config():
    saved = {key: os.environ.get(key) for key in ("XDG_CONFIG_HOME", "OPENAI_API_KEY")}
    previous = get_config().default_embedding_model
    with tempfile.TemporaryDirectory() as config_home:
        os.environ["XDG_CONFIG_HOME"] = config_home
        os.environ.pop("OPENAI_API_KEY", None)
        configure(default_embedding_model=get_config().local_embedding_model)
        try:
            yield
        finally:
            configure(default_embedding_model=previous)
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _chunks(index: CodeIndex) -> dict[str, tuple[str, int, int, str]]:
    return {cid: (rel, start, end, text) for cid, text, rel, start, end in index._bm25_chunks}


def _entry(chunk_id: str, chunk: tuple[str, int, int, str]) -> dict:
    path, start, end, text = chunk
    return {"chunk_id": chunk_id, "path": path, "line_start": start, "line_end": end, "text_sha": _text_sha(text)}


def chunk_map(corpus_dir: Path) -> dict[str, tuple[str, int, int, str]]:
    build_index(Path(corpus_dir))
    index = CodeIndex(corpus_dir)
    index._ensure_bm25()
    return _chunks(index)


def build_pools(corpus_dir: Path, queries: list[dict], *, require_vector: bool = True) -> list[dict]:
    corpus_dir = Path(corpus_dir)
    with _local_embedding_config():
        build_index(corpus_dir)
        index = CodeIndex(corpus_dir)
        if require_vector and index._maybe_semantic() is None:
            raise DatasetError("vector backend unavailable; baseline requires BM25+vector ranking")
        index.build(session_id="retrieval-baseline")
        chunks = _chunks(index)
        model = _effective_embedding_model()
        rows = []
        for query in queries:
            hits = [
                hit for hit in index.query(query["text"], top_k=POOL_SIZE)
                if chunks[hit.locator][0] not in EXCLUDED_PATHS
            ]
            bm25 = [
                hit.locator for hit in index._bm25_query(query["text"], POOL_SIZE)
                if chunks[hit.locator][0] not in EXCLUDED_PATHS
            ]
            rows.append({
                "query_id": query["id"],
                "embedding_model": model,
                "pool": [
                    {"rank": rank, **_entry(hit.locator, chunks[hit.locator]), "score": hit.score}
                    for rank, hit in enumerate(hits, start=1)
                ],
                "bm25": bm25,
            })
    return rows


def _pinned_chunks() -> dict[str, tuple[str, int, int, str]]:
    return chunk_map(materialize(PINNED_COMMIT))


def divergence(index, queries: dict[str, dict]) -> list[str]:
    return sorted(
        qid for qid, row in queries.items()
        if [hit.locator for hit in index.query(row["text"], top_k=K)]
        != [hit.locator for hit in index.query(row["text"], top_k=POOL_SIZE)[:K]]
    )


def _divergence(args: argparse.Namespace) -> int:
    dataset = load_dataset(args.root, split="dev")
    corpus = materialize(PINNED_COMMIT)
    with _local_embedding_config():
        build_index(corpus)
        index = CodeIndex(corpus)
        if index._maybe_semantic() is None:
            raise DatasetError("vector backend unavailable; divergence needs BM25+vector ranking")
        index.build(session_id="retrieval-divergence")
        differing = divergence(index, dataset.queries)
    print(
        f"{len(differing)}/{len(dataset.queries)} dev queries differ between "
        f"query(top_k=5) and query(top_k=15)[:5]"
    )
    for qid in differing:
        print(qid)
    return 0


def latency_gate(receipts: list[dict]) -> dict:
    n = sum(1 for receipt in receipts if receipt["status"] == "answered")
    dispatched = [receipt["latency_ms"] for receipt in receipts if receipt["attempts"] > 0]
    quantiles = statistics.quantiles(dispatched, n=20) if len(dispatched) >= 2 else None
    p95 = quantiles[18] if quantiles else None
    return {
        "n": n,
        "p50_ms": quantiles[9] if quantiles else None,
        "p95_ms": p95,
        "passed": n >= LATENCY_MIN_SAMPLES and p95 is not None and p95 <= LATENCY_P95_MAX_MS,
    }


def _candidate(chunk_id: str, chunk: tuple[str, int, int, str]) -> Candidate:
    path, start, end, text = chunk
    hit = Hit(source="code", locator=chunk_id, score=0.0, excerpt="", line_start=start, line_end=end)
    return Candidate(hit, path, start, end, text, fresh=True)


async def _rerank_pools(
    dataset: Dataset, candidates: dict[str, list[Candidate]]
) -> tuple[dict[str, list[str]], list[dict]]:
    cfg = config.get_judgments_config()
    rankings: dict[str, list[str]] = {}
    receipts: list[dict] = []
    for qid, cands in candidates.items():
        ledger = JudgmentLedger(cfg["max_calls_per_turn"], cfg["max_cost_usd"])
        order = await rerank(cands, task=dataset.queries[qid]["text"], mode="active", ledger=ledger)
        rankings[qid] = [cands[i].hit.locator for i in order]
        receipts.append(asdict(ledger.receipts[0]))
    return rankings, receipts


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _ms(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0f} ms"


def _rerank(args: argparse.Namespace) -> int:
    if args.split == "test" and not args.locked_final:
        print("test split is locked; pass --locked-final only for the J3 comparison run", file=sys.stderr)
        return 2
    if is_killed() or judgments.resolve_api_key() is None:
        print("rerank needs Jev: set TYPESAFE_API_KEY and leave VOSS_JUDGMENTS on", file=sys.stderr)
        return 2
    dataset = load_dataset(args.root, split=args.split, locked_final=args.locked_final)
    reports = Path(args.root) / "reports"
    gate_path = reports / f"rerank-{args.split}.json"
    if args.split == "test" and gate_path.exists():
        raise DatasetError(f"{gate_path} exists; the locked test split is scored once (D-19)")
    chunks = _pinned_chunks()
    missing = sorted({cid for pool in dataset.pools.values() for cid in pool} - chunks.keys())
    if missing:
        raise DatasetError(f"pool chunks missing at the pinned commit: {missing}")
    candidates = {qid: [_candidate(cid, chunks[cid]) for cid in pool] for qid, pool in dataset.pools.items()}
    reports.mkdir(parents=True, exist_ok=True)
    if args.split == "test":
        gate_path.write_text(json.dumps({
            "schema_version": 1, "split": "test", "status": "started",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2) + "\n")
    candidate, receipts = asyncio.run(_rerank_pools(dataset, candidates))
    out_dir = args.out_dir or reports / f"rerank-{args.split}"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / "candidate.jsonl", [{"query_id": qid, "ranking": ranking} for qid, ranking in candidate.items()])
    _write_jsonl(out_dir / "receipts.jsonl", receipts)
    _write_jsonl(out_dir / "samples.jsonl", [
        {
            "query_id": qid, "request_bytes": receipt["detail"]["request_bytes"], "location": args.location,
            "model": receipt["model_requested"], "latency_ms": receipt["latency_ms"],
            "status": receipt["status"], "fallback_reason": receipt["fallback_reason"],
        }
        for qid, receipt in zip(candidate, receipts)
    ])
    ranking = gate(dataset, dataset.pools, candidate)
    latency = latency_gate(receipts)
    report = render_report(dataset, dataset.pools, candidate, receipts, title=f"Code recall rerank ({args.split})")
    report += (
        "\n## Shadow\n\n"
        "- shadow serves the baseline order (nDCG@5 gain 0.0 by definition) and sends the same Jev requests as active\n"
        "\n## Latency gate\n\n"
        f"- location: `{args.location}`\n"
        f"- answered requests: {latency['n']} (need >= {LATENCY_MIN_SAMPLES})\n"
        f"- p50: {_ms(latency['p50_ms'])}\n"
        f"- p95: {_ms(latency['p95_ms'])} (max {LATENCY_P95_MAX_MS} ms, timeouts included)\n"
        f"- gate: **{'PASS' if latency['passed'] else 'FAIL'}**\n"
    )
    (reports / f"rerank-{args.split}.md").write_text(report)
    gate_path.write_text(json.dumps({
        "schema_version": 1,
        "status": "complete",
        "split": args.split,
        "commit": dataset.corpus["commit"],
        "model": _common_value([r for r in receipts if r["model_returned"]], "model_returned"),
        "rubric_version": RUBRIC_VERSION,
        "location": args.location,
        "run_date": datetime.now(timezone.utc).date().isoformat(),
        "ranking": {key: ranking[key] for key in ("mean_gain", "ci_low", "ci_high", "recall_diff", "passed")},
        "latency": latency,
        "fallbacks": dict(Counter(r["fallback_reason"] for r in receipts if r["fallback_reason"])),
        "passed": ranking["passed"] and latency["passed"],
    }, indent=2) + "\n")
    print(f"wrote {gate_path}")
    return 0


def _batch_file(root: Path, kind: str, batch: str) -> Path:
    return Path(root) / kind / f"batch-{batch}.{'csv' if kind == 'labels' else 'jsonl'}"


def _read_labels(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_labels(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _label_row(query_id: str, entry: dict, source: str) -> dict:
    return {
        "query_id": query_id, **{field: entry[field] for field in LABEL_FIELDS[1:6]},
        "source": source, "grade": "", "confidence": "", "flag": "none", "note": "",
    }


def _pool(root: Path, batch: str, query_id: str) -> list[dict]:
    for row in _read_jsonl(_batch_file(root, "baseline", batch)):
        if row["query_id"] == query_id:
            return sorted(row["pool"], key=lambda entry: entry["rank"])
    raise DatasetError(f"{query_id}: no baseline pool in batch {batch}")


def _preview(text: str) -> list[str]:
    return [line[:PREVIEW_WIDTH] for line in text.splitlines() if line.strip()][:PREVIEW_LINES]


def _parse_grade(token: str) -> dict:
    low = token.endswith("?")
    digit = token[:-1] if low else token
    if digit not in ("0", "1", "2", "3"):
        raise DatasetError(f"bad grade {token!r}; use 0-3 with an optional ? suffix")
    return {
        "grade": list(GRADES)[int(digit)],
        "confidence": "low" if low else "high",
        "flag": "review" if low else "none",
    }


def _baseline(args: argparse.Namespace) -> int:
    out = _batch_file(args.root, "baseline", args.batch)
    if out.exists() and not args.force:
        print(f"{out} exists; pass --force to rebuild", file=sys.stderr)
        return 2
    queries = _read_jsonl(_batch_file(args.root, "queries", args.batch))
    rows = build_pools(materialize(PINNED_COMMIT), queries)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(row) + "\n" for row in rows))
    labels_path = _batch_file(args.root, "labels", args.batch)
    labels = _read_labels(labels_path)
    seen = {(row["query_id"], row["chunk_id"]) for row in labels}
    added = [
        _label_row(row["query_id"], entry, "pool")
        for row in rows
        for entry in row["pool"]
        if (row["query_id"], entry["chunk_id"]) not in seen
    ]
    _write_labels(labels_path, labels + added)
    print(f"{len(rows)} queries pooled; {len(added)} label rows added")
    return 0


def _pool_cmd(args: argparse.Namespace) -> int:
    chunks = _pinned_chunks()
    if args.full:
        if args.full not in chunks:
            raise DatasetError(f"unknown chunk {args.full}")
        print(chunks[args.full][3])
        return 0
    if args.path:
        found = sorted(cid for cid, chunk in chunks.items() if chunk[0] == args.path)
        if not found:
            raise DatasetError(f"no chunks for {args.path} at the pinned commit")
        for cid in found:
            print(f"{cid} {chunks[cid][1]}-{chunks[cid][2]}")
        return 0
    if not (args.batch and args.query):
        raise DatasetError("pool needs --batch and --query, --full, or --path")
    texts = {row["id"]: row["text"] for row in _read_jsonl(_batch_file(args.root, "queries", args.batch))}
    grades = {
        row["chunk_id"]: row["grade"]
        for row in _read_labels(_batch_file(args.root, "labels", args.batch))
        if row["query_id"] == args.query
    }
    print(texts[args.query])
    for entry in _pool(args.root, args.batch, args.query):
        cid = entry["chunk_id"]
        print(f"{entry['rank']}. {cid} {entry['path']}:{entry['line_start']}-{entry['line_end']} [{grades.get(cid) or '-'}]")
        for line in _preview(chunks[cid][3]):
            print(f"    {line}")
    return 0


def _grade(args: argparse.Namespace) -> int:
    path = _batch_file(args.root, "labels", args.batch)
    rows = _read_labels(path)
    mine = {row["chunk_id"]: row for row in rows if row["query_id"] == args.query}
    pool = _pool(args.root, args.batch, args.query)
    updates: dict[str, dict] = {}
    if args.grades is not None:
        tokens = args.grades.split()
        if len(tokens) != len(pool):
            raise DatasetError(f"{args.query}: {len(tokens)} grades for {len(pool)} pool rows")
        updates = {entry["chunk_id"]: _parse_grade(token) for entry, token in zip(pool, tokens)}
        missing = [cid for cid in updates if cid not in mine]
        if missing:
            raise DatasetError(f"{args.query}: no label rows for {missing}; run baseline first")
    new_rows = []
    if args.extra:
        chunks = _pinned_chunks()
        for item in args.extra:
            chunk_id, _, token = item.rpartition("=")
            if chunk_id not in chunks:
                raise DatasetError(f"unknown chunk {chunk_id}")
            updates[chunk_id] = _parse_grade(token)
            if chunk_id not in mine:
                mine[chunk_id] = _label_row(args.query, _entry(chunk_id, chunks[chunk_id]), "gold")
                new_rows.append(mine[chunk_id])
    for chunk_id, values in updates.items():
        mine[chunk_id].update(values)
    if args.ambiguous:
        for row in mine.values():
            row["flag"] = "ambiguous"
    _write_labels(path, rows + new_rows)
    print(f"{args.query}: {len(updates)} rows graded")
    return 0


def _review(args: argparse.Namespace) -> int:
    root = Path(args.root)
    texts = {row["id"]: row["text"] for path in sorted((root / "queries").glob("*.jsonl")) for row in _read_jsonl(path)}
    lines = [
        "# Retrieval labels to review",
        "",
        "| batch | rows | graded | flagged | ambiguous queries |",
        "|---|---|---|---|---|",
    ]
    flagged: defaultdict[str, list[tuple[Path, dict]]] = defaultdict(list)
    for path in sorted((root / "labels").glob("*.csv")):
        rows = _read_labels(path)
        graded = sum(1 for row in rows if row["grade"])
        review = [row for row in rows if row["flag"] == "review"]
        ambiguous = len({row["query_id"] for row in rows if row["flag"] == "ambiguous"})
        lines.append(f"| {path.stem.removeprefix('batch-')} | {len(rows)} | {graded} | {len(review)} | {ambiguous} |")
        for row in review:
            flagged[row["query_id"]].append((path, row))
    lines.append("")
    if not flagged:
        lines.append("No rows need review.")
    else:
        chunks = _pinned_chunks()
        lines.append("For each row: edit the named labels CSV, set grade, then flag=reviewed (or flag=ambiguous).")
        for qid in sorted(flagged):
            lines += ["", f"## {qid}", "", f"> {texts[qid]}"]
            for path, row in flagged[qid]:
                lines += [
                    "",
                    f"- `{row['chunk_id']}` {row['path']}:{row['line_start']}-{row['line_end']}; "
                    f"proposed `{row['grade']}`; edit `{path.relative_to(root)}`",
                    "",
                    "```",
                    *_preview(chunks[row["chunk_id"]][3]),
                    "```",
                ]
    (root / "REVIEW.md").write_text("\n".join(lines) + "\n")
    print(f"{sum(len(rows) for rows in flagged.values())} rows need review")
    return 0


def _check(args: argparse.Namespace) -> int:
    rows = _read_labels(_batch_file(args.root, "labels", args.batch))
    chunks = _pinned_chunks()
    vocab = (("source", SOURCES), ("grade", ("", *GRADES)), ("confidence", CONFIDENCES), ("flag", FLAGS))
    problems = []
    for row in rows:
        where = f"{row['query_id']}/{row['chunk_id']}"
        problems += [f"{where}: bad {field} {row[field]!r}" for field, allowed in vocab if row[field] not in allowed]
        if not row["grade"]:
            problems.append(f"{where}: ungraded")
        chunk = chunks.get(row["chunk_id"])
        if chunk is None:
            problems.append(f"{where}: chunk missing at the pinned commit")
        elif _text_sha(chunk[3]) != row["text_sha"]:
            problems.append(f"{where}: text_sha mismatch")
    labeled = {(row["query_id"], row["chunk_id"]) for row in rows}
    pools = {row["query_id"]: row["pool"] for row in _read_jsonl(_batch_file(args.root, "baseline", args.batch))}
    for query in _read_jsonl(_batch_file(args.root, "queries", args.batch)):
        if query["id"] not in pools:
            problems.append(f"{query['id']}: no baseline pool")
    for qid, pool in pools.items():
        problems += [
            f"{qid}/{entry['chunk_id']}: pool chunk has no label row"
            for entry in pool
            if (qid, entry["chunk_id"]) not in labeled
        ]
    print("\n".join(problems) or f"batch {args.batch}: {len(rows)} rows ok")
    return 1 if problems else 0


def _assign_splits(groups: dict[str, list[dict]], seed: int) -> dict[str, str]:
    by_kind: defaultdict[str, list[str]] = defaultdict(list)
    for group, rows in groups.items():
        by_kind[rows[0]["kind"]].append(group)
    rng = random.Random(seed)
    order: list[str] = []
    for kind in sorted(by_kind):
        ids = sorted(by_kind[kind])
        rng.shuffle(ids)
        order += ids
    return {group: SPLITS[i % 2] for i, group in enumerate(order)}


def _structure(root: Path) -> dict[str, dict]:
    counts = {}
    for split in SPLITS:
        dataset = load_dataset(root, split=split, locked_final=True)
        missing = sorted(qid for qid in dataset.queries if qid not in dataset.pools)
        if missing:
            raise DatasetError(f"{split}: queries without a baseline pool: {missing}")
        counts[split] = {
            "groups": len(set(dataset.group_of.values())),
            "queries": len(dataset.queries),
            "adversarial_groups": len({dataset.group_of[qid] for qid in dataset.adversarial}),
            "ambiguous_groups": len({dataset.group_of[qid] for qid in dataset.ambiguous}),
        }
    return counts


def _sha256_files(root: Path) -> dict[str, str]:
    paths = [root / "corpus.json"] + [
        path for sub in ("queries", "baseline", "labels") for path in sorted((root / sub).rglob("*")) if path.is_file()
    ]
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def freeze(args: argparse.Namespace) -> int:
    root = Path(args.root)
    out = root / "freeze.json"
    if out.exists():
        print(f"{out} exists; the dataset is already frozen", file=sys.stderr)
        return 1
    flagged = [
        f"{path.name}: {row['query_id']}/{row['chunk_id']}"
        for path in sorted((root / "labels").glob("*.csv"))
        for row in _read_labels(path)
        if row["flag"] == "review"
    ]
    if flagged:
        print("rows still flagged for review:\n" + "\n".join(flagged), file=sys.stderr)
        return 1
    query_files = sorted((root / "queries").glob("batch-*.jsonl"))
    batches = [path.stem.removeprefix("batch-") for path in query_files]
    if any(_check(argparse.Namespace(root=root, batch=batch)) for batch in batches):
        print("batch check failed; nothing frozen", file=sys.stderr)
        return 1
    originals = {path: path.read_text() for path in query_files}
    groups: dict[str, list[dict]] = {}
    for path in query_files:
        for row in _read_jsonl(path):
            groups.setdefault(row["group"], []).append(row)
    if len(groups) != args.expect_groups:
        print(f"{len(groups)} groups, expected {args.expect_groups}; nothing frozen", file=sys.stderr)
        return 1
    split_of = _assign_splits(groups, args.seed)
    for path in query_files:
        rows = [{**row, "split": split_of[row["group"]]} for row in _read_jsonl(path)]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    try:
        counts = _structure(root)
    except DatasetError:
        for path, text in originals.items():
            path.write_text(text)
        raise
    frozen = {
        "frozen_at": datetime.now(timezone.utc).date().isoformat(),
        "commit": json.loads((root / "corpus.json").read_text())["commit"],
        "seed": args.seed,
        "split_algorithm": (
            "group kind = kind of the group's first query; for each kind in sorted order, sort group ids "
            "and shuffle with one random.Random(seed); concatenate; assign alternately dev, test starting with dev"
        ),
        "splits": counts,
        "metrics": {
            "k": K,
            "ndcg": {
                "gain": "2^g-1",
                "discount": "1/log2(rank+1)",
                "idcg": "all labeled chunks of the query, including gold chunks outside the pool",
            },
            "recall": (
                f"relevant-file recall@{K}: files owning a chunk graded directly_useful or necessary, "
                "macro-averaged over scored queries with at least one relevant file"
            ),
            "bootstrap": {"method": "paired percentile", "b": BOOTSTRAP_B, "seed": BOOTSTRAP_SEED, "unit": "group", "alpha": ALPHA},
            "ambiguous": "excluded from the gate and listed separately",
            "adversarial": "counted in the gate and reported separately",
        },
        "thresholds": {"ndcg_gain_min": NDCG_GAIN_MIN, "ci": "lower bound > 0", "recall_drop_max": RECALL_DROP_MAX},
        "files": _sha256_files(root),
    }
    out.write_text(json.dumps(frozen, indent=2) + "\n")
    for split, split_counts in counts.items():
        print(f"{split}: {split_counts['groups']} groups, {split_counts['queries']} queries")
    print(f"wrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voss.eval.retrieval")
    commands = parser.add_subparsers(dest="command", required=True)
    baseline = commands.add_parser("baseline", help="compute baseline pools at the pinned commit")
    baseline.add_argument("--root", type=Path, default=DATASET_ROOT)
    baseline.add_argument("--batch", required=True)
    baseline.add_argument("--force", action="store_true")
    baseline.set_defaults(handler=_baseline)
    pool = commands.add_parser("pool", help="show a query's pool for grading")
    pool.add_argument("--root", type=Path, default=DATASET_ROOT)
    pool.add_argument("--batch")
    pool.add_argument("--query")
    pool.add_argument("--full", metavar="CHUNK_ID")
    pool.add_argument("--path", metavar="FILE")
    pool.set_defaults(handler=_pool_cmd)
    grade = commands.add_parser("grade", help="record grades for a query's pool")
    grade.add_argument("--root", type=Path, default=DATASET_ROOT)
    grade.add_argument("--batch", required=True)
    grade.add_argument("--query", required=True)
    grade.add_argument("--grades")
    grade.add_argument("--extra", action="append", default=[], metavar="CHUNK_ID=G")
    grade.add_argument("--ambiguous", action="store_true")
    grade.set_defaults(handler=_grade)
    review = commands.add_parser("review", help="write REVIEW.md with flagged rows")
    review.add_argument("--root", type=Path, default=DATASET_ROOT)
    review.set_defaults(handler=_review)
    check = commands.add_parser("check", help="check a batch for ungraded rows and drift")
    check.add_argument("--root", type=Path, default=DATASET_ROOT)
    check.add_argument("--batch", required=True)
    check.set_defaults(handler=_check)
    freeze_parser = commands.add_parser("freeze", help="assign the locked dev/test split and write freeze.json")
    freeze_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    freeze_parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    freeze_parser.add_argument("--expect-groups", type=int, default=200)
    freeze_parser.set_defaults(handler=freeze)
    report = commands.add_parser("report", help="render the retrieval comparison report")
    report.add_argument("--root", type=Path, default=DATASET_ROOT)
    report.add_argument("--split", choices=SPLITS, default="dev")
    report.add_argument("--locked-final", action="store_true")
    report.add_argument("--candidate", type=Path)
    report.add_argument("--receipts", type=Path)
    report.add_argument("--out", type=Path)
    report.set_defaults(handler=_report)
    divergence_parser = commands.add_parser(
        "divergence", help="count dev queries where query(top_k=5) differs from the pool's top 5"
    )
    divergence_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    divergence_parser.set_defaults(handler=_divergence)
    rerank_parser = commands.add_parser("rerank", help="rerank stored pools with Jev and write the comparison and gate file")
    rerank_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    rerank_parser.add_argument("--split", choices=SPLITS, default="dev")
    rerank_parser.add_argument("--locked-final", action="store_true")
    rerank_parser.add_argument("--location", required=True)
    rerank_parser.add_argument("--out-dir", type=Path)
    rerank_parser.set_defaults(handler=_rerank)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except DatasetError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
