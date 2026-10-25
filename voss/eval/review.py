from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import click

from voss.eval import runner
from voss.eval.retrieval import (
    FLAGS,
    PINNED_COMMIT,
    SPLITS,
    DatasetError,
    LockedSplitError,
    _assign_splits,
    _common_value,
    _read_jsonl,
    _write_jsonl,
    materialize,
)
from voss.harness import config, decision_review, judgments
from voss.harness.board.reviewer_b import ReviewerB, build_repo_context
from voss.harness.decision_review import NO_CHECKS, build_packet, load_checks, parse_criteria, touched_paths
from voss_runtime.judgments import KILLED_MESSAGE, MISSING_KEY_MESSAGE, JudgmentError, JudgmentLedger, is_killed

DATASET_ROOT = Path("evals/review")
KINDS = ("missing_criterion", "contradicted", "failed_check", "skipped_check", "no_checks", "ambiguous", "supported")
GOLD = ("supported", "contradicted", "insufficient_evidence")
CONFIDENCES = ("high", "low")
ABSTAINED = ("abstained", "no_answer", None)
RELEASE_BAR = 0.05
START_THRESHOLD = 0.80
FREEZE_SEED = 20261010
TUNE_THRESHOLDS = tuple(round(0.55 + 0.05 * n, 2) for n in range(9))
BASELINE_MODEL = "claude-sonnet-5-5"
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
    locked_only = corpus.get("locked_only", False)
    if locked_only:
        split_of = dict.fromkeys((row["id"] for row in rows), "test")
    else:
        split_of = _assign_splits({row["id"]: [row] for row in rows}, args.seed)
    counts = {split: _split_counts([row for row in rows if split_of[row["id"]] == split]) for split in SPLITS}
    if not locked_only and counts["dev"]["pairs"] != counts["test"]["pairs"]:
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
        "split_algorithm": "every fixture is test" if locked_only else (
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


def _frozen(root: Path) -> dict:
    path = root / "freeze.json"
    if not path.exists():
        raise DatasetError(f"{path} missing; the dataset is not frozen")
    frozen = json.loads(path.read_text())
    if _sha256_files(root) != frozen["files"]:
        raise DatasetError(f"{root}: fixture files changed since freeze.json was written")
    return frozen


def _code_context(tree: Path, diff: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        for path in touched_paths(diff):
            source = Path(tree) / path
            if source.is_file():
                target = Path(tmp) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        subprocess.run(["git", "apply", "-"], cwd=tmp, input=diff, text=True, capture_output=True, check=True)
        return build_repo_context(Path(tmp), diff)


async def _assess_fixtures(fixtures: list[dict], tree: Path) -> tuple[list[dict], list[dict]]:
    cfg = config.get_judgments_config()
    rows: list[dict] = []
    receipts: list[dict] = []
    for fixture in sorted(fixtures, key=lambda row: row["id"]):
        packet = build_packet(
            fixture["criteria"],
            diff=fixture["diff"],
            code=_code_context(tree, fixture["diff"]),
            checks=load_checks(fixture["checks"]),
            candidate={"kind": "fixture", "head": fixture["id"]},
            verification_note=fixture["verification_note"],
        )
        ledger = JudgmentLedger(cfg["max_calls_per_turn"], cfg["max_cost_usd"])
        try:
            await decision_review.assess(packet, mode="explicit", ledger=ledger)
        except JudgmentError:
            pass
        receipt = asdict(ledger.receipts[0])
        receipts.append(receipt)
        labels = receipt["detail"]["labels"] if receipt["status"] == "answered" else {}
        for pair in pairs([fixture]):
            answer = receipt["answers"].get(pair["criterion"])
            rows.append({
                **pair,
                "label": labels.get(pair["criterion"]),
                "probabilities": answer["probabilities"] if answer else None,
            })
    return rows, receipts


def _fmt_proportion(value: dict) -> str:
    if not value["n"]:
        return f"{value['k']}/0 (n/a)"
    low, high = value["ci"]
    return f"{value['k']}/{value['n']} = {value['rate']:.3f} (Wilson 95% {low:.3f} to {high:.3f})"


def _fmt_number(value, spec: str) -> str:
    return "n/a" if value is None else format(value, spec)


def _markdown(report: dict) -> str:
    metrics, cost = report["metrics"], report["receipts"]
    lines = [
        f"# Requirement assessments eval ({report['split']})",
        "",
        f"- commit: `{report['commit']}`",
        f"- rubric: `{report['rubric_version']}`, threshold {report['threshold']}",
        f"- model: `{report['model']}`, location `{report['location']}`",
        f"- false supported: {_fmt_proportion(metrics['false_supported'])}",
        f"- contradicted recall: {_fmt_proportion(metrics['contradicted_recall'])}",
        f"- abstention: {metrics['abstention']['k']}/{metrics['abstention']['n']}, "
        f"coverage {_fmt_number(metrics['coverage'], '.3f')}",
        f"- failed pairs: {metrics['failed']}",
        f"- ambiguous pairs (excluded): {metrics['ambiguous']['count']}",
        f"- calls: {cost['calls']}, answered {cost['answered']}",
        f"- cost: ${cost['cost_usd_total']:.4f} total, ${_fmt_number(cost['cost_usd_mean'], '.4f')} mean",
        f"- latency: p50 {_fmt_number(cost['latency_p50_ms'], '.0f')} ms, p95 {_fmt_number(cost['latency_p95_ms'], '.0f')} ms",
    ]
    if report["passed"] is not None:
        lines += [
            f"- release bar (false supported <= {report['release_bar']['false_supported_max']}, point estimate): "
            f"**{'PASS' if report['passed'] else 'FAIL'}**",
            "- this many locked pairs cannot prove a rate at or below 5%; read the Wilson upper bound",
        ]
    lines += ["", "## By kind", "", "| kind | gold | shown | pairs |", "| --- | --- | --- | --- |"]
    lines += [
        f"| {kind} | {gold} | {shown} | {count} |"
        for kind, golds in sorted(metrics["by_kind"].items())
        for gold, shown_counts in sorted(golds.items())
        for shown, count in sorted(shown_counts.items())
    ]
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.split == "test" and not args.locked_final:
        raise LockedSplitError("test split is locked; pass --locked-final only for the J4 locked run")
    if is_killed():
        raise DatasetError(KILLED_MESSAGE)
    if judgments.resolve_api_key() is None:
        raise DatasetError(MISSING_KEY_MESSAGE)
    frozen = _frozen(root)
    fixtures = load_fixtures(root, split=args.split, locked_final=args.locked_final)
    reports = root / "reports"
    report_path = reports / f"review-{args.split}.json"
    if args.split == "test" and report_path.exists():
        raise DatasetError(f"{report_path} exists; the locked test split is scored once")
    tree = args.tree or materialize()
    reports.mkdir(parents=True, exist_ok=True)
    if args.split == "test":
        report_path.write_text(json.dumps({
            "schema_version": 1, "split": "test", "status": "started",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "threshold": decision_review.THRESHOLD, "rubric_version": decision_review.RUBRIC_VERSION,
        }, indent=2) + "\n")
    rows, receipts = asyncio.run(_assess_fixtures(fixtures, tree))
    out_dir = reports / f"review-{args.split}"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / "rows.jsonl", rows)
    _write_jsonl(out_dir / "receipts.jsonl", receipts)
    metrics = score(rows)
    report = {
        "schema_version": 1,
        "status": "complete",
        "split": args.split,
        "commit": frozen["commit"],
        "rubric_version": decision_review.RUBRIC_VERSION,
        "threshold": decision_review.THRESHOLD,
        "model": _common_value([r for r in receipts if r["model_returned"]], "model_returned"),
        "location": args.location,
        "run_date": datetime.now(timezone.utc).date().isoformat(),
        "metrics": metrics,
        "receipts": receipt_summary(receipts),
        "release_bar": frozen["release_bar"],
        "passed": metrics["passed"] if args.split == "test" else None,
    }
    (reports / f"review-{args.split}.md").write_text(_markdown(report))
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {report_path}")
    return 0


def _relabel(row: dict, threshold: float) -> dict:
    if not row["probabilities"] or row["label"] in (None, "no_answer"):
        return row
    return {**row, "label": decision_review.label_for(SimpleNamespace(probabilities=row["probabilities"]), threshold)}


def tune(args: argparse.Namespace) -> int:
    path = Path(args.report or Path(args.root) / "reports" / "review-dev.json")
    report = json.loads(path.read_text())
    if report.get("split") != "dev" or report.get("status") != "complete":
        raise DatasetError(f"{path}: tune reads only a complete dev report")
    rows = _read_jsonl(path.with_suffix("") / "rows.jsonl")
    print("threshold  false_supported  contradicted_recall  coverage")
    for threshold in TUNE_THRESHOLDS:
        metrics = score([_relabel(row, threshold) for row in rows])
        false_supported, recall = metrics["false_supported"], metrics["contradicted_recall"]
        print(
            f"{threshold:.2f}  {_fmt_number(false_supported['rate'], '.3f')} ({false_supported['k']}/{false_supported['n']})"
            f"  {_fmt_number(recall['rate'], '.3f')} ({recall['k']}/{recall['n']})"
            f"  {_fmt_number(metrics['coverage'], '.3f')}"
        )
    return 0


def _card(fixture: dict, tree: Path) -> SimpleNamespace:
    checks = load_checks(fixture["checks"])
    return SimpleNamespace(
        original_idea=fixture["title"],
        acceptance_criteria="\n".join(fixture["criteria"]),
        artifact=None,
        artifact_text="\n".join(f"{check.name}: {check.status}" for check in checks) or NO_CHECKS,
        file_diff=fixture["diff"],
        a_verification_summary=fixture["verification_note"],
        repo_context=_code_context(tree, fixture["diff"]),
    )


def baseline_b(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.split != "dev" and not args.locked_final:
        raise LockedSplitError("test split is locked; pass --locked-final only for the J4 locked baseline")
    out = root / "reports" / f"reviewer-b-baseline-{args.split}.json"
    if out.exists():
        raise DatasetError(f"{out} exists; the Reviewer B baseline runs once per split")
    _frozen(root)
    splits = SPLITS if args.split == "all" else (args.split,)
    fixtures = [row for split in splits for row in load_fixtures(root, split=split, locked_final=args.locked_final)]
    tree = args.tree or materialize()
    try:
        provider, _ = runner._provider_for_eval(stub=False, auth_pref=args.auth)
    except click.exceptions.Exit as exc:
        return exc.exit_code
    reviewer = ReviewerB(provider=provider, fast_model=args.model, strong_model=args.model, cwd=tree)
    rows = []
    for fixture in sorted(fixtures, key=lambda row: row["id"]):
        row = {"fixture": fixture["id"], "split": fixture["split"], "kind": fixture["kind"]}
        try:
            verdict = reviewer.review(_card(fixture, tree), tier="strong")
        except Exception as exc:
            rows.append({**row, "verdict": None, "conf": None, "evidence_refs": [], "domain_inferred": None,
                         "error": type(exc).__name__})
            continue
        rows.append({
            **row, "verdict": verdict.verdict, "conf": verdict.conf, "evidence_refs": list(verdict.evidence_refs),
            "domain_inferred": verdict.domain_inferred, "error": None,
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema_version": 1, "split": args.split, "model": args.model, "auth": args.auth,
        "run_date": datetime.now(timezone.utc).date().isoformat(), "rows": rows,
    }, indent=2) + "\n")
    errors = sum(1 for row in rows if row["error"])
    print(f"wrote {out} ({len(rows)} fixtures, {errors} errors)")
    return 0


def _baseline_rows(reports: Path) -> list[dict]:
    for name in ("reviewer-b-baseline-test.json", "reviewer-b-baseline-all.json"):
        path = reports / name
        if path.exists():
            return [row for row in json.loads(path.read_text())["rows"] if row["split"] == "test"]
    raise DatasetError(f"{reports}: no Reviewer B baseline for the test split")


def compare(args: argparse.Namespace) -> int:
    reports = Path(args.root) / "reports"
    report_path = reports / "review-test.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    if report.get("status") != "complete":
        raise DatasetError(f"{report_path}: needs a complete locked run")
    rows = _read_jsonl(reports / "review-test" / "rows.jsonl")
    negative: dict[str, list[dict]] = {}
    for row in rows:
        if row["flag"] != "ambiguous" and row["gold"] != "supported":
            negative.setdefault(row["fixture"], []).append(row)
    verdicts = {row["fixture"]: row for row in _baseline_rows(reports)}
    answered = sorted(fid for fid in negative if fid in verdicts and verdicts[fid]["error"] is None)
    b_passes = sum(1 for fid in answered if verdicts[fid]["verdict"] == "pass")
    jev_misses = sum(1 for fid in answered if any(row["label"] == "supported" for row in negative[fid]))
    result = {
        "schema_version": 1,
        "informational": True,
        "split": "test",
        "negative_fixtures": len(negative),
        "compared_fixtures": len(answered),
        "reviewer_b_errors": len(negative) - len(answered),
        "reviewer_b_passes": _proportion(b_passes, len(answered)),
        "jev_fixture_false_supported": _proportion(jev_misses, len(answered)),
        "jev_pair_false_supported": report["metrics"]["false_supported"],
        "threshold": report["threshold"],
    }
    (reports / "review-compare.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Reviewer B baseline (informational, outside the release bar)")
    print(f"- fixtures with a labeled missing or contradicted criterion: {len(negative)}")
    print(f"- Reviewer B passed: {_fmt_proportion(result['reviewer_b_passes'])}")
    print(f"- Reviewer B errors: {result['reviewer_b_errors']}")
    print(f"- Jev showed supported on one of them: {_fmt_proportion(result['jev_fixture_false_supported'])}")
    print(f"- Jev pair-level false supported: {_fmt_proportion(result['jev_pair_false_supported'])}")
    return 0


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
    run_parser = commands.add_parser("run", help="assess each fixture of a split with Jev and write the report")
    run_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    run_parser.add_argument("--split", choices=SPLITS, default="dev")
    run_parser.add_argument("--locked-final", action="store_true")
    run_parser.add_argument("--location", required=True)
    run_parser.add_argument("--tree", type=Path)
    run_parser.set_defaults(handler=run)
    tune_parser = commands.add_parser("tune", help="replay a dev report at thresholds 0.55 to 0.95 without calling Jev")
    tune_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    tune_parser.add_argument("--report", type=Path)
    tune_parser.set_defaults(handler=tune)
    baseline_parser = commands.add_parser("baseline-b", help="run the real Reviewer B on the same fixtures")
    baseline_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    baseline_parser.add_argument("--split", choices=(*SPLITS, "all"), default="dev")
    baseline_parser.add_argument("--locked-final", action="store_true")
    baseline_parser.add_argument("--auth", default="claude")
    baseline_parser.add_argument("--model", default=BASELINE_MODEL)
    baseline_parser.add_argument("--tree", type=Path)
    baseline_parser.set_defaults(handler=baseline_b)
    compare_parser = commands.add_parser("compare", help="compare the Reviewer B baseline with Jev on the locked split")
    compare_parser.add_argument("--root", type=Path, default=DATASET_ROOT)
    compare_parser.set_defaults(handler=compare)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except DatasetError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
