from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from voss.eval.retrieval import (
    FLAGS,
    PINNED_COMMIT,
    SPLITS,
    DatasetError,
    LockedSplitError,
    _assign_splits,
    _read_jsonl,
    materialize,
)
from voss.harness.decision_review import load_checks, parse_criteria

DATASET_ROOT = Path("evals/review")
KINDS = ("missing_criterion", "contradicted", "failed_check", "skipped_check", "no_checks", "ambiguous", "supported")
GOLD = ("supported", "contradicted", "insufficient_evidence")
CONFIDENCES = ("high", "low")
ABSTAINED = ("abstained", "no_answer", None)
RELEASE_BAR = 0.05
START_THRESHOLD = 0.80
FREEZE_SEED = 20261010
_ID_RE = re.compile(r"rv-\d{3}")


def _all_rows(root: Path, batch: str | None = None) -> list[dict]:
    folder = Path(root) / "fixtures"
    paths = sorted(folder.glob(f"batch-{batch}.jsonl" if batch else "*.jsonl"))
    if not paths:
        raise DatasetError(f"no fixture files under {folder}")
    return [row for path in paths for row in _read_jsonl(path)]


def load_fixtures(root: Path = DATASET_ROOT, *, split: str, locked_final: bool = False) -> list[dict]:
    if split == "test" and not locked_final:
        raise LockedSplitError("test split is locked; pass locked_final=True only for the locked run")
    if split not in SPLITS:
        raise DatasetError(f"unknown split {split!r}")
    rows = _all_rows(root)
    if any(row.get("split") not in SPLITS for row in rows):
        raise DatasetError(f"{root}: dataset not frozen")
    return [row for row in rows if row["split"] == split]


def pairs(fixtures: list[dict]) -> list[dict]:
    return [
        {"fixture": row["id"], "kind": row["kind"], "criterion": cid, "gold": label["gold"], "flag": label["flag"]}
        for row in fixtures
        for cid, label in row["labels"].items()
    ]


def _problems(row: dict, shapes: dict, tree: Path) -> list[str]:
    problems = []
    kind = row.get("kind")
    shape = shapes.get(kind) if kind in KINDS else None
    if shape is None:
        problems.append(f"unknown kind {kind!r}")
    criteria = row.get("criteria")
    if not isinstance(criteria, list) or not all(isinstance(item, str) for item in criteria):
        problems.append("criteria must be a list of strings")
        criteria = []
    ids = [criterion.id for criterion in parse_criteria(criteria)]
    labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
    if set(labels) != set(ids):
        problems.append(f"label keys {sorted(labels)} do not match criterion ids {ids}")
    for cid, label in labels.items():
        problems += [
            f"{cid}: bad {field} {label.get(field)!r}"
            for field, allowed in (("gold", GOLD), ("confidence", CONFIDENCES), ("flag", FLAGS))
            if label.get(field) not in allowed
        ]
        if label.get("confidence") == "low" and label.get("flag") == "none":
            problems.append(f"{cid}: low confidence must be flagged")
    if shape is not None:
        if len(ids) != shape["criteria"]:
            problems.append(f"{kind} needs {shape['criteria']} criteria, has {len(ids)}")
        supported = sum(1 for label in labels.values() if label.get("gold") == "supported")
        if supported != shape["supported"]:
            problems.append(f"{kind} needs {shape['supported']} supported gold labels, has {supported}")
    try:
        statuses = {check.status for check in load_checks(row.get("checks"))}
    except ValueError as exc:
        problems.append(f"bad checks: {exc}")
        statuses = None
    if statuses is not None:
        if kind == "failed_check" and "failed" not in statuses:
            problems.append("failed_check needs a failed check")
        elif kind == "skipped_check" and "skipped" not in statuses:
            problems.append("skipped_check needs a skipped check")
        elif kind == "no_checks" and statuses:
            problems.append("no_checks must record no checks")
        elif kind not in ("failed_check", "skipped_check") and statuses & {"failed", "skipped"}:
            problems.append(f"{kind} must not have a failed or skipped check")
    diff = row.get("diff")
    if not isinstance(diff, str) or subprocess.run(
        ["git", "apply", "--check", "-"], cwd=tree, input=diff, capture_output=True, text=True
    ).returncode:
        problems.append("diff does not apply to the pinned tree")
    return problems


def check(args: argparse.Namespace) -> int:
    root = Path(args.root)
    corpus = json.loads((root / "corpus.json").read_text())
    rows = _all_rows(root, args.batch)
    ids = Counter(row.get("id") for row in _all_rows(root))
    tree = args.tree or materialize()
    problems = [] if corpus["commit"] == PINNED_COMMIT else [f"corpus.json: commit is not {PINNED_COMMIT}"]
    for row in rows:
        fid = row.get("id")
        if not isinstance(fid, str) or not _ID_RE.fullmatch(fid):
            problems.append(f"{fid!r}: bad id")
        elif ids[fid] > 1:
            problems.append(f"{fid}: duplicate id")
        problems += [f"{fid}: {problem}" for problem in _problems(row, corpus["kinds"], tree)]
    print("\n".join(problems) or f"{len(rows)} fixtures ok")
    return 1 if problems else 0


def review(args: argparse.Namespace) -> int:
    root = Path(args.root)
    flagged = []
    for row in _all_rows(root):
        texts = {criterion.id: criterion.text for criterion in parse_criteria(row["criteria"])}
        flagged += [
            (row["id"], cid, texts[cid], label)
            for cid, label in row["labels"].items()
            if label["flag"] == "review"
        ]
    lines = ["# Review labels to check", ""]
    if not flagged:
        lines.append("No pairs need review.")
    else:
        lines.append("For each pair: edit the fixture's label, set gold, then flag=reviewed (or flag=ambiguous).")
        for fid, cid, text, label in flagged:
            lines += ["", f"## {fid} {cid}", "", f"> {text}", "", f"- draft gold: `{label['gold']}`", f"- note: {label['note']}"]
    (root / "REVIEW.md").write_text("\n".join(lines) + "\n")
    print(f"{len(flagged)} pairs need review")
    return 0


def _split_counts(rows: list[dict]) -> dict:
    rows_pairs = pairs(rows)
    return {
        "fixtures": len(rows),
        "pairs": len(rows_pairs),
        "gold": dict(sorted(Counter(pair["gold"] for pair in rows_pairs).items())),
        "negatives": sum(1 for pair in rows_pairs if pair["gold"] != "supported" and pair["flag"] != "ambiguous"),
        "ambiguous": sum(1 for pair in rows_pairs if pair["flag"] == "ambiguous"),
    }


def _sha256_files(root: Path) -> dict[str, str]:
    paths = [root / "corpus.json", *sorted((root / "fixtures").glob("*.jsonl"))]
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def freeze(args: argparse.Namespace) -> int:
    root = Path(args.root)
    out = root / "freeze.json"
    if out.exists():
        print(f"{out} exists; the dataset is already frozen", file=sys.stderr)
        return 1
    paths = sorted((root / "fixtures").glob("*.jsonl"))
    rows = _all_rows(root)
    flagged = [f"{pair['fixture']}/{pair['criterion']}" for pair in pairs(rows) if pair["flag"] == "review"]
    if flagged:
        print("pairs still flagged for review:\n" + "\n".join(flagged), file=sys.stderr)
        return 1
    if check(argparse.Namespace(root=root, batch=None, tree=args.tree)):
        print("check failed; nothing frozen", file=sys.stderr)
        return 1
    corpus = json.loads((root / "corpus.json").read_text())
    kinds = Counter(row["kind"] for row in rows)
    expected = Counter({kind: shape["fixtures"] for kind, shape in corpus["kinds"].items()})
    if kinds != expected:
        print(f"fixtures per kind {dict(kinds)}, expected {dict(expected)}; nothing frozen", file=sys.stderr)
        return 1
    split_of = _assign_splits({row["id"]: [row] for row in rows}, args.seed)
    counts = {split: _split_counts([row for row in rows if split_of[row["id"]] == split]) for split in SPLITS}
    if counts["dev"]["pairs"] != counts["test"]["pairs"]:
        print(f"dev has {counts['dev']['pairs']} pairs, test {counts['test']['pairs']}; nothing frozen", file=sys.stderr)
        return 1
    if counts["test"]["negatives"] < corpus["min_locked_negatives"]:
        print(
            f"test has {counts['test']['negatives']} negatives, needs {corpus['min_locked_negatives']}; nothing frozen",
            file=sys.stderr,
        )
        return 1
    for path in paths:
        path.write_text("".join(json.dumps({**row, "split": split_of[row["id"]]}) + "\n" for row in _read_jsonl(path)))
    frozen = {
        "frozen_at": datetime.now(timezone.utc).date().isoformat(),
        "commit": corpus["commit"],
        "rubric_version": corpus["rubric_version"],
        "seed": args.seed,
        "split_algorithm": (
            "each fixture is one group, so all of its criteria share a split; for each kind in sorted order, "
            "sort fixture ids and shuffle with one random.Random(seed); concatenate; assign alternately dev, test "
            "starting with dev"
        ),
        "splits": counts,
        "metrics": {
            "false_supported": (
                "pairs shown supported whose gold is contradicted or insufficient_evidence, over all non-supported "
                "gold pairs; Wilson 95% interval"
            ),
            "contradicted_recall": "pairs shown contradicted over gold contradicted pairs; Wilson 95% interval",
            "abstention_rate": "pairs shown abstained or no_answer, or whose call failed, over all scored pairs",
            "coverage": "1 - abstention_rate",
            "ambiguity": "pairs flagged ambiguous; excluded from every rate and listed separately",
            "brier": "mean (P(supported) - [gold == supported])^2 over scored pairs with probabilities",
            "latency": "p50 and p95 latency_ms over answered receipts",
            "cost": "total and mean observed cost_usd over receipts",
        },
        "threshold_policy": {
            "start": START_THRESHOLD,
            "tuning": "dev split only",
            "locked": "decision_review.THRESHOLD at the locked run, recorded in reports/review-test.json",
        },
        "release_bar": {
            "false_supported_max": RELEASE_BAR,
            "basis": "point estimate on the locked split",
            "interval": "Wilson 95%, reported, not gating",
        },
        "files": _sha256_files(root),
    }
    out.write_text(json.dumps(frozen, indent=2) + "\n")
    for split, split_counts in counts.items():
        print(f"{split}: {split_counts['fixtures']} fixtures, {split_counts['pairs']} pairs, {split_counts['negatives']} negatives")
    print(f"wrote {out}")
    return 0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": k / n if n else None}


def _proportion(k: int, n: int) -> dict:
    return {**_rate(k, n), "ci": list(wilson(k, n))}


def score(rows: list[dict]) -> dict:
    ambiguous = [row for row in rows if row["flag"] == "ambiguous"]
    scored = [row for row in rows if row["flag"] != "ambiguous"]
    negatives = [row for row in scored if row["gold"] != "supported"]
    contradicted = [row for row in scored if row["gold"] == "contradicted"]
    false_supported = _proportion(sum(1 for row in negatives if row["label"] == "supported"), len(negatives))
    abstention = _rate(sum(1 for row in scored if row["label"] in ABSTAINED), len(scored))
    errors = [
        (row["probabilities"]["supported"] - (row["gold"] == "supported")) ** 2 for row in scored if row["probabilities"]
    ]
    by_kind: dict = {}
    for row in scored:
        cell = by_kind.setdefault(row["kind"], {}).setdefault(row["gold"], {})
        shown = row["label"] or "failed"
        cell[shown] = cell.get(shown, 0) + 1
    return {
        "false_supported": false_supported,
        "contradicted_recall": _proportion(sum(1 for row in contradicted if row["label"] == "contradicted"), len(contradicted)),
        "abstention": abstention,
        "coverage": 1 - abstention["rate"] if scored else None,
        "failed": sum(1 for row in scored if row["label"] is None),
        "ambiguous": {"count": len(ambiguous), "pairs": [f"{row['fixture']}/{row['criterion']}" for row in ambiguous]},
        "brier": math.fsum(errors) / len(errors) if errors else None,
        "by_kind": by_kind,
        "passed": false_supported["n"] > 0 and false_supported["rate"] <= RELEASE_BAR,
    }


def receipt_summary(receipts: list[dict]) -> dict:
    answered = [receipt for receipt in receipts if receipt["status"] == "answered"]
    costs = [receipt["cost_usd"] for receipt in receipts if receipt["cost_usd"] is not None]
    latencies = [receipt["latency_ms"] for receipt in answered]
    sizes = [receipt["detail"]["request_bytes"] for receipt in answered]
    quantiles = statistics.quantiles(latencies, n=20) if len(latencies) >= 2 else None
    return {
        "calls": len(receipts),
        "answered": len(answered),
        "cost_usd_total": math.fsum(costs),
        "cost_usd_mean": math.fsum(costs) / len(costs) if costs else None,
        "latency_p50_ms": quantiles[9] if quantiles else None,
        "latency_p95_ms": quantiles[18] if quantiles else None,
        "request_bytes_median": statistics.median(sizes) if sizes else None,
        "request_bytes_max": max(sizes, default=None),
        "models": sorted({receipt["model_returned"] for receipt in receipts if receipt["model_returned"]}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voss.eval.review")
    commands = parser.add_subparsers(dest="command", required=True)
    check_parser = commands.add_parser("check", help="validate fixtures and check that every diff applies")
    check_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    check_parser.add_argument("--batch")
    check_parser.add_argument("--tree", type=Path)
    check_parser.set_defaults(handler=check)
    review_parser = commands.add_parser("review", help="write REVIEW.md with the pairs flagged for review")
    review_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    review_parser.set_defaults(handler=review)
    freeze_parser = commands.add_parser("freeze", help="assign the locked dev/test split and write freeze.json")
    freeze_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    freeze_parser.add_argument("--seed", type=int, default=FREEZE_SEED)
    freeze_parser.add_argument("--tree", type=Path)
    freeze_parser.set_defaults(handler=freeze)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except DatasetError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
