"""J4 requirement-review sets: frozen-hash check, import, baselines, metrics and report."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .report import UNDERPOWERED, fmt_proportion, proportion
from .spec import ReviewRecord
from .store import Store

ABSTAINED = ("abstained", "no_answer", None)
AUTHOR_CLAIM = "rule: accept every change as its author presents it"
REJECT_ALL = "rule: reject every change"


class ReviewDataError(Exception):
    pass


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_freeze(root: Path) -> dict:
    frozen = json.loads((root / "freeze.json").read_text())
    paths = [root / "corpus.json", *sorted((root / "fixtures").glob("*.jsonl"))]
    actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if actual != frozen["files"]:
        raise ReviewDataError(f"{root}: fixture files changed since freeze.json was written")
    return frozen


def _baseline_rows(reports: Path, split: str) -> tuple[Path, list[dict]] | None:
    for name in (f"reviewer-b-baseline-{split}.json", "reviewer-b-baseline-all.json"):
        path = reports / name
        if path.exists():
            data = json.loads(path.read_text())
            return path, [{**row, "model": data.get("model")} for row in data["rows"] if row["split"] == split]
    return None


def _jev_decision(labels: dict[str, str | None]) -> str | None:
    if any(label is None for label in labels.values()):
        return None
    return "accept" if all(label == "supported" for label in labels.values()) else "reject"


def import_review(root: Path, split: str, store: Store) -> list[ReviewRecord]:
    """Read a frozen set's finished reports. Labels are copied, never re-scored or relabeled."""
    root = root.resolve()
    frozen = verify_freeze(root)
    reports = root / "reports"
    report_path = reports / f"review-{split}.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    if report.get("status") != "complete":
        raise ReviewDataError(f"{report_path}: needs a complete run")
    if report["commit"] != frozen["commit"]:
        raise ReviewDataError(f"{report_path}: commit differs from freeze.json")
    fixtures = sorted((row for path in sorted((root / "fixtures").glob("*.jsonl")) for row in _jsonl(path)
                       if row["split"] == split), key=lambda row: row["id"])
    rows = _jsonl(reports / f"review-{split}" / "rows.jsonl")
    receipts = _jsonl(reports / f"review-{split}" / "receipts.jsonl")
    artifacts = {
        "report": store.put(report_path.read_bytes()),
        "rows": store.put((reports / f"review-{split}" / "rows.jsonl").read_bytes()),
        "receipts": store.put((reports / f"review-{split}" / "receipts.jsonl").read_bytes()),
    }
    baseline = _baseline_rows(reports, split)
    if baseline:
        artifacts["reviewer_b"] = store.put(baseline[0].read_bytes())
    pairs = defaultdict(dict)
    for row in rows:
        pairs[row["fixture"]][row["criterion"]] = row
    receipt_for = {r["detail"]["candidate"]["head"]: r for r in receipts if r.get("detail")}
    verdicts = {row["fixture"]: row for row in baseline[1]} if baseline else {}

    def record(config: str, source: str, fixture: dict, **fields) -> ReviewRecord:
        return ReviewRecord(
            experiment_id=store.experiment_id, config=config, source=source, dataset=root.name, split=split,
            freeze_commit=frozen["commit"], rubric_version=report["rubric_version"], fixture=fixture["id"],
            kind=fixture["kind"], gold={c: v["gold"] for c, v in fixture["labels"].items()},
            flags={c: v["flag"] for c, v in fixture["labels"].items()}, **fields,
        )

    records = []
    for fx in fixtures:
        cids = list(fx["labels"])
        records.append(record("author-claim", AUTHOR_CLAIM, fx, decision="accept",
                              labels=dict.fromkeys(cids, "supported"), cost_usd=0.0))
        records.append(record("reject-all", REJECT_ALL, fx, decision="reject",
                              labels=dict.fromkeys(cids, "abstained"), cost_usd=0.0))
        if fx["id"] not in pairs:
            raise ReviewDataError(f"{fx['id']}: no Jev rows in {report_path.parent}")
        labels = {c: pairs[fx["id"]][c]["label"] for c in cids}
        receipt = receipt_for.get(fx["id"], {})
        records.append(record(
            "jev", f"rows {artifacts['rows'][:12]}", fx, decision=_jev_decision(labels), labels=labels,
            probabilities={c: pairs[fx["id"]][c]["probabilities"] for c in cids},
            model=receipt.get("model_returned"), cost_usd=receipt.get("cost_usd"),
            error=None if receipt.get("status") == "answered" else receipt.get("status", "no receipt"),
        ))
        if b := verdicts.get(fx["id"]):
            records.append(record(
                "reviewer-b", f"baseline {artifacts['reviewer_b'][:12]}", fx,
                decision=None if b["error"] else ("accept" if b["verdict"] == "pass" else "reject"),
                confidence=b["conf"], model=b["model"], error=b["error"],
            ))
    with (store.root / "review.jsonl").open("w") as f:
        f.writelines(r.model_dump_json() + "\n" for r in records)
    store.write_manifest({
        "experiment_id": store.experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv,
        "dataset": str(root),
        "split": split,
        "freeze": {k: frozen[k] for k in ("commit", "rubric_version", "seed", "files")},
        "report_rubric_version": report["rubric_version"],
        "threshold": report.get("threshold"),
        "artifacts": artifacts,
    })
    return records


def run_dev(root: Path, location: str, dest: Path) -> Path:
    """Run `voss.eval.review` on the dev split in a copy of the set, so Voss's files stay untouched."""
    shutil.copytree(root, dest)
    subprocess.run([sys.executable, "-m", "voss.eval.review", "run", "--root", str(dest),
                    "--split", "dev", "--location", location], check=True)
    return dest


def read_review(root: Path) -> list[ReviewRecord]:
    return [ReviewRecord.model_validate_json(line)
            for line in (root / "review.jsonl").read_text().splitlines() if line.strip()]


def summarize(records: list[ReviewRecord]) -> dict[str, dict]:
    out = {}
    by_config = defaultdict(list)
    for r in records:
        by_config[r.config].append(r)
    for name, rows in by_config.items():
        clear = [r for r in rows if all(f != "ambiguous" for f in r.flags.values())]
        good = [r for r in clear if all(g == "supported" for g in r.gold.values())]
        bad = [r for r in clear if any(g != "supported" for g in r.gold.values())]
        s = {
            "source": rows[0].source,
            "fixtures": len(rows),
            "ambiguous_fixtures": len(rows) - len(clear),
            "false_accept": proportion(sum(r.decision == "accept" for r in bad), len(bad)),
            "true_accept": proportion(sum(r.decision == "accept" for r in good), len(good)),
            "no_decision": sum(r.decision is None for r in clear),
            "confidence_mean": None,
            "pairs": None,
        }
        confs = [r.confidence for r in rows if r.confidence is not None]
        if confs:
            s["confidence_mean"] = sum(confs) / len(confs)
        costs = [r.cost_usd for r in rows if r.cost_usd is not None]
        s["cost_total"] = math.fsum(costs) if costs else None
        s["cost_known"] = len(costs)
        if rows[0].labels is not None:
            scored = [(r.gold[c], r.labels[c], (r.probabilities or {}).get(c))
                      for r in rows for c in r.gold if r.flags[c] != "ambiguous"]
            negatives = [p for p in scored if p[0] != "supported"]
            errors = [(prob["supported"] - (gold == "supported")) ** 2 for gold, _, prob in scored if prob]
            abstained = sum(label in ABSTAINED for _, label, _ in scored)
            s["pairs"] = {
                "n": len(scored),
                "false_supported": proportion(sum(label == "supported" for _, label, _ in negatives), len(negatives)),
                "supported_recall": proportion(sum(label == "supported" for g, label, _ in scored if g == "supported"),
                                          sum(g == "supported" for g, _, _ in scored)),
                "contradicted_recall": proportion(sum(label == "contradicted" for g, label, _ in scored
                                                 if g == "contradicted"),
                                             sum(g == "contradicted" for g, _, _ in scored)),
                "abstention": proportion(abstained, len(scored)),
                "brier": math.fsum(errors) / len(errors) if errors else None,
                "brier_n": len(errors),
            }
        out[name] = s
    return dict(sorted(out.items()))


def render(records: list[ReviewRecord], title: str) -> str:
    summary = summarize(records)
    first = records[0]
    lines = [
        f"# {title}", "",
        f"Dataset `{first.dataset}`, split `{first.split}`, frozen at `{first.freeze_commit[:12]}`, "
        f"rubric `{first.rubric_version}`. Imported from finished runs; no label was re-scored.", "",
        "## Change-level decisions", "",
        "A change should be accepted only when every criterion's gold label is *supported*. "
        "Both rates are shown together: a reviewer that rejects everything has a perfect false-accept rate "
        "and a true-accept rate of 0.", "",
        "| config | source | false accept (Wilson 95%) | true accept (Wilson 95%) | no decision "
        "| self-reported confidence | cost |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in summary.items():
        conf = "n/a" if s["confidence_mean"] is None else f"mean {s['confidence_mean']:.2f}"
        cost = ("unknown" if s["cost_total"] is None
                else f"${s['cost_total']:.4f} ({s['cost_known']}/{s['fixtures']} known)")
        lines.append(f"| {name} | {s['source']} | {fmt_proportion(s['false_accept'])} | {fmt_proportion(s['true_accept'])} "
                     f"| {s['no_decision']} | {conf} | {cost} |")
    lines += ["", "## Criterion-level labels", "",
              "Only configs that label each criterion appear here. Brier uses the categorical P(supported); "
              "self-reported confidence is never scored as a probability.", "",
              "| config | pairs | false supported | supported recall | contradicted recall | abstention | Brier |",
              "|---|---|---|---|---|---|---|"]
    for name, s in summary.items():
        p = s["pairs"]
        if p is None:
            continue
        brier = "n/a" if p["brier"] is None else f"{p['brier']:.4f} (n={p['brier_n']})"
        lines.append(f"| {name} | {p['n']} | {fmt_proportion(p['false_supported'])} | {fmt_proportion(p['supported_recall'])} "
                     f"| {fmt_proportion(p['contradicted_recall'])} | {fmt_proportion(p['abstention'])} | {brier} |")
    missing = [f"{name}: {s['ambiguous_fixtures']} fixtures with an ambiguous criterion are left out of "
               f"change-level rates" for name, s in summary.items() if s["ambiguous_fixtures"]]
    missing += [f"{r.config} x {r.fixture}: {r.error}" for r in records if r.error]
    if missing:
        lines += ["", "## Missing data and errors", ""] + [f"- {m}" for m in missing[:20]]
    lines += ["", "## Reading this report", "",
              f"- **underpowered** marks a rate over fewer than {UNDERPOWERED} items. Read its interval, "
              "not its point estimate.",
              "- *author-claim* and *reject-all* are rules, not models. They bound what a reviewer has to beat.",
              "- Reviewer B returns one verdict per change, so it has no criterion-level row."]
    return "\n".join(lines) + "\n"


def write_review_report(results: Path) -> Path:
    out = results / "review.md"
    out.write_text(render(read_review(results), f"VossProofs review report: {results.name}"))
    return out
